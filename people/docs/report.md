# Báo cáo phân tích: Bộ lọc ảnh chất lượng cho entity "người"

> Ngày: 2026-10-06 · Trạng thái: phân tích yêu cầu + đề xuất hướng giải (chưa benchmark thực tế)
> Lưu ý: số liệu/giấy phép của model dưới đây lấy từ kiến thức sẵn có, **cần xác minh lại trước khi chốt**.

---

## 1. Yêu cầu

**Mục tiêu:** với mỗi entity là một người (ví dụ một người nổi tiếng), tải ~20 ảnh từ Google về, rồi **chỉ giữ lại các ảnh chất lượng nhất** để dùng làm dữ liệu. Cần một chuỗi service lọc ảnh, chạy được trên máy yếu (model nhỏ gọn).

**3 bài toán nền:**

| # | Bài toán | Bản chất kỹ thuật |
|---|----------|-------------------|
| 1 | Ảnh có người không | Object/face detection (có ≥ 1 detection) |
| 2 | Ảnh có bao nhiêu người | Detection + đếm sau lọc ngưỡng |
| 3 | 2 ảnh có cùng 1 người không | Face verification (embedding + cosine similarity) |

## 2. Nhận xét quan trọng khi phân tích

1. **3 bài toán chưa đủ cho mục tiêu "giữ ảnh tốt nhất".** Còn thiếu hai thứ:
   - **Chất lượng ảnh/khuôn mặt** (mờ, nhỏ, thiếu sáng, nghiêng mặt, bị che, watermark).
   - **Xác định danh tính "đúng"**: kết quả Google Images thường lẫn người khác (người đứng cạnh, ảnh sai). Không có nhãn gốc nên cần suy ra "ai là người chính" bằng clustering.
2. **"Có người" nên hiểu là "có mặt người"** vì mục đích là ảnh chân dung của entity. Detector toàn thân (YOLO person) cho ra ảnh có người nhưng quay lưng/quá xa, không dùng được để nhận diện. Nên dùng **face detector làm lõi**, person detector chỉ làm phụ (nếu cần ảnh toàn thân).
3. **Bài 2 (đếm) và bài 1 gộp được**: cùng một lần chạy face detector cho ra cả "có/không" lẫn số lượng. Cần ngưỡng kích thước tối thiểu để không đếm mặt nền bé xíu.
4. **Bài 3 không nên chỉ so từng cặp.** Với 20 ảnh, cách tốt hơn là tính embedding cho tất cả, tìm cụm chính (medoid), rồi giữ ảnh gần cụm đó. Đây cũng chính là cách phát hiện ảnh sai người.
5. Yêu cầu "nhỏ gọn" nên đặt con số cụ thể (xem mục 7, câu hỏi mở).

## 2B. Tách thành 3 bài toán độc lập để đánh giá riêng

Nguyên tắc: **mỗi bài có đầu vào, đầu ra, nhãn, thước đo và tập dữ liệu riêng**; chọn model cho từng bài bằng số liệu của chính bài đó, không phụ thuộc kết quả bài khác. Các mục 3–6B phía dưới (chọn ảnh tốt, gom cụm danh tính, chọn top 5) là **lớp ghép** xây trên 3 bài này, sẽ đánh giá sau khi 3 bài đã ổn.

```
Bài 1  ảnh  → có người không        (phân loại nhị phân)
Bài 2  ảnh  → có bao nhiêu người    (đếm, số nguyên)
Bài 3  2 ảnh (hoặc 2 mặt) → cùng người không   (so khớp, điểm + ngưỡng)
```

### 2B.1 Quy ước định nghĩa (cần chốt trước khi gán nhãn)

Nếu không chốt định nghĩa thì không so sánh model được, vì mỗi model "hiểu" khác nhau. Đề xuất:

| Khái niệm | Định nghĩa đề xuất |
|-----------|-------------------|
| **Người (person)** | Một người thật nhìn thấy được ít nhất phần thân trên hoặc mặt trong ảnh. Không tính tượng, tranh, hình vẽ, mascot, ảnh trong ảnh (poster/màn hình) trừ khi quy ước khác. |
| **Mặt hợp lệ (valid face)** | Mặt người thật có cạnh ngắn của bbox ≥ ngưỡng `S` (thử `S` = 32 / 48 / 64 px; báo cáo kết quả theo nhiều `S`). Mặt nhỏ hơn `S` là "nền", không tính. |
| **Nhiều người** | Đếm theo **mặt hợp lệ** (biến thể A) và theo **thân người nhìn thấy** (biến thể B). Báo cáo hai biến thể riêng, không trộn. |
| **Mặt chính (main face)** | Mặt lớn nhất; hoặc nhãn tay nếu hai mặt xấp xỉ nhau. |
| **Cùng người (bài 3)** | Cùng một danh tính thực. Ảnh cùng người khác tuổi/trang điểm vẫn tính là cùng, và gắn nhãn độ khó (xem dưới). |

### 2B.2 Một lần gán nhãn nuôi cả 3 bài

Mỗi ảnh trong tập đánh giá nội bộ gán một bộ nhãn:

| Nhãn | Dùng cho |
|------|----------|
| `person_visible_count` (số người nhìn thấy, mọi cỡ) | Bài 1 (`>0` → có người), bài 2 biến thể B |
| `valid_face_count` theo từng ngưỡng `S` (hoặc lưu bbox mặt để tính lại) | Bài 2 biến thể A, và cả bài 1 nếu định nghĩa "có mặt" |
| `main_face_bbox` + `identity_id` (mã danh tính tự đặt, vd `P_anhthu_01`) | Bài 3 |
| `image_type` (chân dung / nửa người / toàn thân / đồ họa / bìa nhạc / cảnh) | Cắt lát kết quả cho cả 3 bài |
| `hard_flags` (đeo kính râm, khẩu trang, nghiêng nặng, mờ, tối, che mặt) | Cắt lát kết quả cho cả 3 bài |

Từ `identity_id` sinh được **tập cặp bài 3 tự động**: mọi cặp cùng `identity_id` là *cùng người*, khác `identity_id` là *khác người*. Chỉ cần gán nhãn từng ảnh một lần, không phải gán nhãn từng cặp.

**Quy mô tối thiểu đề xuất:** 40–60 entity × ~20 ảnh ≈ 800–1200 ảnh. Chọn có chủ đích: entity trùng tên nhiều người (kiểu Anh Thư), entity không phải người (kiểu ADC), nổi tiếng/ít nổi tiếng, đủ các `category`. Gán nhãn kép ~10% để đo độ đồng thuận giữa người gán nhãn.

### 2B.3 Bài 1: Ảnh có người không?

