# Nhiệm vụ SV1 — RAG Pipeline (W3–W4)

## 1. Phạm vi trách nhiệm

Bạn chịu trách nhiệm toàn bộ "bộ não tra cứu + biến đổi": từ việc chia nhỏ tài liệu, biến thành vector, tìm kiếm (dense + hybrid), cho đến việc dùng kết quả tìm được để tính điểm rèn luyện. Đây là lớp **nội bộ** (internal API) — không tự công bố ra ngoài qua MCP, mà để SV3 import và bọc thành tool. Bạn không cần biết gì về giao thức MCP hay cách agent loop hoạt động; chỉ cần hàm của bạn đúng, dễ gọi, dễ test độc lập.

**File bạn sở hữu:**

| File | Vai trò |
|---|---|
| `src/rag/models.py` | Data model `Document`, `DocumentChunk` |
| `src/rag/chunking.py` | Chia nhỏ tài liệu theo Điều/Mục, xử lý front-matter |
| `src/rag/store.py` | VectorStore — dense search, cache |
| `src/rag/hybrid_search.py` | Hybrid search (BM25 + dense) |
| `src/domain/scoring.py` | Tính điểm rèn luyện, đối chiếu khung xếp loại |
| `src/common/json_codec.py` | Encoder JSON cho `@dataclass`/`datetime` |
| `prompts/grounding_rag.txt` | Grounding prompt cho câu trả lời có nguồn |

**Bạn dẫn dắt (cả nhóm góp):** `data/source_docs/` — corpus quy chế, vì bạn cần hiểu rõ nhất cấu trúc tài liệu để test chunking/retrieval.

**Bạn KHÔNG viết `mcp_server/server.py`** — SV3 import trực tiếp các hàm của bạn (`store.search()`, `hybrid_search.search()`, `scoring.calculate_score()`) rồi bọc thành tool. Bạn chỉ cần đảm bảo signature + docstring rõ ràng để SV3 gọi đúng.

---

## 2. Nhiệm vụ chi tiết từng file

### 2.1 `src/rag/models.py`

```python
@dataclass
class Document:
    doc_id: str
    title: str
    content: str
    version: str  # ví dụ "2024-v1", "2021-v1"
    date: str  # ISO format hoặc năm, ví dụ "2021"
    owner: str  # ví dụ "Phòng Tuyển sinh và Công tác Sinh viên"
    metadata: dict = field(default_factory=dict)


@dataclass
class DocumentChunk:
    chunk_id: str
    doc_id: str
    content: str
    chunk_index: int
    embedding: Optional[list[float]] = None
    metadata: dict = field(
        default_factory=dict
    )  # kế thừa title/version/date/owner từ Document gốc
```

- Phải dùng `@dataclass` với type hint đầy đủ — điểm bị kiểm bằng `grep "@dataclass"`.
- `metadata` của `DocumentChunk` **phải** copy `version`, `date`, `doc_id`, `owner` từ `Document` gốc — cơ sở để lọc theo metadata sau này (ví dụ ưu tiên văn bản gốc khi hỏi điều khoản pháp lý cụ thể).

### 2.2 `src/rag/chunking.py`

```python
def chunk_document(
    doc_source: str, max_chars: int = 800, overlap: int = 100
) -> Document:
    """
    Bước 1: tách front-matter YAML (giữa 2 dòng `---`) ở đầu file nguồn,
    parse thành doc_id/title/version/date/owner.
    Bước 2: chia phần nội dung còn lại theo ranh giới "Điều X" / "Mục X"
    (regex) — vì quy chế rèn luyện cấu trúc theo điều khoản, cắt cứng theo
    số ký tự sẽ tách rời 1 tiêu chí điểm khỏi phần diễn giải của nó, làm
    sai lệch cả retrieval lẫn scoring. Nếu tài liệu không có cấu trúc
    Điều/Mục rõ, fallback về fixed-size chunking với overlap.
    """
```

- Viết đúng docstring 3-5 dòng như trên — dùng trực tiếp cho report mục 3, không được bỏ.
- Regex gợi ý: `r"(?:^|\n)(Điều\s+\d+|Mục\s+\d+)"` để tìm điểm cắt.
- **Bắt buộc xử lý front-matter trước khi chunk:** 2 file nguồn (`quy_dinh_diem_ren_luyen.md`, `so_tay_sinh_vien.md`) đều có sẵn khối `---\n doc_id: ...\n title: ...\n version: ...\n date: ...\n owner: ...\n---` ở đầu — không coi khối này là 1 chunk nội dung.
- Test bắt buộc: chunk 2 file quy chế thật, in ra để xác nhận mỗi chunk chứa trọn 1 điều khoản, không bị cắt giữa chừng.

### 2.3 `src/rag/store.py`

