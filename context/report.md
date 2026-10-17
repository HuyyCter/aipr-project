# REPORT — T4: Trợ lý Điểm Rèn Luyện & Khiếu Nại

> Khung sườn. Tổng 8–9 trang. Mỗi mục ghi: số trang, người viết (theo mảng), nội dung phải có, bằng chứng lấy từ đâu.
> Ký hiệu mảng: **[RAG]** = rag/ + search_regulations/get_document · **[SCORING]** = domain/scoring.py + calculate_conduct_score · **[AGENT]** = agent/loop.py + prompts · **[MCP]** = server.py + mcp_client.py + appeals_store.py · **[EVAL]** = eval/evaluate.py · **[CẢ NHÓM]**

---

## 1. Vấn đề, phạm vi, giả định (0.5–1 trang) — [CẢ NHÓM] (1 người viết, 2 người review)

### 1.1 Bài toán và người dùng

Cuối mỗi học kỳ, sinh viên phải tự đối chiếu minh chứng hoạt động với quy chế đánh giá kết quả rèn luyện để biết điểm và xếp loại. Quy chế dài, khung điểm và trần điểm khác nhau theo từng mục, lại có bản cũ và bản mới, nên tra cứu thủ công dễ nhầm và tốn thời gian. Khi thấy điểm sai, sinh viên còn phải nắm hạn nộp và thành phần hồ sơ khiếu nại.

Nhóm xây dựng một trợ lý chạy trên terminal cho **một sinh viên** dùng, giúp ba việc: hỏi đáp quy chế có trích nguồn, tính điểm sơ bộ từ minh chứng, và nộp khiếu nại kèm xác nhận hồ sơ đã được ghi nhận.

### 1.2 Phạm vi: ba tầng của hệ thống

| Tầng | Hệ thống làm gì | Ví dụ |
|---|---|---|
| (a) Tra cứu | Trả lời kèm `doc_id` và đúng phiên bản quy chế; từ chối khi corpus không có thông tin | "Mục chấp hành nội quy tối đa bao nhiêu điểm?" |
| (b) Biến đổi | Cộng điểm các mục, áp trần, đối chiếu khung xếp loại; từ chối tính khi thiếu minh chứng một mục | "Điểm rèn luyện học kỳ này của tôi là bao nhiêu?" |
| (c) Hành động | Ghi hồ sơ khiếu nại vào `data/appeals.jsonl`, sau đó đọc lại để chứng minh hồ sơ đã tồn tại | "Tôi muốn khiếu nại mục hoạt động chính trị - xã hội" |

### 1.3 Hệ thống không làm gì

- Không thay thế quyết định của hội đồng đánh giá; điểm tính ra chỉ mang tính tham khảo.
- Không trả lời nội dung ngoài corpus (học bổng, học phí...): hệ thống từ chối thay vì suy đoán từ kiến thức nền của LLM.
- Không tự đoán điểm khi thiếu minh chứng; tool trả lỗi và agent báo lại đúng như vậy.
- Không xử lý khiếu nại (chỉ tạo hồ sơ `PENDING`), không phục vụ nhiều người dùng đồng thời, không xác thực danh tính sinh viên.

### 1.4 Giả định

- Corpus là dữ liệu mô phỏng phục vụ học tập (DOC0001–DOC0006 của lớp và tài liệu nhóm viết thêm), không phải quy chế đang áp dụng thực tế.
- Minh chứng của sinh viên mẫu là dữ liệu hư cấu hợp lý, cố ý thiếu vài mục để kiểm tra việc từ chối.
- Mã sinh viên do người dùng tự cung cấp và được tin cậy.
- Chỉ có hồ sơ khiếu nại cần lưu nên dùng JSONL append-only thay vì cơ sở dữ liệu; mỗi lần chạy có một client kết nối qua stdio.

---

## 2. Kiến trúc tổng thể (1 trang) — [AGENT] + [MCP]

Hệ thống gồm hai tiến trình tách biệt: **client** (agent) quyết định làm gì, **server** (MCP) thực hiện việc đó; hai bên chỉ giao tiếp bằng JSON-RPC qua stdio.

