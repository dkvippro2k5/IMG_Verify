"""Lập danh sách entity cần crawl thêm ảnh cho một đợt, từ file gốc + nhãn đã duyệt.

Chạy: python people/tools/make_low_list.py <file gốc.csv> <FIRST> <LAST> <file nhãn đã duyệt.csv> <thư mục ra> [--target 40] [--min-add 15]
  FIRST..LAST: khoảng bản ghi (không tính dòng tiêu đề) thuộc phạm vi của đợt; dùng 1 và số dòng nếu lấy cả file.
  File nhãn cần cột entity_id, sha256, flag (flag=approved/rejected) - ví dụ file xuất từ review.html hoặc file giao đã duyệt.
Ghi vào <thư mục ra>: low-ref.csv (entity có >=1 ảnh approved, xếp từ nhiều ảnh nhất = nổi tiếng nhất lên đầu),
  low-noref.csv (entity chưa có ảnh approved nào), low-image-entities.csv (cả hai).
Số ảnh cần thêm mỗi entity (cột need_more_to_reach_10, tên giữ để tương thích crawl_funnel.py) = max(min-add, target - approved).
"""
import argparse
import collections as C
import csv
import os


def rd(p):
    return list(csv.DictReader(open(p, encoding="utf-8-sig", newline="")))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("first", type=int)
    ap.add_argument("last", type=int)
    ap.add_argument("labels")
    ap.add_argument("outdir")
    ap.add_argument("--target", type=int, default=40)
    ap.add_argument("--min-add", type=int, default=15)
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    scope = rd(a.src)[a.first - 1:a.last]
    info = {}
    for r in scope:
        info.setdefault(r["entity_id"], r)
    lab = {(r["entity_id"], r["sha256"]): r["flag"] for r in rd(a.labels) if r.get("flag")}
    tot, ap_, rj = C.Counter(), C.Counter(), C.Counter()
    unl = 0
    for r in scope:
        e = r["entity_id"]
        tot[e] += 1
        f = lab.get((e, r["sha256"]))
        if f == "approved":
            ap_[e] += 1
        elif f == "rejected":
            rj[e] += 1
        else:
            unl += 1
    cols = ["entity_id", "slug", "canonical_name", "category", "total_images", "approved", "rejected", "need_more_to_reach_10"]

    def row(e):
        i = info[e]
        return dict(entity_id=e, slug=i["slug"], canonical_name=i["canonical_name"], category=i["category"],
                    total_images=tot[e], approved=ap_[e], rejected=rj[e], need_more_to_reach_10=max(a.min_add, a.target - ap_[e]))

    ref = sorted([e for e in info if ap_[e] >= 1], key=lambda e: -ap_[e])
    noref = [e for e in info if ap_[e] == 0]
    for name, es in (("low-ref.csv", ref), ("low-noref.csv", noref), ("low-image-entities.csv", ref + noref)):
        with open(os.path.join(a.outdir, name), "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(row(e) for e in es)
    print(f"{len(scope)} ảnh, {len(info)} entity; chưa có nhãn {unl} ảnh; có ảnh tham chiếu {len(ref)} entity "
          f"(cần thêm {sum(max(a.min_add, a.target - ap_[e]) for e in ref)} ảnh), chưa có ảnh approved {len(noref)} entity -> {a.outdir}")


if __name__ == "__main__":
    main()
