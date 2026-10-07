# Final Project AIPR — T4: Trợ lý Điểm Rèn Luyện & Khiếu Nại

> Môn học: AI Programming with Python (W1–W7) · Nhóm 3 SV · 10 ngày
> Giao diện: Terminal · Không dùng Database (file JSON/JSONL)
> File này giải thích project làm gì và tại sao thiết kế như vậy. Cấu trúc thư mục/file cụ thể xem ở `project-structure.md`.

---

## 0. Việc phải nộp (đọc trước khi code)

| # | Sản phẩm | File/thư mục tương ứng |
|---|---|---|
| 1 | `report.docx` 8-9 trang | làm riêng, theo khung ở mục 9 README này |
| 2 | Repo code kèm `.git` (lịch sử commit cả 3 người) | toàn bộ repo |
| 3 | ≥3 lần chạy thật, mỗi lần 1 file `.jsonl` | `logs/run_<timestamp>.jsonl` |
| 4 | ≥12 câu test, ≥4 câu `no_answer` | `tests/testset.jsonl` |
| 5 | Khai báo dùng AI | `ai-usage.md` |
| 6 | Lệnh chạy duy nhất tái lập demo + eval | `Makefile` (`make setup && make demo`, `make eval`) |

**Không chọn được điểm nếu thiếu 1 trong 3 tầng bắt buộc** (theo đề bài gốc): (a) Tra cứu có nguồn, (b) Biến đổi (không copy nguyên văn), (c) Hành động có side effect + verify. Mục 1 dưới đây map rõ cả 3 tầng vào đúng tính năng của đề tài T4.

---

## 1. Bài toán & 3 tầng bắt buộc

**T4 — Trợ lý điểm rèn luyện + khiếu nại**: sinh viên hỏi quy chế điểm rèn luyện, nhờ hệ thống tính điểm rèn luyện dựa trên minh chứng hoạt động, và nộp khiếu nại nếu thấy điểm tính sai — toàn bộ qua agent, có trích nguồn và có thể kiểm chứng.

| Tầng | Trong đề tài T4 cụ thể là | Vì sao không thể bỏ |
|---|---|---|
| **(a) Tra cứu** | "Tiêu chí mục ý thức học tập tính như thế nào?", "Hạn nộp khiếu nại là bao lâu?" — trả lời có `doc_id`, đúng phiên bản quy chế (có 2 bản: cũ/mới) | Không có tầng này thì chỉ là chatbot đọc file, không phải RAG có đo được |
| **(b) Biến đổi** | Tính tổng điểm rèn luyện từ các mục điểm thành phần (phải cộng, đối chiếu khung xếp loại) + phát hiện mâu thuẫn giữa quy chế cũ/mới + từ chối tính nếu thiếu minh chứng một mục | Nếu mọi câu chỉ là "tra 1 đoạn rồi đọc lại" thì faithfulness luôn ≈ 1.0 → eval vô nghĩa |
| **(c) Hành động** | `submit_appeal` (tool ghi — tạo hồ sơ khiếu nại mới) → **bắt buộc** gọi lại `get_appeal_status` ngay sau để chứng minh hồ sơ đã được tạo thật | Thiếu tầng này thì chỉ là pipeline đọc rồi in, không phải agent |

**Câu tự kiểm trước khi nộp:** đưa 1 câu không có trong corpus (ví dụ hỏi về học bổng — ngoài phạm vi quy chế rèn luyện), hệ thống có từ chối đàng hoàng không, hay vẫn bịa ra một câu nghe hợp lý?

---

## 2. Bản đồ W1–W7 → thành phần project

