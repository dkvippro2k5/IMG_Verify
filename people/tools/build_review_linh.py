"""Dựng tool duyệt lại phần của Linh (entity 1-164, approved-results (3).csv): people/review-linh/.

Nhãn của Linh điền sẵn (hiện là nhãn tham chiếu "Linh"); người duyệt xem lại, sửa nếu cần, export CSV.
Chạy: .venv/Scripts/python -u people/tools/build_review_linh.py
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
LINH = os.path.join(PEOPLE, "data", "approved-results-Linh-entity-1-to-164.csv")
TEMPLATE = os.path.join(PEOPLE, "golden", "review.html")
OUT = os.path.join(PEOPLE, "review-linh")
IMG = os.path.join(OUT, "images")
GROUP_SIZE = 50

# Câu của Linh → mã nội bộ của tool
PHRASE = {
    "Không cùng người / Sai người": "wrong_person",
    "Tiêu đề nói người khác": "name_mismatch",
    "Không cùng người": "wrong_person",
    "Chưa xác định được": "unresolved",
    "Không rõ / Khó nhận diện": "hard_to_identify",
    "Không nổi bật": "not_prominent",
    "Không có người / Ảnh lỗi": "no_person",
}


def main():
    os.makedirs(IMG, exist_ok=True)
    lines = {}
    for i, r in enumerate(csv.DictReader(open(SRC, encoding="utf-8-sig", newline=""))):
        lines[(r["entity_id"], r["sha256"])] = (i + 2, r)
    linh = list(csv.DictReader(open(LINH, encoding="utf-8-sig", newline="")))

    items = []
    for l in linh:
        ln, r = lines[(l["entity_id"], l["sha256"])]
        codes = []
        for ph in (p.strip() for p in (l["reject_reason"] or "").split(";") if p.strip()):
            c = PHRASE.get(ph)
            if c is None:
                sys.exit(f"Câu lý do lạ: {ph!r}")
            if c not in codes:
                codes.append(c)
        it = {k: r[k] for k in ("entity_id", "slug", "canonical_name", "category", "kind_hint", "query", "sha256",
                                "image_url", "source_url", "source_domain", "description", "width", "height",
                                "bytes", "face_count", "face_area_pct", "from_db")}
        flag = l["flag"]
        it.update(line_no=ln, mentor_cluster=r["cluster"], download_error="",
                  image_file=r["sha256"][:16] + ext_of(r["image_url"]),
                  gold_flag=flag, gold_reasons=";".join(codes) if flag == "rejected" else "",
                  gold_identity="match" if flag == "approved" else ("unsure" if "unresolved" in codes else "other"),
                  auto_flag="", auto_reasons="", rules="", warnings="", name_status="", n_faces="", best_sim="",
                  anchor_sim="", audit="0")
        items.append(it)
    items.sort(key=lambda it: it["line_no"])

    pending = list(items)
    for rnd in range(4):
        with ThreadPoolExecutor(max_workers=6) as pool:
            errs = list(pool.map(lambda it: download_to(it["image_url"], os.path.join(IMG, it["image_file"])), pending))
        for it, e in zip(pending, errs):
            it["download_error"] = e or ""
        pending = [it for it in pending if it["download_error"]]
        print(f"vòng {rnd + 1}: còn lỗi {len(pending)}/{len(items)}", flush=True)
        if not pending:
            break
        time.sleep(10 * (rnd + 1))

    order = list(dict.fromkeys(it["slug"] for it in items))
    group = {s: i // GROUP_SIZE for i, s in enumerate(order)}
    for it in items:
        it["local_image"] = "" if it["download_error"] else f"images/{it['image_file']}"
        it["batch"] = f"Linh · entity {group[it['slug']] * GROUP_SIZE + 1}–{min(len(order), (group[it['slug']] + 1) * GROUP_SIZE)}"

    with open(os.path.join(OUT, "data.js"), "w", encoding="utf-8") as f:
        f.write("window.GOLDEN_DATA = ")
        json.dump(items, f, ensure_ascii=False)
        f.write(";\n")
    html = open(TEMPLATE, encoding="utf-8").read()
    cfg = '<script>window.REVIEW_CONFIG = { storeKey: "linh-review-v1", filePrefix: "linh-review-labels" };</script>\n'
    html = html.replace("<title>Golden Review</title>", "<title>Duyệt lại phần của Linh</title>")
    html = html.replace("<h1>Golden Review</h1>", "<h1>Duyệt lại phần của Linh</h1>")
    html = html.replace('<script src="data.js"></script>', cfg + '<script src="data.js"></script>')
    html = html.replace("golden: ${esc(r.gold_flag)}", "Linh: ${esc(r.gold_flag)}")
    open(os.path.join(OUT, "review.html"), "w", encoding="utf-8").write(html)
    print(f"{len(items)} ảnh, {len(order)} entity, lỗi tải {len(pending)} → {OUT}", flush=True)


if __name__ == "__main__":
    main()
