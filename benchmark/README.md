# Benchmark truy xuất Pro Git

[questions.jsonl](questions.jsonl) lưu một câu mỗi dòng UTF-8. Câu hỏi và đáp án kỳ vọng viết bằng tiếng Việt, bằng chứng trích nguyên văn từ [corpus tiếng Anh](../data/progit-v2-en.jsonl). Bài đo phản ánh truy xuất xuyên ngôn ngữ trên corpus này.

| Tập | ID | Phạm vi nguồn | Câu có filter |
|---|---|---|---|
| Dev (15 câu) | `q01`–`q15` | Git Basics, Git Branching, Distributed Git | `q06`, `q08` |
| Test (5 câu) | `q16`–`q20` | Git Tools, Customizing Git | `q17`, `q20` |

Tách theo chương trước khi chạy truy xuất. Các trang bằng chứng của hai tập không trùng, kể cả bằng chứng thay thế. Các chương cùng một cuốn sách nên vẫn có thể lặp thuật ngữ và ví dụ Git. Tập test nhỏ, bao phủ hai chương.

## Cách dùng

- Dùng `question` làm query. Cấu hình C áp dụng so khớp chính xác trường `section` nếu có `filter`. Giá trị được nêu trong câu hỏi trước khi truy xuất. Câu không có trường `filter` chạy không lọc.
- Dùng `gold_source_id` và `gold_page` để đối chiếu với `document_id` và `page` trong corpus. `evidence_quote` là đoạn liền mạch ở trang đó. Khi có `alternate_evidence`, chấp nhận bất kỳ đoạn hợp lệ nào đủ hỗ trợ đáp án. Chỉ dùng đáp án, trang nguồn và bằng chứng ở bước chấm.
- Chọn cấu hình trên dev theo thứ tự Evidence Hit@3 cao hơn, Hit@1 cao hơn, rồi thời gian ingest thấp hơn. Nếu vẫn bằng nhau, ưu tiên cấu hình theo thứ tự A, B, C. Cố định tham số và lựa chọn trước khi chạy test.

## Phiên bản chốt trước khi chạy

- Corpus `progit-v2-en` tại commit nguồn `a013e3230a1207cfa5ae94d28ba7d2021063c337`. Mỗi đoạn bằng chứng đã được đối chiếu với văn bản chuẩn hóa của mục tương ứng trong [manifest](../data/manifest.json).
- SHA-256 của `questions.jsonl` là `46fe32cde74f44cac5eadc57802bbf3558b6c498fed8bd0c0c20ea0dfa96adcd`.
- Bằng chứng trích từ *Pro Git, Second Edition* của Scott Chacon và Ben Straub, Apress, theo [CC BY-NC-SA 3.0](https://creativecommons.org/licenses/by-nc-sa/3.0/). Quy tắc chuẩn hóa và ghi công nguồn được lưu trong manifest.
