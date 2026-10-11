import json
import logging
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
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
            return f"Error: không tạo được hồ sơ khiếu nại: {error}"

        return (
            f"Đã tạo hồ sơ khiếu nại #{appeal.appeal_id}, trạng thái: {appeal.status}"
        )

    def get_appeal_by_id(appeal_id: str) -> str:
        """Tra hồ sơ khiếu nại theo id"""
        appeal_id = appeal_id.strip()
        if not appeal_id:
            return "Error: appeal_id đang bị để trống."

        try:
            with open(APPEALS_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    appeal = json.loads(line)
                    if appeal.get("appeal_id") == appeal_id:
                        return (
                            f"[Khiếu nại] #{appeal.get('appeal_id')} - "
                            f"[MSSV] {appeal.get('student_id')} - "
                            f"[Status] {appeal.get('status')} - "
                            f"[Nộp lúc] {appeal.get('timestamp')}"
                        )
        except OSError as error:
            log.error(
                "get_appeal_by_id: không đọc được file %s: %s", APPEALS_PATH, error
            )
            return f"Error: không đọc được hồ sơ khiếu nại: {error}"

        return f"Error: Không tìm thấy hồ sơ khiếu nại #{appeal_id}"

    def list_appeals(student_id: str) -> str:
        """Liệt kê khiếu nại của 1 sinh viên, mới nhất trước, tối đa MAX_LIST hồ sơ."""
        student_id = student_id.strip()
        if not student_id:
            return "Error: student_id đang bị để trống."

        appeals: list[dict] = []
        try:
            with open(APPEALS_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    appeal = json.loads(line)
                    if appeal.get("student_id") == student_id:
                        appeals.append(appeal)
        except OSError as error:
            log.error("list_appeals: không đọc được file %s: %s", APPEALS_PATH, error)
            return f"Error: không đọc được danh sách hồ sơ khiếu nại: {error}"

        if not appeals:
            return f"Sinh viên {student_id} chưa có khiếu nại nào."

        appeals.reverse()
        lines = [f"Sinh viên {student_id} có {len(appeals)} khiếu nại: "]
        for appeal in appeals:
            lines.append(
                f"- [Khiếu nại] #{appeal.get('appeal_id')} - "
                f"[Danh mục] {appeal.get('category')} - "
                f"[Status] {appeal.get('status')} - "
                f"[Nộp lúc] {appeal.get('timestamp')}"
            )

        return "\n".join(lines)
