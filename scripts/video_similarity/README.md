# Chạy lại cơ chế tìm video tương đồng ND3

Quy trình B0–B8 dùng bộ đặc trưng đã trích theo ND2 và quản lý trong MySQL. ND1 cung cấp nhãn dùng đánh giá; nhãn không được dùng để lọc hoặc xếp hạng video. Có thể thực hiện toàn bộ bằng các lệnh dưới đây, không cần AI.

Lần `run01` đã thực hiện xong: mở [trang tổng hợp kết quả và ba ví dụ](../../var/video_similarity/run01/index.html). Để tìm ngay bằng hệ số đã khóa, chạy `.\.venv\Scripts\python.exe run.py query-video --video WAT028` từ thư mục dự án. Các lệnh `run02` phía dưới dành cho việc tái hiện một lần mới từ đầu.

Mỗi lệnh ghi bản sao dòng lệnh, tiến trình và kết quả vào `var/video_similarity/<run>/logs/`. Các bảng CSV dùng UTF-8 có BOM để mở bằng Excel. JSON lưu số đầy đủ, không chỉ số làm tròn trên màn hình.

Thư mục `var/` đang được `.gitignore` bỏ qua. Khi sao lưu hoặc nộp bằng chứng, giữ riêng toàn bộ thư mục run cùng mã nguồn, `report_spec.json` và `specs/`; không chỉ sao chép các file được Git theo dõi. Giữ dữ liệu video ở đường dẫn được ghi trong snapshot để các trang HTML phát được media.

## Chuẩn bị máy và thư mục chạy

Mở PowerShell và chuyển tới dự án. MySQL phải đang chạy và `.mysql.local.json` phải trỏ tới CSDL đã có đặc trưng. Không đưa mật khẩu vào lệnh hoặc báo cáo.

```powershell
cd "D:\video csdldpt\he_thong_nhom12"
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:OPENBLAS_NUM_THREADS = '4'
```

Các lệnh gọi trực tiếp Python, không cần đổi ExecutionPolicy của Windows. `run01` là lần thực hiện đã lưu. Để làm một lần thực nghiệm mới từ đầu, thay `run01` bằng `run02` trong TẤT CẢ các lệnh. Không xóa file khóa để chọn lại trên một lần chạy đã xem kết quả test.

Chụp dữ liệu đầu vào chỉ đọc từ MySQL:

```powershell
.\.venv\Scripts\python.exe run.py video-workflow snapshot --run var/video_similarity/run02
```

Đầu ra `snapshot/`: `vectors.npz` chứa CLIP/HSV/LBP/Flow, `videos.json`, `frames.json`, `info.json` và `files.json` chứa SHA256. Bốn bộ đặc trưng vẫn là HSV128, LBP10, CLIP512 trên 16 khung và Flow24/video. Không trích lại CLIP và không dùng CSDL SQLite làm dữ liệu vận hành.

## B0 Tái lập nhãn đúng code khảo sát ND1

```powershell
.\.venv\Scripts\python.exe run.py video-workflow b0 --run var/video_similarity/run02 --legacy-root D:\csdldpt_system
```

Nguồn gốc được đọc ở chế độ chỉ đọc: `scripts/s01_cache_frames.py`, `scripts/s04_ch1_stats.py`, `src/common.py`, `config.yaml`, `outputs/ch1_stats.json`, `outputs/metadata.csv`, `outputs/manifest.csv`. Chương trình lưu bản sao và SHA256 tại `nd1_sources/`; không chạy các bước cũ có thể ghi đè outputs.

Các thao tác được tái lập:

1. Giải mã video hiện tại theo đúng cách lấy khung của s01: chọn PTS gần nhất, xử lý hòa như code cũ, resize bằng OpenCV INTER_AREA; 16 khung RGB cạnh ngắn 360 và 8 cặp xám cạnh ngắn 180.
2. Cắt viền như khảo sát ND1. Khung dùng màu và Canny thu về cạnh ngắn 256. Cặp dùng D5 giữ cạnh ngắn 180, cắt theo hộp viền tỷ lệ 0,5.
3. Tính tỷ lệ 8 màu theo Bảng 1.5. Chọn màu lớn nhất trước, sau đó ánh xạ GROUP5 đúng s04: xanh dương; xanh lục; trắng-xám; tối; màu ấm. Không cộng tỷ lệ nhóm màu trước khi chọn màu chủ đạo. Lưu cả `dominant_color` 8 màu và `dominant_group` 5 nhóm.
4. Tính mật độ Canny(100,200), trung bình trên 16 khung; dùng ngưỡng `thresholds.edge` của ch1_stats.json, không tính lại phân vị.
5. Tính trung bình hiệu tuyệt đối mức xám float32 trên 8 cặp; dùng `thresholds.motion` từ cùng file, không dùng Optical Flow thay nhãn D5.
6. Tính lại thống kê từ cache khung cũ để đối chiếu metadata cũ. Với 511 video có kích thước khớp manifest cũ, kiểm tra lại nhãn từ video hiện tại và so pixel của 32 khung với cache cũ.

Manifest cũ không có SHA256 video. Vì vậy “511 video không đổi” trước hết là nhóm có cùng số byte; báo cáo giữ riêng bằng chứng so khung và nhãn, không tuyên bố có SHA256 lịch sử. SHA256 của video HIỆN TẠI được lưu đầy đủ.

Đầu ra `b0/`:

| Tệp | Cách dùng khi trình bày |
|---|---|
| `nhan_nd1.csv` | Nhãn và giá trị liên tục cho 561 video hiện tại |
| `raw/<ID>.npz` | 32 khung thực tế dùng để tính nhãn, có thể mở bằng NumPy/Pillow |
| `raw/<ID>.json` | PTS thực, mật độ cạnh từng khung, hiệu từng cặp, tỷ lệ 8 màu, kết quả đối chiếu cache cũ |
| `baseline_check.json` | Danh sách video thay đổi, sai khác nhãn và sai khác pixel |
| `method.json`, `result.json` | Định nghĩa đo, ngưỡng gốc, nguồn và trạng thái kiểm tra |

Nếu B0 không khớp, chương trình dừng chọn hệ số và đánh giá chính thức. Không sửa nhãn để ép khớp. Nhãn chẩn đoán `--diagnostic` chỉ giúp tìm nguyên nhân và không mở khóa B5–B8. Giữ thư mục cache cũ nếu muốn chạy lại phép đối chiếu lịch sử từ đầu.

Để trả lời cụ thể “nhãn của SEA001 được tính thế nào”, tính lại trực tiếp từ 32 khung đã lưu, không cần MySQL hay GPU:

```powershell
.\.venv\Scripts\python.exe scripts/video_similarity/giai_thich_nhan.py --run var/video_similarity/run02 --video SEA001
```

Lệnh in tám tỷ lệ màu, mật độ cạnh của 16 khung, chênh lệch của tám cặp, phép lấy trung bình, ngưỡng gốc và ba nhãn; lưu bản giải thích tại `explanations/SEA001.txt`.

## B1 Cố định mục tiêu và cách chia dữ liệu

```powershell
.\.venv\Scripts\python.exe run.py video-workflow b1 --run var/video_similarity/run02
```

Chương trình sao chép `specs/video_goal.json` vào `b1/muc_tieu_video.json`, lưu mapping tại `mapping_nd1_nd2.json` và chia truy vấn tại `split.csv`, seed 2026. Kho tìm kiếm vẫn gồm đủ 561 video; mỗi truy vấn loại chính nó.

Bốn độ đo là cùng lớp, cùng D1, cùng D2, cùng D5 trong top 5. Tính macro theo sáu lớp. Mục tiêu tổng hợp được tính trên từng truy vấn bằng trung bình bốn độ đo rồi mới tính macro và SE, giữ tương quan giữa các độ đo.

Nếu có danh sách video cùng cảnh/cùng lần quay, chuẩn bị CSV `video_id,group` bao phủ đủ các video và dùng `--groups FILE.csv`. Nhóm không được nằm ở cả phát triển và kiểm tra. Mặc định mỗi video là một nhóm; điều đó không chứng nhận kho đã hết video gần trùng.

Chia dữ liệu là tách truy vấn trong một kho cố định, không phải kiểm tra khả năng tổng quát sang một kho video mới. D3 bố cục chưa có độ đo riêng.

## B2 Tính bốn ma trận tương đồng

```powershell
.\.venv\Scripts\python.exe run.py video-workflow b2 --run var/video_similarity/run02
```

