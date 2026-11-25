# Giai đoạn07 Xây CSDL đầy đủ

```text
Thực hiện giai đoạn07 tại D:/video csdldpt/he_thong_nhom12. Đọc prompts/BOI_CANH_CHUNG.md và kết quả04–06. Chỉ full build khi nguồn/spec/model và review đáp ứng điều kiện.

Hoàn thiện schema/repository/pipeline để trích và lưu toàn bộ video, không chỉ mẫu. Không dùng DB540video/các vector cũ thiếu provenance. Dùng khóa video_id+frame_index, đủ HSV/LBP/CLIP mỗi khung và Flow mỗi video, timestamp/crop, metadata và SHA. Lưu spec/model/dependency identity theo generation.

Xử lý build dài: log tiến độ và thời gian, transaction theo video, trạng thái building/ready nhất quán. Bổ sung resume an toàn nếu cần để tránh chạy lại toàn bộ khi lỗi giữa chừng: chỉ tiếp tục khi source/spec/model/implementation trùng, kiểm tra lại từng phần hoàn thành; không bỏ qua file lỗi rồi đánh dấu ready. Giữ kết quả build cũ, không overwrite âm thầm.

Chạy full build bằng adapter thật. Đối chiếu số lượng theo manifest N: videos=N, keyframes=16N, frame_features=48N, motion=N; nếu N=561 thì 561/8.976/26.928/561. Kiểm tra FK, IDs, bytes/dtype/norm, finite và snapshot chưa đổi; lấy vài vector DB đối chiếu lần trích trực tiếp. Mô phỏng lỗi giữa chừng và nguồn đổi để kiểm tra phục hồi/từ chối.

Đầu ra: index mới ready, environment/snapshot/catalog, thống kê build thực, báo cáo lỗi nếu có và docs/phases/07_KET_QUA.md. Không coi việc file sqlite tồn tại là build thành công.

Nghiệm thu: bao phủ toàn bộ dữ liệu đã chốt, không vector0 thay thế thiếu, không thiếu21video như DB cũ, query nhận diện được generation hợp lệ. Không tự bắt đầu chọn trọng số hay báo cáo accuracy trong giai đoạn này.
```
