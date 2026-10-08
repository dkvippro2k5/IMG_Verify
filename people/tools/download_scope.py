"""Tải ảnh của một phần việc (theo thứ tự bản ghi, không tính dòng tiêu đề) từ approved-results (3).csv.

Chạy: .venv/Scripts/python -u people/tools/download_scope.py [bản_ghi_đầu bản_ghi_cuối] [thư_mục_ra]
Mặc định: 9858 14788 people/scope-kien  (phần của Kiên). Chạy lại được: ảnh đã có thì bỏ qua.
Ghi manifest.json (kèm image_file, download_error) để các bước sau dùng.
"""
import csv
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_golden import download_to, ext_of  # noqa: E402

PEOPLE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(PEOPLE, "data", "approved-results (3).csv")
NET_FAIL_RATE = 0.30
MAX_NET_WAITS = 6


def main():
    a = sys.argv[1:]
    first, last = (int(a[0]), int(a[1])) if len(a) >= 2 else (9858, 14788)
    out = a[2] if len(a) >= 3 else os.path.join(PEOPLE, "scope-kien")
    img_dir = os.path.join(out, "images")
    os.makedirs(img_dir, exist_ok=True)

    items = []
    for i, r in enumerate(csv.DictReader(open(SRC, encoding="utf-8-sig", newline="")), 1):
        if first <= i <= last:
            r.update(record_no=i, line_no=i + 1, download_error="", image_file=r["sha256"][:16] + ext_of(r["image_url"]))
            items.append(r)
    print(f"{len(items)} ảnh, {len({r['slug'] for r in items})} entity (bản ghi {first}–{last})", flush=True)

    def fetch(batch):
        pending = list(batch)
        for rnd in range(4):
            with ThreadPoolExecutor(max_workers=6) as pool:
                errs = list(pool.map(lambda it: download_to(it["image_url"], os.path.join(img_dir, it["image_file"])), pending))
            for it, e in zip(pending, errs):
                it["download_error"] = e or ""
            pending = [it for it in pending if it["download_error"]]
            print(f"  vòng {rnd + 1}: còn lỗi {len(pending)}", flush=True)
            if not pending:
                break
            time.sleep(10 * (rnd + 1))
        return len(pending)

    step = 500
    for s in range(0, len(items), step):
        chunk = items[s:s + step]
        print(f"[{s + 1}–{s + len(chunk)}]", flush=True)
        missing = fetch(chunk)
        for wait in range(MAX_NET_WAITS):
            if missing <= NET_FAIL_RATE * len(chunk):
                break
            print(f"  lỗi {missing}/{len(chunk)}, nghi mạng tới CDN bị chặn; đợi 5 phút ({wait + 1}/{MAX_NET_WAITS})", flush=True)
            time.sleep(300)
            missing = fetch([it for it in chunk if it["download_error"]])
        json.dump(items, open(os.path.join(out, "manifest.json"), "w", encoding="utf-8"), ensure_ascii=False)
    bad = sum(1 for it in items if it["download_error"])
    print(f"XONG: {len(items) - bad}/{len(items)} ảnh tải được, lỗi {bad}", flush=True)


if __name__ == "__main__":
    main()
