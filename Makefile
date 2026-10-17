.PHONY: setup demo eval

# Cai thu vien va tao .env tu .env.example (neu chua co)
setup:
	uv sync
	uv run python -c "import os, shutil; os.makedirs('logs', exist_ok=True); os.path.exists('.env') or shutil.copy('.env.example', '.env')"
	@echo Da tao .env. Dien API key vao .env truoc khi chay make demo.

# Chat tuong tac (spawn MCP server qua stdio)
demo:
	uv run python src/aipr_project/main.py

# Chay testset qua agent that, cham RAGAS, ghi logs/rag_evaluation.json
eval:
	uv run python src/aipr_project/main.py --eval