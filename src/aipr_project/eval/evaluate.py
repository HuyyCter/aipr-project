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
    return contexts


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


def run_ragas(test_set: list[TestCase]):
    """Run the agent on every question and evaluate with RAGAS."""
    run_id, answers = asyncio.run(ask_all(test_set))
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
        run_config=RunConfig(timeout=30, max_retries=1),
        raise_exceptions=True,
    )


if __name__ == "__main__":
    # chat = ChatOpenAI(
    #     model="openai/gpt-oss-20b",
    #     base_url="https://api.groq.com/openai/v1",
    #     api_key=os.getenv("GROQ_API_KEY"),
    #     temperature=0,
    #     reasoning_effort="low",
    # )
    # resp = chat.invoke(
    #     "Liệt kê 5 điều trong một quy chế rèn luyện sinh viên, mỗi điều một dòng."
    # )
    # print(resp.response_metadata.get("finish_reason"), resp.usage_metadata)
    test_set = [line for line in load_testset() if line.ground_truth]
    print(f"Đánh giá {len(test_set)} câu có ground-truth.")

    score = run_ragas(test_set)

    df = score.to_pandas()
    df.to_json(OUTPUT_JSON, index=False, orient="records", force_ascii=False, indent=4)
