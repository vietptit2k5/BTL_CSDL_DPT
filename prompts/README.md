# Chuỗi prompt hoàn thành hệ thống nhóm 12

**Ưu tiên hiện tại:** dùng [chuỗi sáu giai đoạn hoàn thiện hệ thống tìm kiếm trước](UU_TIEN_HE_THONG_TIM_KIEM.md). Chuỗi12giai đoạn bên dưới giữ làm lộ trình học phần đầy đủ, gồm khảo sát và báo cáo sau khi bản tìm kiếm đã chạy được.

Ngày 18/11/2026: giai đoạn 1–3 của chuỗi sáu giai đoạn đã đạt bằng chạy thật; xem [tiến độ hiện tại](TIEN_DO.md). Mốc tiếp theo là giai đoạn 4 hoàn thiện tìm kiếm ảnh trên CSDL mới.

Được soạn ngày 16/11/2026 từ trạng thái bộ khung hiện có. Đây là bộ hướng dẫn để thực hiện tiếp; việc tạo các prompt không có nghĩa các giai đoạn đã chạy.

Mở một file giai đoạn bên dưới, sao chép toàn bộ khối `text` vào Codex đang mở thư mục `D:/video csdldpt`. Có thể tiếp tục cùng hội thoại hoặc mở hội thoại mới. Mỗi prompt yêu cầu đọc `BOI_CANH_CHUNG.md` nên không phụ thuộc vào trí nhớ hội thoại cũ.

| Thứ tự | Prompt | Kết quả phải có |
| --- | --- | --- |
| 01 | [Chốt hợp đồng và rà soát](01_HOP_DONG.md) | Baseline, mapping, danh sách sai lệch cần sửa |
| 02 | [Môi trường chạy thật](02_MOI_TRUONG.md) | Python, FFprobe, thư viện, checkpoint CLIP hoạt động |
| 03 | [Giải mã và tiền xử lý](03_MEDIA_TIEN_XU_LY.md) | PTS, video dọc/VFR, crop đúng; bằng chứng ảnh thật |
| 04 | [Kiểm tra và chốt dữ liệu](04_CHOT_DU_LIEU.md) | Manifest SHA, review có bằng chứng, danh sách nguồn đã chốt |
| 05 | [Trích đặc trưng thử nghiệm](05_DAC_TRUNG.md) | HSV/LBP/CLIP/Flow thật, đúng đặc tả trên mẫu đại diện |
| 06 | [Khảo sát và dữ liệu đánh giá](06_KHAO_SAT_VA_TAP_DANH_GIA.md) | Số liệu ND1, bảy cặp mẫu, manifest validation/test có ID |
| 07 | [Xây CSDL đầy đủ](07_CSDL.md) | Index mới đủ dữ liệu, atomic build, kiểm tra provenance |
| 08 | [Hoàn thiện tìm kiếm và trace](08_TIM_KIEM.md) | Ảnh→5 video và minh họa video–video riêng nếu thực hiện |
| 09 | [Đánh giá và chốt cấu hình](09_DANH_GIA.md) | So sánh cấu hình, test độc lập, độ trễ, quyết định có số liệu |
| 10 | [Giao diện demo cục bộ](10_DEMO.md) | Nhập ảnh, phát5 video, xem trung gian; thử bằng trình duyệt |
| 11 | [Báo cáo nội dung3–4](11_BAO_CAO.md) | Báo cáo dựa trên hệ thống và kết quả thật |
| 12 | [Đóng gói và nghiệm thu](12_NGHIEM_THU.md) | Bản chạy tái lập, hướng dẫn, ma trận yêu cầu và demo cá nhân |

Đi theo thứ tự. Giai đoạn sau đọc kết quả giai đoạn trước; nếu tiêu chí đầu vào chưa đạt thì sửa nguyên nhân trong phạm vi liên quan, không tuyên bố hoàn thành thay cho bằng chứng. Giai đoạn04 và06 có phần đánh giá thủ công; nếu thiếu nhãn, tiếp tục việc độc lập rồi ghi rõ phần chờ xác nhận. Không tự đánh dấu review hoặc tạo nhãn thay con người khi chưa có căn cứ.

Theo dõi ở [TIEN_DO.md](TIEN_DO.md). Sau mỗi giai đoạn, cập nhật tệp này và ghi kết quả tại `docs/phases/NN_KET_QUA.md`. Không chạy lại công việc nặng đã có kết quả hợp lệ cùng SHA/spec/model.

Nếu bị ngắt giữa một giai đoạn, dùng prompt tiếp tục ở cuối `BOI_CANH_CHUNG.md`. Không gộp cả12 giai đoạn vào một lần gửi: mỗi mốc cần kiểm tra kết quả thật trước khi chuyển tiếp.
