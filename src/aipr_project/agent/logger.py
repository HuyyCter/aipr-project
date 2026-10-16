from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[3]
LOGS_DIR = PROJECT_ROOT / "logs"

VALID_STEP_TYPES = {
    "llm_call",
    "tool_call",
    "tool_result",
    "final_answer",
    "error",
}

def generate_run_id() -> str:
    """Sinh run_id duy nhất cho phiên chạy theo định dạng YYYYMMDD-HHMMSS."""
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

def get_log_path(run_id: str) -> Path:
    """Trả về đường dẫn tới file log JSONL của phiên chạy: logs/run_<run_id>.jsonl."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    return LOGS_DIR / f"run_{run_id}.jsonl"

def log_step(
    run_id: str,
    question_id: str,
    step_index: int,
    step_type: str,
    tool_name: Optional[str] = None,
    args: Optional[dict[str, Any]] = None,
    result: Optional[str] = None,
    usage: Optional[dict[str, Any]] = None,
) -> None:

    if step_type not in VALID_STEP_TYPES:
        raise ValueError(
            f"Invalid step_type: '{step_type}'. Expected one of {sorted(VALID_STEP_TYPES)}"
        )

    log_entry: dict[str, Any] = {
        "run_id": run_id,
        "question_id": question_id,
        "step_index": step_index,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "step_type": step_type,
        "tool_name": tool_name if step_type in {"tool_call", "tool_result", "error"} else None,
        "args": args if step_type == "tool_call" else None,
        "result": result if step_type in {"tool_result", "final_answer", "error"} else None,
        "usage": usage if step_type == "llm_call" else None,
    }

    log_path = get_log_path(run_id)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

def read_run_log(run_id: str) -> list[dict[str, Any]]:
    log_path = get_log_path(run_id)
    if not log_path.exists():
        return []
    entries = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries
