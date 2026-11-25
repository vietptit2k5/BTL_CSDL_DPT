# Tiến độ Nội dung 3–4 (cập nhật 25/11/2026)

## Đã xong

| Hạng mục | Kết quả | Vị trí |
|---|---|---|
| Trích đủ 4 đặc trưng (ND3a) | 561 video, 8.976 khung, 26.928 vector khung, 561 vector Optical Flow | `var/build-*/`, MySQL `d23_nhom12` |
| CSDL MySQL (ND3b) | Bảng có khoá ngoại, CHECK độ dài vector, phiên bản chỉ mục, trigger theo dõi thay đổi | `src/nhom12/storage_mysql/` |
| Cơ chế video → video ND3 | Đã chạy B0–B8; 561 video, 4 ma trận, loại chính truy vấn, trả 5 video; đối chiếu scalar 24 cặp đạt | `src/nhom12/video_search.py`, `src/nhom12/video_workflow/`, `var/video_similarity/run01/` |
| Nhãn khảo sát ND1 tính lại | Dùng nguồn s01/s04 cũ và ngưỡng ch1_stats.json; 511/511 video khớp kích thước manifest khớp cả 3 nhãn; giữ riêng 13 trường hợp khác pixel nhưng không đổi nhãn | `run01/b0/`, `run01/nd1_sources/` |
| Hệ số video ND3 | Chọn trên 279 truy vấn phát triển, 125 tổ hợp: CLIP 0,90 / HSV 0,05 / LBP 0 / Flow 0,05; khóa riêng với chế độ ảnh | `run01/trong_so_video.json`, `run01/b5/` |
| Đánh giá video giữ riêng | 282 truy vấn kiểm tra; P@5 lớp 0,9473; D1 0,4989; D2 0,5656; D5 0,5530; có bảng bỏ từng bộ, SE và mức ngẫu nhiên | `run01/b6/`, `run01/b7/` |
| Hướng dẫn không cần AI | Lệnh riêng từng bước, log, khung NPZ, bảng điểm, giải thích nhãn và trace; log ND3 lịch sử 49 test, hồi quy hiện tại 56 test qua | `scripts/video_similarity/README.md`, `docs/HOAN_THIEN_VAN_HANH.md`, `var/completion/tests.log` |
| Tìm ảnh → 5 video (ND4) | Dòng lệnh, chạy hàng loạt, giao diện web cổng 8765 | `run.py query`, `run.py serve` |
| Kết quả trung gian (4b) | Ảnh gốc/sau tiền xử lý/đầu vào CLIP, histogram, vector, điểm từng đặc trưng, khung khớp, tính lại điểm | `var/query-*/` |
| Chọn hệ số ảnh → video | **Đã khoá CLIP 0,95 / HSV 0,05 / LBP 0** (P@5 0,924 ± 0,008; R@1 0,998 trên 561 truy vấn validation) | `scripts/weights/`, `var/weights/trong_so_chot.json`, `var/weights/chon_he_so/` |
| Phân tích độ nhạy | Lưới đủ 231 tổ hợp: cùng kết quả theo 1-SE. Lưới mịn 0,01: HSV 0,01–0,02 cho P@5 cao hơn ~0,009 (~1 SE) – ghi là giới hạn, không đổi kết quả đã khoá | ghi chú trong cuộc trao đổi; cần đưa vào phụ lục 4c |
| Tập test ảnh Internet | 60 ảnh Commons Quality images, 177 ứng viên đã xét theo E1–E6, kiểm tra rò rỉ đạt | `data/test_internet/` |
| Gói gán nhãn mù | Phiếu và ảnh đổi tên cho TV2, TV3 | `data/test_internet/xac_nhan_mu/` |
| Đầu ra 5 file video | Cả truy vấn ảnh và truy vấn video mới xuất 5 MP4, manifest SHA256 và ZIP; giữ nguyên kết quả cũ | `result_export.py`, `var/query-*/`, `run01/b4/` |
| Tài khoản MySQL riêng | Ứng dụng SELECT + EXECUTE thủ tục stamp; root giữ trong file quản trị riêng | `storage_mysql/administration.py`, `scripts/setup_database_account.py` |
| Quản trị metadata | View có kiểu duration/fps/kích thước và lệnh lọc, SQL mẫu | `sql/metadata_examples.sql`, `run.py mysql metadata` |
| Thêm/xóa/thay video | Plan và build generation riêng; tái dùng vector của ID/SHA không đổi; không đổi pointer đang demo; kiểm thử MySQL riêng đạt | `incremental.py`, `run.py dataset-update` |
| Bộ rà soát chất lượng | HTML/CSV theo SHA256, lưu lịch sử nhập, cập nhật trạng thái truy vấn mà không trích lại | `data/reviews/`, `run.py reviews` |
| Kiểm tra vận hành | 3 lượt MySQL/GPU/HTTP đạt, MP4/ZIP/Range/replay; cold 128,92 s, warm 2,18/1,87 s, có thời gian từng pha | `var/completion/functional_validation.json` |
| Chia sẻ nguồn | Script ZIP theo danh sách cho phép, loại credentials/model/venv/cache | `scripts/tao_goi_chia_se.py` |

