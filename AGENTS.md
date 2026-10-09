# 🤖 AGENTS & AI CODING GUIDELINES — autoresearching

> Tài liệu này định nghĩa các nguyên tắc kiến trúc, tiêu chuẩn code và quy tắc bắt buộc mà mọi AI Assistant hoặc Developer **PHẢI** tuân thủ khi làm việc trên codebase này.

---

## 🧩 TASK DECOMPOSITION RULE (MANDATORY – ÁP DỤNG CHO MỌI TASK TRUNG BÌNH ĐẾN LỚN)

> **Mục tiêu**: Tránh "ảo giác" (hallucination) khi xử lý task quá lớn trong một lượt. AI phải chủ động chia nhỏ, lập kế hoạch thành file, rồi thực thi từng phần độc lập.

### Khi nào áp dụng?

Áp dụng bắt buộc khi task có **bất kỳ** dấu hiệu sau:
- Yêu cầu tạo hoặc chỉnh sửa **≥ 3 file** khác nhau.
- Task liên quan đến **nhiều layer** (listener + module + schema + config, v.v.).
- Mô tả yêu cầu dài hơn **10 câu** hoặc có nhiều điều kiện logic phức tạp.
- Ước tính thực thi **> 15 phút**.
- Task có từ "refactor toàn bộ", "migrate", "thêm tính năng X hoàn chỉnh", v.v.

### Quy trình bắt buộc

**Bước 1 – Phân tích & Chia nhỏ (TRƯỚC KHI viết bất kỳ dòng code nào)**

AI phải:
1. Đọc và phân tích toàn bộ yêu cầu.
2. Xác định các **sub-task độc lập** (mỗi sub-task chỉ làm một việc cụ thể).
3. Tạo thư mục `tasks/` ở root project (hoặc `.tasks/` nếu muốn ẩn).
4. Tạo **một file `.md` cho mỗi sub-task** theo format sau:

```
tasks/
├── TASK_PLAN.md          # Tổng quan plan & thứ tự thực hiện
├── task_01_<tên>.md      # Sub-task 1
├── task_02_<tên>.md      # Sub-task 2
├── task_03_<tên>.md      # Sub-task 3
└── ...
```

**Bước 2 – Format mỗi file `task_XX_<tên>.md`**

Mỗi file sub-task phải có cấu trúc chuẩn:

```markdown
# Task XX: <Tên ngắn gọn>

## Mục tiêu
<Mô tả một câu rõ ràng task này làm gì>

## Phạm vi (Scope)
- Files cần tạo/chỉnh sửa: [file1, file2, ...]
- Files KHÔNG được chạm tới: [...]
- Dependencies: Task XX phải hoàn thành trước

## Các bước thực hiện
1. ...
2. ...
3. ...

## Tiêu chí hoàn thành (Done Criteria)
- [ ] <Điều kiện cụ thể, kiểm tra được>
- [ ] Tests pass
- [ ] Không có lỗi lint/type

## Ghi chú / Rủi ro
<Các edge case hoặc điểm cần chú ý>
```

**Bước 3 – Tạo `TASK_PLAN.md` tổng quan**

```markdown
# TASK PLAN: <Tên task lớn>

## Tổng quan
<Mô tả ngắn mục tiêu cuối cùng>

## Thứ tự thực hiện
1. [ ] task_01_<tên>.md – <mô tả 1 dòng>
2. [ ] task_02_<tên>.md – <mô tả 1 dòng>
3. [ ] task_03_<tên>.md – <mô tả 1 dòng>

## Trạng thái
| Task | Status | Ghi chú |
|---|---|---|
| task_01 | ⏳ Pending | |
| task_02 | ⏳ Pending | |
```

**Bước 4 – Thực thi tuần tự**

- **Đọc từng file task một** trước khi thực thi, không đọc tất cả cùng lúc.
- Sau khi hoàn thành mỗi sub-task: cập nhật trạng thái trong `TASK_PLAN.md` (✅ Done / ❌ Failed / ⚠️ Blocked).
- Nếu sub-task phát sinh vấn đề ngoài dự kiến → dừng lại, báo cáo người dùng trước khi tiếp tục.
- **Không nhảy cóc** task — luôn thực hiện đúng thứ tự đã định.

### Ví dụ minh họa

```text
Yêu cầu: "Thêm event mới GENERATE_ABSTRACT vào DocumentSetup pipeline"

✅ ĐÚNG:
  → Chia thành 4 sub-tasks:
     task_01_event_type.md          (thêm enum vào event_type.py)
     task_02_schema.md              (thêm Pydantic schema mới)
     task_03_module_logic.md        (viết business logic trong modules/)
     task_04_listener_dispatch.md   (thêm case dispatch trong document_setup_listener.py)
  → Đọc task_01 → thực thi → tick done → đọc task_02 → ...

❌ SAI:
  → Đọc toàn bộ yêu cầu rồi viết code một lần cho tất cả 4 file
  → Bắt đầu code ngay mà không lập kế hoạch
```

### Quy tắc dọn dẹp

- Sau khi **toàn bộ task lớn hoàn thành**: xóa thư mục `tasks/` hoặc move vào `docs/completed_tasks/` để lưu lịch sử.
- Không commit thư mục `tasks/` vào git (thêm vào `.gitignore`).

---

## 📖 0. DOCS INDEX RULE (MANDATORY – ĐỌC TRƯỚC TIÊN)

**TRƯỚC KHI** viết code, thêm tính năng hoặc sửa bug, AI BẮT BUỘC phải:

1. **Đọc `DOCS_INDEX.md`** (ở root project) để xác định file docs nào liên quan đến nhiệm vụ.
2. **Đọc các file `docs/*.md`** phù hợp dựa theo keyword tra cứu trong `DOCS_INDEX.md`.
3. Chỉ sau khi đọc docs liên quan mới được tiến hành viết hoặc chỉnh sửa code.

**Lý do**: Thư mục `docs/` chứa kiến thức đã được tóm tắt và đánh từ khóa cho từng module. Đọc docs trước giúp loại bỏ việc scan file thừa, tiết kiệm token và tăng tốc debug.

**Quy tắc cập nhật docs**:
- Khi **thêm file mới** → tạo file tóm tắt `docs/<tên_file>.md` tương ứng.
- Khi **sửa đổi đáng kể** một file đã có → cập nhật `docs/<tên_file>.md` tương ứng.
- Sau mọi thay đổi docs → cập nhật `DOCS_INDEX.md` (bảng keyword + flowchart nếu cần).

---

## 🗣️ 1. COMMUNICATION & LANGUAGE RULE (MANDATORY)

- **Luôn trả lời và giải thích bằng tiếng Việt** khi trò chuyện với người dùng.
- Comment code, commit message và tài liệu kỹ thuật có thể viết bằng tiếng Anh hoặc tiếng Việt tùy ngữ cảnh, nhưng **mọi giải thích tương tác** với người dùng PHẢI bằng tiếng Việt.

---

## 📌 2. FILE LENGTH & MODULARITY RULES (MANDATORY)

- **Ngưỡng tối ưu**: Khoảng **150 dòng code** mỗi file.
- **Giới hạn tối đa**: Không được vượt quá **250 dòng code**.
- **Giới hạn tuyệt đối**: **TUYỆT ĐỐI KHÔNG ĐỂ FILE VƯỢT QUÁ 300 DÒNG CODE**.
- **Hành động bắt buộc**: Khi file đạt 200–250 dòng, phải chủ động refactor và tách thành các sub-module nhỏ hơn.

> ⚠️ **LƯU Ý THỰC TẾ**: Dự án hiện có nhiều file rất lớn (ví dụ `write_listener.py` ~98KB, `write_prompt_bank.py` ~125KB). Khi chỉnh sửa các file này, cần ưu tiên refactor dần dần và KHÔNG đọc toàn bộ file bằng `view_file` một lần.

---

## 🏗️ 3. PROJECT ARCHITECTURE

> Dự án **autoresearching** là một hệ thống AI backend xử lý nghiên cứu khoa học tự động. Toàn bộ giao tiếp giữa các thành phần thông qua **Apache Kafka** (event-driven architecture). Không có REST API trực tiếp — tất cả request/response đều qua Kafka topics.

### 3.1 Tech Stack

| Layer | Công nghệ |
|---|---|
| Language | Python 3.x |
| Async Runtime | `asyncio` |
| Message Queue | Apache Kafka (`aiokafka`) |
| LLM Framework | LangChain + LangGraph |
| LLM Providers | OpenAI, Google Gemini |
| Vector DB | Qdrant (`langchain-qdrant`) |
| Document DB | MongoDB (`pymongo`, `langchain-mongodb`) |
| Cache / State | Redis (`redis`, `langgraph-checkpoint-redis`) |
| Object Storage | MinIO (`minio`, `boto3`) |
| Data Analysis | pandas, numpy, scipy, statsmodels, scikit-learn, semopy, rpy2 |
| Containerization | Docker + Docker Compose |
| CI/CD | Jenkins (SSH deploy to server `192.168.3.140`) |
| Config Management | `pydantic_settings` (load từ `/app/.env`) |

### 3.2 Cấu trúc thư mục thực tế

```text
autoresearching/
├── AGENTS.md                          # 🤖 Hướng dẫn AI & quy tắc dự án
├── DOCS_INDEX.md                      # 📚 Mục lục docs – AI đọc TRƯỚC TIÊN
├── README.md                          # Tổng quan dự án
├── requirements.txt                   # Python dependencies toàn bộ dự án
├── .env                               # Biến môi trường (KHÔNG commit)
│
├── main.py                            # Entry point: chạy tất cả 4 listener song song
├── main_chat.py / main_chat_local.py  # Entry point riêng cho Chatbot service
├── main_doc.py / main_doc_local.py    # Entry point riêng cho Document Setup service
├── main_enhance.py / main_enhance_local.py  # Entry point riêng cho Enhancement service
├── main_write.py / main_write_local.py      # Entry point riêng cho Write service
│
├── topics.py                          # 📡 Định nghĩa tất cả Kafka topic names
├── event_type.py                      # 📋 Enum định nghĩa các event type per service
├── error_type.py                      # ❌ Enum định nghĩa các error code
├── error_handle.py                    # Xử lý lỗi tập trung
├── exception_type.py                  # Custom exception classes
├── status_type.py                     # Enum trạng thái xử lý
├── producers.py                       # Kafka producers helper
├── utils.py                           # Shared utilities (Kafka setup, singletons, v.v.)
├── get_llm_response.py                # Wrapper gọi LLM (OpenAI/Gemini)
├── translate.py                       # Module dịch thuật
│
├── listener.py                        # Base listener class (abstract)
├── document_setup_listener.py         # 📄 Listener: xử lý DocumentSetupEvent
├── chatbot_listener.py                # 💬 Listener: xử lý AIEvent (chatbot)
├── enhance_listener.py                # ✨ Listener: xử lý EnhancementEvent
├── write_listener.py                  # 📝 Listener: xử lý WriteEvent
│
├── document_setup/                    # Module: Chuẩn bị tài liệu & ý tưởng nghiên cứu
│   ├── src/
│   │   ├── configs/
│   │   │   └── app.py                 # AppSettings (pydantic_settings) – shared config
│   │   ├── modules/
│   │   │   ├── idea_generation.py     # Sinh domain, subdomain, keyword, title
│   │   │   ├── ingest_docs.py         # Ingest & embed tài liệu vào Qdrant
│   │   │   ├── knowledge_prompt_bank.py  # Prompt templates cho knowledge base
│   │   │   ├── outline_generation.py  # Sinh outline nghiên cứu
│   │   │   ├── outline_prompt_bank.py # Prompt templates cho outline
│   │   │   ├── search_journals.py     # Tìm kiếm journal phù hợp
│   │   │   ├── search_papers.py       # Tìm kiếm paper (OpenAlex API)
│   │   │   └── search_web.py          # Tìm kiếm web (SerpAPI)
│   │   └── schemas/
│   │       ├── outline.py             # Pydantic schema cho outline
│   │       ├── proposal.py            # Pydantic schema cho proposal
│   │       ├── search_papers.py       # Pydantic schema cho search papers
│   │       └── search_web.py          # Pydantic schema cho search web
│   ├── .env-example
│   └── requirements.txt
│
├── write_reports/                     # Module: Viết báo cáo & slide
│   ├── src/
│   │   ├── configs/
│   │   │   └── app.py
│   │   ├── modules/
│   │   │   ├── write_graph.py         # LangGraph workflow viết nội dung chính
│   │   │   ├── write_chat_graph.py    # LangGraph workflow cho writer chatbot
│   │   │   ├── write_prompt_bank.py   # Prompt templates (rất lớn ~125KB)
│   │   │   ├── seminar_graph_1.py     # Workflow viết chuyên đề loại 1
│   │   │   ├── seminar_graph_2.py     # Workflow viết chuyên đề loại 2
│   │   │   ├── seminar_graph_3.py     # Workflow viết chuyên đề loại 3
│   │   │   ├── gen_slide_md.py        # Sinh slide dạng Markdown
│   │   │   ├── gen_slide_prompt.py    # Prompt cho slide generation
│   │   │   ├── references.py          # Quản lý tài liệu tham khảo
│   │   │   ├── translate.py           # Dịch thuật nội dung báo cáo
│   │   │   └── log_cleaner.py         # Dọn dẹp log
│   │   ├── schemas/
│   │   │   ├── section.py             # Pydantic schema cho section báo cáo
│   │   │   ├── slide.py               # Schema cho slide
│   │   │   └── translate.py           # Schema cho translate
│   │   └── template/                  # Template files (docx, pptx, v.v.)
│   ├── .env-example
│   └── requirements.txt
│
├── ai_chatbot/                        # Module: AI Chatbot (inner, outer, writer)
│   ├── src/
│   │   ├── configs/
│   │   ├── modules/
│   │   │   ├── chatbot.py             # Outer chatbot (general Q&A)
│   │   │   ├── inner_chatbot.py       # Inner chatbot (trong research context)
│   │   │   ├── writer_chatbot.py      # Writer chatbot (hỗ trợ viết)
│   │   │   ├── ai_in_doc.py           # AI tương tác trong document
│   │   │   ├── writer_prompt.py       # Prompt templates cho writer chatbot (~57KB)
│   │   │   └── utils.py               # Shared utilities cho chatbot
│   │   └── schemas/
│   └── README.md
│
├── data_analysis/                     # Module: Phân tích dữ liệu thống kê
│   ├── src/
│   │   ├── configs/
│   │   ├── modules/
│   │   │   ├── analyzer.py            # Bộ phân tích dữ liệu chính
│   │   │   ├── analyzer_graph.py      # LangGraph workflow cho phân tích (~67KB)
│   │   │   ├── proposed_method_v2.py  # Đề xuất phương pháp nghiên cứu (~116KB)
│   │   │   ├── prompt_bank.py         # Prompt templates phân tích (~94KB)
│   │   │   └── utils.py               # Utilities thống kê (~129KB – RẤT LỚN)
│   │   └── schemas/
│
├── Dockerfile                         # Docker build (Python base image)
├── docker-compose.yaml                # Production: tất cả services
├── docker-compose-local.yaml          # Local dev: 4 services riêng biệt
├── docker-compose-chat.yaml           # Deploy riêng Chatbot service
├── docker-compose-doc.yaml            # Deploy riêng Document Setup service
├── docker-compose-enhance.yaml        # Deploy riêng Enhancement service
├── docker-compose-write.yaml          # Deploy riêng Write service
│
├── Jenkinsfile                        # CI/CD pipeline (all-in-one)
├── Jenkinsfile-chat                   # CI/CD pipeline Chatbot only
├── Jenkinsfile-doc                    # CI/CD pipeline Document Setup only
├── Jenkinsfile-enhance                # CI/CD pipeline Enhancement only
└── Jenkinsfile-write                  # CI/CD pipeline Write only
```

