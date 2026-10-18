"""Đánh giá RAG bằng RAGAS.

Mỗi câu trong testset (có ground_truth) chạy qua agent/MCP client:
  answer   = câu trả lời cuối của agent
  contexts = các chunk agent lấy được từ search_regulations / get_document
Sau đó gom thành Dataset của RAGAS rồi tính 4 metric.
"""

import asyncio
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from datasets import Dataset
from dotenv import load_dotenv
from langchain_core.embeddings import Embeddings
from langchain_openai import ChatOpenAI
from ragas import RunConfig, evaluate
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import (
    answer_relevancy,
    context_precision,
    context_recall,
    faithfulness,
)

from aipr_project.agent.logger import generate_run_id, read_run_log
from aipr_project.agent.loop import run_agent
from aipr_project.agent.mcp_client import *
from aipr_project.rag.embeddings import batch_embed_key, embed_key

load_dotenv()
PROJECT_ROOT = Path(__file__).resolve().parents[3]
TEST_SET = PROJECT_ROOT / "tests" / "testset.jsonl"
OUTPUT_JSON = PROJECT_ROOT / "logs" / "rag_evaluation.json"
OUTPUT_CSV = PROJECT_ROOT / "logs" / "csv" / "rag_evaluation.csv"
CHUNK_SEP = re.compile(r"\n={5,}\n")


# ======================== TEST SET ========================
@dataclass
class TestCase:
    id: str
    question: str
    type: str
    expected_doc_ids: list[str] = field(default_factory=list)
    ground_truth: str = ""


def load_testset() -> list[TestCase]:
    with open(TEST_SET, "r", encoding="utf-8") as f:
        data = [TestCase(**json.loads(line)) for line in f if line.strip()]
    return data


def get_contexts(run_log: list[dict], question_id: str) -> list[str]:
    """Lấy nội dung các chunk agent đã đọc cho 1 câu hỏi (bỏ dòng header [DOC...])."""
    contexts = []
    for line in run_log:
        if (
            line.get("question_id") != question_id
            or line.get("step_type") != "tool_result"
            or line.get("tool_name") != "search_regulations"
        ):
            continue
        text = line.get("result") or ""
        if text.startswith(("Error", "Không tìm thấy")):
            continue
        for chunk in CHUNK_SEP.split(text):
            header, _, rest = chunk.partition("\n")
            body = rest if header.startswith("[DOC") else chunk
            contexts.append(body.strip())
    return list(dict.fromkeys(contexts))


async def ask_all(test_set: list[TestCase]) -> tuple[str, list[str]]:
    """Chạy từng câu hỏi qua MCP client, trả (run_id, danh sách answer)."""
    run_id = generate_run_id()
    answers = []
    session = await connect()
    try:
        for line in test_set:
            try:
                answer = await run_agent(
                    question=line.question,
                    session=session,
                    run_id=run_id,
                    question_id=line.id,
                )
            except Exception as error:
                answer = f"Error: Agent lỗi: {error}"
            answers.append(answer)
    finally:
        await close()
    return run_id, answers


# ======================== RAGAS EVALUATION ========================
class JinaEmbeddings(Embeddings):
    def embed_documents(self, texts):
        return batch_embed_key(texts)

    def embed_query(self, text):
        return embed_key(text)


def get_ragas_models():
    llm = LangchainLLMWrapper(
        ChatOpenAI(
            model="openai/gpt-oss-120b",
            base_url="https://api.groq.com/openai/v1",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0,
            max_retries=5,
            reasoning_effort="low",
        )
    )
    return llm, LangchainEmbeddingsWrapper(JinaEmbeddings())


def build_ragas_dataset(
    test_set: list[TestCase], answers: list[str], source_list: list[list[str]]
) -> Dataset:
    """Convert evaluation results into a RAGAS Dataset."""
    data = {
        "question": [line.question for line in test_set],
        "answer": answers,
        "contexts": source_list,
        "ground_truth": [line.ground_truth for line in test_set],
    }
    return Dataset.from_dict(data)


def score_answers(test_set: list[TestCase], answers: list[str], run_id: str):
    """Chấm RAGAS trên answers đã có sẵn (không chạy lại agent)."""
    run_log = read_run_log(run_id)
    llm, embeddings = get_ragas_models()
    answer_relevancy.strictness = 1

    source_list = [
        get_contexts(run_log, line.id) or ["Không có context"] for line in test_set
    ]
    dataset = build_ragas_dataset(test_set, answers, source_list)

    return evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        llm=llm,
        embeddings=embeddings,
        run_config=RunConfig(timeout=300, max_retries=3, max_workers=1),
        raise_exceptions=False,  # 1 job lỗi -> NaN, không chết cả lượt
    )


