"""Chọn entity cho golden set đợt 2 (tái lập được nhờ seed cố định).

30 entity ngẫu nhiên phân tầng theo category + 10 entity "giàu ca loại"
(để có đủ mẫu cho rule auto-reject). Chạy: python tools/select_golden.py
"""
import csv
import random
import unicodedata
from collections import OrderedDict

SCOPE_START_LINE = 13329
SEED = 20261007
BATCH1 = {"tuan-duong-btv-vtv", "nhat-phong", "vua-ham-nghi", "phan-hien", "nhom-ac-m",
          "truong-my-lan-cuu-chu-tich-van-thinh-phat", "phuong-loan", "tran-van-khanh",
          "nhu-binh", "nguyen-viet-thanh"}
EXCLUDE = BATCH1 | {"nguyen-van-hieu-nha-bao"}  # entity bị cắt ở dòng 13329
RANDOM_QUOTA = {"singer": 7, "historic": 4, "athletes": 4, "politicer": 4,
                "celeb": 3, "scientist": 3, "businessman": 3, "writer": 2}
SENS = ["bắt", "khởi tố", "tạm giam", "xét xử", "tòa", "toà", "biểu tình", "còng", "truy nã", "bị can", "bị cáo"]


def strip(s):
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace("đ", "d").replace("Đ", "D").lower()


def stats(rs):
    name = rs[0]["canonical_name"]
    low, un = name.lower(), strip(name)
    n = len(rs)
    return dict(
        n=n,
        variant=sum(1 for r in rs if un in strip(r["description"]) and low not in r["description"].lower()),
        no_name=sum(1 for r in rs if un not in strip(r["description"])),
        multi=sum(1 for r in rs if int(r["face_count"]) >= 3),
        small=sum(1 for r in rs if float(r["face_area_pct"]) < 2),
        sens=sum(1 for r in rs if any(k in r["description"].lower() for k in SENS)),
    )


def main():
    rows = list(csv.DictReader(open("approved-results.csv", encoding="utf-8")))[SCOPE_START_LINE - 2:]
    ents = OrderedDict()
    for r in rows:
        ents.setdefault(r["slug"], []).append(r)
    pool = {s: rs for s, rs in ents.items() if s not in EXCLUDE and 6 <= len(rs) <= 20}
    rng = random.Random(SEED)

    chosen = []
    by_cat = {}
    for s, rs in pool.items():
        by_cat.setdefault(rs[0]["category"], []).append(s)
    for cat, k in RANDOM_QUOTA.items():
        cands = sorted(by_cat.get(cat, []))
        chosen += [(s, "ngẫu nhiên") for s in rng.sample(cands, k)]

    taken = {s for s, _ in chosen}
    st = {s: stats(rs) for s, rs in pool.items() if s not in taken}
    targeted = [
        ("variant", "tên khác dấu", 3),
        ("no_name", "tiêu đề hiếm khi nhắc tên", 2),
        ("small", "nhiều mặt rất nhỏ", 2),
        ("multi", "nhiều ảnh đông người", 2),
        ("sens", "tiêu đề có từ khóa bắt/xử", 1),
    ]
    for key, label, k in targeted:
        ranked = sorted((s for s in st if s not in taken),
                        key=lambda s: (-st[s][key] / st[s]["n"], s))
        for s in ranked[:k]:
            chosen.append((s, label))
            taken.add(s)

    total = 0
    for s, why in chosen:
        rs = ents[s]
        total += len(rs)
        print(f"{s}\t{rs[0]['canonical_name']}\t{rs[0]['category']}\t{len(rs)}\t{why}")
    print("TOTAL", len(chosen), total)


if __name__ == "__main__":
    main()
