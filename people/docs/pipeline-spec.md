# Đặc tả model & pipeline — để 3 người chạy giống nhau

> Cập nhật: 2026-10-08 · Dùng cho đợt `approved-results (3).csv`
> Liên quan: [plan.md](plan.md) (quy trình, chia việc) · [golden-guideline.md](golden-guideline.md) (tiêu chí duyệt)
>
> **Mục đích:** để cả 3 người dùng **cùng model, cùng tham số, cùng định dạng output**, nhờ đó kết quả so sánh được và merge được. Mọi con số trong tài liệu này là **bắt buộc giống nhau** trừ phần đánh dấu *(tự đo theo máy)*.

---

## 1. Output format — phần bắt buộc thống nhất

### 1.1. File giao cuối cùng

Mỗi người giao **1 file CSV** = bản sao file gốc `approved-results (3).csv`, **giữ nguyên 23 cột gốc theo đúng thứ tự**, chỉ điền cột `flag` và **thêm 1 cột `reject_reason` ở cuối**.

Tên file: `approved-results-<Tên>-<ngày>-flagged.csv` (vd `approved-results-DuongVanKien-2026-10-15-flagged.csv`).

23 cột gốc, không được đổi tên/thứ tự/thêm/bớt:

```
entity_id, slug, canonical_name, category, kind_hint, query, local_path, sha256,
image_url, source_url, source_domain, description, width, height, bytes, crawled_at,
has_face, face_count, face_error, face_area_pct, from_db, cluster, flag
```

Cột thứ 24 thêm vào: `reject_reason`.

| Cột | Giá trị cho phép | Ghi chú |
|-----|------------------|---------|
| `flag` | `approved` \| `rejected` | Không để trống trong phần của mình |
| `reject_reason` | xem bảng §1.2 | **Trống** khi `flag=approved` |

**Quy ước file:**
- Encoding `utf-8-sig` (UTF-8 có BOM) — để Excel mở không lỗi tiếng Việt.
- Dấu phân cách `,`; trích dẫn chuẩn CSV (`"` khi trong ô có dấu phẩy).
- Dòng 1 là tiêu đề. **Không** thêm dòng trống cuối.
- Chỉ điền phần bản ghi của mình; **các dòng ngoài phạm vi để `flag` trống y như file gốc**, không xoá dòng.

### 1.2. Bảng `reject_reason` — dùng đúng câu, không tự đặt thêm

| Mã nội bộ | Câu ghi vào `reject_reason` |
|-----------|-----------------------------|
| `wrong_person` | `Không cùng người` |
| `name_mismatch` | `Không cùng người` |
| `no_person` | `Không rõ người` |
| `not_clear` | `Nhiều chi tiết thừa` |
| `not_prominent` | `Nhiều chi tiết thừa` |
| `hard_to_identify` | `Nhiều chi tiết thừa` |
| `sensitive` | `Ảnh nhạy cảm` |
| `unresolved` | `Chưa xác định được` |

Nhiều lý do cùng lúc → nối bằng `"; "` (chấm phẩy + 1 khoảng trắng), **không trùng câu**. Ví dụ: `Không rõ người; Nhiều chi tiết thừa`.

> `Ảnh nhạy cảm` và `Chưa xác định được` là 2 câu nhóm mình thêm (bản đợt 1 của Thành chưa có case này). Nếu mentor muốn câu khác thì sửa đồng loạt cả 3 file.

### 1.3. File nhãn trung gian (của công cụ duyệt)

Công cụ duyệt export file riêng để lưu vết, **không phải file giao**. Giữ đúng 16 cột để 3 người so sánh được:

```
line_no, entity_id, slug, canonical_name, sha256, image_url, flag, reasons,
identity, note, labeler, labeled_at, review_source, auto_flag, rules, audit
```

