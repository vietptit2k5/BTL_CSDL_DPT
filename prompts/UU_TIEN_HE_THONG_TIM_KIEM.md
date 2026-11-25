# Sáu giai đoạn ưu tiên hoàn thành hệ thống tìm kiếm

Ưu tiên được điều chỉnh theo yêu cầu: **hoàn thành hệ thống tìm kiếm chạy thật trước**, sau đó khảo sát sâu, tối ưu học thuật và viết báo cáo. Dùng chuỗi sáu prompt dưới đây thay cho việc chạy lần lượt cả12 prompt cũ.

Chỉ sao chép khối `text` của giai đoạn đang thực hiện vào Codex. Mỗi giai đoạn phải tạo sản phẩm chạy được và bằng chứng kiểm tra. Nếu tiếp tục từ kết quả đã có thì xác minh và làm phần còn thiếu; không dựng lại hoặc chạy lại phần nặng còn hợp lệ.

**Cập nhật lưu trữ:** theo lựa chọn của nhóm, backend vận hành là MySQL, database `d23_nhom12`; dùng `var/current_mysql_index.json`. Giai đoạn3 đã chuyển đủ dữ liệu và vector bằng đối chiếu từng byte, xem `docs/MYSQL.md`. SQLite trong generation là bản chứng nhận/checkpoint, không phải nguồn vector của truy vấn vận hành. Giai đoạn4 tiếp tục trên MySQL, tận dụng smoke đã có và ưu tiên giảm độ trễ; không trích lại toàn bộ video chỉ để đổi backend hoặc trọng số.

| Mốc | Sản phẩm cụ thể |
| --- | --- |
| 1 | Môi trường chạy được, CLIP encode được ảnh thật |
| 2 | Một nhóm video thật có đủ bốn đặc trưng đúng báo cáo |
| 3 | CSDL mới bao phủ bộ dữ liệu, có kiểm tra đầy đủ và phục hồi build |
| 4 | Lệnh tìm kiếm nhận ảnh thật, trả5video và trace đúng |
| 5 | Giao diện chọn ảnh, tìm kiếm, phát video và xem trung gian |
| 6 | Khởi chạy lại ổn định, kiểm tra đầu cuối và bàn giao bản chạy |

## Quy tắc áp dụng cho chuỗi mới

Mọi thiết kế mới dùng [mapping toàn bộ slide](../docs/THIET_KE_THEO_SLIDE.md) làm cơ sở bố trí module và giải thích lựa chọn. Đã đọc12bài/386trang, có40nhóm kiến thức trong `docs/course_mapping.json`. Chỉ rõ bài/trang, module, đầu vào/đầu ra và kiểm chứng; phân biệt kỹ thuật ngoài phạm vi như ASR, inverted file, shot detection, k-d/R-tree hay phân tán chưa được cài đặt.

Giữ đặc tả của báo cáo1–2 và yêu cầu Excel. Đọc `prompts/BOI_CANH_CHUNG.md` để lấy tham số, nhưng **thứ tự và phạm vi sáu giai đoạn ở đây thay thế lộ trình12giai đoạn trước**. Không yêu cầu xong khảo sát120video, nhãn validation/test, tối ưu trọng số hoặc báo cáo Word mới được làm tìm kiếm.

Tách trạng thái kỹ thuật của index với trạng thái review chất lượng nội dung: có thể build và thử hệ thống trên video đã giải mã/trích đầy đủ trong khi review scene/trùng/logo còn pending. Không tự ghi review=true, không gọi dữ liệu đã đạt toàn bộ tiêu chí đề nếu chưa kiểm chứng. Review phát hiện video không hợp lệ phải được ghi lại và xử lý minh bạch; không âm thầm bỏ video hoặc thay nguồn.

Mỗi giai đoạn ghi `docs/search_phases/0N_KET_QUA.md`, gồm code thay đổi, lệnh thực chạy, môi trường, artifacts, kiểm tra đã qua và phần chưa xác minh. Giữ video/tài liệu/CSDL cũ nguyên trạng. Không tự gửi, nộp hoặc publish ra ngoài.

## Giai đoạn1 Làm cho môi trường và mô hình chạy thật

