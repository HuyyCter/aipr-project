from aipr_project.rag.jina_embeddings import jina_embeddings
import os
from rich import print
from dotenv import load_dotenv
import numpy as np

load_dotenv()


def embed_key(
    text: str,
    model="jina-embeddings-v3",
    api_key=None
) -> list[float]:

    if api_key is None:
        api_key = os.getenv("JINA_API_KEY")

    resp = jina_embeddings(
        input=text,
        model=model,
        api_key=api_key
    )

    return resp.data[0].embedding


def batch_embed_key(
    texts: list[str],
    model="jina-embeddings-v3",
    api_key=None
) -> list[list[float]]:

    if api_key is None:
        api_key = os.getenv("JINA_API_KEY")

    resp = jina_embeddings(
        input=texts,
        model=model,
        api_key=api_key
    )

    return [
        item.embedding
        for item in resp.data
    ]


def cosine_similiarity(
    a: list[float],
    b: list[float]
):
    return np.dot(a, b) / (
        np.linalg.norm(a) *
        np.linalg.norm(b)
    )


