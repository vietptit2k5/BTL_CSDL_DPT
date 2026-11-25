# Hướng dẫn gán nhãn (làm một mình, không trao đổi với người khác cho tới khi nộp phiếu)

Mở thư mục `anh_<TÊN>/`, xem từng ảnh ở kích thước đầy đủ, điền vào `phieu_<TÊN>.csv` (mở bằng Excel):
- cột `lop`: một trong SEA, WAT, FOR, MOU, RIV, FLO, hoặc KHONG_RO nếu không xác định được một lớp
- cột `muc_do`: `chac` hoặc `phan_van`
- cột `ghi_chu`: lý do khi chọn KHONG_RO hoặc phan_van (ví dụ: "hồ chiếm nửa dưới, núi nửa trên")

Quy tắc (Bảng 1.1 báo cáo ND1): gán theo **chủ thể chính – đối tượng chiếm diện tích lớn nhất và là trọng tâm của ảnh**.
| Mã | Lớp | Chủ thể |
|---|---|---|
| SEA | Biển | mặt biển, sóng, bờ biển, bãi cát giáp biển, hoàng hôn trên biển |
| WAT | Thác nước | dòng nước đổ từ trên cao xuống, kèm bọt và sương |
| FOR | Rừng | tán lá, thân cây, đường mòn trong rừng, rừng phủ kín sườn đồi |
| MOU | Núi | đỉnh núi, dãy núi, sườn núi, thung lũng (hình dạng núi là chủ thể) |
| RIV | Sông/Hồ | mặt nước tương đối phẳng có bờ bao quanh, có thể phản chiếu; không có sóng lớn, không có thác |
| FLO | Hoa | một bông hoa cận cảnh, bụi hoa, cánh đồng hoa |
Ví dụ: hồ có núi phía sau → RIV nếu mặt nước là phần lớn khung hình, MOU nếu núi là điểm nhấn; thác giữa rừng → WAT.

Không mở các file khác trong thư mục `test_internet` (nhãn đề xuất, bảng sàng lọc, bảng đối chiếu tên).
