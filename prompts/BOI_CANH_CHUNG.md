# Bối cảnh bắt buộc cho mọi giai đoạn

## Mục tiêu và nguồn quyết định

Hoàn thành hệ CSDL lưu trữ và tìm kiếm video của D23 lớp04 nhóm12 trên bộ khung `D:/video csdldpt/he_thong_nhom12`.

Đọc nguồn theo thứ tự:

1. `D:/video csdldpt/D23-lớp 4 - Nhóm BTL- update.xlsx`, sheet `Trang tính1`, D34:G36 và E2:G2. Đây là đề chính thức.
2. `[D23-lớp 04] - Nhóm 12.pdf` và `Bao_cao_nhom_12_da_thay_bia_Times_New_Roman.docx` trong thư mục gốc. Xác minh phiên bản còn tồn tại; không dựa vào tên một tệp đã mất.
3. `report_spec.json`, `docs/THIET_KE_VA_MAPPING.md`, `README.md`, `docs/TRANG_THAI_KIEM_CHUNG.md` và kết quả các giai đoạn đã hoàn thành.
4. `docs/THIET_KE_THEO_SLIDE.md` và `docs/course_mapping.json`: thiết kế phải nối với kiến thức toàn bộ12bài trong `HeCSDL_DPT_slides`, dẫn đúng số trang PDF. Phân biệt chức năng đã triển khai với phương án chỉ tham khảo; không thêm mọi thuật toán slide vào đường truy vấn bắt buộc.

XLSX yêu cầu: ≥500 video ngắn cùng chủ đề; mô tả giống/khác; bộ đặc trưng có giải thích; trích đầy đủ và lưu CSDL; **một ảnh tùy chọn → đúng5 video khác nhau xếp giảm dần theo độ tương đồng**; sơ đồ/module vào-ra; kết quả trung gian; đánh giá; demo. Không áp đề D22 với video đầu vào hay tối thiểu10giây sang D23. Nhãn lớp không được dùng để lọc truy vấn thật.

## Hợp đồng phần1–2 cần bảo toàn

- Thiên nhiên, sáu thư mục Sea/Waterfall/Forest/Mountain/River-Lake/Flower; MP4/H.264; một cảnh. Khoảng4–30giây do nhóm chọn, làm tròn thời lượng0,1giây trước kiểm tra; đây không phải điều kiện tối thiểu10giây của thầy.
- K16 khung: t=.05T+.9T(k+.5)/16, k=0..15; chọn khung có PTS gần target nhất; lưu cả target và actual PTS.
- Decode cạnh ngắn360, giữ tỷ lệ. Crop trên max-composite ảnh xám16khung: percentile98<24 HOẶC mean<12; chỉ bỏ viền liên tục từ mép, tối thiểu1% mỗi cạnh; giữ ít nhất40% diện tích. Ảnh truy vấn dùng chính nó để xác định crop.
- HSV toàn khung8×4×4=128chiều, L1; Bhattacharyya dạng Hellinger. LBP uniform riu2 P8 R1,10chiều,L1,bỏ biên1px; Chi-square đối xứng. Ảnh cạnh ngắn256 trước tính hai đặc trưng.
- CLIP ViT-B/32 pretrained, checkpoint OpenAI đã chốt; ảnh giữ trọn nội dung bằng viền đen vuông rồi224×224; vector sau projection512chiều,float32,L2; cosine. Không tự đổi model hoặc fine-tune.
- Motion:8cặp dt dự kiến.25giây, xám short180, cùng vùng crop; Farnebäck(.5,3,15,3,5,1.2); histogram tổng/cục bộ/hướng, mỗi phần8ô. Ngưỡng độ lớn0,.01,.02,.04,.08,.16,.32,.64,∞; hướng≥.01. L1 từng phần, không chia toàn vector thêm3. Góc và xử lý hướng rỗng phải có quy ước rõ. Chuẩn hóa theo thời gian PTS thực khi khoảng cách lấy mẫu lệch dt dự kiến và ghi quyết định này.
- 16×(128+10+512)+24=10.424 số/video;650 số/ảnh. Phải trích cả LBP và Flow cho dữ liệu ngay cả khi trọng số ảnh của LBP bằng0. Không tạo Flow giả cho ảnh tĩnh.
- D5 khảo sát ND1 là chênh mức xám trung bình, khác descriptor Optical Flow. Mẫu quan sát120video và bảy cặp Bảng2.2 cần có ID/bằng chứng.

## Quyết định mới cho phần3–4 cần đánh giá