ảnh

### 2.1 Ranh giới MCP

- **Spawn, không import.** `connect()` chạy `server.py` như subprocess bằng `sys.executable` và đường dẫn tuyệt đối; client không import module nào của server.
- **Discover lúc chạy.** `loop.py` gọi `discover()` (`list_tools`) rồi chuyển schema sang function calling; không có danh sách tool viết cứng.
- **Server không biết agent.** Server chỉ công bố tool và trả text; mọi lỗi trả dưới dạng chuỗi `"Error: ..."`, không ném exception qua ranh giới.

### 2.2 Luồng xử lý một câu hỏi mẫu (khiếu nại)

Câu hỏi: *"Tôi là SV001, muốn khiếu nại mục hoạt động chính trị - xã hội vì thiếu một minh chứng chưa được tính."*

1. `main.py` gọi `connect()` để spawn server; `run_agent` gọi `discover()` lấy danh sách tool và chuyển thành schema cho LLM.
2. LLM trả `tool_calls`: `submit_appeal(student_id, reason, category)`.
3. Loop parse tham số, ghi log, gọi `mcp_client.call()`; server ghi một dòng vào `data/appeals.jsonl` và trả `appeal_id`.
4. Theo luật trong `system_agent.txt`, LLM gọi tiếp `get_appeal_by_id(<appeal_id>)`; server đọc lại hồ sơ từ file và trả kết quả.
5. LLM trả câu trả lời cuối; loop ghi `final_answer`.

Vòng lặp bị chặn bởi `MAX_STEPS = 6`; vượt thì ghi log `error` và dừng.

---

## 3. Thiết kế RAG (1.5 trang) — [RAG]

**Nội dung cần điền:**
- Corpus + metadata (doc_id, title, date/version, owner); bảng DOC của nhóm.
- Chunking theo Điều/Mục + **lý do 3–5 dòng** (không cắt đứt tiêu chí điểm).
- Embedding: model nào, cosine similarity, `store_cache.json`.
- Dense vs hybrid BM25 (tái dùng ex2_1_hybrid_search.py); vì sao hybrid mặc định (thuật ngữ, số điều khoản).
- Xử lý 2 phiên bản quy chế cũ/mới; ngưỡng "không đủ liên quan" → chuỗi fallback.
- (Cộng điểm) metadata filter nếu có dùng.

**Bằng chứng:** docstring chunking.py, prompts/grounding_rag.txt, kết quả so sánh dense vs hybrid từ eval.

---

## 4. Thiết kế Agent & tool (2 trang) — [AGENT] chính, [SCORING] + [MCP] viết phần tool của mình

### 4.1 Schema dữ liệu

> **[CHỜ: thành viên RAG / Agent loop viết]** `Document`, `DocumentChunk` và schema tool phía client (`tool_schema.py`).

Hai schema của tầng Biến đổi và Hành động dùng `@dataclass` có type hint, không dùng dict thô:

```python
@dataclass
class Appeal:  # domain/appeals_store.py
    appeal_id: str
    student_id: str
    reason: str
    category: str
    status: str  # "PENDING"
    timestamp: str  # ISO 8601, UTC


@dataclass
class ScoreResult:  # domain/scoring.py
    raw_total: int  # tổng sau khi trừ điểm, trước khi chốt trần
    total: int  # tổng cuối, trong khoảng 0–100
    classification: str
    breakdown: dict[str, int]  # điểm từng mục sau khi chặn trần
    confirmed_score: bool
```

Mỗi dòng của `appeals.jsonl` là `asdict(Appeal)`; `ScoreResult` giữ cả `raw_total` và `total` để giải thích việc chốt trần.

### 4.2 Mô tả tool

Docstring mỗi tool viết như prompt cho LLM: nêu loại tool (ĐỌC/GHI/TÍNH), điều kiện gọi và hành vi khi thiếu dữ liệu.

> **[CHỜ: thành viên RAG viết]** mô tả `search_regulations` và `get_document`.

**`calculate_conduct_score` (TÍNH).** Hàm thuần `calculate_score()` chạy 4 bước:
1. Chuẩn hóa tên mục về 5 khóa chuẩn bằng so khớp substring; mục "công tác lớp, đoàn, hội" được kiểm tra trước "học tập" vì tên mục này chứa cụm "thành tích đặc biệt trong học tập".
2. Từ chối nếu thiếu mục: `Error: thiếu các mục <...> - không thể tính điểm.` Tool không đoán điểm.
3. Chặn trần từng mục theo `rubric.json` (30/25/30/38/15), điểm âm về 0.
4. Cộng điểm, trừ 10 nếu chưa xác nhận, chốt trần 100, rồi xếp loại theo `rubric.json`.

Trần và ngưỡng xếp loại đọc từ `rubric.json` nên đổi quy chế chỉ cần sửa file này. `confirmed` mặc định `False`, chỉ đặt `True` khi sinh viên nói rõ. Log thật: cùng bộ điểm (18, 22, 15, 20, 8), `confirmed=false` cho 73 điểm (Khá), `confirmed=true` cho 83 điểm (Tốt).

**`submit_appeal` (GHI).** Mỗi lần gọi tạo hồ sơ mới, nên chỉ gọi khi sinh viên nói rõ muốn khiếu nại và nêu lý do; trả `appeal_id` cho bước verify. Thiếu tham số thì trả `Error: ...`.

**`get_appeal_by_id` (ĐỌC, verify).** Tra hồ sơ theo mã; không thấy thì trả `Error: Không tìm thấy hồ sơ khiếu nại #<id>`.

**`list_appeals` (ĐỌC).** Liệt kê khiếu nại của một sinh viên, mới nhất trước.

> **[CHỜ: thành viên Agent loop viết]** 4.3 Agent loop (`MAX_STEPS`, parse an toàn, xử lý lỗi).

### 4.4 Side effect và verify

Tool ghi duy nhất là `submit_appeal` (thêm một dòng vào `appeals.jsonl`); bước verify là gọi `get_appeal_by_id` với mã vừa nhận. Luật này nằm trong `system_agent.txt` (quy tắc bắt buộc số 1), không phải if/else trong `loop.py`, nên loop không cần biết tool nào là tool ghi; đổi lại, độ tin cậy phụ thuộc model tuân thủ prompt, vì vậy nhóm kiểm tra cặp này trên trace.

`get_appeal_by_id` đọc thẳng từ file mỗi lần gọi, không dùng bộ nhớ đệm, nên bằng chứng độc lập với tiến trình server (xem 5.5).

```
[CHỜ: dán đoạn trace thật có cặp submit_appeal → get_appeal_by_id từ logs/run_*.jsonl]
```

> **[CHỜ: thành viên Agent loop viết]** 4.5 Trace thật của một câu hỏi.

---

## 5. MCP server (1 trang) — [MCP]

Server do nhóm tự viết bằng MCP SDK (`MCPServer`), công bố 6 tool bằng `@mcp_server.tool()`; schema JSON được sinh tự động từ type hint và docstring.

### 5.1 Danh sách tool và contract

| Tool | Loại | Tham số | Trả về |
|---|---|---|---|
| `search_regulations` | đọc | `query: str`, `top_k: int = 3` | Các đoạn `[doc_id] tiêu đề (phiên bản, ngày)` + nội dung, ngăn cách bằng `=============`. Không có kết quả: `Không tìm thấy nội dung liên quan trong tài liệu.` |
| `get_document` | đọc | `doc_id: str` | Header + nội dung tài liệu (cắt ở 800 ký tự) |
| `calculate_conduct_score` | tính | `category_scores: dict[str, int]`, `confirmed: bool = False` | `Tổng điểm: x/100`, `Xếp loại`, điểm từng mục; thiếu mục thì trả chuỗi lỗi của `scoring` |
| `submit_appeal` | **ghi** | `student_id: str`, `reason: str`, `category: str` | `Đã tạo hồ sơ khiếu nại #<appeal_id>, trạng thái: PENDING` |
| `get_appeal_by_id` | đọc (verify) | `appeal_id: str` | `[Khiếu nại] #<id> - [MSSV] <mssv> - [Status] <status> - [Nộp lúc] <timestamp>` |
| `list_appeals` | đọc | `student_id: str` | Mỗi hồ sơ một dòng, mới nhất trước |

