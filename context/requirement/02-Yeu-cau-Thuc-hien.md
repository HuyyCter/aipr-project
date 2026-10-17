## FINAL PROJECT AIPR — YÊU CẦU THỰC HIỆN (W1–W7)

Nhóm: 3 SV · Thời gian: 10 ngày · Nộp: report (Word) + code (repo kèm .git) ·

Bảo vệ: 20 phút/nhóm gồm vấn đáp và sửa code trực tiếp trên code đã nộp.

## 1. Sản phẩm phải nộp

| # | Sản phẩm | Ghi chú |
| --- | --- | --- |
| 1 | report.docx | 8–9 trang |
| 2 | Repo code (zip hoặc link) | kèm thư mục .git để xem lịch sử commit |
| 3 | logs/ | ≥3 lần chạy thật, mỗi lần 1 file jsonl có timestamp, các bước, tool args/kết quả, USAGE từng câu (calls, prompt/completion tokens) |
| 4 | tests/testset.jsonl | ≥12 câu, trong đó ≥4 câu no_answer |
| 5 | ai-usage.md | Khai báo dùng AI ở phần nào |
| 6 | README.md | Lệnh chạy duy nhất để tái lập demo và make eval |

## 2. Yêu cầu kỹ thuật bắt buộc

| # | Yêu cầu | Mức tối thiểu (10 ngày) | GV kiểm tra bằng cách |
| --- | --- | --- | --- |
| 2.1 | Ngôn ngữ & môi trường | Python 3.11+, repo chạy trên máy GV bằng đúng 1 lệnh (make setup && make demo) | Chạy tại buổi bảo vệ |
| 2.2 | Orchestration tự viết | Vòng lặp agent do SV viết tay. Được dùng: mcp SDK, thư viện embedding, rank_bm25, numpy, pandas, python-docx | Đọc code, hỏi vấn đáp |
| 2.3 | Typing (w1) | Tool schema khai báo bằng dataclass/TypedDict có type hint, không dùng dict thô | `grep -n "@dataclass\ |
| 2.4 | Gọi API (w2) | Có retry/timeout, log lỗi HTTP; prompt tách khỏi code (template/.txt) | Đọc call_llm + file prompt |
| 2.5 | RAG (w3–w4) | ≥2 chế độ truy vấn: dense + hybrid BM25 — tái dùng w4/ex2_1_hybrid_search.py. Chunking có lý do (viết 3–5 dòng giải thích) | Chạy make eval |
| 2.6 | Agent loop (w6) | Có MAX_STEPS; tool lỗi trả chuỗi "Error: ..." (không raise); parse action an toàn (thiếu dấu ngoặc không làm chết run) | Đọc code + bài C2/C3 ở buổi bảo vệ |
| 2.7 | Side effect + verify | ≥1 tool thay đổi trạng thái; bắt buộc có bước verify (gọi lại tool đọc để chứng minh thay đổi) | Xem trace |
| 2.8 | MCP server (w7) | Server do SV viết, ≥2 tool (≥1 tool ghi), chạy qua stdio; stdout sạch; client discover động danh sách tool | Chạy + đọc code server |

- Tài liệu có metadata: doc_id, title, date/version, owner.

- Dữ liệu có thể tiếng Việt hoặc tiếng Anh; không dùng dữ liệu của nhóm khác cùng đề tài.

- Được phép tái dùng DOC0001–DOC0006 của lớp và viết thêm 2–3 tài liệu mới.


## 3. Điểm không bắt buộc — nhưng được cộng điểm (tối đa +6)

| Việc làm thêm | Cộng | Hướng dẫn |
| --- | --- | --- |
| Metadata filter dùng thật trong pipeline | +1 | Phối hợp w4 vào w6 |
| So sánh thêm 1 cấu hình (chunking hoặc dense-vs-hybrid) | +1 | make eval đã có sẵn |
| MCP server dùng được từ host thứ hai (client Python thứ hai là đủ) | +1 | Chứng minh interop |
| Đồ thị + CSV log chi tiết theo từng câu | +1 | Giúp phần eval dễ đọc hơn |

## 4. Cấu trúc report Word (theo đúng khung, 8–9 trang)

| # | Mục | Trang | Trang Nội dung phải có |
| --- | --- | --- | --- |
| 1 | Vấn đề, phạm vi, giả định | 0.5–1 | Bài toán, người dùng, và hệ thống KHÔNG làm gì |
| 2 | Kiến trúc tổng thể | 1 | Sơ đồ agent/tool/MCP boundary + luồng xử lý 1 câu hỏi mẫu |
| 3 | Thiết kế RAG | 1.5 | Chunking + lý do, embedding, hybrid, sử dụng truy vấn nào |
| 4 | Thiết kế Agent & tool | 2 | Schema dataclass, mô tả tool viết như prompt, MAX_STEPS, xử lý lỗi, side effect + verify, trace thật 1 câu hỏi |
| 5 | MCP server | 1 | Danh sách tool + contract, transport, stdout, cách client discover |
| 6 | Đánh giá | 1.5 | Testset, cách đo, kết quả (kèm chi phí token từng câu), ≥1 ca thất bại + phân tích |
| 7 | Hạn chế & hướng phát triển | 0.5 | ≥2 hạn chế trung thực (không viết "chưa có thời gian") |
| 8 | Phân công & đóng góp | 0.5 | Ai làm gì + commit hash tương ứng (GV đối chiếu khi vấn đáp) |
| 9 | Phụ lục | — | Prompt gốc, trace dài, ai-usage.md |

## 5. Trọng số điểm (để SV biết ưu tiên)

| Khối | Tiêu chí | Điểm |
| --- | --- | --- |
| A. Nhóm (60) | Phạm vi & tính thực tiễn | 5 |
|   | Chất lượng RAG | 13 |
|   | Agent loop & thiết kế tool | 12 |
|   | Tái lập & kỹ thuật (chạy 1 lệnh, README, không lộ key, git của cả 3 người, đúng checkpoint) | 12 |
|   | MCP server | 8 |
|   | Đánh giá & bằng chứng | 10 |
| B. Cá nhân (40) | Bảo vệ phần mình phụ trách | 15 |
|   | Trả lời câu hỏi kỹ thuật | 15 |
|   | Sửa code trực tiếp tại chỗ | 10 |
| Cộng | Việc làm thêm | tối đa +6 |

## 6. Liêm chính học thuật & dùng AI

Được phép dùng AI/LLM để viết code (đúng tinh thần môn học), nhưng không giải thích được và không khai báo AI → B = 0


## 7. Bắt buộc nộp ai-usage.md: dùng công cụ nào, cho phần nào, prompt chính, đoạn code nào do AI sinh.

## 8. Git history phải thể hiện cả ba thành viên làm việc thật (không dồn 1 commit cuối kỳ).

## 9. Bảo vệ 20 phút: SV sẽ được vấn đáp riêng từng người

| TT  | Nội dung | SV chuẩn bị |
| --- | --- | --- |
| 1 | Cold start: chạy lệnh README trên máy GV | README chính xác, .env.example đầy đủ, data có sẵn |
| 2 | Demo: mỗi SV 3 phút, có 1 câu hỏi GV đưa tại chỗ (không có trong testset) | Mở sẵn terminal |
| 3 | Trình bày kiến trúc, không đọc slide | Sơ đồ in sẵn; mỗi SV ~1.5 phút |
| 4 | Vấn đáp 1 câu chính + 1 câu đào sâu cho mỗi SV Ôn khái niệm w1–w7; nhớ số liệu của chính mình |   |
| 5 | Sửa code trực tiếp: 1 yêu cầu/SV | Biết file/dòng mình viết; IDE quen tay |
