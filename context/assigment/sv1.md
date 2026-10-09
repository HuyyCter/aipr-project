# Nhiệm vụ SV1 — Tầng (a) Tra cứu + Agent Loop + MCP Client

## 1. Phạm vi trách nhiệm

Bạn chịu trách nhiệm toàn bộ đường đi từ câu hỏi của người dùng đến lúc agent quyết định gọi tool nào, và toàn bộ cơ chế tìm kiếm tài liệu (dense + hybrid). Đây là 2 phần nặng kỹ thuật nhất của project (W3/W4 + W6/W7), vì agent loop là nơi mọi quyết định "gọi tool hay không, gọi tool nào" xảy ra.

**File bạn sở hữu (viết + chịu trách nhiệm giải trình):**

| File | Vai trò |
|---|---|
| `src/rag/models.py` | Data model `Document`, `DocumentChunk` |
| `src/rag/chunking.py` | Chia nhỏ tài liệu theo Điều/Mục |
| `src/rag/store.py` | VectorStore — dense search |
| `src/rag/hybrid_search.py` | Hybrid search (BM25 + dense) |
| `src/agent/mcp_client.py` | Client MCP — discover + call tool |
| `src/agent/loop.py` | Agent Loop — vòng lặp chính |
| `prompts/system_agent.txt` | System prompt cho agent |
| `prompts/grounding_rag.txt` | Grounding prompt cho câu trả lời có nguồn |

**File bạn góp phần (chung với SV2, SV3):**
- `src/mcp_server/server.py` — bạn viết đúng 2 tool: `search_regulations`, `get_document`
- `data/source_docs/` — corpus đã chốt còn 2 file: `quy_dinh_diem_ren_luyen.md` (DOC0001) và `so_tay_sinh_vien.md` đã trích lọc 3 mục liên quan (DOC0002). Mỗi file có sẵn front-matter YAML (`doc_id`, `title`, `version`, `date`, `owner`) ở đầu — `chunking.py` phải tách khối này ra trước khi áp regex Điều/Mục, rồi parse thành `Document.metadata`, không coi nó là 1 chunk nội dung. Lưu ý: `version` 2 file khác nhau (2021 vs 2024) KHÔNG phải tình huống quy chế mâu thuẫn thật (số liệu giống nhau) — chỉ là 2 loại nguồn khác nhau (văn bản gốc vs sổ tay tóm tắt), chưa có tài liệu nào đóng vai "bản đã điều chỉnh" để test version-conflict.

---

## 2. Nhiệm vụ chi tiết từng file

### 2.1 `src/rag/models.py`

```python
@dataclass
class Document:
    doc_id: str
    title: str
    content: str
    version: str  # ví dụ "2024-v1", "2026-v2"
    date: str  # ISO format "2026-01-15"
    owner: str  # ví dụ "Phòng Công tác Sinh viên"
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
    )  # kế thừa title/version/date từ Document gốc
```

- Phải dùng `@dataclass` với type hint đầy đủ — đây là điểm bị kiểm bằng `grep "@dataclass"`.
- `metadata` của `DocumentChunk` **phải** copy `version`, `date`, `doc_id` từ `Document` gốc — vì đây là cơ sở để agent phát hiện mâu thuẫn phiên bản (quy chế cũ vs mới) khi search trả về nhiều chunk cùng nội dung nhưng khác `version`.

### 2.2 `src/rag/chunking.py`

```python
def chunk_document(
    doc: Document, max_chars: int = 800, overlap: int = 100
) -> list[DocumentChunk]:
    """
    Chia theo ranh giới "Điều X" / "Mục X" (regex) trước, vì quy chế rèn luyện
    cấu trúc theo điều khoản — cắt cứng theo số ký tự sẽ tách rời 1 tiêu chí
    điểm khỏi phần diễn giải của nó, làm sai lệch cả retrieval lẫn scoring.
    Nếu tài liệu không có cấu trúc Điều/Mục rõ (ví dụ danh sách minh chứng
    hoạt động), fallback về fixed-size chunking với overlap.
    """
```

