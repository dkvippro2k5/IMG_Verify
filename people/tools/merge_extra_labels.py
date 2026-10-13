"""Gộp ảnh crawl thêm với nhãn đã duyệt thành file kết quả cuối cùng (cùng cột file gốc + reject_reason).

Chạy: python people/tools/merge_extra_labels.py "<file nhãn xuất từ review-extra>.csv" [file_ra.csv]
Nối bằng entity_id + sha256. Chỉ ảnh đã có nhãn được ghi ra; ảnh chưa duyệt bị bỏ và được báo số lượng.
Cột: toàn bộ cột file gốc (flag = nhãn đã duyệt) + reject_reason + source_batch, origin, search_query, wikidata_id,
ref_type, trust, id_sim, license, image_file (đường dẫn ảnh đã tải, tính từ people/output-batch4/).
Kèm thống kê trước/sau cho các entity <10 ảnh approved.
"""
import collections as C
import csv
import glob
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
B4 = os.path.join(ROOT, "people", "output-batch4")
CRAWL_DIRS = ["crawl-extra-v7", "crawl-extra-ref", "crawl-extra-ref2", "crawl-extra-rej", "crawl-extra-noref"]
EXTRA = ["reject_reason", "source_batch", "origin", "search_query", "wikidata_id", "ref_type", "trust", "id_sim", "license", "image_file"]


def rd(p):
    return list(csv.DictReader(open(p, encoding="utf-8-sig", newline="")))


def main():
    labels_path = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(B4, "DuongVanKien_crawl-extra-results.csv")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    lab = {(r["entity_id"], r["sha256"]): r for r in rd(labels_path)}
    base_cols = list(rd(os.path.join(B4, "approved-results (4).csv"))[0].keys())
    cols = base_cols + EXTRA

    rows, seen = [], set()
    for d in CRAWL_DIRS:
        for p in sorted(glob.glob(os.path.join(B4, d, "**", "extra-results.csv"), recursive=True)):
            rel = os.path.relpath(os.path.dirname(p), B4).replace(os.sep, "/")
            for r in rd(p):
                k = (r["entity_id"], r["sha256"])
                if k not in seen:
                    seen.add(k)
                    r["_dir"] = rel
                    rows.append(r)

    out, skipped = [], 0
    for r in rows:
        l = lab.get((r["entity_id"], r["sha256"]))
        if not l or not l["flag"]:
            skipped += 1
            continue
        o = {c: r.get(c, "") for c in cols}
        o["flag"] = l["flag"]
        o["reject_reason"] = l["reasons"] if l["flag"] == "rejected" else ""
        o["image_file"] = f"{r['_dir']}/{r['local_path']}"
        out.append(o)
    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(out)
    print(f"{len(out)} dòng -> {out_path} (bỏ {skipped} ảnh chưa có nhãn); {dict(C.Counter(o['flag'] for o in out))}")

    merged = rd(os.path.join(B4, "DuongVanKien_merged-batch4-results.csv"))
    before = C.Counter(r["entity_id"] for r in merged if r["flag"] == "approved")
    ents = {r["entity_id"] for r in merged}
    add = C.Counter(o["entity_id"] for o in out if o["flag"] == "approved")
    low = [e for e in ents if before[e] < 10]
    after = {e: before[e] + add[e] for e in low}
    zero = [e for e in low if before[e] == 0]
    print(f"entity <10 ảnh approved: {len(low)}; sau crawl: đủ >=10: {sum(a >= 10 for a in after.values())}, "
          f"còn <10: {sum(a < 10 for a in after.values())}, còn 0 ảnh: {sum(a == 0 for a in after.values())}")
    print(f"entity được thêm >=1 ảnh approved: {sum(1 for e in low if add[e])}; tổng ảnh approved thêm: {sum(add[e] for e in low)}")
    print(f"nhóm 0 ảnh approved ({len(zero)}): có >=1 ảnh: {sum(add[e] > 0 for e in zero)}, >=5 ảnh: {sum(add[e] >= 5 for e in zero)}")
    print(f"tổng approved trên nhóm <10: trước {sum(before[e] for e in low)}, sau {sum(after.values())}")
    for key in ("trust", "origin"):
        print(key, {v: (sum(1 for o in out if o[key] == v and o["flag"] == "approved"), sum(1 for o in out if o[key] == v))
                    for v in sorted({o[key] for o in out})}, "(approved/tổng)")
    print("phân bố số ảnh approved sau crawl:", sorted(C.Counter(after.values()).items()))


if __name__ == "__main__":
    main()
