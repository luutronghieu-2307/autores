# Task 03: docker-compose cho hạ tầng

## Mục tiêu
Một lệnh `docker compose -f docker-compose-infra.yaml up -d` dựng đủ Kafka, Redis Stack, MongoDB, Qdrant, MinIO.

## Phạm vi (Scope)
- Files cần tạo/chỉnh sửa: `docker-compose-infra.yaml` (mới)
- Files KHÔNG được chạm tới: các `docker-compose-*.yaml` cũ (giữ nguyên để tham khảo)
- Dependencies: Task 01, Task 02

## Các bước thực hiện
1. Kafka: `apache/kafka` chế độ KRaft (không cần Zookeeper), port 9092.
2. Kafka UI (`provectuslabs/kafka-ui`), port 8080 – để xem message bằng mắt.
3. Redis Stack (`redis/redis-stack-server`), port 6379, có password – dùng chung cho `REDIS_HOST` và `REDIS_STACK`.
4. MongoDB (`mongo:7`), port 27017, có user/pass.
5. Qdrant (`qdrant/qdrant`), port 6333.
6. MinIO (`minio/minio`), port 9000 (API) + 9001 (console).
7. Mỗi service có volume riêng + healthcheck + `restart: unless-stopped`.

## Tiêu chí hoàn thành (Done Criteria)
- [x] `docker compose -f docker-compose-infra.yaml ps` → tất cả `healthy` (Kafka, Redis, Mongo, Qdrant, MinIO)
- [x] Mở được Kafka UI (localhost:8080 - HTTP 200), MinIO console (localhost:9001 - HTTP 200), Qdrant dashboard (localhost:6333/dashboard - HTTP 200)

## Ghi chú / Rủi ro
- Không mở port DB ra internet khi lên VPS (chỉ bind 127.0.0.1 hoặc dùng firewall).
- `KAFKA_ADVERTISED_LISTENERS` phải đúng IP/host mà app dùng để kết nối.