def run_ragas(test_set: list[TestCase]):
    run_id, answers = asyncio.run(ask_all(test_set))
    return score_answers(test_set, answers, run_id)


# ======================== REPORT: usage + tỉ lệ từ chối ========================
METRICS = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]

REFUSAL_MARKERS = (
    "không tìm thấy",
    "không đề cập",
    "không có thông tin",
    "không có quy định",
    "chỉ hỗ trợ",
    "ngoài phạm vi",
    "không thuộc phạm vi",
    "couldn't find",
    "could not find",
    "not found",
    "no information",
    "not covered",
    "outside the scope",
    "only support",
    "only help",
)


def is_agent_error(answer: str) -> bool:
    return answer.startswith("Error") or answer.startswith("Đã vượt quá số bước")


def is_refusal(answer: str) -> bool:
    text = answer.lower()
    return any(marker in text for marker in REFUSAL_MARKERS)


def usage_per_question(run_log: list[dict], question_id: str) -> dict:
    calls = prompt = completion = max_prompt = tool_calls = 0
    for line in run_log:
        if line.get("question_id") != question_id:
            continue
        if line.get("step_type") == "tool_call":
            tool_calls += 1
        elif line.get("step_type") == "llm_call":
            usage = line.get("usage") or {}
            p = usage.get("prompt_tokens", 0)
            calls += usage.get("calls", 1)
            prompt += p
            completion += usage.get("completion_tokens", 0)
            max_prompt = max(max_prompt, p)
    return {
        "calls": calls,
        "tool_calls": tool_calls,
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "max_prompt": max_prompt,
    }


def _num(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return None if number != number else round(number, 4)  # NaN -> None


def _mean(values):
    values = [v for v in values if v is not None]
    return round(sum(values) / len(values), 4) if values else None


def build_report(
    test_set: list[TestCase],
    answers: list[str],
    run_log: list[dict],
    run_id: str,
    scored_ids: list[str],
    ragas_df=None,
) -> dict:
    """Gom kết quả từng câu + tổng kết. ragas_df=None nếu chưa/không chấm được."""
    ragas_by_id = {}
    if ragas_df is not None:
        for qid, (_, row) in zip(scored_ids, ragas_df.iterrows()):
            ragas_by_id[qid] = {m: _num(row.get(m)) for m in METRICS}

    rows = []
    for case, answer in zip(test_set, answers):
        error = is_agent_error(answer)
        rows.append(
            {
                "id": case.id,
                "type": case.type,
                "question": case.question,
                "answer": answer,
                "agent_error": error,
                "refused": False if error else is_refusal(answer),
                "usage": usage_per_question(run_log, case.id),
                "ragas": ragas_by_id.get(case.id),
            }
        )

    no_answer = [r for r in rows if r["type"] == "no_answer"]
    correct_refusals = [r for r in no_answer if r["refused"]]
    answerable = [r for r in rows if r["type"] in ("direct", "synthesis")]
    false_refusals = [r for r in answerable if r["refused"]]
    usages = [r["usage"] for r in rows]

    summary = {
        "run_id": run_id,
        "n_questions": len(rows),
        "agent_errors": [r["id"] for r in rows if r["agent_error"]],
        "ragas_scored_ids": list(ragas_by_id),
        "ragas_mean": {m: _mean([v[m] for v in ragas_by_id.values()]) for m in METRICS},
        "refusal": {
            "no_answer_total": len(no_answer),
            "correct_refusals": len(correct_refusals),
            "correct_refusal_rate": (
                round(len(correct_refusals) / len(no_answer), 4) if no_answer else None
            ),
            "false_refusals_on_answerable": [r["id"] for r in false_refusals],
        },
        "usage": {
            "total_calls": sum(u["calls"] for u in usages),
            "total_prompt_tokens": sum(u["prompt_tokens"] for u in usages),
            "total_completion_tokens": sum(u["completion_tokens"] for u in usages),
            "max_prompt": max((u["max_prompt"] for u in usages), default=0),
        },
    }
    return {"summary": summary, "questions": rows}
