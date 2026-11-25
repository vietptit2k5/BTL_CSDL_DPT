# Giai đoạn01 Chốt hợp đồng và baseline

```text
Thực hiện giai đoạn01 cho hệ thống D23 nhóm12 tại D:/video csdldpt/he_thong_nhom12. Đọc và tuân theo prompts/BOI_CANH_CHUNG.md.

Đọc trực tiếp đề Excel D34:G36, mốc E2:G2, phần1–2 báo cáo và mã hiện có. Đối chiếu report_spec.json với từng tham số Bảng2.8, gồm các chi tiết crop, histogram, LBP, checkpoint, motion và PTS. Không dựa duy nhất vào bản phân tích cũ.

Chạy baseline tests và doctor bằng trình thông dịch xác định được; nếu môi trường thật thiếu, ghi chính xác thiếu gì và vẫn làm các bước đọc/kiểm tra tĩnh. Rà lỗi thực trong core/media/preprocess/features/repository/pipeline/search/evaluation/demo: PTS, VFR, rotation, preprocessing đồng nhất, provenance model/device, vector thiếu, cách tính điểm và đường dẫn artifact.

Hoàn thiện docs/THIET_KE_VA_MAPPING.md: mỗi yêu cầu Excel và đặc tả ND1–2 phải có module, input/output, bằng chứng và tiêu chí nghiệm thu. Tách quyết định mới ND3–4 khỏi yêu cầu cố định. Lập danh sách lỗi theo mức ảnh hưởng và sửa lỗi hợp đồng đã xác định được, không tự đổi mô hình/số khung/kích thước vector để né lỗi.

Đầu ra: docs/phases/01_KET_QUA.md, mapping cập nhật, kết quả baseline, danh sách khoảng trống và quyết định cần kiểm nghiệm. Ghi checksum nguồn báo cáo/Excel đang dùng để tránh đọc nhầm phiên bản.

Nghiệm thu: không lẫn ảnh đầu vào với video, không thêm điều kiện10giây; mọi đặc trưng báo cáo có đường triển khai; biết rõ đâu là skeleton, đâu đã chạy thật. Chỉ cập nhật giai đoạn01 Đạt khi các đối chiếu này có bằng chứng. Không thực hiện giai đoạn02 trong lượt này.
```
