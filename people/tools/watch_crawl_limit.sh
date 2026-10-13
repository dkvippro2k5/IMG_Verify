#!/usr/bin/env bash
# Dừng crawl khi đủ số ảnh hoặc hết giờ. Dùng: bash people/tools/watch_crawl_limit.sh <thư mục crawl, vd people/output-batch6/crawl-extra-ref> <số ảnh mục tiêu> <số giây tối đa>
DIR="$1"; GOAL="$2"; MAXS="$3"; START=$(date +%s)
count() { python - "$DIR" <<'PY'
import csv, glob, sys
n = 0
for p in glob.glob(sys.argv[1] + "/**/extra-results.csv", recursive=True):
    n += max(0, sum(1 for _ in csv.reader(open(p, encoding="utf-8-sig", newline=""))) - 1)
print(n)
PY
}
while true; do
  N=$(count); EL=$(( $(date +%s) - START ))
  if [ "$N" -ge "$GOAL" ] || [ "$EL" -ge "$MAXS" ]; then
    powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name like 'python%'\" | Where-Object { \$_.CommandLine -like '*crawl_funnel*' } | ForEach-Object { Stop-Process -Id \$_.ProcessId -Force }"
    echo "dừng lúc $(date +%H:%M): $N ảnh sau $((EL/60)) phút (mục tiêu $GOAL, tối đa $((MAXS/60)) phút)"
    break
  fi
  sleep 300
done
