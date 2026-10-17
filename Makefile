.PHONY: setup demo eval

UV ?= uv
PYTHON ?= python

# Install the locked dependencies and create a local .env template when needed.
setup:
	$(UV) sync
	$(UV) run $(PYTHON) -c "from pathlib import Path; import shutil; env = Path('.env'); example = Path('.env.example'); shutil.copyfile(example, env) if not env.exists() and example.exists() else None"

# Start the interactive terminal agent. MCP client starts the server via
# sys.executable and an absolute path, so the command works from any cwd.
demo:
	$(UV) run $(PYTHON) -m aipr_project.main

# Run the full JSONL test set and write the CSV evaluation report.
eval:
	$(UV) run $(PYTHON) -m aipr_project.eval.evaluate --testset tests/testset.jsonl --output logs/eval_report.csv