| Tuần | Concept bắt buộc theo đề | Thành phần trong project |
|---|---|---|
| **W1** | Tool schema bằng `dataclass`/`TypedDict`, có type hint, **không dict thô** | `agent/tool_schema.py`, `rag/models.py` |
| **W2** | Gọi API có retry/timeout, log lỗi HTTP; prompt tách khỏi code | `common/llm_client.py` + file `.txt` trong `prompts/` |
| **W3–W4** | ≥2 chế độ truy vấn (dense + hybrid BM25, tái dùng `ex2_1_hybrid_search.py`); chunking có lý do | `rag/chunking.py`, `rag/store.py`, `rag/hybrid_search.py` |
| **W5** | Đo faithfulness, tỉ lệ từ chối đúng, chi phí token/câu | `eval/evaluate.py`, chạy qua `make eval` |
| **W6** | Agent loop tự viết: `MAX_STEPS`, lỗi tool → chuỗi `"Error: ..."` (không raise), parse action an toàn | `agent/loop.py` |
| **W7** | MCP server tự viết, ≥2 tool (≥1 tool ghi), chạy qua stdio, stdout sạch; client discover động (không hard-code registry) | `mcp_server/server.py`, `agent/mcp_client.py` |

Không có tuần nào là "phụ" — thiếu W7 thì không gọi là đề tài theo đúng yêu cầu khoá học này (vì đề bài ghi rõ trọng tâm bắt buộc gồm cả MCP).

---

## 3. Kiến trúc tổng thể

```
                        ┌───────────────────────────────┐
                        │        TERMINAL (main.py)       │
                        └───────────────┬─────────────────┘
                                        │
                        ┌───────────────▼─────────────────┐
                        │        AGENT LOOP (W6, agent/loop.py) │
                        │  - message → LLM → tool-or-done         │
                        │  - MAX_STEPS guard                       │
                        │  - parse action an toàn (lỗi → "Error: ")│
                        │  - ghi log từng bước vào logs/*.jsonl     │
                        └───────────────┬───────────────────┘
                                        │ stdio (client spawn server,
                                        │ KHÔNG hard-code tool list)
                        ┌───────────────▼───────────────────┐
                        │     MCP SERVER (W7, mcp_server/server.py) │
                        │  tools/list  →  5 tool khai báo bằng decorator│
                        └───┬───────┬───────┬───────┬───────┬───────┘
                            │       │       │       │       │
                  search_regulations  get_document  calculate_conduct_score
                            │       │           submit_appeal (GHI)
                            │       │              get_appeal_status (ĐỌC — verify)
                  ┌─────────▼───────▼─────┐      ┌─────────▼─────────┐
                  │   RAG layer (W3–W4)      │      │  domain/scoring.py  │
                  │   VectorStore (dense)      │      │  domain/appeals_store.py│
                  │   hybrid_search.py (BM25)   │      │  → data/appeals.jsonl    │
                  └─────────┬─────────────┘      └─────────────────────┘
                            │
                  ┌─────────▼─────────────┐
                  │   data/source_docs/       │
                  │   (quy chế, metadata)      │
                  └───────────────────────────┘

                  Mọi lời gọi API đều qua:  common/llm_client.py (W2)
                  Đánh giá độc lập, chạy riêng qua `make eval`:  eval/evaluate.py (W5)
```

**Nguyên tắc thiết kế quan trọng (Concept 1, Week 7):** server **không** publish thẳng các method nội bộ của `VectorStore`/`scoring` — chỉ publish 5 tool có tên là động từ, input/output có kiểu rõ ràng, trả về text kèm `doc_id` (provenance), không trả tuple/object thô. Ví dụ `store.search_with_threshold(q, t)` **không** được publish thẳng vì model không có cơ sở để tự chọn số `threshold`.

---

## 4. Luồng xử lý — 3 kịch bản mẫu

### 4.1 Câu hỏi tra cứu thuần (tầng a)
`"Mục ý thức chấp hành nội quy tối đa bao nhiêu điểm?"`
→ agent gọi `search_regulations` → MCP server chạy hybrid search trên corpus → trả đoạn kèm `[DOC0001]` → agent sinh câu trả lời có trích nguồn.

