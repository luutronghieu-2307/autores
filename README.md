# 🧠 AutoResearching — AI Backend Microservices

> Hệ thống AI Backend hỗ trợ nghiên cứu khoa học tự động, tạo đề tài, tìm kiếm tài liệu (RAG), viết báo cáo chuyên đề và phân tích dữ liệu thống kê.  
> Kiến trúc **Event-Driven Microservices** giao tiếp bất đồng bộ qua **Apache Kafka**.

---

## 🏗️ Kiến trúc & 4 Dịch vụ AI chính

```
                       ┌───────────────────────────────┐
                       │     Apache Kafka (Broker)     │
                       │   Request / Response Topics   │
                       └───┬───────────┬───────────┬───┘
                           │           │           │
            ┌──────────────┴──┐ ┌──────┴─────┐ ┌───┴──────────────┐
            ▼                 ▼ ▼            ▼ ▼                  ▼
    ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
    │  DOC SERVICE  │ │ WRITE SERVICE │ │ CHAT SERVICE  │ │ENHANCE SERVICE│
    │  (Đề tài, RAG,│ │ (Viết bài báo,│ │ (Chatbot inner│ │ (Gợi ý văn    │
    │   outline)    │ │  slide, v.v.) │ │   & outer)    │ │  bản AI inDoc)│
    └───────┬───────┘ └───────┬───────┘ └───────┬───────┘ └───────┬───────┘
            └─────────────────┼─────────────────┼─────────────────┘
                              ▼                 ▼
                       ┌───────────────────────────────┐
                       │    CƠ SỞ DỮ LIỆU & HẠ TẦNG    │
                       │ • Redis Stack (Cache/State)   │
                       │ • MongoDB (Documents/History) │
                       │ • Qdrant (Vector DB / RAG)    │
                       │ • MinIO (S3 Object Storage)   │
                       │ • LiteLLM Proxy (Groq/Local)  │
                       └───────────────────────────────┘
```

---

## ⚡ Triển khai nhanh trên VPS Linux (1-Click Deploy)

Hệ thống cung cấp script [`deploy.sh`](deploy.sh) tự động kiểm tra toàn bộ môi trường (OS, CPU, RAM, Docker, dependencies), cấu hình hạ tầng và khởi chạy cả 4 AI services.

### 1. Chuẩn bị
```bash
# Clone repository
git clone <repo_url> autoresearching
cd autoresearching

# Tạo file cấu hình từ template
cp .env.example .env
nano .env   # Điền GROQ_API_KEY (hoặc OPEN_AI_KEY, GEMINI_KEY)
```

### 2. Chạy Deploy
```bash
chmod +x deploy.sh
./deploy.sh
```

---

## 🎛️ Các tùy chọn chạy Deploy (`deploy.sh`)

| Lệnh | Mục đích | Khi nào dùng? |
|---|---|---|
| `./deploy.sh` | **Deploy toàn diện**: Kiểm tra môi trường → khởi động hạ tầng → build Docker image → start 4 AI service → health check. | Triển khai lần đầu trên VPS mới. |
| `./deploy.sh --skip-build` | **Deploy nhanh**: Bỏ qua bước build image, dùng lại image `autoresearching-ai:latest` đã có sẵn. | Khi chỉ restart hoặc cập nhật cấu hình mà không thay đổi Dockerfile/code dependencies. |
| `./deploy.sh --infra-only` | **Chỉ khởi động hạ tầng**: Kafka, Redis Stack, MongoDB, Qdrant, MinIO, Kafka UI, LiteLLM Proxy và nạp seed data. | Khi muốn chạy hạ tầng trên Docker nhưng chạy 4 AI service trực tiếp từ Python venv để debug code. |
| `./deploy.sh --app-only` | **Chỉ khởi động 4 AI service**: Re-build và start lại 4 container AI (yêu cầu hạ tầng đã chạy). | Khi vừa cập nhật mã nguồn AI modules/listeners và muốn redeploy app nhanh. |

---

## 🌐 Danh sách Cổng Dịch vụ & Web UI

| Dịch vụ | Địa chỉ Web / Cổng | Tài khoản / Mật khẩu | Ghi chú |
|---|---|---|---|
| **Kafka UI** | `http://<IP_VPS>:8080` | *(Không cần login)* | Quản lý topic, message, consumer group |
| **MinIO Console** | `http://<IP_VPS>:9001` | `minio_admin` / `minio_password_local` | Quản lý file, bucket S3 lưu trữ |
| **Qdrant Dashboard**| `http://<IP_VPS>:6333/dashboard` | *(Không cần login)* | Quản lý Vector collections & RAG |
| **LiteLLM Proxy** | `http://<IP_VPS>:8000` | *(Tích hợp Groq)* | Endpoint chuẩn OpenAI API (`localhost:8000/v1`) |
| **Redis Stack** | `Port 6379` | pass: `redis_password_local` | Cache & LangGraph Checkpointer |
| **MongoDB** | `Port 27017` | `root` / `mongo_password_local` | Document database |
| **Kafka Broker** | `Port 9092` | PLAINTEXT | Broker chính cho event bus |

---

## 🛠️ Quản trị & Vận hành Thường dùng

```bash
# Xem log realtime của một service AI
docker logs -f autoresearching-doc      # Document setup
docker logs -f autoresearching-write    # Write reports
docker logs -f autoresearching-chat     # AI Chatbot
docker logs -f autoresearching-enhance  # Enhancement

# Khởi động lại riêng 4 AI service
docker compose -f docker-compose-app.yaml restart

# Dừng toàn bộ hệ thống (App + Hạ tầng)
docker compose -f docker-compose-infra.yaml -f docker-compose-app.yaml down

# Nạp lại dữ liệu khởi tạo (Redis keys, S3 Buckets)
python3 scripts/seed_infra.py
```

---

## 📖 Tài liệu chi tiết khác

- 📑 [DEPLOY.md](DEPLOY.md): Hướng dẫn triển khai thủ công chi tiết từng bước & cấu hình tường lửa.
- 📑 [DOCS_INDEX.md](DOCS_INDEX.md): Danh mục tài liệu kỹ thuật & quy chuẩn kiến trúc của từng module.
- 📑 [AGENTS.md](AGENTS.md): Quy chuẩn clean code và tài liệu hướng dẫn dành cho AI coding assistant.