| Cột | Ý nghĩa |
|-----|---------|
| `reasons` | mã nội bộ, nối bằng `;` (vd `wrong_person;name_mismatch`) |
| `identity` | `match` \| `other` \| `unsure` — kết luận về danh tính |
| `review_source` | `auto` \| `human` \| `audit` \| `gold` — nhãn này do đâu ra |
| `auto_flag` | `rejected` \| `suggest_approved` \| `to_review` — pipeline đề xuất gì |
| `rules` | rule nào kích hoạt (vd `R1`, `A2;R4`) |
| `audit` | `1` nếu ảnh thuộc mẫu kiểm tra 10% |

> **Quan trọng:** nối dữ liệu giữa các file **luôn bằng `entity_id + sha256`**, không dùng `line_no`. Đợt 1 mentor xoá/thêm dòng giữa các phiên bản làm lệch toàn bộ số dòng.

---

## 2. Model — bắt buộc giống nhau

### 2.1. Bộ model

Dùng **InsightFace buffalo_l** dạng ONNX, chạy bằng `onnxruntime` CPU. **Không cài package `insightface`** (nặng, kéo theo nhiều phụ thuộc) — chỉ cần 2 file `.onnx`.

| Vai trò | Model | File | Kích thước |
|---------|-------|------|-----------|
| Phát hiện mặt | SCRFD-10GF | `det_10g.onnx` | 16,9 MB |
| Nhúng đặc trưng mặt | ArcFace R50 (w600k) | `w600k_r50.onnx` | 174,4 MB |

Tải: bộ `buffalo_l` của InsightFace (các file khác trong bộ — `1k3d68`, `2d106det`, `genderage` — **không dùng**, có thể xoá).

Đặt tại: `people/models/buffalo_l/det_10g.onnx` và `people/models/buffalo_l/w600k_r50.onnx`.

> **Giấy phép:** InsightFace pretrained models là **non-commercial, chỉ dùng cho nghiên cứu**. Task này là nghiên cứu nội bộ nên hợp lệ. Không dùng cho sản phẩm thương mại.

### 2.2. Tham số phát hiện mặt (SCRFD) — không được đổi

| Tham số | Giá trị | Ghi chú |
|---------|---------|---------|
| Kích thước đầu vào | `640 × 640` | letterbox giữ tỉ lệ, pad nền đen |
| Chuẩn hoá ảnh | `(pixel − 127,5) / 128` | `swapRB=True` (BGR→RGB) |
| Ngưỡng tin cậy | `0,5` | |
| Ngưỡng NMS (IoU) | `0,4` | |
| Stride | `8, 16, 32` | 2 anchor mỗi vị trí |

### 2.3. Tham số nhúng đặc trưng (ArcFace) — không được đổi

| Tham số | Giá trị |
|---------|---------|
| Căn chỉnh mặt | affine 5 điểm về template ArcFace |
| Template 5 điểm | `(38.2946, 51.6963)`, `(73.5318, 51.5014)`, `(56.0252, 71.7366)`, `(41.5493, 92.3655)`, `(70.7299, 92.2041)` |
| Kích thước crop | `112 × 112` |
| Chuẩn hoá ảnh | `(pixel − 127,5) / 127,5`, `swapRB=True` |
| Chiều vector | `512` |
| Hậu xử lý | **L2-normalize** vector |
| Độ giống | **cosine** = dot product của 2 vector đã L2-normalize |

> Vì vector đã L2-normalize, cosine = dot product. Mọi ngưỡng `sim` dưới đây đều là cosine trong `[−1, 1]`.

### 2.4. Môi trường chạy

| | Giá trị |
|---|---|
| Python | 3.12 |
| `onnxruntime` | 1.30 (CPU, `CPUExecutionProvider`) |
| `numpy` | 2.5 |
| `opencv-python` | 5.0 |
| `pillow` | 12.3 |
| `intra_op_num_threads` | **6** *(tự đo theo máy — xem cảnh báo dưới)* |