### 4.2 Câu hỏi cần tính toán (tầng b)
`"Với minh chứng hiện có, điểm rèn luyện học kỳ này của sinh viên X là bao nhiêu, xếp loại gì?"`
→ agent gọi `search_regulations` lấy khung điểm từng mục + `get_document` lấy minh chứng hoạt động của SV → gọi `calculate_conduct_score(category_scores)` → nếu thiếu minh chứng 1 mục, tool trả `"Error: thiếu dữ liệu mục ... — không thể tính"` thay vì đoán → agent báo lại đúng như vậy, **không tự bịa điểm**.

### 4.3 Câu hỏi hành động (tầng c)
`"Tôi muốn khiếu nại điểm mục hoạt động chính trị-xã hội, lý do: thiếu 1 minh chứng chưa được tính."`
→ agent gọi `submit_appeal(student_id, reason, disputed_criteria)` (tool **ghi**, append vào `data/appeals.jsonl`) → **ngay sau đó bắt buộc** gọi `get_appeal_status(appeal_id)` để đọc lại, chứng minh hồ sơ đã tồn tại → agent in cả hai bước ra terminal, không chỉ báo "đã nộp thành công" suông.

### 4.4 Câu hỏi ngoài phạm vi (no_answer, vẫn thuộc tầng a)
`"Học bổng khuyến khích học tập xét theo tiêu chí nào?"`
→ agent vẫn gọi `search_regulations` (đúng quy trình), không tìm được đoạn nào đủ liên quan → trả lời đúng câu từ chối chuẩn hoá (ví dụ: `"Tài liệu hiện có không đề cập đến nội dung này."`) — **không** suy diễn từ kiến thức nền của LLM.

---

## 5. Vai trò từng thành phần

### 5.1 Data Model (W1)
`Document`, `DocumentChunk` khai báo bằng `@dataclass` (hoặc `TypedDict` cho tool schema phía MCP) — có type hint đầy đủ, không dùng `dict` thô cho bất kỳ schema nào chấm điểm được (`grep -n "@dataclass\|TypedDict"` phải ra kết quả ở đúng những file định nghĩa schema).

### 5.2 LLM Client (W2)
Một điểm gọi API duy nhất, có retry + timeout cho lỗi tạm thời, log lỗi HTTP ra `stderr` (không log ra `stdout` — stdout dành cho giao thức MCP). Prompt (system prompt của agent, grounding prompt cho RAG) nằm trong file `.txt` ở `prompts/`, không hard-code chuỗi trong code — đúng yêu cầu 2.4.

### 5.3 RAG layer (W3–W4)
- **Chunking** có lý do viết thành 3-5 dòng docstring (ví dụ: quy chế chia theo từng "Điều/Mục" — chunk theo ranh giới đó thay vì cắt cứng theo số ký tự, để không cắt đứt giữa 1 tiêu chí điểm).
- **Dense search**: `VectorStore` (embedding + cosine similarity, như đã học W3).
- **Hybrid search**: **tái dùng nguyên file** `ex2_1_hybrid_search.py` đã làm ở lab W4 (BM25 + dense), không viết lại — chỉ viết phần glue code gọi vào.
- Agent mặc định dùng **hybrid** (ổn định hơn cho văn bản quy chế nhiều thuật ngữ/số điều khoản mà dense đơn thuần dễ bỏ sót). `eval/evaluate.py` chạy thêm cấu hình dense-only để so sánh — vừa phục vụ mục "So sánh thêm 1 cấu hình" (điểm cộng), vừa là bằng chứng cho lý do chọn hybrid làm mặc định, nên trình bày rõ trong report mục 3.

