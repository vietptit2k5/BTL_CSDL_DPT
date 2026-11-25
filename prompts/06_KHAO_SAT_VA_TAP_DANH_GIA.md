# Giai đoạn06 Khảo sát ND1 và chuẩn bị đánh giá

```text
Thực hiện giai đoạn06 tại D:/video csdldpt/he_thong_nhom12. Đọc prompts/BOI_CANH_CHUNG.md, kết quả04–05 và mục1.4/Bảng2.2 báo cáo.

Bổ sung job khảo sát tái lập ND1: D1 màu, độ sáng/bão hòa, D2 Canny, D5 mean absolute grayscale difference theo định nghĩa báo cáo, không thay D5 bằng Flow. Mẫu quan sát120video/20mỗi lớp phải có danh sách ID, seed và nhãn quan sát thực. Giữ mẫu cũ nếu còn hợp lệ; dữ liệu đổi thì ghi thay đổi. Xuất số liệu/biểu đồ theo lớp và trong lớp, đối chiếu các con số cũ thay vì chép lại.

Trích lại bảy cặp C1–C7 đúng ID trong Bảng2.2, xuất giá trị khoảng cách và hình minh họa để hỗ trợ nhận xét ND2. Nếu ID đã đổi nội dung, nêu rõ và cập nhật diễn giải dựa trên video hiện tại; không giữ kết luận cũ trái bằng chứng.

Thiết kế manifest truy vấn có query_id, image_path, sha256, nguồn ảnh, source_video_id nếu có, nhóm khó và split validation/test. Có ảnh từ video biến đổi để kiểm tra tìm lại nguồn, đồng thời có ảnh bên ngoài và ảnh ngoài chủ đề. Tách nguồn/cùng cảnh qua các split để tránh rò rỉ. Đặt quy tắc relevance và người gán nhãn độc lập với output hệ thống; không tự gán relevant từ top5 của thuật toán. Tập test phải được giữ riêng trước chọn trọng số.

Đầu ra: job khảo sát, số liệu và danh sách mẫu, bảng bảy cặp, manifest/judgments/schema và quy tắc split, docs/phases/06_KET_QUA.md. Nhãn còn thiếu giữ pending.

Nghiệm thu: ID/snapshot rõ ràng; số liệu ND1 tái tính được; phân biệt bài toán cùng lớp, cùng cảnh và liên quan thị giác; có validation/test đủ đầu vào cho đánh giá sau. Không công bố chỉ số chất lượng khi chưa có judgments thật.
```
