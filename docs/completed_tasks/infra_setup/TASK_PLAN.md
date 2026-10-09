# TASK PLAN: Dựng lại toàn bộ hạ tầng autoresearching (để sếp host lên VPS mới)

## Tổng quan
VPS cũ + Harbor registry đã hết hạn → mất Kafka, Redis, MongoDB, Qdrant, MinIO và base image.
Mục tiêu: chạy được **toàn bộ** hệ thống trên máy local bằng Docker, rồi bàn giao một bộ file
(`Dockerfile` + `docker-compose-infra.yaml` + `docker-compose-app.yaml` + `.env.example` + `DEPLOY.md`)
để sếp copy lên VPS mới và chạy `docker compose up -d` là xong.

## Hạ tầng code bắt buộc phải có (đã kiểm tra trong code)
| Thành phần | Bằng chứng trong code | Ghi chú |
|---|---|---|
| Kafka | `producers.py`, `utils.set_num_partitions` | Service chết ngay nếu không kết nối được |
| Redis (+ module RediSearch) | `utils.get_redis_client`, `get_async_redis_checkpoint` (`REDIS_STACK`) | Checkpoint LangGraph cần **redis-stack** |
| MongoDB | `utils.get_mongodb_client`, `get_async_mongo_checkpoint` | Gọi ngay trong `init_singleton()` |
| MinIO (S3) | `utils.get_minio_client`, `get_s3_client` (`MINIO_DOMAIN`) | Gọi ngay trong `init_singleton()` |
| Qdrant | `utils.get_admin_vector_db` | Dùng khi embed / search tài liệu |
| Health-check API (BE) | `utils.send_health_check` → `http://{REDIS_HOST}:4002` | Không thuộc repo này – chỉ gọi khi có key `AI_STATUS:*` |

## Thứ tự thực hiện
1. [x] task_01_tooling.md - Cài Docker Compose v2 (Đã cài v2.40.3), kiểm tra máy đủ tài nguyên
2. [x] task_02_env_config.md - Gom đủ biến môi trường vào `.env.example`, cho phép đọc `.env` khi chạy local
3. [x] task_03_infra_compose.md - Viết `docker-compose-infra.yaml` (Kafka, Redis Stack, Mongo, Qdrant, MinIO)
4. [x] task_04_seed_data.md - Script nạp API key vào Redis (`AI_KEY:*`) + tạo bucket MinIO
5. [x] task_05_app_compose.md - Build image app từ `Dockerfile` mới, viết `docker-compose-app.yaml` cho 4 service
6. [x] task_06_smoke_test.md - Script bắn event `search_papers` vào Kafka và đọc response
7. [x] task_07_deploy_docs.md - Viết `DEPLOY.md` hướng dẫn sếp host lên VPS

## Trạng thái
| Task | Status | Ghi chú |
|---|---|---|
| task_01 | ✅ Done | Docker Compose v2.40.3 hoạt động, docker ps không cần sudo |
| task_02 | ✅ Done | Tạo .env.example, sửa 4 app.py đọc được .env local & container |
| task_03 | ✅ Done | docker-compose-infra.yaml chạy hoàn hảo, 6/6 container healthy |
| task_04 | ✅ Done | scripts/seed_infra.py đã nạp 9 AI_KEY vào Redis và tạo 4 bucket MinIO |
| task_05 | ✅ Done | Build autoresearching-ai:latest, 4 service (doc, write, chat, enhance) đều đang Up và consume Kafka |
| task_06 | ✅ Done | Test Kafka round-trip thành công; fix Pydantic union Gemini bug |
| task_07 | ✅ Done | Tạo file DEPLOY.md hoàn chỉnh hướng dẫn chi tiết triển khai VPS |
