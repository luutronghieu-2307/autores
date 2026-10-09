# 🎨 TÀI LIỆU ĐẶC TẢ TỪNG TASK FRONTEND (FE) — PHÂN HỆ DOCUMENT SETUP

> **Mục tiêu tài liệu:** Cung cấp thông tin chi tiết cho đội ngũ Frontend (FE) và UI/UX Designer để xây dựng toàn bộ giao diện, luồng tương tác, Input/Output payload và xử lý trạng thái cho phân hệ **Document Setup** (Khởi tạo đề tài & thiết lập tài liệu nghiên cứu).

---

## 🏛️ 1. KIẾN TRÚC TỔNG THỂ & LUỒNG TƯƠNG TÁC DỮ LIỆU

### 1.1. Cơ chế kết nối FE ↔ Core Backend Gateway ↔ AI Engine (Kafka)
Vì cụm AI Engine hoạt động theo mô hình **Event-driven qua Kafka**, Frontend sẽ kết nối thông qua **Core Backend Gateway**:

```
[ FE Client (Web App) ]
       │ ▲
       │ │  HTTP POST / REST API (Gửi request)
       │ │  SSE (Server-Sent Events) hoặc WebSocket (Nhận progress & kết quả realtime)
       ▼ │
[ Core Backend Gateway ]
       │ ▲
       │ │  Kafka Topic: document_setup_request_local
       │ │  Kafka Topic: document_setup_response_local
       ▼ │
[ AI Engine (DocumentSetupEventListener) ]
```

### 1.2. Các trường định danh bắt buộc trong mọi Request Payload
Mỗi request từ FE gửi lên phải đảm bảo có đầy đủ các thông tin ngữ cảnh:
```json
{
  "event_type": "<tên_event>",
  "model_id": "localhost",
  "user_id": "<id_nguoi_dung>",
  "document_id": "<id_du_an_nghien_cuu>",
  "session_id": "<id_phien_lam_viec>",
  "language": "Vietnamese"
}
```

### 1.3. Chu kỳ 4 trạng thái xử lý của AI (`processStatus`)
FE cần lắng nghe `processStatus` để hiển thị UI tương ứng:
- `1` - **`PENDING`**: Request đã vào hàng đợi → Hiển thị badge *"Đang chờ xử lý..."*.
- `2` - **`PROCESSING`**: AI đang chạy LLM / cào dữ liệu OpenAlex / Web Search → Hiển thị Skeleton loading + Progress indicator.
- `3` - **`FINISHED`**: AI hoàn tất → Trả payload dữ liệu kết quả → Render giao diện thành công.
- `4` - **`ERROR`**: Gặp lỗi (`aiError.errorCode`, `aiError.error`) → Hiển thị Toast thông báo lỗi & nút *"Thử lại (Retry)"*.

---

## 📋 2. CHI TIẾT TỪNG TASK FRONTEND (PHÂN HỆ DOCUMENT SETUP)

---

### 🔹 TASK FE-DOC-01: Khởi tạo Lĩnh vực & Gợi ý Chuyên ngành (Field & Domain/Subdomain Selection)

* **Vị trí màn hình:** Bước 1 trong Setup Wizard — *"Xác định hướng nghiên cứu"*.
* **Cần vẽ những gì (UI Components):**
  1. **Field Input Box:** Dropdown chọn ngành lớn (Kinh tế, Công nghệ thông tin, Y sinh, Khoa học xã hội...) hoặc cho phép nhập tay.
  2. **Domain Suggestion Panel:**
     - Nút bấm *"Gợi ý Lĩnh vực nghiên cứu hot"* (kèm bộ đếm số lượng gợi ý `domains_num`, mặc định 5-10).
     - Khung hiển thị danh sách `domains` dạng thẻ (Cards / Tags).
     - Cho phép click chọn 1 domain, hoặc ô text để người dùng tự nhập domain theo ý mình.
  3. **Subdomain Suggestion Panel (Mở sau khi đã có Domain):**
     - Nút bấm *"Gợi ý Hướng nghiên cứu hẹp"* (kèm bộ đếm `subdomains_num`, mặc định 5-10).
     - Danh sách `subdomains` hiển thị dạng Multi-select Chips (chọn nhiều).
     - Ô nhập thêm subdomain thủ công.
