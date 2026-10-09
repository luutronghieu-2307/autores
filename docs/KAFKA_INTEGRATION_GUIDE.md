# 📡 HƯỚNG DẪN TÍCH HỢP KAFKA EVENT CONTRACT (DÀNH CHO CORE BACKEND / FE)

> **Mục đích:** Tài liệu này đặc tả toàn bộ danh sách Kafka Topics, Event Types, quy ước Request / Response JSON Schema và cơ chế quản lý trạng thái của cụm **AI Engine (autoresearching)** để kết nối với Frontend (FE) và Backend chính (CRM / Core Gateway).

---

## 1. THÔNG TIN HẠ TẦNG KẾT NỐI (INFRASTRUCTURE)

- **Kafka Broker Endpoint:**
  - Môi trường Local / Dev: `localhost:9092` (hoặc `<IP_LAN_MAY_AI>:9092`)
  - Môi trường Staging / Production: `<IP_SERVER_VPS>:9092`
- **Giao thức:** Apache Kafka Message Queue (Định dạng payload: `JSON UTF-8`)
- **Web UI Quản lý Kafka (Trực quan hóa message):** `http://<IP_KAFKA>:8080`

---

## 2. DANH SÁCH 4 CẶP KAFKA TOPICS CHÍNH

| STT | Phân hệ nghiệp vụ | Request Topic (FE/Core gửi vào) | Response Topic (AI trả kết quả ra) |
|---|---|---|---|
| **1** | **Chuẩn bị tài liệu & Ý tưởng** | `document_setup_request_local` | `document_setup_response_local` |
| **2** | **Viết báo cáo, chuyên đề & Slide** | `write_section_request_local` | `write_section_response_local` |
| **3** | **AI Chatbot (Hỏi đáp, trao đổi)** | `chatbot_request_local` | `chatbot_response_local` |
| **4** | **Nâng cao văn bản & Gợi ý** | `enhancement_request_local` | `enhancement_response_local` |

*(Lưu ý: Ở môi trường Production thực tế, bỏ hậu tố `_local` ở cuối tên topic).*

---

## 3. CÁC TRƯỜNG ĐỊNH DANH BẮT BUỘC TRONG MỌI REQUEST

Mọi JSON gửi vào Kafka Request Topic đều **PHẢI** chứa 4 trường định danh sau:

```json
{
  "event_type": "<tên_sự_kiện_cụ_thể>",
  "model_id": "localhost",
  "user_id": "user_id_cua_khach_hang",
  "document_id": "doc_id_cua_du_an_nghien_cuu",
  "session_id": "session_id_phien_lam_viec",
  "language": "Vietnamese"
}
```

* `model_id`: Dùng `"localhost"` (trỏ qua Groq proxy), hoặc `"gpt-4o"`, `"gemini-2.5-flash"`.
* `document_id` & `session_id`: Dùng để FE/Core Backend nhận diện kết quả trả về của đúng người dùng khi có nhiều request đồng thời.

---

## 4. QUY ƯỚC TIẾN TRÌNH XỬ LÝ (STATUS & ERROR CODES)

Trong quá trình AI xử lý, AI sẽ publish các message cập nhật trạng thái vào `Response Topic`:

### 4.1. Bảng mã trạng thái (`processStatus`):
* `1` - **`PENDING`**: Đã nhận yêu cầu vào hàng đợi.
* `2` - **`PROCESSING`**: AI đang phân tích / cào dữ liệu / viết nội dung (FE hiển thị loading / progress bar).
* `3` - **`FINISHED`**: Xử lý hoàn tất 100%, trả kèm toàn bộ dữ liệu kết quả trong `message`.
* `4` - **`ERROR`**: Gặp lỗi trong quá trình xử lý (kèm `aiError`).

### 4.2. Cấu trúc phản hồi lỗi khi `processStatus = 4`:
```json
{
  "eventType": "search_papers",
  "processStatus": 4,
  "aiError": {
    "errorCode": 610,
    "error": "Mô tả chi tiết nguyên nhân lỗi"
  }
}
```

---

## 5. ĐẶC TẢ CHI TIẾT CÁC EVENT TIÊU BIỂU (INPUT / OUTPUT SCHEMA)

### 📌 Nhóm 1: Chuẩn bị tài liệu (`document_setup_request_local`)