- **Đầu vào/ra:** ảnh → `có/không` kèm điểm tin cậy.
- **Cách giải:** detector (face và/hoặc person), "có người" = tồn tại ít nhất một detection qua ngưỡng tin cậy và (tùy chọn) kích thước.
- **Thước đo:** precision, recall, F1, PR-AUC; đường PR theo ngưỡng tin cậy; **tỉ lệ dương tính giả** trên ảnh đồ họa/bìa nhạc/đồ ăn và **tỉ lệ bỏ sót** trên ảnh nhìn nghiêng/mặt nhỏ. Cắt lát theo `image_type` và `hard_flags`.
- **Dữ liệu công khai để kiểm chứng sơ bộ:** COCO (class `person`), WIDER FACE (mặt), CrowdHuman, Open Images. Chỉ để đối chiếu độ chính xác trước, kết luận cuối vẫn dựa trên tập nội bộ vì ảnh web Việt khác phân phối.
- **Model ứng viên:** YuNet, SCRFD (0.5g/2.5g/10g), RetinaFace-MobileNet, BlazeFace/MediaPipe, UltraFace; person: YOLOv8n/YOLO11n, YOLOX-nano/tiny, RT-DETR nhỏ, EfficientDet-Lite0.
- **Biến thể cần so:** "có mặt" (face detector) vs "có người" (person detector) vs "hoặc cả hai". Chọn biến thể theo mục tiêu cuối; nhưng đánh giá riêng.

### 2B.4 Bài 2: Có bao nhiêu người?

- **Đầu vào/ra:** ảnh → số nguyên `N` (và danh sách bbox để kiểm tra).
- **Cách giải:** cùng detector bài 1 nhưng thêm NMS, ngưỡng kích thước `S`, ngưỡng tin cậy. Không cần model đếm đám đông, trừ khi ảnh có rất đông người.
- **Thước đo:** **độ chính xác khớp đúng** (exact match), **MAE**, **tỉ lệ sai ≤ 1**, ma trận nhầm lẫn (0 / 1 / 2 / 3+); với bbox: precision/recall ở IoU 0.5. Quan trọng nhất cho dự án: độ chính xác của nhánh "đúng một người" (1 vs ≥2), vì quyết định giữ ảnh và chọn mặt chính phụ thuộc vào đó.
- **Dữ liệu công khai:** WIDER FACE (đếm mặt, có nhãn mức độ khó), CrowdHuman (đếm người; có nhãn thân đầy đủ và thân nhìn thấy), COCO.
- **Điểm cần theo dõi:** hai biến thể đếm (mặt hợp lệ vs thân người) và độ nhạy với ngưỡng `S`; đếm sai thường đến từ mặt nền nhỏ, ảnh poster/màn hình, mặt bị cắt.
- **Phụ thuộc:** dùng chung detector với bài 1 được, nhưng **ngưỡng tối ưu cho bài 1 và bài 2 khác nhau**, nên chọn ngưỡng độc lập cho từng bài.

### 2B.5 Bài 3: Hai ảnh có cùng một người không?

- **Đầu vào/ra:** hai ảnh (hoặc hai mặt đã căn chỉnh) → điểm tương đồng (cosine) → `cùng/khác` theo ngưỡng.
- **Hai cách đánh giá, tách bạch:**
  1. **Embedder thuần:** dùng bbox/landmarks nhãn tay hoặc từ một detector cố định chuẩn, để đo riêng chất lượng embedding.
  2. **Từ đầu đến cuối:** detector + căn chỉnh + embedder, để đo tác động của detector và mặt nhỏ.
- **Thước đo:** ROC, **AUC**, **EER**, **TAR @ FAR = 1e-2 / 1e-3 / 1e-4**, độ chính xác tại ngưỡng đã chọn. Tính riêng theo độ khó cặp (khác tuổi, khác pose, ảnh nhỏ, che mặt) và theo nhóm danh tính.
- **Ngưỡng:** chọn trên tập hiệu chuẩn rồi **khóa lại**, đánh giá trên tập kiểm tra tách riêng (không chọn ngưỡng trên chính dữ liệu báo cáo).
- **Dữ liệu công khai:** LFW, CFP-FP, AgeDB-30, CALFW, CPLFW (các bộ kiểm tra chuẩn trong hệ sinh thái InsightFace), IJB-B/IJB-C để thử nghiệm khó hơn. Chưa có bộ công khai đủ đại diện cho mặt Việt trong ảnh web, nên **tập cặp nội bộ (sinh từ `identity_id`) là bắt buộc** để kết luận.
- **Model ứng viên:** SFace, MobileFaceNet (buffalo_s/sc), EdgeFace, ArcFace R50/R100 (mốc tham chiếu cao), AdaFace, FaceNet (mốc tham chiếu thấp). Dự án nghiên cứu nên dùng được trọng số InsightFace.
- **Lưu ý:** cặp sai-người khó nhất trong dữ liệu của bạn thường là **người cùng gia đình hoặc cùng giới/độ tuổi** (như mẹ-con ở entity Anh Thư), nên cần đưa nhóm cặp này vào tập đánh giá riêng.

### 2B.6 Thước đo hiệu năng dùng chung cho cả 3 bài

Đo cùng một máy, cùng điều kiện, để so sánh công bằng:

| Chỉ số | Cách đo |
|--------|---------|
| Độ trễ | median và p95 ms/ảnh, sau khi khởi động (warm-up), với 1 luồng và N luồng CPU; tách thời gian đọc ảnh/resize và thời gian chạy model |
| Kích thước | dung lượng file model (fp32, fp16, int8 nếu có) |
| RAM | RAM đỉnh khi chạy (đo bằng công cụ hệ điều hành) |
| Độ phân giải đầu vào | ghi rõ (vd 640x640 so với 320x320), vì ảnh hưởng lớn tới cả độ chính xác lẫn tốc độ |
| Môi trường | ONNX Runtime CPU, phiên bản, số luồng, thông số máy; ghi trong báo cáo kết quả |

Kết quả mỗi bài ra thành **bảng**: model × (chỉ số chính xác chính, độ trễ p95, kích thước, RAM), cộng biểu đồ đánh đổi (độ chính xác so với độ trễ) để chọn model ở điểm hợp lý.

### 2B.7 Thứ tự làm và tiêu chí xong của từng bài

| Bài | Làm trước gì | Tiêu chí xong |
|-----|-------------|---------------|
| 1 | Chạy các detector trên tập nội bộ và một tập con COCO/WIDER để đối chiếu | Chọn được 1–2 model có recall cao trên ảnh người và tỉ lệ dương tính giả thấp trên ảnh đồ họa/cảnh |
| 2 | Dùng bbox từ bài 1, chỉnh ngưỡng `S` và NMS | Độ chính xác nhánh "đúng một người" vượt mục tiêu bạn đặt; MAE chấp nhận được |
| 3 | Cố định detector chuẩn, thử các embedder | Chọn được embedder và ngưỡng đạt TAR@FAR mục tiêu trên tập cặp nội bộ, đo cả khi mặt nhỏ/nghiêng |

Các bài 1 và 2 có thể làm song song; bài 3 độc lập với hai bài kia nếu dùng bbox nhãn tay ở chế độ embedder thuần.

### 2B.8 Điều cần bạn chốt cho phần này

