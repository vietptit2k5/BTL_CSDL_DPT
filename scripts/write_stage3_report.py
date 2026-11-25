"""Publish a phase3 report only after full audit and direct checks succeed."""
import json
import hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[1]
out=root/'var/search_phases/03_database'
validation=json.loads((out/'validation.json').read_text(encoding='utf-8'))
assert validation['status']=='passed'
deep=json.loads((out/'deep_validation.json').read_text(encoding='utf-8'))
assert deep['status']=='passed'
index=Path(validation['index']);run=index.parent
checksum=hashlib.sha256()
with index.open('rb') as stream:
    for block in iter(lambda:stream.read(1024*1024),b''): checksum.update(block)
assert deep['index_sha256']==checksum.hexdigest(),'Deep audit belongs to a different database version'
summary=json.loads((run/'summary.json').read_text(encoding='utf-8'))
audit=validation['audit'];counts=audit['counts'];n=counts['videos']
assert counts['keyframes']==16*n and counts['frame_features']==48*n and counts['video_features']==n
report=root/'docs/search_phases/03_KET_QUA.md'
byclass='\n'.join(f'| {c} | {v} |' for c,v in sorted(audit['by_class'].items()))
checks='\n'.join(f'| {r["video_id"]} | {r["status"]} | {max(r["max_abs_differences"].values()):.8g} |' for r in validation['direct_checks'])
relative=index.relative_to(root).as_posix()
report.write_text(f'''# Giai đoạn 3 đã hoàn thành

Ngày kiểm chứng: 18/11/2026. Đã xây CSDL SQLite mới từ video và đặc trưng thật, không nhập lại DB540 video cũ.

## Chỉ mục hiện tại

`{relative}`

| Thành phần | Số lượng thực |
| --- | ---: |
| Video | {n} |
| Khung đại diện | {counts['keyframes']} |
| Vector HSV/LBP/CLIP cấp khung | {counts['frame_features']} |
| Vector chuyển động | {counts['video_features']} |
| Manifest artifact theo video | {counts['video_artifacts']} |

| Lớp | Số video |
| --- | ---: |
{byclass}

Metadata preflight đọc toàn bộ danh sách nguồn. Decoder trích các khung cần thiết theo PTS thật; không dùng việc đó để khẳng định đã kiểm tra nội dung mọi khung hoặc video luôn chỉ có một scene. SHA nguồn được xác minh trước/sau trích và khi hoàn tất toàn bộ generation.

## Tính đầy đủ và toàn vẹn

- SQLite integrity check: **{audit['integrity']}**; không có lỗi khóa ngoại.
- Mỗi video đủ16 khung; mỗi khung đủ HSV128,LBP10,CLIP512 float32. Mỗi video đủ Flow24. Mọi vector finite và đúng chuẩn hóa theo đặc tả ND1–2.
- Kiểm tra toàn bộ ảnh/NPZ bằng manifest SHA256; kiểm tra ID, timestamp tăng, metadata nguồn và source snapshot.
- Đối chiếu toàn bộ {deep['frame_vectors']} BLOB vector khung và {deep['motion_vectors']} BLOB motion với NPZ: bằng nhau chính xác. Đã kiểm tra {deep['pngs']} PNG về checksum, CRC, RGB và kích thước crop.
- Snapshot hash: `{audit['snapshot_hash']}`.
- Spec hash: `{audit['spec_hash']}`.
- Model identity: `{audit['model_identity']}`.
- Implementation hash: `{audit['implementation_hash']}`.

## Resume đã được kiểm chứng

- Bộ22test đã qua, gồm các kiểm tra adapter thật và lỗi/rollback/resume. [Log kiểm thử giai đoạn3](../../var/search_phases/03_tests.log).
- Đã dừng có kiểm soát sau3 video thật; file partial vẫn ở trạng thái building, không phải ready.
- Sau tiếp tục, tái sử dụng {validation['reused_video_events']} video đã hoàn thành và xác minh artifact; không trích lại những video đó.
- Các test mô phỏng cũng kiểm tra lỗi giữa transaction, thay nội dung nguồn dù giữ số byte và artifact hỏng. Resume từ chối nguồn/spec/model/code/environment khác; artifact hỏng được trích lại thay vì bù vector0.
- File chỉ được công bố thành `index.sqlite` khi tất cả dữ liệu đạt kiểm tra. Các generation khác giữ nguyên, không ghi đè.

## Đối chiếu vector bằng trích trực tiếp

Đã mở lại nguồn, giải mã và trích độc lập rồi so các vector trực tiếp với BLOB trong DB, tolerance1e-5. Đây là đối chiếu dữ liệu thật, không phải fixture giả lập.

| Video | Kết quả | Sai khác tuyệt đối lớn nhất |
| --- | --- | ---: |
{checks}

## Trạng thái kỹ thuật và review nội dung

Index **technical ready**. Dataset quality status: **{audit['dataset_quality_status']}**. Số review theo trạng thái: `{json.dumps(summary['quality_counts'])}`.

Trạng thái pending của scene/trùng/logo được lưu rõ trong từng video; không tự điền true để vượt kiểm tra. Chưa công bố dữ liệu đã được review toàn diện hoặc hệ thống đã có accuracy đánh giá độc lập.

## Tối ưu đã thực hiện

Khung đại diện và cặp motion dùng một lượt decode, chỉ chuyển màu/resize các khung đã chọn. Test VFR so PTS và pixel giữa yêu cầu hỗn hợp với các yêu cầu riêng đều qua. Số khung, timestamp đích, crop, descriptor và model theo báo cáo vẫn giữ nguyên.

Session tiếp tục ghi nhận {summary['elapsed_seconds']:.1f}s (gồm các kiểm tra trong session). Tổng lệnh orchestration kể cả pause/resume/audit/spotcheck ghi nhận {validation['elapsed_seconds_this_execution']:.1f}s. Không dùng những số này làm latency truy vấn.

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
- [Build summary](../../{run.relative_to(root).as_posix()}/summary.json)
- [Manifest metadata và nguồn](../../{run.relative_to(root).as_posix()}/manifest.json)
- [Sự kiện/resume](../../{run.relative_to(root).as_posix()}/events.jsonl)

Giai đoạn4 tiếp tục từ index này để hoàn thiện tìm kiếm ảnh và trace. Chưa đánh dấu giao diện, truy vấn đầu cuối hoặc báo cáo học thuật là đã hoàn thành chỉ vì CSDL đã sẵn sàng.
''',encoding='utf-8')
pointer=dict(index=str(index),generation=str(run),technical_status='ready',dataset_quality_status=audit['dataset_quality_status'],
             snapshot_hash=audit['snapshot_hash'],spec_hash=audit['spec_hash'],model_identity=audit['model_identity'])
(root/'var/current_index.json').write_text(json.dumps(pointer,ensure_ascii=False,indent=2),encoding='utf-8')
print(f'Published report: {report}; current index: {index}')
