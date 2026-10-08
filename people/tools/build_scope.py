"""Chuẩn bị dữ liệu cho phạm vi làm việc: 1/3 cuối file của mentor (dòng 13325–19988).

Tải ảnh về scope/images/ (dùng lại ảnh đã có trong golden/images/), ghi scope/manifest.json.
Khóa của mỗi ảnh: entity_id + sha256 (không phụ thuộc số dòng).

Chạy: python tools/build_scope.py   (chạy lại để thử tải lại ảnh lỗi)
"""
import csv
import json
import os
import shutil
from concurrent.futures import ThreadPoolExecutor

from build_golden import FIELDS, download_to, ext_of

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(ROOT, "data", "approved-results (1).csv")
SCOPE_DIR = os.path.join(ROOT, "scope")
IMG_DIR = os.path.join(SCOPE_DIR, "images")
GOLDEN_IMG_DIR = os.path.join(ROOT, "golden", "images")
START_LINE, END_LINE = 13325, 19988  # dòng trong file, dòng tiêu đề là dòng 1


def main():
    os.makedirs(IMG_DIR, exist_ok=True)
    with open(CSV_PATH, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    items = []
    for i, r in enumerate(rows):
        line_no = i + 2
        if START_LINE <= line_no <= END_LINE:
            item = {k: r[k] for k in FIELDS}
            item["line_no"] = line_no
            item["mentor_cluster"] = r["cluster"]
            item["image_file"] = r["sha256"][:16] + ext_of(r["image_url"])
            items.append(item)

    # Dùng lại ảnh golden đã tải (cùng quy tắc đặt tên).
    reused = 0
    for it in items:
        dst = os.path.join(IMG_DIR, it["image_file"])
        src = os.path.join(GOLDEN_IMG_DIR, it["image_file"])
        if not os.path.exists(dst) and os.path.exists(src):
            shutil.copy2(src, dst)
            reused += 1

    def job(it):
        return download_to(it["image_url"], os.path.join(IMG_DIR, it["image_file"]))

    with ThreadPoolExecutor(max_workers=16) as pool:
        errors = list(pool.map(job, items))

    n_err = 0
    for it, err in zip(items, errors):
        it["download_error"] = err or ""
        n_err += bool(err)

    with open(os.path.join(SCOPE_DIR, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False)
    print(f"{len(items)} ảnh, {len({it['entity_id'] for it in items})} entity, "
          f"dùng lại từ golden {reused}, tải lỗi {n_err}")


if __name__ == "__main__":
    main()
