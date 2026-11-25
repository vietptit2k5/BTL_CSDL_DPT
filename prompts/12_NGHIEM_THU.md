# Giai đoạn12 Đóng gói và nghiệm thu cuối

```text
Thực hiện giai đoạn12 tại D:/video csdldpt/he_thong_nhom12. Đọc prompts/BOI_CANH_CHUNG.md và toàn bộ kết quả01–11. Mục tiêu là kiểm chứng bàn giao được, không thêm tính năng mới ngoài yêu cầu.

Rà từng yêu cầu XLSX D34 và mỗi ràng buộc report_spec bằng ma trận nghiệm thu: module, test/chạy thật, artifact, mục báo cáo, trạng thái. Chạy bộ test cuối, kiểm tra cú pháp, DB integrity/coverage/vector/provenance, truy vấn ảnh thật và demo trình duyệt. Xác minh trên phiên làm việc mới bằng hướng dẫn khởi chạy; nếu có thể dùng môi trường sạch trong phạm vi dự án. Không tuyên bố portable nếu còn đường dẫn tuyệt đối chưa xử lý.

Đóng gói mã/config/spec, dependency lock đã thử, script setup/run/check, tài liệu, các truy vấn mẫu có nguồn, trace và báo cáo. Dataset/model/index lớn có thể ở thư mục dữ liệu riêng: ghi rõ thành phần cần mang theo, checksum, cách định vị/mapping đường dẫn và cách tái tạo; không bắt tải Internet trong buổi demo nếu đã chuẩn bị offline. Không đưa venv, token, cache thừa hay script dọn ổ vào gói nộp.

Chuẩn bị kịch bản demo cho ba thành viên: giới thiệu dữ liệu/đặc trưng, giải thích CSDL và pipeline, upload ảnh mới, xem5video/PTS, xem trung gian, nêu đánh giá và giới hạn. Chuẩn bị câu hỏi thường gặp như vì sao Flow không dùng cho ảnh, vì sao K16, CLIP khác HSV/LBP, cách kiểm soát dữ liệu cũ và điểm có phải xác suất không. Không tự phân công theo năng lực chưa biết; đưa đề xuất có thể điều chỉnh.

Đầu ra: docs/NGHIEM_THU_CUOI.md, hướng dẫn bàn giao, kịch bản demo, danh sách artifact/gói mã và docs/phases/12_KET_QUA.md. Ghi các hạn chế còn thật sự tồn tại; không đánh dấu cả hệ thống hoàn thành nếu còn tiêu chí bắt buộc chưa đạt.

Nghiệm thu cuối: đúng đề ảnh→5video, dữ liệu và feature đầy đủ, demo chạy thật, kết quả đánh giá và báo cáo tái lập, người nhận biết cách khởi chạy offline. Không tự gửi/nộp/publish sản phẩm ra ngoài.
```
