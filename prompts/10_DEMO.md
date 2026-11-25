# Giai đoạn10 Giao diện demo cục bộ

```text
Thực hiện giai đoạn10 tại D:/video csdldpt/he_thong_nhom12. Đọc prompts/BOI_CANH_CHUNG.md, query/trace giai đoạn08 và cấu hình đã chốt giai đoạn09.

Hoàn thiện giao diện demo chạy cục bộ trên Windows để thầy có thể chọn ảnh và nhận5video thực. Ưu tiên cách triển khai nhỏ, dễ khởi chạy và tái dùng application service; không viết lại thuật toán trong UI hoặc yêu cầu cloud. HTML xuất từ CLI vẫn là đường dự phòng. Nếu dùng local server, phục vụ video và hỗ trợ tua/range phù hợp để tránh file:// bị trình duyệt chặn; chỉ mở trong máy, không publish.

Giao diện cần ảnh truy vấn/sau tiền xử lý, trạng thái đang chạy/lỗi,5kết quả theo hạng, video phát được, khung khớp và mốc thời gian, điểm cùng giải thích đây là tương đồng tương đối. Có vùng xem histogram/vector tóm tắt, điểm thành phần và tải trace. Không hiển thị toàn bộ512chiều làm màn hình chính; chi tiết đầy đủ nằm trong artifact.

Giới hạn thao tác UI vào ảnh đầu vào và artifacts hợp lệ, không cho URL/path tùy ý đọc file máy; giữ cấu hình/model/index ở phần quản trị phù hợp. Xử lý ảnh hỏng, sai dạng, thiếu model/index, kết quả chậm và yêu cầu trùng lặp. Không bỏ các guard nguồn để làm UI nhanh giả tạo.

Chạy thử bằng trình duyệt thật: chọn ảnh ngoài bộ, trả5video, phát/tua đến khung khớp, mở trung gian và trace, kiểm tra lỗi. Ghi screenshots và kịch bản đã thực hiện; không lấy ảnh mock làm bằng chứng chức năng chạy.

Đầu ra: mã UI, lệnh khởi chạy/dừng, bằng chứng trình duyệt, docs/phases/10_KET_QUA.md. Nghiệm thu: khởi chạy từ môi trường đã chốt, mọi nút quan trọng hoạt động với index thật và không phụ thuộc file:// mong manh. Không triển khai hosting bên ngoài.
```
