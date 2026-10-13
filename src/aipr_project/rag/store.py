from aipr_project.rag.chunking import chunk_documents
from aipr_project.rag.models import Document, DocumentChunk


class DocumentStore:
    def __init__(self):
        self._docs: dict[str, Document] = {}
        self._chunks: dict[str, DocumentChunk] = {}

    def add(self, doc: Document) -> str:
        if not doc.doc_id:
            doc.doc_id = f"DOC{len(self._docs) + 1:03d}"

        self._docs[doc.doc_id] = doc

        for chunk in chunk_documents(doc):
            self.add_chunk(chunk)

        return doc.doc_id

    def get(self, doc_id: str):
        return self._docs.get(doc_id)

    def delete(self, doc_id: str) -> bool:
        if doc_id not in self._docs:
            return False

        del self._docs[doc_id]

        for chunk_id, chunk in list(self._chunks.items()):
            if chunk.doc_id == doc_id:
                del self._chunks[chunk_id]

        return True

    def list_all(self) -> list[Document]:
        return list(self._docs.values())

    def add_chunk(self, chunk: DocumentChunk) -> str:
        if not chunk.chunk_id:
            chunk.chunk_id = f"CHUNK{len(self._chunks) + 1:04d}"

        self._chunks[chunk.chunk_id] = chunk
        return chunk.chunk_id

    def get_chunk(self, chunk_id: str):
        return self._chunks.get(chunk_id)

    def get_chunk_by_doc(self, doc_id: str) -> list[DocumentChunk]:
        return [chunk for chunk in self._chunks.values() if chunk.doc_id == doc_id]

    def count(self) -> dict[str, int]:
        return {
            "documents": len(self._docs),
            "chunks": len(self._chunks),
        }
