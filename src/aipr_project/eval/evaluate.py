"""Module Đánh Giá Hệ Thống Agentic RAG (Week 5 Evaluation).

Nhiệm vụ:
- Đọc bộ câu hỏi kiểm thử từ `tests/testset.jsonl`.
- Chạy từng câu hỏi qua Agent thật (kết nối MCP Server thật qua stdio).
- Đọc log trace từ `logs/run_<run_id>.jsonl` để trích xuất:
    + Ngữ cảnh đã truy hồi (Retrieved Context từ tool search/get_document).
    + Tài nguyên tiêu thụ: số lượt gọi LLM, prompt/completion tokens, chi phí ước tính.
- Đánh giá chất lượng:
    + Với câu hỏi thông thường (direct, synthesis, calc, action): Chấm Faithfulness bằng LLM-as-a-judge
      theo prompt `prompts/judge.txt`.
    + Với câu hỏi ngoài phạm vi (no_answer): Đo tỉ lệ từ chối đúng (Correct Refusal Rate).
    + Đo Retrieval Hit Rate đối chiếu với expected_doc_ids.
- Xuất báo cáo chi tiết ra CSV (`logs/eval_report.csv`) và in bảng tóm tắt ra terminal.
"""

import argparse
import asyncio
import csv
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

from rich.console import Console
from rich.table import Table

from aipr_project.agent import mcp_client
from aipr_project.agent.logger import generate_run_id, read_run_log
from aipr_project.agent.loop import run_agent
from aipr_project.common.llm_client import LLMClient, estimate_cost

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TESTSET_PATH = PROJECT_ROOT / "tests" / "testset.jsonl"
DEFAULT_OUTPUT_CSV = PROJECT_ROOT / "logs" / "eval_report.csv"
JUDGE_PROMPT_PATH = PROJECT_ROOT / "prompts" / "judge.txt"

REFUSAL_KEYWORDS = [
    "không tìm thấy",
    "không đề cập",
    "ngoài phạm vi",
    "không có thông tin",
    "tài liệu hiện có không",
    "chưa có quy định",
    "không thuộc quy chế",
    "không quy định",
    "chưa tìm thấy",
]


@dataclass
class EvalResult:
    question_id: str
    type: str
    question: str
    answer: str
    faithfulness: Optional[float]
    refused_correctly: Optional[int]  # 1 nếu đúng, 0 nếu sai, None nếu không phải no_answer
    retrieval_hit: Optional[float]
    num_llm_calls: int
    prompt_tokens: int
    completion_tokens: int
    total_cost_estimate: float


def load_judge_prompt() -> str:
    """Đọc template prompt judge từ file txt."""
    if not JUDGE_PROMPT_PATH.exists():
        raise FileNotFoundError(f"Không tìm thấy file prompt judge tại: {JUDGE_PROMPT_PATH}")
    return JUDGE_PROMPT_PATH.read_text(encoding="utf-8")


def parse_judge_json(raw_text: str) -> dict[str, Any]:
    """Parse an toàn kết quả JSON do LLM Judge trả về."""
    clean_text = raw_text.strip()
    # Bóc tách code block ```json ... ``` nếu có
    if "```" in clean_text:
        match = re.search(r"```(?:json)?\s*(.*?)\s*```", clean_text, re.DOTALL)
        if match:
            clean_text = match.group(1).strip()

    try:
        return json.loads(clean_text)
    except Exception:
        # Fallback bằng regex nếu JSON bị hỏng nhẹ
        score_match = re.search(r'"faithfulness_score":\s*([0-9\.]+)', clean_text)
        if score_match:
            try:
                score = float(score_match.group(1))
                return {"faithfulness_score": min(1.0, max(0.0, score)), "claims": []}
            except ValueError:
                pass
        return {"faithfulness_score": 0.0, "claims": [], "error": "JSON parse error"}


def judge_faithfulness(
    client: LLMClient,
    judge_prompt_template: str,
    question: str,
    context: str,
    answer: str,
) -> float:
    """Gọi LLM-as-a-judge chấm độ trung thực (Faithfulness) của câu trả lời dựa trên context."""
    if not context.strip():
        # Nếu không có context nào được lấy ra nhưng vẫn trả lời khẳng định sự thực
        return 0.0

    prompt = (
        judge_prompt_template
        .replace("{question}", question)
        .replace("{context}", context)
        .replace("{answer}", answer)
    )

    messages = [
        {"role": "system", "content": "You are a rigorous, unbiased evaluation judge."},
        {"role": "user", "content": prompt},
    ]

    try:
        response = client.chat(messages=messages, temperature=0.0)
        content = response.choices[0].message.content or "{}"
        parsed = parse_judge_json(content)
        score = float(parsed.get("faithfulness_score", 0.0))
        return min(1.0, max(0.0, score))
    except Exception as e:
        print(f"[Judge Error] Không thể chấm faithfulness cho câu hỏi: {e}", file=sys.stderr)
        return 0.0


