import asyncio
import os
import re
import sys
from contextlib import AsyncExitStack
from pathlib import Path

from dotenv import load_dotenv
from mcp import Client, StdioServerParameters
from mcp_types import Tool

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SERVER_PATH = PROJECT_ROOT / "src" / "aipr_project" / "mcp_server" / "server.py"

_stack = AsyncExitStack()


async def connect() -> Client:
    """Tạo MCP Server"""
    load_dotenv()
    server = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER_PATH)],
        cwd=str(PROJECT_ROOT),
        env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT)},
    )
    return await _stack.enter_async_context(Client(server))


async def discover(session: Client) -> list[Tool]:
    tools = (await session.list_tools()).tools
    print(f"Discovered {len(tools)} tools: {[tool.name for tool in tools]}")
    return tools


async def call(session: Client, tool_name: str, args: dict) -> str:
    try:
        result = await session.call_tool(tool_name, args)
    except Exception as exception:
        return f"Error: không gọi được tool {tool_name}: {exception}"

    text = "\n".join(block.text for block in result.content if block.type == "text")
    if result.is_error:
        text = f"Error: {text}"
    return text


async def close() -> None:
    await _stack.aclose()


async def main():
    session = await connect()
    try:
        tools = await discover(session)
        for tool in tools:
            description = tool.description or "(no description)"
            print(f"- {tool.name}: {description.splitlines()[0]}")
            print(f"    + schema: {tool.input_schema}\n")

        # CALL TOOLS
        # GHI -> VERIFY
        print("\n" + "=" * 60)
        submitted = await call(
            session,
            "submit_appeal",
            {
                "student_id": "SV001",
                "reason": "Thiếu minh chứng hoạt động tình nguyện",
                "category": "chinh_tri_xa_hoi",
            },
        )
        print(submitted)

        match = re.search(r"#(\w+)", submitted)
        if match:
            print(
                await call(session, "get_appeal_by_id", {"appeal_id": match.group(1)})
            )

        # id không tồn tại -> phải ra "Error: ...", không crash
        print(await call(session, "get_appeal_by_id", {"appeal_id": "khongco"}))

        print(await call(session, "list_appeals", {"student_id": "SV001"}))
        print(await call(session, "list_appeals", {"student_id": "Huy"}))
    finally:
        await close()


if __name__ == "__main__":
    asyncio.run(main())
