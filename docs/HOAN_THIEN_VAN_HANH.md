# Vận hành và tự thực hiện — cập nhật 25/11/2026

Các lệnh dưới đây chạy trong `D:\video csdldpt\he_thong_nhom12`, bằng PowerShell. Không cần AI để chạy lại. Dùng Python có sẵn của dự án; không cần tạo lại môi trường.

## 1. Mở và chuẩn bị demo

```powershell
$env:PYTHONIOENCODING = 'utf-8'
.\.venv\Scripts\python.exe run.py mysql doctor
.\.venv\Scripts\python.exe run.py serve --port 8765
```

Mở `http://127.0.0.1:8765`, chọn ảnh và tìm thử một lượt trước khi demo. Giữ cửa sổ lệnh đang chạy để tái sử dụng model/index. Dừng bằng Ctrl+C. Sau khi sửa code phải khởi động lại server.

Chọn demo trên **máy hiện tại đã được kiểm chứng**, giữ kiểm tra nghiêm ngặt về model, thư viện, thiết bị và đường dẫn. Gói mã nguồn bên dưới không phải bản mang sang máy khác là chạy ngay. Muốn đổi máy cần chuẩn bị môi trường/model/video và xây lại chỉ mục hoặc thực hiện một đợt chuyển đổi được kiểm chứng riêng; chưa có chế độ nới kiểm tra.

Mỗi lượt tìm ảnh tạo `var/query-ID/`: ảnh trước/sau xử lý, vector, histogram, trace, HTML, `videos/01_ID.mp4` đến `05_ID.mp4`, `result-manifest.json`, `results.zip`. ZIP chứa đúng 5 MP4 và manifest. SHA256 được đối chiếu cả khi chép và khi kiểm tra. Giao diện có tải từng MP4 hoặc cả ZIP; HTTP hỗ trợ Range cho media.

```powershell
.\.venv\Scripts\python.exe run.py query --image 'D:\duong_dan\anh.jpg'
.\.venv\Scripts\python.exe run.py replay --trace var/query-ID/trace.json
.\.venv\Scripts\python.exe run.py query-video --video WAT028
```

Thay đường dẫn ảnh và ID thư mục bằng đầu ra thật. Lệnh video dùng hệ số ND3 đã khóa và tạo thư mục **mới** trong `var/video_similarity/run01/b4/`, có HTML, điểm từng bộ, nhãn D1/D2/D5, ghép khung hai chiều, 5 MP4 và ZIP. Các truy vấn cũ vẫn được giữ nguyên.

## 2. Mapping ND1–2 và các quyết định đã giữ

| Nội dung đã định nghĩa | Cơ chế hiện tại / bằng chứng |
|---|---|
| ND1: 6 lớp, màu D1, kết cấu D2, chuyển động D5 | B0 tính lại bằng code s01/s04 gốc; ngưỡng 0,067/0,133 và 3,9/9,6; không học ngưỡng từ test |
| ND2: 16 khung; HSV128, LBP10, CLIP512; Flow24 cấp video | Trích một lần, lưu MySQL; không sửa quy tắc tiền xử lý hay định nghĩa vector |
| ND3: video tương đồng video | Ghép tập khung hai chiều riêng cho CLIP/HSV/LBP; Flow dùng Chi-square, tổng hợp trọng số; không so thứ tự thời gian |
| ND3: vai trò 4 bộ | Có baseline và bỏ lần lượt từng bộ ở B6; hệ số khóa CLIP 0,90 / HSV 0,05 / LBP 0 / Flow 0,05; LBP có kết quả dùng riêng nhưng không được chọn trong tổ hợp |
| ND4: ảnh tương đồng video | Ba bộ cấp khung, một khung chung làm bằng chứng; CLIP 0,95 / HSV 0,05 / LBP 0 đã chọn bằng validation; ảnh không có chuyển động nên không dùng Flow |
| Quản trị dữ liệu đa phương tiện | Bảng metadata và BLOB vector, khóa ngoại/ràng buộc; view SQL có kiểu; version chỉ mục và trigger theo dõi thay đổi |

ND3 đã có đủ B0–B8, xem [quy trình từng lệnh](../scripts/video_similarity/README.md) và [giải thích cơ chế](ND3_CO_CHE_TIM_VIDEO_TUONG_DONG.md). Không dùng các con số P@5/R@1 của hệ thống CDF cũ làm kết quả hệ thống này. Điểm tương đồng không phải xác suất. Ảnh ngoài chủ đề vẫn nhận đủ 5 kết quả theo đề.

