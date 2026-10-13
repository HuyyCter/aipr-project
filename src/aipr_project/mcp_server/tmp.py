import json
import logging
import sys
from pathlib import Path

from mcp.server.mcpserver import MCPServer


PROJECT_ROOT = Path(__file__).resolve().parents[3]
LOG_PATH = PROJECT_ROOT / "logs" / "server" / "server.log"
RUBRIC_PATH = PROJECT_ROOT / "data" / "rubric.json"

NOT_FOUND_MESSAGE = "Không tìm thấy nội dung liên quan trong tài liệu."
MAX_DOCUMENT_CHARS = 800

with open(RUBRIC_PATH, "r", encoding="utf-8") as f:
    RUBRIC = json.load(f)
print(RUBRIC)
