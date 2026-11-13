# Báo cáo cá nhân — Day 6

## Dữ liệu và pipeline
- Chủ đề, nguồn/quyền, số trang và quy tắc tính trang: Sử dụng Git trong dự án phần mềm. Corpus gồm 32 mục tiếng Anh từ *Pro Git, Second Edition* của Scott Chacon và Ben Straub, theo CC BY-NC-SA 3.0. Mỗi mục AsciiDoc là một đơn vị nguồn. Tổng cộng 416.462 ký tự sau chuẩn hóa, mục ngắn nhất 2.189 ký tự. [Manifest](../../data/manifest.json)
- Chuẩn hóa, lỗi và giới hạn: Chuẩn hóa Unicode NFC và xuống dòng, bỏ chỉ thị ảnh, che địa chỉ email và bỏ hai mục có tệp nhúng lồng nhau. Văn bản có thể thiếu thông tin chỉ xuất hiện trong hình. Đầu vào JSONL thiếu trường bắt buộc trả mã lỗi và ghi tên file cùng số dòng. Khi cập nhật corpus, nạp lại toàn bộ để chuyển alias sang collection mới và loại chunk cũ. Đã kiểm tra nạp lại giữ nguyên ID và số chunk. [Log kiểm tra lỗi](../../results/pipeline_errors.log)
- Embedding model/provider/version/số chiều, vector store/version, metric, lệnh chạy và chi phí: `intfloat/multilingual-e5-small` revision `614241f622f53c4eeff9890bdc4f31cfecc418b3`, chạy local trên CPU bằng ONNX Runtime 1.31.1 với Python 3.14.4. Vector 384 chiều, dùng tiền tố `passage: ` cho chunk và `query: ` cho câu hỏi. Qdrant local 1.20.0 tìm kiếm cosine chính xác. Từ `starter/`, chạy `python -m src.benchmark dev --results-dir /tmp/day06-rerun` rồi `python -m src.benchmark test --results-dir /tmp/day06-rerun`. Chi phí API 0 USD. [Cài đặt và cách chạy](../../starter/README.md)
- Metadata bắt buộc, trường lọc bổ sung, nguồn giá trị và lý do chọn: Chunk lưu `document_id`, `source`, `page`, tiêu đề và offset ký tự để truy lại đúng đoạn. `section` là tên chương lấy từ nguồn gốc, dùng để giới hạn truy xuất theo phạm vi người hỏi chỉ định.

## Cấu hình và benchmark
- A / B / C (tham số cụ thể, khác biệt duy nhất B–C): A chia cửa sổ 500 ký tự, overlap 50. B chia theo heading/đoạn, tối đa 500 ký tự, overlap 0. C dùng chung index với B và lọc chính xác theo `section` khi câu hỏi yêu cầu. Cả ba dùng cùng corpus, model, vector store, cosine và top-3. [Nhật ký thí nghiệm](../../artifacts/experiment_log.csv)
- ≥20 câu: phân chia ≥15 dev / ≥5 test, câu metadata filter và cách kiểm chứng evidence: 20 câu tiếng Việt tách theo chương thành 15 dev và 5 test, mỗi tập có 2 câu filter. Đối chiếu nguyên văn 21 đoạn evidence tiếng Anh, gồm một đoạn thay thế, với đúng trang của corpus chuẩn hóa. [Benchmark](../../benchmark/README.md)
- Tiêu chí chọn chiến lược đã chốt trước khi xem test: Ưu tiên Evidence Hit@3, sau đó Hit@1, thời gian ingest thấp hơn, rồi thứ tự A/B/C. Chọn A trên dev vì cùng Hit@3 với B/C và có Hit@1 cao hơn. [Bản chốt trước test](../../results/selection.json)

## Kết quả
| Strategy | Split | Hit@1 (n/N) | Evidence Hit@3 (n/N) | Chunk count | Thời gian | Chi phí |
|---|---|---|---|---|---|---|
| A | Dev | 2/15 | 3/15 | 937 | 29,701 s | 0 USD API |
| A | Test | 0/5 | 0/5 | 937 | Dùng lại index dev | 0 USD API |
| B | Dev | 1/15 | 3/15 | 1.157 | 33,720 s | 0 USD API |
| B | Test | 0/5 | 0/5 | 1.157 | Dùng lại index dev | 0 USD API |
| C | Dev | 1/15 | 3/15 | 1.157 | Dùng chung index B | 0 USD API |
| C | Test | 0/5 | 0/5 | 1.157 | Dùng chung index B | 0 USD API |