### 3.3 Luồng xử lý Event-Driven (QUAN TRỌNG)

```
Client (CRM/Frontend)
        │
        ▼ Kafka Topic (request)
  ┌─────────────┐
  │  Listener   │  ← dispatch theo event_type
  └──────┬──────┘
         │
    ┌────┴────┐
    │ Module  │  ← business logic (LangGraph workflow / AI calls)
    └────┬────┘
         │
         ▼ Kafka Topic (response)
  Client nhận kết quả
```

**4 Listener chính** (mỗi cái consume một Kafka topic):

| Listener | Topic (request) | Event Enum | Mô tả |
|---|---|---|---|
| `document_setup_listener.py` | `document_setup_request` | `DocumentSetupEvent` | Chuẩn bị tài liệu, sinh outline, tìm paper |
| `write_listener.py` | `write_section_request` | `WriteEvent` | Viết báo cáo, chuyên đề, slide |
| `chatbot_listener.py` | `chatbot_request` | `AIEvent` | AI chatbot (inner/outer/writer) |
| `enhance_listener.py` | `enhancement_request` | `EnhancementEvent` | Nâng cao nội dung, gợi ý, AI in doc |

### 3.4 Cấu hình môi trường (AppSettings)

Cấu hình được load từ `/app/.env` bằng `pydantic_settings`. Class `AppSettings` nằm tại `document_setup/src/configs/app.py` và được **dùng chung toàn bộ project** (import: `from document_setup.src.configs.app import settings`).

