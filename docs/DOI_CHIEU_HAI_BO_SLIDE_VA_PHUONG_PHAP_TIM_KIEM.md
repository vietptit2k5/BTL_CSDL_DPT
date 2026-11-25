# Đối chiếu hai bộ bài giảng: phương pháp tìm kiếm, trọng số và đánh giá

Ngày phân tích: 18/11/2026. Phạm vi: toàn bộ24 PDF ở `HeCSDL_DPT_slides` và `MMDB slides`. Đã trích xuất/rà nội dung từng trang, đọc kỹ phần vector, phản hồi, độ đo ảnh, mô hình dữ liệu và đánh giá; render các trang công thức/biểu đồ liên quan để kiểm tra trực quan. Không chạy OCR toàn bộ các hình trong971trang. Những kết luận “không tìm thấy” là kết quả rà văn bản và các hình liên quan đã kiểm tra, không phải chứng minh hình thức rằng mọi hình ảnh đều không chứa thuật ngữ đó.

**Kết luận trực tiếp:** trong bài giảng có vector/cosine, relevance feedback/Rocchio, nhiều độ đo histogram, phân cụm/k-NN và quy trình đánh giá bằng nhãn liên quan. Không tìm thấy hướng dẫn tự suy ra bộ trọng số tối ưu CLIP/HSV/LBP chỉ từ kho video. Grid search, RRF và learning-to-rank là những hướng mở rộng đã trao đổi, không nên ghi là thuật toán được trình bày trong hai bộ slide này.

Không thay cấu hình0.9/0.1/0, mã tìm kiếm, vector, dữ liệu MySQL hay báo cáo gốc trong lần phân tích này.

## 1. Hai thư mục khác nhau thế nào?

| Bộ tài liệu | Số PDF | Tổng số trang PDF |
| --- | ---: | ---: |
| `HeCSDL_DPT_slides` | 12 | 386 |
| `MMDB slides` | 12 | 585 |
| Tổng | 24 | 971 |

Bộ MMDB có nhiều nội dung mở rộng và ví dụ cụ thể hơn. Tên thư mục mới không đủ xác nhận ngày xuất bản hay phiên bản chính thức mới nhất. Không tự đặt bộ này cao hơn đề Excel D23 hoặc báo cáo ND1–2 của nhóm.

**Các số bài không hoàn toàn tương ứng:** metadata chuyển từ Bài6 tiếng Việt sang Lecture9; dữ liệu nhiều chiều từ Bài7 sang Lecture6; vector/phân cụm từ Bài8 sang Lecture7; văn bản/Boolean từ Bài9 sang Lecture8.

