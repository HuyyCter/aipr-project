import logging
import sys
from pathlib import Path

from mcp.server.mcpserver import MCPServer

from src.aipr_project.domain.appeals_store import Appeal

PROJECT_ROOT = Path(__file__).resolve().parents[3]
LOG_PATH = PROJECT_ROOT / "logs" / "server" / "server.log"

# ==================== LOGGING ====================
_handler: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]
try:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _handler.append(logging.FileHandler(LOG_PATH, encoding="utf-8"))
except OSError as error:
    print(f"warning: cannot open {LOG_PATH}: {error}", file=sys.stderr)

logging.basicConfig(
    level=logging.INFO,
    handlers=_handler,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


# ==================== MCP SERVER ====================
mcp_server = MCPServer(
    "aipr-project",
    description="MCP Server: hỗ trợ tra cứu quy chế, khiếu nại và tính điểm rèn luyện",
)


@mcp_server.tool()
def hello(name: str) -> str:
    """Chào 1 ai đó theo tên của họ truyền vào"""
    log.info("Hàm hello() được gọi bởi %r", name)
    return f"Xin chào {name}! Chúc 1 ngày tốt lành."


@mcp_server.tool()
def submit_appeal(student_id: str, reason: str, category: str) -> str:
    """
    Nộp hồ sơ khiếu nại điểm rèn luyện cho một sinh viên. Đây là tool GHI:
    mỗi lần gọi sẽ tạo thêm một hồ sơ mới, nên chỉ gọi khi sinh viên đã nói rõ
    muốn khiếu nại và đã nêu lý do.

    Args:
        student_id: Mã sinh viên, ví dụ "SV001".
        reason: Lý do khiếu nại, mô tả ngắn gọn vì sao sinh viên cho rằng điểm sai.
        category: Mục điểm bị khiếu nại, ví dụ "chinh_tri_xa_hoi".

    Returns:
        "Đã tạo khiếu nại #<appeal_id>, trạng thái: pending". Dùng appeal_id
        trong kết quả này để tra lại hồ sơ bằng get_appeal_status.
        Lỗi thì trả chuỗi bắt đầu bằng "Error: ".
    """
    log.info(
        "submit_appeal() được gọi: student_id=%r, category=%r", student_id, category
    )
    try:
        return Appeal.submit_appeal(student_id, reason, category)
    except Exception as error:
        log.error(f"submit_appeal() lỗi: {error}")
        return f"Error: Không nộp được đơn thiếu nại: {error}"


if __name__ == "__main__":
    mcp_server.run()
