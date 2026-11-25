# Clone và gán nhãn độc lập cho TV2 / TV3

Repo chứa mã nguồn hệ thống và bộ ảnh gán nhãn mù. Phần gán nhãn chạy trực tiếp trong trình duyệt: **không cần Python, MySQL, CLIP, GPU hoặc video nguồn**. Bộ dữ liệu đầy đủ và môi trường chạy tìm kiếm vẫn ở máy trưởng nhóm; clone repo chưa tạo thành một bản hệ thống tìm kiếm có sẵn CSDL.

## Mỗi thành viên làm trên nhánh riêng

Repository: [vietptit2k5/BTL_CSDL_DPT](https://github.com/vietptit2k5/BTL_CSDL_DPT). Trưởng nhóm cấp quyền cho hai tài khoản Git của thành viên nếu muốn họ push trực tiếp. Các lệnh dưới đây dùng Git đã cài.

```powershell
git clone https://github.com/vietptit2k5/BTL_CSDL_DPT.git
cd BTL_CSDL_DPT
git switch -c gan-nhan/TV2
```

TV3 thay tên nhánh bằng `gan-nhan/TV3`. Không xem phiếu đã điền của người còn lại trước khi nộp phiếu của mình. Hai người có thứ tự ảnh khác nhau: X01 của TV2 không nhất thiết là X01 của TV3.

## Mở trang và điền nhãn

1. TV2 mở `data/test_internet/xac_nhan_mu/TV2.html` bằng Chrome/Edge; TV3 mở `TV3.html`.
2. Xem ảnh, bấm ảnh nếu muốn xem đầy đủ. Chọn lớp, mức chắc chắn; ghi lý do nếu `KHONG_RO` hoặc `phan_van`.
3. Dùng Trước/Tiếp để chuyển ảnh. Có thể chọn “Tới ảnh chưa hoàn tất” để tìm dòng còn thiếu.
4. Trang tự lưu tiến trình trên trình duyệt nếu được hỗ trợ. Tải **bản nháp** thường xuyên; dùng “Nhập lại phiếu CSV” để tiếp tục trên máy/trình duyệt khác. Bản nháp chứa đủ 60 dòng, các dòng chưa làm để trống.
5. Khi đủ 60 ảnh, bấm **Tải phiếu để nộp**. Trang kiểm tra độ đầy đủ và định dạng, không cho biết đáp án đúng/sai.
6. Chép file vừa tải về vào `data/test_internet/xac_nhan_mu/phieu_TV2.csv` hoặc `phieu_TV3.csv`, đúng tên và đúng thành viên. Nếu trình duyệt thêm `(1)` vào tên tải về, đổi lại đúng tên trước khi chép.

Không đổi tên/mã ảnh và không xóa dòng. Bảy lựa chọn: `SEA`, `WAT`, `FOR`, `MOU`, `RIV`, `FLO`, `KHONG_RO`. Mức độ: `chac` hoặc `phan_van`. Ghi chú chỉ giải thích lựa chọn, không tham gia điểm tìm kiếm. [Quy tắc phân lớp](../data/test_internet/xac_nhan_mu/HUONG_DAN.md) dựa trên ND1.

Nếu thích dùng Excel, có thể điền trực tiếp **bản sao** phiếu CSV rồi lưu dạng CSV UTF-8 với đúng bốn cột `anh,lop,muc_do,ghi_chu`; nhập lại vào trang để kiểm tra trước khi nộp. Không cần chạy script tạo bộ ảnh.

Ghi công nguồn và giấy phép ảnh ở `credits_TV2.csv` / `credits_TV3.csv`: các bảng này không có cột lớp đề xuất hoặc ghi chú sàng lọc của trưởng nhóm. Ảnh được thu nhỏ và đổi tên trong đợt chuẩn bị trước; bản ảnh trong gói được giữ nguyên SHA256.

## Kiểm tra và nộp qua Git

Nếu máy có Python 3, có thể kiểm tra thêm bằng lệnh chỉ dùng thư viện chuẩn:

```powershell
python scripts/labels/check.py --rater TV2
```

Thay `TV2` bằng `TV3` cho người còn lại. Kết quả mong đợi: `valid_complete`, `completed: 60`. Không có Python vẫn nộp được sau khi trang cho tải phiếu hoàn chỉnh.

```powershell
git status --short
git diff -- data/test_internet/xac_nhan_mu/phieu_TV2.csv
git add data/test_internet/xac_nhan_mu/phieu_TV2.csv
git commit -m "Complete independent labels for TV2"
git push -u origin gan-nhan/TV2
```

TV3 thay toàn bộ `TV2` bằng `TV3`. Chỉ commit phiếu của mình; không commit bản nháp, file tải trùng tên hoặc sửa mã nguồn. Sau push, gửi tên nhánh cho trưởng nhóm. GitHub cần tài khoản được cấp quyền ghi; nếu không có quyền, gửi đúng CSV để trưởng nhóm nhập. Phiếu ban đầu trên `main` để trống, các phiếu đã nộp nằm trên nhánh riêng; cách này phục vụ độc lập về quy trình, không phải cơ chế giấu nhánh khỏi người có quyền đọc repo.

## Trưởng nhóm nhận phiếu và tổng hợp

Chỉ nhận sau khi cả hai đã hoàn thành độc lập:

```powershell
git switch main
git fetch origin
git diff --name-only main...origin/gan-nhan/TV2
git diff --name-only main...origin/gan-nhan/TV3
```

Kiểm tra mỗi nhánh chỉ sửa đúng phiếu của người đó. Sau đó đưa hai phiếu về máy điều phối:

```powershell
git restore --source=origin/gan-nhan/TV2 -- data/test_internet/xac_nhan_mu/phieu_TV2.csv
git restore --source=origin/gan-nhan/TV3 -- data/test_internet/xac_nhan_mu/phieu_TV3.csv
.\.venv\Scripts\python.exe scripts/labels/check.py --rater TV2
.\.venv\Scripts\python.exe scripts/labels/check.py --rater TV3
.\.venv\Scripts\python.exe scripts/weights/t03_xac_nhan_nhan.py tong_hop
```

Máy điều phối giữ riêng nhãn đề xuất, metadata nguồn và `_doi_chieu_KHONG_MO.csv`; chúng **không nằm trong Git**. Vì vậy lệnh `tong_hop` chạy trên máy này, không chạy trên clone của người gán nhãn. Lệnh tạo thống kê đồng thuận và danh sách bất đồng; nhóm xử lý, khóa nhãn rồi mới chạy đánh giá ND4. Không đổi trọng số dựa trên kết quả test.

Không chạy `t03_xac_nhan_nhan.py tao` để tiếp tục bài đang làm: lệnh cũ tạo lại phiếu và có thể ghi đè nội dung đã điền. Script `scripts/labels/prepare.py` dành cho điều phối viên xuất lại HTML/manifest/credits từ mapping đang có, không tạo lại thứ tự ảnh hoặc phiếu.

## Những gì được giữ ngoài Git

`.gitignore` chỉ cho chia sẻ bộ ảnh mù, phiếu và hướng dẫn trong `data/`. File kết nối/mật khẩu, nhãn đề xuất, bảng đối chiếu, dữ liệu review, model, `.venv`, video, CSDL, vector và `var/` đều giữ cục bộ. Không dùng `git add -f` cho các tệp này. Chưa cần Git LFS cho bộ ảnh mù hiện tại vì từng ảnh nhỏ hơn giới hạn tệp thông thường.