> ⚠️ **Cảnh báo hiệu năng quan trọng:** đặt số luồng = tổng số luồng CPU khiến chạy **chậm gấp ~10 lần**. Đo thực tế trên Core Ultra 7 155H (22 luồng): đặt 22 luồng → **3,4 s/ảnh**; đặt 6 luồng → **0,33 s/ảnh**. Nguyên nhân: các phép toán ONNX nhỏ bị chi phí đồng bộ luồng lấn át.
>
> **Cách tự đo:** chạy 100 ảnh với `intra_op_num_threads` = 4, 6, 8, lấy giá trị nhanh nhất. Thường bằng **số P-core**, không phải tổng số luồng.

### 2.5. Đọc ảnh

Đọc bằng Pillow + `ImageOps.exif_transpose` (xoay theo EXIF) rồi chuyển sang mảng BGR cho OpenCV. **Bỏ bước này sẽ làm mặt bị xoay 90° ở ảnh điện thoại → detector trượt.**

---

## 3. Pipeline — 3 lớp

```
                 ┌──────────────────────────────────────────────┐
  CSV gốc ─────► │ [G1] Tải ảnh                                 │
  (phần của mình)│  • theo image_url, 6 luồng                   │
                 │  • 4 vòng retry, giãn cách tăng dần          │
                 │  • lỗi > 30% → đợi 5 phút, thử lại (tối đa 6)│
                 │  • resume: ảnh đã có thì bỏ qua              │
                 └───────────────────┬──────────────────────────┘
                                     ▼
                 ┌──────────────────────────────────────────────┐
                 │ [A] Trích đặc trưng  (chạy 1 lần, cache)     │
                 │  SCRFD → mọi mặt: bbox, 5 điểm, score, px,   │
                 │          area_pct, blur, yaw                 │
                 │  ArcFace → embedding 512-d cho MỌI mặt       │
                 │  → faces.jsonl + embeddings.f32              │
                 └───────────────────┬──────────────────────────┘
                                     ▼
                 ┌──────────────────────────────────────────────┐
                 │ [B] Danh tính theo entity + rule             │
                 │  1. lọc mặt tốt (score ≥ 0,6, ≥ 24px)        │
                 │  2. gom cụm mặt (single-link, sim ≥ 0,40)    │
                 │  3. chọn cụm chính + tính anchor             │
                 │  4. so khớp tên trong tiêu đề               │
                 │  5. áp rule → auto_flag                      │
                 └───────────────────┬──────────────────────────┘
                                     ▼
                 ┌──────────────────────────────────────────────┐
                 │ [C] Người duyệt (công cụ HTML)               │
                 │  • toàn bộ to_review                         │
                 │  • xác nhận hàng loạt nhóm suggest_approved  │
                 │  • mẫu 10% auto-reject (audit) để đo sai số  │
                 └──────────────────────────────────────────────┘
```

Lớp B **không bao giờ tự ghi `flag` cuối**. Mọi `flag` đều do người duyệt quyết hoặc xác nhận.

---

## 4. Lớp A — trích đặc trưng

### 4.1. Lọc "mặt tốt"

Chỉ mặt thoả **cả hai** điều kiện mới được dùng cho mọi tính toán sau:

| Điều kiện | Giá trị |
|-----------|---------|
| `score` (tin cậy detector) | ≥ `0,6` |
| `size_px` (cạnh lớn hơn của bbox) | ≥ `24` px |

Ảnh không có mặt tốt nào → cảnh báo `no_good_face`, chuyển người duyệt (**không** auto-reject, vì ảnh toàn thân/xa vẫn có thể approved).

### 4.2. Dữ liệu cache

| File | Nội dung |
|------|----------|
| `features/faces.jsonl` | 1 dòng JSON / ảnh: `entity_id`, `sha256`, `line_no`, `error`, `faces[]` |
| `features/embeddings.f32` | mảng `float32` thô, reshape `(-1, 512)`; mỗi mặt có 1 chỉ số `emb` trỏ vào đây |

Mỗi phần tử `faces[]`: `bbox`, `kps` (5 điểm), `score`, `size_px`, `area_pct` (% diện tích ảnh), `blur`, `yaw`, `emb` (chỉ số dòng trong `embeddings.f32`).

