# Lộ Trình & Kế Hoạch Nước Rút — SV2 (Agent Loop + Evaluation)

> **Môn:** AI Programming with Python (AIPR) — Final Project  
> **Đề tài:** T4 — Trợ lý Điểm Rèn Luyện & Khiếu Nại  
> **Phân công SV2:** Agent Loop (W6), Evaluation (W5), LLM Client (W2), Logging, Testset, System Prompt, Báo cáo Mục 4 & 6.  
> ⚠️ **HẠN CHÓT NỘP BÀI (DEADLINE):** **07:00 SÁNG NGÀY 18/10/2026** (Còn ~38 tiếng từ chiều 16/10).

---

## 1. Timeline Nước Rút (Từ 16/10 đến 07:00 18/10)

```mermaid
gantt
    title Kế hoạch Nước Rút SV2 (Deadline 07:00 18/10)
    dateFormat  YYYY-MM-DD HH:mm
    axisFormat  %H:%M (%d/%m)
    
    section Sprint 1: Code & Testset (16/10)
    Hoàn thiện testset.jsonl (>=12 câu)         :done, s1_1, 2026-10-16 16:30, 2h
    Soạn prompts/judge.txt & evaluate.py         :active, s1_2, 2026-10-16 18:30, 3h30m
    Tạo Makefile (setup, demo, eval)            :s1_3, 2026-10-16 22:00, 1h30m
    
    section Sprint 2: Benchmark & Log (17/10 sáng)
    Chạy eval thực nghiệm & fix lỗi             :s2_1, 2026-10-17 00:00, 2h
    So sánh Dense vs Hybrid & biểu đồ (+1đ)     :s2_2, 2026-10-17 08:00, 3h
    Thu thập >=3 run logs mẫu chuẩn             :s2_3, 2026-10-17 11:00, 2h
    
    section Sprint 3: Báo Cáo & AI Usage (17/10 chiều-tối)
    Viết Report Mục 4 (Agent Design & Trace)    :s3_1, 2026-10-17 13:30, 3h
    Viết Report Mục 6 (Eval, Bảng, Ca lỗi)      :s3_2, 2026-10-17 16:30, 3h30m
    Cập nhật ai-usage.md                        :s3_3, 2026-10-17 20:00, 1h30m
    
    section Sprint 4: Rà soát & Đóng gói (Đêm 17 -> Sáng 18)
    Rà soát toàn bộ checklist & chạy thử        :s4_1, 2026-10-17 21:30, 2h30m
    Nghỉ ngơi & chốt nộp trước 06:30            :crit, s4_2, 2026-10-18 05:30, 1h
```

---

## 2. Chi Tiết Kế Hoạch Thực Hiện Theo Từng Khung Giờ

### 🔹 Chặng 1: Hoàn tất Code & Bộ Testset (16h30 – 23h30 Ngày 16/10)
*Mục tiêu: Đạt được phiên bản code chạy thông suốt không lỗi.*

| Công việc | File thực hiện | Deadline chi tiết | Tiêu chí hoàn thành (DoD) | Trạng thái |
|---|---|---|---|---|
| **Cổng LLM Client** | `src/aipr_project/common/llm_client.py` | Đã xong | Hoàn thành chat Groq, embed Jina, retry backoff, estimate cost | **Xong (Done)** |
| **Agent Logger** | `src/aipr_project/agent/logger.py` | Đã xong | Chuẩn hóa 5 `step_type`, ghi JSONL, usage token | **Xong (Done)** |
| **Agent Loop** | `src/aipr_project/agent/loop.py` | Đã xong | ReAct loop, MCP discover động, MAX_STEPS = 6, safe parse | **Xong (Done)** |
| **System Prompt** | `prompts/system_agent.txt` | Đã xong | Luật ReAct, quy tắc verify bắt buộc sau khi submit appeal | **Xong (Done)** |
| **Bổ sung Testset** | `tests/testset.jsonl` | **18:30 (16/10)** | Đủ $\ge 12$ câu (hiện có 10 câu), $\ge 4$ câu `no_answer`, phủ đủ direct, synthesis, calc, action | 🟡 Đang làm |
| **Prompt Judge** | `prompts/judge.txt` | **19:30 (16/10)** | Prompt cho LLM-as-judge chấm faithfulness (0/1) kèm giải thích claim | ⏳ Chưa làm |
| **Module Đánh giá** | `src/aipr_project/eval/evaluate.py` | **22:00 (16/10)** | Chạy qua testset với agent thật, chấm Faithfulness + Refusal Rate, đọc log tính chi phí, xuất `logs/eval_report.csv` | ⏳ Chưa làm |
| **Tạo Makefile** | `Makefile` | **23h30 (16/10)** | Đủ 3 lệnh: `make setup`, `make demo`, `make eval` | ⏳ Chưa làm |

---

### 🔹 Chặng 2: Benchmark (+1đ), Sinh Biểu Đồ & Thu Thập Log Mẫu (00h00 – 12h00 Ngày 17/10)
*Mục tiêu: Có đầy đủ số liệu thực nghiệm, hình ảnh và log chạy thật để đưa vào báo cáo.*

