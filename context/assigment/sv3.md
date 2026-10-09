# Nhiệm vụ SV3 — MCP (W7): Server + Client + Hành động/Verify

## 1. Phạm vi trách nhiệm

Bạn chịu trách nhiệm **toàn bộ giao thức MCP từ 2 đầu**: phía server (công bố tool, type hint → schema, stdio, stdout sạch) và phía client (kết nối, discover tool động, gọi tool). Đây là lý do bạn không chỉ viết `server.py` mà còn `mcp_client.py` — hiểu MCP đầy đủ nghĩa là hiểu cả 2 phía nói chuyện với nhau thế nào, không phải chỉ 1 nửa. Bạn cũng sở hữu tool **ghi** duy nhất của hệ thống (`submit_appeal`) và tool đọc để verify nó (`get_appeal_status`) — phần phân biệt "agent" với "pipeline đọc-rồi-in" của cả đề bài.

**File bạn sở hữu:**

| File | Vai trò |
|---|---|
| `src/agent/mcp_client.py` | Client MCP — connect, discover, call tool |
| `src/mcp_server/server.py` | Server MCP — khai báo & chạy cả 5 tool |
| `src/domain/appeals_store.py` | Ghi/đọc hồ sơ khiếu nại — side effect thật |

**Bạn KHÔNG tự viết logic RAG hay tính điểm** — `server.py` chỉ **import** hàm từ `rag/store.py`, `rag/hybrid_search.py`, `domain/scoring.py` (của SV1) rồi bọc thành tool. Bạn cũng không viết `agent/loop.py` (SV2) — `loop.py` gọi vào `mcp_client.py` của bạn, bạn không tự quyết định khi nào gọi tool nào, chỉ cung cấp cơ chế để gọi.

---

## 2. Nhiệm vụ chi tiết từng file

### 2.1 `src/agent/mcp_client.py`

```python
async def connect() -> ClientSession:
    """Spawn mcp_server/server.py bằng sys.executable + đường dẫn TUYỆT ĐỐI.
    Dùng python trần hoặc đường dẫn tương đối sẽ lỗi 'Connection closed' lúc
    initialize."""


async def discover(session) -> list[Tool]:
    """Gọi list_tools(). KHÔNG hard-code danh sách tool ở bất kỳ đâu trong
    file này — client phải nhận danh sách tool động từ server."""


async def call(session, tool_name: str, args: dict) -> str:
    """Gọi call_tool(). Trả về nội dung text, không raise ra ngoài — lỗi đã
    được server format thành chuỗi "Error: ..." sẵn (do bạn viết trong
    server.py)."""
```

- In ra terminal dòng `Discovered N tools: [...]` ngay sau `discover()` — bằng chứng bắt buộc dán vào report mục 5.
- Tuyệt đối không có biến/dict nào tên kiểu `TOOL_REGISTRY` trong file này — sẽ bị `grep` khi chấm. Đây chính là điểm chứng minh "client discover tool động", không hard-code.
- Đây là file SV2 sẽ `import` trực tiếp vào `agent/loop.py` — giữ 3 hàm trên ổn định signature, báo SV2 nếu đổi.

### 2.2 `src/mcp_server/server.py`

File lớn nhất bạn sở hữu — khai báo và chạy **cả 5 tool**, mỗi tool chỉ là lớp bọc mỏng gọi vào hàm nội bộ của SV1:

```python
@mcp.tool()
def search_regulations(query: str, top_k: int = 3) -> str:
    """Gọi rag.hybrid_search.search(query, top_k) (của SV1), format kết quả
    thành text: mỗi đoạn "[<doc_id>] <title> (phiên bản <version>, <date>)\\n
    <nội dung>", nối nhau bằng "\\n---\\n". Không tìm được đoạn nào đủ liên
    quan → trả đúng chuỗi cố định: "Không tìm thấy nội dung liên quan trong
    tài liệu." (khớp với prompts/grounding_rag.txt của SV1 — SV2 dùng chuỗi
    này để kiểm tỉ lệ từ chối đúng trong evaluate.py)."""


@mcp.tool()
def get_document(doc_id: str) -> str:
    """Trả nguyên nội dung document (không chunk). doc_id không tồn tại →
    "Error: không tìm thấy tài liệu <doc_id>"."""


@mcp.tool()
def calculate_conduct_score(category_scores: dict, confirmed: bool = True) -> str:
    """Gọi domain.scoring.calculate_score() (của SV1). Thành công → format
    "Tổng điểm: <total>/100\\nXếp loại: <classification>\\nChi tiết:\\n-
    <category>: <score>...". Thiếu dữ liệu → nguyên văn chuỗi lỗi mà
    scoring.calculate_score() trả về (đã có sẵn "Error: ...")."""


@mcp.tool()
def submit_appeal(student_id: str, reason: str, disputed_criteria: str) -> str:
    """Gọi domain.appeals_store.submit_appeal() (file của chính bạn)."""


@mcp.tool()
def get_appeal_status(appeal_id: str) -> str:
    """Gọi domain.appeals_store.get_appeal_status() (file của chính bạn)."""
```

