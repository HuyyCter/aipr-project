
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Document:
    """Tai lieu nguon trong he thong RAG."""

    doc_id: str
    title: str
    content: str
    version: str
    date: str = ""
    owner: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DocumentChunk:
    """Mot chunk duoc tach ra tu tai lieu nguon."""
    chunk_id: str
    doc_id: str
    content: str
    chunk_index: int
    embedding: list[float] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
