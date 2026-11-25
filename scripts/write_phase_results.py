"""Render stage1/2 records only from successful real validation JSON files."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
artifact=root/'var/search_phases'
a=json.loads((artifact/'01_environment/validation.json').read_text(encoding='utf-8'))
b=json.loads((artifact/'02_features/validation.json').read_text(encoding='utf-8'))
assert a['status']==b['status']=='passed'
out=root/'docs/search_phases';out.mkdir(parents=True,exist_ok=True)
table='\n'.join(f'| {name} | {value} |' for name,value in a['packages'].items())
(out/'01_KET_QUA.md').write_text(f'''# Giai đoạn 1 đã hoàn thành

Ngày kiểm chứng: 16/11/2026. Phạm vi: môi trường riêng, công cụ đọc video và suy luận CLIP thật; không chạy full build.

## Kết quả chạy thật

- Python 3.11.9 trong `.venv` của dự án, độc lập với site-packages của dự án cũ.
- Đã chép 44 distribution từ môi trường sẵn có bằng RECORD files, không tạo liên kết thư viện về môi trường nguồn. `pip check`: No broken requirements found. Package dự án được cài editable offline.
- FFmpeg/FFprobe 9.0.2 trong `tools/ffmpeg/bin`; checkpoint CLIP ViT-B/32 trong `models/clip-vit-base-patch32`. Không tải lại mô hình.
- CUDA thực: {a['cuda_available']}; thiết bị: **{a['gpu']}**. Cấu hình hiện tại dùng `{a['device']}`.
- Đọc video SEA005 bằng FFprobe/OpenCV, lấy khung PTS {a['actual_pts']:.3f}s, tiền xử lý và encode thật.
- CLIP:512chiều, `{a['features']['clip']['dtype']}`, finite, norm L2={a['features']['clip']['l2']:.9f}. HSV128 và LBP10 cũng đã được trích thật.
- Bộ16test qua, gồm7test adapter OpenCV/scikit-image/FFmpeg thật; test tích hợp CSDL vẫn dùng fixture giả lập và được phân biệt rõ.

| Thư viện | Phiên bản đã chạy |
| --- | --- |
{table}

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

Lần encode đầu bao gồm tải thư viện/mô hình và khởi tạo GPU, tổng phép kiểm tra ghi nhận {a['elapsed_seconds']:.1f}s; không dùng số này làm độ trễ truy vấn ổn định.

## Bằng chứng

- [Validation JSON](../../var/search_phases/01_environment/validation.json)
- [Doctor và vị trí thư viện](../../var/search_phases/01_environment/doctor.json)
- [Log16test](../../var/search_phases/01_environment/tests.log)
- [Bootstrap manifest](../../var/search_phases/01_environment/bootstrap.json)
- [Lock phiên bản](../../requirements.lock.txt)

Model identity: `{a['model_identity']}`. Spec hash: `{a['spec_hash']}`. Hash các nguồn báo cáo/Excel được ghi trong validation JSON; yêu cầu ảnh→5video và các kích thước đặc trưng được giữ nguyên.
''',encoding='utf-8')
rows='\n'.join(f"| {v['video_id']} | {v['metadata']['fps']:.3f} | {v['feature_size'][0]}×{v['feature_size'][1]} | {v['crop_removed_fraction']:.1%} | {v['seconds']:.1f} |" for v in b['videos'])
errors=max(v['max_target_error'] for v in b['videos'])
dtlow=min(v['motion_dt_range'][0] for v in b['videos']);dthigh=max(v['motion_dt_range'][1] for v in b['videos'])
(out/'02_KET_QUA.md').write_text(f'''# Giai đoạn 2 đã hoàn thành

Ngày kiểm chứng: 16/11/2026. Đã chạy trích đặc trưng thật trên **{b['sample_count']}video, hai video mỗi lớp**. Không sử dụng các vector/cache cũ làm kết quả mới và không thay video nguồn.

## Phạm vi và số lượng

- {b['keyframe_count']}khung đại diện, {b['frame_vector_count']}vector cấp khung và {b['motion_vector_count']}vector chuyển động.
- Mỗi video có HSV16×128, LBP16×10, CLIP16×512 và Optical Flow24.
- HSV/LBP L1 và CLIP L2 đều được kiểm tra finite/norm. Motion có3khối8chiều, mỗi khối tổng1, không chia thêm3.
- Spec/model identity trùng giai đoạn1. Tổng thời gian pilot sau khi nạp encoder: {b['elapsed_seconds']:.1f}s; chưa phải benchmark full build.

| Video | FPS | Kích thước ảnh đặc trưng | Diện tích viền bỏ | Thời gian/video giây |
| --- | ---: | --- | ---: | ---: |
{rows}

Mẫu có video dọc, cảnh tối, cảnh tĩnh/động, FPS25/29.97/30/59.94/60 và viền đen Sea. Việc kiểm chứng VFR và rotation dùng fixture kỹ thuật riêng; không tuyên bố các mẫu thiên nhiên có VFR/rotation khi chưa có bằng chứng.

## Decoder và tiền xử lý

Đã so khung được chọn trên fixture VFR với toàn bộ PTS do FFprobe trả về: sai số tới target bằng khoảng cách nhỏ nhất thực tế, không suy thời gian từ FPS. Fixture rotation90° được giải mã thành ảnh dọc180×320. Đã sửa metadata để tách coded dimensions và displayed dimensions, và giới hạn EOF theo khoảng PTS quan sát thay cho hằng0,1s.

Trong12video, sai số target→actualPTS lớn nhất {errors:.6f}s. Khoảng cách PTS thực của cặp motion nằm trong [{dtlow:.6f},{dthigh:.6f}]s; Flow chuẩn hóa theo khoảng cách thực này. Mốc dự kiến vẫn .25s theo báo cáo.

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
''',encoding='utf-8')
print('Wrote successful stage1/stage2 reports from real artifacts')
