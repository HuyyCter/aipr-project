from dataclasses import dataclass, field
from typing import Any


@dataclass
class Document:
    """Tai lieu nguon tu he thong RAG"""

    doc_id: str
    title: str
    version: str
    content: str
    date: str = ""
    owner: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DocumentChunk:
    """Mot doan noi dung tu nguon RAG do"""

    chunk_id: str
    doc_id: str
    title: str
    version: str
    content: str
    date: str = ""
    owner: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)