# Nhiệm vụ SV2 — Tầng (b) Biến đổi + Evaluation

## 1. Phạm vi trách nhiệm

Bạn chịu trách nhiệm phần "có việc để đo" của đề bài: tính điểm rèn luyện từ dữ liệu thô (không copy nguyên văn tài liệu được), và toàn bộ hệ thống đánh giá (W5) — đây là module duy nhất tạo ra con số thật để chứng minh hệ thống hoạt động đúng, nên bạn cần hiểu sơ qua cả 3 tầng, không chỉ phần mình viết.

**File bạn sở hữu:**

| File | Vai trò |
|---|---|
| `src/domain/scoring.py` | Tính điểm rèn luyện, đối chiếu khung xếp loại |
| `src/eval/evaluate.py` | Chạy `make eval` — đo faithfulness, tỉ lệ từ chối đúng, chi phí token |

**File bạn góp phần:**
- `src/mcp_server/server.py` — bạn viết đúng 1 tool: `calculate_conduct_score`
- `tests/testset.jsonl` — bạn chủ trì soạn (cả nhóm góp câu hỏi, bạn tổng hợp vì hiểu rõ nhất cách đo)

---

## 2. Nhiệm vụ chi tiết từng file

### 2.1 `src/domain/scoring.py`

```python
@dataclass
class ScoreResult:
    total: int
    classification: str
    breakdown: dict[str, int]
    missing_categories: list[str] = field(default_factory=list)


def calculate_score(category_scores: dict[str, int], rubric: dict) -> ScoreResult | str:
    """
    Cộng tổng điểm các mục, đối chiếu khung xếp loại LẤY TỪ `rubric`
    (do agent trích từ quy chế qua search_regulations, không hard-code
    ngưỡng xếp loại trong code — quy chế đổi thì không phải sửa code).
    Nếu thiếu dữ liệu 1 mục trong category_scores, trả về chuỗi
    "Error: thiếu dữ liệu mục '<tên mục>' — không thể tính điểm"
    thay vì tự suy đoán hoặc bỏ qua mục đó.
    """
```

- **Nguyên tắc quan trọng nhất:** đây là hàm thuần (pure function) — không tự gọi LLM, không tự search tài liệu. Mọi `category_scores` và `rubric` đều do agent (qua tool `search_regulations`/`get_document`) chuẩn bị sẵn rồi truyền vào. Việc tách bạch này giúp bạn test `scoring.py` độc lập, không phụ thuộc SV1 chạy xong trước.
- **Khung xếp loại không hard-code số** (ví dụ không viết thẳng `if total >= 90: return "Xuất sắc"` với số liệu đóng cứng) — `rubric` phải chứa cả ngưỡng xếp loại, đọc từ đó. Đây là điểm hay bị hỏi vấn đáp nhất của tầng (b).
- Viết test riêng với ít nhất 3 case: (1) đủ dữ liệu tính bình thường, (2) thiếu 1 mục → trả lỗi đúng chuẩn, (3) tổng điểm nằm đúng biên giữa 2 mức xếp loại (test off-by-one).

### 2.2 `src/eval/evaluate.py`

```python
def run_eval(testset_path: str, out_csv: str) -> None:
    """
    Đọc tests/testset.jsonl. Với MỖI câu:
      1. Chạy qua agent THẬT (agent.loop.run_agent) — không mock.
      2. Nếu type != "no_answer": chấm faithfulness (LLM-as-judge:
         tách câu trả lời thành claim, hỏi mỗi claim có được context
         retrieved hỗ trợ không).
      3. Nếu type == "no_answer": kiểm câu trả lời có khớp pattern từ
         chối chuẩn hay không — tính tỉ lệ từ chối đúng trên nhóm này.
      4. Đọc logs/run_<timestamp>.jsonl tương ứng, cộng usage
         (số lần gọi LLM, prompt_tokens, completion_tokens) cho câu đó.
    Xuất CSV: question_id, type, faithfulness, refused_correctly,
    num_llm_calls, prompt_tokens, completion_tokens, total_cost_estimate.
    In bảng tổng kết (trung bình từng cột) ra terminal.
    """
```

- **Không gọi trực tiếp `rag/store.py` hay `domain/scoring.py`** — luôn đi qua agent thật (qua `agent/mcp_client.py`/`agent/loop.py` của SV1), vì mục đích là đo hệ thống thật, không phải đo từng module rời.
- LLM-as-judge: dùng `common/llm_client.py` (W2) gọi lại LLM với prompt riêng (có thể thêm `prompts/judge.txt` nếu muốn tách khỏi code, khuyến khích làm vậy cho nhất quán với yêu cầu 2.4).
- **Chạy thêm 1 lượt so sánh dense-only vs hybrid** (gọi `rag/hybrid_search.py` với `mode="dense"` so với mặc định `"hybrid"`) trên cùng testset — đây là phần điểm cộng "So sánh thêm 1 cấu hình", xuất ra 1 bảng/CSV phụ riêng.
- Vẽ biểu đồ bằng `matplotlib` (đã có trong dependencies) — ví dụ cột faithfulness theo từng loại câu hỏi — phục vụ điểm cộng "Đồ thị + CSV log chi tiết".

