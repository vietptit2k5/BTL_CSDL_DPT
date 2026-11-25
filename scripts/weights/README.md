# Chọn hệ số tính điểm (trọng số kết hợp) cho tìm kiếm ảnh → video

**Phương pháp:** tìm kiếm lưới (grid search) trên tập validation, mục tiêu khai báo trước có ràng buộc, chọn theo quy tắc một sai số chuẩn (1-SE), đánh giá một lần trên tập test giữ riêng.

Công thức điểm giữ nguyên như hệ thống (`src/nhom12/search.py`): với mỗi khung, S = w_clip·s_clip + w_hsv·s_hsv + w_lbp·s_lbp, trong đó s_clip = (1+cos)/2, s_hsv = 1 − d_Bhattacharyya, s_lbp = 1 − χ². Điểm video = max theo 16 khung. Chỉ có bộ trọng số w được chọn ở đây; đặc trưng và khoảng cách vẫn đúng Bảng 2.8 của báo cáo ND2.

## Các bước

| Bước | Script | Ai chạy | Làm gì, vì sao |
|---|---|---|---|
| 1–2 | `w01_tao_tap_validation.py` | đã chạy sẵn | 561 truy vấn giả lập (mỗi video lấy khung số 7, biến đổi như ảnh người dùng giống thí nghiệm ND2), đi qua đúng đường xử lý truy vấn của hệ thống. Nhãn tự động: lớp và video nguồn. Script **tự kiểm tra** điểm tính được trùng với điểm của hệ thống (`ExactFrameIndex`). |
| 3 | `w02_khao_sat.py` | đã chạy sẵn | Khảo sát trước khi chọn: phạm vi điểm (B1), từng đặc trưng dùng riêng (B2), ma trận nhầm lẫn (B3). B2 là căn cứ đặt w_lbp = 0. |
| — | `muc_tieu.json` | **bạn đọc, chỉnh nếu cần** | Khai báo mục tiêu trước khi chọn. Sau khi đã chạy bước 4 thì không sửa nữa. |
| 4 | `w03_chon_he_so.py` | **bạn chạy** | Dò w_hsv trên lưới một chiều (w_clip = 1 − w_hsv), giữ cấu hình đạt R@1 ≥ ngưỡng, chọn theo 1-SE, thử thêm LBP. Ghi và **khoá** `var/weights/trong_so_chot.json`. |
| 5 | `w04_danh_gia_test.py` | **bạn chạy** khi có ảnh của TV3 | Đánh giá một lần trên ảnh Internet: P@5 theo lớp, SE, so với cấu hình cũ 0.9/0.1/0 và chỉ CLIP, thời gian, ảnh ghép 10 ảnh kém nhất để phân tích lỗi. Không chỉnh trọng số ở bước này. |

## Lệnh

Chạy trong thư mục `he_thong_nhom12` (cần MySQL đang chạy, máy đã build index):

```powershell
./scripts/weights/Chay.ps1 chon                                        # bước 4
./scripts/weights/Chay.ps1 test -Anh D:\test\anh -Nhan D:\test\nhan.csv # bước 5
./scripts/weights/Chay.ps1 lai                                         # làm lại bước 1–3 (chỉ khi CSDL thay đổi)
```

File nhãn của bước 5 (UTF-8, có dòng tiêu đề):

```csv
file,lop,nguon,nhom
bien_01.jpg,SEA,https://...,
ho_hoang_hon.jpg,RIV,https://...,ho_X
```

`lop` là SEA/WAT/FOR/MOU/RIV/FLO. `nhom` không bắt buộc: các ảnh cùng một địa điểm ghi cùng mã nhóm, để khi tính sai số chúng được coi là một đơn vị. Không dùng ảnh cắt từ video của nhóm.

## Đầu ra (`var/weights/`)

- `validation/`: ảnh truy vấn, `nhan.csv`, `bang_tuong_dong.csv` (mở bằng Excel để xem điểm từng khung), dữ liệu `.npz`
- `khao_sat/khao_sat.md` và các bảng B1–B3 (CSV)
- `chon_he_so/ket_qua_chon_he_so.md`, `bang_luoi.csv`, `duong_P5_R1.svg`; `trong_so_chot.json` (đã khoá)
- `test/ket_qua_test.md`, `bang_ket_qua.csv`, `top5_tung_anh.csv`, `anh_kem_nhat.jpg`

## Quy tắc giữ cho kết quả có giá trị

1. `muc_tieu.json` cố định trước bước 4; mọi thay đổi ghi vào mục `_lich_su` kèm lý do.
2. Bước 4 khoá kết quả; script từ chối chạy lại khi đã có `trong_so_chot.json`.
3. Chỉ mở tập test (bước 5) sau khi đã khoá; không chỉnh trọng số theo kết quả test.
4. Sau bước 5 mới cập nhật `config.json` (mục `search.weights`) theo `trong_so_chot.json`, rồi chạy `./scripts/Test.ps1`.
5. Không sửa file trong `src/nhom12/`: hệ thống kiểm tra mã băm của các file đó.
