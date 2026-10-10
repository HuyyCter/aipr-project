import asyncio
import os
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
    print(f"Discovered {len(tools)} tools:")
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
        print("\n" + "=" * 60)
        print(
            await call(
                session,
                "submit_appeal",
                {
                    "student_id": "24110095",
                    "reason": "Điểm rèn luyện ngày 6/10/2026 chưa được cộng",
                    "category": "tham_gia_su_kien",
                },
            )
        )
    finally:
        await close()


if __name__ == "__main__":
    asyncio.run(main())