CLIP dùng `(1 + cosine)/2`, HSV dùng `1 - Bhattacharyya`, LBP dùng `1 - Chi-square`. Với mỗi bộ, mỗi khung A tìm khung gần nhất trong B; lấy trung bình, làm ngược lại rồi lấy trung bình hai chiều. Tính riêng từng đặc trưng nên các cặp khung khớp có thể khác nhau. Không xét thứ tự khung theo thời gian.

Flow dùng `1 - Chi-square/3` vì vector 24 chiều gồm ba khối, mỗi khối có tổng bằng 1. Không chia lại vector lưu trong MySQL. Điểm tổng video là tổng các điểm đặc trưng nhân hệ số.

Đầu ra: `b2/matrices.npz` gồm bốn ma trận float64; `video_order.csv` cho biết thứ tự ID; `result.json` ghi thời gian dựng và chính sách. Đây là bước tính trước; không cộng thời gian này vào thời gian tra top 5 từ cache.

## B3 Kiểm tra phép tính

```powershell
.\.venv\Scripts\python.exe run.py video-workflow b3 --run var/video_similarity/run02
```

Kiểm tra miền điểm [0,1], đối xứng, tự so đạt điểm cao nhất (được hòa), đối chiếu các cặp cố định với cách tính từng khung độc lập, sai lệch nhỏ hơn 1e-6. Kết quả `b3/matrix_checks.csv`, `scalar_pairs.csv`, `result.json`. Đây là kiểm tra tính đúng của phép tính, không chứng minh chất lượng tìm kiếm.

## B4 Thử lệnh và mở trang kết quả

Trước khi chọn hệ số, dùng CLIP riêng làm đối chứng được ghi rõ:

```powershell
.\.venv\Scripts\python.exe run.py query-video --run var/video_similarity/run02 --video SEA001 --baseline
```

Sau B5, dùng hệ số video đã khóa:

```powershell
.\.venv\Scripts\python.exe run.py query-video --run var/video_similarity/run02 --video SEA001
```

Mở đường dẫn `ket_qua.html` mà lệnh in ra. Trang có 5 video khác truy vấn, điểm từng bộ, hệ số và đóng góp, D1/D2/D5, cặp khung minh họa riêng cho từng bộ. HTML dùng liên kết tới video cục bộ nên cần giữ đường dẫn dữ liệu trên máy.

Trong cùng thư mục, `all_candidates.csv` lưu toàn bộ 560 ứng viên, `frame_matches.csv` lưu đủ phép ghép hai chiều và `trace.json` lưu chính sách tính điểm. Cặp khung có điểm cao nhất trên trang chỉ là minh họa; điểm video dùng trung bình tất cả phép ghép.

Tính lại một trace đã lưu mà không đọc MySQL:

```powershell
.\.venv\Scripts\python.exe run.py video-workflow replay --run var/video_similarity/run02 --trace "DUONG_DAN_TRACE_JSON_VUA_TAO"
```

## B5 Chọn và khóa hệ số video

```powershell
.\.venv\Scripts\python.exe run.py video-workflow b5 --run var/video_similarity/run02
```

Chỉ chạy khi B0 và B3 đạt. Dò 125 tổ hợp HSV/LBP/Flow trong `{0;0,05;0,10;0,15;0,20}`; CLIP là phần còn lại, tối thiểu 0,4. Dùng 279 truy vấn phát triển của run mặc định; không lấy số đo nửa kiểm tra để chọn.

Giữ cấu hình có P@5 lớp không thấp hơn P@5 lớp tốt nhất trên lưới phát triển trừ một SE của cấu hình tham chiếu. Trong số đó, lấy vùng 1-SE của mục tiêu tổng hợp; ưu tiên ít hệ số khác 0 nhất, rồi CLIP lớn nhất, rồi thứ tự HSV/LBP/Flow để xử lý hòa. Hệ số 0 là kết quả hợp lệ. 1-SE là quy tắc lựa chọn, không phải kiểm định tương đương.

Đầu ra `b5/bang_luoi.csv`, `b5/result.json`, `trong_so_video.json`. Lệnh chạy lại chỉ kiểm tra và trả lại khóa cũ. Đổi dữ liệu, mục tiêu hoặc code thực nghiệm cần một run mới; không xóa khóa. Hệ số ảnh trong config.json không bị thay đổi.