MySQL là backend vận hành theo yêu cầu trực tiếp của nhóm; SQLite được giữ làm checkpoint/bản chứng nhận trích. Đọc `docs/MYSQL.md` và `var/current_mysql_index.json`, không chuyển về SQLite khi phát triển truy vấn/giao diện. `best_joint_frame`, thang điểm bounded và trọng số CLIP.9/HSV.1/LBP0 là cấu hình triển khai đề xuất, chưa phải kết luận tối ưu của báo cáo1–2. Tính điểm thành phần trên cùng khung, gộp rồi chọn khung tốt nhất mỗi video; khung hiển thị phải khớp phép tính. Nếu thay chính sách sau thí nghiệm phải version, cập nhật mapping và trace. Không nhập CDF/trọng số/thí nghiệm cũ540video như kết quả của dataset mới.

Ảnh ngoài chủ đề vẫn trả5 video nếu index đủ; không gọi điểm xếp hạng là xác suất đúng. Đánh giá theo relevance được xác định độc lập, tách tìm lại video nguồn và tìm video liên quan, không chỉ báo cáo độ chính xác theo lớp.

## Hiện trạng đã kiểm chứng ngày18/11/2026

Giai đoạn1–4 đã đạt: venv riêng, CUDA/CLIP/FFmpeg thật; bộ561video đã trích đầy đủ8976khung,26928vector khung,561motion và chuyển chính xác sang MySQL `d23_nhom12` tại3306. Có33test qua và12ca ảnh thật, gồm ảnh độc lập ngoài bộ, dọc/tối; bốn ca khớp scalar trên toàn index. `SearchSession` giữ model/index, warm trung vị1.40giây và cold lượt đầu38.45giây trong một phép đo, có invalidation và trace replay. Đã mapping12bài/386trang slide theo40nhóm kiến thức. Xem `docs/TRANG_THAI_KIEM_CHUNG.md`, `docs/search_phases/04_KET_QUA.md` và `prompts/TIEN_DO.md`; tiếp theo là UI/media server giai đoạn5. Không chạy lại full extraction khi kết quả vẫn hợp lệ. Review scene/trùng/logo và relevance học thuật vẫn pending.

Dự án cũ `D:/csdldpt_system` có mã và mô hình tham khảo, nhưng DB chỉ540video; từng có31tệp trong DB khác nguồn và50tệp khác manifest. Chỉ đọc để tham khảo/tái dùng checkpoint đã xác minh, không sửa dự án cũ hay coi cache cũ là đúng.

## Cách thực hiện và ghi bằng chứng

- Thực hiện công việc được yêu cầu, không dừng ở kế hoạch. Giữ các thay đổi trong dự án mới. Không xóa/thay/cắt video nguồn hoặc sửa tài liệu gốc nếu chưa được người dùng yêu cầu riêng.
- Không giả lập kết quả học thuật, không đánh dấu review `true` chỉ để build chạy. Nhãn chưa biết giữ `null`/pending; tiếp tục phần độc lập và ghi rõ trở ngại cần con người.
- Dùng thư mục output riêng theo run, snapshot nguồn SHA256, hash đặc tả, model identity và phiên bản thư viện. Chặn index thiếu vector hoặc nguồn đã đổi. Không tự sửa hợp đồng ND1–2 để né test thất bại.
- Không suy ra đã hoàn thành từ sự tồn tại của file hoặc test giả lập. Phân biệt kiểm thử unit, tích hợp giả lập, adapter thật, full build và demo thật.
- Mọi lần tải/cài cần kiểm tra trạng thái hiện có, dùng môi trường riêng của dự án, không cài/gỡ toàn hệ thống. Xử lý hạn chế mạng/quyền theo công cụ; không tự nhận đã cài nếu bị chặn.
- Chạy kiểm thử phù hợp vùng thay đổi; không lặp full extraction khi nguồn/spec/model còn nguyên và kết quả đã kiểm chứng. Chốt dependency versions sau khi chạy thật, không bịa lockfile.
- Cập nhật `prompts/TIEN_DO.md`, `docs/TRANG_THAI_KIEM_CHUNG.md`, `docs/phases/NN_KET_QUA.md`. Báo cáo giai đoạn ghi ngày thực, mã đã đổi, lệnh/check thực chạy, đường dẫn bằng chứng, số liệu, hạn chế và đầu vào cho giai đoạn sau. Không đưa token/mật khẩu vào logs.

## Mẫu prompt tiếp tục sau khi bị ngắt

```text
Tiếp tục giai đoạn đang dở của hệ thống D23 nhóm12 trong D:/video csdldpt/he_thong_nhom12. Đọc prompts/BOI_CANH_CHUNG.md, prompts/TIEN_DO.md và kết quả giai đoạn gần nhất. Kiểm tra file/tiến trình đang có trước khi chạy lại. Giữ những kết quả hợp lệ cùng snapshot/spec/model; hoàn thành công việc còn thiếu và kiểm thử liên quan. Không tự chuyển giai đoạn hoặc tuyên bố hoàn tất khi tiêu chí chưa đạt. Cập nhật tiến độ và kết quả bằng bằng chứng thực.
```
