# Luồng chạy project autoresearching

## 1. Các file khởi động

`main.py` khởi động cả bốn listener:

```text
DocumentSetupEventListener
WriteSectionEventListener
ChatbotEventListener
EnhancementEventListener
```

Có thể khởi động riêng từng listener qua `main_doc.py`, `main_write.py`,
`main_chat.py` và `main_enhance.py`. Bản local dùng các Kafka topic có hậu tố
`_local`.

## 2. Luồng request chung

```text
Frontend/API
    -> Kafka request topic
    -> listener
    -> phân nhánh theo event_type
    -> module/graph
    -> MongoDB / Redis / Qdrant / MinIO / LLM
    -> Kafka response topic
    -> Frontend/API
```

Luồng đọc Kafka, đưa vào queue, chạy worker, validate và cập nhật health status
nằm trong `listener.py`.

## 3. Các Kafka topic

| Chức năng | Request | Response |
|---|---|---|
| Thiết kế nghiên cứu | `document_setup_request` | `document_setup_response` |
| Thiết kế nghiên cứu local | `document_setup_request_local` | `document_setup_response_local` |
| Viết báo cáo | `write_section_request` | `write_section_response` |
| Viết báo cáo local | `write_section_request_local` | `write_section_response_local` |
| Chatbot | `chatbot_request` | `chatbot_response` |
| Cải thiện nội dung | `enhancement_request` | `enhancement_response` |

Tên topic nằm trong `topics.py`. Một topic được dùng chung cho nhiều chức năng;
`event_type` quyết định chức năng nào được chạy.

## 4. Luồng thiết kế nghiên cứu

```text
Lĩnh vực
  -> generate_domains
  -> generate_subdomains
  -> generate_titles
  -> proposal / đề xuất nghiên cứu
  -> generate_keywords
  -> search_papers
  -> get_research_type
  -> generate_outline
  -> generate_outline_with_refs
  -> outline + reference được gán cho section/subsection
```

Code chính:

```text
document_setup_listener.py
document_setup/src/modules/idea_generation.py
document_setup/src/modules/search_papers.py
document_setup/src/modules/outline_generation.py
document_setup/src/modules/ingest_docs.py
```

Frontend/API thường lấy response của bước trước để gọi request cho bước sau;
listener không tự nối toàn bộ pipeline bên trong.

## 5. Luồng viết báo cáo

```text
write_section_request
  -> phân nhánh theo event_type
      -> write_content       -> write_graph
      -> chuyen_de_1         -> seminar_graph_1
      -> chuyen_de_2         -> seminar_graph_2
      -> chuyen_de_3         -> Analyzer -> seminar_graph_3
      -> propose_method      -> graph đề xuất phương pháp
      -> analyzer            -> graph phân tích dữ liệu
      -> gen_slides          -> graph sinh slide
      -> translate_report    -> Translator
```

Với `write_content`:

```text
load_input
  -> choose_refs
  -> xác định section tổng quan/phương pháp/kết quả
  -> chia subsection thành các batch
  -> kiểm tra subsection có cần method/data không
  -> viết các subsection
  -> tổng hợp section
  -> thêm references
  -> thêm phụ lục
```

Code chính:

```text
write_listener.py
write_reports/src/modules/write_graph.py
write_reports/src/modules/utils/utils_func.py
write_reports/src/modules/write_prompt_bank.py
```

Các kiểu viết:

- Viết thường dùng proposal, outline, references và web search nếu được bật.
- Viết phương pháp dùng `final_model`, hypotheses, variables, survey questions
  và research questions.
- Viết dữ liệu dùng analysis logs và generated files, làm sạch/chọn log block,
  viết nội dung học thuật rồi chèn bảng và hình.

## 6. Luồng `chuyen_de_3`

```text
request chuyen_de_3
  -> Analyzer chạy phân tích dữ liệu
  -> tạo analyze_log + detailed_logs + generated_files
  -> lưu trạng thái phân tích vào document_configurations
  -> seminar_graph_3 viết báo cáo
  -> write_section_response
```

Graph chạy lâu có thể tạm dừng ở chapter break, analyzer hoặc proposed method.
Client tiếp tục bằng cùng checkpoint/thread identifier.

## 7. Từ điển thuật ngữ

| Từ trong code | Nghĩa trong project |
|---|---|
| `event_type` | Tên thao tác cụ thể trong một Kafka topic; ví dụ `search_papers`, `write_content`, `chuyen_de_3`. |
| `listener` | Bộ phận đọc request từ Kafka, kiểm tra input, gọi module xử lý và gửi response. |
| `proposal` / `final_proposal` | Đề xuất nghiên cứu: tiêu đề, vấn đề, động lực, khoảng trống nghiên cứu, phương pháp và thông tin được kế thừa từ phân tích. |
| `outline` | Dàn ý báo cáo gồm section, subsection, mô tả và giới hạn số từ. |
| `section` | Chương/phần lớn của báo cáo, ví dụ Literature Review hoặc Results. |
| `subsection` | Mục nhỏ nằm trong một section; thường là đơn vị được LLM viết. |
| `reference` / `research_papers` | Các bài nghiên cứu được dùng làm nguồn trích dẫn. |
| `key_points` | Bản tóm tắt có cấu trúc của một paper, không phải chỉ vài từ khóa. |
| `paperChunk` | Đoạn văn thực tế được cắt từ paper; `key_points` là tóm tắt, `paperChunk` là nội dung nguồn. |
| `paperUsage` / `usage` | Chỉ dẫn paper được dùng như thế nào trong section/subsection. |
| `key_points_used` | Vị trí các key point được chọn để đưa vào kế hoạch sử dụng reference. |
| `processed_docs` | Tài liệu đã được đọc/xử lý, gồm metadata, nội dung và key points. |
| `analyze_log` | Trạng thái/tóm tắt của quá trình phân tích dữ liệu. |
| `detailed_logs` | Log chi tiết từng bước phân tích; writer chọn phần liên quan để viết Results/Discussion. |
| `generated_files` | File phân tích được sinh ra, như CSV, bảng, biểu đồ, hình ảnh hoặc HTML. |
| `graph` | Quy trình LangGraph gồm nhiều node và state; có thể dừng rồi resume. |
| `checkpoint` / `thread_id` | Trạng thái đã lưu của graph; muốn tiếp tục đúng phiên phải giữ cùng identifier. |
| `interrupt` | Điểm graph chủ động dừng để chờ khách hàng duyệt, chỉnh hoặc cung cấp thêm dữ liệu. |
| `embedding` | Vector đại diện cho nội dung, dùng để tìm tài liệu/reference tương đồng trong Qdrant. |

### `CHUYEN_DE_1`, `CHUYEN_DE_2`, `CHUYEN_DE_3`

Đây là tên event nội bộ, không phải ba loại lỗi:

