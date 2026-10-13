from dataclasses import dataclass, field

CATEGORIES = (
    "hoc_tap",
    "chap_hanh_noi_quy",
    "chinh_tri_xa_hoi",
    "pham_chat_cong_dan",
    "cong_tac_lop_doan_hoi",
)

MAX_TOTAL = 100
UNCONFIRMED_PENALTY = 10

# THỨ TỰ QUAN TRỌNG: mục đ) có chữ "thành tích đặc biệt trong học tập",
# nên cong_tac_lop_doan_hoi phải kiểm tra TRƯỚC hoc_tap.
_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("cong_tac_lop_doan_hoi", ("công tác", "đoàn", "hội sv", "hội sinh viên")),
    ("chinh_tri_xa_hoi", ("chính trị",)),
    ("chap_hanh_noi_quy", ("nội quy", "chấp hành")),
    ("pham_chat_cong_dan", ("công dân", "cộng đồng", "phẩm chất")),
    ("hoc_tap", ("học tập",)),
]


@dataclass
class ScoreResult:
    raw_total: int
    total: int
    classification: str
    breakdown: dict[str, int] = field(default_factory=dict)
    confirmed_score: bool = False


def normalize_category(raw_name: str) -> str:
    """Map tên mục thô về 1 trong 5 khoá chuẩn (category-mapping.md).

    So khớp theo substring, không phân biệt hoa/thường. Không nhận ra thì
    raise ValueError (calculate_score bắt lại và đổi thành "Error: ...").
    """
    name = raw_name.strip().lower()
    for key, keywords in _KEYWORDS:
        if any(keyword in name for keyword in keywords):
            return key
    raise ValueError(raw_name)


def classify(total: int, rubric: dict) -> str:
    classifications = rubric.get("classification")
    classifications = sorted(
        classifications, key=lambda item: item["min"], reverse=True
    )
    for classification in classifications:
        if total >= classification.get("min"):
            return classification.get("label")


def calculate_score(
    category_scores: dict[str, int], rubric: dict, confirmed: bool = True
) -> ScoreResult | str:
    """
    Cộng điểm 5 mục, trừ điểm nếu chưa xác nhận, chốt trần 100, xếp loại.

    rubric = {"classification": [{"min": int, "label": str}, ...],
              "limits": {"<khoá chuẩn>": int}}   # "limits" là tuỳ chọn
    Thiếu dữ liệu hoặc dữ liệu sai thì trả "Error: ...".
    """

    # B1: Chuẩn hóa tên mục
    normalized_category: dict[str, int] = {}
    for raw_name, score in category_scores.items():
        try:
            key = normalize_category(raw_name)
        except ValueError as error:
            return f"Error: không nhận ra mục '{raw_name}'."

        if key in normalized_category:
            return f"Error: mục '{key}' bị trùng."
        normalized_category[key] = score

    # B2: Kiểm tra thiếu mục
    missing = [
        category for category in CATEGORIES if category not in normalized_category
    ]
    if missing:
        missing_names = ", ".join(missing)
        return f"Error: thiếu các mục {missing_names} - không thể tính điểm."

    # B3: Giới hạn mức trần từng mục
    limits: dict[str, int] = rubric.get("limits", {})
    breakdown: dict[str, int] = {}
    for key in CATEGORIES:
        current_score = max(normalized_category.get(key), 0)
        if key in limits:
            max_score = limits.get(key)
            score = min(current_score, max_score)
        breakdown[key] = score

    # B4: Tính tổng điểm
    raw_total = sum(breakdown.values())
    if not confirmed:
        raw_total -= UNCONFIRMED_PENALTY
    total = max(0, min(raw_total, MAX_TOTAL))

    # B5: Xếp loại
    classification = classify(total, rubric)
    if classification is None:
        return "Error: thiếu khung xếp loại hợp lệ - không thể xếp loại."

    return ScoreResult(
        raw_total=raw_total,
        total=total,
        classification=classification,
        breakdown=breakdown,
        confirmed_score=confirmed,
    )
