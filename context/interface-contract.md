# Interface Contract — chốt trước khi code song song

File này là "hợp đồng" giữa 3 module — đổi bất kỳ field/format nào ở đây phải báo cả nhóm, vì cả 3 người đều phụ thuộc vào nó.

---

## 1. Format log — `logs/run_<run_id>.jsonl`

Người ghi: SV3 (`agent/logger.py`), người gọi: SV1 (`agent/loop.py`), người đọc: SV2 (`eval/evaluate.py`).

Mỗi dòng là 1 object JSON độc lập (JSONL — không phải 1 mảng lớn):

```json
{
  "run_id": "20261008-143000",
  "question_id": "q01",
  "step_index": 0,
  "timestamp": "2026-10-08T14:30:05Z",
  "step_type": "llm_call",
  "tool_name": null,
  "args": null,
  "result": null,
  "usage": {"calls": 1, "prompt_tokens": 850, "completion_tokens": 42}
}
```

| Field | Kiểu | Bắt buộc | Ghi chú |
|---|---|---|---|
| `run_id` | str | luôn có | giống nhau cho mọi dòng trong 1 lần chạy `make demo` (ví dụ timestamp lúc khởi động, format `YYYYMMDD-HHMMSS`) |
| `question_id` | str | luôn có | khớp đúng `id` trong `testset.jsonl` khi chạy qua `make eval`; khi chạy demo tương tác tự do thì dùng `"interactive_<n>"` tăng dần |
| `step_index` | int | luôn có | tăng dần từ 0, reset về 0 mỗi `question_id` mới |
| `timestamp` | str (ISO 8601) | luôn có | `datetime.now(timezone.utc).isoformat()` |
| `step_type` | str | luôn có | 1 trong 5 giá trị: `llm_call`, `tool_call`, `tool_result`, `final_answer`, `error` |
| `tool_name` | str \| null | chỉ có ở `tool_call`/`tool_result` | null ở các step_type khác |
| `args` | object \| null | chỉ có ở `tool_call` | tham số gọi tool |
| `result` | str \| null | có ở `tool_result`/`final_answer`/`error` | nội dung text trả về |
| `usage` | object \| null | **chỉ có ở `step_type == "llm_call"`** | `{"calls": 1, "prompt_tokens": int, "completion_tokens": int}` — luôn `calls: 1` vì mỗi dòng ứng với đúng 1 lần gọi LLM |

**Quy tắc tính usage cho 1 câu hỏi (SV2 dùng trong `evaluate.py`):** gộp tất cả dòng có `question_id` trùng và `step_type == "llm_call"`, cộng `calls`/`prompt_tokens`/`completion_tokens`. Không tính usage từ các step khác.

**Ví dụ 1 chuỗi đầy đủ cho 1 câu hỏi khiếu nại** (tham khảo cho SV1 viết `loop.py` và SV3 viết `logger.py`):

```json
{"run_id": "20261008-143000", "question_id": "q09", "step_index": 0, "timestamp": "...", "step_type": "llm_call", "tool_name": null, "args": null, "result": null, "usage": {"calls": 1, "prompt_tokens": 600, "completion_tokens": 30}}
{"run_id": "20261008-143000", "question_id": "q09", "step_index": 1, "timestamp": "...", "step_type": "tool_call", "tool_name": "submit_appeal", "args": {"student_id": "SV001", "reason": "...", "disputed_criteria": "..."}, "result": null, "usage": null}
{"run_id": "20261008-143000", "question_id": "q09", "step_index": 2, "timestamp": "...", "step_type": "tool_result", "tool_name": "submit_appeal", "args": null, "result": "Đã tạo khiếu nại #a1b2c3, trạng thái: pending", "usage": null}
{"run_id": "20261008-143000", "question_id": "q09", "step_index": 3, "timestamp": "...", "step_type": "llm_call", "tool_name": null, "args": null, "result": null, "usage": {"calls": 1, "prompt_tokens": 650, "completion_tokens": 25}}
{"run_id": "20261008-143000", "question_id": "q09", "step_index": 4, "timestamp": "...", "step_type": "tool_call", "tool_name": "get_appeal_status", "args": {"appeal_id": "a1b2c3"}, "result": null, "usage": null}
{"run_id": "20261008-143000", "question_id": "q09", "step_index": 5, "timestamp": "...", "step_type": "tool_result", "tool_name": "get_appeal_status", "args": null, "result": "Khiếu nại #a1b2c3 — SV001 — pending — nộp lúc 2026-10-08T14:30:12Z", "usage": null}
{"run_id": "20261008-143000", "question_id": "q09", "step_index": 6, "timestamp": "...", "step_type": "final_answer", "tool_name": null, "args": null, "result": "Đã ghi nhận khiếu nại của bạn (#a1b2c3)...", "usage": null}
```

Nếu có lỗi (parse JSON hỏng, tool trả lỗi): dùng `step_type: "error"`, `result` chứa thông điệp lỗi, `tool_name` giữ nguyên tên tool nếu có.

---

## 2. Format text trả về của từng tool MCP

Mọi tool, khi lỗi, **luôn** trả chuỗi bắt đầu bằng `"Error: "` (không raise exception ra ngoài `call_tool`) — đây là yêu cầu 2.6, áp dụng cho cả 5 tool dưới đây.

### `search_regulations(query: str, top_k: int = 3) -> str`
Nhiều đoạn, cách nhau `"\n---\n"`, mỗi đoạn có format:
```
[<doc_id>] <title> (phiên bản <version>, <date>)
<nội dung chunk>
```
Không tìm được đoạn nào đủ liên quan → trả về đúng chuỗi cố định (dùng cho `evaluate.py` kiểm tỉ lệ từ chối đúng):
```
Không tìm thấy nội dung liên quan trong tài liệu.
```

### `get_document(doc_id: str) -> str`
Trả nguyên nội dung document (không chunk), cùng header 1 dòng như trên. Nếu `doc_id` không tồn tại: `"Error: không tìm thấy tài liệu <doc_id>"`.

### `calculate_conduct_score(category_scores: dict, rubric_doc_id: str) -> str`
Thành công:
```
Tổng điểm: <total>/100
Xếp loại: <classification>
Chi tiết:
- <category_1>: <score_1>
- <category_2>: <score_2>
```
Thiếu dữ liệu: `"Error: thiếu dữ liệu mục '<tên mục>' — không thể tính điểm"`.

### `submit_appeal(student_id: str, reason: str, disputed_criteria: str) -> str`
Thành công: `"Đã tạo khiếu nại #<appeal_id>, trạng thái: pending"`.

### `get_appeal_status(appeal_id: str) -> str`
Thành công: `"Khiếu nại #<appeal_id> — <student_id> — <status> — nộp lúc <timestamp>"`.
Không tồn tại: `"Error: không tìm thấy hồ sơ khiếu nại #<appeal_id>"`.

---

## 3. Testset — field chuẩn (xem mẫu thật ở `tests/testset.jsonl`)

```json
{"id": "q01", "question": "...", "type": "direct", "expected_doc_ids": ["DOC0001"]}
```

`type` ∈ `{"direct", "synthesis", "calc", "action", "no_answer"}`. Với `type == "no_answer"`, `expected_doc_ids` luôn là `[]`.

---

## 4. Khi muốn đổi field/format ở đây

Báo trong nhóm chat trước, không tự đổi âm thầm — vì cả 3 file (`loop.py`, `logger.py`, `evaluate.py`, và tất cả tool trong `server.py`) đều đọc đúng những gì được định nghĩa ở file này.