```text
Thực hiện giai đoạn1 theo prompts/UU_TIEN_HE_THONG_TIM_KIEM.md trong D:/video csdldpt/he_thong_nhom12. Mục tiêu là hệ thống tìm kiếm chạy thật trước; chưa khảo sát học thuật hoặc viết báo cáo.

Đọc README.md, report_spec.json, config.json, docs/TRANG_THAI_KIEM_CHUNG.md, prompts/BOI_CANH_CHUNG.md và đề Excel D34:G36. Xác minh nhanh hợp đồng ảnh→5video và bốn loại đặc trưng; không thiết kế lại dự án từ đầu.

Xác định Python thực đang dùng được; tạo/sửa môi trường riêng của dự án khi cần. Hoàn thiện cài đặt NumPy, Pillow, OpenCV, scikit-image, PyTorch, Transformers và FFmpeg/FFprobe. Không sửa hoặc gỡ môi trường cũ toàn hệ thống. Dùng checkpoint CLIP ViT-B/32 đã có nếu phù hợp; xác minh model identity, cấu hình đường dẫn local/commit cố định. Không tải lại mô hình nếu bản local dùng được.

Sửa lỗi tương thích hoặc cấu hình khiến doctor/import/encode thất bại. Chạy FFprobe trên một video, giải mã một khung và encode một ảnh thật thành vector512 float32 finite, L2≈1. Kiểm tra device thực, không giả định có CUDA. Chạy tests hiện có và lưu dependency versions đã xác minh.

Sản phẩm: môi trường hoạt động, cấu hình model, script/lệnh khởi chạy và docs/search_phases/01_KET_QUA.md. Chỉ coi xong khi phép chạy thật thành công; việc pip install xong hoặc test giả lập qua chưa đủ. Nếu gặp giới hạn mạng/quyền, hoàn thành phần độc lập và ghi trở ngại chính xác. Không chuyển sang nghiên cứu trọng số hoặc viết báo cáo.
```

## Giai đoạn2 Hoàn thiện xử lý video và trích đặc trưng

```text
Thực hiện giai đoạn2 theo prompts/UU_TIEN_HE_THONG_TIM_KIEM.md trong D:/video csdldpt/he_thong_nhom12. Đọc bối cảnh chung và kết quả giai đoạn1; sử dụng môi trường/model đã chạy thật.

Hoàn thiện media.py, preprocess.py và features.py trên mẫu video thật đại diện sáu lớp, ưu tiên hai video mỗi lớp và các trường hợp dọc, viền đen, tối, fps khác nhau, tĩnh/động. Lấy16khung theo timestamp đúng báo cáo; lưu target và actual PTS; xử lý rotation, VFR và trường hợp OpenCV không trả PTS hợp lệ bằng backend phù hợp, không dựng timestamp giả từ FPS.

Áp dụng đúng decode short360, crop max-composite theo ngưỡng báo cáo, ảnh short256, CLIP letterbox224. Trích đủ HSV128/LBP10/CLIP512 cho từng khung và Flow24 cho8cặp. Giữ chuẩn hóa đúng, Flow L1 từng phần; không bỏ LBP/Flow vì trọng số truy vấn ảnh không sử dụng chúng. Không thay video nguồn.

Sửa các lỗi phát hiện; thêm test cho lỗi cụ thể. Lưu artifacts mẫu với SHA/spec/model, bảng chiều/dtype/norm, ảnh trước/sau crop, contact sheet và phép so sánh mẫu. Kiểm tra trực quan; không tuyên bố adapter thật hoạt động từ mock tests.

Sản phẩm: pipeline trích trên mẫu chạy thật và docs/search_phases/02_KET_QUA.md. Hoàn thành khi cả bốn loại đặc trưng đúng hợp đồng và không còn lỗi chặn build. Chưa cần khảo sát120video hoặc bộ nhãn đánh giá học thuật.
```

## Giai đoạn3 Xây CSDL cho toàn bộ bộ video

