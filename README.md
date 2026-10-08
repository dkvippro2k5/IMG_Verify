# IMG_Verify

Gắn cờ `approved` / `rejected` cho ảnh của các entity người (file `approved-results (N).csv` của mentor), bằng **bộ lọc rule + so khớp khuôn mặt chạy CPU** kết hợp **người duyệt** qua công cụ HTML. Nghiên cứu nội bộ, phi thương mại.

Mỗi ảnh nhận 2 cột: `flag` (`approved` / `rejected`) và `reject_reason` (câu tiếng Việt, xem [pipeline-spec](people/docs/pipeline-spec.md) §1.2).

## Đọc trước

| Tài liệu | Nội dung |
|----------|----------|
| [people/docs/plan.md](people/docs/plan.md) | Phạm vi, chia việc 3 người, quy trình theo đợt 1000 ảnh, ngưỡng escalate |
| [people/docs/pipeline-spec.md](people/docs/pipeline-spec.md) | **Đặc tả model, tham số, rule, output format** — 3 người phải giống nhau |
| [people/docs/golden-guideline.md](people/docs/golden-guideline.md) | Tiêu chí duyệt ảnh |
| [people/docs/golden-entities.md](people/docs/golden-entities.md) | Danh sách entity golden đợt 1 |
| [people/docs/report.md](people/docs/report.md) | Nghiên cứu ban đầu (model, dataset) |

## Cấu trúc

```
people/                 pipeline duyệt ảnh người
  docs/                 tài liệu (ở trên)
  tools/                mã nguồn pipeline
  golden/review.html    mẫu giao diện duyệt (build_review*.py dùng làm template)
  golden/golden-labels-v2.csv   nhãn golden đợt 1 (mốc đối chiếu)
  data/                 đặt file CSV của mentor ở đây (không đưa lên git)
  models/buffalo_l/     2 file ONNX (không đưa lên git)
```

Thư mục sinh ra khi chạy (đều bị `.gitignore`): `images/`, `features/`, `batches/`, `data.js`, `review.html` của từng phần việc.

## Cài đặt

```bash
python -m venv .venv
.venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

Python 3.12. Chỉ cần CPU, không cài package `insightface`.

**Model:** tải `buffalo_l.zip` của InsightFace
(<https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip>), giải nén, chỉ giữ 2 file:

```
people/models/buffalo_l/det_10g.onnx     (SCRFD, ~17 MB)
people/models/buffalo_l/w600k_r50.onnx   (ArcFace R50, ~174 MB)
```

Giấy phép model InsightFace: **chỉ dùng cho nghiên cứu, phi thương mại**.

**Dữ liệu:** đặt `approved-results (3).csv` vào `people/data/`.

## Chạy

Mọi lệnh chạy từ thư mục gốc repo.

```bash
# 1. Tải ảnh của phần mình (bản ghi đầu/cuối tính KHÔNG kể dòng tiêu đề, xem plan.md §1)
python -u people/tools/download_scope.py 9858 14788 people/scope-kien

# 2. Trích đặc trưng mặt (SCRFD + ArcFace) và áp rule, theo đợt  -> xem pipeline-spec.md §3-6
python -u people/tools/run_batches.py

# 3. Dựng giao diện duyệt, mở people/scope/review.html (nên mở bằng file://)
python people/tools/build_review.py
```

> **Số luồng ONNX:** `intra_op_num_threads` trong `people/tools/extract_faces.py` (hàm `session`) đang là 6. Đặt bằng tổng số luồng CPU có thể chậm gấp ~10 lần — tự đo trên máy mình (pipeline-spec §2.4).
>
> **Lưu ý đường dẫn:** `run_batches.py`, `build_review.py`, `apply_rules.py` còn hard-code khoảng dòng của đợt 1 (`13325–19988`, file `approved-results (1).csv`). Trước khi chạy cho phần việc đợt 2 cần sửa lại hằng số `START_LINE`/`END_LINE`/`CSV_PATH` theo phần của mình.

## Quy ước làm việc

- Nối dữ liệu bằng **`entity_id + sha256`**, không dùng số dòng.
- Không đưa lên git: CSV của mentor, ảnh, model, file nhãn cá nhân.
- Mỗi đợt 1000 ảnh: tỉ lệ `rejected` > 5% thì **escalate** cho mentor trước khi làm tiếp.
- Rule tự loại / gợi ý approved chỉ được bật khi precision ≥ 98% trên golden của phần mình.
