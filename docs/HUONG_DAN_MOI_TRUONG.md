# Môi trường chạy đã kiểm chứng

Môi trường riêng đã được chuẩn bị tại `.venv` của dự án. Ngày16/11/2026, đã chạy thật trên Python3.11.9, RTX3050 Laptop GPU, CUDA, FFmpeg9.0.2, OpenCV5.0 headless và CLIP ViT-B/32 local. Phiên bản đầy đủ nằm trong `requirements.lock.txt`; vị trí thư viện thực nằm trong `var/search_phases/01_environment/doctor.json`.

## Dùng ngay trên máy hiện tại

Mở PowerShell trong thư mục dự án:

```powershell
cd 'D:/video csdldpt/he_thong_nhom12'
./scripts/Run.ps1 doctor --deep
./scripts/Test.ps1 -RealAdapters
```

Wrapper tự thêm `tools/ffmpeg/bin` vào PATH của tiến trình, dùng model local và cấu hình Hugging Face offline. Nó không thay PATH hệ thống. Gọi Python trực tiếp vẫn được; `run.py` và hai script kiểm chứng cũng cấu hình công cụ local.

```powershell
./.venv/Scripts/python.exe scripts/validate_stage1.py
./.venv/Scripts/python.exe scripts/validate_stage2.py
```

Script thứ hai chạy lại pilot12video; chỉ chạy lại khi thay mã trích, nguồn, model hoặc cần tái kiểm chứng. Không dùng pilot như CSDL full build. Script `recheck_pilot_distances.py` chỉ tính lại khoảng cách từ các vector NPZ đã có.

## Cấu hình hiện tại

- `model_path`: `models/clip-vit-base-patch32`, giải quyết tương đối từ gốc dự án.
- `device`: `cuda`, đã kiểm tra bằng GPU thật. Nếu chuyển sang CPU phải đặt `cpu` và tạo/chọn generation phù hợp device; không trộn index profile khác một cách âm thầm.
- `local_files_only`: `true`.
- `database.backend`: `mysql`; MySQL9.5.0 tại3306, driver `mysql-connector-python==9.7.0`. Kết nối lấy từ `.mysql.local.json`, không nằm trong config công khai. Xem [hướng dẫn MySQL](MYSQL.md).
- Thư viện được chép độc lập từ các RECORD của môi trường có sẵn, khoảng4,63GB; model và FFmpeg cũng có bản riêng trong dự án. Không liên kết ngược site-packages nguồn.
- Venv vẫn phụ thuộc Python3.11.9 đã cài trên máy; chép nguyên `.venv` sang máy khác không bảo đảm chạy được.

## Tạo lại từ nguồn local đã có

`Setup.ps1` nhận ba đường dẫn: Python có sẵn những phụ thuộc tương thích, thư mục snapshot CLIP và thư mục bin của FFmpeg. Các lệnh này không tải qua mạng hoặc sửa nguồn:

```powershell
./scripts/Setup.ps1 `
  -SourcePython 'D:/csdldpt_system/.venv/Scripts/python.exe' `
  -SourceModel 'D:/csdldpt_system/cache/hf/hub/models--openai--clip-vit-base-patch32/snapshots/3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268' `
  -SourceFFmpegBin 'C:/Users/ADMIN/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.2-full_build/bin'
./.venv/Scripts/python.exe -m pip install --no-index --no-deps --no-build-isolation -e .
./scripts/Run.ps1 doctor --deep
```

Đã thực hiện các bước tương ứng tạo venv, chép độc lập, `pip check`, cài editable offline và doctor. Script bootstrap bỏ qua file đã chép hợp lệ theo size+mtime khi tiếp tục cùng nguồn; nguồn thay đổi cần kiểm tra fingerprint sau setup. Không dùng bootstrap với nguồn chính là venv đích.

Driver MySQL được bổ sung sau bootstrap từ môi trường cũ; nguồn cũ có thể chưa có gói này. Khi tái tạo, cài `mysql-connector-python==9.7.0` từ wheel/mạng phù hợp hoặc cài đủ các gói trong lock, rồi chạy `pip check` và `./scripts/Run.ps1 mysql doctor`. Cài dependency không tự cài MySQL Server hoặc mang theo database.

## Khi chuyển máy

Tạo venv mới bằng Python tương thích rồi cài các phiên bản đã chốt từ nguồn gói thích hợp cho Windows/CUDA của máy đích; không giả định mọi wheel GPU đều có trên PyPI mặc định. Cần mang theo checkpoint local và FFmpeg hoặc cài công cụ tương đương, sau đó chạy doctor, tests và hai validation scripts. `requirements.lock.txt` ghi môi trường đã chạy, không chứa các wheel hay trình thông dịch.

`models/`, `.venv/`, `tools/ffmpeg/bin/` và `var/` được bỏ qua bởi Git. Khi bàn giao offline phải mang theo chúng theo kế hoạch đóng gói hoặc chỉ rõ cách tái tạo; chỉ clone mã nguồn không tự có model/index.
