"""Đo điểm vector cao nhất (cosine) của từng câu trong testset so với toàn bộ chunk.

Chạy:
    uv run python calibrate_testset.py                       # dùng tests/testset.jsonl
    uv run python calibrate_testset.py tests/testset_v2.jsonl
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

from aipr_project.rag.build_index import INDEX_DIR
from aipr_project.rag.embeddings import cosine_similiarity, embed_key

TESTSET = Path(sys.argv[1] if len(sys.argv) > 1 else "tests/testset.jsonl")
OUT_TYPES = {"no_answer"}

# Câu nguyên văn trong tài liệu: kiểm tra đoạn Điều 12 (hai tuần / tuần thứ ba)
# có được index và tìm thấy không.
PROBES = [
    "đề nghị bổ sung hoặc sửa đổi các nội dung còn thiếu hoặc sai lệch trong thời gian hai tuần kể từ ngày điểm được công bố",
    "Vào tuần thứ ba của học kỳ tiếp theo, SV được quyền khiếu nại về tổng điểm rèn luyện của cá nhân",
]

data = json.loads((INDEX_DIR / "index.json").read_text(encoding="utf-8"))
CHUNKS = data["chunks"]
E = data["embeddings"]


def top_chunks(query: str, n: int = 1) -> list[tuple[float, int]]:
    v = embed_key(query)
    scored = [(cosine_similiarity(v, e), i) for i, e in enumerate(E)]
    scored.sort(reverse=True)
    return scored[:n]


def snippet(i: int, width: int = 70) -> str:
    return CHUNKS[i]["content"].replace("\n", " ")[:width]


def load_cases(path: Path) -> list[dict]:
    cases = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            cases.append(json.loads(line))
    return cases


cases = load_cases(TESTSET)
by_type: dict[str, list[tuple[float, dict, int]]] = defaultdict(list)
for case in cases:
    score, idx = top_chunks(case["question"])[0]
    by_type[case["type"]].append((score, case, idx))

print(f"Testset: {TESTSET} ({len(cases)} câu, {len(E)} chunk)")
for type_name, rows in by_type.items():
    print(f"\n== {type_name}")
    for score, case, idx in sorted(rows, key=lambda r: r[0], reverse=True):
        doc = CHUNKS[idx]["doc_id"]
        print(f"{score:.3f}  {case['id']}  [{doc}] {case['question'][:55]}")
        print(f"        -> {snippet(idx)}")

in_scores = [
    (s, c["id"])
    for t, rows in by_type.items()
    if t not in OUT_TYPES
    for s, c, _ in rows
]
out_scores = [
    (s, c["id"]) for t, rows in by_type.items() if t in OUT_TYPES for s, c, _ in rows
]

print("\n== TỔNG KẾT")
if in_scores and out_scores:
    in_min = min(in_scores)
    out_max = max(out_scores)
    print(f"Thấp nhất nhóm có đáp án : {in_min[0]:.3f} ({in_min[1]})")
    print(f"Cao nhất nhóm no_answer  : {out_max[0]:.3f} ({out_max[1]})")
    if in_min[0] > out_max[0]:
        print(f"Tách được. Ngưỡng gợi ý ~ {(in_min[0] + out_max[0]) / 2:.2f}")
    else:
        bad = [i for s, i in out_scores if s >= in_min[0]]
        print(
            f"CHỒNG LẤN: {bad} (no_answer) cao hơn/bằng câu thấp nhất nhóm có đáp án."
        )
        print("Ngưỡng điểm không đủ để từ chối; phần từ chối phải do prompt/LLM.")

print("\n== PROBE (đoạn Điều 12 có được tìm thấy không)")
for q in PROBES:
    print(f"\n{q[:80]}...")
    for score, idx in top_chunks(q, 3):
        print(f"  {score:.3f} [{CHUNKS[idx]['doc_id']}] {snippet(idx, 90)}")
