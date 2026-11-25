# Giai đoạn 1 đã hoàn thành

Ngày kiểm chứng: 16/11/2026. Phạm vi: môi trường riêng, công cụ đọc video và suy luận CLIP thật; không chạy full build.

## Kết quả chạy thật

- Python 3.11.9 trong `.venv` của dự án, độc lập với site-packages của dự án cũ.
- Đã chép 44 distribution từ môi trường sẵn có bằng RECORD files, không tạo liên kết thư viện về môi trường nguồn. `pip check`: No broken requirements found. Package dự án được cài editable offline.
- FFmpeg/FFprobe 9.0.2 trong `tools/ffmpeg/bin`; checkpoint CLIP ViT-B/32 trong `models/clip-vit-base-patch32`. Không tải lại mô hình.
- CUDA thực: True; thiết bị: **NVIDIA GeForce RTX 3050 Laptop GPU**. Cấu hình hiện tại dùng `cuda`.
- Đọc video SEA005 bằng FFprobe/OpenCV, lấy khung PTS 6.300s, tiền xử lý và encode thật.
- CLIP:512chiều, `float32`, finite, norm L2=0.999999940. HSV128 và LBP10 cũng đã được trích thật.
- Bộ16test qua, gồm7test adapter OpenCV/scikit-image/FFmpeg thật; test tích hợp CSDL vẫn dùng fixture giả lập và được phân biệt rõ.

| Thư viện | Phiên bản đã chạy |
| --- | --- |
| numpy | 2.4.6 |
| Pillow | 13.0.0 |
| scikit-image | 0.26.0 |
| torch | 2.14.1+cu126 |
| transformers | 5.20.2 |
| opencv-python-headless | 5.0.0.93 |

## Thay đổi cần thiết

Đã sửa tương thích CLIP để lấy pooled vision output rồi áp visual projection512 trực tiếp, thay cho giả định `get_image_features` luôn trả tensor. Đây là cách giữ vector sau projection đúng báo cáo khi dùng Transformers5. Tham khảo [tài liệu CLIP chính thức của Hugging Face](https://huggingface.co/docs/transformers/model_doc/clip).

Đã hỗ trợ distribution OpenCV headless trong runtime identity, bổ sung doctor deep và công cụ FFmpeg cục bộ, sửa wrapper test để PowerShell5 không coi tiến độ unittest trên stderr là lỗi.

## Lệnh tái chạy

```powershell
cd 'D:/video csdldpt/he_thong_nhom12'
./scripts/Run.ps1 doctor --deep
./scripts/Test.ps1 -RealAdapters
./.venv/Scripts/python.exe scripts/validate_stage1.py
```

Lần encode đầu bao gồm tải thư viện/mô hình và khởi tạo GPU, tổng phép kiểm tra ghi nhận 90.2s; không dùng số này làm độ trễ truy vấn ổn định.

## Bằng chứng

- [Validation JSON](../../var/search_phases/01_environment/validation.json)
- [Doctor và vị trí thư viện](../../var/search_phases/01_environment/doctor.json)
- [Log16test](../../var/search_phases/01_environment/tests.log)
- [Bootstrap manifest](../../var/search_phases/01_environment/bootstrap.json)
- [Lock phiên bản](../../requirements.lock.txt)

Model identity: `1d4d7979767c631678a97a6117dce125efcd249add4913614bc3b74f87e1e1fc`. Spec hash: `a3f2de2bcfc6d4aa7dea0595cf9a832648b0a3e1b238df293e6b3ea3bcbd84c5`. Hash các nguồn báo cáo/Excel được ghi trong validation JSON; yêu cầu ảnh→5video và các kích thước đặc trưng được giữ nguyên.