**Phải resume được:** chạy lại thì bỏ qua ảnh đã trích; riêng bản ghi có `error = "no_image"` thì thử lại.

---

## 5. Lớp B — logic danh tính (phần dễ lệch nhất giữa 3 người)

### 5.1. So khớp tên trong tiêu đề

Nguồn tên: cột `description` (tiêu đề trang). So với `canonical_name`.

**Chuẩn hoá trước khi so:**
1. Bỏ phần trong ngoặc: `"Thắng (solo)"` → `"Thắng"`.
2. Bỏ tiền tố chức danh đứng đầu: `nhạc sĩ, ca sĩ, nghệ sĩ, vua, nhóm, ban nhạc, NSND, NSƯT, GS, PGS, TS` **+ `NTK`** *(đợt 1 thiếu `NTK` → gây lỗi, đã bổ sung)*.
3. Giữ cả dạng đầy đủ (đã bỏ ngoặc) để so song song; `exact` thắng `variant`.
4. Chuẩn hoá Unicode NFC và **vị trí dấu**: `Hoà ≡ Hòa`, `Thuý ≡ Thúy` *(đợt 1 thiếu → gây lỗi, đã bổ sung)*.

**Thuật toán:** trượt cửa sổ `n` từ (`n` = số từ của tên) trên tiêu đề. Với mỗi cửa sổ, so bản **bỏ dấu**; nếu khớp thì xét tiếp bản **có dấu**:

| Kết quả | Điều kiện |
|---------|-----------|
| `exact` | cửa sổ khớp y hệt cả dấu, **hoặc** cửa sổ vốn không dấu (ASCII), **hoặc** `canonical_name` vốn không dấu |
| `variant` | khớp khi bỏ dấu nhưng **khác dấu** khi có dấu (vd `Hạ Vy` ≠ `Hà Vy`) |
| `no_name` | tên không xuất hiện |

> Ngoại lệ `exact` cho tiêu đề ASCII là **bắt buộc** — nhiều trang viết tên không dấu ("pham cong hung"), nếu coi là `variant` sẽ loại nhầm hàng loạt. Đợt 1 đã mắc lỗi này và phải sửa.

### 5.2. Gom cụm mặt trong 1 entity

Mục đích: tìm xem "người thật" của entity trông thế nào, khi không có ảnh tham chiếu.

| Tham số | Giá trị |
|---------|---------|
| Ngưỡng nối 2 mặt (`LINK_SIM`) | `0,40` |
| Kiểu gom | **single-link** (union-find) |
| Ràng buộc | **chỉ nối 2 mặt ở 2 ảnh KHÁC nhau** |

> Ràng buộc "khác ảnh" rất quan trọng: nhiều mặt trong cùng 1 ảnh (ảnh nhóm) không được tự nối thành một cụm.

**Chọn cụm chính:** điểm cụm = `số ảnh` + `số ảnh có tên khớp exact`. Cụm điểm cao nhất là cụm chính. Không có cụm nào → entity `unresolved`, mọi ảnh chuyển người duyệt.

### 5.3. Anchor (mặt mốc)

Đáng tin hơn cụm chính vì neo vào bằng chứng tên.

1. Với mỗi ảnh có tên khớp `exact`, lấy **mặt lớn nhất** làm ứng viên mốc.
2. Gom cụm các mốc (cùng `LINK_SIM = 0,40`).
3. Giữ cụm mốc lớn nhất, yêu cầu **≥ 2 ảnh**.
4. `anchor_sim` của một ảnh = cosine lớn nhất giữa mặt trong ảnh đó và các mốc, **không tính chính ảnh đó**.

Entity không đủ 2 ảnh mốc → `anchor_sim` không có giá trị, cảnh báo `entity_no_anchor`.

### 5.4. `best_sim`

Cosine lớn nhất giữa mặt trong ảnh và các mặt thuộc cụm chính, **loại trừ chính các mặt của ảnh đó** (nếu không ảnh sẽ tự so với mình = 1,0).

