# Giai đoạn08 Tìm kiếm và kết quả trung gian

```text
Thực hiện giai đoạn08 tại D:/video csdldpt/he_thong_nhom12. Đọc prompts/BOI_CANH_CHUNG.md và kết quả05–07; dùng index thật đã ready.

Hoàn thiện query_image end-to-end: ảnh người dùng tùy chọn đi qua cùng preprocessing/extractor với khung video; so sánh HSV/LBP/CLIP, gộp trên cùng khung, chọn khung tốt nhất mỗi video, trả đúng5 ID khác nhau giảm dần, tie-break ổn định. Không lọc theo lớp hoặc tự gán chủ đề trước tìm kiếm. Ảnh ngoài chủ đề vẫn có top5 tương đối; không dựng motion cho ảnh.

Trace cần chứa query/source hash, index/spec/model/profile, crop, vector, khoảng cách thô, phép chuẩn hóa, trọng số, đóng góp, điểm cuối, video_id, frame_index, actual PTS và đường dẫn phát. Thêm xuất histogram HSV/LBP và ảnh crop/khung dùng tính điểm. Có công cụ kiểm tra/tái tính điểm từ trace. Không gọi score là xác suất hoặc độ chính xác.

Thử ảnh bên ngoài, ảnh cắt từ video, dọc, thiếu sáng, hai lớp gần nhau, ngoài chủ đề và ảnh hỏng. Test index cũ/thiếu vector/model khác/source đổi; lỗi phải rõ, không trả kết quả giả. Nếu cần tối ưu hash mỗi query, dùng phiên index đã xác minh có quy tắc invalidate và báo cáo chi phí kiểm tra nguồn riêng.

Để minh họa vai trò Flow đã cam kết ở báo cáo, triển khai video–video trong module/CLI riêng nếu phạm vi ND3 yêu cầu sử dụng; dùng cả4descriptor và policy/version riêng. Đây là phần bổ sung; tuyệt đối không thay ảnh→video của đề D23. Nếu để lại, ghi chính xác phạm vi chưa triển khai.

Đầu ra: truy vấn thật+trace+ảnh minh họa và docs/phases/08_KET_QUA.md. Nghiệm thu: mỗi điểm có thể đối chiếu, hình hiển thị khớp evidence,5video phát được và mọi kiểm tra provenance giữ hiệu lực. Chưa dùng test set để chọn trọng số.
```
