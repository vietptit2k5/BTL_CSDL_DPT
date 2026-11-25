# Giai đoạn 2 đã hoàn thành

Ngày kiểm chứng: 16/11/2026. Đã chạy trích đặc trưng thật trên **12video, hai video mỗi lớp**. Không sử dụng các vector/cache cũ làm kết quả mới và không thay video nguồn.

## Phạm vi và số lượng

- 192khung đại diện, 576vector cấp khung và 12vector chuyển động.
- Mỗi video có HSV16×128, LBP16×10, CLIP16×512 và Optical Flow24.
- HSV/LBP L1 và CLIP L2 đều được kiểm tra finite/norm. Motion có3khối8chiều, mỗi khối tổng1, không chia thêm3.
- Spec/model identity trùng giai đoạn1. Tổng thời gian pilot sau khi nạp encoder: 100.5s; chưa phải benchmark full build.

| Video | FPS | Kích thước ảnh đặc trưng | Diện tích viền bỏ | Thời gian/video giây |
| --- | ---: | --- | ---: | ---: |
| SEA005 | 30.000 | 455×256 | 25.0% | 8.9 |
| SEA016 | 30.000 | 455×256 | 25.0% | 5.2 |
| WAT001 | 29.970 | 455×256 | 0.0% | 9.6 |
| WAT008 | 60.000 | 455×256 | 0.0% | 15.7 |
| FOR018 | 25.000 | 455×256 | 0.0% | 8.7 |
| FOR015 | 29.970 | 256×454 | 0.0% | 4.4 |
| MOU046 | 30.000 | 455×256 | 0.0% | 11.2 |
| MOU023 | 59.940 | 256×454 | 0.0% | 6.4 |
| RIV001 | 30.000 | 455×256 | 0.0% | 8.1 |
| RIV003 | 30.000 | 455×256 | 0.0% | 6.8 |
| FLO097 | 30.000 | 455×256 | 0.0% | 9.9 |
| FLO114 | 25.000 | 256×454 | 0.0% | 4.6 |

Mẫu có video dọc, cảnh tối, cảnh tĩnh/động, FPS25/29.97/30/59.94/60 và viền đen Sea. Việc kiểm chứng VFR và rotation dùng fixture kỹ thuật riêng; không tuyên bố các mẫu thiên nhiên có VFR/rotation khi chưa có bằng chứng.

## Decoder và tiền xử lý

Đã so khung được chọn trên fixture VFR với toàn bộ PTS do FFprobe trả về: sai số tới target bằng khoảng cách nhỏ nhất thực tế, không suy thời gian từ FPS. Fixture rotation90° được giải mã thành ảnh dọc180×320. Đã sửa metadata để tách coded dimensions và displayed dimensions, và giới hạn EOF theo khoảng PTS quan sát thay cho hằng0,1s.

Trong12video, sai số target→actualPTS lớn nhất 0.019375s. Khoảng cách PTS thực của cặp motion nằm trong [0.233333,0.280000]s; Flow chuẩn hóa theo khoảng cách thực này. Mốc dự kiến vẫn .25s theo báo cáo.

Crop lấy max-composite16ảnh; hai mẫu Sea bỏ đúng25% diện tích viền đen. Các ảnh dọc giữ tỷ lệ và có viền vuông trước CLIP. Ảnh overview/contact sheets được xuất để kiểm tra bằng mắt. Dữ liệu quá tối không tự bị gán thành viền khi crop vượt điều kiện giữ diện tích.

Đã sửa sai số float32 trong khoảng cách HSV: tích lũy float64 và chuẩn hóa hệ số chồng lấp tương ứng OpenCV. Vector lưu vẫn float32 đúng báo cáo. Đã tái kiểm tra khoảng cách trên NPZ, không trích lại video; self-distance HSV/LBP bằng0, CLIP chỉ còn sai số máy khoảng2,22e-16. Test so khớp trực tiếp với `cv2.compareHist` đã qua.

## Bằng chứng và lệnh chạy

- [Tổng hợp kết quả](../../var/search_phases/02_features/validation.json)
- [Ảnh trước và sau của12mẫu](../../var/search_phases/02_features/overview.jpg)
- Mỗi thư mục video có `features.npz`, `validation.json`, `before.png`, `after.png`, `clip_letterbox.png`, `contact_sheet.jpg`, `hsv.png`, `lbp.png`, `motion.png`.
- Giá trị so sánh cặp mẫu và self-distance được lưu trong JSON; đây là kiểm chứng tính toán, chưa phải đánh giá độ chính xác tìm kiếm.

```powershell
cd 'D:/video csdldpt/he_thong_nhom12'
./scripts/Test.ps1 -RealAdapters
./.venv/Scripts/python.exe scripts/validate_stage2.py
```

## Giới hạn và đầu vào giai đoạn3

Đã hoàn thành pilot adapter thật, chưa trích toàn bộ561video hoặc tạo CSDL tìm kiếm mới. Không gán nhãn scene/trùng/logo và không công bố accuracy học thuật. Giai đoạn3 có thể dùng môi trường, model và adapters này để kiểm kê lại snapshot rồi build đầy đủ; không nhập DB540video cũ.

Mã cần tái dùng: `media.py`, `preprocess.py`, `features.py`; script pilot là kiểm chứng riêng, không thay thế orchestration full build trong `pipeline.py`. Review kỹ thuật và quality review nội dung vẫn cần được tách theo prompt giai đoạn3.
