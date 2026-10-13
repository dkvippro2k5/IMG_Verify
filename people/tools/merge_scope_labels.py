"""Gộp file gốc với nhãn đã duyệt của một phạm vi thành file kết quả: cột gốc + flag đã duyệt + reject_reason.

Chạy: python people/tools/merge_scope_labels.py "<approved-results gốc>.csv" "<nhãn xuất từ review.html>.csv" "<file ra>.csv"
Nối bằng entity_id + sha256; giữ đúng thứ tự và giá trị gốc của các dòng có trong file nhãn, không thêm/cắt dòng.
"""
import csv
import sys


def main():
    src, labels, out = sys.argv[1:4]
    rd = lambda p: list(csv.DictReader(open(p, encoding="utf-8-sig", newline="")))
    lab = {(r["entity_id"], r["sha256"]): r for r in rd(labels)}
    rows = rd(src)
    cols = list(rows[0].keys()) + ["reject_reason"]
    n = 0
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            l = lab.get((r["entity_id"], r["sha256"]))
            if l is None:
                continue
            r["flag"], r["reject_reason"] = l["flag"], l["reasons"]
            w.writerow(r)
            n += 1
    print(f"{n} dòng (nhãn có {len(lab)}) -> {out}")


if __name__ == "__main__":
    main()