* **Input (Dữ liệu gửi đi):**
  - Event 1: `generate_domains`
    ```json
    {
      "event_type": "generate_domains",
      "model_id": "localhost",
      "user_id": "user_01",
      "document_id": "doc_01",
      "session_id": "sess_01",
      "language": "Vietnamese",
      "field": "Kinh tế học",
      "domains_num": 6,
      "is_tool": false
    }
    ```
  - Event 2: `generate_subdomains`
    ```json
    {
      "event_type": "generate_subdomains",
      "model_id": "localhost",
      "user_id": "user_01",
      "document_id": "doc_01",
      "session_id": "sess_01",
      "language": "Vietnamese",
      "field": "Kinh tế học",
      "domain": "Thương mại điện tử",
      "subdomains_num": 6,
      "is_tool": false
    }
    ```
* **Output (Dữ liệu nhận về & hiển thị):**
  - Event 1: `domains: string[]` (Ví dụ: `["Thương mại điện tử", "Kinh tế số", "Tài chính hành vi"]`).
  - Event 2: `subdomains: string[]` (Ví dụ: `["Livestream commerce", "Social commerce", "Hành vi người tiêu dùng Gen Z"]`).
* **Luồng xử lý (Flow):**
  1. Người dùng chọn `field` → Bấm nút "Gợi ý Lĩnh vực" → FE gửi event `generate_domains`.
  2. FE hiển thị hiệu ứng Loading Shimmer ở danh sách domains.
  3. Nhận kết quả `FINISHED` → Render danh sách `domains`.
  4. Người dùng chọn 1 `domain` → Tự động hoặc người dùng bấm "Gợi ý Hướng nghiên cứu" → FE gửi event `generate_subdomains`.
  5. Nhận kết quả → Render danh sách `subdomains` dưới dạng Tag Chips. Người dùng tích chọn 1 hoặc nhiều subdomains ưng ý.
  6. Lưu vào Form State và kích hoạt mở Bước 2 (Sinh từ khóa & đề tài).

---

### 🔹 TASK FE-DOC-02: Bộ sinh Từ khóa & Gợi ý Đề tài Nghiên cứu (Keywords & Title Generation)

* **Vị trí màn hình:** Bước 2 trong Setup Wizard — *"Khám phá ý tưởng & Tên đề tài"*.
* **Cần vẽ những gì (UI Components):**
  1. **Academic Level Selector:** Bộ chọn cấp độ nghiên cứu (Cử nhân / Khóa luận tốt nghiệp `KHOA_LUAN`, Thạc sĩ `LUAN_VAN_THAC_SI`, Tiến sĩ `LUAN_AN_TIEN_SI`, Bài báo `BAI_BAO_KHOA_HOC`, Tiểu luận `TIEU_LUAN`).
  2. **Keyword Generator Box:**
     - Nút bấm *"Tạo bộ từ khóa gợi ý"*.
     - Bảng hiển thị 2 nhóm từ khóa:
       - **Từ khóa chính (`main_keywords`):** Dạng Tag xanh đậm, có nút xóa `x` và nút `+ Thêm từ khóa`.
       - **Từ khóa phụ (`supplementary_keywords`):** Dạng Tag xám, cho phép click để chuyển thành từ khóa chính.
  3. **Title Idea Generator Box:**
     - Toggle Switch *"Tìm kiếm thông tin web mở rộng (Web Search)"* (`use_web_search`: true/false).
     - Nút bấm *"Gợi ý danh sách Đề tài tiềm năng"*.
     - Danh sách đề tài dạng **Proposal Cards**:
       - Tên đề tài gợi ý (`title`).
       - Accordion *"Luận cứ & Tính cấp thiết"* (`rationale`, `thinking`).
       - Khung đánh giá tiêu chuẩn học thuật theo cấp độ (`evaluation`): Điểm mới (novelty), tính khả thi (feasibility), độ chặt chẽ phương pháp (rigor)...
       - Nút chọn đề tài làm đề tài chính (Radio button / "Chọn đề tài này").
       - Checkbox chọn nhiều đề tài phục vụ tính năng trộn đề tài (Mix Titles).
* **Input (Dữ liệu gửi đi):**
  - Sinh từ khóa: `generate_keywords`
    ```json
    {
      "event_type": "generate_keywords",
      "model_id": "localhost",
      "user_id": "user_01",
      "document_id": "doc_01",
      "session_id": "sess_01",
      "language": "Vietnamese",
      "proposal": {
        "field": "Kinh tế",
        "domain": "Thương mại điện tử",
        "subdomains": ["Livestream commerce"]
      }
    }
    ```
  - Sinh danh sách đề tài: `generate_titles`
    ```json
    {
      "event_type": "generate_titles",
      "model_id": "localhost",
      "user_id": "user_01",
      "document_id": "doc_01",
      "session_id": "sess_01",
      "language": "Vietnamese",
      "field": "Kinh tế",
      "domain": "Thương mại điện tử",
      "subdomains": ["Livestream commerce"],
      "level": "LUAN_VAN_THAC_SI",
      "use_web_search": true
    }
    ```
