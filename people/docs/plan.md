# Kế hoạch: gắn cờ approved / rejected cho ảnh entity người

> Cập nhật: 2026-10-08 (đợt 2 — dữ liệu `approved-results (3).csv`, 3 người cùng làm)
> Liên quan: [golden-guideline.md](golden-guideline.md) · [report-entities-for-mentor.md](report-entities-for-mentor.md) · [report.md](report.md)
>
> Tài liệu này dùng chung cho cả nhóm. Phần [§8 Cấu hình máy](#8-cấu-hình-máy-mỗi-người-tự-điền) mỗi người tự điền.

## 0. Mục tiêu

Với mỗi ảnh trong [approved-results (3).csv](../data/approved-results%20(3).csv), điền 2 cột:

| Cột | Giá trị |
|-----|---------|
| `flag` | `approved` / `rejected` |
| `reject_reason` | câu tiếng Việt, chỉ điền khi `rejected` (xem §4) |

Tiêu chí duyệt: [golden-guideline.md](golden-guideline.md). Giữ nguyên mọi cột gốc khác.

**Không làm:** không sửa metadata (`canonical_name`, `category`, `query`…); không dùng VLM/agent; không coi `has_face`/`face_count` của file là đúng (vẫn detect lại vì cần bbox + embedding từng mặt).

## 1. Phạm vi và chia việc

Dữ liệu: **14.788 ảnh, 1.609 entity**, 8 category (`singer` 3.657 · `athletes` 2.233 · `politicer` 2.222 · `celeb` 2.207 · `businessman` 1.525 · `scientist` 1.029 · `writer` 984 · `historic` 931).

Chia 3 phần, cắt trọn entity. **Số dưới đây là thứ tự bản ghi, KHÔNG tính dòng tiêu đề** (bản ghi 1 = dòng 2 của file CSV):

| Người | Bản ghi | Dòng trong file | Số ảnh | Entity cuối của phần |
|-------|---------|-----------------|--------|----------------------|
| Linh | 1 – 4936 | 2 – 4937 | 4.936 | `le-thi-hoang-ngoc` (Lê Thị Hoàng Ngọc) |
| Thành | 4937 – 9857 | 4938 – 9858 | 4.921 | `orange-ca-si-kol` (Orange (ca sĩ/KOL)) |
| Kiên | 9858 – 14788 | 9859 – 14789 | 4.931 | `y-nhi-hai-ngoai` (Ý Nhi (hải ngoại)) |

Đã kiểm: cả 3 mốc đều cắt đúng ranh giới entity, không có entity nào bị tách giữa 2 người. Phần của Kiên: 534 entity, bắt đầu từ `pham-anh-khoa`.

> **Lưu ý khi dùng công cụ:** nối dữ liệu bằng `entity_id + sha256`, **không dùng số dòng**. Đợt 1 mentor đã xoá/thêm dòng giữa các phiên bản file làm lệch toàn bộ số dòng.

Cột `cluster` của mentor (`ambiguous` = chưa xác định được cụm, 2.337 ảnh = 15,8%) dùng làm **cảnh báo**, không phải căn cứ loại.

## 2. Chạy theo đợt 1000 ảnh + ngưỡng escalate

**Quy định từ đợt này:** chia phần của mình thành các đợt **1000 ảnh** (cắt trọn entity), duyệt xong đợt nào chốt đợt đó.

> **Nếu một đợt 1000 ảnh có tỉ lệ `rejected` > 5% → dừng và escalate** cho mentor trước khi làm tiếp.

Lý do có ngưỡng này: đợt 1 (`approved-results (1).csv`) tỉ lệ rejected là **36,3%** (2.422/6.664) — rất cao, phần lớn do entity sai người hoặc trùng tên. Dữ liệu đợt 2 kỳ vọng đã được mentor lọc kỹ hơn nên nếu vẫn vượt 5% thì **khả năng cao là lỗi dữ liệu nguồn, không phải việc của người duyệt** → báo sớm để mentor xử lý thay vì duyệt tay hết.

Khi escalate, gửi kèm: số đợt, khoảng bản ghi, tỉ lệ rejected, phân bố `reject_reason`, và danh sách entity sai nhiều nhất (mẫu báo cáo: [report-entities-for-mentor.md](report-entities-for-mentor.md)).

## 3. Kiến trúc

```
Ảnh ──► [A] Trích đặc trưng (chạy 1 lần, cache lại)
            face detector + embedder · đặc trưng không cần model
           │
           ▼
        [B] Bộ lọc 2 chiều
           │  ├─ auto-reject : ca SAI chắc chắn      (precision ≥ 98%)
           │  ├─ gợi ý approved: ca ĐÚNG chắc chắn   (precision ≥ 98%)
           │  └─ còn lại → to_review
           ▼
        [C] Người duyệt: toàn bộ to_review + xác nhận nhóm gợi ý
            + mẫu ngẫu nhiên 10% của auto-reject để đo sai số
```

Không có tầng VLM/agent. Text/collage/AI-image detector **để sau**, chỉ thêm nếu mẫu kiểm tra cho thấy lọt nhiều.

## 4. Mã lý do và câu `reject_reason`

Dùng đúng câu của nhóm để 3 file merge được với nhau:

| Mã nội bộ | `reject_reason` ghi ra file |
|-----------|----------------------------|
| `wrong_person`, `name_mismatch` | Không cùng người |
| `no_person` | Không rõ người |
| `not_clear`, `not_prominent`, `hard_to_identify` | Nhiều chi tiết thừa |
| `sensitive` | Ảnh nhạy cảm |
| `unresolved` | Chưa xác định được |

Nhiều lý do cùng lúc → nối bằng `; `. Ảnh `approved` để trống.

> 2 câu "Ảnh nhạy cảm" và "Chưa xác định được" là nhóm mình tự thêm (bản của Thành đợt 1 chưa có case tương ứng) — cần thống nhất lại với mentor nếu muốn đồng bộ toàn dự án.

## 5. Kết quả đợt 1 và các điểm phải sửa

Đo trên 6.664 ảnh đã gán nhãn tay của đợt 1 (`scope-labels-DuongVanKien-2026-10-08.csv`):

| Nhóm | Số ảnh | Precision | Recall | Nhận xét |
|------|--------|-----------|--------|----------|
| auto-reject | 1.262 | **99,0%** (1.250/1.262) | 51,6% | Đạt mục tiêu, nhưng **bỏ sót 1.172 ảnh sai** |
| gợi ý approved | 2.512 | **96,9%** (2.433/2.512) | 57,4% | **Chưa đạt 98%**, **bỏ sót 1.809 ảnh đúng** |
| to_review (duyệt tay) | 2.890 | — | — | 1.797 approved + 1.093 rejected |

### 5.1. Vấn đề 1 — rule tên chưa lọc hết ca sai

Trong **902 ảnh `name_mismatch` bị bỏ sót**, nguyên nhân phân ra:

| Nguyên nhân | Số ảnh | Hướng xử lý đợt 2 |
|-------------|--------|-------------------|
| Tên **không xuất hiện** trong tiêu đề | 602 | Siết ngưỡng (xem §6.1) |
| Tên **khớp chính xác cả dấu** nhưng là người khác | 276 | Dùng `category` để phát hiện trùng tên khác lĩnh vực (§6.2) |
| Tên khớp khi bỏ dấu, **khác dấu thanh** | 24 | Rule dấu thanh, **nhưng có ngoại lệ bắt buộc** (§6.1) |

**Ngoại lệ bắt buộc — entity không có dấu thanh:** nếu `canonical_name` của entity vốn không có dấu thanh thì khi bỏ dấu nó khớp với nhiều tên khác → **rule không được tự loại, phải để người review**. Ví dụ thật từ đợt 1:

- entity `Phan Thanh` ↔ tiêu đề "Phan **Thành**" (người khác)
- entity `Tôn Thất Tư` ↔ tiêu đề "Tôn Thất **Tùng**" (người khác)
- entity `Thiếu Sơn` ↔ tiêu đề "thiếu **son** môi" (không phải tên người)

**Ngược lại, KHÔNG áp rule cho:** tên bị **đảo thứ tự** hoặc **viết chưa đầy đủ** (vd "Ngọc Trinh" ↔ "Trinh Ngọc", "Phạm Anh Khoa" ↔ "Anh Khoa") — các dạng này rất hay là cùng người, rule sẽ **loại nhầm**.

### 5.2. Vấn đề 2 — rule quan hệ gần như không hoạt động

Đo thực tế trên đợt 1:

| Cách nhận quan hệ | Số ảnh khớp | Precision nếu auto-reject |
|-------------------|-------------|---------------------------|
| Từ quan hệ xuất hiện bất kỳ đâu trong tiêu đề | ~900 | 30–44% |
| Từ quan hệ **gắn ngay trước tên** entity | 10 | 40% |

→ **Cả hai đều không dùng được để auto-reject.** Hai nguyên nhân:

1. Tiêu đề về người thân thường **vẫn có ảnh entity** trong đó: "Vợ Phạm Trưởng không ghen…" → ảnh chụp cả hai → thực tế `approved`.
2. Khớp nhầm từ vựng: "**Võ** Thu Hà" bị hiểu là "vợ", "thiếu **son** môi" thành "Thiếu Sơn", "**bà**/**cha**/**bố**" trùng vô số ngữ cảnh khác.

**Quyết định đợt 2:** từ quan hệ **chỉ dùng để gắn cảnh báo và đẩy ảnh lên đầu hàng đợi duyệt**, tuyệt đối không auto-reject. Không đầu tư thêm vào rule này.

### 5.3. Vấn đề 3 — chưa dùng `category` và `query`

Phân tích trường `query` trên dữ liệu đợt 2: `query` = **chức danh tiếng Việt theo category + canonical_name**, theo bảng cố định:

| `category` | Cụm trong `query` | Từ tiếng Việt gần nghĩa cần coi là KHỚP |
|------------|-------------------|------------------------------------------|
| `singer` | nghệ sĩ | ca sĩ, nhạc sĩ, rapper, NSND, NSƯT, nghệ sĩ, ca nhạc sĩ, diva |
| `athletes` | vận động viên | VĐV, cầu thủ, tiền vệ, hậu vệ, thủ môn, HLV, võ sĩ, kỳ thủ, tay đua |
| `politicer` | chính khách | bộ trưởng, thứ trưởng, chủ tịch, bí thư, đại biểu, ĐBQH, thủ tướng, chủ nhiệm |
| `businessman` | doanh nhân | CEO, chủ tịch HĐQT, tổng giám đốc, TGĐ, nhà sáng lập, founder, shark |
| `scientist` | nhà khoa học | GS, PGS, TS, tiến sĩ, giáo sư, viện trưởng, bác sĩ, nhà nghiên cứu |
| `writer` | nhà văn | nhà thơ, nhà báo, tác giả, dịch giả, nhà phê bình, biên kịch |
| `celeb` | chân dung | diễn viên, người mẫu, hoa hậu, á hậu, MC, KOL, hot girl, streamer, influencer |
| `historic` | lịch sử | vua, hoàng đế, danh nhân, tướng, thi hào, chí sĩ, nhà cách mạng |

**Vì `query` chỉ là template sinh từ `category`, nó KHÔNG phải tín hiệu độc lập** — giá trị thật của nó là cho ta bảng từ vựng chức danh ở trên. Dùng để:

- **Tăng recall ca đúng:** tiêu đề có chức danh **khớp** category + tên khớp chính xác → cộng điểm, hạ yêu cầu về `sim` (nới precision cho nhóm gợi ý approved).
- **Phát hiện trùng tên khác lĩnh vực:** tên khớp chính xác nhưng chức danh trong tiêu đề thuộc **category khác hẳn** → cảnh báo mạnh, đẩy lên đầu hàng đợi. Đây là nhóm 276 ảnh bị bỏ sót ở §5.1. Ví dụ đợt 1: `Phan Thanh` (`politicer`) nhưng tiêu đề là "Nhà toán học Phan Thành Nam" (`scientist`).

> **Lưu ý:** bảng từ vựng là **gần nghĩa, không chính xác** — "singer ↔ nhạc sĩ" khớp, nhưng một `celeb` vẫn có thể được gọi là "ca sĩ". Vì vậy:
> - Chức danh **khớp** → chỉ dùng để **cộng điểm** (nới ca đúng), an toàn.
> - Chức danh **lệch** → chỉ **cảnh báo**, KHÔNG auto-reject (trừ khi kèm điều kiện ở §6.2).

## 6. Rule đợt 2

Ngưỡng cụ thể **chốt lại sau khi đo trên golden đợt 2**, các con số dưới đây là điểm khởi đầu lấy từ đợt 1.

### 6.1. Nhóm auto-reject (mục tiêu precision ≥ 98%)

| # | Điều kiện | Lý do |
|---|-----------|-------|
| R1 | Tiêu đề chứa **biến thể dấu thanh** của tên (khớp khi bỏ dấu, khác khi có dấu) **VÀ** `canonical_name` **có dấu thanh** | `name_mismatch` |
| R2 | Tiêu đề **không có tên** VÀ `sim` tới mặt anchor < 0,25 | `wrong_person` |
| R3 | Tiêu đề **không có tên** VÀ `sim` tới cụm chính < 0,30 | `wrong_person` |
| R4 | Ảnh tải lỗi / không đọc được | Không rõ người |

Thay đổi so với đợt 1:
- **R1 thêm điều kiện chặn:** `canonical_name` phải có dấu thanh. Entity không dấu thanh (`Phan Thanh`, `Tôn Thất Tư`, `Te`, `Tnhan`) → **không auto-reject, chuyển người review**.
- **R2/R3 siết ngưỡng** để giảm 602 ca bỏ sót — nhưng chỉ siết tới mức giữ precision ≥ 98% trên golden.
- **Bỏ** rule quan hệ khỏi nhóm auto-reject (§5.2).

**So khớp tên:** so **có dấu** để phát hiện xung đột; so **bỏ dấu** chỉ để biết tên có xuất hiện. Tiêu đề không chứa tên **không** phải là xung đột. Trước khi so: bỏ ngoặc đơn, bỏ tiền tố chức danh (`NTK`, `nhạc sĩ`, `ca sĩ`, `GS`, `TS`, `NSND`, `NSƯT`, `vua`, `nhóm`…). Chuẩn hoá vị trí dấu (`Hoà` ≡ `Hòa`).

> 2 lỗi chuẩn hoá tên đã phát hiện ở đợt 1 **phải sửa trước khi chạy**: tiền tố `NTK` chưa được bỏ, và `Thái Hoà`/`Thái Hòa` bị coi là khác nhau.

### 6.2. Nhóm gợi ý approved (mục tiêu precision ≥ 98%, tăng recall)

Đợt 1 đạt 96,9% / recall 57,4%. Đợt 2 **nới điều kiện** để tăng recall, vì dữ liệu mới chất lượng cao hơn nên cluster kỳ vọng tốt hơn:

| Điều kiện | Đợt 1 | Đợt 2 (đề xuất) |
|-----------|-------|-----------------|
| Tên khớp chính xác trong tiêu đề | bắt buộc | bắt buộc |
| `sim` tới cụm chính | ≥ 0,50 | ≥ 0,45 |
| `sim` tới anchor | ≥ 0,50 | ≥ 0,45 |
| Độ vượt trội của cụm chính | ≥ 2,0 | ≥ 1,8 |
| Kích thước mặt chính | ≥ 64px | ≥ 56px |
| `cluster` ≠ `ambiguous` | bắt buộc | bắt buộc |
| **Chức danh trong tiêu đề khớp `category`** | — | **mới: cho phép nới `sim` xuống 0,40** |
| **Chức danh lệch hẳn category** | — | **mới: loại khỏi nhóm gợi ý → to_review** |

Nhóm `historic` (tranh, tượng, ảnh cũ) dùng ngưỡng riêng, lỏng hơn — embedder kém với loại ảnh này.

### 6.3. Nhóm cảnh báo (không tự quyết, chỉ sắp xếp)

Đẩy lên đầu hàng đợi duyệt: `cluster=ambiguous` · entity không có anchor · nhiều mặt · mặt < 2% diện tích · từ quan hệ trong tiêu đề · **chức danh lệch category** · tiêu đề có từ khoá nhạy cảm (bắt, còng, khởi tố, xét xử, tòa, biểu tình…).

Nhạy cảm loại sự kiện (bắt giữ, tòa án, biểu tình, bạo lực) **chỉ tính khi chính ảnh thể hiện** → lớp B không nhìn được nội dung này, nên từ khoá tiêu đề chỉ cảnh báo, **không tự loại**.

## 7. Các giai đoạn

### G0 — Chuẩn bị
- Đọc [golden-guideline.md](golden-guideline.md). Sửa 2 lỗi chuẩn hoá tên ở §6.1.
- Cập nhật đường dẫn trong `people/tools/*.py` cho khớp cấu trúc thư mục mới (`people/data`, `people/scope`, `people/models`).

### G1 — Golden đợt 2
- Chọn **30–40 entity** trong phần của mình (`tools/select_golden.py`, seed cố định), phân tầng theo `category`, `face_count`, `face_area_pct`.
- Chủ động đưa ca khó: **entity không có dấu thanh**, tên dễ trùng, trùng tên khác lĩnh vực, nhóm nhạc, `historic`.
- Gán nhãn theo guideline → dùng để **chốt ngưỡng** §6.1/§6.2, không phải huấn luyện model.
- **Chỉ một người gán mỗi phần** → thay gán kép bằng **tự kiểm tra**: sau vài ngày gán lại mù ~10% ảnh, so độ nhất quán.
- Nhãn golden cũng là **nhãn cuối** cho các ảnh đó (công cụ tự prefill, không duyệt lại).

### G2 — Lớp A: trích đặc trưng
- Tải ảnh từ `image_url`, kiểm `sha256`, resume khi dừng. Ảnh tải lỗi → `rejected` · Không rõ người.
- Cache: bbox + landmarks + tin cậy + kích thước **mọi mặt**, embedding mọi mặt, độ nét, pose, độ phân giải, tên xuất hiện trong `description`/`source_url` (có dấu + bỏ dấu), chức danh trong tiêu đề, loại domain.
- **Danh tính theo entity:** gom cụm mặt (single-link, chỉ nối cross-image), chọn cụm chính theo (số ảnh + số ảnh có tên khớp), hoặc đánh entity `unresolved`.
- Gom nhóm ảnh trùng (sha256, pHash) để duyệt một lần; **không loại** ảnh trùng.

### G3 — Lớp B: đo và chốt ngưỡng
- Chạy rule §6 trên golden, đo **precision từng rule** (mục tiêu ≥ 98%) và **recall**.
- Tách kết quả theo `category` — ngưỡng riêng cho `historic`.
- Chỉ bật auto-reject cho rule đạt ≥ 98%. Rule chưa đạt → chuyển sang nhóm cảnh báo.

### G4 — Chạy thật theo đợt 1000 ảnh
1. Chạy A → B cho đợt 1000 ảnh.
2. Hàng đợi duyệt = toàn bộ `to_review` (sắp theo entity, cảnh báo lên đầu) + **mẫu 10%** của auto-reject.
3. Duyệt. Nhóm gợi ý approved: xem nhanh rồi xác nhận hàng loạt.
4. **Kiểm ngưỡng escalate 5%** (§2) trước khi sang đợt sau.
5. Mẫu kiểm tra sai nhiều hơn mục tiêu → chỉnh ngưỡng, chạy lại B (đặc trưng đã cache), duyệt lại.

### G5 — Merge và báo cáo
- Merge nhãn vào bản sao file gốc với 2 cột `flag` + `reject_reason` (§4), nối bằng `entity_id + sha256`.
- Báo cáo: tỉ lệ tự động, precision ước lượng từ mẫu kiểm tra, phân bố `reject_reason`, danh sách entity có vấn đề (theo mẫu [report-entities-for-mentor.md](report-entities-for-mentor.md)).

## 8. Cấu hình máy (mỗi người tự điền)

Hiệu năng ảnh hưởng trực tiếp tới số luồng chạy model. **Quan trọng:** đợt 1 chạy với số luồng = số luồng CPU (22) thì **chậm gấp ~10 lần** so với 6 luồng (3,4 s/ảnh → 0,33 s/ảnh), vì các phép toán ONNX nhỏ bị chi phí đồng bộ luồng lấn át.

| | Linh | Thành | Kiên |
|---|---|---|---|
| CPU | *(điền)* | *(điền)* | Intel Core Ultra 7 155H (16 nhân / 22 luồng) |
| RAM | *(điền)* | *(điền)* | 32 GB |
| GPU | *(điền)* | *(điền)* | Intel Arc tích hợp (không dùng) |
| Ổ cứng trống | *(điền)* | *(điền)* | *(cần ~8 GB cho ~5.000 ảnh)* |
| `intra_op_num_threads` | *(tự đo)* | *(tự đo)* | 6 |
| Tốc độ trích đặc trưng | *(tự đo)* | *(tự đo)* | ~0,33 s/ảnh |

**Cách tự đo số luồng tối ưu:** chạy thử 100 ảnh với `intra_op_num_threads` = 4, 6, 8, rồi lấy giá trị nhanh nhất. Thường bằng **số nhân hiệu năng (P-core)**, không phải tổng số luồng.

Thời gian dự kiến cho ~4.900 ảnh: tải ~1–2 giờ (phụ thuộc mạng), trích đặc trưng ~30 phút ở 0,33 s/ảnh.

## 9. Rủi ro

| Rủi ro | Giảm thiểu |
|--------|-----------|
| Rule loại nhầm ảnh tốt mà không ai thấy | Chỉ bật rule ≥ 98% trên golden; kiểm mẫu 10% auto-reject khi chạy thật |
| Entity **không có dấu thanh** bị loại nhầm | Chặn R1 cho nhóm này, bắt buộc người review (§6.1) |
| Nới ngưỡng ca đúng làm lọt ảnh sai | Đo lại precision nhóm gợi ý trên golden trước khi bật; giữ mốc 98% |
| Trùng tên khác lĩnh vực lọt vào approved | Dùng `category` + chức danh tiếng Việt để cảnh báo (§5.3) |
| Mạng tới CDN bị ngắt giữa lúc tải | Retry nhiều vòng có giãn cách; lỗi > 30% thì đợi rồi thử lại; resume được |
| 3 người gán lệch nhau | Dùng chung guideline + bảng `reject_reason` (§4); escalate khi vượt 5% |
| Embedder kém với mặt Việt / ảnh cũ / tranh | Ngưỡng riêng cho `historic`; đo tách theo `category` |
| Entity bị loại gần hết ảnh | Báo cáo entity còn dưới N ảnh approved (§G5) |

## 10. Quyết định đã chốt

| Chủ đề | Quyết định |
|--------|-----------|
| VLM / agent | **Bỏ**. Ca khó chuyển thẳng người duyệt |
| Lớp B | Tự loại **và** tự gợi ý approved, cả hai cần precision ≥ **98%** |
| Đợt chạy | **1000 ảnh/đợt**; rejected > 5% → **escalate** |
| Rule quan hệ | **Chỉ cảnh báo**, không auto-reject (precision thực đo 40%) |
| Rule dấu thanh | Auto-reject, **trừ** entity `canonical_name` không có dấu thanh |
| Tên đảo / chưa đầy đủ | **Không** áp rule (hay là cùng người, dễ loại nhầm) |
| `category` / `query` | Tham chiếu gần nghĩa: khớp → cộng điểm ca đúng; lệch → cảnh báo |
| Ưu tiên | Chất lượng hơn số lượng |
| Nhạy cảm | Lộ vùng nhạy cảm; bạo lực; sự kiện chính trị nhạy cảm; bắt giữ/còng tay/tòa án **chỉ khi chính ảnh thể hiện** |
| Khó nhận diện | Che khuất nhiều, đồ che kín, ghép ảnh, ảnh AI, chỉnh sửa/hiệu ứng/nhiễu quá nhiều |
| Nhiều người | Entity nổi bật, dễ nhận ra → approved; chung chung → rejected |
| Nhóm nhạc | Approved nếu có tương đối đủ thành viên |
| Lịch sử | Tranh, tượng, ảnh cũ được approved (ngưỡng riêng) |
| Ảnh trùng | Giữ tất cả |
| Ảnh tải lỗi | Rejected · Không rõ người |
| Tên entity | **Rule cứng**: không khớp hoặc không chắc → không auto-approve |
| Nối dữ liệu | `entity_id + sha256`, **không** dùng số dòng |
