# Giai đoạn03 Giải mã và tiền xử lý

```text
Thực hiện giai đoạn03 tại D:/video csdldpt/he_thong_nhom12. Đọc prompts/BOI_CANH_CHUNG.md và kết quả01–02. Dùng thư viện/mô hình đã xác minh.

Hoàn thiện media.py và preprocess.py để bám mục2.1.3 báo cáo. Metadata dùng FFprobe, không lấy duration=frame_count/fps làm dữ liệu chính. Chọn PTS gần target bằng actual timestamps, lưu target/actual và sai số; không tự bù timestamp không hợp lệ bằng FPS. Nếu OpenCV không hỗ trợ file cụ thể, bổ sung backend phù hợp qua ports thay vì bỏ video âm thầm.

Chọn mẫu thật gồm cả sáu lớp và các trường hợp: landscape, portrait, rotation metadata, fps khác nhau/VFR nếu có, video ngắn, viền đen, rừng tối và nền hoa tối. Không khẳng định có VFR/rotation chỉ từ phỏng đoán; nếu thiếu fixture thật thì dùng fixture kiểm thử kỹ thuật và ghi rõ nguồn. Xuất contact sheets target/PTS, ảnh trước/sau crop và letterbox, kiểm tra trực quan.

Xác minh max-composite16khung, liên tục từ mép, ngưỡng percentile/mean, min1%, giữ40%, resize360→crop→256 và CLIP pad224. Motion crop chuyển đúng hệ tọa độ theo cả hai chiều, cặp PTS tăng và khoảng cách thực được lưu. Không cắt/thay file MP4 nguồn.

Thêm kiểm thử có ý nghĩa cho lỗi vừa sửa, gồm PTS thiếu/không tăng, crop nhầm vùng tối, méo tỷ lệ hoặc sai rotation. Đầu ra gồm ảnh bằng chứng, bảng PTS/crop, code và docs/phases/03_KET_QUA.md.

Nghiệm thu: adapter thật chạy trên mẫu, ảnh crop/letterbox được xem, sai số chọn khung hợp lý so với khoảng cách PTS lân cận. Không lấy unit test giả lập làm chứng cứ decoder thật. Chưa build toàn bộ561video.
```