- Viết đúng docstring 3-5 dòng như trên (hoặc tương đương) — dùng trực tiếp cho report mục 3, không được bỏ.
- Regex gợi ý: `r"(?:^|\n)(Điều\s+\d+|Mục\s+\d+)"` để tìm điểm cắt.
- Test bắt buộc: chunk 1 file quy chế thật, in ra để xác nhận mỗi chunk chứa trọn 1 điều khoản, không bị cắt giữa chừng.
- **Bắt buộc xử lý front-matter trước khi chunk:** mỗi file nguồn bắt đầu bằng khối `---\n...\n---` chứa `doc_id/title/version/date/owner` — parse riêng khối này (ví dụ `yaml.safe_load` hoặc tách thủ công theo dòng `---`), gán vào `Document`, rồi mới chạy regex Điều/Mục trên phần nội dung còn lại.

### 2.3 `src/rag/store.py`

```python
class VectorStore:
    def add_document(self, doc: Document) -> None: ...
    def embed_all(self) -> None:
        """Chỉ embed chunk có embedding is None — tránh gọi API thừa."""

    def search(self, query: str, top_k: int = 3) -> list[tuple[DocumentChunk, float]]:
        """Dense search — cosine similarity."""

    def save(self, path: str) -> None: ...
    def load(self, path: str) -> None: ...
```

- `save()/load()` ghi ra `data/store_cache.json` — chạy `make demo` lần 2 không được gọi lại API embedding nếu cache còn hợp lệ.

### 2.4 `src/rag/hybrid_search.py`

- Dùng `rank_bm25` (đã có trong `pyproject.toml`) kết hợp điểm BM25 với điểm cosine similarity của `VectorStore` — có thể cộng có trọng số hoặc reciprocal rank fusion, chọn 1 cách và giải thích được lý do (cho report mục 3).
- Nếu nhóm đã có sẵn file lab `ex2_1_hybrid_search.py` từ Week 4, copy nguyên vào đây rồi chỉ viết phần glue code gọi vào — **không viết lại thuật toán hybrid từ đầu** (đúng yêu cầu đề bài).
- Signature: `def search(query: str, top_k: int = 3, mode: str = "hybrid") -> list[tuple[DocumentChunk, float]]` — `mode` chỉ dùng nội bộ cho `eval/evaluate.py` so sánh, **không** expose `mode` ra tool MCP (model không có cơ sở để tự chọn).

### 2.5 `src/agent/mcp_client.py`

```python
async def connect() -> ClientSession:
    """Spawn mcp_server/server.py bằng sys.executable + đường dẫn TUYỆT ĐỐI.
    Dùng python trần hoặc đường dẫn tương đối sẽ lỗi 'Connection closed' lúc initialize."""


async def discover(session) -> list[Tool]:
    """Gọi list_tools(). KHÔNG hard-code danh sách tool ở bất kỳ đâu trong file này."""


async def call(session, tool_name: str, args: dict) -> str:
    """Gọi call_tool(). Trả về nội dung text, không raise ra ngoài — lỗi đã được
    server format thành chuỗi "Error: ..." sẵn."""
```

- In ra terminal dòng `Discovered N tools: [...]` ngay sau `discover()` — đây là bằng chứng bắt buộc dán vào report mục 5.
- Tuyệt đối không có biến/dict nào tên kiểu `TOOL_REGISTRY` trong file này — sẽ bị `grep` khi chấm.

### 2.6 `src/agent/loop.py`

```python
def run_agent(question: str, session, history: list[dict], max_steps: int = 6) -> str:
    """
    Vòng lặp Week 6 nguyên bản: message → LLM (kèm tool schema từ discover()) →
    nếu có tool_call thì gọi qua mcp_client.call() → đưa Observation lại → lặp.
    Dừng khi: (1) model trả lời cuối cùng không kèm tool_call, hoặc (2) đạt max_steps.
    """
```

- **Parse an toàn:** bọc `json.loads(tool_call.arguments)` trong try/except. Nếu lỗi (thiếu ngoặc, JSON hỏng): không raise, ghi vào Observation chuỗi `"Error: không parse được tham số tool"` và tiếp tục vòng lặp bình thường.
- **MAX_STEPS:** nếu đạt giới hạn mà vẫn chưa có câu trả lời cuối, trả về thông báo rõ ràng kiểu `"Đã vượt quá số bước xử lý cho phép."`, không im lặng treo.
- Mỗi bước gọi `agent/logger.py` (do nhóm thống nhất format, SV3 sở hữu file này) để ghi vào `logs/run_<timestamp>.jsonl`.
- **Luật bắt buộc nằm trong `prompts/system_agent.txt`, không hard-code trong code:** sau khi gọi `submit_appeal` phải gọi lại `get_appeal_status` ngay bước tiếp theo.