* **Output (Dữ liệu nhận về & hiển thị):**
  - Từ khóa: `keywords: { main_keywords: string[], supplementary_keywords: string[] }`.
  - Đề tài: `proposals: IdeaV2[]` (chứa `idea`, `rationale`, `thinking`, `web_search_result`).
* **Luồng xử lý (Flow):**
  1. FE kích hoạt sinh từ khóa → Hiển thị tags từ khóa để người dùng rà soát, tinh chỉnh.
  2. Người dùng chọn cấp độ học thuật (`level`), chọn bật/tắt Web Search → Bấm "Gợi ý Đề tài".
  3. FE hiển thị Skeleton cards trong trạng thái `PROCESSING`.
  4. Nhận danh sách Proposals → Render các Card đề tài với phân tích chuyên sâu.
  5. Người dùng có 3 lựa chọn:
     - **Option A:** Chọn 1 đề tài ưng ý → Chuyển sang Bước 3 (Chi tiết hóa đề cương sơ bộ).
     - **Option B:** Chọn 2-3 đề tài → Bấm nút "Phối hợp đề tài (Mix Titles)".
     - **Option C:** Tự nhập tên đề tài riêng vào ô "Tự viết tên đề tài".

---

### 🔹 TASK FE-DOC-03: Phối hợp Đề tài & Chi tiết hóa Bản đề xuất (Mix Titles & Proposal Specification)

* **Vị trí màn hình:** Bước 3 trong Setup Wizard — *"Bản đề xuất đề tài chi tiết (Research Proposal)"*.
* **Cần vẽ những gì (UI Components):**
  1. **Mix Titles Action (nếu chọn Option B ở Task 2):**
     - Nút bấm *"Phối hợp các đề tài đã chọn"* (Trigger `mix_titles`).
     - AI trả về đề tài mới kết hợp đa chiều → Cập nhật vào ô Title chính.
  2. **Research Proposal Editor Form:**
     - **Tên đề tài chính thức (`title`):** Input text lớn, cho phép chỉnh sửa trực tiếp.
     - **Đặt vấn đề nghiên cứu (`problem_statement`):** Textarea rich-text mô tả thực trạng và vấn đề chưa giải quyết.
     - **Động lực & Tính cấp thiết (`motivation`):** Textarea nêu lý do thực hiện đề tài.
     - **Thông tin Web Search củng cố (`web_search`):** Khung tóm tắt dẫn chứng thực tế từ internet.
     - **Đánh giá tiêu chuẩn học thuật (`evaluation`):** Nhận xét điểm mạnh, điểm cần lưu ý.
  3. **Chế độ tự nhập đề tài (Option C):**
     - Nếu người dùng tự gõ tiêu đề mà không qua bước gợi ý trước, có nút *"Tự động phân tích & sinh Đặt vấn đề/Động lực"* (Trigger `generate_title_description_no_info`).
* **Input (Dữ liệu gửi đi):**
  - Trường hợp Mix đề tài: `mix_titles`
    ```json
    {
      "event_type": "mix_titles",
      "model_id": "localhost",
      "user_id": "user_01",
      "document_id": "doc_01",
      "session_id": "sess_01",
      "language": "Vietnamese",
      "field": "Kinh tế",
      "domain": "Thương mại điện tử",
      "level": "LUAN_VAN_THAC_SI",
      "proposals": [
        {"title": "Đề tài 1..."},
        {"title": "Đề tài 2..."}
      ]
    }
    ```
  - Trường hợp chi tiết hóa đề tài: `generate_title_description` (hoặc `generate_title_description_no_info`)
    ```json
    {
      "event_type": "generate_title_description",
      "model_id": "localhost",
      "user_id": "user_01",
      "document_id": "doc_01",
      "session_id": "sess_01",
      "language": "Vietnamese",
      "field": "Kinh tế",
      "domain": "Thương mại điện tử",
      "level": "LUAN_VAN_THAC_SI",
      "title": "Tác động của Livestream bán hàng đến quyết định mua sắm của Gen Z",
      "knowledge_base": []
    }
    ```
* **Output (Dữ liệu nhận về & hiển thị):**
  - `proposal: { title, problem_statement, motivation, web_search, evaluation }`.