`evaluation.py` vẫn là khung tham khảo; quy trình đánh giá ảnh thật nằm trong `scripts/weights/`. **Đánh giá độc lập ND4 đang để riêng theo yêu cầu:** chưa chạy test 60 ảnh và chưa đổi trạng thái thành kết quả chính thức. `search.status=provisional_requires_evaluation` vì còn bước này, không có nghĩa trọng số hiện tại được ước lượng tùy ý.

## 3. Rà soát nội dung video

Không tìm được phiếu xác nhận toàn bộ kho. Trạng thái hiện tại **0/561 video được người rà soát xác nhận**. Đã đối chiếu nhật ký cũ: 44 bản ghi, 42 khớp MD5 hiện tại; đây là bằng chứng thay video, không thay cho việc xem một cảnh/trùng cảnh/logo.

```powershell
.\.venv\Scripts\python.exe run.py reviews prepare
Start-Process .\data\reviews\review.html
```

Xem toàn bộ video, dùng bốn khung gợi ý để đối chiếu. Chọn từng tiêu chí: chỉ một cảnh liên tục, không trùng/gần trùng cảnh trong kho, không logo/chữ lớn nổi bật. Cần so với video khác trước khi xác nhận không trùng; bốn khung không đủ chứng minh một cảnh. Không chắc thì để trống. Điền tên/mã thành viên rồi tải CSV. Có thể chia ID cho các thành viên; dòng chưa điền không xóa kết quả đã nhập của người khác.

```powershell
.\.venv\Scripts\python.exe run.py reviews import --csv 'D:\duong_dan\review_completed.csv'
.\.venv\Scripts\python.exe run.py reviews status
```

Hoặc điền trực tiếp bản sao `data/reviews/review_template.csv`: các cờ là `true` / `false` / trống, ngày ISO như `2026-11-25T10:00:00+07:00`, giữ nguyên ID và SHA256. Mỗi lần nhập lưu bản trước vào `data/reviews/history/`. Nhãn có SHA cũ không được tính cho video đã thay. Ghi chú phục vụ giải thích/xử lý vấn đề, không tham gia điểm tìm kiếm.

Sổ xác nhận nằm ngoài các vector đã khóa; truy vấn mới ghi ảnh chụp trạng thái vào `quality-review.json` và trace. Không cần trích lại 561 video chỉ để cập nhật xác nhận. `quality_json` trong MySQL vẫn là trạng thái lúc build; view gọi rõ `indexed_review_status`. Giao diện sử dụng sổ xác nhận hiện tại và không che trạng thái chờ. Nếu trình duyệt còn tiến trình nháp cũ, tải lại phiếu mới hoặc dùng bản CSV để nhập đúng phần đã xem.

## 4. Quản trị MySQL

Ứng dụng đã chuyển từ root sang tài khoản riêng chỉ có **SELECT trên `d23_nhom12` và EXECUTE thủ tục `nh12_retrieval_stamp`**. Thủ tục SQL SECURITY DEFINER trả revision/counts/định nghĩa trigger cho việc phát hiện thay đổi. Đã đối chiếu kết quả với đường đọc bằng admin.

`.mysql.local.json` là kết nối ứng dụng; `.mysql.admin.local.json` giữ kết nối quản trị, không đưa vào ZIP hay gửi nhóm. `var/admin.config.json` là profile quản trị. Không chạy build/migrate bằng tài khoản ứng dụng chỉ đọc.

```powershell
.\.venv\Scripts\python.exe run.py mysql metadata --class-code WAT --max-duration 6
.\.venv\Scripts\python.exe run.py mysql metadata --portrait
.\.venv\Scripts\python.exe run.py --config var/admin.config.json mysql setup
```

Lệnh `setup` chỉ dùng khi cần cài view/thủ tục trên CSDL do nhóm quản trị. View `v_video_metadata` tách duration/fps/width/height/codec từ JSON thành cột có kiểu để lọc SQL. Xem [các truy vấn Workbench](../sql/metadata_examples.sql); chọn đúng generation khi chạy SQL trực tiếp.

## 5. Thêm, thay hoặc loại video khỏi phiên bản mới

Ví dụ dưới đây là cú pháp, không phải thao tác đã áp dụng lên kho 561 video. Tệp thêm phải theo mã lớp ND1 như `SEA087.mp4`, codec H.264 và giới hạn thời lượng theo đặc tả; tổng số video không dưới 500.

