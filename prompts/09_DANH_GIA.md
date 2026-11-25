# Giai đoạn09 Đánh giá và chốt cấu hình

```text
Thực hiện giai đoạn09 tại D:/video csdldpt/he_thong_nhom12. Đọc prompts/BOI_CANH_CHUNG.md, manifest/judgments giai đoạn06 và index/query thật giai đoạn07–08. Xác minh mọi query_id/path/hash/split khớp; thiếu nhãn thì không bịa chỉ số.

Hoàn thiện runner đánh giá tái lập. Trên validation, so sánh HSV-only, LBP-only, CLIP-only, tổ hợp CLIP+HSV, CLIP+HSV+LBP và một tập trọng số nhỏ có lý do. Tất cả vẫn trích đủ đặc trưng. Nếu so sánh aggregation/CDF, tách calibration/validation/test và lưu policy; không hiệu chỉnh theo test.

Chốt objective trước chọn cấu hình: precision@5/relevance làm chỉ tiêu chính, các thuộc tính sáng/màu và nhận lại nguồn là chỉ tiêu phụ có định nghĩa. Không nói tổ hợp tốt hơn mọi mặt nếu CLIP-only có chỉ tiêu chính cao hơn. Khóa cấu hình rồi chạy test cuối; nếu sửa theo kết quả test phải gọi đó là phát triển tiếp và cần tập test độc lập mới.

Xuất precision@5, recall@5 và AP@5 theo query và macro; recall chỉ có ý nghĩa khi judgments bao phủ tập relevant theo phạm vi đã xác định. Tách query không có relevant, cùng nguồn/cùng lớp và ảnh ngoài dataset. Đánh giá theo nhóm khó và phân tích lỗi thật. Đo latency cold/warm, decode/preprocess/encode/search và kiểm tra hash riêng, ghi phần cứng,N,K,device và phiên bản.

Đầu ra: runner, raw rankings, judgments version, bảng/biểu đồ, policy đã chốt, docs/phases/09_KET_QUA.md. Không nhập các accuracy93% cũ làm kết quả hiện tại.

Nghiệm thu: người khác chạy lại được cùng query IDs, không rò rỉ split, kết quả báo cáo khớp raw data, cấu hình cuối có quyết định rõ và không che kết quả kém. Không chạy lại full extraction nếu chỉ thay trọng số.
```