| Chủ đề | Bộ tiếng Việt | Bộ MMDB | Nội dung đáng chú ý khi đối chiếu |
| --- | --- | --- | --- |
| Nhập môn, đánh giá | Bài1,51trang | Lecture1,69trang | MMDB tr.57 nêu nhãn relevance do chuyên gia xác định; tr.61–68 nêu benchmark, precision/recall/F1 và khó khăn khi tính recall |
| Các loại dữ liệu | Bài2,37trang | Lecture2,52trang | Mô tả rõ pipeline ảnh, semantic gap, biểu diễn dữ liệu gốc + vector; tr.20 nói về feedback |
| Nén | Bài3,36trang | Lecture3,52trang | Thêm ví dụ lossless/lossy, lượng tử, DPCM, DCT, entropy coding; không phải cách học trọng số xếp hạng ảnh |
| Kiến trúc | Bài4,28trang | Lecture4,50trang | Thêm bài tập kiến trúc, lớp server, QoS và routing; công thức0.5load+0.5RTT ở tr.26 dùng chọn server, không dùng chọn video tương đồng |
| Mô hình dữ liệu | Bài5,23trang | Lecture5,61trang | Mở rộng sang ORDBMS, NoSQL, graph, vector DB; tr.53–58 có embeddings, exact/ANN, HNSW/IVF/PQ và kiến trúc kết hợp |
| Siêu dữ liệu | Bài6,34trang | Lecture9,58trang | Thêm taxonomy, tiêu chuẩn, vòng đời, API và schema mở; giúp lưu nguồn gốc/nhãn/phản hồi nhưng không tự tính relevance |
| Dữ liệu nhiều chiều | Bài7,62trang | Lecture6,75trang | Làm rõ exact/range/NN/k-NN và các loại cây; chủ yếu là tổ chức và tìm ứng viên |
| Vector/phân cụm | Bài8,27trang | Lecture7,31trang | Nêu đích danh Rocchio ở tr.10,13; bổ sung FCM ở tr.27–30, silhouette/WCSS ở tr.16 |
| Văn bản/Boolean | Bài9,18trang | Lecture8,26trang | TF–IDF, inverted index, Boolean trọng số; trọng số từ khóa khác trọng số giữa các descriptor ảnh |
| Âm thanh | Bài10,29trang | Lecture10,45trang | Thêm MFCC/GMM, ASR, DTW, fingerprinting; không áp trực tiếp cho ảnh tĩnh |
| Ảnh | Bài11,27trang | Lecture11,43trang | Thêm bảng L1/L2/chi-square/Bhattacharyya, EMD, PWH, CLIP/CNN, GLCM và các ví dụ pipeline |
| Video | Bài12,14trang | Lecture12,23trang | Làm rõ keyframe, bảng timecode/segment, direct seek, motion, multimodal; tr.16 gắn kết quả với vị trí phát video |

Manifest tên file, số trang và SHA256: `var/course_comparison/manifest.json`. Văn bản đầy đủ từng trang: `var/course_comparison/vietnamese/` và `var/course_comparison/mmdb/`. Các công thức đã render: `var/course_comparison/rendered/`.

**Quy ước:** mọi số trang trong tài liệu này là thứ tự trang PDF, bắt đầu từ1. Số in trên slide có thể khác: MMDB Lecture7 PDFtr.13 in số16; bản Việt Bài8 PDFtr.12 in số13.

## 2. Vector và cosine: một baseline không cần trộn nhiều descriptor

Nguồn:

- [MMDB Lecture5](../../MMDB%20slides/Lecture%205%20-%20MM%20data%20model.pdf), PDFtr.53–55.
- [MMDB Lecture7](../../MMDB%20slides/Lecture%207%20-%20Vector%20database%20and%20Clustering.pdf), PDFtr.2–8.
- [Bài8 tiếng Việt](../../HeCSDL_DPT_slides/8%20-%20Truy%20van%20khong%20gian%20vecto%20va%20phan%20cum.pdf), PDFtr.4–8.

Lecture5 tr.55 có ví dụ ảnh→embedding512chiều→tìm top5 bằng cosine. Lecture7 giải thích tích vô hướng và cosine trên các vector cùng không gian đặc trưng. Với nhóm, CLIP512 và cosine đã có trong code; có thể dùng **CLIP-only** làm baseline theo nguyên lý này.

Điều này không có nghĩa slide chứng minh CLIP-only tốt nhất cho561video. Nó chỉ cho một phương pháp tìm kiếm không cần tự chọn ba hệ số trộn CLIP/HSV/LBP. HSV/LBP/Flow vẫn phải được trích và lưu đủ theo ND3/báo cáo.

Chuẩn hóa L1/L2 giải quyết quy mô biểu diễn, không tự xác định mức quan trọng ngữ nghĩa giữa các descriptor. Cosine cũng không làm hai vector128chiều và512chiều tự trở nên so sánh trực tiếp được. Ghép650chiều rồi cosine tạo ra giả định/trọng số ngầm theo cách chuẩn hóa; không được gọi đó là tự học trọng số tối ưu.

## 3. Relevance feedback/Rocchio: phương pháp rõ nhất để kết quả thích nghi

