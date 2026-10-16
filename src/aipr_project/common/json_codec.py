
"""JSON serialization helpers for RAG documents and chunks."""

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from aipr_project.rag.models import Document, DocumentChunk


def document_to_dict(document: Document) -> dict[str, Any]:
    """Convert a Document to a JSON-compatible dictionary."""
    return asdict(document)


def document_from_dict(data: dict[str, Any]) -> Document:
    """Create a Document from a dictionary."""
    return Document(
        doc_id=data["doc_id"],
        title=data["title"],
        content=data["content"],
        version=data["version"],
        date=data.get("date", ""),
        owner=data.get("owner", ""),
        metadata=data.get("metadata", {}),
    )


def chunk_to_dict(chunk: DocumentChunk) -> dict[str, Any]:
    """Convert a DocumentChunk to a JSON-compatible dictionary."""
    return asdict(chunk)


def chunk_from_dict(data: dict[str, Any]) -> DocumentChunk:
    """Create a DocumentChunk from a dictionary."""
    embedding = data.get("embedding")

    return DocumentChunk(
        chunk_id=data["chunk_id"],
        doc_id=data["doc_id"],
        content=data["content"],
        chunk_index=int(data["chunk_index"]),
        embedding=(
            [float(value) for value in embedding]
            if embedding is not None
            else None
        ),
        metadata=data.get("metadata", {}),
    )


def save_json(path: str | Path, data: Any) -> None:
    """Save data to a UTF-8 JSON file."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )


def load_json(path: str | Path) -> Any:
    """Load JSON data from a UTF-8 JSON file."""
    input_path = Path(path)

    with input_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_chunks(path: str | Path, chunks: list[DocumentChunk]) -> None:
    """Save a list of chunks to JSON."""
    save_json(path, [chunk_to_dict(chunk) for chunk in chunks])


def load_chunks(path: str | Path) -> list[DocumentChunk]:
    """Load chunks from JSON."""
    data = load_json(path)

    if not isinstance(data, list):
        raise ValueError("Chunk cache must contain a JSON list.")

    return [chunk_from_dict(item) for item in data]
