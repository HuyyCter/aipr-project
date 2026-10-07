# Project Structure — T4: Trợ lý Điểm Rèn Luyện & Khiếu Nại

Project độc lập — tạo folder riêng và `uv init` tại đó, không liên quan repo `aipr` chứa bài học theo tuần.

```
drl-agent/                              ← uv init tại đây (đổi tên tuỳ nhóm)
├── .venv/
├── .env                                 # API key — KHÔNG commit
├── .env.example
├── .gitignore
├── .python-version
├── pyproject.toml
├── uv.lock
├── Makefile                              # make setup / make demo / make eval
├── README.md
├── project-structure.md                  # chính file này
├── ai-usage.md                           # khai báo dùng AI (bắt buộc nộp)
│
├── prompts/
│   ├── system_agent.txt                   # system prompt cho agent loop (W2: prompt tách khỏi code)
│   └── grounding_rag.txt                  # grounding prompt cho câu trả lời có trích nguồn
│
├── data/
│   ├── source_docs/                        # DOC000x (quy chế, quy trình khiếu nại) + 2-3 tài liệu mới
│   ├── store_cache.json                    # VectorStore đã embed (khỏi embed lại mỗi lần chạy)
│   └── appeals.jsonl                       # "database-free" — append record khiếu nại (side effect)
│
├── logs/
│   └── run_<timestamp>.jsonl               # ≥3 lần chạy thật — step, tool args/kết quả, USAGE/câu
│
├── tests/
│   └── testset.jsonl                       # ≥12 câu, ≥4 no_answer (xem mục 7 README)
│
└── src/
    ├── common/
    │   ├── llm_client.py                    # W2 — retry/timeout, log lỗi HTTP ra stderr
    │   └── json_codec.py                    # W1 — encoder cho datetime/@dataclass
    │
    ├── rag/
    │   ├── models.py                        # W1 — Document, DocumentChunk (@dataclass)
    │   ├── chunking.py                       # W3 — chunking theo Điều/Mục + lý do (docstring)
    │   ├── store.py                          # W3/W4 — VectorStore (dense, cosine similarity)
    │   └── hybrid_search.py                  # W4 — TÁI DÙNG ex2_1_hybrid_search.py (BM25 + dense)
    │
    ├── domain/
    │   ├── scoring.py                        # tầng (b) — tính điểm rèn luyện, đối chiếu khung xếp loại
    │   └── appeals_store.py                  # tầng (c) — ghi/đọc data/appeals.jsonl
    │
    ├── mcp_server/
    │   └── server.py                         # W7 — 5 tool (@mcp.tool()), stdio, stdout sạch, load store 1 lần
    │
    ├── agent/
    │   ├── tool_schema.py                     # W1 — dataclass/TypedDict cho schema phía client (nếu cần)
    │   ├── mcp_client.py                       # W7 — list_tools()/call_tool(), KHÔNG hard-code registry
    │   ├── loop.py                             # W6 — Agent Loop: MAX_STEPS, parse an toàn, lỗi → "Error: ..."
    │   └── logger.py                           # ghi logs/*.jsonl mỗi bước + USAGE mỗi câu
    │
    ├── eval/
    │   └── evaluate.py                        # W5 — make eval: faithfulness, tỉ lệ từ chối đúng, chi phí token
    │
    └── main.py                                 # entry point terminal — spawn MCP server (stdio) + chạy agent loop
```

## Bảng phụ thuộc giữa các file

| File | Phụ thuộc | Không phụ thuộc |
|---|---|---|
| `rag/models.py` | không phụ thuộc module khác | — |
| `rag/chunking.py` | `rag/models.py` | LLM, store |
| `rag/store.py` | `rag/models.py`, `rag/chunking.py`, `common/llm_client.py` | mcp_server, agent |
| `rag/hybrid_search.py` | `rag/store.py` (glue code gọi vào file lab tái dùng) | mcp_server, agent |
| `domain/scoring.py` | không phụ thuộc RAG — nhận input đã trích sẵn, hàm thuần | mcp_server, agent |
| `domain/appeals_store.py` | chỉ đọc/ghi `data/appeals.jsonl` | mọi thứ khác |
| `mcp_server/server.py` | `rag/store.py`, `rag/hybrid_search.py`, `domain/scoring.py`, `domain/appeals_store.py`, `common/llm_client.py` (nếu tool cần gọi LLM) | `agent/*` — server không được biết gì về agent gọi nó |
| `agent/mcp_client.py` | thư viện `mcp` (client SDK) | không import trực tiếp `mcp_server/server.py` — chỉ spawn nó như subprocess qua đường dẫn tuyệt đối |
| `agent/loop.py` | `agent/mcp_client.py`, `agent/logger.py`, `common/llm_client.py` | không hard-code danh sách tool |
| `eval/evaluate.py` | `agent/loop.py` (chạy agent thật qua từng câu trong testset), `common/llm_client.py` (LLM-as-judge) | không gọi trực tiếp `rag/store.py` — luôn đi qua agent/MCP để đo đúng hệ thống thật |
| `main.py` | `agent/loop.py` | mọi thứ khác gọi gián tiếp qua đây |

Thứ tự code hợp lý (theo đúng chiều phụ thuộc):
`rag/models.py` → `common/json_codec.py` → `common/llm_client.py` → `rag/chunking.py` → `rag/store.py` → `rag/hybrid_search.py` → `domain/scoring.py` → `domain/appeals_store.py` → `mcp_server/server.py` → `agent/tool_schema.py` → `agent/mcp_client.py` → `agent/logger.py` → `agent/loop.py` → `eval/evaluate.py` → `main.py`.

## Makefile (nội dung dự kiến)

```makefile
setup:
	uv sync
	test -f .env || cp .env.example .env

demo:
	uv run python src/main.py

eval:
	uv run python src/eval/evaluate.py --testset tests/testset.jsonl --out logs/eval_report.csv
```

## Vì sao không có `db/`

Toàn bộ trạng thái "ghi" (khiếu nại) nằm trong `data/appeals.jsonl` — append-only, không cần Database thật, vẫn đủ để demo cặp side-effect + verify theo đúng yêu cầu 2.7. `data/store_cache.json` chỉ là cache embedding, không phải nơi lưu trạng thái nghiệp vụ.

## Dependencies dự kiến (`uv add ...`)

Client API (OpenAI-compatible hoặc provider nhóm đang dùng), `mcp` (SDK MCP — chú ý pin version: `mcp[cli]` cho v2), `python-dotenv`, `numpy` (cosine similarity), `rank_bm25` (hybrid search — nằm trong danh sách lib được phép dùng), `tiktoken` (đếm token cho USAGE log).