 
import re
from typing import Any

from aipr_project.rag.models import Document, DocumentChunk


DEFAULT_CHUNK_SIZE = 800
DEFAULT_OVERLAP = 100


def remove_table_of_contents(text: str) -> str:
    """Loại bỏ mục lục Markdown nếu có."""

    pattern = (
        r"^#{1,6}\s*MỤC\s*LỤC\s*$"
        r".*?"
        r"(?=^#{1,6}\s|\Z)"
    )

    return re.sub(
        pattern,
        "",
        text,
        count=1,
        flags=re.MULTILINE | re.DOTALL | re.IGNORECASE,
    ).strip()


def parse_front_matter(doc_source: str) -> tuple[dict[str, Any], str]:
    """
    Đọc YAML front matter ở đầu tài liệu.

    Trả về:
        (metadata_header, content)
    """

    text = doc_source.lstrip("\ufeff").strip()

    if not text.startswith("---"):
        raise ValueError(
            "Tài liệu thiếu YAML front matter bắt đầu bằng '---'."
        )

    lines = text.splitlines()

    if not lines or lines[0].strip() != "---":
        raise ValueError("Dòng đầu tiên phải là '---'.")

    end_index = None

    for i in range(1, len(lines)):
        if lines[i].strip() in ("---", "..."):
            end_index = i
            break

    if end_index is None:
        raise ValueError("Không tìm thấy dòng kết thúc front matter.")

    header = {}

    for line in lines[1:end_index]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue

        if ":" not in line:
            continue

        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()

        # Xử lý giá trị dạng chuỗi có dấu nháy.
        if (
            len(value) >= 2
            and value[0] == value[-1]
            and value[0] in ("'", '"')
        ):
            value = value[1:-1]

        header[key] = value

    content = "\n".join(lines[end_index + 1:]).strip()

    required_fields = ("doc_id", "title", "version")

    for field in required_fields:
        if not header.get(field):
            raise ValueError(
                f"Front matter thiếu trường bắt buộc: {field}"
            )

    return header, content


def parse_document(doc_source: str) -> Document:
    """Chuyển nội dung Markdown có front matter thành Document."""

    header, content = parse_front_matter(doc_source)

    return Document(
        doc_id=str(header["doc_id"]),
        title=str(header["title"]),
        content=content,
        version=str(header["version"]),
        date=str(header.get("date", "")),
        owner=str(header.get("owner", "")),
        metadata={
            key: value
            for key, value in header.items()
            if key not in {
                "doc_id",
                "title",
                "version",
                "date",
                "owner",
            }
        },
    )


def split_long_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[str]:
    """
    Chia văn bản dài, ưu tiên ranh giới dòng, câu và từ.

    Các chunk có overlap để giữ ngữ cảnh giữa các đoạn.
    """

    if chunk_size <= 0:
        raise ValueError("chunk_size phải lớn hơn 0.")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError(
            "overlap phải từ 0 đến nhỏ hơn chunk_size."
        )

    text = text.strip()

    if not text:
        return []

    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + chunk_size, text_length)

        if end < text_length:
            # Ưu tiên ngắt ở ranh giới dễ đọc.
            candidates = [
                text.rfind("\n", start, end),
                text.rfind(". ", start, end),
                text.rfind("? ", start, end),
                text.rfind("! ", start, end),
                text.rfind("; ", start, end),
                text.rfind(" ", start, end),
            ]

            split_at = max(candidates)

            # Chỉ chọn ranh giới nằm trong phần văn bản hiện tại.
            if split_at > start:
                end = split_at + 1

        part = text[start:end].strip()

        if part:
            chunks.append(part)

        if end >= text_length:
            break

        # Lùi lại một đoạn để tạo overlap.
        next_start = max(start + 1, end - overlap)

        # Tránh bắt đầu ngay giữa một từ nếu có thể.
        while (
            next_start < end
            and not text[next_start - 1].isspace()
            and not text[next_start].isspace()
        ):
            next_start += 1

        start = next_start

    return chunks



def split_by_articles(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[str]:
    """
    Chia văn bản theo Điều/Mục trong Markdown.
    Điều/Mục quá dài mới được chia nhỏ.
    """

    if chunk_size <= 0:
        raise ValueError("chunk_size phải lớn hơn 0.")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap phải từ 0 đến nhỏ hơn chunk_size.")

    text = remove_table_of_contents(text).strip()

    # Nhận diện tiêu đề Điều/Mục kể cả khi có Markdown:
    # ## **Điều 1\. Phạm vi...**
    # **Điều 3. Trách nhiệm...**
    pattern = re.compile(
        r"(?im)^[ \t]*"
        r"(?:#{1,6}[ \t]*)?"
        r"(?:\*\*[ \t]*)?"
        r"(?:Điều[ \t]+\d+[a-zA-Z]?|"
        r"Mục[ \t]+\d+(?:\.\d+)*[a-zA-Z]?)"
        r"(?:\\?\.[ \t]*|[ \t]+)"
        r".*$"
    )

    matches = list(pattern.finditer(text))

    if not matches:
        return split_long_text(text, chunk_size, overlap)

    sections = []

    # Giữ phần mở đầu trước Điều/Mục đầu tiên.
    prefix = text[:matches[0].start()].strip()
    if prefix:
        sections.append(prefix)

    for i, match in enumerate(matches):
        end = (
            matches[i + 1].start()
            if i + 1 < len(matches)
            else len(text)
        )
        section = text[match.start():end].strip()

        if section:
            sections.append(section)

    chunks = []
    current = ""

    for section in sections:
        if len(section) > chunk_size:
            if current:
                chunks.append(current)
                current = ""

            chunks.extend(
                split_long_text(section, chunk_size, overlap)
            )
            continue

        candidate = (
            f"{current}\n\n{section}" if current else section
        )

        if len(candidate) <= chunk_size:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = section

    if current:
        chunks.append(current)

    return chunks



def chunk_documents(
    doc: Document,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[DocumentChunk]:
    """
    Chia Document thành DocumentChunk.

    Metadata của mỗi chunk giữ lại thông tin tài liệu nguồn.
    """

    if chunk_size <= 0:
        raise ValueError("chunk_size phải lớn hơn 0.")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError(
            "overlap phải từ 0 đến nhỏ hơn chunk_size."
        )

    content = remove_table_of_contents(doc.content.strip())

    if not content:
        return []

    pieces = split_by_articles(
        content,
        chunk_size=chunk_size,
        overlap=overlap,
    )

    chunks = []

    for index, piece in enumerate(pieces):
        chunk_metadata = dict(doc.metadata)

        # Các trường nguồn được ưu tiên, không để metadata
        # tùy chỉnh ghi đè thông tin của tài liệu.
        chunk_metadata.update({
            "doc_id": doc.doc_id,
            "title": doc.title,
            "version": doc.version,
            "date": doc.date,
            "owner": doc.owner,
        })

        chunks.append(
            DocumentChunk(
                chunk_id=f"{doc.doc_id}_{index}",
                doc_id=doc.doc_id,
                content=piece,
                chunk_index=index,
                embedding=None,
                metadata=chunk_metadata,
            )
        )

    return chunks


def chunk_document(
    doc_source: str,
    max_chars: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[DocumentChunk]:
    """
    Đọc Markdown có front matter rồi trả về danh sách chunks.
    """

    doc = parse_document(doc_source)

    return chunk_documents(
        doc,
        chunk_size=max_chars,
        overlap=overlap,
    )