Nguồn:

- MMDB Lecture7, PDFtr.10–14, nhắc lại ở tr.31.
- Bài8 tiếng Việt, PDFtr.10–13.
- [MMDB Lecture11](../../MMDB%20slides/Lecture%2011%20-%20Indexing%20and%20Retrieval%20for%20Image.pdf), PDFtr.11 và35.

Luồng được dạy:

```text
Truy vấn ban đầu → kết quả
    → người dùng đánh dấu liên quan / không liên quan
    → điều chỉnh vector truy vấn
    → tìm lại và xếp hạng mới
```

Công thức in trong MMDB Lecture7 PDFtr.13 là:

```text
q_next = α q + β Σ(d thuộc Rel) − γ Σ(d thuộc NonRel)
```

Slide dùng **tổng**, không in mẫu số số lượng phần tử. Các giá trị điển hình được nêu là α=1, β=0.75, γ=0.15 và được ghi **tunable**. Bản tiếng Việt Bài8 PDFtr.12 dùng q_next=q+αΣRel−βΣNonRel. Hai bộ có quy ước ký hiệu hệ số khác nhau; không chép cùng tên hệ số sang code rồi cho rằng chúng đồng nhất.

### Điều phương pháp làm được

Nó dùng phản hồi để thay đổi hướng truy vấn, tiến về các kết quả được chọn và tránh các kết quả bị loại. Có thể phù hợp cho demo có nút “Liên quan/Không liên quan/Tìm lại”. Đây là cơ sở bài giảng trực tiếp cho chức năng feedback, thay vì tự gắn nhãn kết quả đầu tiên là đúng.

### Điều phương pháp không làm

Các hệ số α/β/γ ở trên là hệ số của **truy vấn gốc, phản hồi dương và phản hồi âm**. Chúng không phải w_CLIP/w_HSV/w_LBP. Rocchio không tự trả ra bộ0.9/0.1/0 tối ưu cho toàn kho, và vẫn có tham số cần chọn/đánh giá. Chính slide tr.13 cũng nêu giới hạn đối với deep embedding; không có bảo đảm cải thiện CLIP trên kho của nhóm.

### Nếu áp dụng cho hệ thống hiện tại — đề xuất triển khai, chưa được cài

- Giữ query/ảnh/vector gốc, thu nhãn trên các video và gắn với khung bằng chứng đã hiển thị.
- Thử điều chỉnh vector CLIP trong phạm vi phiên; L2-normalize sau cập nhật và xử lý trường hợp vector gần0. Không sửa các vector gốc trong MySQL như cách chỉnh document vectors ở slide14.
- Không áp thẳng công thức trừ vào HSV/LBP rồi dùng Bhattacharyya: vector histogram có thể xuất hiện số âm, trái điều kiện của độ đo/chuẩn hóa hiện tại. Muốn cập nhật histogram phải nêu rõ quy tắc xử lý và kiểm thử như một biến thể mới.
- Lưu feedback, query trước/sau, hệ số, phiên và top5 trong trace để tái lập. Ghi phiên bản policy mới; không giả rằng vector đã cập nhật vẫn là kết quả trích trực tiếp từ ảnh đầu vào.
- So với truy vấn không feedback trên các vòng thử độc lập. Không dùng chính nhãn đã đưa vào feedback làm toàn bộ bằng chứng đánh giá cuối rồi kết luận hệ thống tổng quát tốt hơn.

## 4. Độ đo histogram và trọng số cảm nhận màu

Nguồn: MMDB Lecture11 PDFtr.13,15,19,21–26,36; [Bài11 tiếng Việt](../../HeCSDL_DPT_slides/11%20-%20Chi%20so%20hoa%20va%20truy%20van%20du%20lieu%20anh.pdf) PDFtr.9–18.

### Các độ đo được nêu

