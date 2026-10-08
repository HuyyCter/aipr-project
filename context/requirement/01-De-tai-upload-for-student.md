# FINAL PROJECT AIPR — ĐỀ TÀI GỢI Ý (W1–W7)

Hình thức: nhóm 3 SV, thực hiện trong 10 ngày, nộp report (Word) + code, bảo vệ 20 phút/nhóm (vấn đáp + sửa code tại chỗ).

Trọng tâm bắt buộc: RAG (w3–w4) + Agent loop & tool (w6) + MCP (w7), có đo lường (w5).

Mỗi nhóm chọn 1 trong 5 đề tài dưới đây (hoặc đề xuất đề tài riêng, nhưng phải qua đúng bộ yêu cầu ở tài liệu 02-yeu-cau-thuc-hien.md).

## 1. Một đề tài đạt yêu cầu phải có đủ 3 tầng

| Tầng | Nghĩa là | Nếu thiếu thì |
| --- | --- | --- |
| (a) Tra cứu | Câu trả lời này nằm ở đâu trong tài liệu? | Một bài lab RAG/chatbot hỏi đáp tài liệu. Bị đánh giá chất lượng RAG |
| (b) Biến đổi | Từ các mảnh tài liệu đó, tôi suy ra / tính / so sánh ra được gì? | Không có gì để đo → eval vô nghĩa |
| (c) Hành động | Sau khi hiểu, hệ thống làm gì và làm sao biết là đã làm? | Chỉ là pipeline tra cứu, không phải agent |

### Giải thích thêm

#### (a) Tra cứu: tầng "có bằng chứng"

Mọi câu trả lời phải truy được về nguồn, có doc_id cụ thể, chứ không phải "LLM nhớ mang máng". Và quan trọng không kém: câu hỏi không có đáp án trong corpus (no_answer) phải được nhận diện đúng.

Hai kỹ năng tách biệt trong tầng này:

- Grounding: trích dẫn đúng mảnh tài liệu, đúng phiên bản (version).
- Calibration: biết khi nào không trả lời. Đây là chỗ dễ mất điểm nhất: một hệ thống luôn trả lời trông rất "giỏi" nhưng thực chất đang bịa.

**Câu tự kiểm:** Đưa 1 câu mà đáp án không có trong corpus thì hệ thống có từ chối không, hay vẫn bịa ra một câu nghe hợp lý?

#### (b) Biến đổi: tầng "có việc để đo"

Nghĩa là: câu trả lời không thể copy nguyên văn một chunk. Nó đòi hỏi ít nhất một trong:

- Tính toán (T4: cộng lại tổng chi tiêu, đối chiếu hạn mức);
- Tổng hợp nhiều tài liệu (T1: phải trích ≥2 document mới trả lời được);
- So sánh / phát hiện mâu thuẫn (T1: hai bản policy khác phiên bản — phải chọn bản mới nhất, T2: chọn 1 trong 2 giả thuyết đều đúng một phần);
- Từ chối vì thiếu dữ liệu để suy luận (thiếu 1 vế thì không so sánh được → phải nói "không đủ dữ liệu").

Nếu mọi câu hỏi đều là "tra 1 chunk rồi đọc lại", thì faithfulness luôn ≈ 1.0, độ chính xác luôn ≈ 100%, và bảng eval của bạn trở thành con số vô nghĩa. Tầng (b) tạo ra chỗ có thể sai — và chỗ có thể sai chính là chỗ chấm được điểm. Đó là lý do "Nếu thiếu → không có gì để đánh giá".

Phân biệt với tầng (a): hai mục "từ chối" không trùng nhau.

- (i) Từ chối vì tài liệu không chứa thông tin → lỗi ở khâu truy vấn
- (ii) Từ chối vì thông tin có nhưng không đủ để biến đổi (ví dụ chỉ có hạn mức, không có hoá đơn) → lỗi ở khâu suy luận.