```python
class VectorStore:
    def add_document(self, doc: Document) -> None: ...
    def embed_all(self) -> None:
        """Chỉ embed chunk có embedding is None — tránh gọi API thừa.
        Gọi common/llm_client.embed() (SV2 sở hữu file này — xem mục 3)."""

    def search(self, query: str, top_k: int = 3) -> list[tuple[DocumentChunk, float]]:
        """Dense search — cosine similarity."""

    def save(self, path: str) -> None: ...  # dùng common/json_codec.py
    def load(self, path: str) -> None: ...
```

- `save()/load()` ghi ra `data/store_cache.json` bằng `common/json_codec.py` — chạy `make demo` lần 2 không được gọi lại API embedding nếu cache còn hợp lệ.

### 2.4 `src/rag/hybrid_search.py`

- Dùng `rank_bm25` kết hợp điểm BM25 với điểm cosine similarity của `VectorStore` — có thể cộng có trọng số hoặc reciprocal rank fusion, chọn 1 cách và giải thích được lý do (cho report mục 3).
- Nếu nhóm đã có sẵn file lab `ex2_1_hybrid_search.py` từ Week 4, copy nguyên vào đây rồi chỉ viết phần glue code gọi vào — **không viết lại thuật toán hybrid từ đầu**.
- Signature: `def search(query: str, top_k: int = 3, mode: str = "hybrid") -> list[tuple[DocumentChunk, float]]` — `mode` chỉ dùng nội bộ cho `eval/evaluate.py` (của SV2) so sánh, **không** để SV3 expose `mode` ra tool MCP (model không có cơ sở để tự chọn).

### 2.5 `src/domain/scoring.py`

Đọc `category-mapping.md` trước khi viết file này — bảng ánh xạ 5 khoá chuẩn dùng xuyên suốt `category_scores`/`rubric`/`breakdown`, tránh so khớp nhầm giữa các cách viết khác nhau của cùng 1 mục (Điều 4 vs Phụ lục 1 vs minh chứng SV).

```python
@dataclass
class ScoreResult:
    raw_total: int  # tổng 5 mục trước khi chốt trần — có thể > 100
    total: int  # min(raw_total, 100) theo Điều 4.2 — dùng để xếp loại
    classification: str
    breakdown: dict[str, int]  # key = khoá chuẩn, xem category-mapping.md
    missing_categories: list[str] = field(default_factory=list)
    confirmed_deduction_applied: bool = False


def normalize_category(raw_name: str) -> str:
    """Map tên mục thô (trích từ Điều 4/Điều 5-9/Phụ lục 1/minh chứng SV) về 1 trong
    5 khoá chuẩn — xem bảng đầy đủ trong category-mapping.md. So khớp theo substring,
    không phân biệt hoa/thường, không so khớp chuỗi chính xác."""


def calculate_score(
    category_scores: dict[str, int], rubric: dict, confirmed: bool = True
) -> ScoreResult | str:
    """
    Cộng tổng điểm 5 mục (key đã qua normalize_category), đối chiếu khung xếp loại
    LẤY TỪ `rubric` (SV3 trích từ quy chế qua tool search_regulations, không
    hard-code ngưỡng trong code).

    Nếu thiếu dữ liệu 1 mục: trả "Error: thiếu dữ liệu mục '<tên mục>' — không thể
    tính điểm", không tự suy đoán hay bỏ qua.

    Nếu confirmed=False (SV không xác nhận điểm rèn luyện — Điều 12.3): trừ 10 điểm
    vào raw_total trước khi chốt trần.

    total PHẢI chốt trần ở 100 (min(raw_total, 100)) — 5 mục cộng đúng luật vẫn có
    thể vượt 100 trên thực tế (dữ liệu thật: 27+25+19+30+2 = 103 → chốt 100, Xuất
    sắc). Quy tắc này không file quy định nào viết tường minh thành công thức — chỉ
    phát hiện được khi đối chiếu với bảng điểm thật (Điều 4.2 chỉ nói "khung 100").
    """
```

- **Hàm thuần (pure function)** — không tự gọi LLM, không tự search tài liệu. Mọi `category_scores`/`rubric` do SV3 (qua tool) chuẩn bị sẵn rồi truyền vào — tách bạch để bạn test độc lập, không phụ thuộc SV3 viết server xong trước.
- **Khung xếp loại không hard-code số** — `rubric` phải chứa cả ngưỡng xếp loại, đọc từ đó.
- Test riêng ≥3 case: (1) đủ dữ liệu tính bình thường, (2) thiếu 1 mục → lỗi đúng chuẩn, (3) biên giữa 2 mức xếp loại (off-by-one), (4) dữ liệu thật trong `tmp.md` phải ra đúng `total=100, raw_total=103, "Xuất sắc"`.

### 2.6 `src/common/json_codec.py`