```bash
OPEN_AI_KEY=             # OpenAI API key
GEMINI_KEY=              # Google Gemini API key
SERP_KEY=                # SerpAPI key (tìm web)
KAFKA=                   # Kafka bootstrap servers
REDIS=                   # Redis connection string
REDIS_HOST=              # Redis host
REDIS_PORT=              # Redis port
REDIS_PWD=               # Redis password
REDIS_TTL=               # Redis TTL (seconds)
MINIO_ENDPOINT=          # MinIO endpoint
MINIO_PORT=              # MinIO port
MINIO_ACCESS_KEY_ID=     # MinIO access key
MINIO_SECRET_ACCESS_KEY= # MinIO secret key
QDRANT_URL=              # Qdrant vector DB URL
EMBEDDING_MODEL=         # Tên model embedding
OPEN_ALEX_EMAIL=         # OpenAlex API email
OPEN_ALEX_USER=          # OpenAlex username
OPEN_ALEX_KEY=           # OpenAlex API key
MONGO_CONNECTION_STRING= # MongoDB connection string
TMP_FOLDER=              # Thư mục lưu file tạm
LOCALLLM_BASE_URL=       # Base URL cho local LLM (nếu dùng)
```

---

## 🎯 4. CLEAN CODE & DEVELOPMENT STANDARDS

### 4.1 Quy tắc chung

1. **Separation of Concerns trong Listener**:
   - `*_listener.py`: Chỉ consume Kafka message, dispatch sang module, publish response. **Không** chứa business logic.
   - `modules/`: Chứa toàn bộ business logic và LangGraph workflow.
   - `schemas/`: Chỉ chứa Pydantic models cho input/output.
   - `configs/`: Chỉ chứa settings và hằng số.

2. **Thứ tự bắt buộc khi thêm event mới**:
   1. Thêm enum vào `event_type.py`
   2. Tạo/cập nhật Pydantic schema trong `<module>/src/schemas/`
   3. Viết logic trong `<module>/src/modules/`
   4. Thêm prompt vào `*_prompt_bank.py` nếu cần
   5. Thêm dispatch case trong `<module>_listener.py`

3. **Type Hinting & Validation**: Dùng Pydantic v2 cho tất cả input/output của Listener.

4. **Environment & Secrets**:
   - **Không bao giờ hardcode** API keys, connection strings.
   - Luôn đọc từ `settings` (import từ `document_setup.src.configs.app`).
   - Commit `.env-example`, không bao giờ commit `.env`.

5. **Error Handling**:
   - Dùng `error_type.py` và `exception_type.py` cho các error có cấu trúc.
   - Listener phải catch exception và publish error response về Kafka — không để crash silent.
   - Log đầy đủ context (event_type, request_id) để debug.

6. **Naming Conventions** (Python):
   - `snake_case` cho biến/hàm/file.
   - `PascalCase` cho class và Pydantic models.
   - Tên listener: `<service>_listener.py`.
   - Tên module: mô tả chức năng rõ ràng (`idea_generation.py`, `write_graph.py`).

