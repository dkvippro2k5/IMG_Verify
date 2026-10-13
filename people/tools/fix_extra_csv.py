"""Sửa các extra-results.csv bị lệch cột (dòng dài hơn tiêu đề đúng 2 cột: line_no, reject_reason chèn sau flag).

Chạy: python people/tools/fix_extra_csv.py <thư mục gốc chứa các extra-results.csv>
Ghi đè từng file về tiêu đề thống nhất (bỏ hai cột chèn thừa), sao lưu bản cũ thành extra-results.csv.bak.
"""
import csv
import glob
import os
import shutil
import sys

DROP = {"line_no", "reject_reason"}


def main():
    root = sys.argv[1]
    total = fixed = 0
    for p in sorted(glob.glob(os.path.join(root, "**", "extra-results.csv"), recursive=True)):
        rows = list(csv.reader(open(p, encoding="utf-8-sig", newline="")))
        head = rows[0]
        cut = head.index("flag") + 1
        full = head if DROP & set(head) else head[:cut] + ["line_no", "reject_reason"] + head[cut:]
        out, bad = [], 0
        for r in rows[1:]:
            if len(r) == len(full):
                d = dict(zip(full, r))
            elif len(r) == len(head):
                d = dict(zip(head, r))
            else:
                bad += 1
                continue
            if len(r) != len(head):
                fixed += 1
            out.append(d)
        cols = [c for c in full if c not in DROP]
        shutil.copy(p, p + ".bak")
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8-sig", newline="") as f:  # ghi ra file tạm rồi mới thay, để lỗi giữa chừng không làm mất dữ liệu
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(out)
        os.replace(tmp, p)
        total += len(out)
        print(f"{p}: {len(out)} dòng, cột {len(cols)}, dòng hỏng bỏ qua {bad}")
    print(f"tổng {total} dòng; số dòng đã sửa lệch cột {fixed}")


if __name__ == "__main__":
    main()
