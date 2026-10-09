# Task 07: Tài liệu bàn giao cho sếp host VPS

## Mục tiêu
`DEPLOY.md` đủ để sếp làm theo trên VPS trắng mà không cần hỏi lại.

## Phạm vi (Scope)
- Files cần tạo/chỉnh sửa: `DEPLOY.md` (mới)
- Files KHÔNG được chạm tới: Jenkinsfile (ghi chú là đang trỏ server cũ, xử lý sau)
- Dependencies: Task 01–06

## Các bước thực hiện
1. Yêu cầu VPS tối thiểu (CPU/RAM/disk, Ubuntu 24.04, Docker + compose v2).
2. Các bước: clone repo → `cp .env.example .env` → điền key → `up` infra → seed → `up` app → smoke test.
3. Bảo mật: đổi password mặc định, firewall chỉ mở port cần thiết.
4. Vận hành: xem log, restart, backup volume Mongo/MinIO/Qdrant.

## Tiêu chí hoàn thành (Done Criteria)
- [x] Đã tạo file `DEPLOY.md` hoàn chỉnh, chi tiết từng bước từ cài đặt môi trường, cấu hình .env, chạy hạ tầng, nạp seed data đến khởi chạy và test ứng dụng.
- [x] Đã ghi chú đầy đủ danh sách cổng kết nối, tài khoản/mật khẩu mặc định và giao diện Web UI (Kafka UI, MinIO, Qdrant).
- [x] Đã hướng dẫn chi tiết cách bảo mật, xem logs thời gian thực và backup volumes.
- [x] Đã làm rõ sự tách biệt với Backend CRM (port 4002) và kế hoạch cập nhật CI/CD Jenkins khi có VPS mới.

## Ghi chú / Rủi ro
- Health-check API (port 4002) là service của BE, không nằm trong repo này → đã ghi rõ trong DEPLOY.md.
- Jenkinsfile đang SSH vào `192.168.3.140` (server cũ) → đã ghi chú trong DEPLOY.md cần cập nhật khi có VPS mới.
