"""Entry point terminal: spawn MCP server (stdio) + chạy agent loop.

Dùng:
    uv run python src/aipr_project/main.py                  # chat tương tác
    uv run python src/aipr_project/main.py "câu hỏi..."     # hỏi 1 câu rồi thoát
"""

import asyncio
import json
import sys

from aipr_project.agent import mcp_client
from aipr_project.agent.logger import generate_run_id, read_run_log
from aipr_project.agent.loop import run_agent
from aipr_project.eval.evaluate import (
    OUTPUT_JSON,
    build_report,
    is_agent_error,
    load_testset,
    score_answers,
)

EXIT_WORDS = {"exit", "quit", "thoat", "thoát"}


def save_report(report: dict) -> None:
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )


async def run_eval() -> None:
    """Chạy lần lượt testset theo đúng pattern của chat, rồi chấm điểm."""
    run_id = generate_run_id()
    test_set = load_testset()
    answers: list[str] = []

    session = await mcp_client.connect()
    try:
        for i, case in enumerate(test_set, 1):
            print(f"[{i}/{len(test_set)}] {case.id}: {case.question}")
            answer = await ask(case.question, session, run_id, case.id)
            answers.append(answer or "Error: agent lỗi")
            print(f"  -> {answers[-1][:120]}...\n")
    finally:
        await mcp_client.close()

    run_log = read_run_log(run_id)

    # Lưu ngay (chưa có RAGAS) để lỡ RAGAS lỗi vẫn còn số liệu
    save_report(build_report(test_set, answers, run_log, run_id, []))
    print(f"[log] {OUTPUT_JSON} (chưa có RAGAS)")

    # RAGAS chỉ chấm câu có ground_truth và agent không lỗi
    scored = [
        (c, a)
        for c, a in zip(test_set, answers)
        if c.ground_truth and not is_agent_error(a)
    ]
    ragas_df, scored_ids = None, []
    if scored:
        cases = [c for c, _ in scored]
        scored_ids = [c.id for c in cases]
        print(f"\nChấm RAGAS {len(scored)} câu...")
        try:
            result = await asyncio.to_thread(
                score_answers, cases, [a for _, a in scored], run_id
            )
            ragas_df = result.to_pandas()
        except Exception as error:
            print(f"RAGAS lỗi: {error}", file=sys.stderr)

    report = build_report(test_set, answers, run_log, run_id, scored_ids, ragas_df)
    save_report(report)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"[log] {OUTPUT_JSON}")


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
    if "--eval" in sys.argv:
        await run_eval()
        return

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