- **Load `VectorStore` MỘT LẦN ở module level** (không rebuild index mỗi lần gọi tool) — lỗi kinh điển gây timeout.
- Chạy qua **stdio** (phù hợp vì corpus cục bộ, 1 người dùng).
- **Tuyệt đối không `print()` trong bất kỳ tool nào** — mọi log đi qua `stderr`/logging facility, vì `stdout` thuộc về giao thức JSON-RPC. In nhầm ra `stdout` sẽ làm hỏng cả kết nối, không chỉ 1 tool.
- Type hint đầy đủ trên mọi tham số tool (`category_scores: dict`, `confirmed: bool`...) — đây chính là yêu cầu 2.3 (Typing W1) áp dụng vào MCP: schema JSON mà `list_tools()` trả về được sinh tự động từ type hint này.
- Mọi tool, khi lỗi, **luôn** trả chuỗi bắt đầu `"Error: "`, không raise exception ra ngoài `call_tool` — áp dụng cho cả 5 tool.

### 2.3 `src/domain/appeals_store.py`

```python
@dataclass
class Appeal:
    appeal_id: str
    student_id: str
    reason: str
    disputed_criteria: str
    status: str  # "pending" | "resolved" | "rejected"
    timestamp: str  # ISO format


def submit_appeal(student_id: str, reason: str, disputed_criteria: str) -> str:
    """
    Tạo appeal_id DUY NHẤT (gợi ý: uuid4, không dùng số đếm tăng dần — số
    đếm có thể trùng nếu 2 tiến trình ghi gần như đồng thời).
    Append 1 dòng JSON vào data/appeals.jsonl (KHÔNG đọc hết file rồi ghi
    đè lại toàn bộ — chỉ append, để không mất dữ liệu cũ nếu crash giữa
    chừng).
    Trả về text có appeal_id rõ ràng, ví dụ:
    "Đã tạo khiếu nại #<appeal_id>, trạng thái: pending"
    """


def get_appeal_status(appeal_id: str) -> str:
    """
    ĐỌC TRỰC TIẾP TỪ FILE data/appeals.jsonl (không đọc từ biến nhớ tạm
    trong RAM) — điểm mấu chốt để verify là thật: nếu restart chương
    trình, get_appeal_status vẫn phải đọc lại được record cũ.
    Nếu appeal_id không tồn tại: trả "Error: không tìm thấy hồ sơ khiếu
    nại #<appeal_id>", không raise exception.
    """


def list_appeals(student_id: str) -> str:
    """(Tuỳ chọn) Liệt kê tất cả khiếu nại của 1 sinh viên."""
```

- **Lý do đọc trực tiếp từ file, không cache trong RAM:** nếu `get_appeal_status` chỉ đọc từ 1 dict Python giữ trong bộ nhớ của cùng tiến trình, verify sẽ "ăn gian" — chứng minh được gì cũng chỉ là server tự nói chuyện với chính nó. Đọc từ file là bằng chứng độc lập với process đang chạy.
- JSONL — mỗi dòng 1 object JSON hoàn chỉnh, không phải 1 mảng lớn — để append không cần parse lại toàn file.

---

## 3. Luồng side-effect + verify — phải xuất hiện đúng như sau trong mọi trace có khiếu nại

```
[Bước N]   tool_call: submit_appeal(student_id="SV001", reason="...", disputed_criteria="...")
[Bước N]   tool_result: "Đã tạo khiếu nại #a1b2c3, trạng thái: pending"
[Bước N+1] tool_call: get_appeal_status(appeal_id="a1b2c3")
[Bước N+1] tool_result: "Khiếu nại #a1b2c3 — SV001 — pending — nộp lúc 2026-10-07T..."
[Bước N+2] final_answer: "Đã ghi nhận khiếu nại của bạn (#a1b2c3)..."
```

- Nếu bước N+1 **không xuất hiện** trong bất kỳ trace nào có `submit_appeal` — lỗi nghiêm trọng nhất bạn có thể mắc, vì đúng là điểm giám khảo sẽ tìm trước tiên (yêu cầu 2.7).
- Luật "sau submit_appeal phải gọi get_appeal_status" nằm trong `prompts/system_agent.txt` (SV2 viết) — bạn cần đọc kỹ để xác nhận đúng ý 2 tool của mình khớp với mô tả SV2 viết, **không** hard-code if/else buộc gọi trong code của bạn.

