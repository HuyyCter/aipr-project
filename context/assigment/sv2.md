# Nhiệm vụ SV2 — Agent Loop / ReAct (W6) + Evaluation

## 1. Phạm vi trách nhiệm

Bạn chịu trách nhiệm "bộ não điều phối": vòng lặp nhận câu hỏi, hỏi LLM, quyết định gọi tool hay trả lời thẳng, nhận kết quả rồi lặp lại tới khi xong. Đây là nơi mọi quyết định "gọi tool nào, khi nào dừng" xảy ra — không có file này thì RAG (SV1) và MCP (SV3) chỉ là các hàm/tool rời rạc, không ai gọi chúng theo đúng trình tự cả. Bạn cũng là người duy nhất đo lường toàn hệ thống (`make eval`), vì eval chạy xuyên qua chính vòng lặp bạn viết.

**File bạn sở hữu:**

| File | Vai trò |
|---|---|
| `src/agent/loop.py` | Agent Loop — vòng lặp chính (ReAct / tool-calling) |
| `src/agent/logger.py` | Ghi `logs/*.jsonl` — mọi bước agent chạy |
| `src/eval/evaluate.py` | Chạy `make eval` — faithfulness, tỉ lệ từ chối đúng, chi phí token |
| `src/common/llm_client.py` | Gọi LLM — chat completion + embeddings, retry/timeout |
| `tests/testset.jsonl` | Bộ câu hỏi kiểm thử |
| `prompts/system_agent.txt` | System prompt cho agent |

**Bạn KHÔNG viết `mcp_server/server.py` hay `agent/mcp_client.py`** (SV3 sở hữu cả 2) — `loop.py` của bạn **gọi vào** `mcp_client.discover()`/`mcp_client.call()` của SV3, không tự nói chuyện với MCP server.

---

## 2. Nhiệm vụ chi tiết từng file

### 2.1 `src/agent/loop.py`

```python
def run_agent(
    question: str, mcp_session, history: list[dict], max_steps: int = 6
) -> str:
    """
    Vòng lặp Week 6: message → LLM (kèm tool schema từ mcp_client.discover()) →
    nếu có tool_call thì gọi qua mcp_client.call() (của SV3) → đưa Observation
    lại → lặp. Dừng khi: (1) model trả lời cuối cùng không kèm tool_call, hoặc
    (2) đạt max_steps.
    """
```