```text
CHUYEN_DE_1 -> chuyên đề tổng quan tài liệu / Literature Review
CHUYEN_DE_2 -> chuyên đề phương pháp / Methodology
CHUYEN_DE_3 -> chuyên đề kết quả và thảo luận / Results and Discussion
```

Trong code, `CHUYEN_DE_1` chạy `seminar_graph_1`, `CHUYEN_DE_2` chạy
`seminar_graph_2`. `CHUYEN_DE_3` chạy Analyzer trước, sau đó dùng
`seminar_graph_3` để viết báo cáo.

### `key_points` dùng để làm gì?

```text
Paper/PDF
  -> đọc và tóm tắt thành key_points
  -> chọn paper phù hợp với section
  -> chọn key point và paperChunk phù hợp
  -> đưa vào prompt viết
  -> sinh nội dung + citation
```

`KeyPoints` gồm các nhóm thông tin: chủ đề, bối cảnh, tầm quan trọng, gap,
vấn đề, mục tiêu, phạm vi, phương pháp, dữ liệu, biến, kết quả, kết luận,
đóng góp, hướng phát triển, hypotheses, model, variables và measurement items.

## 8. Luồng phản hồi và phản biện với khách hàng

Feedback không có Kafka topic riêng. Khách hàng phản hồi bằng request mới trên
cùng topic, kèm `event_type`, `thread_id` hoặc `document_id` và cờ resume.

### A. Khách hàng duyệt/chỉnh kế hoạch phân tích

```text
analyzer / chuyen_de_3
  -> Analyzer tạo kế hoạch
  -> interrupt gửi kế hoạch cho khách hàng
      -> [ACCEPT]      -> chạy phân tích
      -> [EDIT_PLAN]   -> quay lại sửa kế hoạch
      -> tool_configs   -> chạy kế hoạch do khách hàng cung cấp
```

Trong lúc phân tích, action cũng có thể chờ phản hồi:

```text
action pending
  -> [APPROVE] -> thực thi action
  -> [REJECT]  -> đánh dấu từ chối và xử lý tiếp
```

Luồng này nằm trong `data_analysis/src/modules/analyzer_graph.py`, node
`human_feedback_node`.

### B. Khách hàng góp ý cho kết quả phân tích

```text
comment_data
  -> Analyzer kiểm tra điều kiện của biến/dữ liệu
  -> trả comments

check_logic_data
  -> kiểm tra logic giữa các biến
  -> trả errors_logic + warnings_logic
```

Hai event này dùng để phát hiện vấn đề trước khi đưa kết quả vào báo cáo.

### C. Khách hàng yêu cầu sửa đoạn văn

```text
ai_in_doc
  -> khách hàng chọn đoạn + action + context
  -> AIInDoc xử lý
  -> trả response

get_suggestions
  -> sinh các đoạn gợi ý
  -> khách hàng chọn gợi ý

enhance / enhance_all
  -> áp dụng một hoặc nhiều gợi ý
  -> trả updated_paragraphs
```

Code xử lý: `enhance_listener.py` và `ai_chatbot/src/modules/ai_in_doc.py`.

### D. Khách hàng duyệt phương pháp nghiên cứu

```text
propose_method
  -> graph sinh model, hypotheses, variables, survey questions
  -> interrupt hỏi ý kiến khách hàng
  -> resume_method + user_input
  -> hoàn thiện final_proposal
  -> chuyển thông tin cho writer
```

### E. Khách hàng duyệt trong lúc viết báo cáo

```text
write_content / chuyen_de_1 / chuyen_de_2 / chuyen_de_3
  -> graph viết từng section
  -> chapter_break / analyzer / propose_method interrupt
  -> response tạm về client
  -> client gửi resume với cùng thread_id/document_id
  -> graph viết tiếp
```

Các cờ resume thường gặp:

```text
resume              : tiếp tục graph chính
resume_error        : tiếp tục sau lỗi
resume_method       : tiếp tục sau phần phương pháp
resumeCharacter     : tiếp tục viết chapter
write_resume_error  : tiếp tục phần writer sau lỗi Analyzer
```

### F. Khách hàng hỏi/trao đổi với chatbot

```text
outer_chatbot  -> hỏi đáp chung
inner_chatbot  -> hỏi đáp dựa trên tài liệu
writer_chatbot -> trao đổi về outline/nội dung viết
writer         -> hội thoại hỗ trợ thiết kế nghiên cứu
```

Các event này đi qua `chatbot_request`; trạng thái hội thoại được giữ bằng
`conv_id` hoặc `thread_id`.

## 9. Luồng lỗi và cách lần ngược

```text
Kafka request
  -> thiếu/sai input?
      -> error_code 603 INVALID_PARAMS
  -> module chạy?
      -> lỗi LLM/API/search/database
      -> listener bắt lỗi và gắn error_code
  -> quá thời gian?
      -> error_code 604 TIME_OUT_REQUEST
  -> thành công/lỗi
      -> response topic + health status
```

Các trạng thái health:

```text
1 PENDING    : Kafka đã nhận request
2 PROCESSING : đang xử lý
3 FINISHED   : xử lý xong
4 ERROR      : xử lý lỗi
5 SUSPENDED  : bị dừng/timeout theo cơ chế finalize
```

| Mã/nhóm | Ý nghĩa | Nơi thường xem |
|---|---|---|
| `603` | Thiếu field, sai kiểu, dữ liệu rỗng hoặc sai điều kiện | listener tương ứng |
| `604` | Timeout | listener + health status |
| `605` | Model chưa được hỗ trợ | listener |
| `606` | `event_type` không tồn tại | listener |
| `401/403/429/500/503` | Lỗi xác thực, quyền, quota, server hoặc provider | `error_handle.py` |
| `600-609`, `700-704` | Network, đọc paper, token, search API | `error_type.py` |
| `610-628` | Lỗi nhóm thiết kế nghiên cứu | `DocumentSetupError` |
| `630-642` | Lỗi nhóm viết/phân tích/report | `WriteSectionError` |
| `650-653` | Lỗi chatbot | `ChatbotError` |
| `670-673` | Lỗi enhance nội dung | `EnhancementError` |

Khi gặp lỗi từ khách hàng, lần theo:

```text
1. Topic request nào?
2. event_type nào?
3. listener branch nào?
4. error_code là lỗi input, provider hay module riêng?
5. Có document_id/conv_id/thread_id để xem health/checkpoint không?
6. Lỗi xảy ra trước hay sau interrupt?
```

Code bắt lỗi và gửi response nằm ở `*_listener.py`; mapping mã lỗi ở
`error_type.py`; chuyển lỗi provider về `AIERROR` ở `error_handle.py`.

## 10. Bản đồ module theo chức năng

