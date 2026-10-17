# AI Usage Declaration — T4: Trợ lý Điểm Rèn Luyện & Khiếu Nại

Khai báo trung thực việc dùng AI/LLM hỗ trợ viết code trong project này. Không khai báo (dù có dùng) → tính B theo quy định của đề bài.

---

## SV1 — Tầng (a) Tra cứu + Agent Loop + MCP Client

**Công cụ AI đã dùng:** _(ví dụ: Claude, ChatGPT, GitHub Copilot...)_

**Dùng cho phần nào:**

- [ ] `rag/models.py`
- [ ] `rag/chunking.py`
- [ ] `rag/store.py`
- [ ] `rag/hybrid_search.py`
- [ ] `agent/mcp_client.py`
- [ ] `agent/loop.py`
- [ ] `prompts/*.txt`
- [ ] Khác: \_\_\_

**Prompt chính đã dùng** (dán nguyên văn 1-2 prompt tiêu biểu nhất, không cần toàn bộ lịch sử chat):

```
(điền sau)
```

**Đoạn code nào do AI sinh (vs tự viết):** mô tả ngắn gọn — ví dụ "AI sinh khung vòng lặp agent loop ban đầu, tự sửa lại phần xử lý lỗi parse JSON và thêm MAX_STEPS".

---

## SV2 — Agent Loop (W6) + Evaluation (W5) + LLM Client (W2)

**Công cụ AI đã dùng:** Antigravity (Google Gemini)

**Dùng cho phần nào:**

- [x] Lên kế hoạch lộ trình tiến độ, phân kỳ mốc merge code (`context/roadmap-sv2.md`)
- [x] `agent/loop.py`
- [ ] `agent/logger.py`
- [x] `eval/evaluate.py`
- [x] `common/llm_client.py`
- [x] `tests/testset.jsonl`
- [ ] `prompts/system_agent.txt`
- [x] `prompts/judge.txt`

**Prompt chính đã dùng:**

```text
1. [Thiết kế & Lộ trình] Phân tích yêu cầu đề tài T4 từ thư mục context, lập kế hoạch chi tiết các mốc tiến độ cho SV2 (LLM client, agent loop, evaluation) và ánh xạ với các bài lab W1-W7.
2. [Đánh giá & Benchmark] Hướng dẫn xây dựng module evaluate.py và thiết kế prompts/judge.txt theo mô hình LLM-as-a-judge chấm Faithfulness, đo Correct Refusal Rate cho câu no_answer và trích xuất chi phí token từ log trace.
3. [Tối ưu Token & Rate Limit] Phân tích lỗi Rate Limit của Groq API (TPM 8,000 vs TPD 200,000 tokens/ngày); hỗ trợ viết hàm prune_messages() trong loop.py để cắt gọn context và tối ưu cơ chế fail-fast trong llm_client.py.
```

**Đoạn code nào do AI sinh (vs tự viết):**

- AI hỗ trợ phân tích yêu cầu từ các file context, lập kế hoạch chi tiết 4 giai đoạn thực hiện, các mốc merge code, và xây dựng bảng ánh xạ trực tiếp từng đầu việc SV2 với các file tài liệu mẫu trong `context/roadmap-sv2.md`.
- Trong `src/aipr_project/common/llm_client.py`:
  - Tự viết: Kế thừa hàm `_jina_embeddings` và cấu trúc `embed()` từ lab Week 3, tích hợp vào `LLMClient`.
  - AI hỗ trợ: Sinh cấu trúc hàm `chat()` tích hợp model chuẩn `openai/gpt-oss-20b`, xử lý cơ chế retry exponential backoff và phân loại lỗi HTTP. Tinh chỉnh nâng cao: phân biệt rõ lỗi Rate Limit ngày (TPD) để ngắt ngay lập tức tránh retry vô ích và chỉ chờ hồi phục đối với lỗi Rate Limit phút (TPM); dọn dẹp code thừa và hoàn thiện cơ chế bắt lỗi Jina 401/403.
- Trong `src/aipr_project/agent/loop.py`:
  - Tự viết: Cài đặt luồng vòng lặp ReAct, kết nối `mcp_client.connect()` / `discover()`, cơ chế ngắt trần `MAX_STEPS = 6` và parse tham số `tool_calls` an toàn.
  - AI hỗ trợ: Bổ sung hàm `prune_messages()` tự động rút gọn các `tool_result` cũ khi chuỗi hội thoại vượt ngưỡng 10,000 ký tự nhằm chống tràn Rate Limit TPM (8,000 tokens) và lỗi HTTP 413 của Groq; bọc `try...except` quanh `client.chat()` chống sập luồng agent.
- Trong `prompts/judge.txt`:
  - AI sinh toàn bộ nội dung prompt cho mô hình LLM-as-a-judge (tách câu trả lời thành atomic claims, đối chiếu ngữ cảnh truy hồi, xuất định dạng JSON chấm điểm Faithfulness).
- Trong `src/aipr_project/eval/evaluate.py`:
  - AI sinh toàn bộ khung sườn và hoàn thiện code chạy đánh giá hệ thống Agentic RAG qua testset thật (kết nối MCP Server thật qua stdio, trích xuất retrieved context và token usage từ trace logs, gọi LLM judge chấm Faithfulness, đo Refusal Rate cho câu `no_answer`, đo Retrieval Hit Rate, xuất báo cáo CSV và in Rich Table).
- Trong `tests/testset.jsonl`:
  - Tự viết: Đóng góp và mở rộng các câu hỏi tình huống tiếng Việt và tiếng Anh.
  - AI hỗ trợ: Bổ sung câu `q15` (thiếu dữ liệu đầu vào), chèn các dòng comment phân nhóm và hỗ trợ `evaluate.py` đọc bỏ qua dòng comment; chuẩn hóa toàn bộ `expected_doc_ids` loại bỏ các mã giả định `DOC0003`, `DOC0004` để chỉ còn `DOC0001` và `DOC0002` khớp chuẩn xác với kho tài liệu thực tế `data/source_docs/`.

---

## SV3 — Tầng (c) Hành động + Verify

**Công cụ AI đã dùng:** **\_**

**Dùng cho phần nào:**

- [ ] `domain/appeals_store.py`
- [ ] `agent/logger.py`
- [ ] Khác: \_\_\_

**Prompt chính đã dùng:**

```
(điền sau)
```

**Đoạn code nào do AI sinh (vs tự viết):**

---

## Việc chung cả nhóm

**Công cụ AI đã dùng cho:** README.md, project-structure.md, interface-contract.md, phân công nhiệm vụ, report.docx (nếu có hỗ trợ).

**Ghi chú:** các file tài liệu trên được soạn với sự hỗ trợ của AI (Claude) theo đúng yêu cầu đề bài 02-Yeu-cau-Thuc-hien.pdf và 01-De-tai-upload-for-student.pdf; nội dung code (`src/`) do từng thành viên tự viết, có AI hỗ trợ ở mức độ khai báo riêng từng người ở trên.
