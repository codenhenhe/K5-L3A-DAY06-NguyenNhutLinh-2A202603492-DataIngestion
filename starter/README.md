# Pipeline Pro Git

Pipeline Python đọc [corpus JSONL](../data/progit-v2-en.jsonl), chuẩn hóa Unicode NFC, chia chunk, tạo embedding và lập chỉ mục Qdrant local. Các lệnh dưới đây chạy từ thư mục gốc của repo trên Linux với Python 3.14.

```bash
cd starter
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-local.txt

mkdir -p .models
model_revision=614241f622f53c4eeff9890bdc4f31cfecc418b3
model_url="https://huggingface.co/intfloat/multilingual-e5-small/resolve/$model_revision/onnx"
curl -fL --retry 2 -o .models/tokenizer.json "$model_url/tokenizer.json"
curl -fL --retry 2 -o .models/model.onnx "$model_url/model.onnx"
```

Dùng trọng số ONNX chính thức của [multilingual-e5-small](https://huggingface.co/intfloat/multilingual-e5-small/tree/614241f622f53c4eeff9890bdc4f31cfecc418b3/onnx), chạy CPU với ONNX Runtime. Tài liệu dùng tiền tố `passage: `, truy vấn dùng `query: `. Vector có 384 chiều, lấy trung bình token có mask rồi chuẩn hóa L2. Đầu vào vượt 512 token sẽ báo lỗi. Chi phí API là 0 USD.

```bash
python -m src.run ingest --chunking fixed --size 500 --overlap 50
python -m src.run query 'Cách tạo và chuyển sang nhánh Git mới?' --chunking fixed

python -m src.run ingest --chunking paragraph --size 500
python -m src.run query 'Cách tạo và chuyển sang nhánh Git mới?' --chunking paragraph --section 'Git Branching'
```

- `fixed` chia cửa sổ ký tự có overlap. `paragraph` ghép các đoạn liền kề, bắt đầu chunk mới tại heading AsciiDoc và tách đoạn quá dài. Mỗi chunk giữ `document_id`, `source`, `page`, `section` và offset ký tự trong văn bản đã chuẩn hóa. `char_start` được tính từ 0 và `char_end` là cận loại trừ.
- Qdrant local lưu vào `.qdrant/` với alias `day06_fixed` và `day06_paragraph`. `query` trả top-3 mặc định theo cosine chính xác, gồm ID, nội dung, điểm và metadata. `--section` áp dụng lọc bằng tên chương. Chạy các lệnh truy cập cùng thư mục store lần lượt vì Qdrant local giữ khóa thư mục khi mở.
- Khi corpus đổi, cập nhật JSONL và [manifest](../data/manifest.json), rồi chạy lại `ingest` cho từng kiểu chunk đã dùng. `--corpus` nhận đường dẫn đến snapshot **đầy đủ**. Pipeline kiểm tra dữ liệu, tạo embedding và ghi toàn bộ vào collection mới trước khi chuyển alias. Sau khi chuyển alias, collection trước đó được dọn để bỏ cả chunk của các trang đã xóa. Nạp lại cùng đầu vào giữ nguyên ID và số lượng chunk.
- Thống kê ingest xuất ra JSON. Lỗi đọc, ghi hoặc suy luận làm lệnh trả mã lỗi và ghi chi tiết vào `results/pipeline.log`. Model, dữ liệu Qdrant và log cục bộ được loại khỏi Git.

## Chạy benchmark A/B/C

Từ thư mục `starter/`, chạy hai lệnh theo thứ tự sau. Dùng cùng `--results-dir` cho hai lệnh. Thư mục mới giữ riêng kết quả và index của lần tái lập. Kết quả chính nằm tại `results/` ở thư mục gốc của repo.

```bash
python -m src.benchmark dev --results-dir /tmp/day06-rerun
python -m src.benchmark test --results-dir /tmp/day06-rerun
```

Dev nạp hai index và lưu `selection.json` trước khi có kết quả test. B và C truy vấn chung index theo heading/đoạn. Chỉ C áp dụng `section` nếu benchmark đã cung cấp. Test kiểm tra lại hash corpus, bộ câu hỏi, tham số và alias index. Cả hai lượt lưu chỉ số và trace top-3 theo từng câu. Khi dùng thư mục kết quả mặc định, lượt test cũng điền `artifacts/experiment_log.csv`.

Hit tự động yêu cầu toàn bộ đoạn trích nằm trong một chunk đúng nguồn và trang, kể cả nguồn thay thế đã ghi. Một kết quả có bằng chứng tương đương cần được kiểm tra thủ công.

## Starter PostgreSQL + pgvector (tùy chọn)

Bộ khởi động **tùy chọn** cho lab cá nhân. Docker Compose tạo PostgreSQL + pgvector local để kiểm tra kết nối nếu muốn thử backend này. Pipeline ở trên dùng Qdrant local.

## Cấu trúc

```text
starter/
├── docker-compose.yml     # PostgreSQL 16 + pgvector, chỉ mở cổng local
├── init.sql               # bật extension khi tạo database mới
├── requirements.txt       # psycopg, pypdf và python-dotenv
├── .env.example           # cấu hình mẫu; copy thành .env
├── scripts/check_setup.py # kiểm tra kết nối và extension (đã chạy được)
├── src/
│   ├── models.py          # cấu trúc dữ liệu mẫu
│   ├── ingestion.py       # đọc và chuẩn hóa tài liệu
│   ├── chunking.py        # chia chunk
│   ├── embeddings.py      # embedding E5 local
│   ├── store.py           # lưu và tìm kiếm trong Qdrant local
│   ├── evaluation.py      # chấm tự động và tạo trace
│   ├── benchmark.py       # chạy dev, chốt cấu hình và chạy test
│   └── run.py             # lệnh ingest và query
├── data/                  # bạn tự chuẩn bị corpus được phép sử dụng
└── results/               # lưu log và kết quả
```

### Cài và kiểm tra database

Cần Docker Desktop hoặc Docker Engine + Compose, Python **3.11–3.14**, và mạng để tải image/dependencies lần đầu. Các lệnh sau chạy từ thư mục `starter/`:

```bash
cd starter
python3 -m venv .venv
```

Kích hoạt `.venv`: macOS/Linux dùng `source .venv/bin/activate`; Windows PowerShell dùng `.venv\Scripts\Activate.ps1`. Sau đó:

```bash
python -m pip install -r requirements.txt
# macOS/Linux: cp .env.example .env
# Windows PowerShell: Copy-Item .env.example .env
docker compose -p day6_student_starter up -d --wait
python scripts/check_setup.py
```

Kỳ vọng: hiện tên database, phiên bản PostgreSQL và pgvector, sau đó `Setup OK`. Đây **chỉ là kiểm tra hạ tầng**, không phải kết quả benchmark. Docker dùng cổng `127.0.0.1:55433` và mật khẩu cố định **chỉ dùng local cho lab**; nếu cổng bận, sửa đồng thời port trong `docker-compose.yml` và `DATABASE_URL` trong `.env`. `init.sql` chỉ chạy khi volume mới được tạo; nếu database sẵn có chưa bật extension, xem log Docker và kiểm tra cấu hình thay vì xóa volume chứa dữ liệu.

Dừng container nhưng giữ dữ liệu:

```bash
docker compose -p day6_student_starter stop
```
