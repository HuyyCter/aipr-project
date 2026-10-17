
"""Document storage and hybrid retrieval for the RAG system."""

import re
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi

from aipr_project.rag.models import Document, DocumentChunk
from aipr_project.rag.chunking import chunk_documents
from aipr_project.common.json_codec import save_chunks, load_chunks
from aipr_project.rag.embeddings import embed_key, batch_embed_key


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CACHE_PATH = PROJECT_ROOT / "data" / "store_cache.json"

DEFAULT_EMBEDDING_MODEL = "jina-embeddings-v3"
DEFAULT_CHUNK_SIZE = 800
DEFAULT_OVERLAP = 100
EMBEDDING_BATCH_SIZE = 32


def _tokenize(text: str) -> list[str]:
    """Tokenize text for BM25, including Vietnamese text."""
    return re.findall(r"\w+", text.lower(), flags=re.UNICODE)


class DocumentStore:
    """Store documents and retrieve relevant chunks."""

    def __init__(
        self,
        llm_client=None,
        cache_path: str | Path | None = None,
    ):
        self._docs: dict[str, Document] = {}
        self._chunks: dict[str, DocumentChunk] = {}
        self.llm_client = llm_client
        self.cache_path = (
            Path(cache_path) if cache_path else DEFAULT_CACHE_PATH
        )

        self._load_cache()

    # ---------------------------------------------------------
    # Cache
    # ---------------------------------------------------------

    def _load_cache(self) -> None:
        """Load previously saved chunks and embeddings."""
        if not self.cache_path.exists():
            return

        for chunk in load_chunks(self.cache_path):
            self._chunks[chunk.chunk_id] = chunk

    def _save_cache(self) -> None:
        """Persist all chunks, including their embeddings."""
        save_chunks(self.cache_path, list(self._chunks.values()))

    # ---------------------------------------------------------
    # Documents and chunks
    # ---------------------------------------------------------

    def add(self, doc: Document) -> str:
        """Add or update a document and remove obsolete chunks."""
        if not doc.doc_id:
            doc.doc_id = f"DOC{len(self._docs) + 1:03d}"

        self._docs[doc.doc_id] = doc

        new_chunks = chunk_documents(
            doc,
            chunk_size=DEFAULT_CHUNK_SIZE,
            overlap=DEFAULT_OVERLAP,
        )
        new_chunk_ids = {chunk.chunk_id for chunk in new_chunks}

        # Remove obsolete chunks when a document is updated.
        for chunk_id, old_chunk in list(self._chunks.items()):
            if (
                old_chunk.doc_id == doc.doc_id
                and chunk_id not in new_chunk_ids
            ):
                del self._chunks[chunk_id]

        # Reuse cached embeddings when the content is unchanged.
        for chunk in new_chunks:
            self.add_chunk(chunk, save=False)

        self._save_cache()
        return doc.doc_id

    def get(self, doc_id: str) -> Document | None:
        return self._docs.get(doc_id)

    def delete(self, doc_id: str) -> bool:
        if doc_id not in self._docs:
            return False

        del self._docs[doc_id]

        for chunk_id, chunk in list(self._chunks.items()):
            if chunk.doc_id == doc_id:
                del self._chunks[chunk_id]

        self._save_cache()
        return True

    def list_all(self) -> list[Document]:
        return list(self._docs.values())

    def add_chunk(
        self,
        chunk: DocumentChunk,
        save: bool = True,
    ) -> str:
        """Add a chunk and reuse its cached embedding if valid."""
        if not chunk.chunk_id:
            chunk.chunk_id = f"CHUNK{len(self._chunks) + 1:04d}"

        previous = self._chunks.get(chunk.chunk_id)

        if previous is not None and previous.content == chunk.content:
            if chunk.embedding is None:
                chunk.embedding = previous.embedding

        self._chunks[chunk.chunk_id] = chunk

        if save:
            self._save_cache()

        return chunk.chunk_id

    def get_chunk(self, chunk_id: str) -> DocumentChunk | None:
        return self._chunks.get(chunk_id)

    def get_chunk_by_doc(self, doc_id: str) -> list[DocumentChunk]:
        return [
            chunk
            for chunk in self._chunks.values()
            if chunk.doc_id == doc_id
        ]

    def count(self) -> dict[str, int]:
        return {
            "documents": len(self._docs),
            "chunks": len(self._chunks),
        }

    # ---------------------------------------------------------
    # Embeddings
    # ---------------------------------------------------------

    def _ensure_embeddings(self) -> None:
        """Create embeddings only for chunks that lack them."""
        missing = [
            chunk
            for chunk in self._chunks.values()
            if chunk.embedding is None
        ]

        if not missing:
            return

        for start in range(0, len(missing), EMBEDDING_BATCH_SIZE):
            batch = missing[start:start + EMBEDDING_BATCH_SIZE]

            vectors = batch_embed_key(
                [chunk.content for chunk in batch],
                model=DEFAULT_EMBEDDING_MODEL,
            )

            if len(vectors) != len(batch):
                raise RuntimeError(
                    "Số embedding trả về không khớp số chunks."
                )

            for chunk, vector in zip(batch, vectors):
                if not vector:
                    raise RuntimeError(
                        f"Embedding rỗng cho chunk {chunk.chunk_id}."
                    )

                chunk.embedding = [float(value) for value in vector]

        self._save_cache()

    def _embed_query(self, query: str) -> list[float]:
        """Create an embedding for the search query."""
        vector = embed_key(
            query,
            model=DEFAULT_EMBEDDING_MODEL,
        )

        if not vector:
            raise RuntimeError("Không nhận được embedding cho query.")

        return [float(value) for value in vector]

    # ---------------------------------------------------------
    # BM25 retrieval
    # ---------------------------------------------------------

    def _bm25_search(
        self,
        query: str,
        top_k: int,
    ) -> list[tuple[DocumentChunk, float]]:
        chunks = list(self._chunks.values())

        if not chunks or top_k <= 0:
            return []

        corpus = [_tokenize(chunk.content) for chunk in chunks]
        query_tokens = _tokenize(query)

        if not query_tokens:
            return []

        # Empty tokenized documents can cause issues in some BM25 setups.
        bm25 = BM25Okapi(corpus)
        scores = bm25.get_scores(query_tokens)

        ranked_indices = sorted(
            range(len(chunks)),
            key=lambda i: float(scores[i]),
            reverse=True,
        )

        return [
            (chunks[i], float(scores[i]))
            for i in ranked_indices[:top_k]
            if scores[i] > 0
        ]

    # ---------------------------------------------------------
    # Dense retrieval
    # ---------------------------------------------------------

    def _dense_search(
        self,
        query: str,
        top_k: int,
    ) -> list[tuple[DocumentChunk, float]]:
        chunks = [
            chunk
            for chunk in self._chunks.values()
            if chunk.embedding is not None
        ]

        if not chunks or top_k <= 0:
            return []

        query_vector = np.asarray(
            self._embed_query(query),
            dtype=np.float32,
        )

        matrix = np.asarray(
            [chunk.embedding for chunk in chunks],
            dtype=np.float32,
        )

        if matrix.ndim != 2 or matrix.shape[1] != query_vector.shape[0]:
            raise ValueError(
                "Kích thước embedding của query và chunks không khớp."
            )

        # Valid for normalized embeddings.
        scores = matrix @ query_vector

        ranked_indices = np.argsort(scores)[::-1][:top_k]

        return [
            (chunks[int(i)], float(scores[int(i)]))
            for i in ranked_indices
        ]

    # ---------------------------------------------------------
    # Hybrid retrieval
    # ---------------------------------------------------------

    def _hybrid_search(
        self,
        query: str,
        top_k: int,
    ) -> list[tuple[DocumentChunk, float]]:
        """Combine BM25 and Dense rankings using RRF."""
        candidate_k = max(top_k * 3, 10)

        bm25_results = self._bm25_search(query, candidate_k)
        dense_results = self._dense_search(query, candidate_k)

        rrf_scores: dict[str, float] = {}
        chunks_by_id: dict[str, DocumentChunk] = {}
        rrf_constant = 60

        for results in (bm25_results, dense_results):
            for rank, (chunk, _score) in enumerate(results, start=1):
                chunks_by_id[chunk.chunk_id] = chunk
                rrf_scores[chunk.chunk_id] = (
                    rrf_scores.get(chunk.chunk_id, 0.0)
                    + 1.0 / (rrf_constant + rank)
                )

        ranked = sorted(
            rrf_scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        return [
            (chunks_by_id[chunk_id], score)
            for chunk_id, score in ranked[:top_k]
        ]

    # ---------------------------------------------------------
    # Public search API
    # ---------------------------------------------------------

    def search(
        self,
        query: str,
        top_k: int = 3,
        mode: str = "hybrid",
    ) -> list[tuple[DocumentChunk, float]]:
        """
        Search using BM25, Dense, or Hybrid retrieval.

        mode:
            "bm25"   - keyword-based retrieval
            "dense"  - embedding similarity
            "hybrid" - Reciprocal Rank Fusion of BM25 and Dense
        """
        if not query or not query.strip():
            return []

        if top_k <= 0:
            return []

        if mode not in {"bm25", "dense", "hybrid"}:
            raise ValueError(
                "mode phải là 'bm25', 'dense' hoặc 'hybrid'."
            )

        if mode == "bm25":
            return self._bm25_search(query, top_k)

        # Dense and Hybrid require embeddings.
        self._ensure_embeddings()

        if mode == "dense":
            return self._dense_search(query, top_k)

        return self._hybrid_search(query, top_k)
