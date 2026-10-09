# Nhiệm vụ SV3 — Tầng (c) Hành động + Verify

## 1. Phạm vi trách nhiệm

Bạn chịu trách nhiệm phần phân biệt "agent" với "pipeline đọc-rồi-in": tool có side effect thật (ghi dữ liệu) và bước verify ngay sau đó để chứng minh thay đổi là có thật — đây là tầng dễ mất điểm nhất nếu chỉ làm cho có, vì giám khảo sẽ đọc trace thật để kiểm tra, không chỉ nghe mô tả.

**File bạn sở hữu:**

| File | Vai trò |
|---|---|
| `src/domain/appeals_store.py` | Ghi/đọc hồ sơ khiếu nại — side effect thật |
| `src/agent/logger.py` | Ghi `logs/*.jsonl` — bằng chứng mọi bước agent chạy |

**File bạn góp phần:**
- `src/mcp_server/server.py` — bạn viết đúng 2 tool: `submit_appeal` (ghi), `get_appeal_status` (đọc — verify)
- `data/appeals.jsonl` — file dữ liệu sinh ra khi chạy thật, phải có ít nhất vài record mẫu trong repo lúc nộp

**Vì sao `logger.py` thuộc tầng của bạn chứ không phải của SV1 (dù nó được gọi từ `agent/loop.py`):** bản chất của "verify" trong đề bài không chỉ là `get_appeal_status` — nó là nguyên tắc "mọi hành động phải để lại bằng chứng đọc lại được". `logs/*.jsonl` chính là bằng chứng cấp hệ thống cho toàn bộ agent, cùng logic với `get_appeal_status` là bằng chứng cấp 1 tool. Gộp 2 thứ này vào tay 1 người giữ nguyên tắc nhất quán.

---

## 2. Nhiệm vụ chi tiết từng file