## B6 Đo đóng góp trên nửa kiểm tra

```powershell
.\.venv\Scripts\python.exe run.py video-workflow b6 --run var/video_similarity/run02
```

Lần đầu tạo kế hoạch test cố định rồi đánh giá 282 truy vấn kiểm tra của run mặc định. Chạy lại với cùng đầu vào trả lại kết quả đã niêm phong; không chọn lại hệ số. Bảng gồm 9 cấu hình: bốn bộ dùng riêng; cấu hình chọn; bốn cấu hình bỏ lần lượt từng bộ và chuẩn hóa phần còn lại, không tối ưu lại. Nếu bỏ bộ duy nhất đang có hệ số thì dòng đó được ghi không xác định.

Đầu ra: `bang_dong_gop.csv`, `per_query.csv`, `top5_all_configurations.csv`, `per_class.csv`, `confusion_chosen.csv`, `result.json`. Có SE và chênh lệch ghép cặp; thêm chỉ số cùng lớp đồng thời cùng D1/D2/D5 để tránh diễn giải nhầm việc tăng khớp thuộc tính do trả về sai lớp.

## B7 Xuất báo cáo đánh giá

```powershell
.\.venv\Scripts\python.exe run.py video-workflow b7 --run var/video_similarity/run02
```

Đọc kết quả B6, không mở một đợt chọn lại. `b7/ket_qua.md` có bảng kết quả và cách diễn giải. Mức ngẫu nhiên tính từ phân bố nhãn thật trong kho, loại video truy vấn; không mặc định D5 bằng 1/3. Thời gian trong B6 là tra ma trận, kết hợp và xếp hạng từ cache; thời gian MySQL và dựng ma trận được lưu riêng.

Nhãn D1/D2/D5 là phép đo tự động của ND1, có liên hệ tự nhiên với HSV/LBP/Flow. Kết quả không thay thế hoàn toàn nhận xét liên quan của người dùng và không chứng minh D3 bố cục.

## B8 Xuất ví dụ báo cáo và demo

```powershell
.\.venv\Scripts\python.exe run.py video-workflow b8 --run var/video_similarity/run02
```

Chọn theo quy tắc cố định trên tập kiểm tra: truy vấn có mục tiêu tổng hợp tốt nhất; truy vấn có P@5 lớp thấp nhất; thêm truy vấn tăng D5 nhiều nhất khi có Flow nếu quan sát được tăng dương. Không mặc định Flow phải nhận hệ số dương. Kết quả `b8/result.json` trỏ tới các trang HTML và trace B4.

Kiểm tra lại các trace và tạo trang `index.html` liên kết toàn bộ đầu ra:

```powershell
.\.venv\Scripts\python.exe scripts/video_similarity/kiem_tra_vi_du.py --run var/video_similarity/run02
```

Lệnh này đọc các artifact đã niêm phong, tính lại điểm từ vector/ma trận, kiểm tra đủ năm video khác truy vấn và xuất `verification/final_examples.json`. Nó không chạy lại phép chọn hệ số hoặc đánh giá test.

## Kiểm tra trạng thái và kiểm thử mã

```powershell
.\.venv\Scripts\python.exe run.py video-workflow status --run var/video_similarity/run02
$env:PYTHONPATH = 'src;tests'
.\.venv\Scripts\python.exe -m unittest test_video_search -v
$env:NHOM12_RUN_MEDIA_TESTS = '1'
.\.venv\Scripts\python.exe scripts/run_tests.py
```

Các test MySQL tích hợp cần cấu hình CSDL kiểm thử riêng qua `NHOM12_MYSQL_TEST_CONFIG`; không trỏ biến này tới CSDL d23_nhom12 đang dùng. Kết quả có dòng skipped phải ghi rõ, không tính thành test đã chạy đạt.

Để giải thích một kết quả khi được hỏi, đi theo thứ tự: `nd1_sources` → `b0/raw` → `b0/nhan_nd1.csv` → `b1/mapping_nd1_nd2.json` và `split.csv` → `b2/matrices.npz` → `b3/scalar_pairs.csv` → `b5/bang_luoi.csv` → `trong_so_video.json` → `b6` → HTML và trace. Mọi bước có lệnh riêng và tệp trung gian tương ứng.