### 5.4 Biến đổi — Scoring (tầng b)
`domain/scoring.py` — hàm thuần (pure function), nhận điểm từng mục (đã được agent/LLM trích từ minh chứng + đối chiếu khung quy chế), cộng tổng, so khớp khung xếp loại lấy từ chính quy chế (không hard-code ngưỡng xếp loại trong code — đọc từ tài liệu, tránh lệch khi quy chế đổi). Nếu thiếu dữ liệu 1 mục, trả lỗi rõ ràng thay vì tính thiếu.

### 5.5 Hành động — Appeals (tầng c)
`domain/appeals_store.py` — "database-free": append record vào `data/appeals.jsonl` (mỗi dòng 1 JSON object có `appeal_id`, `student_id`, `timestamp`, `reason`, `status`). Đây là tool **ghi** bắt buộc theo yêu cầu 2.7. Cặp `submit_appeal()` → đọc lại bằng `get_appeal_status()` là bằng chứng "agent thực sự dùng kết quả tool", không phải LLM tự diễn.

### 5.6 MCP Server (W7)
`mcp_server/server.py` publish đúng 5 tool (3 đọc + 1 ghi + 1 đọc-để-verify), dùng decorator (`@mcp.tool()`), load `VectorStore` **một lần** ở module level (không rebuild index mỗi lần gọi tool — lỗi kinh điển gây timeout). Chạy qua **stdio** (phù hợp vì là corpus cục bộ, 1 người dùng — đúng bảng so sánh transport ở slide W7). Tuyệt đối không `print()` trong tool — mọi log đi qua `stderr`/logging facility, vì `stdout` thuộc về giao thức JSON-RPC.

### 5.7 Agent Loop & Logging (W6 + W7)
`agent/loop.py` — vòng lặp **Week 6 nguyên bản** (message → LLM → tool-or-done), chỉ khác ở chỗ danh sách tool **lấy từ `list_tools()` lúc chạy**, không có `TOOL_REGISTRY` hard-code nào trong file (sẽ bị kiểm bằng `grep`). Có `MAX_STEPS` chặn lặp vô hạn; nếu model trả về action sai định dạng (thiếu ngoặc, JSON lỗi), loop bắt lỗi và tiếp tục chứ không crash. Mỗi bước (Thought/Action/Observation hoặc tool_call/tool_result) được ghi vào `logs/run_<timestamp>.jsonl`, kèm `USAGE` (số lần gọi LLM, `prompt_tokens`, `completion_tokens`) cho từng câu hỏi.

### 5.8 Evaluation (W5)
`eval/evaluate.py` chạy độc lập qua `make eval`, đọc `tests/testset.jsonl`, với mỗi câu: chạy qua agent thật (không mock), chấm **faithfulness** (claim có được context hỗ trợ không) và với riêng nhóm câu `no_answer` thì chấm **tỉ lệ từ chối đúng** (có từ chối đúng cách hay bịa). Xuất báo cáo kèm chi phí token từng câu — dùng trực tiếp cho report mục 6 và cho điểm cộng "Đồ thị + CSV log chi tiết".

---

## 6. Dữ liệu & tài liệu nguồn

Mọi tài liệu trong `data/source_docs/` phải có metadata: `doc_id`, `title`, `date/version`, `owner`. Gợi ý bộ corpus cho T4 (được phép tái dùng DOC0001–DOC0006 của lớp + viết thêm 2-3 tài liệu mới — **không dùng dữ liệu của nhóm khác cùng đề tài T4**):

| doc_id | Nội dung | Vai trò |
|---|---|---|
| DOC000x | Quy chế đánh giá kết quả rèn luyện — bản hiện hành | nguồn chính cho tra cứu + khung tính điểm |
| DOC000x | Quy chế bản cũ (đã hết hiệu lực) | kiểm tra agent có chọn đúng bản mới khi có mâu thuẫn phiên bản |
| DOC000x | Quy định/quy trình khiếu nại kết quả rèn luyện | hạn nộp, nơi nộp, thành phần hồ sơ |
| *(mới)* | Danh sách minh chứng hoạt động của 1 sinh viên mẫu (có thể hư cấu, hợp lý) | dữ liệu để tính điểm — cố ý để thiếu minh chứng 1-2 mục để test "từ chối vì thiếu dữ liệu" |
| *(mới)* | 1-2 tài liệu phụ (ví dụ: thông báo điều chỉnh một mục điểm năm nay) | tăng độ khó cho tổng hợp/so sánh |

