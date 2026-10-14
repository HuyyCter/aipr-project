"""Entry point terminal: spawn MCP server (stdio) + chạy agent loop.

Dùng:
    uv run python src/aipr_project/main.py                  # chat tương tác
    uv run python src/aipr_project/main.py "câu hỏi..."     # hỏi 1 câu rồi thoát
"""

import asyncio
import sys

from aipr_project.agent import mcp_client
from aipr_project.agent.logger import generate_run_id
from aipr_project.agent.loop import run_agent

EXIT_WORDS = {"exit", "quit", "thoat", "thoát"}


async def ask(
    question: str,
    session,
    run_id: str,
    question_id: str,
    history: list[dict] | None = None,
) -> str | None:
    """Gọi agent, không để lỗi làm chết chương trình."""
    try:
        return await run_agent(
            question,
            session,
            history=history,
            run_id=run_id,
            question_id=question_id,
        )
    except Exception as error:
        print(f"\nError: agent lỗi: {error}", file=sys.stderr)
        return None


async def main() -> None:
    run_id = generate_run_id()
    one_shot = " ".join(sys.argv[1:]).strip()

    session = await mcp_client.connect()
    try:
        # Chế độ 1 câu: dùng cho demo nhanh / test
        if one_shot:
            answer = await ask(one_shot, session, run_id, "interactive_1")
            if answer is not None:
                print(f"\nTrợ lý: {answer}")
            print(f"\n[log] logs/run_{run_id}.jsonl")
            return

        # Chế độ chat tương tác
        print(f"Trợ lý điểm rèn luyện (run_id={run_id}). Gõ 'exit' để thoát.")
        history: list[dict] = []
        n = 0
        while True:
            try:
                question = input("\nBạn: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not question:
                continue
            if question.lower() in EXIT_WORDS:
                break

            n += 1
            answer = await ask(question, session, run_id, f"interactive_{n}", history)
            if answer is None:
                continue

            print(f"\nTrợ lý: {answer}")
            history.append({"role": "user", "content": question})
            history.append({"role": "assistant", "content": answer})

        print(f"\n[log] logs/run_{run_id}.jsonl")
    finally:
        await mcp_client.close()


if __name__ == "__main__":
    asyncio.run(main())
