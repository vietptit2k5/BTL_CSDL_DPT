# Giai đoạn 3: đã chuyển sang MySQL

Kiểm chứng ngày 18/11/2026 theo yêu cầu quản lý dữ liệu bằng MySQL của nhóm D23 nhóm12. Database vận hành: **`d23_nhom12`**, MySQL9.5.0 tại **`127.0.0.1:3306`**. Driver thực tế `mysql-connector-python==9.7.0`. Cấu hình mặc định đã chọn MySQL.

## Dữ liệu thật đã nhập

| Thành phần | Số lượng |
| --- | ---: |
| Video | 561 |
| Keyframe | 8976 |
| Vector HSV128 | 8976 |
| Vector LBP10 | 8976 |
| Vector CLIP512 | 8976 |
| Vector motion24 | 561 |
| Manifest ảnh/NPZ | 561 |

Phân bố lớp giữ nguyên: SEA86, WAT98, FOR85, MOU85, RIV87, FLO120. Cả bốn loại đặc trưng trong báo cáo phần2 đều có trong MySQL. Bộ dữ liệu đáp ứng số lượng tối thiểu500 video; kiểm duyệt scene/trùng/logo vẫn pending.

Generation: `7cf27d6f707c0bf2276cdf84e1e270b8`, trạng thái `ready`. Pointer: `var/current_mysql_index.json`.

Nguồn là bản trích mới của nhóm12 tại `var/build-40f06039320a4b90a82eb182792670b0/index.sqlite`, không dùng lại DB540video của dự án cũ. SHA256 nguồn vẫn là `7cf27d6f707c0bf2276cdf84e1e270b85cd8ff9e308d96bd8fc2f8a667c9842a`. Chuyển dữ liệu không trích CLIP/Flow lại và không sửa nguồn SQLite.

## Kiểm chứng

- Audit nguồn kiểm tra snapshot video, spec, model, môi trường, vector và artifact. Các module/hàm trích được đối chiếu với source archive đã chứng nhận; hash trong DB nguồn giữ nguyên.
- Cả sáu bảng dữ liệu được đối chiếu toàn bộ cột và từng hàng. JSON so theo giá trị; toàn bộ26928 BLOB vector khung và561 BLOB motion giống từng byte.
- Migration chỉ chuyển generation sang `ready` sau khi transaction nhập dữ liệu qua kiểm tra; nhập lại cùng nguồn không nhân bản dữ liệu.
- **25 kiểm thử đều qua**, gồm8 kiểm thử adapter media thật,2 kiểm thử MySQL thật và kiểm chứng archive. Test MySQL dùng database/instance kiểm thử riêng cổng3307 với media giả lập, tách khỏi database vận hành3306 và bộ561video thật.
- MySQL thật đã kiểm tra ràng buộc kích thước BLOB, khóa ngoại, rollback khi đối chiếu thất bại và retry thành công.
- `pip check` qua với45 distribution phụ thuộc được khóa trong `requirements.lock.txt`.

## Truy vấn ảnh thật trên GPU qua MySQL

Ảnh smoke là keyframe0 củaSEA005, lưu tại `var/search_phases/03_mysql/query-input.png`. Đây là phép thử chức năng bằng ảnh trong bộ dữ liệu, không phải đánh giá độc lập về độ chính xác.

Luồng truy vấn đã chạy CLIP thật trên GPU và bị chặn truy cập SQLite bằng guard kiểm thử. Dữ liệu xếp hạng được đọc từ MySQL. Sau truy vấn, phép tính tham chiếu trên SQLite cho kết quả trùng toàn bộ trường của cả năm hit.

| Hạng | Video | Điểm |
| --- | --- | ---: |
| 1 | SEA005 | 0.995636799 |
| 2 | SEA061 | 0.906884051 |
| 3 | SEA040 | 0.903785070 |
| 4 | SEA019 | 0.884898386 |
| 5 | SEA010 | 0.884811436 |

Năm video riêng biệt, điểm giảm dần. Mỗi hit có khung khớp, timestamp, khoảng cách HSV/LBP/CLIP và đóng góp vào điểm tổng. Luồng smoke đầu mất **98.99 giây**, bao gồm kiểm tra nguồn/checkpoint, nạp mô hình và xếp hạng; chưa tối ưu độ trễ. Trọng số vẫn là cấu hình thử CLIP0.9/HSV0.1/LBP0, không thay cho đánh giá thực nghiệm.

## Bằng chứng và sử dụng

- [Đối chiếu dữ liệu](../../var/search_phases/03_mysql/migration.json)
- [Kiểm tra MySQL sau commit và toàn bộ artifact](../../var/search_phases/03_mysql/verification.json)
- [Kiểm tra11 câu SQL quản lý](../../var/search_phases/03_mysql/management_sql_validation.json)
- [Kết quả smoke GPU](../../var/search_phases/03_mysql/query_validation.json)
- [HTML smoke](../../var/query-7c6ee95c9d174331bd48db39b8aea5c2/demo.html)
- [Log25 test](../../var/search_phases/03_mysql/tests.log)
- [Hướng dẫn MySQL và Workbench](../MYSQL.md)
- [SQL xem/quản lý dữ liệu](../../sql/mysql_management.sql)

```powershell
./scripts/Run.ps1 mysql doctor
./scripts/Run.ps1 mysql list
./scripts/Run.ps1 mysql verify
./scripts/Run.ps1 query --image var/search_phases/03_mysql/query-input.png
```

Giai đoạn4 cần tiếp tục với ảnh ngoài bộ dữ liệu, xử lý lỗi đầu vào và tối ưu truy vấn. Giao diện chọn ảnh, đánh giá độc lập và nội dung báo cáo3–4 chưa được đánh dấu hoàn thành từ phép smoke này.
