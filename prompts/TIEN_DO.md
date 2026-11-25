# Tiến độ thực hiện theo prompt

## Chuỗi sáu giai đoạn đang được ưu tiên

Cập nhật 25/11/2026, theo yêu cầu hoàn thành hệ thống trước và để riêng đánh giá độc lập ND4. Xem [hướng dẫn vận hành](../docs/HOAN_THIEN_VAN_HANH.md) và [tiến độ ND3–4](../docs/TIEN_DO_ND3_ND4.md).

| Giai đoạn | Trạng thái | Bằng chứng |
| --- | --- | --- |
| 1 Môi trường và CLIP thật | **Đạt** | [Kết quả](../docs/search_phases/01_KET_QUA.md): Python riêng, RTX 3050, CLIP512, pip check, 16 tests |
| 2 Xử lý và trích đặc trưng mẫu | **Đạt** | [Kết quả](../docs/search_phases/02_KET_QUA.md): 12 video thật, 192 khung, 576 vector khung, 12 motion |
| 3 CSDL đầy đủ | **Đạt, đã chuyển MySQL** | [Build](../docs/search_phases/03_KET_QUA.md), [MySQL](../docs/search_phases/03_MYSQL.md): 561 video, 8.976 khung, 26.928 vector khung, 561 motion; toàn bộ byte dữ liệu khớp |
| 4 Tìm kiếm ảnh end-to-end | **Đạt** | [Kết quả](../docs/search_phases/04_KET_QUA.md):12ca thật, ảnh độc lập/dọc/tối và lỗi input;33test; replay; bốn ca khớp scalar toàn index; warm trung vị1.40giây |
| 5 Giao diện sử dụng | **Đạt kiểm tra chức năng trên máy demo** | UI/media server có Range; tìm MySQL/GPU thật, 5 MP4 và ZIP; ba lượt HTTP đạt; Chrome Guest chọn ảnh/tìm/phát/tua trên hai video đạt |
| 6 Hoàn thiện bản chạy | Phần kỹ thuật đã triển khai; chờ rà soát nội dung và ND4 độc lập | 56 test qua; ND3 B0–B8 hoàn thành; tài khoản riêng, view SQL, incremental, gói nguồn và hướng dẫn tự chạy; không tự xác nhận 561 video |

Thiết kế xuyên các giai đoạn bám [toàn bộ12bài/386trang slide](../docs/THIET_KE_THEO_SLIDE.md), có40nhóm mapping trong `docs/course_mapping.json`. UI đã dùng MySQL và tái sử dụng `SearchSession`; không khởi tạo model/index lại mỗi ảnh. Các số 16/33 test trong bảng là bằng chứng lịch sử từng giai đoạn; log hồi quy mới có 56 test tại `var/completion/tests.log`.

## Chuỗi 12 giai đoạn tham khảo cũ

Các số thứ tự dưới đây thuộc lộ trình học phần cũ, không đồng nhất với chuỗi sáu giai đoạn hiện tại. Đây là checklist cũ chưa đối chiếu lại từng tiêu chí, không dùng các trạng thái bên dưới để mô tả tiến độ hiện tại. Dùng bảng sáu giai đoạn và tài liệu ND3–4 phía trên; không chạy lại công việc nặng chỉ để đánh dấu lại lộ trình cũ.

| Giai đoạn | Trạng thái | Kết quả / bằng chứng |
| --- | --- | --- |
| 01 Hợp đồng và baseline | Chưa bắt đầu | — |
| 02 Môi trường thật | Chưa bắt đầu | — |
| 03 Media và tiền xử lý | Chưa bắt đầu | — |
| 04 Chốt dữ liệu | Chưa bắt đầu | — |
| 05 Đặc trưng thật | Chưa bắt đầu | — |
| 06 Khảo sát và tập đánh giá | Chưa bắt đầu | — |
| 07 CSDL đầy đủ | Chưa bắt đầu | — |
| 08 Tìm kiếm và trace | Chưa bắt đầu | — |
| 09 Đánh giá và chốt cấu hình | Chưa bắt đầu | — |
| 10 Demo cục bộ | Chưa bắt đầu | — |
| 11 Báo cáo | Chưa bắt đầu | — |
| 12 Nghiệm thu | Chưa bắt đầu | — |

Dùng trạng thái: Chưa bắt đầu / Đang làm / Chờ đầu vào cụ thể / Đạt. Chỉ dùng Đạt khi tiêu chí và bằng chứng của prompt tương ứng đều đủ. Ghi rõ mục chờ; không biến sự thiếu nhãn hoặc thiếu môi trường thành kết quả đạt.