```text
Runtime chung
  main.py / main_*.py
  listener.py / producers.py / utils.py / topics.py

Thiết kế nghiên cứu
  document_setup/
  - idea_generation.py       domain, title, proposal, keyword
  - search_web.py             lập kế hoạch và lấy thông tin web
  - search_papers.py          tìm paper
  - ingest_docs.py            đọc tài liệu và tạo key_points/embedding
  - outline_generation.py     sinh outline và gán reference
  - search_journals.py        cập nhật journal, Q, ISSN

Phân tích dữ liệu và phương pháp
  data_analysis/
  - proposed_method_v2.py     model, hypotheses, variables, survey
  - analyzer_graph.py         lập kế hoạch, duyệt kế hoạch, chạy action
  - tools/analysis/preprocess  làm sạch/chuẩn bị dữ liệu
  - tools/analysis/cross_section  thống kê, regression, EFA, CFA, SEM, PLS, GSCA
  - tools/analysis/time          time series, stationarity, estimation, diagnostics
  - tools/analysis/panel         panel model và model selection

Viết báo cáo
  write_reports/
  - write_graph.py            viết report thông thường
  - seminar_graph_1/2/3.py    ba luồng chuyên đề
  - write_chat_graph.py       chatbot hỗ trợ viết
  - utils/utils_func.py       viết, tổng hợp, citation, bảng/hình, phụ lục
  - gen_slide_md.py           sinh PowerPoint từ nội dung
  - translate.py              dịch report/outline
  - references.py             format reference
  - log_cleaner.py            làm sạch analysis logs

Chatbot và chỉnh sửa trực tiếp
  ai_chatbot/
  - chatbot.py                hỏi đáp
  - inner_chatbot.py          hỏi đáp theo tài liệu
  - writer_chatbot.py         hội thoại hỗ trợ viết
  - ai_in_doc.py              xử lý đoạn văn được chọn
```

## 11. Vai trò các hệ thống lưu trữ

```text
MongoDB  : proposal, outline, report section, reference, cấu hình phân tích
Redis    : AI key, health status, LangGraph checkpoint
Qdrant   : embedding của tài liệu/reference
MinIO    : PDF, hình ảnh, bảng, file phân tích được sinh ra
```

## 12. Giới hạn kiểm tra hiện tại

File này mô tả routing theo code hiện tại. Static scan phát hiện lỗi syntax
f-string ở một số listener và graph module, nên chưa xác nhận được runtime
hoạt động hoàn chỉnh cho đến khi xử lý các lỗi này.

## 13. Câu hỏi critical thinking khi đọc project

Dùng các câu hỏi dưới đây khi đọc code hoặc xử lý một phản hồi từ khách hàng.
Mỗi câu đều chỉ ra điểm cần lần trong flow.

### A. Hiểu một request đi qua hệ thống như thế nào?

1. Request đầu tiên đi vào topic nào?
   - Thiết kế nghiên cứu: `document_setup_request`.
   - Viết/phân tích/report: `write_section_request`.
   - Chatbot: `chatbot_request`.
   - Sửa nội dung: `enhancement_request`.

2. Ai là code đầu tiên đọc request?
   - Listener tương ứng, sau đó listener đọc `event_type` để chọn nhánh.

3. Vì sao nhiều chức năng dùng chung một topic?
   - Kafka chỉ vận chuyển message; `event_type` mới là thông tin chọn nghiệp vụ.
   - Cách này gom routing vào listener, nhưng khi debug bắt buộc phải xem cả topic và `event_type`.

4. Sau listener, request đi đâu?
   - Vào class/module hoặc LangGraph tương ứng, rồi mới gọi LLM, database, search hoặc file storage.

5. Response quay về đâu?
   - Về response topic cùng nhóm với request; không tự quay ngược trực tiếp vào request topic.

6. Bước sau lấy dữ liệu từ đâu?
   - Thông thường client lấy response bước trước rồi gửi request mới. Listener không tự chạy toàn bộ chuỗi setup.

### B. Khi đọc phần thiết kế nghiên cứu

1. `proposal` được tạo ở đâu và dùng tiếp ở đâu?
   - Tạo trong các nhánh sinh title/proposal; sau đó truyền qua keywords, search papers, outline và writer.

2. Vì sao cần cả `key_points` và `paperChunk`?
   - `key_points` giúp chọn và hiểu nhanh paper; `paperChunk` giữ đoạn nguồn cụ thể để viết/citation.

3. Nếu paper không được gán vào outline thì chuyện gì xảy ra?
   - Paper không được đưa vào reference của section/subsection đó, nên writer không có nguồn để dùng ở phần đó.

4. Vì sao outline phải có `word_count`, `overview`, `subheadings`?
   - Đây là hợp đồng đầu vào để writer biết viết phần nào, viết sâu tới đâu và giới hạn độ dài.

5. Tại sao phải có `generate_outline_with_refs` sau `generate_outline`?
   - `generate_outline` chỉ tạo cấu trúc; bước sau mới gán paper, key point, chunk và cách sử dụng reference.

6. Tài liệu người dùng đi qua đâu?
   - `processed_docs` → `ingest_docs.py` → đọc/tóm tắt/embedding → MongoDB/Qdrant → dùng lại khi search hoặc viết.

### C. Khi đọc phần viết báo cáo

1. Writer biết section hiện tại là Literature Review, Methodology hay Results bằng cách nào?
   - `choose_refs` đọc heading trong outline và xác định vị trí các section; nếu không rõ thì dùng LLM để nhận diện.

2. Vì sao subsection được chia thành batch?
   - Các subsection độc lập có thể viết song song; subsection phụ thuộc nội dung trước phải chạy tuần tự.

3. Khi nào writer dùng `write`, `write_method`, `write_data`?
   - Viết thường dùng `write`; nội dung phương pháp dùng `write_method`; section có kết quả/log dữ liệu dùng `write_data`.

4. Vì sao writer không đưa toàn bộ analysis log vào prompt?
   - Log được chọn, làm sạch và chia thành block trước; chỉ block liên quan mới được viết thành nội dung học thuật.

5. Vì sao phải có bước `section_synthesizer`?
   - Worker viết từng subsection, còn synthesizer ghép lại, đánh số heading, gắn citation, bảng và hình.

6. `CHUYEN_DE_3` khác `write_content` ở đâu?
   - `CHUYEN_DE_3` chạy Analyzer trước để tạo log/file kết quả, sau đó mới chạy graph viết phần Results/Discussion.

### D. Khi đọc một điểm `interrupt`

1. Graph dừng vì lỗi hay vì cần khách hàng quyết định?
   - `interrupt` thường là điểm chờ người dùng; lỗi thật đi theo `error_code` và `error`.

2. Sau khi client nhận interrupt, phải giữ thông tin nào?
   - Giữ `thread_id`/`document_id`, loại điểm dừng và dữ liệu khách hàng muốn duyệt hoặc chỉnh.