---

## 7. Bộ testset (`tests/testset.jsonl`)

≥12 câu, ≥4 câu `no_answer`, phủ đủ cả 3 tầng:

| Loại | Số câu gợi ý | Mục đích |
|---|---|---|
| Direct (tầng a) | 3-4 | 1 đoạn trả lời được ngay, có doc_id |
| Synthesis / so sánh phiên bản (tầng a+b) | 2-3 | phải ghép ≥2 tài liệu, hoặc chọn đúng bản mới khi 2 bản mâu thuẫn |
| Tính toán (tầng b) | 2-3 | tính điểm rèn luyện; ít nhất 1 câu cố ý thiếu dữ liệu để kiểm tra từ chối đúng kiểu (ii) — "thiếu để suy luận", khác với (i) "tài liệu không có" |
| Hành động (tầng c) | 1-2 | nộp khiếu nại, kiểm tra cặp ghi→verify xuất hiện trong trace |
| `no_answer` (ngoài corpus) | ≥4 | ví dụ hỏi học bổng, hỏi học phí — không liên quan quy chế rèn luyện |

Mỗi dòng JSONL nên có ít nhất: `id`, `question`, `type` (direct/synthesis/calc/action/no_answer), `expected_doc_ids` (rỗng nếu `no_answer`).

---

## 8. Reproducibility & Makefile

Ba lệnh duy nhất giảng viên sẽ chạy trên máy của họ:

```
make setup   # uv sync + chuẩn bị .env từ .env.example (không tự điền key)
make demo    # chạy agent terminal tương tác — spawns MCP server qua stdio tự động
make eval    # chạy tests/testset.jsonl qua eval/evaluate.py, in kết quả + ghi report CSV
```

`make demo` phải chạy được **ngay trên máy giảng viên** mà không cần sửa đường dẫn — tuyệt đối không spawn server bằng `python` trần + đường dẫn tương đối (lỗi kinh điển "Connection closed" lúc initialize); dùng `sys.executable` + đường dẫn tuyệt đối.

---

## 9. Khung report.docx (8-9 trang — làm riêng, không phải code)

1. Vấn đề, phạm vi, giả định (0.5-1tr) — hệ thống **không** làm gì (ví dụ: không thay thế quyết định cuối của phòng công tác SV, chỉ hỗ trợ tra cứu + tính sơ bộ + nộp khiếu nại).
2. Kiến trúc tổng thể (1tr) — lấy sơ đồ mục 3 + vẽ lại 1 luồng xử lý cho đúng 1 câu hỏi mẫu (dùng ví dụ mục 4.3 vì có đủ cả ghi + verify).
3. Thiết kế RAG (1.5tr) — chunking + lý do, embedding, hybrid vs dense, vì sao chọn hybrid mặc định.
4. Thiết kế Agent & tool (2tr) — schema dataclass thật trong code, mô tả 5 tool như một bản "API docs", `MAX_STEPS`, cách xử lý lỗi, cặp side-effect + verify, 1 trace thật dán nguyên văn.
5. MCP server (1tr) — danh sách tool + contract, transport (vì sao stdio), vì sao stdout sạch, cách client discover (dán đoạn log `Discovered N tools: [...]`).
6. Đánh giá (1.5tr) — mô tả testset, cách đo faithfulness + tỉ lệ từ chối đúng, bảng kết quả kèm chi phí token/câu, ≥1 ca thất bại thật + phân tích nguyên nhân.
7. Hạn chế & hướng phát triển (0.5tr) — ≥2 hạn chế **trung thực** (không viết "chưa có thời gian").
8. Phân công & đóng góp (0.5tr) — ai làm gì + commit hash tương ứng.
9. Phụ lục — prompt gốc, trace dài, `ai-usage.md`.

