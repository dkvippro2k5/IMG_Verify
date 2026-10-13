"""Tách kết quả cuối của một đợt thành 2 file nộp, đều theo cột file gốc + reject_reason:
  1) <out1>: ảnh gốc của phạm vi (bản ghi FIRST..LAST của file gốc) với flag/reject_reason đã duyệt;
  2) <out2>: ảnh crawl mới đã duyệt (cột gốc; local_path trỏ tới ảnh đã tải, tính từ thư mục kết xuất).

Chạy: python people/tools/make_final_split.py <file gốc.csv> <FIRST> <LAST> <thư mục kết xuất> <out1.csv> <out2.csv> \
        <nhãn mới nhất.csv> [nhãn bổ sung.csv ...] -- <thư mục crawl 1> [thư mục crawl 2 ...]
Nhãn: file đứng trước được ưu tiên; file sau chỉ dùng cho ảnh mà các file trước không có.
Nối bằng entity_id + sha256. Ảnh gốc không có nhãn ở bất kỳ file nào sẽ bị báo và bỏ qua.
"""
import csv
import glob
import os
import sys


def rd(p):
    return list(csv.DictReader(open(p, encoding="utf-8-sig", newline="")))


def main():
    a = sys.argv[1:]
    src, first, last, outdir, out1, out2 = a[0], int(a[1]), int(a[2]), a[3], a[4], a[5]
    sep = a.index("--")
    label_files, crawl_dirs = a[6:sep], a[sep + 1:]
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    labels = {}  # (entity_id, sha256) -> (flag, reasons, nguồn)
    for i, f in enumerate(label_files):
        for r in rd(f):
            k = (r["entity_id"], r["sha256"])
            if k not in labels and r["flag"]:
                labels[k] = (r["flag"], r["reasons"] if r["flag"] == "rejected" else "", i)

    rows = rd(src)
    cols = list(rows[0].keys()) + ["reject_reason"]
    scope = rows[first - 1:last]

    # 1) ảnh gốc của phạm vi
    n1, miss, by_src = 0, 0, {}
    with open(out1, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in scope:
            l = labels.get((r["entity_id"], r["sha256"]))
            if l is None:
                miss += 1
                continue
            r = dict(r)
            r["flag"], r["reject_reason"] = l[0], l[1]
            w.writerow(r)
            n1 += 1
            by_src[l[2]] = by_src.get(l[2], 0) + 1
    print(f"[1] {n1}/{len(scope)} ảnh gốc -> {out1} (thiếu nhãn {miss}); nguồn nhãn theo thứ tự file: {by_src}")

    # 2) ảnh crawl mới
    seen, n2, nolab = set(), 0, 0
    cnt = {}
    with open(out2, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for d in crawl_dirs:
            for p in sorted(glob.glob(os.path.join(d, "**", "extra-results.csv"), recursive=True)):
                rel = os.path.relpath(os.path.dirname(p), outdir).replace(os.sep, "/")
                for r in rd(p):
                    k = (r["entity_id"], r["sha256"])
                    if k in seen:
                        continue
                    seen.add(k)
                    l = labels.get(k)
                    if l is None:
                        nolab += 1
                        continue
                    o = {c: r.get(c, "") for c in cols}
                    o["local_path"] = f"{rel}/{r['local_path']}"
                    o["flag"], o["reject_reason"] = l[0], l[1]
                    w.writerow(o)
                    n2 += 1
                    cnt[l[0]] = cnt.get(l[0], 0) + 1
    print(f"[2] {n2} ảnh crawl mới -> {out2} (chưa có nhãn, bỏ qua: {nolab}); {cnt}")


if __name__ == "__main__":
    main()