1. "Có người" ở bài 1: **có mặt**, **có thân người**, hay **một trong hai**?
2. Đếm ở bài 2: theo **mặt hợp lệ**, **thân người**, hay báo cáo cả hai?
3. Ngưỡng kích thước mặt tối thiểu `S` ban đầu (đề xuất thử 32/48/64 px)?
4. Mục tiêu số (vd recall bài 1 ≥ 98%, độ chính xác "một người" bài 2 ≥ 95%, TAR@FAR=1e-3 bài 3 ≥ 90%) hay để kết quả benchmark quyết định?
5. Ai gán nhãn và có đủ công để làm ~1000 ảnh? (nếu không, thu nhỏ còn ~400–500 ảnh và dùng thêm tập công khai.)

## 2C. Dataset công khai gần với dữ liệu mẫu, để chạy thử trước

Chưa có bộ công khai nào giống hệt dữ liệu của bạn (ảnh web thô, lẫn sai người, lẫn đồ họa, tiêu đề trang đi kèm). Nhưng ghép vài bộ lại được một bộ **gần giống**, đủ để chạy thử nghiệm trước khi gán nhãn dữ liệu thật. Thông tin dưới đây tra từ web ngày 2026-10-06; **link tải, điều khoản và tình trạng còn tải được cần kiểm tra lại trước khi dùng**.

### 2C.1 Ứng viên gần nhất: VN-Celeb (mặt người nổi tiếng Việt Nam)

