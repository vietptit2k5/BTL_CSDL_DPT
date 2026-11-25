# Giai đoạn05 Trích đặc trưng thật trên mẫu

```text
Thực hiện giai đoạn05 tại D:/video csdldpt/he_thong_nhom12. Đọc prompts/BOI_CANH_CHUNG.md, kết quả02–04 và report_spec.json.

Hoàn thiện features.py bằng thư viện thật. Trích HSV128/LBP10/CLIP512 trên cùng16khung và Flow24 trên8cặp của mẫu đại diện đã kiểm tra. Dùng ít nhất hai video mỗi lớp nếu dữ liệu đủ; gồm ảnh dọc/viền đen/cảnh tối/tĩnh/động. Mọi kết quả gắn SHA nguồn, spec, model, device và versions.

Kiểm tra công thức HSV bin đúng OpenCV [0,180), LBP uniform riu2 và biên1px, CLIP sau projection và không crop mất nội dung, Farnebäck đúng tham số, magnitude/time/shortside, residual median và ngưỡng hướng≥.01. Flow mỗi phần L1 tổng1; không chia thêm3. Đặc tả trường hợp không có vector hướng hợp lệ và test quy ước đã chọn; không tuyên bố uniform direction là dữ liệu quan sát thật.

Lưu bảng chiều/dtype/min/max/norm, histogram HSV/LBP, minh họa motion và vector CLIP. Tính khoảng cách thật giữa một vài cặp; kiểm tra identical inputs, khoảng cách hữu hạn và miền giá trị. Không đoán tính đúng ngữ nghĩa từ việc vector đủ chiều; nhận xét chất lượng dựa trên mẫu thật và giữ bất định.

Chạy tests adapter và kiểm tra trực quan. Đầu ra: tính năng đã sửa, artifacts mẫu, thời gian/thiết bị, docs/phases/05_KET_QUA.md và ước lượng chi phí full build có căn cứ.

Nghiệm thu: cả bốn loại đặc trưng thật chạy đúng hợp đồng, cả ba descriptor ảnh được tính dù LBP đang có weight0. Không thay mô hình hoặc descriptor để đạt kết quả đẹp hơn. Chưa coi mẫu nhỏ là đã hoàn thành ND3 toàn bộ dữ liệu.
```
