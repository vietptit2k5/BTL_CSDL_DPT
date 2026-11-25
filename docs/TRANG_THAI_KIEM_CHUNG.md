# Trạng thái kiểm chứng ngày 18 tháng 11 năm 2026

> Đây là bản ghi lịch sử ngày 18/11. Trạng thái mới ngày 25/11: đã có UI/media server, ND3 B0–B8, xuất 5 MP4/ZIP, 56 test qua, MySQL tài khoản riêng, view metadata và incremental. Xem [tiến độ hiện tại](TIEN_DO_ND3_ND4.md) và [hướng dẫn vận hành](HOAN_THIEN_VAN_HANH.md). Các mục “chưa có UI” bên dưới chỉ mô tả mốc cũ; đánh giá độc lập ND4 và xác nhận chất lượng nội dung vẫn chờ.

## Đã kiểm chứng

- **Giai đoạn 1 đạt:** môi trường Python 3.11.9 riêng, dependencies độc lập, `pip check` qua; checkpoint CLIP ViT-B/32 và FFmpeg/FFprobe local hoạt động offline. CLIP đã encode ảnh thật trên NVIDIA RTX 3050 Laptop GPU, vector 512 chiều float32, norm L2 gần 1.
- **Giai đoạn 2 đạt:** 12 video thật, hai video mỗi lớp; 192 khung, 576 vector cấp khung và 12 vector Flow. Mọi vector finite, đúng chiều và chuẩn hóa theo báo cáo. Đã xem ảnh overview trước/sau crop và letterbox.
- **Giai đoạn 3 đạt:** CSDL SQLite mới technical ready, đủ 561 video / 8.976 khung / 26.928 vector cấp khung / 561 motion. Full audit, FK và integrity check qua; toàn bộ vector DB khớp NPZ chính xác và mọi PNG qua kiểm tra checksum/CRC/kích thước.
- Đã dừng thật sau 3 video rồi resume, tái sử dụng đúng 3 video. Ba video đại diện được trích lại trực tiếp, mọi descriptor khớp DB với sai khác bằng 0.
- **33kiểm thử qua**, gồm8test adapter thật,3test MySQL thật, vector hóa/tie-break, khóa đọc nguồn Windows, lỗi ảnh/EXIF, replay và invalidation. Test MySQL dùng fixture rõ ràng và database riêng, tách khỏi bộ561video thật.
- **MySQL đã vận hành:** database `d23_nhom12` trên `127.0.0.1:3306`; đủ 561 video, 8976 keyframe, 26928 vector khung, 561 motion. Mọi cột/JSON/vector khớp nguồn SQLite; bản nguồn giữ nguyên SHA256. Truy vấn GPU thật qua MySQL trả năm video riêng biệt, điểm giảm dần và top5 khớp phép tính trên SQLite.
- **Giai đoạn4 đạt:**12ca ảnh thật (6ảnh nguồn,4ảnh độc lập ngoài chủ đề, dọc/tối) và2lỗi đầu vào được kiểm tra. Bốn ca so scalar trên mọi8976khung khớp toàn bộ trường của năm hit. Truy vấn đã có phiên trung vị1.40giây; lượt đầu38.45giây gồm khởi tạo. Trace v2 có crop/histogram/vector khung khớp và tái tính điểm độc lập.
- **Thiết kế theo môn học:** đã đọc nội dung12bài/386trang, kiểm tra sơ đồ quan trọng;40nhóm mapping từ kiến thức/trang PDF đến module và giới hạn triển khai. PDF nguồn giữ nguyên checksum.
- Mọi module Python đã kiểm tra cú pháp bằng compileall.
- `plan` đã chạy trên 561 MP4 thật; hash snapshot: `f0af1a341f7b7a44a97235686d9446b41329ea133002fe551776813177e7cdf5`.
- Số lượng full build đã được xác nhận thực tế. Xem `var/current_mysql_index.json` cho backend hiện hành và `var/current_index.json` cho bản SQLite đối chiếu.
- Chưa sửa video, tài liệu nộp thầy, CSDL cũ hoặc dự án `D:/csdldpt_system`.

## Bằng chứng chạy thật

- [Kết quả giai đoạn 1](search_phases/01_KET_QUA.md) và [giai đoạn 2](search_phases/02_KET_QUA.md).
- [Environment validation](../var/search_phases/01_environment/validation.json), [log test](../var/search_phases/01_environment/tests.log), [pilot validation](../var/search_phases/02_features/validation.json).
- [Ảnh 12 mẫu trước/sau](../var/search_phases/02_features/overview.jpg) và [hướng dẫn môi trường](HUONG_DAN_MOI_TRUONG.md).
- [Kết quả giai đoạn 3](search_phases/03_KET_QUA.md), [full audit](../var/search_phases/03_database/audit.json), [deep vector/PNG check](../var/search_phases/03_database/deep_validation.json) và [direct checks](../var/search_phases/03_database/direct_checks.json).
- [Kết quả chuyển MySQL](search_phases/03_MYSQL.md), [đối chiếu toàn bộ dữ liệu](../var/search_phases/03_mysql/migration.json), [truy vấn GPU thật](../var/search_phases/03_mysql/query_validation.json) và [25 test](../var/search_phases/03_mysql/tests.log).
- [Kết quả giai đoạn4](search_phases/04_KET_QUA.md), [12ca thật và timings](../var/search_phases/04_query/validation.json), [33test](../var/search_phases/04_query/tests.log), [bảo toàn dữ liệu](../var/search_phases/04_query/preservation.json).
- [Thiết kế theo slide](THIET_KE_THEO_SLIDE.md), [mapping40nhóm](course_mapping.json), [kiểm tra nguồn và trang](../var/course_slides/mapping_validation.json).

Nhận định trước đây về môi trường thiếu thư viện chỉ phản ánh runtime thử lúc tạo skeleton. Python cũ còn hoạt động khi có quyền truy cập phù hợp; đã sao chép dependencies vào môi trường riêng và kiểm chứng import thật. Không còn dùng tình trạng thiếu thư viện ban đầu làm trạng thái hiện tại.

## Phạm vi chưa hoàn thành

Chưa có UI chọn ảnh/media server và kiểm thử phát/tua trong trình duyệt, chưa đánh giá accuracy độc lập với relevance có nhãn. Review scene/trùng/logo vẫn pending cho561video; technical ready không đồng nghĩa đã review nội dung toàn diện. Video VFR/rotation đã được thử bằng fixture kỹ thuật, không tự khẳng định chúng có mặt trong dataset.

## Đầu việc tiếp theo

Tiếp theo là giai đoạn5 trong [chuỗi sáu giai đoạn](../prompts/UU_TIEN_HE_THONG_TIM_KIEM.md): UI dùng lại `SearchSession`, phục vụ media cục bộ và kiểm tra phát/tua. Bố trí theo [thiết kế môn học](THIET_KE_THEO_SLIDE.md). Không full extraction lại chỉ vì thay trọng số hay giao diện; khi đổi mã trích cần đối chiếu compatibility với bản source đã lưu.
