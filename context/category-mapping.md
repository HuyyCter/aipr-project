# Category Mapping — ánh xạ tên mục điểm rèn luyện

File tham khảo, không phải code — SV2 dùng để implement 1 dict/hàm `normalize_category()` trong `domain/scoring.py` khi bắt đầu code. Không sửa bất kỳ tài liệu gốc nào trong `data/source_docs/`.

**Vì sao cần:** 3 nguồn — văn bản Điều 4 (`quy_dinh_diem_ren_luyen.md`), Phụ lục 1 cùng file, và minh chứng hoạt động thật của sinh viên — gọi cùng 1 mục bằng 3 cách viết khác nhau. `calculate_conduct_score` phải so khớp `category_scores` (từ minh chứng SV) với `rubric` (từ Phụ lục) theo đúng 1 khoá, nên cần ánh xạ về 1 bộ khoá chuẩn trước khi so sánh.

---

## Bảng ánh xạ đầy đủ

| Khoá chuẩn | Điều 4 (liệt kê 5 mục) | Điều 5–9 (tiêu đề từng điều) | Phụ lục 1 (số La Mã) | `tmp.md` — bảng điểm thật của SV | Khung điểm cơ bản | Trần vượt khung |
|---|---|---|---|---|---|---|
| `hoc_tap` | a) Ý thức và kết quả học tập | Điều 5. Đánh giá về ý thức và kết quả học tập | I. HỌC TẬP | "Ý thức và kết quả học tập (vượt khung không quá 30 điểm)" | 0–20 | 30 |
| `chap_hanh_noi_quy` | b) Ý thức và kết quả chấp hành nội quy, quy chế, quy định của trường | Điều 6. Đánh giá về ý thức và kết quả chấp hành nội quy, quy chế, quy định trong trường | II. CHẤP HÀNH NỘI QUY, QUY CHẾ | "Ý thức và kết quả chấp hành nội quy, quy chế trong nhà trường (từ 0-25 điểm)" | 0–25 | 25 *(không vượt khung, dưới 0 làm tròn về 0)* |
| `chinh_tri_xa_hoi` | c) Ý thức và kết quả tham gia các hoạt động chính trị xã hội, văn hóa, văn nghệ, thể thao, phòng chống tội phạm và các tệ nạn xã hội | Điều 7. ... | III. THAM GIA CÁC HOẠT ĐỘNG CHÍNH TRỊ-XÃ HỘI, VĂN HÓA, VĂN NGHỆ, THỂ THAO, PHÒNG CHỐNG CÁC TỆ NẠN XÃ HỘI | "Ý thức và kết quả tham gia các hoạt động chính trị – xã hội, văn hóa, văn nghệ, thể thao, phòng chống các tệ nạn xã hội (vượt khung không quá 30 điểm)" | 0–20 | 30 |
| `pham_chat_cong_dan` | d) Ý thức công dân trong quan hệ với cộng đồng | Điều 8. Đánh giá về ý thức công dân trong quan hệ cộng đồng | IV. PHẨM CHẤT CÔNG DÂN TRONG QUAN HỆ VỚI CỘNG ĐỒNG | "Phẩm chất công dân và quan hệ với cộng đồng (vượt khung không quá 38 điểm)" | 0–25 | 38 |
| `cong_tac_lop_doan_hoi` | đ) Ý thức và kết quả tham gia công tác của lớp, các đoàn thể, tổ chức khác trong trường hoặc các thành tích đặc biệt trong học tập, rèn luyện của SV | Điều 9. ... | V. THAM GIA CÔNG TÁC LỚP, ĐOÀN, HỘI SV | "Ý thức và kết quả tham gia công tác của lớp, các đoàn thể, tổ chức khác trong nhà trường hoặc các thành tích đặc biệt trong học tập, rèn luyện của SV (vượt khung không quá 15 điểm)" | 0–10 | 15 |

**5 khoá trên dùng làm key của `category_scores: dict[str, int]`** truyền vào `calculate_conduct_score`.

---

## Trường hợp đặc biệt: `VI. KHÁC` (Phụ lục 1) — KHÔNG đưa vào `category_scores`

"Sinh viên không xác nhận điểm rèn luyện trong học kỳ: -10 điểm" không phải 1 mục có khung điểm riêng để sinh viên tích luỹ — nó là **1 khoản trừ áp dụng sau khi đã cộng xong 5 mục**, chỉ xảy ra nếu SV không xác nhận bảng điểm trên hệ thống (Điều 12.3 `quy_dinh_diem_ren_luyen.md`).

→ Xử lý bằng 1 tham số riêng, không lẫn vào 5 khoá trên:
```python
def calculate_score(
    category_scores: dict[str, int], rubric: dict, confirmed: bool = True
) -> ScoreResult | str:
    raw_total = sum(category_scores.values())
    if not confirmed:
        raw_total -= 10
    total = min(
        raw_total, 100
    )  # chốt trần 100 theo Điều 4.2 — xem phát hiện ở lượt trước
    ...
```

---

## Khi nào dùng bảng này

- **SV1** (viết `search_regulations`): khi agent trích rubric từ `quy_dinh_diem_ren_luyen.md`, dùng bảng này để biết đoạn trích "I. HỌC TẬP" và đoạn trích "Điều 5..." là **cùng 1 mục**, tránh đưa 2 bản rubric trùng vào context.
- **SV2** (viết `domain/scoring.py`): implement `normalize_category(raw_name: str) -> str` dựa đúng bảng này, dùng `str.lower()` + kiểm tra substring (ví dụ `"học tập" in raw_name.lower()` → `hoc_tap`) thay vì so khớp chuỗi chính xác, vì cách viết thật có thể thêm bớt khoảng trắng/dấu ngoặc đơn vượt khung.
- **Người soạn file minh chứng SV** (từ `tmp.md`) cho corpus: nên giữ nguyên tiêu đề gốc như trong `tmp.md` (không cần đổi sang khoá chuẩn ngay trong tài liệu) — việc ánh xạ xảy ra ở code, tài liệu minh chứng cứ để tự nhiên như sinh viên thật đọc được.