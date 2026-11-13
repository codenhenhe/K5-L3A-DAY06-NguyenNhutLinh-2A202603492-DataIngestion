# Day 06 · Data Ingestion Engineering

**Lab cá nhân** · **4 giờ** · **Dữ liệu tự chọn**

Biến tài liệu thành kho tri thức có thể truy xuất cho AI agent, rồi đo xem cách chuẩn bị dữ liệu nào hiệu quả nhất.

| 📄 Dữ liệu | 🧩 Chiến lược | 🎯 Benchmark |
|---|---|---|
| Tối thiểu **30 trang nội dung** | Tối thiểu **3 cấu hình** | Tối thiểu **20 câu hỏi** |

## Bắt đầu nhanh

Dùng [starter PostgreSQL + pgvector](starter/README.md) để dựng database và hoàn thiện các hàm TODO, hoặc tự chọn vector store tương đương. Starter chỉ là khung: **bạn tự hiện thực pipeline và benchmark**.

## 1. Xây pipeline

![Đọc tài liệu, chuẩn hóa, chia chunk, tạo vector, lưu và kiểm tra](assets/ingestion-pipeline.svg)

Chọn tài liệu được phép sử dụng; giữ **ID tài liệu, nguồn, trang/vị trí** và metadata phù hợp. Dùng embedding model thật qua API hoặc chạy local; lưu và truy xuất bằng pgvector, Qdrant, Chroma hoặc một store tương đương.

## 2. So sánh và đánh giá

![Ba chiến lược được đánh giá trên cùng corpus và benchmark dev/test](assets/benchmark-workflow.svg)

Dùng cùng dữ liệu, model và câu hỏi cho cả ba cấu hình. Tách **15 câu dev / 5 câu test** trước khi chạy; chọn cấu hình trên dev, rồi đánh giá test sau khi cố định. Mỗi câu hỏi cần có đoạn bằng chứng và trang nguồn; thiết kế bộ câu hỏi và đánh giá theo [BENCHMARK.md](BENCHMARK.md).

Đánh giá theo năm khía cạnh: **độ chính xác truy xuất**, **tính mạch lạc của chunk**, **tính hữu dụng của metadata**, **chất lượng grounding** và **tác động của chiến lược dữ liệu**. Giải thích lựa chọn bằng kết quả, ví dụ lỗi và các đánh đổi.

## 3. Chuẩn bị bài nộp

1. Chạy pipeline và lưu cấu hình, kết quả top-3, trace cùng nhãn đánh giá thủ công.
2. Điền [thông tin học viên](STUDENT.md), [nhật ký thí nghiệm](artifacts/experiment_log.csv) và bản sao [mẫu báo cáo cá nhân](report/individual/MSSV_HoTen.md).
3. Kiểm tra mã nguồn, cách chạy, manifest dữ liệu và checklist trong [SUBMISSION.md](SUBMISSION.md).

## Tài liệu hướng dẫn

| Bạn cần tìm | Tài liệu |
|---|---|
| Cài và chạy pipeline E5 + Qdrant local | [starter/README.md](starter/README.md) |
| Các bước làm và cách tính chỉ số | [GUIDE.md](GUIDE.md) |
| Tiến độ trong 4 giờ | [CHECKPOINTS.md](CHECKPOINTS.md) |
| Năm tiêu chí benchmark và bộ câu hỏi | [BENCHMARK.md](BENCHMARK.md) |
| Tiêu chí chấm điểm | [RUBRIC.md](RUBRIC.md) |
| Quy tắc sử dụng dữ liệu, AI và API | [RULES.md](RULES.md) |
| Cách nộp bài | [SUBMISSION.md](SUBMISSION.md) |

[data/format-example.json](data/format-example.json) chỉ minh họa định dạng, không phải corpus đủ điều kiện. Phần xử lý và benchmark do bạn tự hiện thực; không bắt buộc xây chatbot.

## Bài làm cá nhân

Phần trên là hướng dẫn gốc. Phần này mô tả bài làm đã thực hiện và cách tái lập.

### Dữ liệu, mã nguồn và hồ sơ nộp

| Thành phần | Vị trí trong repo |
|---|---|
| Thông tin học viên | [STUDENT.md](STUDENT.md) |
| Corpus Pro Git và quy tắc đếm | [Corpus JSONL](data/progit-v2-en.jsonl) · [Manifest](data/manifest.json) |
| Pipeline Python và hướng dẫn cài đặt | [Mã nguồn](starter/src/) · [Hướng dẫn](starter/README.md) |
| Câu hỏi, dev/test và gold evidence | [Bộ câu hỏi](benchmark/questions.jsonl) · [Cách chia tập và tiêu chí chọn](benchmark/README.md) |
| Cấu hình và nhật ký thí nghiệm | [Cấu hình chốt trước test](results/selection.json) · [Nhật ký A/B/C](artifacts/experiment_log.csv) |
| Kết quả, nhãn và log lỗi | [Thư mục results](results/) · [Log kiểm tra đầu vào lỗi](results/pipeline_errors.log) |
| Báo cáo cá nhân | [2A202603492_NguyenNhutLinh.md](report/individual/2A202603492_NguyenNhutLinh.md) |

