# Tìm video bằng ảnh trên MySQL

Chạy PowerShell trong `D:/video csdldpt/he_thong_nhom12`. Môi trường, checkpoint và dữ liệu MySQL đã có trên máy hiện tại.

## Một ảnh

```powershell
./scripts/Run.ps1 mysql doctor
./scripts/Run.ps1 query --image 'D:/anh/anh-moi.jpg'
```

Nhận đường dẫn HTML kết quả. Mở file đó để xem5video, ảnh truy vấn/crop, khung dùng tính điểm và timestamp. Liên kết trace chứa vector và phép tính trung gian. Điểm là thứ tự tương đồng, không phải xác suất đúng; ảnh ngoài chủ đề vẫn trả5video trong kho.

Lượt CLI mới cần nạp CLIP và xác minh dữ liệu, có thể mất hàng chục giây. Không phải mọi lượt CLI đơn lẻ đều đạt thời gian warm của phiên đã nạp.

## Nhiều ảnh dùng chung một phiên

```powershell
./scripts/Run.ps1 query-batch --images 'D:/anh/a.jpg' 'D:/anh/b.png' 'D:/anh/c.webp'
```

Chỉ khởi tạo model/index ở ảnh hợp lệ đầu tiên; mỗi ảnh có thư mục kết quả riêng. Số đo thực tế11lượt đã có phiên: trung vị1.40giây và tối đa1.60giây trong một lần thử, xem [kết quả giai đoạn4](search_phases/04_KET_QUA.md).

Ảnh hỏng/không tồn tại được ghi lỗi theo từng ảnh. Nếu có lỗi, batch trả mã thoát2. Khi index/source/model đổi làm phiên không còn hợp lệ, mở phiên mới sau khi kiểm tra/xây lại dữ liệu cần thiết.

Trong phiên Windows, các file nguồn/model được giữ mở ở chế độ chỉ chia sẻ đọc để bảo toàn bản đã xác minh. Phiên kết thúc sẽ thả handle. Việc cập nhật dữ liệu MySQL trong lúc tìm kiếm sẽ làm guard yêu cầu mở lại phiên, tránh dùng cache cũ.

## Tái tính điểm kết quả

```powershell
./scripts/Run.ps1 replay --trace 'var/query-ID/trace.json'
```

Replay trace `nd4-v2` dùng vector được lưu cùng kết quả, không cần GPU hoặc kết nối MySQL. Lệnh kiểm tra checksum artifact, khoảng cách, điểm chuẩn hóa, đóng góp trọng số và điểm cuối của cả5hit. Nó kiểm tra phép tính của kết quả đã lưu; không phải đánh giá relevance hoặc chứng minh lại top5 trên toàn bộ kho.

## File kết quả

| File | Nội dung |
| --- | --- |
| `demo.html` | Năm kết quả và dữ liệu trung gian |
| `source-image.bin` | Byte ảnh đầu vào để đối chiếu SHA256 |
| `input.png`, `preprocessed.png` | Ảnh đã xử lý EXIF/RGB và ảnh sau crop/resize |
| `clip-input-preview.png` | Preview letterbox224 trước chuẩn hóa tensor CLIP |
| `histograms.svg` | Histogram HSV128/LBP10, có giá trị vector gốc trong trace |
| `query-features.npz` | Vector HSV/LBP/CLIP truy vấn |
| `trace.json` | Policy, model/spec/code/index/revision, crop, vector khung khớp, khoảng cách, PTS và thời gian |

Ảnh/video/keyframe vẫn là file cục bộ; MySQL quản lý metadata, vector và checksum. Thẻ phát video trong HTML có thể bị hạn chế theo trình duyệt. Giai đoạn5 sẽ cung cấp giao diện và media server để kiểm tra phát/tua ổn định.

Quản trị dữ liệu: [MYSQL.md](MYSQL.md). Cơ sở môn học: [THIET_KE_THEO_SLIDE.md](THIET_KE_THEO_SLIDE.md).