* **Luồng xử lý (Flow):**
  1. Người dùng kích hoạt sinh chi tiết đề xuất → AI phân tích và trả về bản mô tả đầy đủ.
  2. Dữ liệu được đưa vào Form để người dùng có thể tự gõ bổ sung hoặc chỉnh sửa trực tiếp.
  3. Bấm nút "Lưu đề xuất đề tài" → Lưu vào State dự án và sẵn sàng cho bước tiếp theo.

---

### 🔹 TASK FE-DOC-04: Xác định Phương pháp luận Nghiên cứu (Research Methodology Identification)

* **Vị trí màn hình:** Section tích hợp ở cuối Bước 3 hoặc Popup xác nhận phương pháp.
* **Cần vẽ những gì (UI Components):**
  1. **Research Type Badge & Recommendation Card:**
     - Hiển thị loại hình nghiên cứu AI đề xuất:
       - `0`: **Nghiên cứu Định tính (Qualitative research)** (Phỏng vấn sâu, phân tích tình huống, nghiên cứu hiện tượng học...).
       - `1`: **Nghiên cứu Định lượng (Quantitative research)** (Mô hình SEM/PLS-SEM, khảo sát thang đo Likert, hồi quy...).
       - `2`: **Nghiên cứu Hỗn hợp (Mixed Methods)** (Kết hợp cả định tính và định lượng).
     - Hộp giải thích chi tiết (`reason`): Lý do tại sao đề tài này nên chọn phương pháp đó dựa theo mục tiêu và biến số nghiên cứu.
  2. **Manual Override Toggle:** Bộ 3 nút Radio cho phép người dùng tự đổi loại hình nếu muốn thay đổi theo hướng của giảng viên hướng dẫn.
* **Input (Dữ liệu gửi đi):**
  - Event: `get_research_type`
    ```json
    {
      "event_type": "get_research_type",
      "model_id": "localhost",
      "user_id": "user_01",
      "document_id": "doc_01",
      "session_id": "sess_01",
      "language": "Vietnamese",
      "field": "Kinh tế",
      "domain": "Thương mại điện tử",
      "proposal": {
        "title": "Tác động của Livestream bán hàng đến quyết định mua sắm của Gen Z",
        "problem_statement": "...",
        "motivation": "..."
      }
    }
    ```
* **Output (Dữ liệu nhận về & hiển thị):**
  - `research_type: { type: 0 | 1 | 2, reason: string }`.
* **Luồng xử lý (Flow):**
  1. Sau khi hoàn thành proposal ở Task 3, hệ thống tự động gọi `get_research_type`.
  2. Render card phương pháp kèm huy hiệu nổi bật và lý do giải thích.
  3. Giá trị này (`research_type`) sẽ là input bắt buộc cho khâu sinh Đề cương (Outline) ở các bước sau.

---

### 🔹 TASK FE-DOC-05: Tìm kiếm & Lọc Bài báo Khoa học Quốc tế (Academic Paper Search Engine)

* **Vị trí màn hình:** Bước 4 — *"Tìm kiếm & Thu thập Tài liệu Tham khảo (Literature Review)"*.
* **Cần vẽ những gì (UI Components):**
  1. **Search Bar:** Thanh tìm kiếm chính (`query`), tự động điền sẵn từ khóa từ Đề tài / Keywords, có nút tìm kiếm.
  2. **Filter Toolbar (Bộ lọc chuyên sâu cho nghiên cứu):**
     - **Năm xuất bản (Year Range):** Dual Slider hoặc 2 ô nhập (`cut_off_year_low` đến `cut_off_year_high`, ví dụ 2020 - 2025).
     - **Xếp hạng Scimago (Journal Ranking):** Filter Chips (Tất cả, Q1, Q2, Q3, Q4).
     - **Lọc Open Access (`oa_filter`):** Checkbox chỉ lấy bài báo mở miễn phí toàn văn.
     - **Nguồn gốc (`country_filter`):** Dropdown chọn `vietnam`, `international`, hoặc `both`.
     - **Phạm vi tìm (`search_range`):** Dropdown chọn `all`, `title`, `abstract`.
     - **Mở rộng Google Web Search (`use_web_search`):** Switch On/Off.
  3. **Paper Results Table / Card List:**
     - Tên bài báo gốc tiếng Anh (`title`) + Bản dịch tên bài báo sang tiếng Việt (`user_language_title`).
     - Tác giả (`authors`), Năm (`year`), Tên tạp chí (`journal`).
     - Huy hiệu xếp hạng: Tag đỏ `Q1`, Tag cam `Q2`, Tag xanh `Peer-reviewed`, Tag `Open Access`.
     - Số lượt trích dẫn (`citation`).
     - Nút liên kết ngoài (DOI / URL) mở tab mới.
     - Checkbox "Chọn bài báo này" (Thêm vào Tủ tài liệu tham khảo của đề tài).
  4. **Reference Bucket Drawer (Ngăn kéo Tủ tài liệu):**
     - Thanh ghim nổi bên phải/dưới đếm: *"Đã chọn X bài báo"*.
     - Mở ra xem nhanh danh sách bài báo đã chọn, cho phép xóa bớt trước khi sang bước lập đề cương.
