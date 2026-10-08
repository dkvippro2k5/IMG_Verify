"""Chuẩn bị dữ liệu cho tool duyệt golden set.

Đọc approved-results.csv, lấy các entity trong golden-entities, tải ảnh về
golden/images/ và ghi golden/data.js cho golden/review.html.

Chạy: python tools/build_golden.py
"""
import csv
import json
import os
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(ROOT, "approved-results.csv")
OUT_DIR = os.path.join(ROOT, "golden")
IMG_DIR = os.path.join(OUT_DIR, "images")
SCOPE_START_LINE = 13329  # dòng trong file, dòng tiêu đề là dòng 1

BATCH_1 = [
    "tuan-duong-btv-vtv",
    "nhat-phong",
    "vua-ham-nghi",
    "phan-hien",
    "nhom-ac-m",
    "truong-my-lan-cuu-chu-tich-van-thinh-phat",
    "phuong-loan",
    "tran-van-khanh",
    "nhu-binh",
    "nguyen-viet-thanh",
]
# Sinh bởi tools/select_golden.py (seed cố định).
BATCH_2 = [
    "quoc-dai", "thang-solo", "nhac-si-thai-co", "scope-5-hieuthuhai", "wean-le",
    "wukong-rapper", "viet-khang", "pham-dinh-trong", "tinh-khong-thien-su",
    "pham-nguyen-du", "vu-vi-pho-bang-khoa-1901", "tran-thi-hai-linh",
    "vu-thi-nguyet-anh", "patrik-le-giang", "tran-nguyen-bao-chau",
    "nguyen-van-hong-can-tho", "vo-van-hung", "pham-the-tung", "pham-chuyen",
    "thanh-thanh-huyen", "phan-phuong-oanh", "phuong-linh-a-hau-miss-international",
    "pham-cong-thien-triet-gia-hoc-gia", "phan-hong-giang-nghien-cuu-dich-gia",
    "vu-hai-quan", "phan-van-hung-startup", "to-manh-cuong-mobifone", "tran-thi-le",
    "tran-ninh-ho", "pham-xuan-truong", "tran-luu", "tho-nguyen-tho-nguyen",
    "nguyen-xuan-son-sonx", "nguyen-van-luyen-y-hoc", "nguyen-van-quyen",
    "van-dong-vien-cu-ta", "tu-do-ban-nhac-rock", "thuy-linh-5-dong-ke",
    "scope-5-da-lab", "tran-quoc-toan-cu-ta",
]
BATCHES = [("Đợt 1", BATCH_1), ("Đợt 2", BATCH_2)]
GOLDEN_SLUGS = [s for _, b in BATCHES for s in b]
BATCH_OF = {s: name for name, b in BATCHES for s in b}

FIELDS = [
    "entity_id", "slug", "canonical_name", "category", "kind_hint", "query",
    "sha256", "image_url", "source_url", "source_domain", "description",
    "width", "height", "bytes", "face_count", "face_area_pct", "from_db",
]

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")


def ext_of(url):
    path = url.split("?", 1)[0].lower()
    for e in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"):
        if path.endswith(e):
            return e
    return ".jpg"


def download_to(url, dest):
    """Tải url về dest nếu chưa có. Trả về None nếu thành công, chuỗi lỗi nếu thất bại."""
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        if not data:
            return "empty response"
        with open(dest, "wb") as f:
            f.write(data)
        return None
    except Exception as e:  # ghi lỗi, không dừng cả lô
        return f"{type(e).__name__}: {e}"


def download(row):
    name = row["sha256"][:16] + ext_of(row["image_url"])
    err = download_to(row["image_url"], os.path.join(IMG_DIR, name))
    return (None, err) if err else (name, None)


def main():
    os.makedirs(IMG_DIR, exist_ok=True)
    with open(CSV_PATH, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    picked = []
    for i, r in enumerate(rows):
        line_no = i + 2
        if line_no >= SCOPE_START_LINE and r["slug"] in GOLDEN_SLUGS:
            item = {k: r[k] for k in FIELDS}
            item["line_no"] = line_no
            item["batch"] = BATCH_OF[r["slug"]]
            picked.append(item)

    found = {r["slug"] for r in picked}
    missing = [s for s in GOLDEN_SLUGS if s not in found]
    if missing:
        sys.exit(f"Không tìm thấy entity: {missing}")

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(download, picked))

    errors = 0
    for item, (name, err) in zip(picked, results):
        item["local_image"] = f"images/{name}" if name else ""
        item["download_error"] = err or ""
        if err:
            errors += 1
            print(f"[lỗi] dòng {item['line_no']} {item['slug']}: {err}")

    order = {s: i for i, s in enumerate(GOLDEN_SLUGS)}
    picked.sort(key=lambda r: (order[r["slug"]], r["line_no"]))

    with open(os.path.join(OUT_DIR, "data.js"), "w", encoding="utf-8") as f:
        f.write("window.GOLDEN_DATA = ")
        json.dump(picked, f, ensure_ascii=False, indent=1)
        f.write(";\n")

    print(f"{len(picked)} ảnh, {len(GOLDEN_SLUGS)} entity, tải lỗi {errors}")
    if errors:
        print("Chạy lại script để thử tải lại các ảnh lỗi.")


if __name__ == "__main__":
    main()
