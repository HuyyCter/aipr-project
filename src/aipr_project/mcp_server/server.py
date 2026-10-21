import json
import logging
import sys
from pathlib import Path

from mcp.server.mcpserver import MCPServer

from aipr_project.domain.appeals_store import Appeal
from aipr_project.domain.scoring import *
from aipr_project.rag.build_index import (
    DOCS_DIR,
    INDEX_DIR,
    SOURCE_FILES,
    read_document,
)
from aipr_project.rag.hybrid_search import build_bm25_index, hybrid_search
from aipr_project.rag.models import DocumentChunk
from aipr_project.rag.store import DocumentStore

PROJECT_ROOT = Path(__file__).resolve().parents[3]
LOG_PATH = PROJECT_ROOT / "logs" / "server" / "server.log"
RUBRIC_PATH = PROJECT_ROOT / "data" / "rubric.json"

NOT_FOUND_MESSAGE = "Không tìm thấy nội dung liên quan trong tài liệu."
MAX_DOCUMENT_CHARS = 800
MIN_VECTOR_SCORE = 0.5

with open(RUBRIC_PATH, "r", encoding="utf-8") as f:
    RUBRIC = json.load(f)


# ==================== HELPERS ====================
def _header(doc_id: str, title: str, version: str, date: str) -> str:
    return f"[{doc_id}] {title} (phiên bản {version}, {date})"


def _format_score(result: ScoreResult) -> str:
    lines = [
        f"Tổng điểm: {result.total}/100",
        f"Xếp loại: {result.classification}",
    ]
    if result.raw_total != result.total:
        lines.append(f"(tổng thô {result.raw_total}, đã chốt trần {result.total})")
    if not result.confirmed_score:
        lines.append(
            f"(đã trừ {UNCONFIRMED_PENALTY} điểm vì chưa xác nhận điểm rèn luyện)"
        )
    lines.append("Chi tiết:")
    for key in CATEGORIES:
        lines.append(f"- {key}: {result.breakdown[key]}")
    return "\n".join(lines)


# ==================== LOGGING ====================
_handler: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]
try:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _handler.append(logging.FileHandler(LOG_PATH, encoding="utf-8"))
except OSError as error:
    print(f"warning: cannot open {LOG_PATH}: {error}", file=sys.stderr)