- `CustomEncoder` cho `json.dumps` xử lý `@dataclass` (dùng `dataclasses.asdict`) và `datetime` — dùng bởi `store.py` (`save()/load()`).

### 2.7 `prompts/grounding_rag.txt`

- Chỉ thị: "chỉ trả lời dựa trên context được cung cấp dưới đây, nếu không đủ thông tin phải nói rõ 'không tìm thấy', không được suy diễn từ kiến thức khác". SV3 đọc file này khi viết tool `search_regulations`/`get_document` để biết format fallback khi không tìm thấy context.
- Không hard-code trong code Python — đọc từ file `.txt` lúc runtime (yêu cầu 2.4).

---

## 3. Interface — bạn cần thống nhất với SV2, SV3

**Bạn expose cho người khác:**
- Signature + docstring đầy đủ của `VectorStore.search()`, `hybrid_search.search()`, `scoring.calculate_score()`, `scoring.normalize_category()` — SV3 import trực tiếp các hàm này vào `mcp_server/server.py` để bọc thành tool `search_regulations`, `get_document`, `calculate_conduct_score`.
- Nội dung `prompts/grounding_rag.txt` — SV3 cần biết format fallback ("Không tìm thấy nội dung liên quan trong tài liệu.") để trả đúng chuỗi đó trong tool.

**Bạn cần nhận từ người khác:**
- Từ SV2: `common/llm_client.py` (file SV2 sở hữu) — bạn gọi `llm_client.embed()` trong `store.embed_all()`. Thống nhất sớm signature hàm `embed(texts: list[str]) -> list[list[float]]`.
- Từ SV3: format text đầu ra mà tool `search_regulations` cần (ví dụ có kèm `[doc_id]` ở đầu mỗi đoạn hay không) — vì `search()` của bạn trả `list[tuple[DocumentChunk, float]]` (dữ liệu có cấu trúc), còn SV3 mới là người format thành chuỗi text cuối cùng trả qua MCP.

---

## 4. Checklist tự kiểm tra trước khi tích hợp

- [ ] Chunk 2 file quy chế thật, mỗi chunk chứa trọn 1 điều khoản, front-matter không lẫn vào chunk nội dung
- [ ] Hybrid search trả kết quả khác (và tốt hơn) dense-only cho ít nhất 1 câu test có thuật ngữ/số điều khoản cụ thể
- [ ] `save()/load()` qua `data/store_cache.json` — chạy lần 2 không gọi lại API embedding
- [ ] `normalize_category()` khớp đúng cả 3 cách viết thật (Điều 4, Điều 5-9, Phụ lục 1, minh chứng SV) về cùng 1 khoá — test bằng chính 5 tên trong `tmp.md`
- [ ] Cộng đúng dữ liệu thật (27+25+19+30+2 = 103) ra `total = 100`, `raw_total = 103`, "Xuất sắc"
- [ ] `confirmed=False` trừ đúng 10 điểm vào `raw_total` trước khi chốt trần 100
- [ ] `calculate_score` trả lỗi rõ ràng khi thiếu dữ liệu, không tự đoán
- [ ] `grep -n "@dataclass" src/rag/models.py src/domain/scoring.py` ra kết quả

---

## 5. Câu hỏi vấn đáp bạn phải trả lời được

- **"Nếu tôi sửa `overlap` trong `chunk_document` thì hệ thống thay đổi gì?"** → Tăng overlap giảm rủi ro cắt đứt ý ở ranh giới chunk nhưng tăng số lượng chunk (tăng chi phí embedding + có thể làm loãng kết quả search do nhiều chunk trùng nội dung).
- **"Vì sao chọn hybrid (BM25 + dense) thay vì chỉ dense?"** → Văn bản quy chế có nhiều số điều khoản, thuật ngữ cụ thể ("Điều 10", "Phụ lục 1") mà dense embedding dễ bỏ sót (embedding tối ưu cho nghĩa, không tối ưu cho khớp từ khoá chính xác); BM25 bù lại phần đó.
- **"Vì sao 5 mục cộng lại có thể vượt 100 mà điểm cuối vẫn phải là 100?"** → Mỗi mục có trần "vượt khung" riêng (mục I tối đa 30, mục IV tối đa 38...), cộng dồn lý thuyết của cả 5 trần vượt quá 100, nhưng Điều 4.2 quy định điểm rèn luyện đánh giá theo khung 100 — nên sau khi cộng phải chốt `min(raw_total, 100)`. Phát hiện từ đối chiếu bảng điểm thật (103 → 100), không đọc thấy trực tiếp trong văn bản.
- **"Nếu corpus không có đáp án thì sao?"** → `search()`/`hybrid_search.search()` vẫn trả về bình thường (điểm similarity thấp hoặc rỗng) — việc quyết định "từ chối" nằm ở `grounding_rag.txt` + cách SV3 format khi không có kết quả đủ tốt, không phải logic trong file của bạn.