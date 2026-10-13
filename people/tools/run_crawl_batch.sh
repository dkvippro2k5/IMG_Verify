#!/usr/bin/env bash
# Chạy crawl thêm ảnh cho một đợt, chia N tiến trình song song (cấu hình đã dùng ở batch5 giai đoạn nhanh).
# Dùng: bash people/tools/run_crawl_batch.sh <thư mục đợt, vd people/output-batch6> <file gốc.csv> <file nhãn đã duyệt.csv> [số_tiến_trình=4]
# Cần có sẵn <thư mục đợt>/low-ref.csv (tạo bằng make_low_list.py). Log: $TEMP/crawl_<tên đợt>_<k>.log; kết quả: <thư mục đợt>/crawl-extra-ref/shard<k>/.
# Chạy lại an toàn: entity đã xong trong funnel.json được bỏ qua. Dừng: kill các tiến trình python có 'crawl_funnel' trong dòng lệnh.
set -e
BATCH="$1"; SRC="$2"; LABELS="$3"; N="${4:-4}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
export IMG_BATCH_DIR="$ROOT/$BATCH" IMG_SRC_CSV="$SRC" IMG_LABELS_CSV="$LABELS" IMG_LOW_CSV="$ROOT/$BATCH/low-ref.csv"
export ORT_THREADS="${ORT_THREADS:-4}" PYTHONIOENCODING=utf-8
NAME="$(basename "$BATCH")"
for k in $(seq 1 "$N"); do
  nohup "$ROOT/.venv/Scripts/python.exe" -u "$ROOT/people/tools/crawl_funnel.py" --shard "$k/$N" \
    --max-dl 160 --ddg-n 80 --skip-wiki --drop-low --skip-done-in "$ROOT/$BATCH/crawl-extra-ref" --out "$ROOT/$BATCH/crawl-extra-ref/shard$k" \
    >> "${TEMP:-/tmp}/crawl_${NAME}_$k.log" 2>&1 &
done
echo "đã chạy $N tiến trình cho $BATCH"
