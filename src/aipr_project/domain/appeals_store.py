import json
import logging
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
APPEALS_PATH = PROJECT_ROOT / "data" / "appeals.jsonl"

log = logging.getLogger(__name__)


@dataclass
class Appeal:
    appeal_id: str
    student_id: str
    reason: str
    category: str
    status: str
    timestamp: str

    def submit_appeal(student_id: str, reason: str, category: str) -> str:
        """Tạo hồ sơ khiếu nại, append vào appeals.jsonl"""
        student_id = student_id.strip()
        reason = reason.strip()
        category = category.strip()

        if not student_id or not reason or not category:
            return "Error: Thiếu student_id, reason hoặc category."

        appeal = Appeal(
            appeal_id=str(uuid.uuid4())[:8],
            student_id=student_id,
            reason=reason,
            category=category,
            status="PENDING",
            timestamp=datetime.now(UTC).isoformat(),
        )

        try:
            APPEALS_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(APPEALS_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(appeal), ensure_ascii=False) + "\n")
        except OSError as error:
            log.error("submit_appeal: không ghi được file %s: %s", APPEALS_PATH, error)
            return f"Không tạo được hồ sơ khiếu nại: {error}"

        return (
            f"Đã tạo hồ sơ khiếu nại #{appeal.appeal_id}, trạng thái: {appeal.status}"
        )