---

## 10. Giới hạn cần nêu trong báo cáo

- Điểm rèn luyện do hệ thống tính là **sơ bộ**, dựa trên minh chứng agent đọc được — không thay thế quyết định chính thức của hội đồng đánh giá.
- Faithfulness đo "bám vào context", không đo "đúng theo quy chế thật sự áp dụng" nếu quy chế trong corpus đã lỗi thời so với bản hiện hành của trường (phải nói rõ corpus dùng là dữ liệu mô phỏng cho mục đích học tập).
- LLM-as-judge trong `eval/evaluate.py` có thể dễ dãi — nên kiểm tay 1 mẫu nhỏ trước khi tin số liệu.

---

## 11. Phân công theo 3 tầng + verify (nhóm đã chốt)

Vì đề chấm theo RAG + Reasoning + Agent + MCP + Eval (không phải frontend/backend/report), nhóm chia đúng theo 3 tầng đề bài định nghĩa — mỗi người có 1 module kỹ thuật rõ ràng, dễ chứng minh đóng góp cá nhân khi vấn đáp:

| Người | Tầng chính | Module | + phụ trách thêm |
|---|---|---|---|
| **SV 1** | (a) Tra cứu | `rag/`, `mcp_server/server.py` (phần tool đọc: `search_regulations`, `get_document`) | **Agent Loop + MCP Client** — `agent/loop.py`, `agent/mcp_client.py` |
| **SV 2** | (b) Biến đổi | `domain/scoring.py`, `mcp_server/server.py` (tool `calculate_conduct_score`) | **Evaluation** — `eval/evaluate.py` |
| **SV 3** | (c) Hành động + Verify | `domain/appeals_store.py`, `mcp_server/server.py` (tool `submit_appeal`, `get_appeal_status`) | — |

**Vì sao verify đi chung với Hành động, không tách riêng:** verify không phải một bước độc lập — nó là nửa còn lại của chính tool ghi (`submit_appeal` → `get_appeal_status`). Tách nó ra khỏi tầng (c) mới là sai bản chất.

**Vì sao Agent Loop + MCP Client gắn với SV 1:** đây là phần quyết định *khi nào gọi tool nào*, `MAX_STEPS`, parse lỗi an toàn, discover tool động — không gắn riêng cho ai thì khi vấn đáp hỏi "Agent biết phải gọi tool này vì sao?", không ai trả lời dứt khoát được. Gắn với người phụ trách tra cứu là hợp lý vì search luôn là tool đầu tiên trong mọi luồng xử lý.

**Lưu ý khi chuẩn bị vấn đáp cho SV 2:** `eval/evaluate.py` chạy qua *toàn bộ* testset (cả tra cứu, tính toán, hành động, no_answer), không chỉ riêng tầng (b) — nên cần hiểu sơ qua cả 3 tầng để giải thích được số liệu, không chỉ phần mình viết.

**Bốn câu mỗi người phải trả lời được cho đúng module mình phụ trách** (giám khảo sẽ hỏi dạng này):
- "Nếu tôi sửa dòng này thì hệ thống thay đổi gì?"
- "Tại sao Agent biết phải gọi tool này?" *(SV 1 — agent loop)*
- "Nếu corpus không có đáp án thì sao?" *(SV 1 — grounding + no_answer)*
- "Làm sao chứng minh tool đã thực sự thay đổi dữ liệu?" *(SV 3 — submit_appeal → get_appeal_status)*

Mỗi người nên có commit riêng rải trong 10 ngày (không dồn 1 commit cuối) để khớp yêu cầu "git history thể hiện cả ba thành viên làm việc thật".