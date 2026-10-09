import logging
import sys
from pathlib import Path

from mcp.server.mcpserver import MCPServer

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
    return f"Xin chào {name}! Chúc 1 ngày tốt lành."


if __name__ == "__main__":
    mcp_server.run()
