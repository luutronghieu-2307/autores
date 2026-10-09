 TASK 2: Viết bộ Script Test tự động cho các tính năng tiêu biểu
Mục tiêu: Để bạn tự kiểm tra toàn bộ 4 service trên máy mình, đảm bảo AI chạy ngon 100% trước khi team kia gọi vào.

 2.1. Đã có: scripts/test_kafka_search_papers.py (Tìm bài báo - Đã test thành công ✅).
 2.2. Tạo scripts/test_kafka_idea_gen.py: Test tính năng sinh ý tưởng & tên đề tài nghiên cứu.
 2.3. Tạo scripts/test_kafka_outline.py: Test tính năng sinh dàn ý / đề cương nghiên cứu.
 2.4. Tạo scripts/test_kafka_chatbot.py: Test tính năng AI Chatbot trao đổi học thuật.
🔹 TASK 3: Cấu hình Mạng (Network / IP) để Team kết nối vào Kafka
Mục tiêu: Cho phép máy tính của bạn dev khác trong công ty kết nối được vào Kafka 9092 trên máy của bạn (hoặc trên VPS).

 3.1. Kiểm tra IP LAN của máy bạn (ip a hoặc hostname -I).
 3.2. Cập nhật KAFKA_ADVERTISED_LISTENERS trong docker-compose-infra.yaml từ localhost sang IP LAN (hoặc IP VPS) để máy ngoài gọi vào được.
 3.3. Mở quyền truy cập cổng 8080 (Kafka UI) để cả team cùng xem message trực tiếp trên web.
🔹 TASK 4: Họp bàn giao & Đấu nối tính năng đầu tiên
Mục tiêu: Hoàn thành kết nối thực tế 1 tính năng đầu tiên từ giao diện FE xuống AI của bạn.

 4.1. Gửi file tài liệu KAFKA_INTEGRATION_GUIDE.md cho bạn Backend chính / FE.
 4.2. Thống nhất chọn tính năng đầu tiên để đấu nối: Tìm kiếm bài báo (search_papers) hoặc Lên ý tưởng (idea_generation).
 4.3. Backend chính / FE gửi 1 request thật từ giao diện.
 4.4. Hai bên cùng mở http://<IP>:8080 (Kafka UI) để xem message chạy qua và xác nhận FE hiển thị kết quả thành công.