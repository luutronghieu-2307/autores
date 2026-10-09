# Task 04: Nạp dữ liệu khởi tạo

## Mục tiêu
Redis có sẵn API key mà `get_key()` cần, MinIO có sẵn bucket – để request đầu tiên không bị lỗi thiếu key.

## Phạm vi (Scope)
- Files cần tạo/chỉnh sửa: `scripts/seed_redis.py`, `scripts/init_minio.sh` (mới)
- Files KHÔNG được chạm tới: `listener.py`
- Dependencies: Task 03

## Các bước thực hiện
1. `get_key(model_id)` trong `listener.py` đọc các key dạng JSON-string:
   - `AI_KEY:<model_id>` (vd `AI_KEY:gemini-2.5-flash`) → LLM key
   - `AI_KEY:db_key` → key embedding (OpenAI)
   - `AI_KEY:search_web_key` → key search web
2. Viết script đọc key từ `.env` rồi `SET` vào Redis (dạng `json.dumps(key)`).
3. Tạo bucket MinIO theo `MINIO_BUCKET` / `MINIO_PREFIX`.

## Tiêu chí hoàn thành (Done Criteria)
- [x] `redis-cli -a <pwd> KEYS 'AI_KEY:*'` có đủ 9 key
- [x] MinIO console thấy 4 bucket (autoresearching, analysis, documents, users)

## Ghi chú / Rủi ro
- Cần hỏi sếp: danh sách `model_id` mà FE/BE sẽ gửi lên (để seed đúng tên key).
- Cần API key thật (Gemini/OpenAI/OpenAlex) – không commit vào repo.
