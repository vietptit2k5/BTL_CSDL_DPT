# Giai đoạn02 Môi trường chạy thật

```text
Thực hiện giai đoạn02 tại D:/video csdldpt/he_thong_nhom12. Đọc prompts/BOI_CANH_CHUNG.md và docs/phases/01_KET_QUA.md; xử lý các lỗi chặn liên quan trước.

Thiết lập môi trường Python riêng dùng được, không tái sử dụng venv hỏng hay gỡ phần mềm hệ thống. Xác minh Python thực, CPU/GPU, NumPy/Pillow/OpenCV/scikit-image/PyTorch/Transformers và FFmpeg/FFprobe. Kiểm tra tương thích bằng import và phép tính thật, không chỉ pip list. Cập nhật doctor và hướng dẫn bootstrap PowerShell có đường dẫn được quote đúng khi chứa khoảng trắng.

Tìm checkpoint CLIP sẵn có trong D:/csdldpt_system/cache/hf theo chế độ chỉ đọc, xác minh kiến trúc ViT-B/32 và định danh. Cấu hình đường dẫn local hoặc commit cố định. Không tải lại hàng trăm MB nếu checkpoint phù hợp đã có. Mặc định giữ offline khi dùng cache. Thử encode một ảnh thật: output512 float32, finite, normL2≈1. Nếu GPU hoạt động, ghi đúng device/dtype; không mặc định có CUDA.

Chạy tests. Sau khi bộ phụ thuộc chạy được, lưu versions/lock tương ứng môi trường đã xác minh và hướng dẫn tạo lại. Không bịa phiên bản hoặc ghi rằng mô hình đã chạy nếu tải/import bị lỗi. Nếu mạng/quyền cản trở, hoàn thành phần độc lập và ghi hành động cụ thể còn thiếu.

Đầu ra: cấu hình môi trường/model cập nhật, lệnh cài/chạy tái lập, log doctor/import/FFprobe/CLIP smoke test, docs/phases/02_KET_QUA.md.

Nghiệm thu: chạy được bộ kiểm thử hiện có, mở video bằng decoder thật, probe metadata và encode CLIP thật. Chưa chạy full extraction; không tự chuyển sang giai đoạn03.
```