* **Input (Dữ liệu gửi đi):**
  - Event: `search_papers`
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
      "cut_off_year_low": 2021,
      "cut_off_year_high": 2025,
      "search_range": "all",
      "use_web_search": false
    }
    ```
* **Output (Dữ liệu nhận về & hiển thị):**
  - `papers: PaperItem[]`:
    ```json
    [
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
    ]
    ```
* **Luồng xử lý (Flow):**
  1. FE bind các giá trị mặc định từ các bước trước vào bộ lọc.
  2. Người dùng nhấn "Tìm kiếm" → Hiển thị Skeleton loading.
  3. Nhận danh sách bài báo → Render danh sách.
  4. Người dùng lọc theo Q1, lọc năm, tích chọn các bài báo cốt lõi cần trích dẫn.
  5. Danh sách các bài đã chọn (`downloaded_papers` / `selected_papers`) được lưu lại để phục vụ ánh xạ đề cương.

---

### 🔹 TASK FE-DOC-06: Tải lên, Trích xuất & Vector hóa Tài liệu Người dùng (User Docs Ingestion & RAG Indexing)

* **Vị trí màn hình:** Tab phụ trong Bước 4 — *"Tài liệu cá nhân của bạn"*.
* **Cần vẽ những gì (UI Components):**
  1. **Upload Dropzone:** Vùng kéo thả tệp tải lên (hỗ trợ .pdf, .docx).
  2. **Uploaded Documents List:**
     - Danh sách file: Tên file, dung lượng, thời gian tải lên.
     - Trạng thái xử lý theo từng dòng:
       - Icon 1: *Đã tải lên*
       - Icon 2: *Đã trích xuất điểm cốt lõi (Key points extracted)*
       - Icon 3: *Đã lưu trữ vector (Vector DB indexed)*
     - Nút xóa file (Trigger `delete_documents`).
  3. **Key Points Preview Modal:** Khi click vào một bài báo đã upload, xem được danh sách các luận điểm chính (`key_points`) mà AI đã bóc tách từ bài báo đó.
  4. **Action Buttons:**
     - Nút *"Trích xuất dữ liệu tài liệu"* (Trigger `user_documents`).
     - Nút *"Lưu vào bộ nhớ AI (Vector Embed)"* (Trigger `embed_user_documents`).
* **Input (Dữ liệu gửi đi):**
  - Bóc tách nội dung: `user_documents`
    ```json
    {
      "event_type": "user_documents",
      "model_id": "localhost",
      "user_id": "user_01",
      "document_id": "doc_01",
      "session_id": "sess_01",
      "language": "Vietnamese",
      "documents": [
        {
          "file_name": "paper_mau.pdf",
          "file_url": "http://minio.../paper_mau.pdf"
        }
      ]
    }
    ```
  - Vector hóa vào Qdrant: `embed_user_documents`
    ```json
    {
      "event_type": "embed_user_documents",
      "user_id": "user_01",
      "document_id": "doc_01",
      "session_id": "sess_01",
      "language": "Tiếng Việt",
      "processed_docs": [ /* danh sách docs đã qua bóc tách ở bước trên */ ]
    }
    ```
  - Xóa tài liệu: `delete_documents`
    ```json
    {
      "event_type": "delete_documents",
      "collection": "user_documents",
      "documents": [{"uuids": ["uuid_chunk_1", "uuid_chunk_2"]}],
      "data_id": "doc_01"
    }
    ```
* **Output (Dữ liệu nhận về & hiển thị):**
  - `processed_docs: ProcessedDocItem[]` (Mỗi doc có `title`, `key_points`: string[], `publication_info`, `uuids`).
  - `embed_tokens`: Số token vector hóa.
* **Luồng xử lý (Flow):**
  1. Người dùng upload file lên MinIO storage qua Backend Gateway.
  2. Gửi event `user_documents` để AI đọc PDF, bóc tách luận điểm chính (`key_points`).
  3. Hiển thị preview các `key_points` cho người dùng kiểm tra.
  4. Gửi event `embed_user_documents` để lưu vào Qdrant Vector DB (sử dụng cho RAG trong suốt quá trình viết báo cáo sau này).

---

### 🔹 TASK FE-DOC-07: Sinh Dàn ý & Đề cương Chi tiết (Research Outline Generation)

* **Vị trí màn hình:** Bước 5 trong Setup Wizard — *"Xây dựng Đề cương nghiên cứu (Outline)"*.
* **Cần vẽ những gì (UI Components):**
  1. **Outline Configuration Bar:**
     - **Dung lượng ước tính (`word_count_str`):** Dropdown hoặc input chọn số từ tổng thể (Ví dụ: "8000 - 10000 từ", "12000 - 15000 từ").
     - **Danh sách Chương sơ bộ (`headings`):** Bảng danh sách các chương mặc định (Chương 1: Giới thiệu, Chương 2: Cơ sở lý thuyết & Mô hình, Chương 3: Phương pháp nghiên cứu...).
     - **Thanh trượt Tỷ lệ phân bổ (`headings_percent`):** Slider đa đoạn thể hiện % số từ cho từng chương (Tổng luôn bằng 100%, ví dụ: [10%, 30%, 25%, 25%, 10%]).
  2. **Action Button:** Nút *"Sinh Đề cương Chi tiết bằng AI"*.
  3. **Detailed Outline Tree View (Cây Đề cương chi tiết):**
     - Cấp 1 (Chương / Heading): Tên chương, số từ phân bổ (`word_count`), đoạn tóm tắt tổng quan chương (`overview`).
     - Cấp 2 (Tiểu mục / Subheading): Tên tiểu mục, khoảng từ quy định (`subheading_word_count`, vd: "250-400 từ"), bản mô tả chi tiết nội dung cần viết (`detail_description`).
     - Nút mở rộng/thu gọn (Expand/Collapse All).
     - Inline Edit: Cho phép click đúp vào tên chương / tên tiểu mục để sửa nhanh nội dung.
* **Input (Dữ liệu gửi đi):**
  - Event: `generate_outline`
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
      "research_type": {"type": 1, "reason": "..."},
      "word_count_str": "10000 - 12000 words",
      "headings": [
        {"heading": "Chương 1: Giới thiệu nghiên cứu"},
        {"heading": "Chương 2: Cơ sở lý thuyết và mô hình nghiên cứu"},
        {"heading": "Chương 3: Phương pháp nghiên cứu"},
        {"heading": "Chương 4: Kết quả nghiên cứu và thảo luận"},
        {"heading": "Chương 5: Kết luận và hàm ý quản trị"}
      ],
      "headings_percent": [10, 30, 25, 25, 10],
      "final_proposal": {
        "title": "Tác động của Livestream bán hàng...",
        "problem_statement": "...",
        "motivation": "..."
      }
    }
    ```