**Câu tự kiểm:** Câu hỏi này nếu đưa cho một người chỉ được đọc 1 đoạn tài liệu, họ có trả lời được ngay không? Nếu "có" → đề tài đang thiếu tầng (b).

#### (c) Hành động: tầng "chứng minh là agent"

Nghĩa là: có ít nhất một tool ghi (thay đổi trạng thái thật: tạo request, chặn IP, submit quyết định, ghi log), và ngay sau đó bắt buộc có bước verify gọi lại một tool đọc để chứng minh trạng thái đã thực sự đổi.

Cấu trúc bắt buộc là một cặp: write_tool() → đọc lại → thấy thay đổi.

Đây là tầng phân biệt "agent" với "pipeline". Ba giá trị của nó:

1. Chứng minh agent thực sự dùng kết quả tool, chứ không phải LLM tự diễn. Câu "agent có thực sự dùng kết quả tool" chỉ trả lời được nếu tool có kết quả quan sát được.
2. Ràng buộc an toàn: bước verify buộc agent phải quan sát hậu quả, tức là có cơ chế để "chỉ hành động khi bằng chứng đủ".

Thiếu tầng này → bạn có một pipeline tra cứu đọc–rồi–in. Không có side effect thì không có gì để verify, không có gì để agent "quyết định"

**Câu tự kiểm:** Sau khi hệ thống chạy xong, có một dòng dữ liệu nào trong DB/file/trạng thái thật sự bị thay đổi không? Và tôi chứng minh điều đó bằng lệnh đọc nào?

**Tóm tắt:** (a) Trả lời có nguồn → (b) Suy ra được điều không viết sẵn → (c) Làm thay đổi trạng thái và tự kiểm chứng. Đủ 3 tầng thì đề tài mới là "agent có RAG có đo lường".

## 2. Bảng tóm tắt 5 đề tài

| # | Đề tài | Sản phẩm chính |
| --- | --- | --- |
| T1 | Trợ lý quy chế + hành động | Hỏi quy chế → làm thủ tục → xác nhận |
| T2 | Kiểm toán chi tiêu công tác | Báo cáo → đối chiếu hạn mức → duyệt/từ chối/leo thang |
| T3 | Trợ lý học tập trên lesson plan môn học | Hỏi nội dung môn → trả lời có trích → từ chối nếu ngoài chương trình |
| T4 | Trợ lý điểm rèn luyện + khiếu nại | Hỏi quy tắc → tính điểm rèn luyện → khiếu nại → xác nhận |
| T5 | Trợ lý CTXH: quy đổi & đăng ký | Tra mã hoạt động → quy đổi ngày → đăng ký → xác nhận |

## 3. Yêu cầu tối thiểu mà mọi đề tài phải có

Bản đầy đủ ở 02-yeu-cau-thuc-hien.pdf. Tóm tắt nhanh:

- ≥2 chế độ truy vấn (dense + hybrid BM25: w4/ex2_1_hybrid_search.py, không viết lại)
- MCP server do SV tự viết, ≥2 tool (≥1 tool thay đổi trạng thái); client discover động, không hardcode danh sách tool
- ≥1 tool có side effect + bước verify ngay sau đó
- Testset ≥12 câu, ≥4 câu no_answer; đo faithfulness và tỉ lệ từ chối đúng; log `USAGE` từng câu (calls, prompt_tokens, completion_tokens, max_prompt)
- Chạy được trên máy GV bằng đúng 1 lệnh; mọi số liệu trong report tái lập được bằng make eval

Các mục không bắt buộc (đổi thành điểm cộng, tối đa +6): metadata filter dùng thật

## 4. Không chọn loại đề tài:

- Đề tài chỉ có tra cứu (chatbot hỏi đáp tài liệu)
- Đề tài dùng tool chỉ để đọc (không có side effect) → không chạy được bài kiểm tra "agent có thực sự dùng kết quả tool".
- Đề tài mà câu trả lời có thể tra Google trong 10 giây
