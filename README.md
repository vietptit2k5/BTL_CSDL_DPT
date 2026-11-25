# Hệ thống tìm kiếm video của D23 nhóm 12

**TV2/TV3 làm bài gán nhãn:** clone repo, mở `data/test_internet/xac_nhan_mu/TV2.html` hoặc `TV3.html` bằng trình duyệt. Không cần MySQL/GPU/Python cho việc gán nhãn. Xem [hướng dẫn clone, điền và nộp phiếu qua Git](docs/GIT_GAN_NHAN.md). Mỗi người làm trên nhánh riêng; nhãn đề xuất và bảng đối chiếu được giữ ngoài Git.

Hệ thống bám báo cáo ND1–2, đề Excel nhóm12 và slide môn học; đã có giao diện tìm ảnh, MySQL đủ **561 video, 8.976 khung, 26.928 vector khung, 561 vector Optical Flow**, cùng cơ chế tìm video tương đồng ND3 hoàn thành B0–B8. **56 kiểm thử đã qua** ngày 25/11/2026. Kết quả tìm kiếm xuất đủ 5 file MP4 và ZIP, có trace tính lại được. Đánh giá độc lập ND4 được để riêng theo yêu cầu; rà soát nội dung video vẫn chờ người xác nhận.

Xem [hướng dẫn vận hành và tự chạy từng việc](docs/HOAN_THIEN_VAN_HANH.md), [tiến độ ND3–4](docs/TIEN_DO_ND3_ND4.md) và [toàn bộ kết quả ND3](var/video_similarity/run01/index.html). Demo hiện chọn máy đã kiểm chứng; giữ kiểm tra chặt về môi trường và chỉ mục.

Xem [kết quả giai đoạn 1](docs/search_phases/01_KET_QUA.md), [kết quả giai đoạn 2](docs/search_phases/02_KET_QUA.md) và [hướng dẫn môi trường đã chuẩn bị](docs/HUONG_DAN_MOI_TRUONG.md).

Xem [kết quả full build giai đoạn 3](docs/search_phases/03_KET_QUA.md), [kết quả chuyển MySQL](docs/search_phases/03_MYSQL.md) và [hướng dẫn MySQL/Workbench](docs/MYSQL.md). `config.json` dùng MySQL tại `127.0.0.1:3306`, database `d23_nhom12`; `var/current_mysql_index.json` chọn generation sẵn sàng. Bản SQLite gốc trong `var/current_index.json` được giữ để đối chiếu. Review nội dung vẫn pending.

Đọc [phân tích và mapping](docs/THIET_KE_VA_MAPPING.md) trước khi phát triển tiếp.

Thiết kế được tổ chức theo [12bài/386trang slide](docs/THIET_KE_THEO_SLIDE.md), có40nhóm mapping kiến thức→trang→module→phạm vi. Xem [kết quả giai đoạn4](docs/search_phases/04_KET_QUA.md) và [hướng dẫn tìm kiếm](docs/HUONG_DAN_TIM_KIEM.md).

Để triển khai tiếp theo từng mốc, dùng [chuỗi 12 prompt](prompts/README.md). Mỗi prompt có việc cần thực hiện, đầu ra và tiêu chí nghiệm thu; theo dõi tại [tiến độ giai đoạn](prompts/TIEN_DO.md).

Theo ưu tiên mới của nhóm, bắt đầu bằng [sáu prompt hoàn thiện hệ thống tìm kiếm trước](prompts/UU_TIEN_HE_THONG_TIM_KIEM.md); phần khảo sát học thuật và báo cáo làm sau.

## Cấu trúc

```text
report_spec.json       Đặc tả ND1–2, khóa tham số của Bảng 2.8
config.json            Đường dẫn, model, quyết định xếp hạng ND3–4
src/nhom12/
  core.py              Hợp đồng, snapshot SHA256, lấy mẫu thời gian, kiểm tra vector
  ports.py             Giao diện adapter và điểm mở rộng
  media.py             Đọc video, metadata và lấy khung gần PTS nhất
  preprocess.py        Giữ tỷ lệ, cắt viền chung, chuẩn hóa, letterbox
  features.py          HSV, LBP, CLIP và Optical Flow
  schema.sql           CSDL có khóa ngoại, ràng buộc kiểu/kích thước
  repository.py        Ghi, đọc và kiểm tra đủ vector
  building.py          Full build, resume, preflight và audit index
  provenance.py        Đối chiếu mã trích với source archive đã chứng nhận
  storage_mysql/       Schema, migration, kiểm tra và đọc vector từ MySQL
  pipeline.py          Luồng xây CSDL và truy vấn ảnh
  search.py            Tính điểm cùng khung, gom theo video, top5
  retrieval.py         So mọi khung bằng ma trận, tinh chỉnh bằng công thức tham chiếu
  querying.py          Phiên MySQL/GPU tái sử dụng, guard và xử lý ảnh
  file_snapshot.py     Giữ snapshot đọc nguồn/model trong phiên Windows
  query_evidence.py    Histogram, bằng chứng và tái tính điểm trace
  evaluation.py        Đánh giá bằng nhãn liên quan và ID truy vấn
  demo.py              Xuất HTML cục bộ có phát video và dấu vết
  cli.py               Các lệnh doctor, plan, build, verify, query
tests/                 Kiểm thử hợp đồng và lỗi dữ liệu
var/                   Đầu ra sinh tự động, không đưa vào mã nguồn
```

## Chạy bộ khung

Dùng Python 3.11 trở lên và môi trường riêng của dự án. Những lệnh sau chạy trong `he_thong_nhom12`.