## Đánh giá độc lập ND4 — để riêng theo yêu cầu

1. TV2, TV3 điền phiếu gán nhãn mù → `t03_xac_nhan_nhan.py tong_hop` → xử lý `bat_dong.csv`.
2. Chạy `Chay.ps1 test -Anh data\test_internet\anh -Nhan data\test_internet\nhan.csv` (một lần).
3. Hệ số ảnh 0,95/0,05/0 đã áp dụng trong `config.json`; phần đánh giá ảnh Internet vẫn chờ nhãn. Hệ số video được lưu riêng và không ghi đè hệ số ảnh.

## Đối chiếu các vấn đề A/B/C đã nêu

| # | Việc | Ghi chú |
|---|---|---|
| A1 | Đã xong ND3 video tương đồng video | B0–B8, Flow có đóng góp đo được ở D5; LBP được chọn hệ số 0 |
| A2–A3 | Hệ số ảnh đã chọn và áp dụng; đánh giá độc lập chưa chạy | Giữ `provisional_requires_evaluation`, không gắn nhãn chính thức trước test |
| A4 | Hoàn thành cơ chế quản lý review, chưa có xác nhận con người | 0/561; 44 bản ghi thay cũ có 42 khớp, không đủ chứng nhận toàn kho; giữ hiển thị trung thực |
| B1 | README/tiến độ đã cập nhật | Số test mới là 56; log cũ giữ nguyên lịch sử |
| B2 | Chọn demo trên máy hiện tại đã kiểm chứng | Không nới kiểm tra; chuyển máy là công việc riêng cần kiểm chứng |
| B3 | Tái sử dụng phiên, hướng dẫn warm-up, đo tách pha | Cold vẫn 128,92 s ở lần đo mới; không tuyên bố đã loại bỏ thời gian khởi tạo |
| B4 | Có lệnh incremental | Bản dữ liệu/index/config mới riêng; kiểm thử tổng hợp trên MySQL riêng, chưa thay kho thật |
| B5 | Đã dùng tài khoản ứng dụng riêng, gói nguồn loại mật khẩu | Kết nối quản trị giữ riêng, không phát hành |
| B6 | Đã xuất 5 MP4 và ZIP | Đối chiếu SHA256; HTTP tải file và byte-range đạt |
| B7 | Đã có view và lọc metadata | JSON gốc vẫn giữ, view tách cột kiểu số để quản trị |
| C1 | Đã tái hiện crop ảnh trời tối, giữ thuật toán ND2 | `var/completion/crop/`; cần ghi hạn chế trong báo cáo |
| C2–C4 | Đã ghi đúng quy tắc điểm, ngoài chủ đề và cấu hình máy | Xem hướng dẫn vận hành; không dùng số hệ thống CDF cũ |
| C5 | Video truy vấn theo mã trong kho đã có | File video mới làm truy vấn trực tiếp vẫn là mở rộng ngoài phạm vi hiện tại |
| C6 | LBP hệ số 0 ở cả hai cấu hình đã chọn | Báo cáo trung thực, vẫn có số đo baseline LBP riêng ở ND3 |
| C7 | Đã phân biệt tổng thời lượng và thời gian build | `metadata_seconds` ≈ 6.877,73 s; `elapsed_seconds` ≈ 1.994,78 s |

Trước báo cáo cuối còn: nhóm xem và xác nhận nội dung video; tiếp tục đánh giá độc lập ND4 khi được yêu cầu; viết báo cáo từ các bảng/trace đã lưu. **Đã chốt phát/tua trên Chrome Guest**: chọn ảnh/gửi truy vấn/hiện đủ 5 kết quả, FLO037 phát và tua 5,80 s, FLO053 tua/phát 6,12 s; bằng chứng `var/completion/browser_validation.json`. Xem [hướng dẫn tự chạy chi tiết](HOAN_THIEN_VAN_HANH.md).

Không sửa: `core.py`, `media.py`, `preprocess.py`, `features.py`, `repository.py`, `schema.sql`, các hàm `extract_video`, `quality_review`, `build_index`, `model_identity`, `runtime_identity` (sửa là phải build lại ~33 phút và nạp lại MySQL).
