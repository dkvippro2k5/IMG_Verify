"""Dựng tool duyệt cho phạm vi làm việc: scope/review.html + scope/data.js.

Ghép scope/manifest.json với scope/auto_labels.csv (kết quả apply_rules.py). Ảnh tự loại (không thuộc
mẫu kiểm tra) được ẩn mặc định và tính là xong; người duyệt chỉ cần xem ảnh to_review + mẫu kiểm tra.

Chạy: python tools/build_review.py
"""
import csv
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCOPE = os.path.join(ROOT, "scope")
TEMPLATE = os.path.join(ROOT, "golden", "review.html")
GROUP_SIZE = 50  # số entity mỗi nhóm trên thanh bên
AUTO_FIELDS = ["auto_flag", "auto_reasons", "rules", "warnings", "name_status", "n_faces", "best_sim", "anchor_sim", "audit"]


def main():
    items = json.load(open(os.path.join(SCOPE, "manifest.json"), encoding="utf-8"))
    auto = {(r["entity_id"], r["sha256"]): r
            for r in csv.DictReader(open(os.path.join(SCOPE, "auto_labels.csv"), encoding="utf-8-sig"))}

    # Chỉ đưa vào tool các ảnh đã qua pipeline (chạy theo batch thì tool lớn dần).
    items = [it for it in items if (it["entity_id"], it["sha256"]) in auto]
    items.sort(key=lambda it: it["line_no"])
    order = list(dict.fromkeys(it["slug"] for it in items))
    labels_path = os.path.join(SCOPE, "batch_labels.json")
    batch_labels = json.load(open(labels_path, encoding="utf-8")) if os.path.exists(labels_path) else {}
    group_of = {s: i // GROUP_SIZE for i, s in enumerate(order)}
    ranges = {}
    for it in items:
        g = group_of[it["slug"]]
        lo, hi = ranges.get(g, (it["line_no"], it["line_no"]))
        ranges[g] = (min(lo, it["line_no"]), max(hi, it["line_no"]))

    # Nhãn golden đã gán (golden-labels-v2.csv, nối qua golden/data.js) → điền sẵn, không cần duyệt lại.
    gold = {}
    gdata_path = os.path.join(ROOT, "golden", "data.js")
    glabel_path = os.path.join(ROOT, "golden", "golden-labels-v2.csv")
    if os.path.exists(gdata_path) and os.path.exists(glabel_path):
        text = open(gdata_path, encoding="utf-8").read()
        gkey = {r["line_no"]: (r["entity_id"], r["sha256"]) for r in json.loads(text[text.index("["):text.rindex("]") + 1])}
        for r in csv.DictReader(open(glabel_path, encoding="utf-8-sig")):
            k = gkey.get(int(r["line_no"]))
            if k and r["flag"]:
                gold[k] = r

    out = []
    for it in items:
        a = auto[(it["entity_id"], it["sha256"])]
        g = group_of[it["slug"]]
        row = dict(it)
        row["local_image"] = "" if it.get("download_error") else f"images/{it['image_file']}"
        row["batch"] = batch_labels.get(it["slug"]) or f"Nhóm {g + 1} · dòng {ranges[g][0]}–{ranges[g][1]}"
        for k in AUTO_FIELDS:
            row[k] = a[k]
        g = gold.get((it["entity_id"], it["sha256"]))
        if g:
            row.update(gold_flag=g["flag"], gold_reasons=g["reasons"], gold_identity=g["identity"])
        out.append(row)

    with open(os.path.join(SCOPE, "data.js"), "w", encoding="utf-8") as f:
        f.write("window.GOLDEN_DATA = ")
        json.dump(out, f, ensure_ascii=False)
        f.write(";\n")

    html = open(TEMPLATE, encoding="utf-8").read()
    cfg = '<script>window.REVIEW_CONFIG = { storeKey: "scope-review-v1", filePrefix: "scope-labels" };</script>\n'
    html = html.replace('<title>Golden Review</title>', '<title>Scope Review</title>')
    html = html.replace('<h1>Golden Review</h1>', '<h1>Duyệt phạm vi</h1>')
    html = html.replace('<script src="data.js"></script>', cfg + '<script src="data.js"></script>')
    path = os.path.join(SCOPE, "review.html")
    if not os.path.exists(path) or open(path, encoding="utf-8").read() != html:
        open(path, "w", encoding="utf-8").write(html)

    n_auto = sum(1 for r in out if r["auto_flag"] == "rejected" and r["audit"] != "1")
    n_gold = sum(1 for r in out if r.get("gold_flag"))
    print(f"{len(out)} ảnh, {len(order)} entity, {len(ranges)} nhóm; tự loại (ẩn) {n_auto}, "
          f"đã có nhãn golden {n_gold}, cần duyệt {len(out) - n_auto - n_gold}")


if __name__ == "__main__":
    main()