Trên máy hiện tại, `.venv`, checkpoint và FFmpeg đã được chuẩn bị độc lập. Chạy `./scripts/Run.ps1 doctor --deep` và `./scripts/Test.ps1 -RealAdapters`; không cần cài lại theo lệnh tổng quát bên dưới. Kiểm chứng thực tế cho thấy Python cũ chạy được khi có quyền truy cập phù hợp; không kết luận trình thông dịch cũ đã bị gỡ.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[extraction]"
.\.venv\Scripts\python.exe run.py doctor
.\.venv\Scripts\python.exe run.py plan
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

`plan` chỉ đọc video để tính SHA256 và lập danh sách. Nó không xác nhận codec, thời lượng, một cảnh hay không trùng cảnh. Bản review mẫu giữ các trường kiểm tra là `null`, không tự đánh dấu đã đạt. Sao chép thành tệp review làm việc và ghi kết quả kiểm tra thật; đừng ghi đè mẫu đang dùng khi chạy plan lại.

Trước khi trích đặc trưng, cấu hình `model_path` tới checkpoint CLIP ViT-B/32 cục bộ hoặc đặt `model_revision` là commit đã chốt. Mặc định `local_files_only=true`, không tự tải mô hình. Hệ số ảnh hiện tại đã chọn bằng validation: CLIP 0,95 / HSV 0,05 / LBP 0; hệ số video khóa riêng: CLIP 0,90 / HSV 0,05 / LBP 0 / Flow 0,05. Đây là quyết định thực nghiệm của nhóm, không phải trọng số thầy quy định. Đánh giá ảnh độc lập chưa chạy.

Cần FFmpeg/FFprobe trên PATH để lấy metadata thời lượng thực, gồm cả video tốc độ khung biến đổi. OpenCV dùng để giải mã và lấy PTS; nếu backend không trả PTS tăng dần thì báo lỗi, không tự dựng timestamp từ FPS. `probe_estimate` chỉ dành cho chẩn đoán, không tham gia build.

```powershell
.\.venv\Scripts\python.exe run.py build
.\.venv\Scripts\python.exe run.py build --resume var/build-ID
.\.venv\Scripts\python.exe run.py mysql doctor
.\.venv\Scripts\python.exe run.py mysql list
.\.venv\Scripts\python.exe run.py query --image anh_truy_van.jpg
.\.venv\Scripts\python.exe run.py query-batch --images anh_a.jpg anh_b.png
.\.venv\Scripts\python.exe run.py replay --trace var/query-ID/trace.json
.\.venv\Scripts\python.exe run.py serve --port 8765
.\.venv\Scripts\python.exe run.py query-video --video WAT028
.\.venv\Scripts\python.exe run.py mysql metadata --class-code WAT --max-duration 6
```

Build tạo thư mục riêng, giữ `.building.sqlite` nếu chưa hoàn thành và chỉ đổi thành `index.sqlite` sau kiểm tra đầy đủ; cấu hình MySQL sẽ xuất bản bản trích đầy đủ vào MySQL trước khi trả pointer. `--resume` xác minh source/spec/model/code/environment và artifact trước khi reuse; `--reviews` tùy chọn gắn quality review với SHA. Pending không bị ghi thành true và không chặn readiness kỹ thuật. Không ghi vào video nguồn hoặc CSDL cũ. Muốn đổi máy cần giữ/mapping lại đường dẫn artifact hoặc xây lại index.

Kiểm tra index hiện tại:

```powershell
./scripts/Run.ps1 mysql verify
```

Query tạo `input.png`, `preprocessed.png`, vector, histogram, `trace.json`, `demo.html`, 5 bản sao MP4 trong `videos/`, manifest SHA256 và `results.zip`. Mở giao diện HTTP để tìm và phát/tải video; một số trình duyệt hạn chế đường dẫn file cục bộ trong HTML xuất riêng. JSON là bằng chứng chính cho vector, khoảng cách, điểm thành phần và thời điểm. Ứng dụng dùng tài khoản MySQL chỉ đọc; build/migrate cần profile quản trị riêng trong [hướng dẫn vận hành](docs/HOAN_THIEN_VAN_HANH.md).

## Trạng thái trước báo cáo

- ND3 video→video đã hoàn thành B0–B8, có nhãn ND1 tính lại bằng code gốc, hệ số khóa, baseline/ablation/SE và ví dụ. Xem [hướng dẫn tự chạy](scripts/video_similarity/README.md). `--baseline` chỉ dùng khi muốn so CLIP riêng.
- UI, xuất 5 MP4/ZIP, SQL lọc metadata, tài khoản ứng dụng riêng và lệnh incremental tạo generation mới đã có. Ba lượt chức năng MySQL/GPU/HTTP đạt; cold 128,92 s, warm 2,18/1,87 s trong lần đo 25/11, đã tách encode/search/guard/export. Đây không phải số đo độ liên quan.
- Chuẩn bị rà soát tại `data/reviews/review.html`, nhập CSV bằng `run.py reviews import`. Chưa có xác nhận toàn kho nên giao diện giữ trạng thái chờ. Chrome Guest đã kiểm tra chọn ảnh/tìm/hiện 5 kết quả, phát và tua đúng đoạn khớp trên hai video.
- Tập 60 ảnh và phiếu mù TV2/TV3 đã chuẩn bị; đánh giá độc lập ND4 để riêng, không dùng kết quả hệ thống cũ thay thế.
- Viết báo cáo ND3–4 và kịch bản demo từ artifact hiện tại; ghi các giới hạn về crop ảnh tối, nhãn chuyển động có liên hệ tự nhiên với Flow và khả năng chuyển máy.
