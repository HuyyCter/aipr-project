
"""Shared embedding utilities for the RAG system."""

import os

import numpy as np
from dotenv import load_dotenv

from aipr_project.rag.jina_embeddings import jina_embeddings

load_dotenv()

DEFAULT_EMBEDDING_MODEL = "jina-embeddings-v3"
DEFAULT_DOCUMENT_TASK = "retrieval.passage"
DEFAULT_QUERY_TASK = "retrieval.query"


def _get_api_key(api_key: str | None = None) -> str:
    """Get the Jina API key from an argument or environment."""
    key = api_key or os.getenv("JINA_API_KEY")

    if not key:
        raise RuntimeError(
            "Thiếu JINA_API_KEY. Hãy kiểm tra file .env."
        )

    return key


def _validate_task(task: str) -> None:
    """Validate the supported Jina retrieval tasks."""
    if task not in {
        DEFAULT_DOCUMENT_TASK,
        DEFAULT_QUERY_TASK,
    }:
        raise ValueError(
            "task phải là 'retrieval.passage' hoặc 'retrieval.query'."
        )


def embed_key(
    text: str,
    model: str = DEFAULT_EMBEDDING_MODEL,
    api_key: str | None = None,
    task: str = DEFAULT_QUERY_TASK,
) -> list[float]:
    """Create an embedding for one text."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("text không được rỗng.")

    _validate_task(task)
    key = _get_api_key(api_key)

    response = jina_embeddings(
        input=text,
        model=model,
        api_key=key,
        task=task,
    )

    if not response.data or not response.data[0].embedding:
        raise RuntimeError("Jina không trả về embedding hợp lệ.")

    return [float(value) for value in response.data[0].embedding]


def batch_embed_key(
    texts: list[str],
    model: str = DEFAULT_EMBEDDING_MODEL,
    api_key: str | None = None,
    task: str = DEFAULT_DOCUMENT_TASK,
) -> list[list[float]]:
    """Create embeddings for a batch of texts."""
    if not texts:
        return []

    if any(not isinstance(text, str) or not text.strip() for text in texts):
        raise ValueError("Danh sách texts chứa nội dung rỗng hoặc không hợp lệ.")

    _validate_task(task)
    key = _get_api_key(api_key)

    response = jina_embeddings(
        input=texts,
        model=model,
        api_key=key,
        task=task,
    )

    if len(response.data) != len(texts):
        raise RuntimeError(
            "Số embedding trả về không khớp số văn bản đầu vào."
        )

    vectors = [
        [float(value) for value in item.embedding]
        for item in response.data
    ]

    if any(not vector for vector in vectors):
        raise RuntimeError("Jina trả về embedding rỗng.")

    return vectors


def cosine_similiarity(
    a: list[float],
    b: list[float],
) -> float:
    """Calculate cosine similarity between two vectors."""
    if len(a) != len(b):
        raise ValueError("Hai vector phải có cùng số chiều.")

    vector_a = np.asarray(a, dtype=np.float32)
    vector_b = np.asarray(b, dtype=np.float32)

    denominator = np.linalg.norm(vector_a) * np.linalg.norm(vector_b)

    if denominator == 0:
        return 0.0

    return float(np.dot(vector_a, vector_b) / denominator)
