# Giai đoạn 3 đã hoàn thành

**Cập nhật:** đã chuyển chính xác toàn bộ dữ liệu dưới đây sang MySQL theo yêu cầu của nhóm. MySQL là backend truy vấn mặc định; SQLite được giữ làm bản chứng nhận/đối chiếu. Xem [kết quả MySQL](03_MYSQL.md).

Ngày kiểm chứng: 18/11/2026. Đã xây CSDL SQLite mới từ video và đặc trưng thật, không nhập lại DB540 video cũ.

## Chỉ mục hiện tại

`var/build-40f06039320a4b90a82eb182792670b0/index.sqlite`

| Thành phần | Số lượng thực |
| --- | ---: |
| Video | 561 |
| Khung đại diện | 8976 |
| Vector HSV/LBP/CLIP cấp khung | 26928 |
| Vector chuyển động | 561 |
| Manifest artifact theo video | 561 |

| Lớp | Số video |
| --- | ---: |
| FLO | 120 |
| FOR | 85 |
| MOU | 85 |
| RIV | 87 |
| SEA | 86 |
| WAT | 98 |

Metadata preflight đọc toàn bộ danh sách nguồn. Decoder trích các khung cần thiết theo PTS thật; không dùng việc đó để khẳng định đã kiểm tra nội dung mọi khung hoặc video luôn chỉ có một scene. SHA nguồn được xác minh trước/sau trích và khi hoàn tất toàn bộ generation.

## Tính đầy đủ và toàn vẹn

- SQLite integrity check: **ok**; không có lỗi khóa ngoại.
- Mỗi video đủ16 khung; mỗi khung đủ HSV128,LBP10,CLIP512 float32. Mỗi video đủ Flow24. Mọi vector finite và đúng chuẩn hóa theo đặc tả ND1–2.
- Kiểm tra toàn bộ ảnh/NPZ bằng manifest SHA256; kiểm tra ID, timestamp tăng, metadata nguồn và source snapshot.
- Đối chiếu toàn bộ 26928 BLOB vector khung và 561 BLOB motion với NPZ: bằng nhau chính xác. Đã kiểm tra 8976 PNG về checksum, CRC, RGB và kích thước crop.
- Snapshot hash: `f0af1a341f7b7a44a97235686d9446b41329ea133002fe551776813177e7cdf5`.
- Spec hash: `a3f2de2bcfc6d4aa7dea0595cf9a832648b0a3e1b238df293e6b3ea3bcbd84c5`.
- Model identity: `1d4d7979767c631678a97a6117dce125efcd249add4913614bc3b74f87e1e1fc`.
- Implementation hash: `536b1f649a1b1f678d9c001cfcebdd3a92730d9b5f310d27aa28ebf202a9aef3`.

## Resume đã được kiểm chứng

- Bộ22test đã qua, gồm các kiểm tra adapter thật và lỗi/rollback/resume. [Log kiểm thử giai đoạn3](../../var/search_phases/03_tests.log).
- Đã dừng có kiểm soát sau3 video thật; file partial vẫn ở trạng thái building, không phải ready.
- Sau tiếp tục, tái sử dụng 3 video đã hoàn thành và xác minh artifact; không trích lại những video đó.
- Các test mô phỏng cũng kiểm tra lỗi giữa transaction, thay nội dung nguồn dù giữ số byte và artifact hỏng. Resume từ chối nguồn/spec/model/code/environment khác; artifact hỏng được trích lại thay vì bù vector0.
- File chỉ được công bố thành `index.sqlite` khi tất cả dữ liệu đạt kiểm tra. Các generation khác giữ nguyên, không ghi đè.

## Đối chiếu vector bằng trích trực tiếp

Đã mở lại nguồn, giải mã và trích độc lập rồi so các vector trực tiếp với BLOB trong DB, tolerance1e-5. Đây là đối chiếu dữ liệu thật, không phải fixture giả lập.

| Video | Kết quả | Sai khác tuyệt đối lớn nhất |
| --- | --- | ---: |
| SEA005 | passed | 0 |
| MOU023 | passed | 0 |
| FLO114 | passed | 0 |

## Trạng thái kỹ thuật và review nội dung

Index **technical ready**. Dataset quality status: **pending**. Số review theo trạng thái: `{"pending": 561}`.

Trạng thái pending của scene/trùng/logo được lưu rõ trong từng video; không tự điền true để vượt kiểm tra. Chưa công bố dữ liệu đã được review toàn diện hoặc hệ thống đã có accuracy đánh giá độc lập.

## Tối ưu đã thực hiện

Khung đại diện và cặp motion dùng một lượt decode, chỉ chuyển màu/resize các khung đã chọn. Test VFR so PTS và pixel giữa yêu cầu hỗn hợp với các yêu cầu riêng đều qua. Số khung, timestamp đích, crop, descriptor và model theo báo cáo vẫn giữ nguyên.

Session tiếp tục ghi nhận 1994.8s (gồm các kiểm tra trong session). Tổng lệnh orchestration kể cả pause/resume/audit/spotcheck ghi nhận 2090.8s. Không dùng những số này làm latency truy vấn.

## Sử dụng

```powershell
cd 'D:/video csdldpt/he_thong_nhom12'
$index = (Get-Content -LiteralPath 'var/current_index.json' -Raw | ConvertFrom-Json).index
./scripts/Run.ps1 verify --index $index
```

Tạo generation mới: `./scripts/Run.ps1 build`. Tiếp tục partial: `./scripts/Run.ps1 build --resume 'var/build-ID'`. `--reviews` là đầu vào tùy chọn gắn SHA, không làm giả phán đoán thủ công. `--stop-after N` phục vụ kiểm tra phục hồi và không tạo chỉ mục ready khi còn thiếu video.

## Bằng chứng

- [Full audit](../../var/search_phases/03_database/audit.json)
- [Kết quả giai đoạn3](../../var/search_phases/03_database/validation.json)
- [Direct feature checks](../../var/search_phases/03_database/direct_checks.json)
- [Full BLOB/NPZ/PNG validation](../../var/search_phases/03_database/deep_validation.json)
- [Execution log](../../var/search_phases/03_database/execution.log)
- [Build summary](../../var/build-40f06039320a4b90a82eb182792670b0/summary.json)
- [Manifest metadata và nguồn](../../var/build-40f06039320a4b90a82eb182792670b0/manifest.json)
- [Sự kiện/resume](../../var/build-40f06039320a4b90a82eb182792670b0/events.jsonl)

Giai đoạn4 tiếp tục từ index này để hoàn thiện tìm kiếm ảnh và trace. Chưa đánh dấu giao diện, truy vấn đầu cuối hoặc báo cáo học thuật là đã hoàn thành chỉ vì CSDL đã sẵn sàng.
