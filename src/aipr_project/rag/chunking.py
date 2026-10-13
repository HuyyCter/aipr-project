
import re

from aipr_project.rag.models import Document, DocumentChunk


def remove_table_of_contents(text: str) -> str:
    """Loại bỏ phần mục lục Markdown."""

    pattern = (
        r"^#{1,6}\s*MỤC\s*LỤC\s*$"
        r".*?"
        r"(?=^#\s|\Z)"
    )

    return re.sub(
        pattern,
        "",
        text,
        count=1,
        flags=re.MULTILINE | re.DOTALL | re.IGNORECASE,
    ).strip()


def split_long_text(text: str, chunk_size: int) -> list[str]:
    """Chia văn bản dài mà không bỏ mất ký tự."""

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))

        if end < len(text):
            # Ưu tiên ngắt ở cuối dòng hoặc cuối câu.
            candidates = [
                text.rfind("\n", start, end),
                text.rfind(". ", start, end),
                text.rfind("? ", start, end),
                text.rfind("! ", start, end),
                text.rfind(" ", start, end),
            ]

            split_at = max(candidates)

            # Chỉ ngắt nếu tìm được vị trí phù hợp.
            if split_at > start:
                end = split_at + 1

        part = text[start:end].strip()

        if part:
            chunks.append(part)

        # Không bỏ qua phần văn bản chưa được xử lý.
        start = end

    return chunks


def chunk_documents(
    doc: Document,
    chunk_size: int = 512,
    overlap: int = 64,
) -> list[DocumentChunk]:
    """Chia tài liệu theo heading và nội dung."""

    if chunk_size <= 0:
        raise ValueError("chunk_size phải lớn hơn 0")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap phải từ 0 đến nhỏ hơn chunk_size")

    text = remove_table_of_contents(doc.content.strip())

    # Chia theo từng dòng để nhận diện heading chính xác.
    lines = text.splitlines()

    sections = []
    headings = []
    paragraph_lines = []

    def save_paragraph():
        """Lưu đoạn hiện tại cùng ngữ cảnh heading."""
        nonlocal paragraph_lines

        paragraph = "\n".join(paragraph_lines).strip()
        paragraph_lines = []

        if not paragraph:
            return

        heading_text = "\n".join(
            heading for _, heading in headings
        )

        if heading_text:
            sections.append(f"{heading_text}\n{paragraph}")
        else:
            sections.append(paragraph)

    for line in lines:
        stripped = line.strip()

        # Nhận diện heading Markdown ở đầu dòng.
        match = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", stripped)

        if match:
            save_paragraph()

            level = len(match.group(1))

            # Giữ heading cha, bỏ heading cùng cấp hoặc thấp hơn.
            headings[:] = [
                (old_level, heading)
                for old_level, heading in headings
                if old_level < level
            ]

            headings.append((level, stripped))
            continue

        if not stripped:
            save_paragraph()
        else:
            paragraph_lines.append(stripped)

    save_paragraph()

    # Chia những section vượt giới hạn.
    pieces = []

    for section in sections:
        if len(section) <= chunk_size:
            pieces.append(section)
        else:
            pieces.extend(split_long_text(section, chunk_size))

    # Gộp các đoạn nhỏ nếu không vượt chunk_size.
    merged = []

    for piece in pieces:
        if (
            merged
            and len(merged[-1]) + len(piece) + 2 <= chunk_size
        ):
            merged[-1] += "\n\n" + piece
        else:
            merged.append(piece)

    # Tạo DocumentChunk, giữ nguyên cấu trúc dữ liệu hiện tại.
    chunks = []

    for i, piece in enumerate(merged):
        content = piece

        # Thêm phần cuối của chunk trước làm overlap.
        if i > 0 and overlap > 0:
            previous = merged[i - 1]
            tail = previous[-overlap:]

            if tail and not content.startswith(tail):
                candidate = tail + "\n" + content

                # Không vượt giới hạn chunk_size.
                if len(candidate) <= chunk_size:
                    content = candidate

        chunks.append(
            DocumentChunk(
                chunk_id=f"{doc.doc_id}_{i}",
                doc_id=doc.doc_id,
                title=doc.title,
                version=doc.version,
                content=content,
                date=doc.date,
                owner=doc.owner,
                metadata=doc.metadata,
            )
        )

    return chunks