---

## 4. Interface — bạn cần thống nhất với SV1, SV2

**Bạn expose cho người khác:**
- Signature + docstring của `mcp_client.discover()`/`mcp_client.call()` — SV2 import trực tiếp vào `agent/loop.py`.
- Tên 5 tool chính xác + format lỗi `"Error: ..."` của từng tool — SV2 cần để viết `prompts/system_agent.txt` khớp đúng.
- Signature + format trả về của `submit_appeal`/`get_appeal_status` (bao gồm format `appeal_id`) — SV2 cần để model biết cách dùng `appeal_id` ở bước verify.

**Bạn cần nhận từ người khác:**
- Từ SV1: signature + docstring chính xác của `store.search()`, `hybrid_search.search()`, `scoring.calculate_score()`, `scoring.normalize_category()` — bạn import thẳng vào `server.py`.
- Từ SV1: nội dung `prompts/grounding_rag.txt` (chuỗi fallback "không tìm thấy") — phải dùng đúng y hệt trong tool `search_regulations`.

---

## 5. Checklist tự kiểm tra trước khi tích hợp

- [ ] `discover()` in đúng dòng `Discovered N tools: [...]`, không có `TOOL_REGISTRY` hard-code nào trong `mcp_client.py`
- [ ] Spawn server bằng `sys.executable` + đường dẫn tuyệt đối — test chạy từ thư mục khác vẫn connect được
- [ ] Cả 5 tool có type hint đầy đủ trên tham số
- [ ] Không có `print()` nào trong `server.py` — chỉ dùng logging ra stderr
- [ ] `VectorStore` load đúng 1 lần lúc server khởi động, không rebuild mỗi lần gọi tool
- [ ] `submit_appeal` tạo `appeal_id` không trùng qua nhiều lần gọi liên tiếp
- [ ] `get_appeal_status` đọc đúng record vừa tạo — test bằng cách: gọi `submit_appeal`, **tắt và chạy lại server**, gọi `get_appeal_status` với id vừa tạo, vẫn đọc được
- [ ] `get_appeal_status` với id không tồn tại trả `"Error: ..."`, không raise exception làm crash server
- [ ] `data/appeals.jsonl` là JSONL hợp lệ — mỗi dòng `json.loads()` được độc lập
- [ ] Chạy thử 1 câu hỏi khiếu nại qua agent thật (nhờ SV2), xác nhận trace in ra đủ cặp ghi→verify như mục 3
- [ ] `grep -n "@dataclass" src/domain/appeals_store.py` ra kết quả

---

## 6. Câu hỏi vấn đáp bạn phải trả lời được

- **"Vì sao chạy qua stdio mà không phải HTTP?"** → Corpus cục bộ, chỉ 1 người dùng, server và client chạy cùng máy trong cùng phiên — stdio đơn giản hơn, không cần quản lý cổng/mạng, phù hợp đúng kịch bản "client spawn server làm subprocess".
- **"Client discover tool động nghĩa là gì, sao không hard-code danh sách tool cho nhanh?"** → `discover()` gọi `list_tools()` lấy schema trực tiếp từ server lúc runtime — nếu server thêm/bớt/đổi tool, client tự nhận biết mà không cần sửa code. Hard-code sẽ gãy ngay khi server đổi mà client không hay biết.
- **"Làm sao chứng minh tool đã thực sự thay đổi dữ liệu?"** → `get_appeal_status` đọc trực tiếp từ file `appeals.jsonl` trên đĩa, không đọc từ biến nhớ tạm — nên nếu khởi động lại server, dữ liệu vẫn còn, chứng minh thay đổi là bền vững chứ không phải chỉ tồn tại trong phiên chạy hiện tại.
- **"Nếu tôi sửa dòng sinh `appeal_id` từ uuid4 sang số đếm tăng dần thì hệ thống thay đổi gì?"** → Số đếm tăng dần cần đọc lại file để biết số tiếp theo, có rủi ro trùng nếu ghi đồng thời; uuid4 tránh rủi ro này nhưng id dài khó đọc hơn khi debug — đánh đổi cần giải thích được.
- **"Vì sao `calculate_conduct_score` không tự ý đoán điểm khi thiếu dữ liệu?"** → Tool chỉ là lớp bọc gọi `scoring.calculate_score()` của SV1 — bản thân hàm đó đã thiết kế trả lỗi rõ ràng thay vì đoán; tool của bạn chỉ việc trả nguyên văn lỗi đó ra, không thêm logic che giấu.