* **Output (Dữ liệu nhận về & hiển thị):**
  - `outline`:
    ```json
    {
      "title": "Tác động của Livestream bán hàng...",
      "outline": [
        {
          "heading": "Chương 1: Giới thiệu nghiên cứu",
          "word_count": "1000-1200",
          "overview": "Tổng quan bối cảnh thương mại điện tử...",
          "subheadings": [
            {
              "subheading": "1.1. Tính cấp thiết của đề tài",
              "subheading_word_count": "300-400",
              "detail_description": "Trình bày sự bùng nổ của livestream và các vấn đề đặt ra..."
            }
          ]
        }
      ]
    }
    ```
* **Luồng xử lý (Flow):**
  1. Người dùng thiết lập tổng số từ và % cho từng chương.
  2. Nhấn "Sinh Đề cương" → FE hiển thị hiệu ứng Loading Timeline tương tác.
  3. Nhận kết quả → Render Tree view phân cấp trực quan.
  4. Người dùng kiểm tra tổng thể đề cương xem đã đúng logic học thuật hay chưa.

---

### 🔹 TASK FE-DOC-08: Trợ lý AI Tinh chỉnh & Điều chỉnh Đề cương (Interactive Outline Modification)

* **Vị trí màn hình:** Bảng công cụ điều khiển đính kèm bên cạnh Tree View Đề cương.
* **Cần vẽ những gì (UI Components):**
  1. **AI Prompt Box (Chỉnh sửa đề cương bằng ngôn ngữ tự nhiên):**
     - Ô nhập lệnh: Ví dụ *"Chia chương 2 thành 2 phần riêng biệt", "Bổ sung tiểu mục phân tích mẫu theo độ tuổi vào chương 3", "Đổi trọng số chương 4 lên 35%"*.
     - Nút gửi lệnh *"Yêu cầu AI cập nhật đề cương"*.
  2. **Direct Visual Editor (Chỉnh sửa trực quan):**
     - Nút `+ Thêm chương mới`, `+ Thêm tiểu mục`.
     - Kéo thả (Drag & Drop) để hoán đổi thứ tự các chương hoặc chuyển tiểu mục từ chương này sang chương khác.
     - Nút Xóa chương / tiểu mục.
  3. **Diff View Modal (So sánh thay đổi):**
     - Khi AI cập nhật xong, hiển thị màn hình so sánh 2 cột: Cột trái (Đề cương cũ), Cột phải (Đề cương mới có highlight xanh thêm / đỏ xóa).
     - Nút *"Áp dụng (Accept)"* hoặc *"Hoàn tác (Reject)"*.