#### 1.1. `event_type`: `search_papers` (Tìm kiếm bài báo khoa học)
* **Mục đích:** Tìm bài báo quốc tế theo từ khóa, lọc theo năm, open access và xếp hạng Scimago Q1-Q4.
* **Input Request:**
```json
{
  "event_type": "search_papers",
  "model_id": "localhost",
  "user_id": "user_01",
  "document_id": "doc_01",
  "session_id": "sess_01",
  "language": "Vietnamese",
  "field": "Kinh tế",
  "domain": "Thương mại điện tử",
  "subdomains": ["Livestream commerce"],
  "query": "Hành vi người tiêu dùng livestream",
  "country_filter": "both",
  "oa_filter": false,
  "is_oa": false,
  "is_tool": false,
  "downloaded_papers": [],
  "cut_off_year_low": 2022,
  "cut_off_year_high": 2025,
  "search_range": "all",
  "use_web_search": false
}
```
* **Output Response (khi `FINISHED`):**
```json
{
  "event_type": "search_papers",
  "document_id": "doc_01",
  "user_id": "user_01",
  "session_id": "sess_01",
  "papers": [
    {
      "title": "When we are alike: homophily in livestream commerce",
      "user_language_title": "Khi chúng ta giống nhau: sự đồng điệu trong thương mại livestream",
      "year": "2025",
      "authors": ["Yijia Cao", "Yusuf Oc"],
      "journal": "Journal of Consumer Marketing",
      "q": "Q1",
      "url": "https://doi.org/10.1108/jcm-03-2024-6668",
      "open_access": false,
      "status": "Peer-reviewed",
      "citation": 12
    }
  ],
  "input_tokens": 5205,
  "output_tokens": 5256
}
```

---

#### 1.2. `event_type`: `generate_domains` (Gợi ý ngành / lĩnh vực nghiên cứu)
* **Input Request:**
```json
{
  "event_type": "generate_domains",
  "model_id": "localhost",
  "user_id": "user_01",
  "document_id": "doc_01",
  "session_id": "sess_01",
  "language": "Vietnamese",
  "field": "Kinh tế học",
  "query": "Xu hướng kinh tế số và thương mại điện tử"
}
```

---

#### 1.3. `event_type`: `generate_outline` (Sinh đề cương / dàn ý nghiên cứu)
* **Input Request:**
```json
{
  "event_type": "generate_outline",
  "model_id": "localhost",
  "user_id": "user_01",
  "document_id": "doc_01",
  "session_id": "sess_01",
  "language": "Vietnamese",
  "field": "Kinh tế",
  "domain": "Thương mại điện tử",
  "subdomains": ["Livestream commerce"],
  "title": "Tác động của Livestream bán hàng đến quyết định mua sắm của Gen Z",
  "description": "Nghiên cứu định lượng tại thị trường Việt Nam",
  "num_chapters": 5
}
```

---

### 📌 Nhóm 2: AI Chatbot (`chatbot_request_local`)

#### 2.1. `event_type`: `outer_chatbot` (Chatbot tư vấn học thuật chung)
* **Input Request:**
```json
{
  "event_type": "outer_chatbot",
  "model_id": "localhost",
  "user_id": "user_01",
  "session_id": "sess_chat_01",
  "language": "Vietnamese",
  "message": "Phương pháp nghiên cứu định lượng PLS-SEM có những ưu điểm gì so với CB-SEM?",
  "history": [
    {"role": "user", "content": "Xin chào AI"},
    {"role": "assistant", "content": "Chào bạn! Tôi có thể giúp gì cho nghiên cứu của bạn?"}
  ]
}
```
* **Output Response:**
```json
{
  "event_type": "outer_chatbot",
  "user_id": "user_01",
  "session_id": "sess_chat_01",
  "response": "PLS-SEM (Partial Least Squares Structural Equation Modeling) có nhiều ưu điểm nổi bật: 1. Thích hợp với mẫu nhỏ, 2. Xử lý tốt các mô hình phức tạp...",
  "input_tokens": 320,
  "output_tokens": 450
}
```

---

### 📌 Nhóm 3: Viết nội dung & Báo cáo (`write_section_request_local`)

#### 3.1. `event_type`: `write_content` (Viết nội dung cho 1 mục theo đề cương)
* **Input Request:**
```json
{
  "event_type": "write_content",
  "model_id": "localhost",
  "user_id": "user_01",
  "document_id": "doc_01",
  "session_id": "sess_01",
  "language": "Vietnamese",
  "section_title": "1.2. Tổng quan các nghiên cứu thực nghiệm trong nước và quốc tế",
  "outline_context": "Chương 1: Tổng quan nghiên cứu",
  "references": [
    {
      "title": "When we are alike: homophily in livestream commerce",
      "authors": ["Yijia Cao", "Yusuf Oc"],
      "year": "2025"
    }
  ]
}
```

---

## 6. CHECKLIST ĐẤU NỐI DÀNH CHO DEVELOPER (CORE BE / FE)

1. [ ] Cài đặt Kafka Client (Node.js dùng `kafkajs`, Java dùng `spring-kafka`, Python dùng `aiokafka`).
2. [ ] Tạo Kafka Producer kết nối tới `IP:9092` để đẩy request vào topic `*_request_local`.
3. [ ] Tạo Kafka Consumer lắng nghe topic `*_response_local` và lọc message theo `document_id` / `session_id`.
4. [ ] Bắn thử request `search_papers` mẫu ở Mục 5.1 và kiểm tra dữ liệu nhận về.