3. Vì sao resume sai `thread_id` làm mất trạng thái?
   - Checkpoint được lưu theo identifier; identifier khác nghĩa là graph khác hoặc không có checkpoint.

4. Khách hàng chỉnh ở đâu thì dữ liệu thay đổi đi đâu?
   - Sửa plan → `planner`/`analyzer`; duyệt action → trạng thái action; sửa phương pháp → `final_proposal`; sửa đoạn văn → `AIInDoc`/enhance.

### E. Luồng phản biện với khách hàng cần tự hỏi gì?

1. Khách hàng đang phản hồi về kế hoạch, dữ liệu, phương pháp hay câu chữ?
   - Kế hoạch/dữ liệu: `analyzer`, `comment_data`, `check_logic_data`.
   - Phương pháp: `propose_method`, `resume_method`.
   - Câu chữ: `ai_in_doc`, `get_suggestions`, `enhance`, `enhance_all`.
   - Báo cáo đang viết dở: `write_content` hoặc `chuyen_de_*` với resume.

2. Phản hồi đó là command hay nội dung tự do?
   - Analyzer dùng command rõ như `[ACCEPT]`, `[EDIT_PLAN]`, `[APPROVE]`, `[REJECT]`.
   - Một số graph nhận `feedback` hoặc `user_input` để resume; phải xem đúng branch trước khi đổi format.

3. Phản hồi có làm chạy lại từ đầu không?
   - Không mặc định. Nếu có checkpoint và cờ resume thì graph tiếp tục từ điểm dừng; request mới không có resume có thể khởi tạo lại flow.

4. Khách hàng thấy response tạm hay kết quả cuối?
   - Có `ai_message`, `section`, `change_section` hoặc `has_finished` thì thường là trạng thái trung gian; chỉ khi graph hoàn thành mới có kết quả cuối đầy đủ.

### F. Cách lần ngược một issue từ khách hàng

```text
Khách hàng báo lỗi
  -> xác định chức năng họ đang dùng
  -> xác định request topic
  -> đọc event_type
  -> tìm branch trong listener
  -> kiểm tra input bắt buộc
  -> kiểm tra module/graph được gọi
  -> kiểm tra database/API/file mà branch dùng
  -> xem response: error_code, error, has_finished, ai_message
  -> xem health status và checkpoint nếu là flow dài
```

Các câu hỏi bắt buộc:

1. Message có tới Kafka không?
2. Listener có consume message không?
3. `event_type` có đúng tên enum không?
4. Input có thiếu field, sai kiểu hoặc rỗng không?
5. Lỗi xảy ra trước hay sau khi gọi LLM/tool?
6. Có phải timeout, quota, model không hỗ trợ hay lỗi dữ liệu?
7. Nếu khách hàng resume, `thread_id` có trùng checkpoint cũ không?
8. Response đã gửi nhưng frontend đang đọc đúng response topic chưa?

Nếu trả lời được tám câu này, thường đã xác định được lỗi nằm ở client,
Kafka/listener, input contract, graph/module, external service hay storage.

## 14. Bản đồ hàm code và logic chính

Phần này ghi các hàm cần đọc khi muốn lần từ request đến kết quả. Không cần
đọc mọi helper nhỏ; chỉ cần nắm các điểm vào, điểm rẽ nhánh, graph và chỗ lưu
kết quả là hiểu được luồng chính.

### A. Từ Kafka vào worker

| File / hàm | Logic cần nắm |
|---|---|
| `main.py` → `main()` | Khởi động bốn listener: document setup, write section, enhancement và chatbot. Mỗi listener chạy như một task async riêng. |
| `listener.py` → `BaseAsyncListener.__init__()` | Tạo kết nối MongoDB, Redis, Redis Stack, queue và semaphore giới hạn số task chạy đồng thời. |
| `BaseAsyncListener._ingestor_loop()` | Đọc record từ Kafka, đưa record vào queue, gửi health `PENDING` cho `document_id`, rồi commit offset. Đây là biên nhận message. |
| `BaseAsyncListener._worker_loop()` | Lấy record từ queue và gọi `_handle_record()` của listener con. Logic nghiệp vụ nằm ở từng listener. |
| `BaseAsyncListener.start()` | Mở MongoDB và Kafka consumer, sau đó tạo ingestor/worker task. |
| `BaseAsyncListener._finalize_task()` | Khi xong hoặc lỗi: hủy timer, gửi response về Kafka, cập nhật health `FINISHED`/`ERROR`/`SUSPENDED`. |
| `BaseAsyncListener.send_message()` | Gửi message vào response topic; đồng thời cập nhật Redis cho trạng thái report nếu có `document_id`. |
| `BaseAsyncListener.get_key()` | Lấy key LLM/search từ Redis theo `model_id`, `AI_KEY:db_key` hoặc `AI_KEY:search_web_key`. |
| `field_validate_*()` và `empty_value_check()` | Kiểm tra kiểu và field rỗng trước khi chạy graph. |

Luồng rút gọn:

```text
Kafka request topic
  -> _ingestor_loop()
  -> queue
  -> _worker_loop()
  -> listener con._handle_record()
  -> listener con xử lý event
  -> _finalize_task()
  -> Kafka response topic + Redis health/report
```

Điểm quan trọng: offset Kafka được commit ở ingestor, còn xử lý thật diễn ra
ở worker. Khi phản biện lỗi phải tách hai câu hỏi: message đã được consume
chưa, và worker/graph có xử lý thành công chưa.

### B. Document setup: từ ý tưởng đến outline có reference

#### 1. Router và các event

`document_setup_listener.py`:

- `_handle_record()` chọn cloud topic hay local topic, đọc request và đặt
  timeout cho task.
- `_handle_document_setup_event()` đọc `event_type`, validate input rồi rẽ
  sang hàm tương ứng: tìm paper, sinh domain/subdomain/keyword/title, tạo
  proposal, tạo outline, lấy journal hoặc xử lý tài liệu người dùng.
- `start_listener()` là điểm chạy service riêng của document setup.

Các nhánh không phải một pipeline duy nhất. Ví dụ `generate_domains` có thể
được gọi độc lập; còn outline thường nhận proposal, papers và key points từ
các bước trước đó.

#### 2. Sinh ý tưởng và proposal

File: `document_setup/src/modules/idea_generation.py`, class `IdeaGeneration`.

