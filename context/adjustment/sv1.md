# Yêu cầu SV1 chỉnh sửa `rag/` để tích hợp với MCP server

Từ: SV3 (MCP server) · Gửi: SV1 (RAG)

Khi tích hợp `server.py` với `rag/`, SV3 phát hiện **2 vấn đề** ở phía RAG. Cả hai đều ảnh hưởng trực tiếp đến điểm nhóm (Chất lượng RAG 13đ, Đánh giá 10đ, MCP 8đ).

---

## Vấn đề 1: Thiếu hàm "load + search" để server chỉ cần gọi

### Hiện trạng

Theo `sv3.md`, `server.py` chỉ **import hàm của SV1 rồi bọc thành tool** (`store.search()`, `hybrid_search.search(query, top_k)`). Thực tế `rag/` hiện có:

| File | Có | Thiếu |
|---|---|---|
| `build_index.py` | `read_document()`, `main()` (ghi `data/index/index.json`) | Không có hàm nào để **đọc index lại** |
| `store.py` | `DocumentStore` (add/get/list/count) | Không có `search()`, không nạp được từ `index.json`, không giữ embeddings |
| `hybrid_search.py` | `hybrid_search(query, chunks, embeddings, bm25_index, ...)` trả `list[(vị trí, điểm)]` | Không có `search(query, top_k)` như contract. Caller phải tự giữ chunks, embeddings, BM25 rồi tự map vị trí → chunk |

Hậu quả: SV3 phải tự viết trong `server.py` các hàm `_load_store()`, `_load_index()`, dựng BM25, map `CHUNKS[i]`. Đó là logic RAG nằm sai chỗ, và SV3 không phải người sở hữu nó.

### Cần SV1 bổ sung (không đổi hàm hiện có)

Một điểm vào duy nhất trong `rag/`, server chỉ gọi 2 thứ:

```python
# rag/store.py hoặc hybrid_search.py
def load_store() -> DocumentStore:
    """Đọc SOURCE_FILES -> DocumentStore đầy đủ (get(doc_id) dùng được)."""


class HybridRetriever:
    def __init__(self, index_path=...):
        """Đọc index.json 1 lần: chunks + embeddings, dựng BM25 1 lần."""

    def search(self, query: str, top_k: int = 3) -> list[tuple[DocumentChunk, float]]:
        """Trả (chunk, điểm), đã sắp giảm dần. Rỗng nếu không đủ liên quan."""
```

Server sau đó chỉ còn:

```python
STORE = load_store()
RETRIEVER = HybridRetriever()
...
hits = RETRIEVER.search(query, top_k)
```

Yêu cầu kèm theo:
- Khởi tạo **một lần** (server load ở module level). Không rebuild BM25 hay đọc lại file mỗi lần search.
- Nếu chưa có `index.json`: raise `FileNotFoundError` có thông báo "chạy build_index.py trước".
- Không `print()` ở bất kỳ hàm nào mà server import. stdout thuộc về giao thức MCP. Dùng `logging` hoặc `sys.stderr`.
- Báo lại SV3 tên hàm/class và signature cuối cùng để server import đúng.

---

## Vấn đề 2: Câu hỏi ngoài phạm vi vẫn trả chunk (không có `no_answer`)

### Hiện trạng

`hybrid_search()` luôn trả đủ `top_k` kết quả. Nguyên nhân gốc là bước chuẩn hóa:

```python
def normalise_scores(scores):
    ...
    return [(score - min_score) / (max_score - min_score) for score in scores]
```

Min-max luôn đẩy chunk tốt nhất lên **1.0**, kể cả khi cả corpus chẳng liên quan gì đến câu hỏi. Sau chuẩn hóa không còn thông tin "tốt nhất có đủ tốt không". Vì vậy chuỗi:

```
Không tìm thấy nội dung liên quan trong tài liệu.
```

không bao giờ được trả. Đây là yêu cầu của đề (tầng a, *calibration*) và `evaluate.py` dùng chuỗi này để đo **tỉ lệ từ chối đúng** trên ≥4 câu `no_answer`. Hiện tại metric này gần như chắc chắn = 0%.

Ví dụ thật SV3 đã chạy: query `"học bổng khuyến khích học tập"` vẫn nhận chunk DOC0002 (kỷ luật). Lưu ý: chunk đó có nhắc "học bổng" trong ngữ cảnh kỷ luật, nên câu này chưa phải ca no_answer lý tưởng. Hãy test thêm bằng câu **hoàn toàn ngoài miền** như học phí, lịch thi, ký túc xá, thời tiết.

### Cần SV1 sửa

Chặn **trước khi chuẩn hóa**, dựa trên điểm thô:

```python
vector_scores = [cosine_similiarity(query_vector, v) for v in embeddings]

if max(vector_scores) < MIN_VECTOR_SCORE:  # kiểm tra trên điểm THÔ
    return []

bm25_scores = normalise_scores(bm25_scores)  # chuẩn hóa sau
...
```

`search()` của retriever trả `[]` khi rỗng, server sẽ tự trả đúng câu từ chối.

Cách chọn ngưỡng (đừng đoán số):
1. Chọn ~5 câu **trong** corpus và ~5 câu **ngoài** corpus.
2. In `max(vector_scores)` của từng câu ra stderr.
3. Chọn ngưỡng nằm giữa 2 nhóm. Ghi lại bảng số liệu này, nó thành bằng chứng cho report mục 3 và mục 6.
4. Nếu 2 nhóm chồng lấn, thêm điều kiện phụ: điểm BM25 thô của chunk top = 0 (không trùng từ khóa nào).

### Gợi ý nhỏ (không bắt buộc, nhưng cải thiện chất lượng)

`embed_key()` đang dùng task mặc định `retrieval.passage` cho cả câu hỏi. Jina khuyến nghị `retrieval.query` khi embed câu truy vấn (còn chunk giữ `retrieval.passage`). Cần thêm tham số `task` vào `embed_key` / `jina_embeddings` và truyền `"retrieval.query"` trong `hybrid_search`. Sau khi đổi, **chạy lại phép đo ngưỡng** ở trên vì phân bố điểm sẽ đổi.

---

## Cách kiểm tra khi SV1 sửa xong

```
uv run python src/aipr_project/rag/build_index.py
uv run python test_mcp.py
```

Kỳ vọng:
- `search_regulations("mục chấp hành nội quy tối đa bao nhiêu điểm")` → có đoạn `[DOC0001]...`
- `search_regulations("học phí học kỳ này bao nhiêu")` → đúng chuỗi `Không tìm thấy nội dung liên quan trong tài liệu.`
- `server.py` không còn hàm tự viết `_load_store`, `_load_index`, `build_bm25_index`.

## Tóm tắt

| # | Việc | Ưu tiên |
|---|---|---|
| 1 | Thêm `load_store()` + `HybridRetriever.search(query, top_k)` trong `rag/`, load 1 lần | Cao |
| 2 | Ngưỡng trên điểm cosine **thô** trước khi min-max, trả `[]` khi không đủ liên quan | Cao |
| 3 | Đổi task embedding câu hỏi sang `retrieval.query`, đo lại ngưỡng | Thấp |