7. **LangGraph Workflows**:
   - Mỗi workflow là một LangGraph `StateGraph` riêng biệt.
   - State schema phải được định nghĩa rõ với `TypedDict`.
   - Node functions phải pure (không side-effect ngoài state update).

8. **Async**: Toàn bộ Kafka consumer/producer và LLM call phải dùng `async/await`. Không block event loop.

9. **DRY**: Nếu một đoạn code lặp ≥ 2 lần → extract thành hàm/helper riêng vào `utils.py` hoặc `<module>/src/modules/utils.py`.

10. **Comment & Documentation**: Mọi function/method public phải có **docstring** mô tả mục đích, params và return value. Không viết comment giải thích "cái gì" mà chỉ viết comment giải thích **"tại sao"** khi logic không hiển nhiên.

### 4.2 Quy tắc đặc thù dự án

- **Prompt engineering**: Toàn bộ prompt phải đặt trong file `*_prompt_bank.py` riêng biệt, không inline trong business logic.
- **LLM calls**: Dùng wrapper `get_llm_response.py` ở root khi cần gọi LLM ngoài LangGraph workflow.
- **Kafka topics**: Luôn import từ `topics.py`, không hardcode tên topic.
- **Local vs Production**: Dùng `*_LOCAL` topic khi chạy local (xem `topics.py`). Entry points local dùng `main_*_local.py`.
- **File tạm**: Lưu vào thư mục được cấu hình bởi `settings.TMP_FOLDER`, không dùng `/tmp` hardcode.

---

## 🧪 5. TESTING POLICY

> ⚠️ **Lưu ý**: Dự án hiện chưa có thư mục `test/`. Khi thêm test, tạo mới theo cấu trúc dưới đây.

### 5.1 Quy tắc bắt buộc

1. **Thêm tính năng mới** → BẮT BUỘC tạo file test mới trong `test/`:
   - `test/test_<module_name>.py`
2. **Sửa đổi logic quan trọng** → BẮT BUỘC cập nhật test file tương ứng.
3. **Độ bao phủ tối thiểu**: **≥ 80%** cho mọi module mới (LLM-heavy modules khó đạt 90%).
4. **Mock LLM calls**: Luôn mock các call đến OpenAI/Gemini/Qdrant/Kafka trong unit tests.

### 5.2 Cấu trúc thư mục test

```
test/
├── conftest.py                         # Shared fixtures (mock settings, Kafka, LLM)
├── test_document_setup_listener.py     # Tests listener dispatch logic
├── test_write_listener.py
├── test_chatbot_listener.py
├── test_enhance_listener.py
├── test_idea_generation.py             # Tests module logic
├── test_outline_generation.py
├── test_write_graph.py
└── coverage/                           # Coverage report (gitignored)
```

### 5.3 Lệnh chạy tests

```bash
# Chạy tất cả tests
pytest --cov=. --cov-report=term-missing --cov-fail-under=80

# Chạy test cho một module cụ thể
pytest test/test_idea_generation.py -v

# Chạy với asyncio support
pytest --asyncio-mode=auto -v
```

### 5.4 Tiêu chí coverage

| Layer | Tool | Min Coverage |
|---|---|---|
| Listener dispatch | pytest + pytest-asyncio | ≥ 80% |
| Module logic | pytest + pytest-asyncio | ≥ 80% |
| LangGraph workflow | pytest + unittest.mock | ≥ 70% |

### 5.5 Checklist khi thêm tính năng mới

- [ ] Tạo file test mới trong `test/` với tên phù hợp (`test_<module>.py`)
- [ ] Viết test case cho: happy path, edge cases, error cases
- [ ] Mock toàn bộ LLM calls (OpenAI/Gemini), Kafka, Qdrant trong unit tests
- [ ] Chạy toàn bộ test suite và đảm bảo pass (`pytest --asyncio-mode=auto -v`)
- [ ] Kiểm tra coverage report đạt ngưỡng tối thiểu
- [ ] Cập nhật `DOCS_INDEX.md` nếu thêm module mới

---

## 🚀 6. MCP FASTCODE – QUY TẮC TỐI ƯU TOKEN (MANDATORY)