* **Input (Dữ liệu gửi đi):**
  - Event: `modify_outline`
    ```json
    {
      "event_type": "modify_outline",
      "model_id": "localhost",
      "user_id": "user_01",
      "document_id": "doc_01",
      "session_id": "sess_01",
      "language": "Vietnamese",
      "field": "Kinh tế",
      "domain": "Thương mại điện tử",
      "research_type": {"type": 1},
      "headings": ["Chương 1...", "Chương 2..."],
      "headings_percent": [10, 30, 25, 25, 10],
      "new_headings": ["Chương 1...", "Chương 2...", "Chương 3 mới..."],
      "new_headings_percent": [10, 25, 25, 25, 15],
      "final_proposal": { "title": "..." }
    }
    ```
* **Output (Dữ liệu nhận về & hiển thị):**
  - `updated_outline`: Cấu trúc đề cương mới sau khi điều chỉnh cấu trúc và phân bổ lại số từ.
* **Luồng xử lý (Flow):**
  1. Người dùng gõ yêu cầu điều chỉnh hoặc kéo thả các mục trên giao diện.
  2. Bấm "Cập nhật" → AI tính toán lại toàn bộ cấu trúc và số từ tương ứng.
  3. Hiển thị bản Diff xem trước để người dùng duyệt thay đổi.
  4. Lưu đề cương hoàn thiện.

---

### 🔹 TASK FE-DOC-09: Ánh xạ Tài liệu Tham khảo vào Đề cương & Hoàn tất Thiết lập (Reference Mapping & Setup Finalization)

* **Vị trí màn hình:** Bước 6 — Bước cuối cùng của Document Setup: *"Gán tài liệu tham khảo & Hoàn tất"*.
* **Cần vẽ những gì (UI Components):**
  1. **Auto-Mapping Action Button:**
     - Nút bấm lớn *"AI Tự động Phân bổ Tài liệu Tham khảo vào từng Mục"* (Trigger `generate_outline_with_refs`).
  2. **Mapped Outline View (Đề cương đính kèm tài liệu):**
     - Dưới mỗi tiểu mục (`subheading`), hiển thị danh sách các bài báo được gán kèm:
       - Tên bài báo (`title`).
       - **Mục đích sử dụng (`usage_type`):** Huy hiệu màu rõ ràng (vd: *Cung cấp bối cảnh*, *Xác định khoảng trống nghiên cứu*, *Kế thừa mô hình lý thuyết*, *Biện minh phương pháp luận*, *So sánh kết quả*).
       - **Chỉ dẫn viết bài (`usage_description`):** Đoạn giải thích của AI hướng dẫn người viết cần dùng số liệu/luận điểm nào của bài báo này để viết mục này.
       - **Luận điểm sử dụng (`key_points_used`):** Số thứ tự các luận điểm cốt lõi.
  3. **Manual Reference Assign Drawer (Điều chỉnh phân bổ thủ công):**
     - Cho phép người dùng click *"Gán thêm tài liệu"* ở bất kỳ mục nào để mở danh sách bài báo và tích chọn bổ sung (Trigger `update_user_refs`).
  4. **Setup Complete Banner:**
     - Nút *"Hoàn tất Thiết lập Đề tài & Bắt đầu Viết"* → Chuyển toàn bộ dữ liệu dự án sang phân hệ Viết báo cáo (`write_reports`).
* **Input (Dữ liệu gửi đi):**
  - Event: `generate_outline_with_refs`
    ```json
    {
      "event_type": "generate_outline_with_refs",
      "model_id": "localhost",
      "user_id": "user_01",
      "document_id": "doc_01",
      "session_id": "sess_01",
      "language": "Vietnamese",
      "outline": { "title": "...", "outline": [ /* danh sách heading từ Task 7 */ ] },
      "final_proposal": { "title": "...", "problem_statement": "..." },
      "processed_docs": [ /* danh sách papers & user docs đã thu thập */ ]
    }
    ```
