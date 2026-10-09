# Task 02: Chuẩn hoá biến môi trường

## Mục tiêu
Có một file `.env.example` ở root liệt kê ĐỦ biến mà 4 file config đang đọc, và app đọc được `.env` cả khi chạy trong Docker lẫn chạy local bằng venv.

## Phạm vi (Scope)
- Files cần tạo/chỉnh sửa:
  - `.env.example` (mới, ở root)
  - `document_setup/src/configs/app.py`, `write_reports/src/configs/app.py`,
    `ai_chatbot/src/configs/app.py`, `data_analysis/src/configs/app.py`
    → chỉ đổi `env_file="/app/.env"` thành `env_file=("/app/.env", ".env")`
- Files KHÔNG được chạm tới: listener, module logic
- Dependencies: không

## Các bước thực hiện
1. Gom biến từ 4 file config (đã liệt kê):
   KAFKA, REDIS, REDIS_HOST, REDIS_PORT, REDIS_PWD, REDIS_TTL, REDIS_STACK,
   MONGO_CONNECTION_STRING, QDRANT_URL, EMBEDDING_MODEL,
   MINIO_ENDPOINT, MINIO_PORT, MINIO_ACCESS_KEY_ID, MINIO_SECRET_ACCESS_KEY,
   MINIO_DOMAIN, MINIO_PREFIX, MINIO_BUCKET_ANALYSIS,
   OPEN_AI_KEY, GEMINI_KEY, SERP_KEY, OPEN_ALEX_EMAIL, OPEN_ALEX_USER, OPEN_ALEX_KEY,
   API_KEY_ID, TMP_FOLDER, LOCALLLM_BASE_URL
2. Viết `.env.example` với giá trị mặc định trỏ vào hạ tầng local (localhost).
3. Sửa `env_file` trong 4 file config.
4. `cp .env.example .env` rồi điền API key thật.

## Tiêu chí hoàn thành (Done Criteria)
- [x] `python -c "from write_reports.src.configs.app import settings; print(settings.KAFKA)"` in đúng giá trị từ `.env` (KAFKA = 'localhost:9092')
- [x] `.env` không bị commit (đã thêm vào .gitignore)

## Ghi chú / Rủi ro
- Hiện tại 4 file config chỉ đọc `/app/.env` → chạy local bằng venv sẽ ra chuỗi rỗng (chính là lỗi `Unable to bootstrap from ('', 9092)`).
- Trong Docker vẫn chạy được vì compose truyền `env_file: .env` thành biến môi trường.
