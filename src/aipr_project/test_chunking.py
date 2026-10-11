
from aipr_project.rag.models import Document
from aipr_project.rag.chunking import chunk_document


document = Document(
    doc_id="DRL001",
    title="Quy chế điểm rèn luyện",
    version="1.0",
    date="2026-10-11",
    owner="Phòng Công tác sinh viên",
    content=(
        "QUY CHẾ ĐIỂM RÈN LUYỆN\n\n"
        "Điều 1. Phạm vi áp dụng\n"
        "Quy chế áp dụng cho sinh viên chính quy.\n\n"
        "Điều 2. Nguyên tắc đánh giá\n"
        "Sinh viên được đánh giá theo các tiêu chí quy định."
    ),
)

chunks = chunk_document(document)

print(f"So chunk: {len(chunks)}")

for chunk in chunks:
    print("\n--------------------")
    print(f"Chunk ID: {chunk.chunk_id}")
    print(f"Document ID: {chunk.doc_id}")
    print(f"Title: {chunk.title}")
    print(f"Version: {chunk.version}")
    print(f"Owner: {chunk.owner}")
    print(f"Content:\n{chunk.content}")