---

## 6. Lớp B — rule

> Ngưỡng dưới đây là **điểm khởi đầu từ đợt 1**. Mỗi người **phải đo lại trên golden của mình** rồi chốt, vì phân bố dữ liệu từng phần khác nhau. Mốc bắt buộc: **precision ≥ 98%** cho cả 2 nhóm tự quyết.

### 6.1. Nhóm auto-reject

| # | Điều kiện | Mã lý do |
|---|-----------|----------|
| `R1` | tên trong tiêu đề là `variant` (khác dấu) **VÀ `canonical_name` CÓ dấu thanh** | `name_mismatch` |
| `A2` | `no_name` **VÀ** có mặt tốt **VÀ** `anchor_sim < 0,25` | `wrong_person` |
| `R4` | `no_name` **VÀ** có mặt tốt **VÀ** `best_sim < 0,30` | `wrong_person` |
| `R5` | ảnh tải lỗi / không đọc được | `no_person` |

**Thay đổi so với đợt 1 — phải áp dụng:**

- **`R1` thêm điều kiện chặn `canonical_name` có dấu thanh.** Entity vốn không có dấu thanh thì khi bỏ dấu khớp với rất nhiều tên khác → rule sẽ loại nhầm. Ca thật đợt 1: entity `Phan Thanh` khớp nhầm "Phan **Thành**"; `Tôn Thất Tư` khớp nhầm "Tôn Thất **Tùng**"; `Thiếu Sơn` khớp nhầm "thiếu **son** môi". → nhóm này **bắt buộc người review**.
- **KHÔNG áp rule cho tên đảo thứ tự hoặc viết chưa đầy đủ** (`Phạm Anh Khoa` ↔ `Anh Khoa`) — rất hay là cùng người.
- **Bỏ rule quan hệ khỏi auto-reject.** Đo thực tế đợt 1: từ quan hệ (`vợ`, `con trai`, `bố`…) xuất hiện bất kỳ đâu → precision chỉ **30–44%**; gắn ngay trước tên → chỉ khớp **10/6.664 ảnh, precision 40%**. Lý do: tiêu đề "Vợ Phạm Trưởng…" thì ảnh **vẫn chụp cả hai** → thực tế approved; và khớp nhầm từ vựng ("**Võ** Thu Hà" → "vợ"). → chỉ dùng **cảnh báo**.

### 6.2. Nhóm gợi ý approved

Tất cả điều kiện phải **cùng đúng**:

| Điều kiện | Đợt 1 | Đợt 2 (đề xuất, phải đo lại) |
|-----------|-------|------------------------------|
| Tên trong tiêu đề | `exact` | `exact` (giữ) |
| `best_sim` (cụm chính) | ≥ `0,50` | ≥ `0,45` |
| `anchor_sim` | ≥ `0,50` | ≥ `0,45` |
| Độ vượt trội mặt chính | ≥ `2,0` | ≥ `1,8` |
| `size_px` mặt chính | ≥ `64` | ≥ `56` |
| `cluster` của mentor | ≠ `ambiguous` | ≠ `ambiguous` (giữ) |
| **Chức danh khớp `category`** | — | **mới:** cho phép hạ `sim` xuống `0,40` |
| **Chức danh lệch hẳn `category`** | — | **mới:** loại khỏi nhóm gợi ý → `to_review` |

Độ vượt trội = `area_pct` mặt lớn nhất / `area_pct` mặt thứ hai (1 mặt → vô cùng).

Nhóm `category = historic` (tranh, tượng, ảnh cũ) dùng ngưỡng **lỏng hơn** — ArcFace kém với loại ảnh này.

### 6.3. Bảng chức danh ↔ category (mới, dùng cho §6.2)

Trường `query` của file = `<chức danh tiếng Việt theo category> + canonical_name`, nên **không phải tín hiệu độc lập** với `category`. Giá trị của nó là bảng từ vựng dưới đây:

| `category` | Cụm trong `query` | Từ gần nghĩa coi là KHỚP |
|------------|-------------------|--------------------------|
| `singer` | nghệ sĩ | ca sĩ, nhạc sĩ, rapper, NSND, NSƯT, diva |
| `athletes` | vận động viên | VĐV, cầu thủ, tiền vệ, hậu vệ, thủ môn, HLV, võ sĩ, kỳ thủ, tay đua |
| `politicer` | chính khách | bộ trưởng, thứ trưởng, chủ tịch, bí thư, đại biểu, ĐBQH, thủ tướng |
| `businessman` | doanh nhân | CEO, chủ tịch HĐQT, tổng giám đốc, TGĐ, nhà sáng lập, founder, shark |
| `scientist` | nhà khoa học | GS, PGS, TS, tiến sĩ, giáo sư, viện trưởng, bác sĩ, nhà nghiên cứu |
| `writer` | nhà văn | nhà thơ, nhà báo, tác giả, dịch giả, nhà phê bình, biên kịch |
| `celeb` | chân dung | diễn viên, người mẫu, hoa hậu, á hậu, MC, KOL, hot girl, streamer |
| `historic` | lịch sử | vua, hoàng đế, danh nhân, tướng, thi hào, chí sĩ, nhà cách mạng |

> Bảng này **gần nghĩa, không chính xác** (một `celeb` vẫn có thể được gọi "ca sĩ"). Vì vậy: **khớp → chỉ cộng điểm** (an toàn); **lệch → chỉ cảnh báo**, không auto-reject.

### 6.4. Cảnh báo (không tự quyết, chỉ sắp xếp hàng đợi)

| Mã | Điều kiện |
|----|-----------|
| `no_image` | tải lỗi / không đọc được |
| `no_good_face` | không có mặt nào đạt §4.1 |
| `title_no_name` | tiêu đề không chứa tên |
| `mentor_ambiguous` | `cluster = ambiguous` |
| `multi_face` | > 1 mặt tốt |
| `small_face` | mặt lớn nhất < 2% diện tích ảnh |
| `entity_no_anchor` | entity không đủ 2 ảnh mốc |
| `role_mismatch` | **mới:** chức danh trong tiêu đề lệch hẳn `category` |
| `relation_word` | **mới:** tiêu đề có từ quan hệ (`vợ`, `con trai`, `bố`…) |
| `sensitive_kw` | tiêu đề có từ khoá: bắt, còng, khởi tố, xét xử, tòa, biểu tình… |

Ảnh có cảnh báo được **đẩy lên đầu hàng đợi duyệt**, không bị loại.

Nhạy cảm loại sự kiện (bắt giữ, tòa án, biểu tình, bạo lực) **chỉ tính khi chính ảnh thể hiện** — lớp B không nhìn được nội dung này, nên từ khoá tiêu đề **chỉ cảnh báo**.

---

## 7. Lớp C — người duyệt

### 7.1. Hàng đợi

Thứ tự hiển thị (ảnh cần quyết định lên trước):

| Hạng | Nhóm |
|------|------|
| 0 | `to_review` + ảnh `audit` (mẫu kiểm tra) |
| 1 | `suggest_approved` (viền xanh nét đứt, xác nhận hàng loạt) |
| 2 | nhãn golden đã có (prefill, không duyệt lại) |
| 3 | `auto-reject` (ẩn mặc định, có nút hiện) |

### 7.2. Mẫu kiểm tra (audit)

| Tham số | Giá trị |
|---------|---------|
| Tỉ lệ | **10%** của nhóm auto-reject |
| Cách chọn | ngẫu nhiên, **seed cố định** (`SEED + số_đợt`) để tái lập được |

Người duyệt xem mẫu này như ảnh thường. Sau đợt, so nhãn người vs auto để **đo precision thật**. Precision thật < 98% → chỉnh ngưỡng, chạy lại lớp B (đặc trưng đã cache, rất nhanh), duyệt lại.

### 7.3. Ràng buộc nhập nhãn