```text
Thực hiện giai đoạn3 theo prompts/UU_TIEN_HE_THONG_TIM_KIEM.md trong D:/video csdldpt/he_thong_nhom12. Đọc kết quả1–2 và mã schema/repository/pipeline hiện có.

Kiểm kê SHA256, metadata và khả năng giải mã toàn bộ video hiện tại. Dùng manifest thật và báo rõ lỗi, không chỉ tin con số561 hoặc DB540video cũ. Giữ dữ liệu nguồn nguyên trạng; không nhập đặc trưng/cache cũ thiếu provenance.

Điều chỉnh kiến trúc để review thủ công scene/trùng/logo pending không chặn công việc build và thử tìm kiếm. Tách technical_ready với dataset_quality_status; giữ review pending nguyên nghĩa, không tự đánh dấu true, không bỏ kiểm tra codec/chiều/dtype/norm/vector đầy đủ. Những video thực sự lỗi phải có danh sách và nguyên nhân, không âm thầm loại khỏi index rồi công bố đủ dữ liệu.

Hoàn thiện full build, log tiến độ, transaction, cơ chế resume an toàn và trạng thái building/ready. Chỉ tiếp tục một build khi SHA/spec/model/implementation khớp. Không overwrite index hợp lệ; nguồn thay đổi phải invalidate phần liên quan.

Chạy trích thật toàn bộ dữ liệu, giữ checkpoint SQLite để phục hồi và xuất bản vào MySQL theo lựa chọn hiện tại của nhóm. Nếu kết quả đã được chứng nhận thì dùng migration đối chiếu từng byte, không trích lại chỉ để đổi backend. Với Nvideo, đối chiếu videos=N,keyframes=16N,frame_features=48N,motion=N. Nếu N=561 thì tương ứng561/8.976/26.928/561. Kiểm tra FK, ID, vectorfinite/norm, snapshot; đối chiếu một số vectorDB với lần trích trực tiếp. Kiểm thử lỗi giữa chừng và resume.

Sản phẩm: đường dẫn index dùng được, manifest/build summary và docs/search_phases/03_KET_QUA.md. Phân biệt rõ index đủ kỹ thuật với review nội dung còn thiếu. Không chờ hoàn tất báo cáo hoặc tối ưu học thuật mới build.
```

## Giai đoạn4 Hoàn thiện chức năng ảnh tìm video

```text
Thực hiện giai đoạn4 theo prompts/UU_TIEN_HE_THONG_TIM_KIEM.md trong D:/video csdldpt/he_thong_nhom12. Đọc kết quả1–3; dùng index thật đã kiểm tra.

Hoàn thiện lệnh query nhận một ảnh tùy chọn, áp dụng đúng tiền xử lý và HSV/LBP/CLIP, so khớp và trả đúng5video khác nhau giảm dần. Tính các điểm thành phần trên cùng khung rồi lấy khung tốt nhất mỗi video; hiển thị đúng khung dùng tính điểm và timestamp. Không lọc theo lớp, không tạo motion giả cho ảnh, không gọi điểm tương đồng là xác suất đúng.

Trước mắt dùng cấu hình provisional đang có CLIP.9/HSV.1/LBP0 hoặc baseline đã xác minh. Không dành giai đoạn này để grid search/viết báo cáo. Ghi rõ trọng số chưa được tối ưu; vẫn lưu đủ các đặc trưng theo ND3.

Hoàn thiện trace: queryhash, index/spec/model, crop, vectors, distances, normalizedscores, weights, contributions, finalscore, video/frameID và PTS. Xuất ảnh trước/sau và histogram; có cách tái tính/đối chiếu điểm từ trace. Kiểm tra source/index/model đã đổi và vector thiếu; không trả kết quả giả khi có lỗi.

Chạy thử bằng ảnh thật bên ngoài dataset, ảnh lấy từ video, ảnh dọc/tối/ngoài chủ đề và ảnh hỏng. Sửa lỗi, bảo đảm đường dẫn video/khung tồn tại và phát được. Đo thời gian sơ bộ, tách kiểm tra nguồn/encode/search; tránh nạp lại model và index cho mọi thao tác trong cùng phiên nếu có thể giữ guard hợp lệ.

Sản phẩm: truy vấn CLI chạy thật, top5+trace và docs/search_phases/04_KET_QUA.md. Hoàn thành khi kết quả tái tính được và không sai luồng đầu cuối. Video→video để sau nếu ảnh→video chưa hoàn thiện.
```

## Giai đoạn5 Làm giao diện sử dụng được

