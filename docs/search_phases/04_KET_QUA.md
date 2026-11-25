# Giai đoạn4: tìm kiếm ảnh trên MySQL đã hoàn thành

Kiểm chứng ngày18/11/2026. Đã triển khai service tìm kiếm có thể tái sử dụng phiên, CLI một/nhiều ảnh, bằng chứng trung gian và tái tính điểm. Giữ MySQL `d23_nhom12`, bộ561video,16khung/video và bốn descriptor của báo cáo ND2. Không trích lại video để thực hiện giai đoạn này.

## Mapping thiết kế theo môn học

Đã đọc đủ **12bài/386trang** trong `HeCSDL_DPT_slides`, kiểm tra trực quan các sơ đồ kiến trúc/metadata và công thức. [Thiết kế theo slide](../THIET_KE_THEO_SLIDE.md) tổ chức hệ thống theo các khối trong môn học; [course_mapping.json](../course_mapping.json) nối40nhóm kiến thức với trang PDF, module và phạm vi áp dụng. [Kiểm tra mapping](../../var/course_slides/mapping_validation.json) xác nhận đủ bài/trang, checksum PDF và các module được dẫn.

| Cơ sở môn học | Công việc giai đoạn4 |
| --- | --- |
| B1 tr.24–28: tạo CSDL và truy vấn riêng | Dùng index đã trích, `SearchSession` phục vụ ảnh mới |
| B4 tr.3–8,14–17; B6 tr.30–32: kiến trúc và metadata manager | Tách MySQL, file gốc, feature index, query và result preparation |
| B7 tr.18–20; B8 tr.4–6: NN/k-NN, cosine, xếp hạng | Quét ma trận mọi khung, gộp theo video, top5 riêng biệt; không tuyên bố có k-d/ANN |
| B11 tr.9–18,26: màu, histogram, kết cấu | Giữ HSV/LBP/CLIP đúng báo cáo; thêm histogram và khoảng cách thành phần |
| B12 tr.3–5,10–13: keyframe và motion | So ảnh với16khung/video, lưu PTS/khung bằng chứng; không tạo Flow cho ảnh |
| B1 tr.43–51: efficiency khác effectiveness | Đo latency/correctness; không công bố precision/recall khi chưa có relevance |

Âm thanh/ASR, văn bản/Boolean/inverted file, phân cụm/phản hồi, shot detection, shape/DCT và CSDL phân tán được ghi rõ là kiến thức tham khảo hoặc phần mở rộng chưa cài đặt. Không thêm descriptor trái hợp đồng ND2 để phủ slide.

## Code đã hoàn thiện

- `retrieval.ExactFrameIndex`: dùng ma trận float64 tính khoảng cách trên mọi8976khung; tính scalar lại các video gần ngưỡng top5 để giữ điểm, khung và tie-break như baseline. Không lọc theo lớp, không dùng ANN.
- `querying.SearchSession`: nạp/xác minh index và CLIP một lần cho nhiều ảnh, tuần tự hóa xử lý. Ảnh hỏng/không tồn tại báo lỗi trước khi nạp DB/model. Hỗ trợ EXIF, ảnh dọc, tối và ngoài chủ đề.
- `file_snapshot.FrozenFiles`: trên Windows, giữ handle chỉ cho chia sẻ đọc ở nguồn/model trong phiên đã xác minh. Đóng phiên thả handle; nền tảng khác kiểm tra SHA256 mỗi lượt.
- `storage_mysql.revisions`: thêm bảng marker và21trigger cho7bảng; DML commit làm invalidation, rollback không xuất bản thay đổi. Guard còn kiểm tra ready/context, số hàng, trigger, pointer, danh sách file và runtime trước/sau mỗi lượt.
- `query_evidence`: ảnh gốc/crop/preview, histogram SVG, NPZ, vector khung khớp, khoảng cách/điểm/đóng góp, metadata phiên, timings và SHA256 artifact. `replay` tái tính điểm độc lập không cần GPU/DB.
- CLI `query-batch` tái sử dụng phiên; `query` một ảnh giữ tương thích. Batch có lỗi trả mã2 và ghi trạng thái từng ảnh. HTML kết quả hiển thị năm video, khung/PTS, histogram và liên kết trace.

## Kiểm thử thực tế

**33 kiểm thử đều qua**, gồm8kiểm thử adapter thật,3kiểm thử MySQL thật trên instance kiểm thử riêng, kiểm tra khóa đọc Windows, đầu vào/EXIF, vector hóa/công thức/tie-break, replay và invalidation. Test dùng adapter giả lập vẫn được ghi rõ; không thay bằng chứng MySQL/GPU dưới đây.

Đã chạy12ca trên **MySQL vận hành3306 và RTX3050 Laptop GPU**:

