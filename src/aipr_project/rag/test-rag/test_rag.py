
from pathlib import Path
import sys

# Cho phep chay file test truc tiep tu thu muc du an.
PROJECT_ROOT = Path(__file__).resolve().parents[4]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from aipr_project.rag.chunking import parse_document
from aipr_project.rag.store import DocumentStore


DOCS_DIR = PROJECT_ROOT / "data" / "source_docs"
CACHE_PATH = PROJECT_ROOT / "data" / "store_cache.json"

SOURCE_FILES = [
    "quy_dinh_diem_ren_luyen.md",
    "so_tay_sinh_vien.md",
]

TOP_K = 3


def build_test_store():
    """Nap tai lieu nguon vao DocumentStore."""
    store = DocumentStore(cache_path=CACHE_PATH)

    for filename in SOURCE_FILES:
        path = DOCS_DIR / filename

        if not path.exists():
            raise FileNotFoundError(f"Khong tim thay tai lieu: {path}")

        content = path.read_text(encoding="utf-8")
        doc = parse_document(content)
        store.add(doc)

        print(f"[OK] Da nap tai lieu: {doc.doc_id} - {doc.title}")

    return store


def test_documents_and_chunks(store):
    """Kiem tra tai lieu, chunks va metadata."""
    print("\n=== TEST 1: DOCUMENTS AND CHUNKS ===")

    counts = store.count()
    chunks = [
        chunk
        for doc in store.list_all()
        for chunk in store.get_chunk_by_doc(doc.doc_id)
    ]

    checks = {
        "Co tai lieu": counts["documents"] > 0,
        "Co chunks": len(chunks) > 0,
        "Chunk ID khong trung": (
            len({chunk.chunk_id for chunk in chunks}) == len(chunks)
        ),
        "Chunk co noi dung": all(
            chunk.content.strip() for chunk in chunks
        ),
        "Chunk co doc_id": all(chunk.doc_id for chunk in chunks),
        "Chunk co title": all(
            chunk.metadata.get("title") for chunk in chunks
        ),
        "Chunk co version": all(
            chunk.metadata.get("version") for chunk in chunks
        ),
    }

    print(f"So tai lieu: {counts['documents']}")
    print(f"So chunks: {len(chunks)}")

    for name, passed in checks.items():
        print(f"[{'PASS' if passed else 'FAIL'}] {name}")

    return all(checks.values())


def test_bm25_search(store):
    """Kiem tra BM25 ma khong can goi embedding API."""
    print("\n=== TEST 2: BM25 SEARCH ===")

    query = "diem ren luyen sinh vien"
    results = store.search(query, top_k=TOP_K, mode="bm25")

    print(f"Query: {query}")
    print(f"So ket qua: {len(results)}")

    for rank, (chunk, score) in enumerate(results, start=1):
        title = chunk.metadata.get("title", "")
        print(
            f"[{rank}] {chunk.chunk_id} | {title} | "
            f"Score: {score:.4f}"
        )
        print(chunk.content[:180].replace("\n", " "))
        print()

    passed = (
        len(results) > 0
        and all(isinstance(score, (int, float)) for _, score in results)
    )

    print(f"[{'PASS' if passed else 'FAIL'}] BM25 search")
    return passed


def test_dense_and_hybrid_search(store):
    """Kiem tra Dense va Hybrid search; can JINA_API_KEY."""
    print("\n=== TEST 3: DENSE AND HYBRID SEARCH ===")

    query = "thoi gian danh gia diem ren luyen sinh vien"

    try:
        for mode in ("dense", "hybrid"):
            print(f"\n--- Mode: {mode} ---")
            results = store.search(query, top_k=TOP_K, mode=mode)

            print(f"So ket qua: {len(results)}")

            for rank, (chunk, score) in enumerate(results, start=1):
                title = chunk.metadata.get("title", "")
                print(
                    f"[{rank}] {chunk.chunk_id} | {title} | "
                    f"Score: {score:.4f}"
                )
                print(chunk.content[:180].replace("\n", " "))

            if not results:
                print(f"[FAIL] {mode}: khong co ket qua")
                return False

        print("\n[PASS] Dense va Hybrid search")
        return True

    except Exception as exc:
        print(f"\n[FAIL] Dense/Hybrid search: {exc}")
        print("Kiem tra JINA_API_KEY, ket noi mang va embedding cache.")
        return False


def test_invalid_inputs(store):
    """Kiem tra cac dau vao khong hop le."""
    print("\n=== TEST 4: INVALID INPUTS ===")

    empty_query_ok = store.search("", mode="bm25") == []
    invalid_mode_ok = False

    try:
        store.search("diem ren luyen", mode="invalid")
    except ValueError:
        invalid_mode_ok = True

    invalid_top_k_ok = store.search(
        "diem ren luyen", top_k=0, mode="bm25"
    ) == []

    checks = {
        "Query rong": empty_query_ok,
        "Mode khong hop le": invalid_mode_ok,
        "top_k bang 0": invalid_top_k_ok,
    }

    for name, passed in checks.items():
        print(f"[{'PASS' if passed else 'FAIL'}] {name}")

    return all(checks.values())


def main():
    print("=" * 60)
    print("RAG RETRIEVAL TEST")
    print("=" * 60)

    try:
        store = build_test_store()
    except Exception as exc:
        print(f"\n[ERROR] Khong the nap tai lieu: {exc}")
        return

    results = {
        "Documents/chunks": test_documents_and_chunks(store),
        "BM25": test_bm25_search(store),
        "Dense/Hybrid": test_dense_and_hybrid_search(store),
        "Invalid inputs": test_invalid_inputs(store),
    }

    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)

    for name, passed in results.items():
        print(f"[{'PASS' if passed else 'FAIL'}] {name}")

    passed_count = sum(results.values())
    print(f"\nTong ket: {passed_count}/{len(results)} nhom test PASS")

    if all(results.values()):
        print("RAG RETRIEVAL TEST PASSED")
    else:
        print("RAG RETRIEVAL TEST CO MUC CAN KIEM TRA")


if __name__ == "__main__":
    main()