L1, L2, histogram intersection, chi-square, Bhattacharyya; Lecture11 tr.36 bổ sung EMD. Đây là những cách đo độ gần của **một loại biểu diễn**, có thể đưa vào thí nghiệm so sánh. Không phải thuật toán học tầm quan trọng giữa CLIP, HSV và LBP.

Trong tr.15, Bhattacharyya được ghi là hệ số tương đồng Σsqrt(H1_i H2_i), còn hệ thống nhóm dùng khoảng cách kiểu Hellinger sqrt(1−coefficient) với chuẩn hóa phù hợp. Chi-square trên slide không có hệ số0.5 như công thức đối xứng hiện tại của nhóm. Cần giữ định nghĩa rõ theo báo cáo và policy, không đổi công thức chỉ vì cùng tên.

### Cross-bin similarity và PWH

MMDB tr.19,22 và bản Việt tr.15 trình bày:

```text
a_ij = 1 − d(color_i, color_j)/d_max
z = Hx − Hy
weighted color difference = zᵀ A z
```

PWH gán đóng góp pixel theo khoảng cách đến các màu đại diện. Mục tiêu là phản ánh các màu gần nhau về cảm nhận hoặc tránh biên ô histogram gây sai khác quá mạnh.

**A và các trọng số PWH là quan hệ giữa màu/ô màu/pixel**, không phải ba trọng số kết hợp descriptor. Nếu dùng PWH/cross-bin distance, cần định nghĩa biểu diễn/ma trận màu, so với baseline và version thay đổi; không mặc nhiên thay thế HSV128 đã chứng nhận.

### Trọng số vật thể và nền

MMDB tr.21,24 và bản Việt tr.16–17 nói về chia vùng/foreground-background và đặt đóng góp khác nhau. Đây là trọng số **vùng ảnh**. Muốn dùng cần xác định vùng/vật thể; không có công thức trong những trang đó tự học các hệ số CLIP/HSV/LBP tối ưu từ kho video.

## 5. Phân cụm, FCM và các chỉ mục

Nguồn: MMDB Lecture7 PDFtr.15–30; [Lecture6](../../MMDB%20slides/Lecture%206%20-%20Multidimensional%20data%20structures.pdf) PDFtr.2–5,75; Lecture5 PDFtr.53–56. Đối chiếu Bài8 tiếng Việt tr.14–27 và Bài7 tr.2–62.

Có K-means, hierarchical/pairwise, random-threshold clustering; MMDB bổ sung **Fuzzy c-Means** và multi-probe. FCM tính membership u_ik của **đối tượng i với cụm k**, với tổng membership theo cụm bằng1.

Membership là đại lượng tự cập nhật theo khoảng cách/tâm cụm, nhưng **không phải trọng số của từng descriptor**. Silhouette và WCSS đánh giá cấu trúc cụm, không chứng minh năm video trả về liên quan với ý định của người dùng.

K-d/quadtree/R-tree và ANN như HNSW/IVF/PQ hỗ trợ tổ chức/tìm ứng viên. Chúng không quyết định bộ trọng số nội dung. Chọn ít cụm hoặc ANN có thể bỏ ứng viên; nếu khảo sát cần đo recall của bước ứng viên so với exact baseline. Với8976khung hiện tại, chưa có lý do thay exact search chỉ để giải quyết câu hỏi trọng số.

## 6. TF–IDF và Boolean: có công thức trọng số tự động, nhưng cho từ khóa

Nguồn: [MMDB Lecture8](../../MMDB%20slides/Lecture%208%20-%20Text%20documents%20and%20Boolean.pdf), PDFtr.7–8,23–26; [Bài9 tiếng Việt](../../HeCSDL_DPT_slides/9%20-%20Du%20lieu%20van%20ban%20va%20Boolean.pdf), PDFtr.14–17.