```text
Thực hiện giai đoạn5 theo prompts/UU_TIEN_HE_THONG_TIM_KIEM.md trong D:/video csdldpt/he_thong_nhom12. Đọc kết quả4 và tái sử dụng application service tìm kiếm đã chạy thật.

Xây/hoàn thiện giao diện cục bộ đơn giản: chọn ảnh, xem preview, bấm tìm kiếm, trạng thái xử lý/lỗi và năm kết quả. Mỗi kết quả có video phát được, hạng, điểm tương đồng, khung khớp và timestamp để tua; có khu vực xem ảnh tiền xử lý, histogram/điểm thành phần và tải trace.

Ưu tiên hoàn thành chức năng và độ ổn định. Không viết lại thuật toán trong UI hoặc phát triển tài khoản/quản trị/cloud. Nếu HTMLfile bị hạn chế phát video, triển khai local server phù hợp, có phục vụ media và hỗ trợ tua, chỉ lắng nghe trên máy cục bộ. Không publish ra Internet. Nạp model/index một lần phù hợp phiên làm việc, quản lý request để tránh chồng GPU/memory; không bỏ guard phiên bản dữ liệu.

Xử lý ảnh hỏng/sai dạng, thiếu index/model, request đang chạy và lỗi backend. UI chỉ truy cập media/artifacts thuộc phạm vi cho phép; không biến đường dẫn nhập vào thành chức năng đọc mọi file trên máy. Hiển thị trạng thái review nội dung ở nơi phù hợp nếu còn pending, không coi dữ liệu đã được kiểm chứng toàn diện.

Chạy trình duyệt thật: chọn ảnhmới→tìm→nhận5video→phát/tua→xem trung gian/trace; kiểm tra luồng lỗi và nhiều truy vấn liên tiếp. Sửa lỗi thực phát hiện và lưu bằng chứng.

Sản phẩm: giao diện và lệnh khởi chạy, screenshots/test results, docs/search_phases/05_KET_QUA.md. Hoàn thành khi người dùng thao tác được từ đầu tới cuối với index thật, không chỉ có mockup hoặc ảnh kết quả sẵn.
```

## Giai đoạn6 Hoàn thiện bản chạy và kiểm tra cuối

```text
Thực hiện giai đoạn6 theo prompts/UU_TIEN_HE_THONG_TIM_KIEM.md trong D:/video csdldpt/he_thong_nhom12. Mục tiêu bàn giao hệ thống tìm kiếm sử dụng được; đọc kết quả1–5.

Rà và sửa lỗi đầu cuối, chạy tests liên quan và kiểm tra toàn bộ indexcoverage/provenance. Thử khởi chạy lại ở phiên mới theo hướng dẫn, dùng model/index local và không phụ thuộc Internet khi đã có dữ liệu. Kiểm tra nhiều ảnh thật, ảnh ngoài chủ đề, lỗi input, năm ID khác nhau và điểm giảm dần, khả năng phát/tua và trace đúng phép tính. Kiểm tra model/index thiếu hoặc không cùng phiên bản và việc video nguồn thay đổi.

Đo latencycold/warm và bộ nhớ cơ bản; sửa các nút thắt rõ ràng như nạp model lặp, queryDB lặp hoặc hash lại không cần thiết trong phiên đã xác minh. Giữ quy tắc invalidate và tính đúng. Không biến tối ưu tốc độ thành bỏ descriptor, giảm K hoặc thay model trái báo cáo.

Hoàn thiện một lệnh/script khởi chạy, doctor rõ ràng, dependency versions đã kiểm chứng và hướng dẫn dùng trên Windows. Ghi cách cấu hình đường dẫn khi chuyển máy; chuẩn bị một ít ảnhdemo có nguồn và trace thực. Không đóng gói venv/token/cachethừa hoặc scripts dọn ổ. Giữ nguồn và artifacts quan trọng.

Sản phẩm: docs/HUONG_DAN_SU_DUNG.md, docs/search_phases/06_KET_QUA.md và bảng trạng thái chức năng với bằng chứng. Nêu chính xác hạn chế còn lại: reviewscene, nhãn đánh giá, tối ưu trọng số, video→video nếu chưa làm. Không công bố accuracy học thuật khi chưa có đánh giá độc lập.

Chỉ xác nhận bản tìm kiếm đã hoàn thành khi người dùng có thể khởi chạy→chọn ảnhmới→nhận5videothật→phátvideo→xem bằng chứng. Khảo sát/đánh giá học thuật sâu và báo cáo sẽ thực hiện trong chuỗi tiếp theo, không phải điều kiện để bắt đầu làm giao diện.
```

## Sau khi hệ thống tìm kiếm chạy ổn định

Quay lại các prompt cũ để hoàn tất nghĩa vụ học phần: khảo sát ND1 và review nội dung còn pending; tập relevance validation/test; so sánh và chốt trọng số; vai trò Flow qua video–video nếu cần; báo cáo ND3–4 và nghiệm thu toàn bộ yêu cầu Excel. Hoàn thành chức năng tìm kiếm chưa đồng nghĩa đã hoàn thành mọi nội dung nộp thầy.
