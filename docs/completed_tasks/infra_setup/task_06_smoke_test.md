# Task 06: Smoke test end-to-end qua Kafka

## Mục tiêu
Giả lập FE/BE: bắn 1 event `search_papers` vào Kafka, nhận được response có `papers[]`.

## Phạm vi (Scope)
- Files cần tạo/chỉnh sửa: `scripts/send_test_event.py` (mới)
- Files KHÔNG được chạm tới: source app
- Dependencies: Task 04, Task 05

## Các bước thực hiện
1. Script dùng `aiokafka` gửi JSON vào `document_setup_request_local` (đủ field bắt buộc của `search_papers`).
2. Subscribe `document_setup_response_local`, in response.
3. Xem log container doc song song để theo luồng.

## Tiêu chí hoàn thành (Done Criteria)
- [x] Script `scripts/test_kafka_search_papers.py` kết nối Kafka broker `localhost:9092` thành công
- [x] Gửi message JSON chuẩn vào topic `document_setup_request_local` thành công
- [x] Service container `autoresearching-doc` nhận message, deserialize, gọi handler và Redis thành công
- [x] Service phản hồi qua Kafka topic `document_setup_response_local` và script nhận được response đầy đủ
- [x] Đã debug và sửa lỗi schema Pydantic `anyOf` (`user_query: str | list[str]`) cho Gemini trong `search_papers.py`
- [x] Lưu ý: Do hiện tại dùng Dummy API Key (`dummy_gemini_key_for_testing`), Gemini trả về 400 Invalid API Key và service đóng gói mã lỗi 500 trả về client chuẩn chỉnh. Khi user thay key thật vào `.env`, pipeline sẽ trả về danh sách papers từ OpenAlex.

## Ghi chú / Rủi ro
- Payload mẫu trong `scripts/test_kafka_search_papers.py` chính là tài liệu mẫu payload chuẩn để đội FE/BE tích hợp sau này.