- Khoảng **23.105 mặt của 1.020 người**, trung bình ~20 ảnh/người, **cùng quy mô với dữ liệu của bạn**.
- Thu thập bằng đúng cách của bạn: lấy tên từ Wikipedia tiếng Việt/Wikidata, tìm trên Google Images, detect mặt bằng MTCNN, rồi **dọn nhiễu bằng tay**.
- Nhãn theo danh tính; mặt đã crop ở 128x128 và 182x182; công khai cho mục đích học tập/nghiên cứu (theo bài giới thiệu trên Viblo, điều khoản chi tiết chưa rõ).
- Nguồn: [Viblo: VN-Celeb dữ liệu khuôn mặt người nổi tiếng Việt Nam](https://viblo.asia/p/vn-celeb-du-lieu-khuon-mat-nguoi-noi-tieng-viet-nam-va-bai-toan-face-recognition-Az45bG9VKxY).
- **Hạn chế:** đã dọn sạch (không còn ảnh sai người), chỉ còn mặt crop nhỏ (không có ảnh toàn cảnh, toàn thân, không có ảnh không người). Dùng tốt cho **bài 3** và để mô phỏng nhiễu, **không dùng cho bài 1, bài 2**. Lưu ý: "Vietnam-Celeb" là bộ khác (giọng nói), đừng nhầm.

### 2C.2 Bảng theo từng bài

| Bài | Dataset | Dùng để làm gì | Lưu ý |
|-----|---------|----------------|-------|
| 1, 2 | **COCO** (class `person`, và ảnh không có người) | Kiểm tra "có người" và đếm; có sẵn ảnh **không có người** làm mẫu âm (cảnh, đồ ăn, vật thể) | Ảnh phương Tây, không phải chân dung |
| 1, 2 | **WIDER FACE** | Phát hiện/đếm mặt, nhiều mức khó (mặt nhỏ, che, đông) | Thiên về cảnh đông người |
| 1, 2 | **CrowdHuman** | Đếm thân người, có nhãn thân đầy đủ và phần nhìn thấy | Cảnh đông; để thử bài 2 biến thể thân người |
| 1, 2 | **Open Images** (class Person, ảnh không người) | Thêm đa dạng ảnh web | Nhãn chưa đầy đủ ở một số ảnh |
| 3 | **LFW, CFP-FP, AgeDB-30, CALFW, CPLFW** | Chuẩn so sánh embedder với số liệu đã công bố | Gần bão hòa ở LFW; CPLFW/CFP-FP khó hơn |
| 3 | **IJB-B / IJB-C** | Thử khó hơn (ảnh/video không ràng buộc) | Cần đăng ký xin dữ liệu |
| 3 | **VN-Celeb** | Kiểm tra embedder trên **mặt Việt** | Xem 2C.1 |
| 3, nhiễu | **FaceScrub** (141k mặt của 695 người, tìm bằng search engine) | Mô phỏng ảnh tìm từ web, có nhiễu | Giấy phép CC-BY-NC; nhóm người nổi tiếng phương Tây |
| 3, nhiễu | **IMDb-Face** (~1,7 triệu mặt, 59 nghìn người, đã dọn tay từ 2 triệu ảnh thô) | Thử với dữ liệu "thô vs đã dọn" để thấy tác động của nhiễu ([IMDb-Face](https://github.com/fwang91/IMDb-Face), bài [The Devil of Face Recognition is in the Noise](https://arxiv.org/pdf/1807.11649)) | Chỉ nghiên cứu |
| 3, huấn luyện | **VGGFace2** (3,31 triệu ảnh, 9.131 người, tải cần tài khoản), **WebFace42M/260M**, **Glint360K** | Chủ yếu để **huấn luyện** model; không cần cho bài của bạn trừ khi muốn fine-tune ([WebFace260M](https://arxiv.org/pdf/2103.04098)) | Rất lớn; VGGFace2 tôi nhớ từng có giai đoạn bị gỡ tải, cần kiểm tra lại tình trạng |
| 3, chất lượng | Bộ dùng cho đánh giá chất lượng mặt (FIQA) như **XQLFW** (LFW đã chia theo chất lượng) | Thử các thước đo chất lượng ở mục 5 | Cần kiểm tra |
| — | **MS-Celeb-1M** | Không nên dùng: đã bị gỡ vì vấn đề riêng tư | |

### 2C.3 Cách ghép "bộ giả lập" gần giống dữ liệu mẫu

Dựng một bộ nhỏ có **nhãn đúng sẵn**, mô phỏng đủ các ca khó thấy trong CSV:

1. Lấy ~100 người từ **VN-Celeb** (chủ yếu) và vài chục từ FaceScrub/IMDb-Face làm "entity". Mỗi người ~12 ảnh thật.
2. **Chèn nhiễu có kiểm soát** để mỗi entity thành ~20 ảnh:
   - 2–4 ảnh của **người khác** (lấy từ người khác trong cùng bộ; chọn cả người cùng giới/độ tuổi để khó hơn),
   - 1–3 ảnh **không có người** từ COCO/Open Images (đồ ăn, cảnh, vật),
   - 1–3 ảnh **đồ họa/bìa/biểu đồ** (có thể lấy từ ảnh trong dữ liệu của bạn có nhãn "đồ họa", hoặc từ các bộ ảnh minh họa công khai),
   - bản sao **nén thấp/cắt khác** của chính ảnh trong bộ để mô phỏng "nhiều crop cùng một trang".
3. Mô phỏng ca "tên trùng nhiều người" (như Anh Thư): gộp ảnh của 2–3 người vào **một entity** có tên chung, nhãn đúng là cụm lớn nhất hoặc `ambiguous`.
4. Mô phỏng ca `no_person` (như ADC): entity chỉ gồm ảnh không người/đồ họa.
5. Giữ **nhãn gốc** của mọi ảnh (ảnh đúng/sai/không người/đồ họa) để đo tự động, không cần gán tay.

Bộ giả lập cho phép: so detector, so embedder, thử ngưỡng, và kiểm tra logic chọn cụm/`ambiguous`/`no_person` trước khi tốn công gán nhãn dữ liệu thật.

### 2C.4 Giới hạn cần nhớ

- Bộ giả lập **sạch và dễ hơn dữ liệu thật**: ảnh VN-Celeb đã được dọn và crop, thiếu ảnh nền/toàn thân, thiếu tiêu đề trang. Kết quả trên bộ giả lập là **cận trên**; vẫn cần tập nhãn tay ~400–1000 ảnh thật (mục 2B.2) để kết luận cuối.
- Tín hiệu văn bản (tên trong tiêu đề/URL, domain) **không có trong bộ công khai**; chỉ thử được trên dữ liệu của bạn.
- Mỗi bộ có điều khoản riêng (nghiên cứu/phi thương mại, CC-BY-NC). Dự án của bạn là nghiên cứu nên thường phù hợp, nhưng nên đọc điều khoản từng bộ.

## 3. Kiến trúc đề xuất (lớp ghép, xây trên 3 bài ở mục 2B)

> Cập nhật: dữ liệu mẫu không có ảnh tham chiếu, nên bước [4] dưới đây được thay bằng chấm điểm cụm danh tính như mục 6B.3 (mục 6A.2 chỉ áp dụng nếu sau này có anchor).

```
Ảnh thô (~20)
  │
  ├─ [0] Lọc cơ bản: định dạng, độ phân giải tối thiểu, tỉ lệ khung hình
  │       + loại trùng lặp (perceptual hash / embedding gần giống)
  │
  ├─ [1] Face detection + landmarks 5 điểm        → bài toán 1 & 2
  │       (0 mặt → loại; >1 mặt → xử lý theo chính sách)
  │
  ├─ [2] Chấm chất lượng từng ảnh                 → mục 5
  │       (kích thước mặt, độ nét, pose, sáng, che)
  │
  ├─ [3] Align mặt → embedding                    → bài toán 3
  │
  ├─ [4] Clustering danh tính → chọn cụm chính
  │       (loại ảnh khác người)
  │
  └─ [5] Xếp hạng theo điểm tổng hợp, giữ top-K, đảm bảo đa dạng (pose/ánh sáng)
```

Chính sách cho ảnh nhiều mặt (cần chốt): (a) loại hẳn, (b) giữ nếu mặt của entity là mặt lớn nhất/chính, rồi crop. Với dữ liệu train/reference thì (a) hoặc crop là an toàn nhất.

## 4. Ứng viên model theo từng bài toán

### 4.1 Bài 1 & 2 — Phát hiện và đếm người/mặt

**Face detector (khuyến nghị làm lõi):**

| Model | Điểm mạnh | Lưu ý |
|-------|-----------|-------|
| **YuNet** (OpenCV Zoo) | Rất nhỏ (~vài chục nghìn tham số, ~300KB), chạy CPU nhanh, có 5 landmarks, giấy phép MIT | Độ chính xác thấp hơn SCRFD ở mặt nhỏ/khó |
| **SCRFD** (InsightFace; 0.5g / 2.5g / 10g) | Cân bằng tốc độ–độ chính xác tốt, có landmarks | Trọng số InsightFace thường giới hạn **phi thương mại** — kiểm tra |
| **RetinaFace** (MobileNet0.25) | Phổ biến, nhiều bản ONNX | Nặng hơn YuNet |
| **UltraFace / Ultra-Light** (~1MB) | Cực nhẹ | Không có landmarks, kém ở mặt nhỏ |
| **MediaPipe Face Detector (BlazeFace)** | Rất nhẹ, tối ưu mobile | Tốt cho mặt gần; yếu với mặt nhỏ/xa |

**Person detector (tùy chọn, nếu cần "có người" theo nghĩa toàn thân):**

| Model | Lưu ý |
|-------|-------|
| YOLOv8n / YOLO11n (class `person`) | Nhỏ (~3M tham số), nhanh, nhưng giấy phép **AGPL-3.0** — cần cân nhắc nếu dùng thương mại |
| YOLOX-nano/tiny | Giấy phép Apache-2.0 |
| MediaPipe Object Detector (EfficientDet-Lite0) / SSD-MobileNet | Nhẹ, Apache-2.0, độ chính xác trung bình |
| RT-DETR nhỏ, RF-DETR | Mới hơn, nặng hơn các lựa chọn trên |

**Đếm:** đếm số detection sau khi áp (a) ngưỡng confidence, (b) NMS, (c) kích thước mặt tối thiểu (vd cạnh ngắn ≥ 5–8% cạnh ngắn ảnh, hoặc ≥ 60–80 px). Không cần model đếm đám đông chuyên dụng.

### 4.2 Bài 3 — So khớp khuôn mặt

| Model | Ghi chú |
|-------|---------|
| **SFace** (OpenCV Zoo) | Nhỏ, Apache-2.0, đủ tốt cho lọc thô; ngưỡng cosine tham khảo ~0.36 |
| **MobileFaceNet / ArcFace-MobileFaceNet** (InsightFace `buffalo_s`/`buffalo_sc`) | ~1M tham số, ~4–13MB; giấy phép trọng số cần kiểm tra |
| **EdgeFace** (EPFL, 2023) | Thiết kế cho edge, độ chính xác cao so với kích thước — kiểm tra license |
| **ArcFace R50/R100** (`buffalo_l`, Glint360K) | Chính xác nhất nhóm này nhưng lớn (R50 ~ 90MB+) — dùng làm baseline "vàng" để so sánh |
| **AdaFace**, **MagFace** | Chịu ảnh chất lượng thấp tốt hơn; MagFace còn cho **độ lớn embedding ~ chất lượng mặt** |
| **FaceNet (InceptionResnetV1)** | Cũ, nặng hơn, kém hơn ArcFace-family |

Cách so khớp: cosine similarity giữa embedding đã L2-normalize. **Ngưỡng phụ thuộc model** → phải tự hiệu chuẩn trên dữ liệu thật của mình (vd chọn ngưỡng tại FPR ~1e-3 trên tập có nhãn nhỏ), không dùng ngưỡng mặc định mù quáng.

## 5. Thiết kế chấm điểm chất lượng ảnh

Chia **hard filter** (loại thẳng) và **soft score** (xếp hạng).

**Hard filter:**
- Không có mặt, hoặc nhiều mặt mà không xác định được mặt chính.
- Mặt quá nhỏ (cạnh mặt < ~80–112 px sau khi crop gốc; 112 là đầu vào chuẩn của ArcFace).
- Pose quá lệch (|yaw| > ~45–60°), ước lượng từ 5 landmarks hoặc model head-pose nhỏ.
- Embedding xa cụm danh tính chính (ảnh sai người).
- Trùng lặp gần như tuyệt đối.

**Soft score (gợi ý trọng số, cần tinh chỉnh):**

| Tiêu chí | Cách đo | Công cụ |
|----------|---------|---------|
| Độ nét vùng mặt | Variance of Laplacian trên crop mặt (không phải toàn ảnh — nền bokeh sẽ đánh lừa) | OpenCV |
| Kích thước mặt | Cạnh mặt / độ phân giải | Từ detector |
| Pose | Yaw/pitch/roll | Landmarks hoặc 6DRepNet/img2pose |
| Phơi sáng | Histogram vùng mặt (cháy/tối) | OpenCV |
| Che khuất (kính đen, khẩu trang, tay) | Model nhận diện occlusion hoặc dùng độ tin cậy detector/landmark làm proxy | tùy chọn |
| **Face Image Quality (FIQA)** | Điểm học sẵn dự báo mức hữu ích cho nhận diện | **MagFace** (độ lớn embedding), **CR-FIQA**, **SER-FIQ**, **SDD-FIQA**, **FaceQAN** |
| Chất lượng thẩm mỹ chung | Điểm IQA không tham chiếu | BRISQUE, NIQE (nhẹ); MUSIQ, CLIP-IQA (nặng hơn) |
| Watermark/chữ chèn/ảnh stock | Heuristic hoặc classifier nhỏ | tùy chọn |
| Độ gần cụm danh tính | cosine tới medoid | từ bước embedding |

**Gợi ý hiện thực tối thiểu:** điểm = trọng số của (FIQA hoặc độ nét + kích thước mặt + pose + độ gần medoid). Bắt đầu đơn giản, đo lại, rồi mới thêm tiêu chí.

**Đa dạng:** sau khi xếp hạng, tránh giữ 10 ảnh gần giống nhau (cùng buổi chụp). Dùng greedy selection: chọn ảnh điểm cao nhất, các ảnh sau phải cách ảnh đã chọn một khoảng tối thiểu trong không gian embedding/hash.

## 6. Xử lý "chọn đúng người" khi không có ảnh tham chiếu

1. Detect + embed mọi mặt hợp lệ.
2. Cluster (agglomerative / DBSCAN trên cosine, hoặc đơn giản: tìm ảnh có tổng similarity cao nhất với các ảnh còn lại = medoid).
3. Cụm lớn nhất = entity chính (giả định: trong 20 kết quả, đa số đúng người).
4. Giữ ảnh có similarity tới cụm ≥ ngưỡng đã hiệu chuẩn.
5. Nếu có sẵn 1–3 ảnh chuẩn (ví dụ từ Wikipedia/Wikidata) → dùng làm anchor thay medoid, đáng tin hơn.

Rủi ro: entity ít ảnh đúng (<50% kết quả) hoặc tên trùng nhiều người → medoid sai. Cần cảnh báo khi cụm chính quá nhỏ/quá rời rạc.

## 6A. Học từ tính năng "People" của iPhone (Apple Photos)

Nguồn chính: bài của Apple Machine Learning Research, [Recognizing People in Photos Through Private On-Device Machine Learning](https://machinelearning.apple.com/research/recognizing-people-photos) (cũng có tóm tắt trên [AppleInsider](https://appleinsider.com/articles/21/07/23/photos-in-ios-15-can-identify-people-by-their-upper-bodies)). Apple không công bố model hay code, nhưng mô tả khá rõ cách làm, và phần lớn tái hiện được bằng model mã nguồn mở.

### 6A.1 Cách Apple làm

1. **Detect cả mặt lẫn thân trên** bằng một mạng cho ra bbox hai loại, rồi ghép mặt với thân trên tương ứng (dựa trên diện tích, vị trí, phần giao nhau của bbox).
2. **Hai mạng embedding riêng**: một cho mặt, một cho thân trên (quần áo, dáng người). Embedding cùng người thì gần nhau.
3. **Gom cụm hai lượt (agglomerative):**
   - *Lượt 1, bảo thủ (ưu tiên precision):* kết hợp khoảng cách mặt và thân trên. Khớp thân trên chỉ được phép trong **cùng một "moment"** (cùng thời điểm/địa điểm), vì quần áo chỉ ổn định trong thời gian ngắn.
   - *Lượt 2, mở rộng (tăng recall):* chỉ dùng embedding mặt, gom hierarchical qua các moment khác nhau, median linkage, có lấy mẫu ngẫu nhiên để chạy nhanh.
4. **Lọc quan sát kém** (mặt mờ, ngoài phân phối, false positive) trước khi cho vào cụm, để tránh làm "bẩn" cụm.
5. **Huấn luyện chịu che khuất** (kể cả khẩu trang giả), và kiểm tra công bằng giữa các nhóm nhân khẩu.
6. Chạy on-device, embedding mặt dưới ~4ms trên Neural Engine; có cập nhật cụm tăng dần.

Điều làm iPhone "hiệu quả" không phải một model thần kỳ, mà là: **lượt chặt trước rồi mới nới**, **dùng thêm tín hiệu thân trên khi mặt không rõ**, và **lọc đầu vào kém**.

### 6A.2 Áp dụng khi có ảnh tham chiếu (tùy chọn; chế độ chính hiện là mục 6B)

Khác Apple ở chỗ bạn **có ảnh gốc làm mỏ neo**, nên không cần gom cụm tự do mà gom theo mỏ neo. Pipeline đề xuất:

```
Ảnh tham chiếu ──► face embedding (anchor, có thể nhiều ảnh → lấy trung bình/giữ riêng)

Mỗi ảnh ứng viên của entity (~20):
  1. Detect mặt + người; bỏ quan sát kém (lọc kiểu Apple)
  2. Lượt 1 – chắc chắn: cosine(mặt, anchor) ≥ ngưỡng chặt  → "chắc là đúng người"
  3. Lượt 2 – mở rộng (transitive): mặt chưa đạt ngưỡng chặt nhưng giống
     mạnh với một ảnh đã được chấp nhận ở lượt 1 (ngưỡng nới, median linkage
     trên nhóm đã chấp nhận) → thêm vào
  4. Ảnh toàn thân/mặt nhỏ/quay đi: so embedding thân trên (ReID) với ảnh đã
     chấp nhận *trong cùng bộ 20 ảnh* (tương đương "cùng moment" của Apple:
     cùng buổi chụp/cùng nguồn trang) → chỉ chấp nhận nếu rất giống
  5. Chấm điểm chất lượng (mục 5), chuẩn hóa theo loại ảnh, chọn top 5 theo quota
```

Lợi ích: lượt 2 cứu được ảnh góc nghiêng/ánh sáng khó mà mặt-so-với-anchor không đủ giống; lượt 4 xử lý đúng yêu cầu "cần cả toàn thân" mà face embedding đơn lẻ không làm được.

**Thân trên / toàn thân (person re-identification):** các model ReID nhỏ như OSNet (x0.25, x0.5, x1.0), thư viện torchreid; tính chất giống Apple là dựa vào quần áo nên **chỉ tin trong cùng nguồn/cùng buổi chụp**. Đây là điểm yếu: ảnh Google của cùng entity ở các sự kiện khác nhau mặc đồ khác nhau, nên ReID chỉ nên là tín hiệu phụ, không dùng làm quyết định duy nhất.

### 6A.3 Ước lượng khối lượng (cần xác minh ở P1)

Với 60k–80k ảnh trên CPU, giả sử ~100–250 ms/ảnh tính cả detect + embedding + chất lượng (số này chỉ là phỏng đoán, phụ thuộc model và máy):
- 1 tiến trình: ≈ 2–6 giờ. Chạy đa tiến trình (4–8 core) còn khoảng vài chục phút đến ~1 giờ.
- So khớp với anchor chỉ là phép nhân vector, chi phí không đáng kể; không cần thư viện vector DB ở quy mô này (mỗi entity chỉ ~20 ảnh).
- Cần: cache embedding ra đĩa (npy/parquet) để đổi ngưỡng mà không chạy lại model, ghi log lý do loại từng ảnh, resume khi dừng giữa chừng.
- Ảnh tải về dễ có file lỗi/định dạng lạ/ảnh rất lớn: bước đọc ảnh cần chống lỗi và resize trước khi vào model.

### 6A.4 Một tính năng khác của iPhone: gom ảnh "giống nhau" (không theo người)

Ngoài People, Photos còn nhóm ảnh trùng/gần giống (burst, ảnh chụp liên tiếp) và gợi ý "ảnh đẹp nhất". Apple mô tả ít hơn, nhưng cách tương đương mở nguồn là: **embedding hình ảnh toàn cục** (CLIP/DINOv2 bản nhỏ, hoặc MobileNet đặc trưng) + khoảng cách cosine để tìm cặp gần giống, **perceptual hash (pHash/dHash)** cho ảnh trùng tuyệt đối/chỉ đổi kích thước, rồi giữ một ảnh tốt nhất trong mỗi nhóm. Đây là bước dedup/đa dạng ở mục 5, không thay thế bước nhận diện người.

## 6B. Phân tích dữ liệu mẫu (CSV bạn gửi) và thiết kế không cần ảnh tham chiếu

### 6B.1 Cấu trúc dữ liệu

Cột: `entity_id, slug, canonical_name, category, kind_hint, query, local_path, sha256, image_url, source_url, source_domain, description, width, height, bytes, crawled_at, has_face, face_count, face_error, face_area_pct, from_db`.

- Mỗi dòng là một ảnh. `image_url` là bản đã lưu trên CDN (cloudfront); `local_path` đang trống nên cần bước **tải ảnh về** (có `sha256` để kiểm tra toàn vẹn và loại trùng tuyệt đối).
- `source_url` + `description` là **trang web chứa ảnh và tiêu đề trang**, không phải nhãn ảnh. Ảnh lấy từ trang bài báo/profile chứ không phải lưới Google Images thuần túy.
- `has_face, face_count, face_error, face_area_pct` đang trống: đây chính là các cột pipeline sẽ điền (`face_area_pct` có lẽ là tỉ lệ diện tích mặt lớn nhất so với ảnh; cần bạn xác nhận định nghĩa).
- Mẫu gồm 3 entity đầy đủ (khoảng 12, 20, 17 ảnh) và 1 ảnh lẻ; category gồm `athletes`, `celeb`, `businessman`.

### 6B.2 Những gì dữ liệu mẫu cho thấy

| # | Quan sát trong mẫu | Hệ quả thiết kế |
|---|-------------------|-----------------|
| 1 | **Entity "ADC" (athletes)**: 12 ảnh gồm bộ chuyển đổi analog-to-digital, đảng chính trị African Democratic Congress, video kỹ thuật trên YouTube. Từ khóa "ADC" bị hiểu sai nghĩa, có thể 0 ảnh là người. | Có entity **không có ảnh hợp lệ nào**. Pipeline phải trả trạng thái `no_person`/`unresolvable` chứ không cố chọn đủ 5 ảnh. |
| 2 | **Entity "Anh Thư"**: trùng tên nhiều người (siêu mẫu Anh Thư, Mạc Anh Thư, Đào Anh Thư kênh YouTube, Phan Ngọc Anh Thư hot girl), lại có ảnh **con trai** của siêu mẫu. | Gom cụm có thể ra **nhiều cụm gần ngang nhau**. Cần trạng thái `ambiguous` cho người duyệt, không được âm thầm chọn một cụm. Medoid thuần túy là rủi ro. |
| 3 | **Entity "Angie Vũ Hà"**: nhiều bìa album, ảnh vuông 500x500, thumbnail bài báo đã cắt, một ảnh Pinterest lệch tên ("Angie Wolf"), và một số trang có nội dung nhạy cảm hoặc tin bắt giữ. | Cần lọc **đồ họa/bìa đĩa/ảnh có chữ** và **NSFW**; ảnh nhỏ và ảnh vuông bìa nhạc thường chất lượng thấp cho mục tiêu của bạn. |
| 4 | **Entity "Anh Trần Đăng Tuấn cha đẻ Cơm có thịt"**: ảnh duy nhất là "Bữa cơm miền Tây nhà Út Tình", nhiều khả năng là ảnh đồ ăn/cảnh, không phải người. | Query dạng mô tả dài có thể không ra người; kiểm tra "có người" (bài toán 1) là hàng rào cần thiết. |
| 5 | **Nhiều ảnh cùng `source_url`** (danviet 3 ảnh, znews 2, thanhnien 2, dantri 2, monolithicpower 2, dewesoft 2). | Giống "moment" của Apple: ảnh cùng trang thường cùng người/sự kiện, nhưng cũng là **các lần cắt khác nhau của cùng một ảnh gốc** → dedup bằng hash cảm nhận và **giới hạn tối đa 1–2 ảnh/trang** khi chọn top 5. Cũng là nơi hợp lý để dùng ReID thân trên. |
| 6 | `source_domain` có loại rõ: báo (vnexpress, thanhnien, dantri), wiki người nổi tiếng (nguoinoitieng.tv), nền tảng nhạc (spotify, beatport, apple music), IMDb, trang lạ/rác. | Dùng làm **tiên nghiệm tin cậy theo domain** (IMDb/báo lớn/profile > trang lạ); có thể học dần trọng số từ dữ liệu. |
| 7 | **`description` (tiêu đề trang) thường chứa tên** (vd "Angie Vu Ha - IMDb", "Siêu mẫu Anh Thư: ..."), một số lệch tên. | Tín hiệu văn bản rẻ và mạnh: tên đã chuẩn hóa (bỏ dấu, chữ thường) có xuất hiện trong title/URL không? Dùng để chọn cụm danh tính đúng. |
| 8 | Kích thước đa dạng: 500x500 đến 2000x2000, ngang và dọc; có `webp`, `png`, `jpg`. Ảnh >1000px mà chỉ vài chục KB thường là đồ họa hoặc nén nặng. | Hard filter theo độ phân giải tối thiểu và `bytes/pixel` bất thường. |
| 9 | Tên tiếng Việt, người Việt/châu Á là chính. | **Kiểm tra độ chính xác của detector/embedder trên khuôn mặt Việt** ở P1, không chỉ tin điểm benchmark phương Tây. |
| 10 | Có `from_db` = 1 và cột `has_face` đã tồn tại. | Có thể hệ thống phía trước đã có bước gán nhãn mặt; cần biết để so sánh làm baseline. |

### 6B.3 Chọn đúng người khi không có ảnh tham chiếu

Chuyển từ "so với ảnh gốc" sang "**chấm điểm từng cụm danh tính**":

```
Mỗi entity (~20 ảnh):
  1. Tải ảnh; loại ảnh lỗi / trùng sha256 / trùng pHash; loại đồ họa, ảnh quá nhỏ, NSFW.
  2. Detect mặt + người. Lọc quan sát kém (mặt mờ/nhỏ). Embedding mặt chính.
  3. Gom cụm (agglomerative, cosine, ngưỡng hiệu chuẩn).
  4. Chấm điểm mỗi cụm = f(
        số ảnh khác source_url (không đếm lặp cùng trang),
        tỉ lệ ảnh có tên trong title/URL,
        tiên nghiệm domain,
        chất lượng trung bình / độ chặt cụm )
  5. Quyết định:
        - một cụm vượt trội rõ rệt        -> chọn làm "người của entity"   (ok)
        - hai cụm điểm sát nhau           -> ambiguous (người duyệt)
        - không cụm nào đủ điểm / 0 mặt   -> no_person / unresolvable
  6. Trong cụm đã chọn: chấm chất lượng (mục 5), chuẩn hóa theo loại ảnh,
     tối đa 1-2 ảnh/trang, chọn top 5 theo quota (đề xuất 3 cận mặt / 1 nửa người / 1 toàn thân).
  7. Ảnh toàn thân/mặt nhỏ: ghép vào entity bằng ReID thân trên với ảnh đã chọn cùng source_url.
```

**Đầu ra mỗi entity:** trạng thái (`ok / ambiguous / no_person / too_few`), danh sách ảnh giữ kèm `rank`, điểm thành phần và lý do loại các ảnh còn lại; điền `has_face`, `face_count`, `face_error`, `face_area_pct` cho từng ảnh.

**Có thể mạnh hơn sau này:** lấy anchor tự động cho người nổi tiếng (ảnh chân dung trên Wikipedia/Wikidata), hoặc dùng "ảnh hạt giống" là ảnh có tên trong title + đúng một mặt lớn + domain đáng tin; hoặc dùng CLIP kiểm tra "ảnh chân dung của người tên X". CLIP không đáng tin để phân biệt tên người ít nổi tiếng nên chỉ là tín hiệu phụ.

### 6B.4 Điều chỉnh kế hoạch đánh giá (P1)

- Dựng **tập vàng nhỏ ~30–50 entity** chọn có chủ đích, đủ ca khó: tên trùng nhiều người (kiểu Anh Thư), entity không phải người (kiểu ADC), entity nổi tiếng nhiều ảnh, entity ít nổi tiếng, mỗi `category`.
- Nhãn tay cho từng ảnh: *đúng người / sai người / không có người / đồ họa / ảnh tốt hay không*; và cho entity: *ok / ambiguous / no_person*.
- Đo thêm: tỉ lệ entity được gán đúng trạng thái; tỉ lệ ảnh sai người lọt vào top 5; độ đa dạng của top 5.

### 6B.5 Điểm cần lưu ý thêm

- **Nội dung nhạy cảm:** mẫu có tiêu đề kiểu tin bắt giữ và trang nội dung người lớn. Cần bộ lọc NSFW (classifier nhỏ) và chính sách cho entity là người dính tin tiêu cực.
- **Bản quyền/riêng tư:** ảnh từ trang báo và trang thương mại; dự án nghiên cứu phi thương mại, nhưng nên lưu `source_url` cho mọi ảnh giữ lại để truy nguồn.
- **Query chưa tốt** (như "vận động viên ADC") là lỗi phía thu thập, pipeline lọc chỉ cứu được một phần. Nên báo ngược danh sách entity `no_person`/`ambiguous` để sửa query hoặc `kind_hint` (cột này đang trống hoặc "unknown").

## 7. Quyết định đã chốt & câu hỏi còn mở

**Đã chốt (cập nhật 2026-10-06):**

| Mục | Quyết định | Hệ quả |
|-----|-----------|--------|
| Môi trường | **CPU only**, có thể chạy trên mobile. Không cần tối ưu riêng cho thiết bị biên (edge). | Dùng ONNX Runtime CPU; ưu tiên model int8/fp16 nhỏ. Mobile ở đây chỉ nên hiểu là "model đủ nhẹ", chưa cần TFLite/CoreML/NNAPI ở giai đoạn đầu. |
| RAM / dung lượng | Chưa ước được | Không đặt ngưỡng cứng; **đo thực tế ở P1** rồi mới quyết (ghi cả kích thước file và RAM đỉnh). |
| Độ trễ | Chưa chốt, **so sánh nhiều phương pháp** | P1 phải đo ms/ảnh (median, p95) trên cùng một máy CPU cho mọi tổ hợp detector × embedder. |
| Giấy phép | **Nghiên cứu, phi thương mại** | Được dùng InsightFace weights (SCRFD, buffalo_*, ArcFace) và YOLO (AGPL). Mở rộng danh sách ứng viên so với ban đầu. Nếu sau này thương mại hóa phải thay lại. |
| Nhiều mặt | **Chọn mặt chính** | Mặt chính = mặt lớn nhất/gần cụm danh tính nhất. Xem lưu ý bên dưới. |
| Loại ảnh | **Cần cả chân dung, nửa người và toàn thân** | Cần thêm person detector (YOLO) bên cạnh face detector; xem mục 7.1. |
| K cuối | **Top 5**, không ràng buộc pose cố định | Vẫn nên đa dạng hóa nhẹ để 5 ảnh không gần như trùng nhau. |
| Ảnh tham chiếu | **Cập nhật 2026-10-06: dữ liệu mẫu cho thấy không có ảnh tham chiếu** | Chế độ chính chuyển thành **không anchor**: gom cụm + tín hiệu văn bản (tên trong tiêu đề/URL). Anchor chỉ là tùy chọn nếu sau này có. Xem mục 6B. |
| Quy mô & kiểu chạy | **Batch/CLI**, ~60k–80k ảnh (≈ 3–4k entity nếu 20 ảnh/entity) | Ưu tiên throughput, đa tiến trình, cache embedding, resume khi lỗi. Ước lượng thời gian ở mục 6A.3. |

### 7.1 Hệ quả của "cần cả toàn thân" + "crop mặt chính"

Hai yêu cầu này cần làm rõ để không mâu thuẫn:
- **Mặt chính dùng để nhận diện danh tính**, không nhất thiết là thứ được lưu. Đề xuất: **giữ ảnh gốc**, đồng thời lưu thêm bbox/crop mặt nếu cần. Nếu crop và vứt phần còn lại thì ảnh toàn thân mất ý nghĩa.
- Ảnh toàn thân thường có mặt nhỏ (vd 40–60 px), nên **ngưỡng kích thước mặt phải theo loại ảnh** (chân dung: nghiêm; toàn thân: nới lỏng) và embedding sẽ kém tin cậy hơn. Nên gắn nhãn loại ảnh (cận mặt / nửa người / toàn thân) dựa trên tỉ lệ bbox người/ảnh và tỉ lệ mặt/người.
- Với ảnh toàn thân mặt quá nhỏ để verify: có thể (a) so với cụm danh tính bằng ngưỡng mềm hơn, hoặc (b) tạm giữ nếu chỉ có một người trong ảnh và ảnh đến từ cùng kết quả tìm kiếm — cần chốt ở P1 bằng dữ liệu thật.
- Chấm điểm phải **chuẩn hóa theo loại ảnh**, nếu không ảnh toàn thân luôn thua ảnh cận mặt và top 5 toàn chân dung. Gợi ý: xếp hạng trong từng nhóm, rồi chọn top 5 theo quota (vd 3 cận mặt + 1 nửa người + 1 toàn thân), quota cấu hình được.

### 7.2 Giải thích câu "quy mô, batch hay online"

Ý câu hỏi là để quyết định cách đóng gói và tối ưu, vì hai hướng khác nhau khá nhiều:

| | Batch (chạy script một lần cho nhiều entity) | Online (API, gọi từng entity/ảnh) |
|---|---|---|
| Ví dụ | Có danh sách 500 entity, chạy qua đêm, lưu kết quả ra thư mục | App gửi 20 ảnh, chờ vài giây nhận lại 5 ảnh |
| Điều quan trọng | **Throughput** (tổng thời gian), dùng đa tiến trình, có thể chấp nhận model chậm hơn | **Độ trễ mỗi request**, giữ model nạp sẵn trong RAM, giới hạn đồng thời |
| Độ phức tạp | Thấp: CLI/script | Cao hơn: FastAPI, hàng đợi, xử lý lỗi |
| Chạy trên mobile | Ít gặp | Có thể nếu chạy ngay trên máy |

Và **số entity** (10 hay 10.000) ảnh hưởng việc có cần cache embedding, lưu kết quả vào DB hay không.

Đề xuất: **làm CLI/batch trước** (đủ cho nghiên cứu và benchmark), thiết kế lõi là một hàm thuần `filter_images(list_ảnh) -> top5 + lý do`, sau này bọc thêm API nếu cần. Bạn chỉ cần cho biết sơ bộ: *dự kiến xử lý khoảng bao nhiêu entity* và *có cần người dùng chờ kết quả trực tiếp không*.

### 7.3 Câu hỏi còn mở
1. Ngưỡng RAM / dung lượng / độ trễ: sẽ rút ra từ kết quả P1.
2. Ảnh tham chiếu: hiện coi là không có. Nếu về sau có (kể cả tự lấy từ Wikipedia/Wikidata cho người nổi tiếng) thì dùng làm anchor theo mục 6A.2.
3. Quota giữa cận mặt / nửa người / toàn thân trong top 5 (mặc định đề xuất 3/1/1).

## 8. Đề xuất triển khai theo giai đoạn

| Giai đoạn | Nội dung | Kết quả |
|-----------|----------|---------|
| **P0 – Baseline** | Dựng pipeline bằng ONNX Runtime: YuNet (hoặc SCRFD-0.5g) + SFace/MobileFaceNet + Laplacian + medoid. Chạy thử trên ~10 entity | Pipeline end-to-end chạy được |
| **P1 – Benchmark (chạy riêng từng bài theo 2B)** | Tạo tập đánh giá nhỏ có nhãn tay (~10 entity × 20 ảnh, gắn nhãn: có người / số mặt / đúng người / "ảnh tốt"). So sánh detector (YuNet vs SCRFD vs RetinaFace) và embedder (SFace vs MobileFaceNet vs EdgeFace vs ArcFace-R50 làm tham chiếu). Đo precision/recall, latency, kích thước | Bảng chọn model có số liệu |
| **P2 – Chất lượng** | Thêm FIQA (MagFace/CR-FIQA), pose, dedup, đa dạng; tinh chỉnh trọng số theo nhãn "ảnh tốt" | Bộ xếp hạng ổn định |
| **P3 – Service hóa** | Đóng gói API (FastAPI) hoặc CLI, cache embedding, log lý do loại từng ảnh | Service dùng được |

Chỉ số đánh giá:
- Detection: precision/recall theo ngưỡng; độ chính xác đếm (exact-match, MAE).
- Verification: ROC, TAR@FAR=1e-3, ngưỡng đã hiệu chuẩn.
- Pipeline: tỉ lệ ảnh sai người lọt qua, tỉ lệ ảnh tốt bị loại nhầm, **top-K có được người thật đánh giá là "tốt" hay không** (chỉ số quan trọng nhất).
- Vận hành: ms/ảnh trên máy mục tiêu, kích thước model, RAM.

## 9. Rủi ro & lưu ý

- **Thiên lệch nhân khẩu học:** các model nhận diện mặt có sai số khác nhau theo sắc tộc, giới tính, độ tuổi; ngưỡng cần kiểm tra trên nhóm đối tượng thực tế của bạn.
- **Ảnh cũ/trẻ/già, trang điểm, ảnh cắt ghép/AI-generated** có thể đánh lừa verification; ảnh deepfake/AI không được lọc bởi pipeline này.
- **Pháp lý & đạo đức:** tải ảnh từ Google có thể vướng bản quyền; embedding khuôn mặt là dữ liệu sinh trắc học (GDPR, và các luật tương tự). Cần xác định mục đích sử dụng và quyền dùng dữ liệu, đặc biệt nếu entity không phải người của công chúng.
- **Giấy phép model** (InsightFace, YOLO/Ultralytics): hiện dùng được vì dự án nghiên cứu phi thương mại; nếu sau này thương mại hóa phải thay model hoặc xin giấy phép.
- Con số kích thước/độ chính xác ở trên là ước lượng; cần đo thực tế ở P1.

## 10. Kết luận ngắn

- Gộp bài 1 + 2 thành **một face detector nhỏ** (khởi đầu: YuNet hoặc SCRFD-0.5g), bổ sung person detector chỉ khi thực sự cần ảnh toàn thân.
- Bài 3 dùng **embedding nhỏ (SFace / MobileFaceNet / EdgeFace)** và áp dụng cho **cả tập 20 ảnh qua clustering/medoid**, không chỉ so từng cặp.
- Phần "lọc ảnh tốt" cần thêm **chấm điểm chất lượng mặt** (độ nét vùng mặt, kích thước, pose, FIQA) và **loại trùng/đa dạng hóa** — đây là phần tạo giá trị thực sự cho mục tiêu của bạn.
- Bước tiếp theo: trả lời các câu hỏi ở mục 7 (đặc biệt môi trường chạy và giấy phép), sau đó làm P0 + P1 để chọn model bằng số liệu thay vì phỏng đoán.
