
import json
from pathlib import Path

from aipr_project.rag.models import DocumentChunk
from aipr_project.rag.hybrid_search import (
    build_bm25_index,
    hybrid_search,
)


# ============================================================
# 1. CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[4]
INDEX_PATH = PROJECT_ROOT / "data" / "index" / "index.json"

TOP_K = 3

FALLBACK = (
    "I cannot find enough information "
    "in the provided documents."
)


# ============================================================
# 2. RETRIEVAL TEST CASES
# ============================================================

TEST_CASES = [
    {
        "query": "Điểm rèn luyện được đánh giá như thế nào?",
        "expected_docs": {"DOC0001", "DOC0002"},
        "expected_keywords": ["điểm rèn luyện"],
    },
    {
        "query": "Sinh viên được xếp loại rèn luyện theo những mức nào?",
        "expected_docs": {"DOC0001"},
        "expected_keywords": [
            "xuất sắc",
            "tốt",
            "khá",
            "trung bình",
            "yếu",
            "kém",
        ],
    },
    {
        "query": (
            "Hoạt động công tác xã hội "
            "của sinh viên được quy định ra sao?"
        ),
        "expected_docs": {"DOC0002"},
        "expected_keywords": ["công tác xã hội"],
    },
    {
        "query": "Điểm rèn luyện được tính theo những tiêu chí nào?",
        "expected_docs": {"DOC0001"},
        "expected_keywords": ["điểm rèn luyện"],
    },
    {
        "query": "Sinh viên có thể tham gia hoạt động công tác xã hội nào?",
        "expected_docs": {"DOC0002"},
        "expected_keywords": ["công tác xã hội"],
    },
    {
        "query": "Quy định về điểm rèn luyện của sinh viên là gì?",
        "expected_docs": {"DOC0001", "DOC0002"},
        "expected_keywords": ["điểm rèn luyện"],
    },
]


# ============================================================
# 3. LOAD INDEX
# ============================================================

def load_index():
    print("=" * 65)
    print("TEST RAG - LOAD INDEX")
    print("=" * 65)

    if not INDEX_PATH.exists():
        raise FileNotFoundError(
            f"Không tìm thấy index: {INDEX_PATH}"
        )

    with INDEX_PATH.open("r", encoding="utf-8") as file:
        index_data = json.load(file)

    chunks = [
        DocumentChunk(
            chunk_id=item["chunk_id"],
            doc_id=item["doc_id"],
            content=item["content"],
            chunk_index=item.get("chunk_index", i),
            embedding=index_data["embeddings"][i],
            metadata={
                **item.get("metadata", {}),
                "title": item.get("title", ""),
                "version": item.get("version", ""),
                "date": item.get("date", ""),
                "owner": item.get("owner", ""),
            },
        )
        for i, item in enumerate(index_data["chunks"])
    ]

    embeddings = index_data["embeddings"]   

    if not chunks:
        raise ValueError("Index không có chunks.")

    if len(chunks) != len(embeddings):
        raise ValueError(
            "Số chunks và embeddings không khớp."
        )

    print(f"Index: {INDEX_PATH}")
    print(f"Số chunks: {len(chunks)}")
    print(f"Số embeddings: {len(embeddings)}")

    return chunks, embeddings


# ============================================================
# 4. TEST CITATION AND VERSION
# ============================================================

def test_citations(chunks):
    print("\n" + "=" * 65)
    print("TEST CITATION AND VERSION")
    print("=" * 65)

    passed = 0

    for chunk in chunks:
        valid = all([
            bool(chunk.chunk_id),
            bool(chunk.doc_id),
            bool(chunk.metadata.get("title")),
            bool(chunk.metadata.get("version")),
            bool(chunk.content.strip()),
        ])

        if valid:
            passed += 1
        else:
            print(
                f"[FAIL] Metadata không hợp lệ: "
                f"{chunk.chunk_id}"
            )

    print(
        f"Metadata hợp lệ: {passed}/{len(chunks)} chunks"
    )

    # Kiểm tra chunk_id không bị trùng.
    chunk_ids = [chunk.chunk_id for chunk in chunks]
    unique_ids = set(chunk_ids)

    unique_ok = len(chunk_ids) == len(unique_ids)

    print(
        "Chunk ID duy nhất: "
        f"{'PASS' if unique_ok else 'FAIL'}"
    )

    return passed == len(chunks) and unique_ok


# ============================================================
# 5. TEST RETRIEVAL
# ============================================================