* **Output (Dữ liệu nhận về & hiển thị):**
  - `outline`: Đề cương hoàn chỉnh tích hợp trường `subsection_refs`:
    ```json
    [
      {
        "title": "When we are alike: homophily in livestream commerce",
        "usage_type": "Kế thừa hoặc điều chỉnh mô hình nghiên cứu/lý thuyết",
        "usage": "Sử dụng mô hình đồng điệu (homophily) từ nghiên cứu này để làm cơ sở cho giả thuyết H1...",
        "key_points_used": [1, 3, 5]
      }
    ]
    ```
* **Luồng xử lý (Flow):**
  1. Người dùng bấm "AI Tự động Phân bổ Tài liệu".
  2. AI đọc sâu toàn bộ bài báo và đối chiếu với từng mục trong đề cương.
  3. Render đề cương hoàn chỉnh với đầy đủ "bản đồ tài liệu" (Reference Blueprint).
  4. Người dùng xem lại, có thể kéo thả gán thêm hoặc đổi mục đích sử dụng.
  5. Bấm "Hoàn tất Thiết lập Đề tài" → Lưu toàn bộ vào Database và sẵn sàng cho việc sinh nội dung văn bản.

---

### 🔹 TASK FE-DOC-10 (Bổ trợ/Admin): Tra cứu Tạp chí & Quản lý Tài liệu Hệ thống

* **Nghiệp vụ:**
  1. **Tra cứu Tạp chí (`get_journals`):** Màn hình tra cứu ISSN, tên tạp chí và xếp hạng Scimago (Q1-Q4) được cập nhật định kỳ.
  2. **Quản trị Tài liệu Mẫu (`admin_documents` & `user_guide_documents`):** Dành riêng cho màn hình Admin để tải lên các tài liệu mẫu, cẩm nang viết luận văn hoặc tài liệu hướng dẫn hệ thống nạp vào Vector DB dùng chung.

---

## 📊 3. BẢNG CHECKLIST TRIỂN KHAI DÀNH CHO FRONTEND DEVELOPER

| Mã Task | Tên Task & Giao diện | Events kết nối | Mức độ ưu tiên | Trạng thái |
|---|---|---|---|---|
| **FE-DOC-01** | Chọn Ngành lớn, Gợi ý Lĩnh vực & Hướng hẹp | `generate_domains`, `generate_subdomains` | 🔴 P0 (Bắt buộc) | ⏳ Chờ làm |
| **FE-DOC-02** | Sinh Bộ từ khóa & Gợi ý Danh sách Đề tài | `generate_keywords`, `generate_titles` | 🔴 P0 (Bắt buộc) | ⏳ Chờ làm |
| **FE-DOC-03** | Trộn Đề tài & Chi tiết hóa Bản đề xuất (Proposal) | `mix_titles`, `generate_title_description` | 🔴 P0 (Bắt buộc) | ⏳ Chờ làm |
| **FE-DOC-04** | Xác định Phương pháp luận (Định tính / Định lượng) | `get_research_type` | 🟡 P1 (Quan trọng) | ⏳ Chờ làm |
| **FE-DOC-05** | Bộ máy Tìm kiếm & Lọc Bài báo Quốc tế (OpenAlex/Q1) | `search_papers` | 🔴 P0 (Bắt buộc) | ⏳ Chờ làm |
| **FE-DOC-06** | Tải lên PDF cá nhân, Bóc tách Keypoints & Vector DB | `user_documents`, `embed_user_documents`, `delete_documents` | 🟡 P1 (Quan trọng) | ⏳ Chờ làm |
| **FE-DOC-07** | Sinh Cấu trúc Đề cương Chi tiết (Tree View) | `generate_outline` | 🔴 P0 (Bắt buộc) | ⏳ Chờ làm |
| **FE-DOC-08** | Trình chỉnh sửa & AI Tinh chỉnh Đề cương (Diff View) | `modify_outline` | 🟡 P1 (Quan trọng) | ⏳ Chờ làm |
| **FE-DOC-09** | Ánh xạ Tài liệu vào Đề cương & Hoàn tất Setup | `generate_outline_with_refs`, `update_user_refs` | 🔴 P0 (Bắt buộc) | ⏳ Chờ làm |
| **FE-DOC-10** | Tra cứu Tạp chí & Quản trị Tài liệu Hướng dẫn | `get_journals`, `admin_documents` | 🟢 P2 (Phụ trợ) | ⏳ Chờ làm |