> **Ưu tiên dùng MCP Fastcode để đọc và điều hướng codebase thay vì đọc file thô, nhằm tiết kiệm token đáng kể (44–55%) và tăng tốc độ xử lý 3–4 lần.**
>
> ⚠️ **ĐẶC BIỆT QUAN TRỌNG với dự án này**: Nhiều file rất lớn (>50KB). TUYỆT ĐỐI không đọc toàn bộ các file này bằng `view_file` ngay từ đầu.

### 6.1 Khi nào PHẢI dùng Fastcode

| Tình huống | Tool Fastcode nên dùng |
|---|---|
| Khám phá cấu trúc dự án lần đầu | `get_repo_structure` |
| Tìm kiếm symbol (hàm, class, biến) | `search_symbol` |
| Hiểu tổng quan một file | `get_file_summary` |
| Truy vết luồng gọi hàm / dependency | `get_call_chain` |
| Hỏi về logic hoặc kiến trúc codebase | `code_qa` |
| Repo chưa được index | `reindex_repo` (chạy một lần) |

### 6.2 Thứ tự ưu tiên khi đọc code

```
1. fastcode.get_repo_structure   → xem cây thư mục tổng quan
2. fastcode.get_file_summary     → đọc tóm tắt ngữ nghĩa của file
3. fastcode.search_symbol        → tìm chính xác hàm/class cần đọc
4. fastcode.get_call_chain       → truy vết luồng gọi nếu cần
5. fastcode.code_qa              → hỏi trực tiếp về logic nếu vẫn chưa rõ
6. view_file (tool gốc)          → CHỈ dùng khi cần đọc chi tiết từng dòng
                                    hoặc khi fastcode không đủ ngữ cảnh
```

> ⚠️ **KHÔNG được** dùng `view_file` hoặc `grep_search` trực tiếp vào file thô khi chưa thử qua Fastcode trước.

### 6.3 Các file LỚN cần đặc biệt chú ý

| File | Kích thước | Lưu ý |
|---|---|---|
| `data_analysis/src/modules/utils.py` | ~129KB | Dùng `search_symbol` để tìm hàm cụ thể |
| `write_reports/src/modules/write_prompt_bank.py` | ~125KB | Dùng `search_symbol` để tìm prompt cụ thể |
| `data_analysis/src/modules/proposed_method_v2.py` | ~116KB | Dùng `get_call_chain` để truy vết workflow |
| `data_analysis/src/modules/prompt_bank.py` | ~94KB | Dùng `search_symbol` để tìm prompt |
| `document_setup_listener.py` | ~86KB | Dùng `search_symbol` để tìm event handler |
| `write_listener.py` | ~98KB | Dùng `get_file_summary` trước |
| `ai_chatbot/src/modules/writer_prompt.py` | ~57KB | Dùng `search_symbol` để tìm prompt |
| `write_reports/src/modules/write_graph.py` | ~40KB | Dùng `get_call_chain` để truy vết |

### 6.4 Nhược điểm cần lưu ý

- **Bỏ sót chi tiết dòng code**: Fastcode tóm tắt cấp cao; nếu cần logic phức tạp từng dòng → vẫn phải dùng `view_file` (chỉ đọc đúng range cần thiết).
- **Phụ thuộc vào chất lượng index**: Nếu repo có cấu trúc bất thường hoặc index cũ → fallback sang `view_file` + `grep_search`.
- **Luôn xác minh**: Kết quả từ Fastcode là gợi ý ngữ nghĩa, **KHÔNG phải nguồn chân lý tuyệt đối**. Cross-check với code thực tế trước khi edit.

### 6.5 Quy tắc index repo

- **Lần đầu làm việc với dự án**: Chạy `reindex_repo` để tạo bản đồ ngữ nghĩa.
- **Sau khi thêm file/module mới**: Chạy lại `reindex_repo` để cập nhật index.
- **Không cần reindex** khi chỉ sửa nhỏ trong file đã có.

---

## 🔐 7. GIT & VERSION CONTROL RULES