def test_retrieval(chunks, embeddings, bm25_index):
    print("\n" + "=" * 65)
    print("TEST RETRIEVAL")
    print("=" * 65)

    passed = 0

    for case in TEST_CASES:
        query = case["query"]

        results = hybrid_search(
            query=query,
            chunks=chunks,
            embeddings=embeddings,
            bm25_index=bm25_index,
            top_k=TOP_K,
        )

        # Tài liệu xuất hiện trong Top K.
        found_docs = {
            chunks[index].doc_id
            for index, score in results
        }

        # Nội dung thực tế của Top K.
        retrieved_content = "\n".join(
            chunks[index].content
            for index, score in results
        ).casefold()

        expected_docs = case["expected_docs"]

        # Kiểm tra có ít nhất một tài liệu mong đợi.
        document_ok = bool(found_docs & expected_docs)

        # Kiểm tra có ít nhất một từ khóa mong đợi.
        keyword_ok = any(
            keyword.casefold() in retrieved_content
            for keyword in case["expected_keywords"]
        )

        # Lưu ý: đây là kiểm tra sơ bộ, chưa chứng minh
        # đoạn trích đã trả lời đầy đủ câu hỏi.
        ok = document_ok and keyword_ok

        if ok:
            passed += 1

        print(f"\nCâu hỏi: {query}")
        print(f"Tài liệu mong đợi: {sorted(expected_docs)}")
        print(f"Tài liệu tìm được: {sorted(found_docs)}")
        print(f"Kiểm tra tài liệu: {'PASS' if document_ok else 'FAIL'}")
        print(f"Kiểm tra từ khóa: {'PASS' if keyword_ok else 'FAIL'}")
        print(f"Kết quả: {'PASS' if ok else 'FAIL'}")

        for rank, (index, score) in enumerate(results, start=1):
            chunk = chunks[index]

            print(
                f"  [{rank}] {chunk.chunk_id} | "
                f"{chunk.metadata.get('title', '')} | "
                f"Version: {chunk.metadata.get('version', '')} | "
                f"Score: {score:.4f}"
            )

    print(f"\nRetrieval: {passed}/{len(TEST_CASES)} câu đạt")

    return passed == len(TEST_CASES)


# ============================================================
# 6. TEST OUT-OF-SCOPE RETRIEVAL
# ============================================================

def test_out_of_scope(chunks, embeddings, bm25_index):
    print("\n" + "=" * 65)
    print("TEST OUT-OF-SCOPE QUESTION")
    print("=" * 65)

    query = "Thời tiết ngày mai ở Hà Nội như thế nào?"

    results = hybrid_search(
        query=query,
        chunks=chunks,
        embeddings=embeddings,
        bm25_index=bm25_index,
        top_k=TOP_K,
    )

    print(f"Câu hỏi: {query}")
    print(
        "Lưu ý: Hybrid search vẫn có thể trả về Top K "
        "dù tài liệu không chứa câu trả lời."
    )

    for rank, (index, score) in enumerate(results, start=1):
        chunk = chunks[index]

        print(f"\n[{rank}] Score: {score:.4f}")
        print(f"Tài liệu: {chunk.metadata.get('title', '')}")
        print(f"Chunk ID: {chunk.chunk_id}")
        print(f"Nội dung: {chunk.content[:200]}")

    print(
        "\nFallback chưa được xác nhận ở đây; "
        "cần kiểm tra qua Agent/Generation."
    )

    return True


# ============================================================
# 7. MAIN
# ============================================================

def main():
    chunks, embeddings = load_index()

    bm25_index = build_bm25_index(chunks)
    print("\nBM25 index: OK")

    citation_ok = test_citations(chunks)

    retrieval_ok = test_retrieval(
        chunks,
        embeddings,
        bm25_index,
    )

    test_out_of_scope(
        chunks,
        embeddings,
        bm25_index,
    )

    print("\n" + "=" * 65)
    print("FINAL SUMMARY")
    print("=" * 65)

    print(f"Citation / metadata: {'PASS' if citation_ok else 'FAIL'}")
    print(f"Retrieval: {'PASS' if retrieval_ok else 'FAIL'}")
    print("Fallback: NOT TESTED - cần tích hợp Agent/Generation")

    if citation_ok and retrieval_ok:
        print("\nRAG CORE TEST PASSED")
    else:
        print("\nRAG CORE TEST FAILED - cần kiểm tra các mục FAIL")


if __name__ == "__main__":
    main()