| Strategy | Coherence trung bình /2 (n) | Metadata đủ và đúng (n/N) | Filter tuân thủ (n/N hoặc N/A) | Grounding 0/1/2 (số câu) và trung bình /2 |
|---|---|---|---|---|
| A | 1,50 (10) | 15/15 | Dev 0/2, test 1/2 | 3/1/1, TB 0,60 |
| B | 1,90 (10) | 15/15 | Dev 1/2, test 1/2 | 1/3/1, TB 1,00 |
| C | 1,90 (10) | 15/15 | Dev 2/2, test 2/2 | 0/4/1, TB 1,20 |

Đường dẫn trace, nhãn thủ công và cách chọn mẫu: Bảng truy xuất dùng kết quả khớp nguyên văn trong một chunk đúng nguồn/trang. Khi đối chiếu test, chunk hạng 3 của B và C ở q18 đủ bằng chứng tương đương, nên Evidence Hit@3 sau đối chiếu là A 0/5, B 1/5, C 1/5. Hit@1 test vẫn 0/5 ở cả ba. Mạch lạc chấm chunk đầu bao phủ vị trí giữa văn bản của 10 ID mục đầu theo thứ tự. Metadata đối chiếu đủ 45 bản ghi top-3 của test với corpus. Filter tuân thủ khi cả ba kết quả thuộc chương được yêu cầu. Grounding đọc toàn bộ top-3 của 5 câu test mỗi cấu hình. [Trace dev](../../results/dev_traces.jsonl) · [Trace test](../../results/test_traces.jsonl) · [Đối chiếu q18](../../results/evidence_review.csv) · [Mạch lạc](../../results/coherence_audit.csv) · [Metadata](../../results/metadata_audit.csv) · [Grounding](../../results/grounding_audit.csv)

## Phân tích và kết luận
- So sánh A–B và B–C; 2 ví dụ sai có ID câu và nguồn: B tăng mạch lạc từ 1,50 lên 1,90, tạo thêm 220 chunk và ingest lâu hơn khoảng 4 giây. A có độ dài min/trung vị/max là 68/500/500 ký tự, tổng 461.712 ký tự và 132.661 token. B và C có độ dài 14/392/500, tổng 416.460 ký tự và 121.204 token. Với cùng index, filter của C tăng tuân thủ test từ 1/2 lên 2/2 và grounding từ 1,00 lên 1,20. **q16, nguồn 07.10:** cả ba tìm được ví dụ `git bisect run`, nhưng thiếu quy ước mã thoát. **q20, nguồn 08.03:** B trả đoạn về remote và submodule. C tìm được đoạn cùng chương giải thích hook `update` ở 08.04, nhưng còn thiếu bằng chứng về `pre-receive`.
- Chiến lược chọn, đánh đổi, điều kiện áp dụng: Giữ A theo tiêu chí đã chốt trên dev. A có Hit@1 dev cao hơn và ingest nhanh hơn trong lần đo này. B/C đạt điểm mạch lạc cao hơn trên mẫu 10 vị trí. Lọc theo chương có ích khi người hỏi nêu phạm vi, nhưng trong cùng một chương vẫn có thể truy xuất nhầm mục.
- Hạn chế của dữ liệu, nhãn, test nhỏ, đo thời gian/chi phí: Corpus và câu hỏi khác ngôn ngữ, test chỉ có 5 câu từ hai chương. Lần chạy báo cáo ngày 13/11/2026, chốt dev lúc 17:24:43 và lưu trace test lúc 17:24:51 (UTC+7). Đo ingest một lần, gồm chia chunk, tạo vector và ghi Qdrant sau khi model đã nạp. Tổng token gồm tiền tố và token đặc biệt, bỏ padding. Codex hỗ trợ viết code, báo cáo và đọc trace để gán nhãn mạch lạc, grounding. Đã kiểm tra lại hash corpus/benchmark, thời điểm chốt dev, mẫu số và metadata theo từng bản ghi. Tôi đã xem qua các nhãn mạch lạc và grounding do Codex đề xuất và đồng ý giữ nguyên điểm.
- Nếu làm lại hoặc mở rộng, cải tiến gì? Chốt các đoạn bằng chứng tối thiểu đủ trả lời ngay khi soạn benchmark mới, tăng số câu test và mời người thứ hai chấm độc lập để đối chiếu nhãn.