| Công việc | File / Thư mục | Deadline chi tiết | Tiêu chí hoàn thành (DoD) |
|---|---|---|---|
| **Chạy Eval lần 1 & Fix lỗi** | `logs/eval_report.csv` | **02:00 (17/10)** | Chạy `make eval` mượt mà, ghi nhận bảng điểm ban đầu |
| **So sánh Dense vs Hybrid (+1đ)** | `src/aipr_project/eval/evaluate.py` | **10:00 (17/10)** | Chạy thêm 1 lượt testset với cấu hình Dense-only để so sánh độ chính xác với Hybrid Search |
| **Vẽ biểu đồ Matplotlib** | `logs/faithfulness_comparison.png` | **11:00 (17/10)** | Biểu đồ cột so sánh Faithfulness giữa 2 cấu hình, dùng dán vào Report Mục 6 |
| **Lưu $\ge 3$ run logs thật** | `logs/run_<timestamp>.jsonl` | **12:00 (17/10)** | 3 file log riêng biệt thể hiện 3 kịch bản: tra cứu quy chế, tính điểm rèn luyện, nộp khiếu nại (có verify) |

---

### 🔹 Chặng 3: Viết Báo Cáo Word & Hoàn Thiện Hồ Sơ (13h30 – 21h30 Ngày 17/10)
*Mục tiêu: Hoàn tất nội dung phần SV2 trong Báo cáo cuối kỳ 8–9 trang.*

| Nội dung báo cáo | Vị trí trong `report.docx` | Deadline chi tiết | Yêu cầu nội dung |
|---|---|---|---|
| **Thiết kế Agent & Tools** | **Mục 4** (2 trang) | **16:30 (17/10)** | - Schema dataclass thật trong code.<br>- Cơ chế ReAct loop, dynamic tool discovery qua MCP.<br>- Giải thích `MAX_STEPS = 6`, cơ chế xử lý lỗi an toàn không crash.<br>- Quy tắc cặp hành động bắt buộc: `submit_appeal` $\rightarrow$ `get_appeal_by_id`.<br>- Dán 1 trace chạy thật nguyên văn trích từ `logs/run_*.jsonl`. |
| **Đánh giá thực nghiệm** | **Mục 6** (1.5 trang) | **20:00 (17/10)** | - Bảng số liệu tổng hợp: Faithfulness, Tỉ lệ từ chối đúng (Refusal Rate), Chi phí token/câu.<br>- Biểu đồ cột so sánh Dense vs Hybrid.<br>- Phân tích chuyên sâu ít nhất 1 ca lỗi thật (failure analysis). |
| **Khai báo sử dụng AI** | `ai-usage.md` | **21:30 (17/10)** | Liệt kê chi tiết các công cụ AI, prompt mẫu và các đoạn code được hỗ trợ trong phần việc SV2. |

---

### 🔹 Chặng 4: Tổng Duyệt, Sanity Check & Nộp Bài (21h30 Ngày 17/10 – 06h30 Sáng 18/10)
*Mục tiêu: Đảm bảo không có lỗi ngớ ngẩn (broken path, thiếu file, crash).*

| Khung giờ | Nội dung kiểm tra |
|---|---|
| **21:30 – 23:00 (17/10)** | Chạy thử toàn bộ các lệnh trên terminal sạch: `make setup`, `make demo`, `make eval`. Kiểm tra `git status` và clean code. |
| **23:00 – 24:00 (17/10)** | Tạo Pull Request từ `feature/stage-b` vào `main`, review code chung với SV1 và SV3, merge vào nhánh chính. |
| **24:00 – 05:30 (18/10)** | Nghỉ ngơi giữ sức khỏe cho buổi bảo vệ. |
| **05:30 – 06:30 (18/10)** | Kiểm tra lần cuối file `report.docx`, link GitHub repo, các file log. Nộp bài trước **07:00**. |

---

## 3. Checklist Tự Kiểm Tra Kỹ Thuật (Pre-submission Sanity Check)

Trước khi đóng gói nộp bài trước 06:30 ngày 18/10:

- [ ] `grep -rn "TOOL_REGISTRY" src/aipr_project/agent/` $\rightarrow$ Không có kết quả nào (discover động 100%).
- [ ] Chạy câu hỏi sai định dạng args $\rightarrow$ Agent không crash, log ghi `"Error:..."` và tiếp tục.
- [ ] `MAX_STEPS = 6` ngắt đúng lúc khi gặp câu hỏi lặp vô tận.
- [ ] Mỗi dòng `step_type == "llm_call"` có `usage` đủ 3 trường (`calls`, `prompt_tokens`, `completion_tokens`).
- [ ] Đủ $\ge 3$ file log `logs/run_*.jsonl` thực tế, không ghi đè nhau.
- [ ] Lệnh `make eval` chạy trọn vẹn từ đầu đến cuối không bị exception, xuất `logs/eval_report.csv`.
- [ ] Đủ $\ge 12$ câu trong `tests/testset.jsonl` với $\ge 4$ câu `no_answer`.
- [ ] Có biểu đồ `logs/faithfulness_comparison.png` và bảng đối sánh Dense vs Hybrid.
- [ ] `Makefile` chạy mượt trên cả Windows (PowerShell/cmd) và Linux.