| Hàm | Logic |
|---|---|
| `generate_keywords_v2()` / `generate_keywords_v3()` | Từ field/domain sinh bộ keyword phục vụ search hoặc mở rộng proposal. |
| `generate_domains()` | Từ chủ đề ban đầu sinh các domain nghiên cứu khả thi. |
| `generate_subdomains()` | Chia domain thành các hướng nhỏ hơn để search và sinh title có phạm vi rõ hơn. |
| `generate_titles_v2()` | Lập kế hoạch search cho từng subdomain, lấy context từ web/knowledge base rồi gọi bước sinh proposal. |
| `_generate_for_subdomain()` | Xử lý riêng từng subdomain, tách các nhánh title theo hướng nghiên cứu. |
| `generate_proposal_v2()` / `_generate_proposal_v2()` | Sinh proposal, dịch/đánh giá khi cần, lọc title trùng và trả proposal có cấu trúc. |
| `generate_extra_proposal()` | Sinh thêm proposal khi kết quả hiện tại chưa đủ. |
| `mix_titles_v2()` | Kết hợp title/ý tưởng đã có thành hướng nghiên cứu mới. |
| `get_research_type()` | Phân loại proposal để outline, methodology và data analysis biết hướng xử lý. |

File: `document_setup/src/modules/search_web.py`, class `SearchWeb`.

- `plan_knowledge_base()` / `plan_knowledge_base_v2()` quyết định cần tìm gì.
- `construct_knowledge_base()` gom kết quả search thành context đưa vào prompt.

Search ở đây không chỉ là gọi API; còn có bước lập kế hoạch và dựng context
trước khi LLM sinh nội dung.

#### 3. Search paper và key points

File: `document_setup/src/modules/search_papers.py`, class `SearchPapers`.

- `refine_query_v2()` làm query rõ hơn trước khi search.
- `_search_papers()` thực hiện search theo nguồn/journal.
- `search_papers()` điều phối search, lọc và chuẩn hóa danh sách paper.
- `add_user_language_title()` bổ sung title theo ngôn ngữ người dùng.

File: `document_setup/src/modules/ingest_docs.py`, class `VectorDBProcessor`.

- `batch_ingestion()` chunk và embed nhiều tài liệu.
- `ingest_admin_docs()` đưa tài liệu hướng dẫn/admin vào kho dùng chung.
- `get_key_points()` và `get_key_points_user_docs()` lấy key points.
- `embed_user_docs()` đưa tài liệu người dùng vào vector DB.
- `update_user_docs()` cập nhật dữ liệu đã ingest.

`KeyPoints` gom các trường như `main_topic`, `background`, `importance`,
`research_gap`, `problem`, `objectives`, `scope`, `methodology`, `data`,
`analysis`, `results`, `contributions`, `hypotheses`, `model_design`,
`variables` và `measurement_items`. Các bước sau dùng phần tóm tắt có cấu
trúc này thay vì nhồi toàn bộ paper vào mỗi prompt.

Luồng paper:

```text
query
  -> refine_query_v2()
  -> search_papers()
  -> lấy abstract/full text/chunk
  -> get_key_points()
  -> embed nếu là tài liệu cần truy hồi
  -> papers + key_points cho outline/writer
```

#### 4. Sinh outline và gắn reference

File: `document_setup/src/modules/outline_generation.py`, class
`OutlineGeneration`.

| Hàm | Logic |
|---|---|
| `generate_outline_description_v2()` | Từ proposal/research type sinh khung outline và mô tả cho từng heading. |
| `update_outline()` / `update_outline_percent()` | Cập nhật outline sau khi người dùng chỉnh hoặc reference thay đổi. |
| `get_refs_section()` / `get_refs_subsection()` | Chọn reference phù hợp cho section/subsection. |
| `get_outline_with_refs_v2()` | Lấy key points, map paper vào section/subsection, tạo kế hoạch viết và trả outline có reference. |
| `_map_papers_to_sections()` | Phân bổ paper vào các section lớn. |
| `_map_single_paper_to_sections()` | Đánh giá một paper nên xuất hiện ở section nào. |
| `_distribute_papers_to_subsections()` | Chia paper cho subsection để writer dùng đúng phạm vi. |
| `_generate_plans_for_subsection()` | Tạo kế hoạch nội dung cho từng subsection. |
| `_generate_integration_paragraph()` | Tạo đoạn nối/tổng hợp khi nhiều paper cùng đóng góp. |
| `update_user_refs()` / `update_user_refs_v2()` | Cập nhật reference do người dùng thêm hoặc thay đổi. |

Outline mô tả “section này sẽ viết gì”, còn reference mapping mô tả “paper nào
được phép hỗ trợ section này”. Outline đúng nhưng mapping sai vẫn có thể tạo
câu chữ trôi chảy với dẫn chứng sai chỗ.

### C. Data analysis và đề xuất phương pháp

#### 1. Graph phân tích dữ liệu

File: `data_analysis/src/modules/analyzer.py`, class `Analyzer`.

- `run_graph()` là cửa vào phân tích: chọn checkpoint Redis/Mongo, tạo hoặc
  resume graph, nhận `feedback`, rồi trả interrupt hoặc kết quả gồm
  `analyze_log`, `detailed_logs`, `generated_files`.
- `check_variable_conditions()` kiểm tra điều kiện/quan hệ của biến.
- `check_variable_logic()` kiểm tra logic biến và trả `errors_logic`,
  `warnings_logic`.

File: `data_analysis/src/modules/analyzer_graph.py`.

```text
coordinator_node()
  -> background_investigation_node()
  -> planner_node()
  -> human_feedback_node()
  -> analyzer_node()
  -> section_reporter()
  -> collector_node()
```

- `coordinator_node()` xác định mục tiêu phân tích.
- `background_investigation_node()` tìm thông tin nền/điều kiện cần thiết.
- `planner_node()` lập kế hoạch tool và các bước phân tích.
- `human_feedback_node()` dừng để khách hàng duyệt hoặc sửa plan:
  `[ACCEPT]` đi tiếp, `[EDIT_PLAN]` quay lại planner, còn
  `[APPROVE]`/`[REJECT]` xử lý action đang chờ.
- `analyzer_node()` chạy tool và có thể quay lại khi cần thêm thông tin.
- `section_reporter()` tạo log theo section; `collector_node()` gom log và
  file cuối cùng.

Các nhóm tool chính dưới `data_analysis/src/tools/analysis/`:

- `preprocess`: làm sạch, chuẩn hóa và chuẩn bị dữ liệu.
- `cross_section`: descriptive, t-test/ANOVA, regression, EFA/CFA/SEM,
  PLS/GSCA, clustering và pipeline.
- `time`: stationarity, chọn cấu trúc model, estimation, diagnostics và
  application.
- `panel`: chọn model và phân tích panel nâng cao.

#### 2. Graph đề xuất phương pháp

File: `data_analysis/src/modules/proposed_method_v2.py`.

- `get_key_points()` lấy context nghiên cứu có cấu trúc.
- `coordinator()` quyết định bước tiếp theo theo `research_type` và state.
- `reference_selection()`, `model_recommend()`, `recommend_assumptions()`,
  `recommend_variables()`, `recommend_survey()` và
  `recommend_questions()` sinh từng phần methodology.