### 2.7 `prompts/system_agent.txt` và `prompts/grounding_rag.txt`

- `system_agent.txt`: mô tả vai trò agent, liệt kê khi nào nên gọi tool nào (ví dụ: câu hỏi quy định → `search_regulations`; câu hỏi tính điểm → `search_regulations` rồi `calculate_conduct_score`; yêu cầu khiếu nại → `submit_appeal` rồi **bắt buộc** `get_appeal_status`), và luật từ chối khi không tìm thấy.
- `grounding_rag.txt`: chỉ thị "chỉ trả lời dựa trên context được cung cấp dưới đây, nếu không đủ thông tin phải nói rõ 'không tìm thấy', không được suy diễn từ kiến thức khác".
- Không hard-code 2 prompt này trong code Python — đọc từ file `.txt` lúc runtime (yêu cầu 2.4).

---

## 3. Interface — bạn cần thống nhất với SV2, SV3

**Bạn expose cho người khác:**
- Format trả về của `search_regulations`/`get_document` qua MCP: text có kèm `[doc_id]` ở đầu mỗi đoạn — SV2 cần biết format này để tool `calculate_conduct_score` nhận đúng rubric đã trích.
- Danh sách tool đã discover (in log) — SV3 cần biết tên tool `submit_appeal`/`get_appeal_status` khớp đúng với những gì bạn viết trong `system_agent.txt`.

**Bạn cần nhận từ người khác:**
- Từ SV2: signature chính xác và format lỗi của `calculate_conduct_score` (để viết đúng hướng dẫn trong `system_agent.txt`).
- Từ SV3: signature chính xác của `submit_appeal`/`get_appeal_status`, format `appeal_id` trả về (để model biết cách dùng `appeal_id` ở bước verify).

---

## 4. Checklist tự kiểm tra trước khi tích hợp

- [ ] `search_regulations` trả đúng đoạn kèm `doc_id` khi hỏi câu trực tiếp
- [ ] Hybrid search trả kết quả khác (và tốt hơn) dense-only cho ít nhất 1 câu test có thuật ngữ/số điều khoản cụ thể
- [ ] Agent in đúng dòng `Discovered N tools: [...]` lúc khởi động
- [ ] Hỏi câu ngoài phạm vi corpus → agent từ chối đúng chuẩn, không bịa
- [ ] Giả lập model trả JSON lỗi (thiếu ngoặc) → loop không crash, log ghi `"Error: ..."`
- [ ] Giả lập model gọi tool liên tục không dừng → `MAX_STEPS` chặn đúng lúc
- [ ] `grep -rn "TOOL_REGISTRY\|@dataclass" src/agent/` không ra kết quả registry hard-code nào

---

## 5. Câu hỏi vấn đáp bạn phải trả lời được

- **"Tại sao Agent biết phải gọi tool này?"** → Vì `list_tools()` trả về schema (tên, mô tả, tham số) do server khai báo qua type hint, cộng với `system_agent.txt` mô tả ngữ cảnh khi nào dùng tool nào — model chọn tool dựa trên 2 nguồn đó, không có logic if/else nào trong code quyết định thay model.
- **"Nếu corpus không có đáp án thì sao?"** → `search_regulations` vẫn được gọi bình thường, trả về điểm similarity thấp hoặc rỗng; grounding prompt buộc model phải nói "không tìm thấy" thay vì dùng kiến thức nền trả lời.
- **"Nếu tôi sửa `overlap` trong `chunk_document` thì hệ thống thay đổi gì?"** → Tăng overlap giảm rủi ro cắt đứt ý ở ranh giới chunk nhưng tăng số lượng chunk (tăng chi phí embedding + có thể làm loãng kết quả search do nhiều chunk trùng nội dung); phải giải thích được đánh đổi này, không chỉ nói "tăng cho an toàn".
- **"Nếu tôi đổi `MAX_STEPS` từ 6 xuống 2 thì sao?"** → Các câu hỏi cần nhiều bước (ví dụ search rồi tính điểm rồi khiếu nại) có thể bị cắt giữa chừng, trả về thông báo "vượt quá số bước" dù lẽ ra trả lời được — đây là đánh đổi giữa an toàn (chặn lặp vô hạn) và khả năng hoàn thành tác vụ phức tạp.