### 2.3 `tests/testset.jsonl`

Mỗi dòng tối thiểu:
```json
{"id": "q01", "question": "...", "type": "direct", "expected_doc_ids": ["DOC0001"]}
```

- `type` ∈ `{direct, synthesis, calc, action, no_answer}`.
- ≥12 câu, ≥4 câu `type == "no_answer"`.
- Với câu `type == "calc"`: nên có ít nhất 1 câu cố ý thiếu dữ liệu 1 mục, để test đúng nhánh lỗi của `scoring.py` chạy xuyên suốt qua agent thật.
- Tổng hợp từ cả 3 người (SV1 góp câu direct/synthesis, SV3 góp câu action) nhưng bạn là người review cuối, đảm bảo đủ cơ cấu như bảng mục 7 trong README.

---

## 3. Interface — bạn cần thống nhất với SV1, SV3

**Bạn expose cho người khác:**
- Signature và format lỗi của `calculate_conduct_score` (text trả về, bao gồm cả trường hợp `"Error: ..."`) — SV1 cần đúng format này để viết hướng dẫn gọi tool trong `prompts/system_agent.txt`.

**Bạn cần nhận từ người khác:**
- Từ SV1: format text trả về của `search_regulations`/`get_document` (để biết rubric/category_scores agent trích ra sẽ có hình dạng thế nào trước khi truyền vào `calculate_score`).
- Từ SV3: format chính xác từng dòng trong `logs/run_<timestamp>.jsonl` (tên field cho `tool_name`, `args`, `result`, `usage`) — bạn cần parse đúng field này trong `evaluate.py` để cộng token usage. **Thống nhất format này sớm nhất có thể**, vì cả bạn và SV3 cùng phụ thuộc vào nó.

---

## 4. Checklist tự kiểm tra trước khi tích hợp

- [ ] `calculate_score` trả lỗi rõ ràng khi thiếu dữ liệu, không tự đoán hay bỏ qua mục thiếu
- [ ] Khung xếp loại đọc từ `rubric` truyền vào, không có số ngưỡng hard-code trong `scoring.py`
- [ ] Test riêng biên giới xếp loại (ví dụ đúng 90 điểm) ra đúng mức mong đợi
- [ ] `make eval` chạy hết `testset.jsonl` không crash, xuất CSV đủ cột
- [ ] Phát hiện đúng ≥4 câu `no_answer` là từ chối đúng (không bị tính nhầm là sai)
- [ ] Có bảng/biểu đồ so sánh dense vs hybrid
- [ ] `grep -n "@dataclass\|TypedDict" src/domain/scoring.py` ra kết quả (không dùng dict thô)

---

## 5. Câu hỏi vấn đáp bạn phải trả lời được

- **"Nếu tôi sửa dòng khung xếp loại (hard-code ngưỡng) thì hệ thống thay đổi gì?"** → Nếu hard-code, khi quy chế đổi ngưỡng xếp loại thì code không tự cập nhật, phải sửa 2 chỗ (tài liệu + code) dễ gây lệch nhau — đây chính là lý do thiết kế đọc `rubric` từ document.
- **"Faithfulness đo cái gì, không đo cái gì?"** → Đo mức độ câu trả lời bám vào context đã retrieve được, không đo câu trả lời có đúng theo quy chế thật áp dụng ngoài đời hay không (nếu corpus lỗi thời, faithfulness vẫn có thể cao dù sai thực tế).
- **"Tỉ lệ từ chối đúng tính thế nào, và vì sao cần tách riêng khỏi faithfulness?"** → Câu `no_answer` không có context để chấm faithfulness (không có gì để "bám vào"), nên phải đo riêng bằng cách kiểm câu trả lời có đúng pattern từ chối hay không — gộp chung 2 metric sẽ làm sai lệch cả hai.
- **"Nếu corpus không có đáp án thì sao?"** (áp dụng cho tầng (b) khi thiếu dữ liệu để tính) → Phân biệt 2 loại từ chối: (i) tài liệu không đề cập (lỗi khâu truy vấn, thuộc SV1) và (ii) có tài liệu nhưng thiếu dữ liệu để suy luận/tính toán (lỗi khâu biến đổi, thuộc bạn) — `calculate_score` phải trả đúng loại (ii), không lẫn với (i).