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

## SV2 — Agent Loop (W6) + Evaluation (W5) + LLM Client (W2)

**Công cụ AI đã dùng:** Antigravity (Google Gemini)

**Dùng cho phần nào:**
- [x] Lên kế hoạch lộ trình tiến độ, phân kỳ mốc merge code (`context/roadmap-sv2.md`)
- [ ] `agent/loop.py`
- [ ] `agent/logger.py`
- [ ] `eval/evaluate.py`
- [x] `common/llm_client.py`
- [ ] `tests/testset.jsonl`
- [ ] `prompts/system_agent.txt`

**Prompt chính đã dùng:**
```text
1. Overview du an, toi thuc hien voi tu cach la sv2, nhung cong viec se lam va pham vi kien thuc, check trong thu muc me aipr
2. Tao giup toi mot file local md de chia giai doan cac viec cua sv2 de theo doi tien do, khi nao nen hoan thanh file, khi nao can merge code voi thanh vien khac. Cap nhat ban da lam len ai-usage.md cua sv2
3. cap nhat them phan nao lien quan den file tai lieu mau nao trong roadmap-sv2
4. toi muon hoi ham embed() trong llm_client, input la mot list toi co nen tach them embed_text va batch_embed_text nhu w3 hay khong. Toi du tinh su dung jina_embedding nhu w3 hay viet lai, trong context co quy dinh ve them file vao khong va co nen lam the khong
5. Giup toi viet ham chat() trong llm_client nhung toi khong muon xai qua nhieu model va viet them 1 ham main/chuong trinh de test. Ghi phan nay vao ai-usage
```

**Đoạn code nào do AI sinh (vs tự viết):** 
- AI hỗ trợ phân tích yêu cầu từ các file context, lập kế hoạch chi tiết 4 giai đoạn thực hiện, các mốc merge code, và xây dựng bảng ánh xạ trực tiếp từng đầu việc SV2 với các file tài liệu mẫu trong `context/roadmap-sv2.md`.
- Trong `src/aipr_project/common/llm_client.py`:
  + Tự viết: Kế thừa hàm `_jina_embeddings` và cấu trúc `embed()` từ lab Week 3, tích hợp vào `LLMClient`.
  + AI hỗ trợ: Sinh cấu trúc hàm `chat()` tích hợp model chuẩn `openai/gpt-oss-20b` (kế thừa từ W2/W6), xử lý cơ chế retry exponential backoff và phân loại lỗi HTTP (ngắt khi 401/403/404, retry khi 429/5xx), ghi log lỗi ra `sys.stderr` theo Yêu cầu 2.4, và viết khối `if __name__ == "__main__":` kiểm thử end-to-end cả chat thường, chat tool-calling và embedding.

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