def check_refusal(answer: str, retrieved_context: str) -> int:
    """Kiểm tra xem Agent có từ chối câu hỏi ngoài phạm vi (no_answer) đúng cách hay không."""
    combined = (answer + " " + retrieved_context).lower()
    for kw in REFUSAL_KEYWORDS:
        if kw in combined:
            return 1
    return 0


def calculate_retrieval_hit(expected_doc_ids: list[str], retrieved_context: str) -> Optional[float]:
    """Tính tỉ lệ retrieve trúng các doc_id kỳ vọng (Hit Rate)."""
    if not expected_doc_ids:
        return None
    hits = sum(1 for doc_id in expected_doc_ids if doc_id in retrieved_context)
    return round(hits / len(expected_doc_ids), 2)


def extract_trace_metrics(
    log_entries: list[dict[str, Any]], question_id: str
) -> tuple[str, int, int, int, float]:
    """Trích xuất context, số lượt gọi LLM, số token và chi phí từ file run log JSONL."""
    retrieved_chunks = []
    num_calls = 0
    prompt_tokens = 0
    completion_tokens = 0

    for entry in log_entries:
        if entry.get("question_id") != question_id:
            continue

        step_type = entry.get("step_type")
        tool_name = entry.get("tool_name")
        result = entry.get("result")
        usage = entry.get("usage")

        if step_type == "tool_result" and tool_name in {"search_regulations", "get_document"}:
            if result:
                retrieved_chunks.append(str(result))

        if step_type == "llm_call" and usage:
            num_calls += usage.get("calls", 1)
            prompt_tokens += usage.get("prompt_tokens", 0)
            completion_tokens += usage.get("completion_tokens", 0)

    context = "\n---\n".join(retrieved_chunks)
    cost = estimate_cost("openai/gpt-oss-20b", prompt_tokens, completion_tokens)
    return context, num_calls, prompt_tokens, completion_tokens, cost


async def run_eval(
    testset_path: Path = DEFAULT_TESTSET_PATH,
    out_csv: Path = DEFAULT_OUTPUT_CSV,
    limit: Optional[int] = None,
) -> list[EvalResult]:
    """Chạy toàn bộ quy trình đánh giá testset và xuất báo cáo."""
    console = Console()
    console.print(f"[bold cyan]=== BẮT ĐẦU ĐÁNH GIÁ HỆ THỐNG AGENTIC RAG (EVALUATE.PY) ===[/bold cyan]")
    console.print(f"Testset: [yellow]{testset_path}[/yellow]")
    console.print(f"Báo cáo CSV: [yellow]{out_csv}[/yellow]\n")

    if not testset_path.exists():
        raise FileNotFoundError(f"Không tìm thấy testset: {testset_path}")

    with open(testset_path, "r", encoding="utf-8") as f:
        test_items = [
            json.loads(line)
            for line in f
            if line.strip() and not line.strip().startswith(("#", "//"))
        ]

    if limit:
        test_items = test_items[:limit]

    judge_template = load_judge_prompt()
    judge_client = LLMClient()
    run_id = generate_run_id()

    eval_results: list[EvalResult] = []

    # Khởi tạo kết nối tới MCP Server thật qua stdio
    console.print("[dim]Đang khởi động MCP Server và kết nối session...[/dim]")
    session = await mcp_client.connect()

    try:
        for idx, item in enumerate(test_items, 1):
            q_id = item.get("id", f"q{idx:02d}")
            question = item.get("question", "")
            q_type = item.get("type", "direct")
            expected_docs = item.get("expected_doc_ids", [])

            console.print(
                f"[bold green][{idx}/{len(test_items)}][/bold green] "
                f"Đang chạy câu hỏi [bold]{q_id}[/bold] ({q_type}): \"{question}\"..."
            )

            # 1. Chạy qua Agent thật (agent loop)
            answer = await run_agent(
                question=question,
                session=session,
                run_id=run_id,
                question_id=q_id,
            )

            # 2. Đọc trace log sinh ra từ logger.py
            log_entries = read_run_log(run_id)
            context, num_calls, p_tokens, c_tokens, cost = extract_trace_metrics(log_entries, q_id)

            # 3. Đánh giá chất lượng
            faithfulness_score: Optional[float] = None
            refused_score: Optional[int] = None
            retrieval_hit: Optional[float] = None

            if q_type == "no_answer":
                refused_score = check_refusal(answer, context)
                faithfulness_score = None  # Không đo faithfulness cho câu no_answer
            else:
                faithfulness_score = judge_faithfulness(
                    client=judge_client,
                    judge_prompt_template=judge_template,
                    question=question,
                    context=context,
                    answer=answer,
                )
                retrieval_hit = calculate_retrieval_hit(expected_docs, context)

            eval_results.append(
                EvalResult(
                    question_id=q_id,
                    type=q_type,
                    question=question,
                    answer=answer,
                    faithfulness=faithfulness_score,
                    refused_correctly=refused_score,
                    retrieval_hit=retrieval_hit,
                    num_llm_calls=num_calls,
                    prompt_tokens=p_tokens,
                    completion_tokens=c_tokens,
                    total_cost_estimate=cost,
                )
            )

    finally:
        await mcp_client.close()

    # 4. Ghi kết quả ra CSV
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "question_id",
            "type",
            "faithfulness",
            "refused_correctly",
            "retrieval_hit",
            "num_llm_calls",
            "prompt_tokens",
            "completion_tokens",
            "total_cost_estimate",
        ])
        for r in eval_results:
            writer.writerow([
                r.question_id,
                r.type,
                f"{r.faithfulness:.2f}" if r.faithfulness is not None else "",
                r.refused_correctly if r.refused_correctly is not None else "",
                f"{r.retrieval_hit:.2f}" if r.retrieval_hit is not None else "",
                r.num_llm_calls,
                r.prompt_tokens,
                r.completion_tokens,
                f"{r.total_cost_estimate:.6f}",
            ])

    console.print(f"\n[bold green]✓ Đã xuất báo cáo CSV thành công tại: {out_csv}[/bold green]\n")

    # 5. In bảng tổng hợp kết quả (Summary Table)
    print_summary_table(console, eval_results)
    return eval_results