- `review_interrupt()` dừng để người dùng review từng bước.
- `human_feedback_node()` đọc feedback và điều hướng lại node cần sửa.
- `finalize_analysis()` gom model, giả thuyết, biến và survey thành kết quả.
- `parse_variables_node()` chuẩn hóa biến để writer dùng tiếp.
- `get_graph()` nối các node thành graph có checkpoint.

Người dùng có thể duyệt reference, sửa model, sửa biến hoặc yêu cầu sinh lại
một node; checkpoint giữ ngữ cảnh của lần trước.

### D. Writer: từ outline đến section hoàn chỉnh

#### 1. Router của write service

File: `write_listener.py`.

- `_handle_record()` chọn local/cloud request topic và timeout.
- `_handle_write_section_event()` rẽ theo `WriteEvent`:
  `write_content`, `analyzer`, `analyzer_tool`, `chuyen_de_1`,
  `chuyen_de_2`, `chuyen_de_3`, `gen_slides`, `translate_report`,
  `comment_data`, `check_logic_data`, `propose_method`, `delete_report`.
- `check_interrupt()` xử lý điểm graph dừng chờ input.
- `send_section()` gửi từng section/chunk để frontend thấy tiến độ.
- `write_appendices()` xử lý phần phụ lục sau khi phần thân hoàn tất.

Nhánh `write_content` nhận outline, papers, proposal, field, domain và các
cờ như `resume`, `resume_error`, `resume_method`, `resumeCharacter`,
`use_web_search`, `thread_id`. Vì vậy “resume không chạy” cần kiểm tra cả
checkpoint key/thread id, không chỉ kiểm tra prompt.

#### 2. Graph viết section thường

File: `write_reports/src/modules/write_graph.py`.

```text
load_input()
  -> choose_refs()
  -> write_section()
  -> create_subsection_batch()
  -> check_propose_method()
  -> check_for_data()
  -> write_subsection()
  -> section_synthesizer()
  -> lặp subsection/section
  -> add_ref()
  -> write_appendices()
```

| Hàm | Logic |
|---|---|
| `load_input()` | Load model, paper, outline và input ban đầu vào state. |
| `choose_refs()` | Phân loại section, lấy report hiện tại từ Mongo và chuẩn bị reference/context. |
| `write_section()` | Chọn section hiện tại; nếu đến ranh giới chapter hoặc cần input thì interrupt. |
| `create_subsection_batch()` | Gom subsection độc lập để chạy batch; subsection phụ thuộc thì giữ thứ tự. |
| `check_propose_method()` | Dừng yêu cầu đề xuất method nếu section cần method nhưng chưa có `final_model`. |
| `check_for_data()` | Dừng nếu section cần data nhưng chưa có `analyze_log`; nếu có thì load log/file/reference. |
| `write_subsection()` | Chọn `write_data`, `write_method`, `write` hoặc `write_no_sub` theo state. |
| `section_synthesizer()` | Gom subsection, đánh lại số heading, citation, table và survey question. |
| `add_ref()` | Format và thêm references sau khi section cuối đã xong. |
| `write_appendices()` | Sinh phụ lục từ file/log/table đã thu thập. |
| `get_graph()` | Nối các node và điều kiện lặp của write flow. |

#### 3. Các hàm sinh nội dung thật

File: `write_reports/src/modules/utils/utils_func.py`.

- `_load_model()` đọc reference/key points từ Mongo, đặc biệt vùng
  `user_documents.reports_refs`.
- `load_current_section()` đọc section đã có trong `admin.outlines`, gắn
  reference summary/chunk vào heading và xác định phase search.
- `get_need_data()` và `get_need_propose_method()` dùng LLM structured output
  để quyết định subsection có cần dữ liệu hoặc cần đề xuất method không.
- `write()` sinh subsection bình thường, có thể `search_web()`, chọn reference
  theo title rồi `tidy_up()`.
- `write_no_sub()` là đường viết section không có subsection.
- `write_data()` chọn và làm sạch log, parse log thành block, chọn block liên
  quan, viết prose rồi chèn file thành table/figure.
- `write_method()` chọn log methodology như model, hypothesis, variables,
  survey/question và viết section phương pháp; có thể chèn ảnh model.
- `_section_synthesizer()` hợp nhất kết quả writer, dọn heading/citation và
  cộng token usage.
- `get_appendices()` tạo phụ lục và dọn cache search/reference liên quan.

`write_data()` và `write_method()` là hai nhánh khác writer thường. Chúng nhận
đầu ra của analyzer, nên nếu analyzer chưa hoàn thành hoặc log không được lưu
đúng document configuration thì writer không có đủ nguyên liệu dù outline
vẫn hợp lệ.

#### 4. Ba graph chuyên đề

Các file `seminar_graph_1.py`, `seminar_graph_2.py` và `seminar_graph_3.py`
có cấu trúc tương tự writer thường: `load_model`, `choose_refs`,
`write_section`, `create_subsection_batch`, `write_subsection`,
`section_synthesizer`, `add_ref`, `write_appendices`, `get_graph`.

- `chuyen_de_1`: chủ yếu viết phần tổng quan/literature review.
- `chuyen_de_2`: viết phần methodology, có nhánh dùng kết quả đề xuất phương
  pháp.
- `chuyen_de_3`: viết phần result/discussion; trước đó listener chạy analyzer,
  lưu `detailedLogs`, `analyzeLog`, `generatedFiles` vào
  `admin.document_configurations`, rồi mới chạy graph chuyên đề 3.

Chuỗi riêng của `chuyen_de_3`:

```text
WriteSectionEventListener
  -> Analyzer.run_graph()
  -> lưu analyzeLog/detailedLogs/generatedFiles
  -> seminar_graph_3.get_graph()
  -> check_for_data()
  -> write_data()
  -> section_synthesizer()
  -> response từng chunk + kết quả cuối
```

### E. Chatbot, enhancement và kiểm tra phản biện

#### 1. Chatbot

File: `chatbot_listener.py`.

- `_handle_record()` chọn cloud/local topic.
- `_handle_chatbot_event()` rẽ theo `AIEvent`:
  `OUTER_CHATBOT` trả lời hội thoại chung; `INNER_CHATBOT` có thêm user
  documents; `WRITER_CHATBOT` dùng graph chat của write reports; `WRITER`
  dùng writer chatbot graph.
- Các nhánh dài hỗ trợ `resume`, `conv_id`, `thread_id` và interrupt.

Phân biệt `INNER_CHATBOT` với `WRITER_CHATBOT`: inner chatbot thiên về hỏi
đáp trên tài liệu người dùng; writer chatbot thiên về ngữ cảnh viết báo cáo.