- `identity = other` hoặc `unsure` → **bắt buộc** `flag = rejected` + lý do `wrong_person`.
- Entity không xác định được → đánh dấu `unresolved` cho cả entity.
- Nhãn lưu `localStorage` theo origin; export CSV để lưu vết. **Mở bằng `file://` hoặc tắt Live Server auto-reload**, nếu không trang tự tải lại giữa lúc duyệt.

---

## 8. Kết quả đợt 1 — mốc để đối chiếu

Đo trên **6.664 ảnh** đã gán nhãn tay (phần của Kiên, `approved-results (1).csv`):

| Nhóm | Số ảnh | Precision | Recall |
|------|--------|-----------|--------|
| auto-reject | 1.262 | **99,0%** (1.250/1.262) | 51,6% |
| gợi ý approved | 2.512 | **96,9%** (2.433/2.512) | 57,4% |
| `to_review` (duyệt tay) | 2.890 | — | — |

Tỉ lệ rejected thật: **36,3%** (2.422/6.664).

**Hai điểm yếu đã biết, đợt 2 phải cải thiện:**
1. Gợi ý approved **chưa đạt 98%** → cần siết (hoặc dùng `category` để loại ca trùng tên).
2. Bỏ sót nhiều: **1.172 ảnh sai** và **1.809 ảnh đúng** vẫn phải duyệt tay.

Trong 902 ảnh `name_mismatch` bị bỏ sót:

| Nguyên nhân | Số ảnh | Hướng xử lý |
|-------------|--------|-------------|
| Tên **không có** trong tiêu đề | 602 | siết `A2`/`R4` |
| Tên khớp **đúng cả dấu** nhưng là người khác | 276 | dùng `category` (§6.3) |
| Khớp khi bỏ dấu, **khác dấu thanh** | 24 | `R1` + ngoại lệ §6.1 |

> Dùng các số này làm **mốc so sánh**: nếu phần của bạn lệch nhiều (vd precision auto-reject < 95%), khả năng cao là tham số hoặc model bị khác → đối chiếu lại §2.

---

## 9. Checklist trước khi chạy thật

- [ ] 2 file `.onnx` đúng tên, đúng kích thước (§2.1).
- [ ] Phiên bản thư viện khớp §2.4.
- [ ] Đã tự đo `intra_op_num_threads` (§2.4) — **đừng để mặc định**.
- [ ] Đã đọc ảnh qua `exif_transpose` (§2.5).
- [ ] Đã sửa 2 lỗi chuẩn hoá tên: tiền tố `NTK`, dấu `Hoà ≡ Hòa` (§5.1).
- [ ] `R1` đã có điều kiện chặn entity không dấu thanh (§6.1).
- [ ] Đã gán golden 30–40 entity và **đo precision ≥ 98%** cho cả 2 nhóm tự quyết.
- [ ] Mẫu audit 10% có seed cố định (§7.2).
- [ ] Output đúng 23 cột gốc + `reject_reason`, encoding `utf-8-sig` (§1.1).
- [ ] Dùng đúng bảng câu `reject_reason` (§1.2) — không tự đặt câu mới.
- [ ] Nối dữ liệu bằng `entity_id + sha256` (§1.3).

---

## 10. Mã nguồn

| File | Việc |
|------|------|
| `tools/extract_faces.py` | lớp A: SCRFD + ArcFace, cache `faces.jsonl` + `embeddings.f32` |
| `tools/eval_identity.py` | so khớp tên, gom cụm, anchor; đo rule trên golden |
| `tools/apply_rules.py` | lớp B: áp rule → `auto_flag`, cảnh báo, mẫu audit |
| `tools/run_batches.py` | điều phối theo đợt: tải → trích → áp rule → gộp |
| `tools/build_review.py` | sinh công cụ duyệt (`review.html` + `data.js`) |
| `tools/select_golden.py` | chọn golden phân tầng, seed cố định |

> Sau khi đổi cấu trúc thư mục sang `people/`, đường dẫn trong các script **chưa được cập nhật** — cần sửa trước khi chạy.
