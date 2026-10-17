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
- [ ] `agent/loop.py`
- [ ] `agent/logger.py`
- [x] `eval/evaluate.py`
- [x] `common/llm_client.py`
- [x] `tests/testset.jsonl`
- [ ] `prompts/system_agent.txt`
- [x] `prompts/judge.txt`

**Prompt chính đã dùng:**

```text
1. Overview du an, toi thuc hien voi tu cach la sv2, nhung cong viec se lam va pham vi kien thuc, check trong thu muc me aipr
2. Tao giup toi mot file local md de chia giai doan cac viec cua sv2 de theo doi tien do, khi nao nen hoan thanh file, khi nao can merge code voi thanh vien khac. Cap nhat ban da lam len ai-usage.md cua sv2
3. cap nhat them phan nao lien quan den file tai lieu mau nao trong roadmap-sv2
4. toi muon hoi ham embed() trong llm_client, input la mot list toi co nen tach them embed_text va batch_embed_text nhu w3 hay khong. Toi du tinh su dung jina_embedding nhu w3 hay viet lai, trong context co quy dinh ve them file vao khong va co nen lam the khong
5. Giup toi viet ham chat() trong llm_client nhung toi khong muon xai qua nhieu model va viet them 1 ham main/chuong trinh de test. Ghi phan nay vao ai-usage
6. evaluate.py co xay dung theo mo hinh RAGAS khong. Neu khong thi can nhung do luong nhung gi: Faithfulness, answer relevance, context precision,...
7. Tao cho toi khung suon cho evaluate.py va viet prompt cho judge.txt
8. Kiem tra va sua loi KeyError '\n  "claims"' khi format prompt trong evaluate.py (chuyen sang dung chuoi .replace() an toan)
9. Kiem tra file llm_client xem co phan nao du thua/bat hop ly, xoa ham log_api_call, xoa khoi test __main__ va fix logic ngat HTTP 401/403 cua Jina
10. Kiem tra lich su ai tao 10 cau trong testset, vi sao co DOC0003 va DOC0004 trong khi project moi co 2 file
11. Chuan hoa bo 20 cau hoi testset.jsonl (chia 5 type ro rang, bo sung q15 thieu du lieu va chu thich nhom)
12. Dieu chinh lai testset.expected_doc_ids: loai bo DOC0003 va DOC0004 (chi con DOC0001 va DOC0002) de khop voi kho source_docs thuc te
13. Xu ly loi HTTP 413 (Rate limit TPM 8,000 tokens) va crash o cau q08 khi chay evaluate: cai dat context pruning trong loop.py, cat ngan context trong judge_faithfulness, them try-catch per-item va delay hoi token trong evaluate.py
14. Tinh chinh bo testset.jsonl xuong 13 cau chuan (danh so q01-q13 lien tuc, bo sung cau tieng Anh q03, q05, q13, giu day du 5 nhom va 4 cau no_answer)
```

**Đoạn code nào do AI sinh (vs tự viết):**

- AI hỗ trợ phân tích yêu cầu từ các file context, lập kế hoạch chi tiết 4 giai đoạn thực hiện, các mốc merge code, và xây dựng bảng ánh xạ trực tiếp từng đầu việc SV2 với các file tài liệu mẫu trong `context/roadmap-sv2.md`.
- Trong `src/aipr_project/common/llm_client.py`:
  - Tự viết: Kế thừa hàm `_jina_embeddings` và cấu trúc `embed()` từ lab Week 3, tích hợp vào `LLMClient`.
  - AI hỗ trợ: Sinh cấu trúc hàm `chat()` tích hợp model chuẩn `openai/gpt-oss-20b`, xử lý cơ chế retry exponential backoff và phân loại lỗi HTTP (ngắt khi 401/403/404, retry khi 429/5xx). Sau đó AI hỗ trợ refactor dọn dẹp code thừa: xóa `log_api_call`, xóa khối test `__main__` và chỉnh sửa bắt lỗi 401/403 của Jina để ngắt ngay lập tức không retry.
- Trong `prompts/judge.txt`:
  - AI sinh toàn bộ nội dung prompt cho mô hình LLM-as-a-judge (tách câu trả lời thành atomic claims, đối chiếu ngữ cảnh truy hồi, xuất định dạng JSON chấm điểm Faithfulness).
- Trong `src/aipr_project/eval/evaluate.py`:
  - AI sinh toàn bộ khung sườn và hoàn thiện code chạy đánh giá hệ thống Agentic RAG qua testset thật (kết nối MCP Server thật qua stdio, trích xuất retrieved context và token usage từ trace logs, gọi LLM judge chấm Faithfulness, đo Refusal Rate cho câu `no_answer`, đo Retrieval Hit Rate, xuất báo cáo CSV và in Rich Table). Bổ sung cơ chế cắt ngắn context trong `judge_faithfulness`, bọc `try...except` độc lập cho từng câu và thêm `asyncio.sleep(2.0)` hồi token bucket.
- Trong `src/aipr_project/agent/loop.py`:
  - AI hỗ trợ: Bổ sung hàm `prune_messages()` tự động cắt gọn kết quả `tool_result` cũ khi chuỗi hội thoại dài vượt ngưỡng an toàn, chống tràn TPM 8,000 tokens của Groq; bọc `try...except` quanh `client.chat()` chống sập luồng agent.
- Trong `tests/testset.jsonl`:
  - Tự viết: Đóng góp và mở rộng các câu hỏi tình huống tiếng Việt và tiếng Anh.
  - AI hỗ trợ: Chuẩn hóa bộ 13 câu hỏi đạt chuẩn đặc tả $\ge 12$ câu (đánh số liên tục từ `q01` đến `q13`, phủ đủ 5 nhóm câu hỏi, có 3 câu tiếng Anh `q03`, `q05`, `q13` và 4 câu `no_answer`).

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