TF–IDF tính trọng số của từ khóa theo tần suất trong tài liệu và độ phổ biến trong kho. Weighted Boolean dùng max/min/hiệu theo mô hình trình bày. Đây là ví dụ **có tính toán trọng số từ dữ liệu**, nhưng đối tượng là term/từ khóa của văn bản, không phải ba descriptor thị giác.

Không lấy TF–IDF cho ba tên “CLIP”, “HSV”, “LBP” để suy ra hệ số xếp hạng. Nếu sau này có caption/subtitle, TF–IDF/BM25/Boolean mới là nhánh text IR có đầu vào đúng; kết hợp text với ảnh lại là một quyết định khác cần đánh giá.

## 7. Phương pháp đánh giá thực sự có trong slide

Nguồn: [MMDB Lecture1](../../MMDB%20slides/Lecture%201%20-%20Introduction.pdf), PDFtr.52–68; [Bài1 tiếng Việt](../../HeCSDL_DPT_slides/Bai%201%20-%20Gioi%20thieu.pdf), PDFtr.43–51.

- Phân biệt efficiency (thời gian, tài nguyên, I/O) với effectiveness (liên quan/hữu ích).
- MMDB tr.57 nói rõ relevance/non-relevance được **chuyên gia gán nhãn**; tr.58,64 so kết quả máy với tập người đánh giá chọn.
- Tr.61–62 nhắc benchmark có nhãn, truy vấn cố định, offline/online evaluation; tr.65–68 có precision/recall, macro nhiều truy vấn và hạn chế của recall.
- Bộ tiếng Việt có precision/recall ở tr.49 và đánh giá offline/user-centered ở tr.51.

Đây là cơ sở vững nhất để chọn giữa các cấu hình trên bộ video nhóm: tạo truy vấn và nhãn liên quan, chạy cùng điều kiện, đo chỉ số, ghi kết quả. Đề yêu cầu trả5video nên áp dụng **Precision@5** là quyết định triển khai cụ thể từ khái niệm precision trong bài giảng.

Tách validation/test, tìm lưới trọng số và đánh giá độc lập là cách tổ chức thực nghiệm được đề xuất cho dự án; không tìm thấy các slide hướng dẫn trực tiếp grid search. Không đồng nhất thông số tăngtốc, silhouette hay confidence của model với relevance do người đánh giá xác định.

## 8. Các loại “trọng số” cần phân biệt

| Đại lượng | Nguồn | Nó điều khiển gì? | Có phải w_CLIP/w_HSV/w_LBP? |
| --- | --- | --- | --- |
| Hệ số Rocchio α/β/γ | MMDB7 tr.13 | Query gốc/phản hồi dương/phản hồi âm | Không |
| Cross-bin matrix A/PWH | MMDB11 tr.19,22 | Quan hệ màu/pixel/ô histogram | Không |
| Trọng số nền/vật thể | MMDB11 tr.24 | Đóng góp vùng ảnh | Không |
| Membership FCM u_ik | MMDB7 tr.27 | Mức thuộc cụm của đối tượng | Không |
| TF–IDF | MMDB8 tr.7–8 | Từ khóa trong văn bản/kho | Không |
| 0.5load+0.5RTT | MMDB4 tr.26 | Chọn máy chủ phục vụ | Không |
| Hệ số kết hợp CLIP/HSV/LBP | Cấu hình dự án ND3–4 | Điểm cuối của các descriptor khác nhau | Chính là tham số nhóm đang cần kiểm chứng |

## 9. Tìm có hệ thống những phương pháp đã trao đổi

Tìm trên văn bản mọi trang của24 PDF: `RRF/reciprocal rank`, `grid search/hyperparameter/cross validation`, `learning to rank/RankNet/LambdaMART`, `Mahalanobis/inverse variance/feature weighting`. Không có kết quả cho các nhóm đó. “Rocchio” có trong MMDB Lecture7 tr.10,13,31; bộ Việt mô tả cùng cơ chế phản hồi ở Bài8 nhưng không ghi tên Rocchio trong văn bản trích xuất.

