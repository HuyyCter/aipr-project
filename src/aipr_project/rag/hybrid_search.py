
from rank_bm25 import BM25Okapi

from aipr_project.rag.models import DocumentChunk
from aipr_project.rag.embeddings import (
    embed_key,
    cosine_similiarity,
)


def normalise_scores(scores: list[float]) -> list[float]:
    """Chuẩn hóa điểm về khoảng 0 đến 1."""

    if not scores:
        return []

    min_score = min(scores)
    max_score = max(scores)

    if max_score == min_score:
        return [1.0] * len(scores)

    return [
        (score - min_score) / (max_score - min_score)
        for score in scores
    ]


def build_bm25_index(chunks: list[DocumentChunk]) -> BM25Okapi:
    """Tạo BM25 index từ nội dung các chunks."""

    if not chunks:
        raise ValueError("Không có chunks để tạo BM25 index.")

    tokenized = [
        chunk.content.lower().split()
        for chunk in chunks
    ]

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
    """Kết hợp tìm kiếm BM25 và vector."""

    if not chunks:
        return []

    if len(chunks) != len(embeddings):
        raise ValueError(
            "Số chunks phải bằng số embeddings."
        )

    if top_k <= 0:
        return []

    if w_bm25 < 0 or w_vector < 0:
        raise ValueError("Trọng số không được âm.")

    if w_bm25 + w_vector == 0:
        raise ValueError("Tổng trọng số phải lớn hơn 0.")

    # 1. Tính điểm BM25.
    bm25_scores = list(
        bm25_index.get_scores(query.lower().split())
    )

    # 2. Tạo embedding cho câu hỏi.
    query_vector = embed_key(query)

    # 3. Tính cosine similarity giữa câu hỏi và từng chunk.
    vector_scores = [
        cosine_similiarity(query_vector, vector)
        for vector in embeddings
    ]

    # 4. Chuẩn hóa cả hai nguồn điểm.
    bm25_scores = normalise_scores(bm25_scores)
    vector_scores = normalise_scores(vector_scores)

    # 5. Chuẩn hóa trọng số để tổng bằng 1.
    total_weight = w_bm25 + w_vector
    bm25_weight = w_bm25 / total_weight
    vector_weight = w_vector / total_weight

    # 6. Kết hợp điểm BM25 và vector.
    scores = [
        bm25_weight * bm25 + vector_weight * vector
        for bm25, vector in zip(
            bm25_scores,
            vector_scores,
        )
    ]

    # 7. Trả về danh sách (vị trí chunk, điểm), giảm dần.
    return sorted(
        enumerate(scores),
        key=lambda item: item[1],
        reverse=True,
    )[:top_k]
