
from aipr_project.rag.models import Document, DocumentChunk


def chunk_documents(doc: Document, chunk_size: int = 512,overlap: int = 64) -> list[DocumentChunk]:
    chunks = []
    text = doc.content
    step = chunk_size - overlap
    start = 0
    while start < len(text):
        content = text[start:start + chunk_size]

        chunks.append(
            DocumentChunk(
                chunk_id=f"{doc.doc_id}_{len(chunks)}",
                doc_id=doc.doc_id,
                title=doc.title,
                version=doc.version,
                content=content,
                date=doc.date,
                owner=doc.owner,
                metadata=doc.metadata,
            )
        )
        start += step
    return chunks
