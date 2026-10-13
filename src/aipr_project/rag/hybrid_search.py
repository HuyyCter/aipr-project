from rank_bm25 import BM25Okapi
from w3.jina_embeddings import cosine_similiarity, embed_key

from aipr_project.rag.models import DocumentChunk


def normalise_scores(scores: list[float]) -> list[float]:
    if not scores:
        return []

    min_score = min(scores)
    max_score = max(scores)

    if min_score == max_score:
        return [1.0] * len(scores)

    return [(score - min_score) / (max_score - min_score) for score in scores]


def build_bm25_index(chunks: list[DocumentChunk]) -> BM25Okapi:
    tokenized = [chunk.content.lower().split() for chunk in chunks]
    return BM25Okapi(tokenized)


def hybrid_search(
    query: str,
    chunks: list[DocumentChunk],
    embeddings: list[list[float]],
    bm25_index: BM25Okapi,
    top_k: int = 3,
    w_bm25: float = 0.5,
    w_vector: float = 0.5,
) -> list[tuple[int, float]]:
    if not chunks:
        return []

    bm25_scores = list(bm25_index.get_scores(query.lower().split()))
    query_vector = embed_key(query)

    vector_scores = [cosine_similiarity(query_vector, vector) for vector in embeddings]

    bm25_scores = normalise_scores(bm25_scores)

    scores = [
        w_bm25 * bm25 + w_vector * vector
        for bm25, vector in zip(bm25_scores, vector_scores)
    ]

    return sorted(
        enumerate(scores),
        key=lambda item: item[1],
        reverse=True,
    )[:top_k]