**Quy ước lỗi:** mọi tool bọc trong `try/except` và khi lỗi luôn trả chuỗi bắt đầu bằng `"Error: "`; `mcp_client.call()` cũng bắt exception, nên agent loop không nhận exception từ tool.

### 5.2 Transport: stdio

Nhóm chọn stdio vì corpus cục bộ, chỉ một người dùng, client và server chạy cùng máy; client spawn server như subprocess nên không cần quản lý cổng mạng hay xác thực.

### 5.3 Stdout sạch và khởi động một lần

`stdout` thuộc về JSON-RPC, một `print()` lạc vào sẽ hỏng cả kết nối, nên server không dùng `print()`; log đi qua `logging` tới `stderr` và `logs/server/server.log`. `DocumentStore`, index embedding và BM25 được nạp một lần ở module level, nên mỗi `call_tool` không phải dựng lại index.

### 5.4 Client discover động

`discover()` gọi `list_tools()` và nhận tool cùng schema từ server lúc chạy; client không có registry viết cứng, nên server thêm, bớt hoặc đổi tool thì client tự cập nhật. Server được spawn bằng `sys.executable` và đường dẫn tuyệt đối nên chạy được từ mọi thư mục.

```
[CHỜ: dán output thật của dòng "Discovered N tools: [...]" sau khi sửa discover()]
```

### 5.5 Dữ liệu bền vững cho cặp ghi → verify

`submit_appeal` chỉ append một dòng JSON vào `data/appeals.jsonl` (`appeal_id` là 8 ký tự đầu của `uuid4`); `get_appeal_by_id` đọc trực tiếp từ file mỗi lần gọi. File hiện có 13 hồ sơ nộp trong 10–14/10/2026 qua nhiều lần khởi động server, tất cả vẫn đọc lại được.

---

## 6. Đánh giá (1.5 trang) — [EVAL] chính, [CẢ NHÓM] cung cấp số liệu phần mình

**Nội dung cần điền:**
- Testset: ≥12 câu, ≥4 no_answer; bảng phân bố theo type (direct/synthesis/calc/action/no_answer).
- Cách đo: faithfulness (LLM-as-judge), tỉ lệ từ chối đúng, chi phí token/câu (calls, prompt/completion tokens).
- Bảng kết quả từng câu kèm token.
- So sánh dense-only vs hybrid (cộng điểm).
- **≥1 ca thất bại thật + phân tích nguyên nhân** (khâu nào hỏng: truy vấn, suy luận, hay judge).
- Lưu ý judge dễ dãi, đã kiểm tay mẫu nhỏ.
- (Cộng điểm) đồ thị + CSV.

**Bằng chứng:** logs/eval_report.csv, tests/testset.jsonl.

---

## 7. Hạn chế & hướng phát triển (0.5 trang) — [CẢ NHÓM]

**1. Vòng đời khiếu nại dừng ở "đã nộp".** `submit_appeal` chỉ tạo hồ sơ `PENDING` và hệ thống không có tool nào để duyệt, từ chối hay phản hồi, nên cặp ghi → verify chỉ chứng minh hồ sơ **đã tồn tại**, không cho biết khiếu nại có được xử lý hay không. Hướng phát triển: thêm tool cho phía nhà trường cập nhật trạng thái; vì file append-only, ghi thêm bản ghi sự kiện cùng `appeal_id` và để `get_appeal_by_id` đọc bản ghi mới nhất.

---

## 8. Phân công & đóng góp (0.5 trang) — [CẢ NHÓM]

**Nội dung cần điền:** bảng Người — Module/file — Commit hash tiêu biểu. Điền sau khi code xong, đối chiếu `git log`.

---

## 9. Phụ lục — [CẢ NHÓM]

- A. Prompt gốc: system_agent.txt, grounding_rag.txt (dán nguyên văn).
- B. Trace dài (1–2 run đầy đủ).
- C. ai-usage.md (dán nguyên văn).