```powershell
# Chỉ xem kế hoạch, chưa trích hay nhập CSDL
.\.venv\Scripts\python.exe run.py dataset-update --add 'D:\video_moi\SEA087.mp4'
.\.venv\Scripts\python.exe run.py dataset-update --remove SEA001
.\.venv\Scripts\python.exe run.py dataset-update --add 'D:\video_moi\SEA001.mp4' --replace

# Thực hiện sau khi đã đọc kế hoạch
.\.venv\Scripts\python.exe run.py dataset-update --add 'D:\video_moi\SEA087.mp4' --apply
```

Kế hoạch chưa áp dụng được giữ tại `var/dataset_plans/ID.json`; màn hình in đường dẫn, số video tái dùng/cần trích và generation nguồn. Mặc định dùng file quản trị riêng khi nhập generation mới; có thể chỉ định `--admin-connection FILE`. Lệnh chép các video của phiên bản mới vào `var/dataset_versions/ID/dataset`, tái dùng vector/khung còn nguyên SHA256 và chỉ trích video thêm/thay. Cần đủ dung lượng cho bản sao toàn kho. Video bị loại chỉ vắng trong phiên bản mới, tệp gốc vẫn giữ. Phiên bản mới có `change-plan.json`, `result.json`, `config.json` và pointer riêng; lỗi được lưu `failure.json`.

Mở phiên bản mới bằng đường dẫn `config` mà lệnh trả về:

```powershell
.\.venv\Scripts\python.exe run.py --config var/dataset_versions/ID/config.json serve --port 8767
```

Không tự đổi `config.json` hay pointer hiện tại. Không tái dùng ma trận/hệ số ND3 của kho cũ để tuyên bố kết quả trên kho mới: cần run ND3 riêng khi đổi dữ liệu. `run01` tiếp tục thuộc đúng 561 video gốc đã khóa. Cơ chế incremental đã được kiểm thử tích hợp MySQL riêng bằng adapter giả lập: 6 video → 7, tái dùng 6/trích 1, generation và pointer ban đầu giữ nguyên. Chưa áp dụng thay đổi nội dung nào vào kho thật trong đợt này.

## 6. Kiểm thử vận hành và thời gian

Đầu ra ngày 25/11 nằm trong `var/completion/`:

| Kiểm tra | Kết quả |
|---|---|
| Hồi quy | 56 test qua, có adapter media thật và MySQL riêng; `tests.log` |
| HTTP + GPU + MySQL thật | 3 truy vấn chức năng qua; đủ 5 ID khác nhau, giảm dần, replay điểm đạt |
| Tệp đầu ra | 5 MP4/ZIP đối chiếu SHA; Range 512 byte trả 206; tải MP4 có attachment |
| Lượt đầu | Job 128,92 s, gồm khởi tạo/xác minh/nạp model, không gọi đó là thời gian so khớp |
| Hai lượt sau | Job 2,18 / 1,87 s; encode 0,164 / 0,116 s; so khớp 0,067 / 0,061 s |
| Bảo vệ trước+sau | Khoảng 0,89 / 0,79 s ở hai lượt sau |
| Chép 5 MP4 + ZIP | 0,346 / 0,271 s ở hai lượt sau |
| Trình duyệt | Chrome Guest: chọn ảnh/gửi truy vấn/hiện 5 kết quả đạt; FLO037 phát thật và tua tới 5,80 s, FLO053 tua/phát từ 6,12 s; `browser_validation.json` |

Đây là kiểm thử chức năng, không phải đánh giá độ liên quan ND4; không dùng 60 ảnh test. Ba lượt HTTP và một lượt trên Chrome, cùng một máy, không khái quát thành benchmark diện rộng. Lượt Chrome riêng hiển thị cold 113,21 s; đã kiểm tra phát/tua trực tiếp hai video, không khẳng định đã xem hết cả năm. Chi tiết từng pha trong `functional_validation.json` và trace. Báo cáo HTTP được giữ nguyên trạng thái tại thời điểm chạy; xác nhận trình duyệt thực hiện sau nằm trong `browser_validation.json`. Có thể chạy lại:

```powershell
.\.venv\Scripts\python.exe scripts/kiem_thu_van_hanh.py --port 8766
.\.venv\Scripts\python.exe scripts/kiem_tra_crop_anh_toi.py
.\.venv\Scripts\python.exe scripts/kiem_tra_bao_toan.py
```