##### Case 2: writer chatbot bị kẹt ở bước hỏi dữ kiện

Hiện tượng: user nói muốn viết về một chủ đề nhưng chưa đủ dữ kiện. Khi user
chuyển sang chat nội dung khác, chatbot vẫn trả lại prompt yêu cầu bổ sung dữ
kiện.

Nguyên nhân: graph vẫn giữ state thu thập dữ kiện của report hiện tại.
`_is_ask_clarify()` thấy các field bắt buộc còn thiếu nên tiếp tục gọi
`CLARIFY_REPORT`, trong khi `_check_intent()` trước đây chỉ phân biệt đổi loại
intent, chưa phân biệt câu trả lời dữ kiện, chủ đề mới và chat ngoài luồng.
Ngoài ra graph có edge conditional và unconditional trùng từ bước nhận câu trả
lời, khiến state có thể bị cập nhật hai nhánh.

Flow mong muốn cần chốt khi xử lý case này:

```text
chat thu thập dữ kiện
  -> đủ dữ kiện
  -> summary + user xác nhận
  -> generate outline
  -> user duyệt outline
  -> viết từng section/chapter
```

Khi chưa đủ dữ kiện, chatbot chỉ gọi `CLARIFY_REPORT` nếu message mới thực sự
là câu trả lời bổ sung. Chủ đề mới sẽ xóa `dependencies` cũ rồi thu thập lại;
chat ngoài luồng được trả lời một lượt và sau đó quay lại câu hỏi đang dở;
đổi loại intent vẫn đi qua bước xác nhận.

Đã triển khai trong `writer_chatbot.py`, `writer.py` và `writer_prompt.py`:

- Thêm `message_type`: `field_answer`, `new_topic`, `off_topic`.
- Bỏ edge chạy trùng ở report/section flow.
- Reset note khi có chủ đề mới.
- Thêm nhánh trả lời chat ngoài luồng rồi resume lại bước thiếu dữ kiện.

##### Case 3: model nghiên cứu bị chọn ngoài ba loại base

Ba loại model hợp lệ là:

```text
Simple / Extended / Comprehensive
```

Tài liệu mô tả `Simple` cho quan hệ trực tiếp, `Extended` cho mediator hoặc
moderator, và `Comprehensive` cho nhiều biến phụ thuộc, biến ẩn hoặc mạng
quan hệ phức tạp. Mô hình có nhiều biến phụ thuộc (ví dụ 5 biến) và cấu trúc
phức tạp phải được xếp vào `Comprehensive`, nhưng cần kiểm tra thêm sample
size và chất lượng thang đo.

Nguyên nhân model đôi lúc trả về tên khác như `SEM`, `PLS-SEM`, `TAM`, `TPB`
hoặc `Complex Model`: `HEURISTIC_GUIDE` có rule chi tiết nhưng chỉ được dùng
ở nhánh `ANALYZER`; nhánh `PROPOSE_METHOD` chạy `model_recommend` với
`model_instructions` rút gọn. Ngoài ra `ModelRecommendation` chỉ nhận
`thinking_process` và `sketch` dạng string, còn parser chỉ đọc giá trị sau
`ModelType:` mà không kiểm tra whitelist.

Hướng xử lý khi triển khai:

- Dùng chung `HEURISTIC_GUIDE` cho prompt `model_recommend`.
- Khóa `ModelType` bằng enum chỉ gồm `Simple`, `Extended`, `Comprehensive`.
- Tách rõ model type, theory (`TAM`, `TPB`, `UTAUT`) và phương pháp phân tích
  (`SEM`, `PLS-SEM`, regression, PROCESS).
- Validate `ModelType` trong sketch phải trùng với model type structured output;
  nếu sai thì reject/regenerate.

Không cần đổi input của writer cho lỗi format này. Chỉ cần bổ sung sample size
nếu muốn đánh giá đầy đủ điều kiện thống kê trước khi chọn `Comprehensive`.

##### Case 10: gợi ý phương pháp chạy số liệu chưa bám dạng dữ liệu

Hiện tượng: phương pháp phân tích được đề xuất có lúc không phù hợp với dạng
dữ liệu, giống như LLM tự chọn ngẫu nhiên.

Root cause đã xác định:

- Nhánh `propose_method` chủ yếu nhận `research_type` và proposal; không nhận
  profile dataframe thực tế như số dòng, kiểu biến, biến phụ thuộc, time/entity
  index, binary/continuous hay latent/observed.
- `model_recommend` đang đề xuất conceptual model, không phải bộ chọn tool chạy
  số liệu. Hai khái niệm này đang bị dùng lẫn.
- Planner có `HEURISTIC_GUIDE`, nhưng vẫn đưa toàn bộ `TOOLS_DOCUMENT` cho LLM
  tự chọn. `available_tools` chỉ được tính sau đó để hiển thị/review, chưa là
  rào chắn trước khi sinh plan.
- `data_summary` của planner đang để trống. Ngoài ra parameters do LLM sinh ra
  bị bỏ khi chuyển `SimplifiedPlanStep` thành `AnalyzeStep`, nên tool chạy bằng
  default thay vì cấu hình đã được đề xuất.
- `get_tool_availability()` mới kiểm tra thô time/entity/latent/binary, chưa đủ
  các điều kiện như sample size, cardinality, missingness, ordinal và mục tiêu
  phân tích.

Hướng xử lý khi triển khai:

- Tạo một `data_profile` từ dataframe thật và biến đã parse.
- Dùng profile để dựng danh sách phương pháp hợp lệ và thứ tự prerequisite;
  LLM chỉ chọn trong danh sách này, sau đó validate lại trước khi chạy.
- Tách rõ `model_recommend` (mô hình nghiên cứu) khỏi analyzer planner
  (phương pháp chạy số liệu).
- Giữ lại parameters của planner khi tạo `AnalyzeStep`.
- Nếu chưa có dataset thì chỉ đề xuất phương pháp dự kiến, không khẳng định
  phương pháp chạy số liệu cuối cùng.

##### Case 4: bảng kết quả và đoạn phân tích không đồng bộ

Hiện tượng: trong chương kết quả, bảng và đoạn phân tích không hiển thị song
song theo từng kết quả/giả thuyết. Có trường hợp cùng một Cronbach's Alpha
nhưng chương chính ghi `0.87`, còn bảng ở phụ lục ghi `0.574`.

Root cause đã xác định:

- Tool tính Alpha bằng code (`pg.cronbach_alpha(data)`), không phải bằng prompt.
- `write_data()` cho LLM viết narrative trước; lúc này prompt chỉ nhận tên file
  CSV, chưa nhận nội dung bảng thực tế.
