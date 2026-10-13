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
  tools/crawl_*.py, build_extra_review.py, make_*.py, run_crawl_batch.sh   crawl thêm ảnh + duyệt + tách file nộp (xem mục dưới)
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

## Crawl thêm ảnh cho entity ít ảnh (batch bổ sung)

Dùng sau khi một đợt đã được duyệt xong: tìm thêm ảnh cho các entity còn ít ảnh `approved`, lọc tự động rồi duyệt tay phần mới.
Nguồn ảnh là DuckDuckGo Images (thư viện `ddgs`, không cần API key) và Wikimedia Commons; chạy CPU, không tốn quota trả phí.

**Chuẩn bị:** `pip install -r requirements.txt` (đã gồm `ddgs`), có model ở `people/models/buffalo_l/`, file dữ liệu của đợt và **file nhãn đã duyệt**
(cột `entity_id`, `sha256`, `flag` = `approved`/`rejected`; thêm `image_url`, `line_no`, `reject_reason` nếu muốn dựng trang duyệt cho ảnh cũ).
Mọi lệnh chạy từ thư mục gốc repo (Git Bash trên Windows).

```bash
# 1. Danh sách entity cần crawl: đủ 15-40 ảnh approved/entity, nổi tiếng (nhiều ảnh) xếp trước
python people/tools/make_low_list.py "people/data/approved-results (N).csv" FIRST LAST "<file nhãn>.csv" people/output-batchN
#    -> low-ref.csv (entity có ảnh approved làm tham chiếu), low-noref.csv (chưa có ảnh nào: nên kéo thả tay, crawl tự động rất kém)

# 2. Crawl nền, 4 tiến trình song song; chạy lại được, entity đã xong tự bỏ qua; log ở $TEMP/crawl_<đợt>_<k>.log
bash people/tools/run_crawl_batch.sh people/output-batchN "<file dữ liệu>.csv" "<file nhãn>.csv" 4
bash people/tools/watch_crawl_limit.sh people/output-batchN/crawl-extra-ref 3000 10800   # tự dừng khi đủ 3000 ảnh hoặc sau 3 giờ

# 3. Dựng trang duyệt (ảnh mới lên đầu từng entity, entity chưa duyệt lên đầu danh sách)
B=people/output-batchN
IMG_BATCH_DIR="$PWD/$B" IMG_CRAWL_DIRS=crawl-extra-ref IMG_MERGED_CSV="$PWD/$B/<file nhãn>.csv" IMG_LABELS_CSV="$PWD/$B/<file nhãn>.csv" IMG_REVIEW_KEY=extra-review-N-v1 IMG_REVIEW_PREFIX=extra-labels-N python people/tools/build_extra_review.py
#    -> $B/review-extra/review.html (mở bằng file://). Dựng lại bất cứ lúc nào crawl có thêm ảnh; nhãn đã duyệt trong trình duyệt được giữ.
#    Tuỳ chọn: IMG_ENTITY_LIST=<csv cột entity_id> đưa cả entity chưa có ảnh crawl; IMG_FILL_REASON=wrong_person điền lý do cho ảnh cũ bị reject không có lý do.

# 4. Duyệt trong review.html, bấm "Xuất CSV" (nhãn chỉ lưu trong trình duyệt nên xuất thường xuyên)

# 5. Tách file nộp: ảnh gốc đã duyệt + ảnh crawl mới đã duyệt, đều theo cột file gốc + reject_reason
python people/tools/make_final_split.py "people/data/approved-results (N).csv" FIRST LAST $B $B/<gốc>.csv $B/<crawl-new>.csv "<nhãn mới nhất>.csv" ["<nhãn cũ bổ sung>.csv"] -- $B/crawl-extra-ref
```

**Bộ lọc tự động** (`crawl_funnel.py`): tải tối đa 160 ảnh thô/entity (`--max-dl`), bỏ ảnh nhỏ (<400 px), ảnh trùng `sha256`/gần trùng, ảnh tượng/tranh/bia mộ (theo tiêu đề);
chỉ giữ ảnh có **một mặt rõ chiếm >= 2% diện tích ảnh**; so ArcFace với ảnh đã approved của chính entity (dưới 0,25 bị loại, từ 0,40 là mức tin cậy `high`);
bỏ ảnh `low` (`--drop-low`). Entity chưa có ảnh tham chiếu chỉ tự dựng tham chiếu từ ảnh có tên trong tiêu đề nên kết quả kém.

**Thêm ảnh bằng tay:** trên `review.html`, kéo ảnh từ Google/Bing Images thả vào trang (hoặc dán link ảnh vào ô trên đầu) để thêm vào entity đang mở;
link bài viết có thể dán sau vào ô trên thẻ ảnh. Ảnh thêm tay có `origin = manual`, `sha256` để trống (tải về và tính sau).

**Lưu ý:** `ORT_THREADS` (mặc định 6) chỉnh số luồng ONNX mỗi tiến trình; tổng luồng của các tiến trình không nên vượt số luồng CPU.
Mức chạy tham khảo ở batch5: khoảng 1 entity/phút với 4 tiến trình. DuckDuckGo giới hạn theo IP nên không tăng quá nhiều tiến trình.
Nếu `extra-results.csv` bị lệch cột (do file nhãn đổi cột giữa các lần chạy) dùng `people/tools/fix_extra_csv.py <thư mục crawl>`.
Ảnh trùng `sha256` giữa các entity khác nhau (dữ liệu có nhiều entity cùng một người) được giữ nguyên.

## Quy ước làm việc

- Nối dữ liệu bằng **`entity_id + sha256`**, không dùng số dòng.
- Không đưa lên git: CSV của mentor, ảnh, model, file nhãn cá nhân.
- Mỗi đợt 1000 ảnh: tỉ lệ `rejected` > 5% thì **escalate** cho mentor trước khi làm tiếp.
- Rule tự loại / gợi ý approved chỉ được bật khi precision ≥ 98% trên golden của phần mình.