Kiểm thử hồi quy đầy đủ cần MySQL thử nghiệm riêng: đặt `NHOM12_MYSQL_TEST_CONFIG` tới file kết nối CSDL thử nghiệm, `NHOM12_RUN_MEDIA_TESTS=1`, rồi chạy `python scripts/run_tests.py`. Không trỏ biến này vào `d23_nhom12`: test cần CSDL có thể tạo/xóa fixture. Log lưu trong `var/completion/tests.log`; không ghi đè log lịch sử của ND3. MySQL thử nghiệm cổng 3307 đã dừng sau lần chạy; dịch vụ chính cổng 3306 vẫn hoạt động.

Trên đúng máy hiện tại, datadir và kết nối kiểm thử đã được chuẩn bị trong `var/mysql-integration/`. Có thể mở lại server đó bằng MySQL 9.5 đã cài; không dùng đường dẫn datadir của dịch vụ chính:

```powershell
$testRoot = (Resolve-Path .\var\mysql-integration).Path
$testData = Join-Path $testRoot 'data'
$mysqlTestProcess = Start-Process -FilePath 'C:\Program Files\MySQL\MySQL Server 9.5\bin\mysqld.exe' -WindowStyle Hidden -PassThru -ArgumentList @(
  "--datadir=`"$testData`"", '--port=3307', '--bind-address=127.0.0.1', '--mysqlx=0',
  "--log-error=`"$testRoot\server.log`""
)
$env:NHOM12_MYSQL_TEST_CONFIG = (Resolve-Path .\var\mysql-integration\connection.json).Path
$env:NHOM12_RUN_MEDIA_TESTS = '1'
$env:PYTHONIOENCODING = 'utf-8'
# Đợi server.log có ready for connections rồi chạy:
.\.venv\Scripts\python.exe scripts/run_tests.py 2>&1 | Tee-Object var/completion/tests_replay.log
```

Sau khi test xong, dừng **đúng server thử nghiệm** qua kết nối đã kiểm tra cổng/database:

```powershell
.\.venv\Scripts\python.exe -c "import json; from pathlib import Path; import mysql.connector; c=json.loads(Path('var/mysql-integration/connection.json').read_text(encoding='utf-8-sig')); assert c['host']=='127.0.0.1' and int(c['port'])==3307 and c['database']=='nhom12_integration'; con=mysql.connector.connect(**c); con.cursor().execute('SHUTDOWN')"
```

Không chạy lệnh mở lại nếu cổng 3307 đã có server khác. Datadir thử nghiệm không nằm trong gói mã nguồn; trên máy khác phải tạo môi trường thử nghiệm riêng. Không thay file kết nối bằng mật khẩu viết trực tiếp trong lệnh.

Giới hạn ND2 đã tái hiện bằng ảnh tổng hợp 1280×720 có khoảng 42% phía trên tối: mức xám 8/15 bị cắt phần tối; mức 30 không bị cắt. [Kết quả crop](../var/completion/crop/report.json) và ảnh trước/sau được giữ. Không sửa thuật toán ND2 đã khóa; ghi rõ rủi ro với ảnh trời đêm trong phần hạn chế. Trong summary build cũ, `metadata_seconds` ≈ 6.877,73 s là **tổng thời lượng video**, còn `elapsed_seconds` ≈ 1.994,78 s mới là thời gian build; không sửa artifact lịch sử để đổi tên trường.

## 7. Đóng gói chia sẻ

```powershell
.\.venv\Scripts\python.exe scripts/tao_goi_chia_se.py
# Tùy chọn kèm toàn bộ bằng chứng ND3, dung lượng lớn hơn
.\.venv\Scripts\python.exe scripts/tao_goi_chia_se.py --full-run var/video_similarity/run01
```

Script chọn rõ các thư mục mã nguồn/tài liệu/test/SQL, kiểm tra ZIP và loại tệp mật khẩu, `.venv`, model, cache và video gốc. Mặc định kết quả ND3 đầy đủ vẫn giữ trên máy, không nằm trong gói nguồn. Không nén nguyên cả thư mục dự án bằng tay rồi gửi vì có các file kết nối riêng.

Các phần còn cần người làm trước báo cáo cuối: rà soát nội dung video thực tế, đánh giá độc lập ND4 khi nhóm tiếp tục phần đó, và viết báo cáo từ đúng artifact của hệ thống hiện tại. Phát/tua giao diện đã kiểm tra trực tiếp trên máy demo.
