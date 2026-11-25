# Giai đoạn04 Kiểm tra và chốt dữ liệu

```text
Thực hiện giai đoạn04 tại D:/video csdldpt/he_thong_nhom12. Đọc prompts/BOI_CANH_CHUNG.md và kết quả01–03.

Chạy kiểm kê SHA256/metadata cho toàn bộ video sáu thư mục. Đếm lại từ dữ liệu hiện tại;561 chỉ là snapshot cũ. Kiểm tra ≥500, ID duy nhất, MP4/H.264, thời lượng theo quy ước báo cáo và khả năng giải mã; ghi các lỗi hoặc ngoại lệ bằng ID. Kiểm tra duplicate byte bằng SHA và tạo danh sách nghi trùng cảnh/chuyển cảnh để review. Không coi một ngưỡng tự động là bằng chứng tuyệt đối.

Tạo quy trình review có contact sheet và liên kết video, gắn video_id+SHA. Giữ nguyên những review hợp lệ cùng SHA đã có; SHA đổi thì invalidate review tương ứng. Xác nhận single_scene/not_duplicate/no_large_logo chỉ khi có bằng chứng xem/đánh giá; lưu reviewer, thời điểm, phương pháp, notes. Chưa biết thì null/pending. Không điền true hàng loạt để vượt điều kiện build.

Giải quyết rõ staging so với file nguồn: index phiên bản nào phải có đường dẫn/hash phiên bản đó, không trộn file mới với cache cũ. Không tự thay/cắt/xóa video nguồn. Với lỗi cần thay dữ liệu, xuất danh sách và phương án cụ thể; tiếp tục các phần độc lập. Thu thập URL/nguồn/giấy phép khi có bằng chứng, trường không biết để trống rõ ràng.

Đầu ra: manifest có hash+metadata, báo cáo chất lượng, review có căn cứ, danh sách pending, snapshot đã chốt hoặc lý do chưa chốt, docs/phases/04_KET_QUA.md.

Nghiệm thu: đủ dữ liệu hợp lệ và review đúng snapshot để build production. Nếu còn review cần con người, giữ trạng thái Chờ đầu vào cụ thể; không làm giả trạng thái Đạt. Giai đoạn05 có thể thử trên tập con đã review nếu ghi rõ chưa đủ điều kiện full build.
```