logging.basicConfig(
    level=logging.INFO,
    handlers=_handler,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


# ==================== LOAD RAG ====================
def _load_store() -> DocumentStore:
    store = DocumentStore()
    for name in SOURCE_FILES:
        store.add(read_document(DOCS_DIR / name))
    return store


def _load_index() -> tuple[list[DocumentChunk], list[list[float]]]:
    index_path = INDEX_DIR / "index.json"
    if not index_path.exists():
        raise FileNotFoundError(f"Chưa có {index_path}. Chạy build_index.py trước.")
    data = json.loads(index_path.read_text(encoding="utf-8"))
    chunks = [DocumentChunk(**c) for c in data["chunks"]]
    return chunks, data["embeddings"]


STORE = _load_store()
CHUNKS, EMBEDDINGS = _load_index()
BM25 = build_bm25_index(CHUNKS)
log.info("RAG loaded: %d chunks, %s", len(CHUNKS), STORE.count())


# ==================== MCP SERVER ====================
mcp_server = MCPServer(
    "aipr-project",
    description="MCP Server: hỗ trợ tra cứu quy chế, khiếu nại và tính điểm rèn luyện",
)


@mcp_server.tool()
def search_regulations(query: str, top_k: int = 3) -> str:
    """
    Tìm trong tài liệu quy chế điểm rèn luyện và quy trình khiếu nại những đoạn
    liên quan nhất tới câu hỏi. Dùng cho mọi câu hỏi về quy định: khung điểm từng
    mục, tiêu chí xếp loại, hạn nộp khiếu nại, thủ tục. Đây là tool ĐỌC.

    Args:
        query: Câu hỏi hoặc từ khóa cần tìm, viết bằng tiếng Việt.
        top_k: Số đoạn tối đa trả về (1-5, mặc định 3).

    Returns:
        Các đoạn cách nhau bằng "---", mỗi đoạn bắt đầu bằng dòng
        "[doc_id] tiêu đề (phiên bản, ngày)" rồi đến nội dung. Dùng doc_id này để
        trích nguồn. Nếu không có đoạn nào liên quan, trả đúng câu:
        "Không tìm thấy nội dung liên quan trong tài liệu." - khi đó KHÔNG được
        tự suy đoán câu trả lời. Lỗi thì trả chuỗi bắt đầu bằng "Error: ".
    """
    log.info("search_regulations() được gọi: query=%r, top_k=%r", query, top_k)
    try:
        if not query.strip():
            return "Error: query không được rỗng."

        top_k = max(1, min(top_k, 3))
        result = hybrid_search(
            query,
            CHUNKS,
            EMBEDDINGS,
            BM25,
            top_k=top_k,
            min_vector_score=MIN_VECTOR_SCORE,
        )
        if not result:
            return NOT_FOUND_MESSAGE
        return "\n=============\n".join(
            f"{_header(chunk.doc_id, chunk.title, chunk.version, chunk.date)}\n{chunk.content}"
            for chunk in (CHUNKS[i] for i, _ in result)
        )
    except Exception as error:
        log.error(f"search_regulations() lỗi: {error}")
        return f"Error: không tìm kiếm được: {error}"


# @mcp_server.tool()
def get_document(doc_id: str) -> str:
    """
    Lấy toàn bộ nội dung một tài liệu theo mã. Dùng sau search_regulations khi một
    đoạn trích chưa đủ ngữ cảnh, hoặc khi cần đọc nguyên văn một tài liệu cụ thể
    (ví dụ bảng minh chứng hoạt động của sinh viên). Đây là tool ĐỌC.

    Args:
        doc_id: Mã tài liệu, ví dụ "DOC0001" (lấy từ kết quả search_regulations).

    Returns:
        Dòng "[doc_id] tiêu đề (phiên bản, ngày)" rồi đến nội dung. Tài liệu quá
        dài sẽ bị cắt và có ghi chú. Không tìm thấy thì trả
        "Error: không tìm thấy tài liệu <doc_id>".
    """
    log.info("get_document() được gọi: doc_id=%r", doc_id)
    try:
        document = STORE.get(doc_id.strip())
        if not document:
            return f"Error: Không tìm thấy tài liệu {doc_id}."
        text = document.content
        if len(text) > MAX_DOCUMENT_CHARS:
            text = text[:MAX_DOCUMENT_CHARS] + "\n[...Đã cắt bớt...]"

        title = document.title
        version = document.version
        date = document.date
        return f"{_header(doc_id, title, version, date)}\n{text}"
    except Exception as error:
        log.error(f"get_document() lỗi: {error}")
        return f"Error: không lấy được tài liệu: {error}"


@mcp_server.tool()
def calculate_conduct_score(
    category_scores: dict[str, int], confirmed: bool = False
) -> str:
    """
    Tính tổng điểm rèn luyện và xếp loại. Đây là tool TÍNH TOÁN: luôn dùng nó để
    cộng điểm, KHÔNG tự cộng 5 mục. Gọi sau khi đã tra khung điểm bằng
    search_regulations. Không tự đoán điểm: thiếu mục nào thì tool báo lỗi, khi
    đó hỏi lại sinh viên thay vì bịa.

    Args:
        category_scores: Từ điển mục điểm -> điểm của mục đó (số nguyên). Phải đủ
            5 khóa: "hoc_tap", "chap_hanh_noi_quy", "chinh_tri_xa_hoi",
            "pham_chat_cong_dan", "cong_tac_lop_doan_hoi".
        confirmed: True nếu sinh viên NÊU RÕ đã xác nhận điểm rèn luyện trên hệ thống.
            Mặc định False (chưa xác nhận, bị trừ 10 điểm). Nếu sinh viên không nói,
            giữ False và trong câu trả lời nêu rõ kết quả đã bị trừ 10 điểm vì chưa xác nhận.

    Returns:
        Tổng điểm, xếp loại và điểm từng mục. Lỗi thì trả chuỗi bắt đầu bằng "Error: ".
    """
    log.info(
        "calculate_conduct_score() được gọi: scores=%r, confirmed=%r",
        category_scores,
        confirmed,
    )
    try:
        result = calculate_score(category_scores, RUBRIC, confirmed)
        if isinstance(result, str):
            return result
        return _format_score(result)
    except Exception as error:
        log.error(f"calculate_conduct_score() lỗi: {error}")
        return f"Error: không tính được điểm: {error}"


@mcp_server.tool()
def submit_appeal(student_id: str, reason: str, category: str) -> str:
    """
    Nộp hồ sơ khiếu nại điểm rèn luyện cho một sinh viên. Đây là tool GHI:
    mỗi lần gọi sẽ tạo thêm một hồ sơ mới, nên chỉ gọi khi sinh viên đã nói rõ
    muốn khiếu nại và đã nêu lý do.

    Args:
        student_id: Mã sinh viên, ví dụ "SV001".
        reason: Lý do khiếu nại, mô tả ngắn gọn vì sao sinh viên cho rằng điểm sai.
        category: Mục điểm bị khiếu nại, ví dụ "chinh_tri_xa_hoi".

    Returns:
        "Đã tạo khiếu nại #<appeal_id>, trạng thái: pending". Dùng appeal_id
        trong kết quả này để tra lại hồ sơ bằng get_appeal_status.
        Lỗi thì trả chuỗi bắt đầu bằng "Error: ".
    """
    log.info(
        "submit_appeal() được gọi: student_id=%r, category=%r", student_id, category
    )
    try:
        return Appeal.submit_appeal(student_id, reason, category)
    except Exception as error:
        log.error(f"submit_appeal() lỗi: {error}")
        return f"Error: Không nộp được đơn thiếu nại: {error}"


@mcp_server.tool()
def get_appeal_by_id(appeal_id: str) -> str:
    """
    Tra cứu một hồ sơ khiếu nại theo mã. Đây là tool ĐỌC, dùng để xác nhận
    hồ sơ đã thực sự được lưu (ví dụ ngay sau khi gọi submit_appeal) hoặc để
    kiểm tra trạng thái hồ sơ.

    Args:
        appeal_id: Mã hồ sơ, lấy từ kết quả của submit_appeal,
            ví dụ "a1b2c3d4" (có hoặc không có dấu "#" đều được).

    Returns:
        "Khiếu nại #<appeal_id> — <student_id> — <status> — nộp lúc <timestamp>".
        Không tìm thấy hoặc lỗi thì trả chuỗi bắt đầu bằng "Error: ".
    """
    log.info("get_appeal_by_id() được gọi: appeal_id=%r", appeal_id)
    try:
        return Appeal.get_appeal_by_id(appeal_id)
    except Exception as error:
        log.error(f"get_appeal_by_id() lỗi: {error}")
        return f"Error: Không đọc được đơn thiếu nại: {error}"


@mcp_server.tool()
def list_appeals(student_id: str) -> str:
    """
    Liệt kê các khiếu nại đã nộp của một sinh viên (mới nhất trước, tối đa 10
    hồ sơ). Đây là tool ĐỌC. Dùng khi sinh viên hỏi mình đã nộp những khiếu
    nại nào, hoặc khi cần tìm lại mã hồ sơ mà không nhớ. Nếu đã biết mã hồ sơ
    thì dùng get_appeal_status.

    Args:
        student_id: Mã sinh viên, ví dụ "SV001".

    Returns:
        Mỗi hồ sơ một dòng gồm mã, mục điểm bị khiếu nại, trạng thái, thời
        điểm nộp. Chưa có hồ sơ nào thì trả câu thông báo bình thường. Lỗi
        thì trả chuỗi bắt đầu bằng "Error: ".
    """
    log.info("list_appeals() được gọi: student_id=%r", student_id)
    try:
        return Appeal.list_appeals(student_id)
    except Exception as error:
        log.error(f"list_appeals() lỗi: {error}")
        return f"Error: Không đọc được danh sách đơn thiếu nại: {error}"


if __name__ == "__main__":
    mcp_server.run()
