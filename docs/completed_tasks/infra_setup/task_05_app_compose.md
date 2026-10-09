# Task 05: Build image app + compose cho 4 service

## Mục tiêu
Build image từ `Dockerfile` mới và chạy 4 service (doc, write, chat, enhance) nối vào hạ tầng ở Task 03.

## Phạm vi (Scope)
- Files cần tạo/chỉnh sửa: `docker-compose-app.yaml` (mới), `.dockerignore` (mới), `Dockerfile` (đã viết, chỉ tinh chỉnh nếu build lỗi)
- Files KHÔNG được chạm tới: `main_*.py`, listener
- Dependencies: Task 02, Task 03

## Các bước thực hiện
1. `.dockerignore`: bỏ `venv/`, `__pycache__/`, `.env`, `tasks/`, `.ruff_cache/`.
2. `docker build -t autoresearching-ai:latest .` → sửa lỗi build nếu có.
3. `docker-compose-app.yaml`: 4 service dùng chung image, khác `command` (`main_doc_local.py`, ...), `env_file: .env`, cùng network với infra.
4. Chạy service doc trước, xem log kết nối đủ Kafka/Redis/Mongo/MinIO.

## Tiêu chí hoàn thành (Done Criteria)
- [x] Image build thành công (autoresearching-ai:latest)
- [x] Log service doc không có lỗi kết nối, đang chờ consume topic `document_setup_request_local`
- [x] 4 service cùng chạy ổn định (doc, write, chat, enhance)

## Ghi chú / Rủi ro
- Image có R + thư viện thống kê → khá nặng (~2–3GB), build lần đầu lâu.
- Dùng topic `*_LOCAL` khi test để không đụng production.
