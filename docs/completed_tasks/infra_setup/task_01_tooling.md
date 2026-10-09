# Task 01: Cài Docker Compose v2

## Mục tiêu
Có lệnh `docker compose` (v2) hoạt động, vì `docker-compose` 1.29.2 đang cài quá cũ so với Docker 29.

## Phạm vi (Scope)
- Files cần tạo/chỉnh sửa: không có
- Files KHÔNG được chạm tới: toàn bộ source
- Dependencies: không

## Các bước thực hiện
1. `sudo apt install -y docker-compose-v2`
2. `sudo usermod -aG docker $USER` rồi logout/login (để khỏi gõ sudo)
3. Kiểm tra: `docker compose version`, `docker run --rm hello-world`

## Tiêu chí hoàn thành (Done Criteria)
- [x] `docker compose version` in ra v2.x (Docker Compose version v2.40.3)
- [x] Chạy docker không cần sudo (Đã kiểm tra docker ps thành công)

## Ghi chú / Rủi ro
- `docker-compose` 1.29.2 (bản Python) hay lỗi `KeyError: 'ContainerConfig'` với Docker mới → không dùng nữa.
- Máy hiện có 8 CPU / 15GB RAM → đủ chạy toàn bộ stack (ước tính ~4–5GB RAM).