### 2.1 `src/domain/appeals_store.py`

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
    Tạo appeal_id DUY NHẤT (gợi ý: uuid4, không dùng số đếm tăng dần —
    số đếm có thể trùng nếu 2 tiến trình ghi gần như đồng thời).
    Append 1 dòng JSON vào data/appeals.jsonl (KHÔNG đọc hết file rồi
    ghi đè lại toàn bộ — chỉ append, để không mất dữ liệu cũ nếu crash
    giữa chừng).
    Trả về text có appeal_id rõ ràng, ví dụ:
    "Đã tạo khiếu nại #<appeal_id>, trạng thái: pending"
    """


def get_appeal_status(appeal_id: str) -> str:
    """
    ĐỌC TRỰC TIẾP TỪ FILE data/appeals.jsonl (không đọc từ biến nhớ tạm
    trong RAM) — đây là điểm mấu chốt để verify là thật: nếu restart
    chương trình, get_appeal_status vẫn phải đọc lại được record cũ.
    Nếu appeal_id không tồn tại: trả "Error: không tìm thấy hồ sơ khiếu
    nại #<appeal_id>", không raise exception.
    """


def list_appeals(student_id: str) -> str:
    """(Tuỳ chọn) Liệt kê tất cả khiếu nại của 1 sinh viên — dùng khi
    agent cần xác nhận lại danh sách thay vì chỉ 1 appeal_id cụ thể."""
```

- **Lý do đọc trực tiếp từ file, không cache trong RAM:** nếu `get_appeal_status` chỉ đọc từ 1 dict Python giữ trong bộ nhớ của cùng tiến trình, verify sẽ "ăn gian" — chứng minh được gì cũng chỉ là agent tự nói chuyện với chính nó. Đọc từ file là bằng chứng độc lập với process đang chạy.
- Dùng module `json` chuẩn, mỗi dòng trong `appeals.jsonl` là 1 object JSON hoàn chỉnh (JSONL, không phải 1 mảng JSON lớn) — để append không cần parse lại toàn file.

### 2.2 `src/agent/logger.py`

```python
def log_step(
    run_id: str,
    question_id: str,
    step_index: int,
    step_type: str,  # "llm_call" | "tool_call" | "tool_result" | "final_answer" | "error"
    tool_name: str | None,
    args: dict | None,
    result: str | None,
    usage: dict | None,  # CHỈ điền khi step_type == "llm_call":
    # {"calls": 1, "prompt_tokens": int, "completion_tokens": int}
    # None ở mọi step_type khác
) -> None:
    """Append 1 dòng JSON vào logs/run_<run_id>.jsonl, tự sinh thêm field "timestamp"
    (ISO 8601, UTC). Gọi bởi agent/loop.py (của SV1) ở MỌI lần gọi LLM (step_type=
    "llm_call") và mọi tool_call/tool_result/final_answer/error. Format 5 step_type
    này đã chốt trong interface-contract.md — đổi field name ở đây phải báo SV2 vì
    evaluate.py đọc trực tiếp."""
```

- **Thống nhất tên field với SV2 TRƯỚC KHI viết `evaluate.py`** — `evaluate.py` đọc trực tiếp các field này để tính tổng usage/câu, đổi tên field giữa chừng sẽ làm hỏng cả 2 phía.
- Mỗi lần `make demo` chạy xong 1 phiên, phải có 1 file `logs/run_<timestamp>.jsonl` mới — đủ 3 lần chạy thật là 3 file riêng biệt, không ghi đè lên nhau.
- Log phải đủ chi tiết để nhìn vào là biết: câu hỏi nào, bước nào, gọi tool gì với tham số gì, kết quả gì, tốn bao nhiêu token — đây chính là nội dung dán vào report mục 4 (trace thật) và mục 6 (chi phí token/câu).

---

## 3. Luồng side-effect + verify — phải xuất hiện đúng như sau trong mọi trace có khiếu nại

```
[Bước N]   tool_call: submit_appeal(student_id="SV001", reason="...", disputed_criteria="...")
[Bước N]   tool_result: "Đã tạo khiếu nại #a1b2c3, trạng thái: pending"
[Bước N+1] tool_call: get_appeal_status(appeal_id="a1b2c3")
[Bước N+1] tool_result: "Khiếu nại #a1b2c3 — SV001 — pending — nộp lúc 2026-10-07T..."
[Bước N+2] final_answer: "Đã ghi nhận khiếu nại của bạn (#a1b2c3)..."
```

- Nếu bước N+1 (`get_appeal_status`) **không xuất hiện** trong bất kỳ trace nào có `submit_appeal` — đây là lỗi nghiêm trọng nhất bạn có thể mắc, vì đúng là điểm giám khảo sẽ tìm trước tiên (yêu cầu 2.7 ghi rõ "bắt buộc có bước verify").
- Luật "sau submit_appeal phải gọi get_appeal_status" nằm trong `prompts/system_agent.txt` (SV1 viết, bạn cần đọc kỹ để xác nhận đúng ý tool của mình), **không** hard-code if/else buộc gọi trong code — vì đây là agent tự quyết định theo prompt, không phải pipeline cứng.

---

## 4. Interface — bạn cần thống nhất với SV1, SV2

**Bạn expose cho người khác:**
- Signature và format trả về chính xác của `submit_appeal`/`get_appeal_status` (bao gồm format `appeal_id`) — SV1 cần để viết đúng hướng dẫn trong `system_agent.txt`.
- Format field trong `logs/*.jsonl` — SV2 cần để `evaluate.py` parse đúng.

**Bạn cần nhận từ người khác:**
- Từ SV1: signature `run_agent()` trong `agent/loop.py` gọi `logger.log_step()` ở những điểm nào trong vòng lặp (đầu bước, sau tool_call, sau tool_result) — để bạn biết `log_step()` cần nhận tham số gì ở mỗi lần gọi.

---

## 5. Checklist tự kiểm tra trước khi tích hợp

- [ ] `submit_appeal` tạo `appeal_id` không trùng qua nhiều lần gọi liên tiếp
- [ ] `get_appeal_status` đọc đúng record vừa tạo — test bằng cách: gọi `submit_appeal`, **tắt và chạy lại chương trình**, gọi `get_appeal_status` với id vừa tạo, vẫn đọc được
- [ ] `get_appeal_status` với id không tồn tại trả `"Error: ..."`, không raise exception làm crash server
- [ ] `data/appeals.jsonl` là JSONL hợp lệ — mỗi dòng `json.loads()` được độc lập
- [ ] Chạy thử 1 câu hỏi khiếu nại qua agent thật, xác nhận trace in ra đủ cặp `submit_appeal` → `get_appeal_status` như mục 3
- [ ] `logs/run_*.jsonl` sinh đúng 1 file mới mỗi lần `make demo` chạy xong, không ghi đè file cũ
- [ ] `grep -n "@dataclass\|TypedDict" src/domain/appeals_store.py` ra kết quả
- [ ] Mỗi dòng `step_type == "llm_call"` có `usage` đủ 3 field; mọi `step_type` khác có `usage: null`

---

## 6. Câu hỏi vấn đáp bạn phải trả lời được

- **"Làm sao chứng minh tool đã thực sự thay đổi dữ liệu?"** → `get_appeal_status` đọc trực tiếp từ file `appeals.jsonl` trên đĩa, không đọc từ biến nhớ tạm — nên nếu khởi động lại chương trình, dữ liệu vẫn còn, chứng minh thay đổi là bền vững chứ không phải chỉ tồn tại trong phiên chạy hiện tại.
- **"Nếu tôi sửa dòng sinh `appeal_id` từ uuid4 sang số đếm tăng dần thì hệ thống thay đổi gì?"** → Số đếm tăng dần cần đọc lại file để biết số tiếp theo, có rủi ro trùng nếu ghi đồng thời (dù project này chạy đơn luồng nên rủi ro thấp, nhưng vẫn là điểm yếu thiết kế cần nêu); uuid4 tránh hoàn toàn rủi ro này nhưng id dài khó đọc hơn khi debug — đây là đánh đổi cần giải thích được.
- **"Tại sao không cho agent tự quyết định có cần verify hay không?"** → Vì side effect (ghi dữ liệu khiếu nại) là hành động không thể thu hồi dễ dàng, luật "luôn verify sau khi ghi" đặt cứng trong system prompt để đảm bảo mọi lần ghi đều có bằng chứng đọc lại, không phụ thuộc vào việc model "nhớ" phải làm vậy.
- **"Nếu `get_appeal_status` bị gọi trước khi `submit_appeal` chạy xong (race condition) thì sao?"** → Trong thiết kế hiện tại, agent loop chạy tuần tự (1 tool tại 1 thời điểm), nên không có race condition thật; nếu mở rộng sang chạy song song nhiều agent, cần thêm cơ chế khoá file hoặc chuyển sang ghi có giao dịch (transaction) — nên nêu đây là hạn chế trong report mục 7.