- Sau khi LLM viết xong, code mới chèn CSV/HTML vào placeholder. Vì vậy LLM có
  thể lấy số từ log/AI overview hoặc suy diễn sai, còn bảng lại dùng số thật.
- `get_appendix_4()` chỉ dựng bảng từ `generated_files`, không chèn đoạn phân
  tích tương ứng cạnh bảng.
- Pipeline có thể ghi đè `generated_files[file_path]` sau khi chạy lại/reflection
  nhưng vẫn giữ log cũ trong `detailedLogs`; log cũ và bảng mới có thể lệch.

Về lưu trữ: `detailedLogs`, `analyzeLog` và `generatedFiles` được lưu trong
`document_configurations`. Tuy nhiên overview/chart chỉ lưu kết quả ảnh hoặc
file, chưa có liên kết rõ giữa narrative, bảng và cùng một analysis run.

Hướng xử lý khi triển khai:

- Truyền nội dung bảng thực tế vào prompt writer, không chỉ truyền filename.
- Nếu log và bảng khác số, luôn lấy bảng làm nguồn sự thật; không cho LLM tự
  tính hoặc suy diễn lại Cronbach's Alpha.
- Bắt buộc mỗi bảng có đoạn phân tích ngay sau placeholder của chính bảng đó.
- Gắn narrative và generated file bằng cùng `file_key`/analysis run để không
  trộn log cũ với bảng mới.
- Cho phụ lục dùng đúng bảng canonical đã dùng ở chương chính; không tính lại
  từ AI overview.

Không giải quyết case này bằng cách sửa riêng câu chữ prompt. Lỗi chính nằm ở
việc narrative được sinh trước khi writer nhận dữ liệu bảng và việc các nguồn
log/file chưa được liên kết theo cùng một phiên phân tích.

#### 2. Enhancement trong tài liệu

File: `enhance_listener.py`, class `EnhancementEventListener`.

- `_handle_record()` nhận request và xử lý timeout.
- `_handle_enhancement_event()` rẽ theo `EnhancementEvent`.
- `AI_IN_DOC` lấy paragraph được chọn, context, action và proposal rồi gọi
  `AIInDoc.process_paragraph()`.
- `GET_SUGGESTIONS` review section/context bằng `_review()` và trả các đoạn
  gợi ý.
- `ENHANCE` cập nhật một gợi ý qua `update_one()`.
- `ENHANCE_ALL` cập nhật nhiều gợi ý qua `update_many()`.

Đây là flow chỉnh câu/chỉnh đoạn trên nội dung đã có, không phải flow sinh
outline hay phân tích dữ liệu mới.

#### 3. Hai nhánh kiểm tra để phản biện với khách hàng

Trong `write_listener.py`:

- `comment_data` gọi `Analyzer.check_variable_conditions()` và trả
  `comments`: giải thích điều kiện/điểm cần xem lại.
- `check_logic_data` gọi `Analyzer.check_variable_logic()` và trả
  `errors_logic`, `warnings_logic`: tách lỗi logic nghiêm trọng khỏi cảnh báo
  cần cân nhắc.
- `propose_method` gọi graph đề xuất phương pháp; `resume_method` tiếp tục từ
  checkpoint thay vì sinh lại toàn bộ.

Khi khách hàng nói “kết quả phân tích sai”, cần xác định họ đang nói về logic
biến, điều kiện thống kê, output của tool, cách diễn giải thành văn, hay
reference. Mỗi loại đi vào một hàm khác nhau.

### F. Những chuỗi gọi hàm nên nhớ

#### Sinh outline có reference

```text
document_setup_listener._handle_record()
  -> _handle_document_setup_event()
  -> OutlineGeneration.get_outline_with_refs_v2()
  -> _map_papers_to_sections()
  -> _distribute_papers_to_subsections()
  -> _generate_plans_for_subsection()
  -> response outline + refs
```

#### Viết một báo cáo bình thường

```text
write_listener._handle_record()
  -> _handle_write_section_event()
  -> write_graph.get_graph()
  -> load_input() -> choose_refs()
  -> write_section() -> create_subsection_batch()
  -> check_for_data() -> write_subsection()
  -> write()/write_data()/write_method()
  -> section_synthesizer()
  -> add_ref() -> write_appendices()
```

#### Chạy chuyên đề 3 có phân tích dữ liệu

```text
write_listener._handle_write_section_event()
  -> Analyzer.run_graph()
  -> analyzer_graph.coordinator_node()
  -> planner_node() -> human_feedback_node()
  -> analyzer_node() -> collector_node()
  -> lưu log/file
  -> seminar_graph_3.get_graph()
  -> write_data() -> section_synthesizer()
```

#### Sửa một đoạn trong tài liệu

```text
enhance_listener._handle_enhancement_event()
  -> AIInDoc.process_paragraph() / update_one() / update_many()
  -> response change_section hoặc suggested paragraphs
```

### G. Cách đọc một hàm khi trace lỗi

Với mỗi hàm quan trọng, đọc theo bốn câu hỏi sau:

1. Hàm nhận state/input nào, field nào bắt buộc và field nào tùy chọn?
2. Hàm gọi LLM, search, database, vector DB hay graph nào tiếp theo?
3. Hàm trả state/response gì cho node hoặc listener kế tiếp?
4. Nếu timeout, interrupt, exception hoặc resume xảy ra ở đây thì state được
   lưu ở đâu và client nhận dấu hiệu nào?

Ví dụ với `write_subsection()`: không hỏi “LLM viết có tốt không” ngay. Phải
kiểm tra trước `need_data`, `need_method`, `analyze_log` và `final_model` để
biết nó đã đi vào đúng nhánh `write_data`, `write_method` hay `write` chưa.

### H. Các điểm dễ phát sinh vấn đề

- Sai `event_type`: request vẫn tới Kafka nhưng không vào đúng branch.
- Sai topic cloud/local: producer gửi đúng message nhưng listener đang nghe
  topic còn lại.
- Thiếu `document_id`, `thread_id` hoặc `outline_code`: mất liên kết giữa
  response, checkpoint và report đang viết.
- Có `resume` nhưng khác thread/checkpoint: graph có thể khởi tạo state mới.
- Có outline nhưng thiếu key points/ref chunks: writer chạy được nhưng nội
  dung thiếu nền tảng hoặc citation.
- Có section cần data nhưng thiếu `analyzeLog`: `check_for_data()` dừng flow.
- Analyzer tạo file nhưng chưa lưu `generatedFiles`: writer không chèn được
  bảng/hình.
- Lỗi provider/model/quota/token: xem `error_handle.py`, `error_type.py` và
  response `error_code`; không quy ngay cho Kafka.
- Syntax/import/runtime chưa pass: static code flow có thể đúng trên giấy
  nhưng service vẫn không start được. Giới hạn kiểm tra hiện tại ở mục 12 vẫn
  phải được tính đến.