Kết quả máy đọc: `var/course_comparison/method_search.json`. Các trang chỉ có hình không được coi là đã OCR đầy đủ; đã xem trực quan những trang công thức/biểu đồ liên quan đến các kết luận chính.

Vì vậy:

- **Có trong slide:** vector/cosine, relevance feedback/Rocchio, các độ đo histogram, PWH, phân cụm/FCM, k-NN/chỉ mục, TF–IDF và benchmark precision/recall.
- **Phần mở rộng dự án nếu sử dụng:** tự tìm lưới trọng số, RRF, learning-to-rank, học metric hay inverse-variance feature weighting. Cần nguồn và thực nghiệm riêng, không gán cho hai bộ bài giảng.

## 10. Lựa chọn cho D23 nhóm12

### Để bám sát bài giảng và giữ báo cáo

1. Giữ MySQL,16keyframe/video, HSV128/LBP10/CLIP512/Flow24 và provenance đã chứng nhận.
2. Tạo baseline **CLIP512 + cosine** theo MMDB5 tr.55 và MMDB7 tr.6–7; vẫn trích/lưu toàn bộ descriptor theo ND3.
3. Chuẩn bị bộ ảnh truy vấn có nhãn liên quan theo MMDB1 tr.57,62. Tách tìm lại nguồn khỏi tìm cùng nội dung; không chỉ dùng frame đã có trong index để báo cáo chất lượng.
4. So baseline với tổ hợp HSV/CLIP/LBP hiện tại và các cấu hình khác bằng Precision@5; giữ định nghĩa khoảng cách và gộp điểm cùng khung. Chỉ đổi cấu hình sau khi có kết quả xác minh.
5. Nếu cần điểm nhấn thuật toán trong môn học, **Rocchio feedback** là phương án có nguồn bài giảng rõ nhất: thử trên query CLIP trong phiên, giữ original/query-updated riêng, đánh giá trước/sau và không hứa chắc tốt hơn.
6. Nếu mục tiêu vẫn là tự chọn ba trọng số toàn cục, bổ sung runner validation/grid search như một phương pháp thực nghiệm của nhóm. Không có nhãn hoặc tiêu chí liên quan thì chưa thể tuyên bố bộ trọng số tìm ra là tối ưu về ngữ nghĩa.

### Mapping với code hiện tại và phần chưa làm

| Nội dung slide | Code hiện tại | Trạng thái |
| --- | --- | --- |
| Vector/cosine/độ đo histogram | `features.py`, `search.py`, `retrieval.py` | Có; chi tiết theo báo cáo ND2 |
| Video→keyframe→top5 và timecode | `building.py`, MySQL, `querying.py` | Có theo hợp đồng K16; không tự chứng nhận shot detection |
| Bằng chứng/so kết quả | `query_evidence.py`, trace/replay | Có; chỉ kiểm chứng phép tính, không thay relevance |
| Precision/recall | `evaluation.py` | Có hàm tính; thiếu bộ judgments độc lập để công bố chất lượng |
| Thu nhãn relevance | Chưa có workflow chuyên dụng | Cần bổ sung/gán thật |
| Rocchio và vòng feedback | Chưa có | Đề xuất, chưa triển khai |
| Tìm lưới trọng số/RRF/LTR | Chưa có runner/thuật toán hoàn chỉnh | Phần mở rộng, không nằm trong slide đã tìm được |
| Clustering/FCM/ANN | Chưa dùng trong truy vấn chính | Không cần thêm chỉ để tìm trọng số |

Giai đoạn5 UI đã có mã nhưng chưa nghiệm thu trình duyệt do Computer Use dừng; lần phân tích này không thay đổi trạng thái đó. Việc so sánh bài giảng không được dùng để tự đánh dấu giai đoạn UI hoặc đánh giá học thuật đã hoàn thành.
