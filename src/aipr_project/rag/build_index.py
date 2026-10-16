
import json
from pathlib import Path

from aipr_project.rag.chunking import parse_document
from aipr_project.rag.store import DocumentStore


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DOCS_DIR = PROJECT_ROOT / "data" / "source_docs"
INDEX_DIR = PROJECT_ROOT / "data" / "index"
INDEX_PATH = INDEX_DIR / "index.json"

CACHE_PATH = PROJECT_ROOT / "data" / "store_cache.json"

SOURCE_FILES = [
    "quy_dinh_diem_ren_luyen.md",
    "so_tay_sinh_vien.md",
]


def main() -> None:
    store = DocumentStore(cache_path=CACHE_PATH)

    # 1. Read and chunk source documents.
    for filename in SOURCE_FILES:
        path = DOCS_DIR / filename

        if not path.exists():
            raise FileNotFoundError(f"Khong tim thay: {path}")

        doc = parse_document(path.read_text(encoding="utf-8"))
        store.add(doc)

        print(f"Da doc: {doc.doc_id} - {doc.title}")

    # 2. Collect chunks from the current documents.
    chunks = [
        chunk
        for doc in store.list_all()
        for chunk in store.get_chunk_by_doc(doc.doc_id)
    ]

    if not chunks:
        raise ValueError("Khong co chunks de tao index.")

    print(f"\nSo tai lieu: {store.count()['documents']}")
    print(f"So chunks: {len(chunks)}")

    # 3. Generate only missing embeddings.
    store._ensure_embeddings()

    # 4. Save the legacy index format for existing consumers.
    index_data = {
        "chunks": [
            {
                "chunk_id": chunk.chunk_id,
                "doc_id": chunk.doc_id,
                "title": chunk.metadata.get("title", ""),
                "version": chunk.metadata.get("version", ""),
                "date": chunk.metadata.get("date", ""),
                "owner": chunk.metadata.get("owner", ""),
                "content": chunk.content,
                "metadata": chunk.metadata,
            }
            for chunk in chunks
        ],
        "embeddings": [chunk.embedding for chunk in chunks],
    }

    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(
        json.dumps(index_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\nDa luu index tai: {INDEX_PATH}")
    print("Build index thanh cong!")


if __name__ == "__main__":
    main()