| Nhóm | Số ca | Kết quả |
| --- | ---: | --- |
| Keyframe lấy từ SEA/WAT/FOR/MOU/RIV/FLO | 6 | Chạy đầu cuối; video nguồn đứng đầu cả6ca; không coi đây là đánh giá độc lập |
| Ảnh thật độc lập: astronaut/coffee/chelsea/rocket từ scikit-image | 4 | Trả5video thật, không lặp, điểm giảm dần; ảnh ngoài sáu lớp vẫn được xử lý |
| Ảnh dọc và ảnh tối từ ảnh coffee độc lập | 2 | Chạy đầu cuối, đủ vector/trace và đường dẫn kết quả hợp lệ |
| Ảnh hỏng và đường dẫn không tồn tại | 2lỗi đầu vào | Bị từ chối trước khi phiên nạp DB/model |

Mọi ca đều quét8976khung, có5ID khác nhau, replay qua và file video/keyframe tồn tại. Luồng online bị guard kiểm thử cấm mở SQLite. Bốn ca (ảnh nguồn, astronaut, dọc, tối) được so với scalar baseline trên **toàn bộ8976khung**; mọi trường của năm hit khớp chính xác.

Nguồn ảnh độc lập được ghi trong [validation.json](../../var/search_phases/04_query/validation.json), lấy từ [bộ mẫu chính thức scikit-image](https://scikit-image.org/docs/stable/api/skimage.data.html). Các ảnh này phục vụ thử chức năng; chưa có relevance judgments để đánh giá chất lượng ngữ nghĩa.

## Độ trễ đã đo

Một lượt nghiệm thu12ảnh, đo wall clock quanh hàm query; gồm ghi bằng chứng, replay nội bộ và HTML:

| Mốc | Thời gian |
| --- | ---: |
| Xác minh/nạp index | 11.63giây |
| Nạp CLIP | 22.82giây |
| Toàn bộ khởi tạo phiên | 35.67giây |
| Lượt truy vấn đầu, gồm khởi tạo | 38.45giây |
| Trung vị11lượt đã có phiên | **1.40giây/ảnh** |
| Lâu nhất trong11lượt đã có phiên | 1.60giây |
| So khớp ma trận ở4ca đối chiếu | 0.063–0.081giây |
| Scalar baseline cùng4ca | 5.73–6.22giây |

Số đo phụ thuộc tải máy/GPU/cache. Trước khi bổ sung đo toàn lượt, phép đo chỉ phần xử lý từng ghi khoảng0.64giây; dùng số đo wall clock1.40giây ở trên để báo cáo. Không so số warm với cold như cùng điều kiện. Mỗi lần gọi CLI riêng lại là một process mới và phải khởi tạo; lợi ích giữ model/index có trong `query-batch` hoặc service được UI sử dụng lâu dài ở giai đoạn5.

## Bảo toàn dữ liệu

[preservation.json](../../var/search_phases/04_query/preservation.json) xác nhận mọi cột/JSON/BLOB của sáu bảng dữ liệu MySQL vẫn khớp SQLite nguồn. SQLite vẫn có SHA256 `7cf27d6f707c0bf2276cdf84e1e270b85cd8ff9e308d96bd8fc2f8a667c9842a`. Excel, Word và PDF báo cáo gốc giữ nguyên. Không đổi descriptor, K, model, nguồn video hoặc tự gắn quality review=true.

Các thay đổi MySQL chỉ bổ sung tracking; dữ liệu đã trích không bị viết lại. Bản báo cáo phần1–2 được bảo toàn; thiết kế phần3–4 nằm trong tài liệu dự án mới.

## Cách dùng

```powershell
cd 'D:/video csdldpt/he_thong_nhom12'
./scripts/Run.ps1 query --image 'D:/anh/anh-moi.jpg'
./scripts/Run.ps1 query-batch --images 'D:/anh/a.jpg' 'D:/anh/b.png'
./scripts/Run.ps1 replay --trace 'var/query-ID/trace.json'
```

Lệnh in đường dẫn `demo.html`; cùng thư mục có `trace.json`, ảnh trung gian, `histograms.svg` và vector NPZ. Với batch, mỗi ảnh có output riêng và thông tin cold/warm trong trace. Xem [hướng dẫn sử dụng CLI](../HUONG_DAN_TIM_KIEM.md).

## Bằng chứng và phần tiếp theo

- [33test](../../var/search_phases/04_query/tests.log), [12ca thật](../../var/search_phases/04_query/validation.json), [execution log](../../var/search_phases/04_query/execution.log).
- [Contact sheet đầu vào](../../var/search_phases/04_query/visual/input-overview.jpg); đã kiểm tra trực quan histogram ảnh tối/dọc và sơ đồ slide quan trọng.
- [Toàn bộ thiết kế theo slide](../THIET_KE_THEO_SLIDE.md), [mapping có cấu trúc](../course_mapping.json).

Giai đoạn5 tiếp tục UI chọn ảnh/preview, dùng lại service, phục vụ media cục bộ có hỗ trợ tua/Range và kiểm thử trình duyệt thật theo B4. HTML hiện tại chưa thay thế nghiệm thu phát/tua trong trình duyệt. Review scene/trùng/logo, nguồn/giấy phép video, khảo sát120video và đánh giá relevance độc lập vẫn chưa hoàn thành; không tuyên bố accuracy học thuật từ33test hoặc12ca chức năng.
