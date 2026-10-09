import asyncio
import os
import sys
from contextlib import AsyncExitStack
from pathlib import Path

from dotenv import load_dotenv
from mcp import Client, StdioServerParameters
from mcp_types import Tool

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SERVER_PATH = PROJECT_ROOT / "src" / "mcp_server" / "server.py"

_stack = AsyncExitStack()


async def connect() -> Client:
    """Tạo MCP Server"""
    load_dotenv()
    server = StdioServerParameters(
        command=sys.executable,
        args=[SERVER_PATH],
        cwd=PROJECT_ROOT,
        env={**os.environ, "PYTHONPATH": PROJECT_ROOT},
    )
    return _stack.enter_async_context(Client(server))


async def discover(session: Client) -> list[Tool]:
    tools = (await session.list_tools()).tools
    print(f"Discovered {len(tools)} tools:")
    for tool in tools:
        description = tool.description or "(no description)"
        print(f"- {tool.name}: {description.splitlines()[0]}")
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


if __name__ == "__main__":
    asyncio.run(main())