- **Parse an toàn:** bọc `json.loads(tool_call.arguments)` trong try/except. Nếu lỗi (thiếu ngoặc, JSON hỏng): không raise, ghi vào Observation chuỗi `"Error: không parse được tham số tool"` và tiếp tục vòng lặp bình thường.
- **MAX_STEPS:** nếu đạt giới hạn mà vẫn chưa có câu trả lời cuối, trả về thông báo rõ ràng kiểu `"Đã vượt quá số bước xử lý cho phép."`, không im lặng treo.
- Mỗi bước gọi `logger.log_step()` (file của chính bạn) để ghi vào `logs/run_<timestamp>.jsonl` — xem format chuẩn ở mục 2.2.
- **Luật bắt buộc nằm trong `prompts/system_agent.txt`, không hard-code trong code:** sau khi gọi `submit_appeal` phải gọi lại `get_appeal_status` ngay bước tiếp theo.
- Mọi lời gọi LLM trong vòng lặp đi qua `common/llm_client.py` (file của chính bạn), không gọi thẳng SDK API ở đây.

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
    (ISO 8601, UTC). Gọi bởi agent/loop.py (của chính bạn) ở MỌI lần gọi LLM
    (step_type="llm_call") và mọi tool_call/tool_result/final_answer/error."""
```

- Thống nhất tên field với chính mình trước khi viết `evaluate.py` (cùng người, nhưng vẫn phải nhất quán format — `evaluate.py` đọc trực tiếp các field này).
- Mỗi lần `make demo` chạy xong 1 phiên, phải có 1 file `logs/run_<timestamp>.jsonl` mới — đủ 3 lần chạy thật là 3 file riêng biệt, không ghi đè lên nhau.
- Log phải đủ chi tiết để nhìn vào là biết: câu hỏi nào, bước nào, gọi tool gì với tham số gì, kết quả gì, tốn bao nhiêu token — dán vào report mục 4 (trace thật) và mục 6 (chi phí token/câu).

### 2.3 `src/common/llm_client.py`

```python
class LLMClient:
    def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        temperature: float = 0.0,
    ) -> Response:
        """Retry + timeout cho lỗi tạm thời (rate limit, mất kết nối); KHÔNG
        retry khi sai key (lỗi xác thực). Log lỗi HTTP ra stderr (không ra
        stdout — stdout dành cho giao thức MCP nếu client/server cùng tiến
        trình đâu đó)."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Dùng bởi SV1 trong store.embed_all() — thống nhất signature với
        SV1 trước khi code."""
```

- Đây là điểm gọi API **duy nhất** trong toàn hệ thống — SV1 (`embed_all`) và chính bạn (`loop.py`, `evaluate.py` LLM-as-judge) đều gọi qua đây, không ai tự gọi SDK trực tiếp.
- Prompt (system prompt, grounding prompt) đọc từ file `.txt`, không hard-code trong `.py` (yêu cầu 2.4).

### 2.4 `src/eval/evaluate.py`

```python
def run_eval(testset_path: str, out_csv: str) -> None:
    """
    Đọc tests/testset.jsonl. Với MỖI câu:
      1. Chạy qua agent THẬT (agent.loop.run_agent) — không mock.
      2. Nếu type != "no_answer": chấm faithfulness (LLM-as-judge: tách câu
         trả lời thành claim, hỏi mỗi claim có được context retrieved hỗ
         trợ không).
      3. Nếu type == "no_answer": kiểm câu trả lời có khớp pattern từ chối
         chuẩn hay không — tính tỉ lệ từ chối đúng trên nhóm này.
      4. Đọc logs/run_<timestamp>.jsonl tương ứng, cộng usage (số lần gọi
         LLM, prompt_tokens, completion_tokens) cho câu đó.
    Xuất CSV: question_id, type, faithfulness, refused_correctly,
    num_llm_calls, prompt_tokens, completion_tokens, total_cost_estimate.
    In bảng tổng kết (trung bình từng cột) ra terminal.
    """
```

- **Không gọi trực tiếp `rag/store.py` hay `domain/scoring.py`** — luôn đi qua agent thật (qua `mcp_client`/`loop.py`), vì mục đích là đo hệ thống thật, không phải đo từng module rời.
- LLM-as-judge dùng `common/llm_client.py` với prompt riêng (`prompts/judge.txt`, khuyến khích tách khỏi code cho nhất quán với yêu cầu 2.4).
- **Chạy thêm 1 lượt so sánh dense-only vs hybrid** (nhờ SV1 expose `mode` nội bộ trong `hybrid_search.search()`) trên cùng testset — điểm cộng "So sánh thêm 1 cấu hình".
- Vẽ biểu đồ bằng `matplotlib` — ví dụ cột faithfulness theo từng loại câu hỏi — phục vụ điểm cộng "Đồ thị + CSV log chi tiết".

### 2.5 `tests/testset.jsonl`

Mỗi dòng tối thiểu:
```json
{"id": "q01", "question": "...", "type": "direct", "expected_doc_ids": ["DOC0001"]}
```

- `type` ∈ `{direct, synthesis, calc, action, no_answer}`.
- ≥12 câu, ≥4 câu `type == "no_answer"`.
- Với câu `type == "calc"`: ≥1 câu cố ý thiếu dữ liệu 1 mục, test đúng nhánh lỗi của `scoring.py` (SV1) chạy xuyên suốt qua agent thật.
- Bạn chủ trì soạn + tổng hợp từ câu cả nhóm góp, đảm bảo đủ cơ cấu như bảng mục 7 README.

### 2.6 `prompts/system_agent.txt`

- Mô tả vai trò agent, liệt kê khi nào nên gọi tool nào (câu hỏi quy định → `search_regulations`; câu hỏi tính điểm → `search_regulations` rồi `calculate_conduct_score`; yêu cầu khiếu nại → `submit_appeal` rồi **bắt buộc** `get_appeal_status`), và luật từ chối khi không tìm thấy.
- Tên tool phải khớp đúng 100% với tên SV3 khai báo trong `mcp_server/server.py` — xác nhận với SV3 trước khi chốt file này.

---

## 3. Interface — bạn cần thống nhất với SV1, SV3

**Bạn expose cho người khác:**
- Format field trong `logs/*.jsonl` (5 `step_type`, field usage) — không ai khác cần đọc trực tiếp trừ chính `evaluate.py` của bạn, nhưng SV3 nên biết để hiểu trace lúc debug chung.
- `common/llm_client.py` — SV1 gọi `embed()` trong `store.embed_all()`.

**Bạn cần nhận từ người khác:**
- Từ SV3: signature `mcp_client.discover(session) -> list[Tool]` và `mcp_client.call(session, tool_name, args) -> str` — `loop.py` gọi trực tiếp 2 hàm này, cần đúng signature trước khi code.
- Từ SV3: danh sách tên tool chính xác (`search_regulations`, `get_document`, `calculate_conduct_score`, `submit_appeal`, `get_appeal_status`) và format lỗi `"Error: ..."` của từng tool — để viết đúng `system_agent.txt` và để `evaluate.py` nhận diện đúng khi tool thất bại.
- Từ SV1: format fallback trong `grounding_rag.txt` (chuỗi "không tìm thấy" chính xác) — để `evaluate.py` kiểm tỉ lệ từ chối đúng bằng string match, không cần LLM-as-judge cho phần này.

---

## 4. Checklist tự kiểm tra trước khi tích hợp

- [ ] Giả lập model trả JSON lỗi (thiếu ngoặc) → loop không crash, log ghi `"Error: ..."`
- [ ] Giả lập model gọi tool liên tục không dừng → `MAX_STEPS` chặn đúng lúc
- [ ] Mỗi dòng `step_type == "llm_call"` có `usage` đủ 3 field; mọi `step_type` khác có `usage: null`
- [ ] `logs/run_*.jsonl` sinh đúng 1 file mới mỗi lần `make demo` chạy xong, không ghi đè file cũ
- [ ] `make eval` chạy hết `testset.jsonl` không crash, xuất CSV đủ cột
- [ ] Phát hiện đúng ≥4 câu `no_answer` là từ chối đúng (không bị tính nhầm là sai)
- [ ] Có bảng/biểu đồ so sánh dense vs hybrid
- [x] `llm_client.chat()` retry đúng khi rate-limit, KHÔNG retry khi sai key (đã kiểm thử và chạy OK)
- [ ] `grep -rn "TOOL_REGISTRY" src/agent/` không ra kết quả registry hard-code nào

---

## 5. Câu hỏi vấn đáp bạn phải trả lời được

- **"Tại sao Agent biết phải gọi tool này?"** → Vì `mcp_client.discover()` (của SV3) trả về schema (tên, mô tả, tham số) do server khai báo qua type hint, cộng với `system_agent.txt` mô tả ngữ cảnh khi nào dùng tool nào — model chọn tool dựa trên 2 nguồn đó, không có logic if/else nào trong `loop.py` quyết định thay model.
- **"Nếu tôi đổi `MAX_STEPS` từ 6 xuống 2 thì sao?"** → Các câu hỏi cần nhiều bước (search rồi tính điểm rồi khiếu nại) có thể bị cắt giữa chừng, trả thông báo "vượt quá số bước" dù lẽ ra trả lời được — đánh đổi giữa an toàn (chặn lặp vô hạn) và khả năng hoàn thành tác vụ phức tạp.
- **"Faithfulness đo cái gì, không đo cái gì?"** → Đo mức độ câu trả lời bám vào context đã retrieve được, không đo câu trả lời có đúng theo quy chế thật áp dụng ngoài đời hay không (nếu corpus lỗi thời, faithfulness vẫn có thể cao dù sai thực tế).
- **"Tỉ lệ từ chối đúng tính thế nào, và vì sao cần tách riêng khỏi faithfulness?"** → Câu `no_answer` không có context để chấm faithfulness (không có gì để "bám vào"), nên phải đo riêng bằng cách kiểm câu trả lời có đúng pattern từ chối hay không — gộp chung 2 metric sẽ làm sai lệch cả hai.
- **"Vì sao `loop.py` không tự gọi MCP server trực tiếp mà phải qua `mcp_client.py` của SV3?"** → Tách lớp: `loop.py` chỉ cần biết "có 1 danh sách tool, gọi tool X với args Y, nhận text Z" — không cần biết gì về stdio, giao thức JSON-RPC hay cách spawn subprocess. Nếu sau này đổi transport (stdio → HTTP), chỉ `mcp_client.py` phải sửa, `loop.py` không đổi gì.