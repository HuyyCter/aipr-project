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
- [ ] Khác: ___

**Prompt chính đã dùng** (dán nguyên văn 1-2 prompt tiêu biểu nhất, không cần toàn bộ lịch sử chat):
```
(điền sau)
```

**Đoạn code nào do AI sinh (vs tự viết):** mô tả ngắn gọn — ví dụ "AI sinh khung vòng lặp agent loop ban đầu, tự sửa lại phần xử lý lỗi parse JSON và thêm MAX_STEPS".

---

## SV2 — Tầng (b) Biến đổi + Evaluation

**Công cụ AI đã dùng:** _____

**Dùng cho phần nào:**
- [ ] `domain/scoring.py`
- [ ] `eval/evaluate.py`
- [ ] `tests/testset.jsonl`
- [ ] Khác: ___

**Prompt chính đã dùng:**
```
(điền sau)
```

**Đoạn code nào do AI sinh (vs tự viết):**

---

## SV3 — Tầng (c) Hành động + Verify

**Công cụ AI đã dùng:** _____

**Dùng cho phần nào:**
- [ ] `domain/appeals_store.py`
- [ ] `agent/logger.py`
- [ ] Khác: ___

**Prompt chính đã dùng:**
```
(điền sau)
```

**Đoạn code nào do AI sinh (vs tự viết):**

---

## Việc chung cả nhóm

**Công cụ AI đã dùng cho:** README.md, project-structure.md, interface-contract.md, phân công nhiệm vụ, report.docx (nếu có hỗ trợ).

**Ghi chú:** các file tài liệu trên được soạn với sự hỗ trợ của AI (Claude) theo đúng yêu cầu đề bài 02-Yeu-cau-Thuc-hien.pdf và 01-De-tai-upload-for-student.pdf; nội dung code (`src/`) do từng thành viên tự viết, có AI hỗ trợ ở mức độ khai báo riêng từng người ở trên.