1. **Commit message** phải rõ ràng, theo format:
   ```
   <type>(<scope>): <mô tả ngắn>

   type: feat | fix | refactor | docs | test | chore | style
   scope: document_setup | write_reports | ai_chatbot | data_analysis | listener | core
   ```
   Ví dụ:
   - `feat(document_setup): add GENERATE_ABSTRACT event handler`
   - `fix(write_listener): handle timeout error for long write tasks`
   - `refactor(data_analysis): split utils.py into smaller helpers`

2. **Không bao giờ commit**:
   - File `.env` chứa secrets thật
   - File `__pycache__/`, `.pyc`
   - Thư mục `tasks/` (task decomposition plans)
   - File tmp/generated trong `TMP_FOLDER`

3. **Branch naming**: `feature/<tên>`, `fix/<tên>`, `refactor/<tên>`, `docs/<tên>`.
   - Ví dụ: `feature/add-abstract-generation`, `fix/kafka-timeout-write`

4. **Deployment branches** (theo Jenkinsfile hiện tại):
   - Deploy target: Server `192.168.3.140`, path `/u01/autoresearching-ai-dev`
   - Mỗi service có Jenkinsfile riêng để deploy độc lập (`Jenkinsfile-chat`, `Jenkinsfile-doc`, v.v.).

5. **Mỗi PR/commit** chỉ giải quyết một vấn đề cụ thể (atomic commits).

---

## 🐳 8. DOCKER & DEPLOYMENT

### 8.1 Build & Run Local

```bash
# Build image
docker buildx build --no-cache --network host -t autoresearching-ai-dev -f Dockerfile ./

# Chạy tất cả services (production mode)
docker-compose up -d

# Chạy từng service riêng lẻ (local mode với local Kafka topics)
docker-compose -f docker-compose-local.yaml up autoresearching-ai-dev-chat-local
docker-compose -f docker-compose-local.yaml up autoresearching-ai-dev-doc-local
docker-compose -f docker-compose-local.yaml up autoresearching-ai-dev-write-local
docker-compose -f docker-compose-local.yaml up autoresearching-ai-dev-enhance-local

# Chạy tất cả local services
docker-compose -f docker-compose-local.yaml up -d
```

### 8.2 Entry Points

| Mode | File | Kafka Topics |
|---|---|---|
| All-in-one (prod) | `main.py` | Tất cả production topics |
| Chatbot (prod) | `main_chat.py` | `chatbot_request` |
| Document (prod) | `main_doc.py` | `document_setup_request` |
| Enhance (prod) | `main_enhance.py` | `enhancement_request` |
| Write (prod) | `main_write.py` | `write_section_request` |
| Chatbot (local) | `main_chat_local.py` | `chatbot_request_local` |
| Document (local) | `main_doc_local.py` | `document_setup_request_local` |
| Enhance (local) | `main_enhance_local.py` | `enhancement_request_local` |
| Write (local) | `main_write_local.py` | `write_section_request_local` |

### 8.3 CI/CD Pipeline (Jenkins)

Mỗi Jenkinsfile thực hiện theo thứ tự:
1. **Workspace Clearing** → 2. **Checkout code** → 3. **Remove old code** (SSH) → 4. **Copy code** (SCP) → 5. **Docker build** → 6. **Docker Compose up** → 7. **Docker prune**

---

## ✅ 9. CHECKLIST KHI THÊM TÍNH NĂNG MỚI

Khi thêm một event/tính năng mới vào hệ thống:

- [ ] **Thêm enum** vào `event_type.py` (class tương ứng với service)
- [ ] **Tạo/cập nhật Pydantic schema** trong `<module>/src/schemas/`
- [ ] **Viết module logic** trong `<module>/src/modules/`
- [ ] **Thêm prompt** vào `*_prompt_bank.py` nếu cần LLM
- [ ] **Thêm dispatch case** vào `<module>_listener.py`
- [ ] **Cập nhật `topics.py`** nếu cần topic mới
- [ ] **Viết test** trong `test/test_<module>.py`
- [ ] **Cập nhật `DOCS_INDEX.md`** nếu thêm module mới
- [ ] **Chạy `reindex_repo`** (MCP Fastcode) để cập nhật index
- [ ] **Kiểm tra file length** – không để file vượt quá 300 dòng