def print_summary_table(console: Console, results: list[EvalResult]) -> None:
    """Hiển thị bảng kết quả trực quan trên terminal."""
    table = Table(title="KẾT QUẢ ĐÁNH GIÁ HỆ THỐNG AGENTIC RAG", show_header=True, header_style="bold magenta")
    table.add_column("ID", style="dim", width=6)
    table.add_column("Type", width=12)
    table.add_column("Faithfulness", justify="right")
    table.add_column("Refusal", justify="center")
    table.add_column("Hit Rate", justify="right")
    table.add_column("Calls", justify="right")
    table.add_column("Prompt Tok", justify="right")
    table.add_column("Comp Tok", justify="right")
    table.add_column("Cost ($)", justify="right")

    faith_scores = []
    refusal_scores = []
    hit_scores = []
    total_calls = 0
    total_prompt_tok = 0
    total_comp_tok = 0
    total_cost = 0.0

    for r in results:
        faith_str = f"{r.faithfulness:.2f}" if r.faithfulness is not None else "-"
        if r.faithfulness is not None:
            faith_scores.append(r.faithfulness)

        refusal_str = str(r.refused_correctly) if r.refused_correctly is not None else "-"
        if r.refused_correctly is not None:
            refusal_scores.append(r.refused_correctly)

        hit_str = f"{r.retrieval_hit:.2f}" if r.retrieval_hit is not None else "-"
        if r.retrieval_hit is not None:
            hit_scores.append(r.retrieval_hit)

        total_calls += r.num_llm_calls
        total_prompt_tok += r.prompt_tokens
        total_comp_tok += r.completion_tokens
        total_cost += r.total_cost_estimate

        table.add_row(
            r.question_id,
            r.type,
            faith_str,
            refusal_str,
            hit_str,
            str(r.num_llm_calls),
            str(r.prompt_tokens),
            str(r.completion_tokens),
            f"${r.total_cost_estimate:.5f}",
        )

    # Dòng tổng hợp trung bình
    avg_faith = sum(faith_scores) / len(faith_scores) if faith_scores else 0.0
    refusal_rate = (sum(refusal_scores) / len(refusal_scores)) * 100 if refusal_scores else 0.0
    avg_hit = sum(hit_scores) / len(hit_scores) if hit_scores else 0.0

    table.add_section()
    table.add_row(
        "[bold]AVG[/bold]",
        f"[bold]{len(results)} câu[/bold]",
        f"[bold green]{avg_faith:.2f}[/bold green]",
        f"[bold cyan]{refusal_rate:.1f}%[/bold cyan]",
        f"[bold]{avg_hit:.2f}[/bold]",
        f"[bold]{total_calls}[/bold]",
        f"[bold]{total_prompt_tok}[/bold]",
        f"[bold]{total_comp_tok}[/bold]",
        f"[bold yellow]${total_cost:.5f}[/bold yellow]",
    )

    console.print(table)


def main() -> None:
    parser = argparse.ArgumentParser(description="Chạy đánh giá Agentic RAG qua testset")
    parser.add_argument("--testset", type=Path, default=DEFAULT_TESTSET_PATH, help="Đường dẫn file testset.jsonl")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_CSV, help="Đường dẫn file CSV kết quả")
    parser.add_argument("--limit", type=int, default=None, help="Giới hạn số câu test để chạy thử nhanh")
    args = parser.parse_args()

    asyncio.run(run_eval(testset_path=args.testset, out_csv=args.output, limit=args.limit))


if __name__ == "__main__":
    main()