Corpus gồm **32 mục tiếng Anh** từ *Pro Git, Second Edition*, với **416.462 ký tự** sau chuẩn hóa. Mỗi mục có ID, URL tới nguồn tại commit cố định và tên chương dùng làm metadata `section`. Manifest ghi ranh giới từng mục, các mục bị loại, cách đếm và giấy phép [CC BY-NC-SA 3.0](https://creativecommons.org/licenses/by-nc-sa/3.0/).

### Cài đặt và tái lập benchmark

Môi trường đã kiểm chứng là Linux với Python 3.14.4. Pipeline dùng **multilingual-e5-small** revision `614241f622f53c4eeff9890bdc4f31cfecc418b3`, chạy CPU bằng ONNX Runtime 1.31.1 để tạo vector 384 chiều. Qdrant local 1.20.0 lưu vector và metadata trong `starter/.qdrant/`. Chi phí API là **0 USD**. [Phiên bản thư viện](starter/requirements-local.txt)

Từ gốc repo, tạo môi trường và tải đúng phiên bản model:

```bash
cd starter
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-local.txt

mkdir -p .models
model_url=https://huggingface.co/intfloat/multilingual-e5-small/resolve/614241f622f53c4eeff9890bdc4f31cfecc418b3/onnx
curl -fL --retry 2 -o .models/tokenizer.json "$model_url/tokenizer.json"
curl -fL --retry 2 -o .models/model.onnx "$model_url/model.onnx"
```

Chạy tiếp từ `starter/`. Dùng cùng một thư mục kết quả mới cho hai lệnh:

```bash
run_dir=$(mktemp -d /tmp/day06-rerun.XXXXXX)
python -m src.benchmark dev --results-dir "$run_dir" &&
python -m src.benchmark test --results-dir "$run_dir"
```

Lượt dev tạo index và ghi `selection.json`. Lượt test kiểm tra lại hash corpus, benchmark, cấu hình và alias index trước khi chạy. Các kết quả đã nộp nằm trong [results/](results/).

### Cấu hình và kết quả đã chốt

Cả ba cấu hình dùng cùng corpus, model, Qdrant local và truy xuất top-3 theo cosine chính xác.

| Cấu hình | Chia chunk | Lọc metadata |
|---|---|---|
| A | Cửa sổ 500 ký tự, overlap 50 | Không lọc |
| B | Theo tiêu đề và đoạn, tối đa 500 ký tự | Không lọc |
| C | Dùng chung chunk và vector với B | Lọc `section` khi câu hỏi chỉ định chương |

Benchmark có **15 câu dev và 5 câu test**, mỗi tập có 2 câu chỉ định filter. **A được chọn trên dev** vì cả ba cùng đạt Evidence Hit@3 là 3/15 và A có Hit@1 cao hơn.

| Cấu hình | Dev Hit@1 | Dev Evidence Hit@3 | Test Hit@1 | Test Evidence Hit@3 |
|---|---:|---:|---:|---:|
| A | 2/15 | 3/15 | 0/5 | 0/5 |
| B | 1/15 | 3/15 | 0/5 | 0/5 |
| C | 1/15 | 3/15 | 0/5 | 0/5 |

Bảng dùng phép chấm tự động yêu cầu một chunk chứa trọn đoạn trích trên đúng trang. Khi đối chiếu thêm câu `q18`, chunk hạng 3 của B và C có bằng chứng tương đương đủ trả lời, nên Evidence Hit@3 test sau đối chiếu là **A 0/5, B 1/5, C 1/5**. [Trace dev](results/dev_traces.jsonl) · [Trace test](results/test_traces.jsonl) · [Đối chiếu q18](results/evidence_review.csv)

Kết quả đã lưu gồm 60 lượt truy xuất và 180 bản ghi top-3. C đáp ứng filter trên cả 2 câu test có chỉ định chương. Học viên đã xem qua và đồng ý giữ điểm mạch lạc và grounding do Codex đề xuất. Phương pháp, lý do chấm và giới hạn của tập test 5 câu được ghi trong báo cáo. [Mạch lạc](results/coherence_audit.csv) · [Metadata](results/metadata_audit.csv) · [Grounding](results/grounding_audit.csv)
