import json
from pathlib import Path

from aipr_project.rag.models import Document
from aipr_project.rag.store import DocumentStore
from aipr_project.rag.embeddings import batch_embed_key


# Thư mục gốc của project
PROJECT_ROOT = Path(__file__).resolve().parents[3]

DOCS_DIR = PROJECT_ROOT / "data" / "source_docs"
INDEX_DIR = PROJECT_ROOT / "data" / "index"

SOURCE_FILES = [
    "quy_dinh_diem_ren_luyen.md",
    "so_tay_sinh_vien.md",
]


def read_document(path: Path) -> Document:
    """Đọc Markdown và lấy metadata từ YAML frontmatter."""

    text = path.read_text(encoding="utf-8")

    if not text.startswith("---"):
        raise ValueError(f"Thiếu YAML frontmatter: {path.name}")

    parts = text.split("---", 2)

    if len(parts) != 3:
        raise ValueError(f"Frontmatter không hợp lệ: {path.name}")

    metadata_text = parts[1]
    content = parts[2].strip()

    # Đọc các trường metadata đơn giản trong YAML
    metadata = {}

    for line in metadata_text.splitlines():
        if ":" not in line:
            continue

        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"').strip("'")

    required_fields = ["doc_id", "title", "version"]

    for field in required_fields:
        if not metadata.get(field):
            raise ValueError(
                f"Thiếu trường {field} trong {path.name}"
            )

    return Document(
        doc_id=metadata["doc_id"],
        title=metadata["title"],
        version=metadata["version"],
        date=metadata.get("date", ""),
        owner=metadata.get("owner", ""),
        content=content,
        metadata=metadata,
    )


def main():
    store = DocumentStore()

    # 1. Đọc tài liệu và chia chunks
    for filename in SOURCE_FILES:
        path = DOCS_DIR / filename

        if not path.exists():
            raise FileNotFoundError(f"Không tìm thấy: {path}")

        doc = read_document(path)
        store.add(doc)

        print(f"Đã đọc: {doc.doc_id} - {doc.title}")

    # 2. Lấy tất cả chunks
    chunks = [
        chunk
        for doc in store.list_all()
        for chunk in store.get_chunk_by_doc(doc.doc_id)
    ]

    if not chunks:
        raise ValueError("Không có chunks để tạo index.")

    print(f"\nSố tài liệu: {store.count()['documents']}")
    print(f"Số chunks: {len(chunks)}")

    # 3. Tạo embeddings theo batch
    embeddings = batch_embed_key(
        [chunk.content for chunk in chunks]
    )

    if len(embeddings) != len(chunks):
        raise ValueError("Số embeddings không khớp số chunks.")

    # 4. Lưu chunks và embeddings
    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    index_data = {
        "chunks": [
            {
                "chunk_id": chunk.chunk_id,
                "doc_id": chunk.doc_id,
                "title": chunk.title,
                "version": chunk.version,
                "date": chunk.date,
                "owner": chunk.owner,
                "content": chunk.content,
                "metadata": chunk.metadata,
            }
            for chunk in chunks
        ],
        "embeddings": embeddings,
    }

    output_path = INDEX_DIR / "index.json"

    output_path.write_text(
        json.dumps(index_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\nĐã lưu index tại: {output_path}")
    print("Build index thành công!")


if __name__ == "__main__":
    main()
