"""Đo các rule tự loại (danh tính) trên golden.

Với mỗi entity: gom cụm các mặt, chọn cụm chính (nhiều ảnh nhất, ưu tiên ảnh có tên khớp trong
tiêu đề), rồi tính cho từng ảnh độ giống lớn nhất giữa các mặt trong ảnh và cụm chính.
Sau đó đo precision của từng rule loại so với nhãn golden.

Chạy: .venv/Scripts/python tools/eval_identity.py [đường_dẫn_nhãn.csv]
"""
import csv
import json
import re
import os
import sys
import unicodedata
from collections import defaultdict

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLDEN = os.path.join(ROOT, "golden")
LABELS = os.path.join(GOLDEN, "golden-labels-v2.csv")  # đổi bằng đối số khi chạy trực tiếp
# File của mentor (đã lọc thêm): chỉ đo trên ảnh còn trong file này; lấy thêm cột cluster.
CURRENT_CSV = os.path.join(ROOT, "data", "approved-results (1).csv")

MIN_FACE_SCORE = 0.6
MIN_FACE_PX = 24
LINK_SIM = 0.40  # hai mặt coi là cùng người khi cosine ≥ ngưỡng này (dùng để gom cụm)


# ---------- tên ----------
def strip(s):
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace("đ", "d").replace("Đ", "D").lower()


def clean(tok):
    return "".join(c for c in tok if c.isalnum() or c == "&")


ROLE_PREFIXES = ("nhạc sĩ", "ca sĩ", "nghệ sĩ", "vua", "nhóm", "ban nhạc", "nsnd", "nsưt", "gs", "pgs", "ts")


def name_forms(name):
    """Các dạng tên để so: bỏ phần trong ngoặc ("Thắng (solo)" → "Thắng") và chức danh đứng đầu
    ("Nhạc sĩ Thái Cơ" → "Thái Cơ"). Dạng đầy đủ (đã bỏ ngoặc) luôn được giữ."""
    base = re.sub(r"\s*\(.*?\)\s*", " ", name).strip()
    forms = [base]
    low = base.lower()
    for p in ROLE_PREFIXES:
        if low.startswith(p + " ") and len(base) > len(p) + 1:
            forms.append(base[len(p) + 1:].strip())
    return forms


def name_status(desc, name):
    """exact / variant / no_name trên mọi dạng tên; exact thắng variant."""
    res = [_name_status(desc, f) for f in name_forms(name)]
    return "exact" if "exact" in res else ("variant" if "variant" in res else "no_name")


def _name_status(desc, name):
    """exact / variant / no_name, cùng quy ước với golden/review.html."""
    toks = [clean(t) for t in unicodedata.normalize("NFC", desc).split()]
    toks = [t for t in toks if t]
    ntoks = [clean(t) for t in unicodedata.normalize("NFC", name).split()]
    ntoks = [t for t in ntoks if t]
    n = len(ntoks)
    name_exact = " ".join(ntoks).lower()
    name_strip = strip(name_exact)
    exact = variant = 0
    for k in range(len(toks) - n + 1):
        win = " ".join(toks[k:k + n]).lower()
        if strip(win) != name_strip:
            continue
        if win == name_exact or strip(win) == win or name_strip == name_exact:
            exact += 1
        else:
            variant += 1
    return "exact" if exact else ("variant" if variant else "no_name")


# ---------- dữ liệu ----------
def load():
    text = open(os.path.join(GOLDEN, "data.js"), encoding="utf-8").read()
    data = {r["line_no"]: r for r in json.loads(text[text.index("["):text.rindex("]") + 1])}
    faces = {r["line_no"]: r for r in json.load(open(os.path.join(GOLDEN, "features", "faces.json"), encoding="utf-8"))}
    embs = np.load(os.path.join(GOLDEN, "features", "embeddings.npy"))
    labels = {int(r["line_no"]): r for r in csv.DictReader(open(LABELS, encoding="utf-8-sig"))}
    current = {(r["entity_id"], r["sha256"]): r["cluster"]
               for r in csv.DictReader(open(CURRENT_CSV, encoding="utf-8-sig"))}
    # Khóa nối là entity_id + sha256, không phụ thuộc số dòng.
    for ln in list(data):
        key = (data[ln]["entity_id"], data[ln]["sha256"])
        if key not in current:
            del data[ln]
        else:
            data[ln]["mentor_cluster"] = current[key]
    return data, faces, embs, labels


def good_faces(rec):
    return [f for f in rec.get("faces", []) if f["score"] >= MIN_FACE_SCORE and f["size_px"] >= MIN_FACE_PX]


def cluster_entity(lines, faces, embs, names):
    """Gom cụm liên kết đơn trên đồ thị mặt (cosine ≥ LINK_SIM, chỉ nối mặt khác ảnh).
    Trả về: danh sách cụm [(điểm, số ảnh, số ảnh có tên khớp, set chỉ số emb)], sắp giảm dần."""
    nodes = [(ln, f["emb"]) for ln in lines for f in good_faces(faces[ln])]
    if not nodes:
        return []
    idx = np.array([e for _, e in nodes])
    sim = embs[idx] @ embs[idx].T
    parent = list(range(len(nodes)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            if nodes[i][0] != nodes[j][0] and sim[i, j] >= LINK_SIM:
                parent[find(i)] = find(j)
    groups = defaultdict(list)
    for i in range(len(nodes)):
        groups[find(i)].append(i)
    out = []
    for members in groups.values():
        imgs = {nodes[i][0] for i in members}
        named = sum(1 for ln in imgs if names[ln] == "exact")
        out.append((len(imgs) + named, len(imgs), named, {nodes[i][1] for i in members}))
    out.sort(key=lambda c: (-c[0], -c[1]))
    return out


def anchor_similarity(by_ent, data, faces, embs, min_anchor_imgs=2):
    """Mốc = mặt lớn nhất của mỗi ảnh có tên khớp đúng. Gom cụm các mốc, giữ cụm mốc lớn nhất
    (≥ min_anchor_imgs ảnh). Trả về {dòng: độ giống lớn nhất giữa mặt trong ảnh và cụm mốc,
    không tính chính ảnh đó}. Entity không đủ mốc thì không có giá trị."""
    out = {}
    for slug, lines in by_ent.items():
        anchors = []
        for ln in lines:
            if name_status(data[ln]["description"], data[ln]["canonical_name"]) != "exact":
                continue
            gf = good_faces(faces[ln])
            if gf:
                anchors.append((ln, max(gf, key=lambda f: f["area_pct"])["emb"]))
        if len(anchors) < min_anchor_imgs:
            continue
        idx = np.array([e for _, e in anchors])
        sim = embs[idx] @ embs[idx].T
        parent = list(range(len(anchors)))

        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a

        for i in range(len(anchors)):
            for j in range(i + 1, len(anchors)):
                if sim[i, j] >= LINK_SIM:
                    parent[find(i)] = find(j)
        groups = defaultdict(list)
        for i in range(len(anchors)):
            groups[find(i)].append(i)
        best = max(groups.values(), key=len)
        if len(best) < min_anchor_imgs:
            continue
        ref = [anchors[i] for i in best]
        for ln in lines:
            gf = good_faces(faces[ln])
            r = np.array([e for a_ln, e in ref if a_ln != ln])
            if not gf or not len(r):
                out[ln] = -1.0 if not gf else None
                continue
            out[ln] = float(max(np.max(embs[r] @ embs[f["emb"]]) for f in gf))
    return {k: v for k, v in out.items() if v is not None}


def main():
    global LABELS
    if len(sys.argv) > 1:
        LABELS = sys.argv[1]
    data, faces, embs, labels = load()
    by_ent = defaultdict(list)
    for ln, r in data.items():
        by_ent[r["slug"]].append(ln)

    rows = []
    ent_info = {}
    for slug, lines in by_ent.items():
        names = {ln: name_status(data[ln]["description"], data[ln]["canonical_name"]) for ln in lines}
        clusters = cluster_entity(lines, faces, embs, names)
        main = clusters[0] if clusters else None
        second = clusters[1] if len(clusters) > 1 else None
        n_img = len(lines)
        main_imgs = main[1] if main else 0
        ent_info[slug] = dict(
            n=n_img, main_imgs=main_imgs, main_named=main[2] if main else 0,
            second_imgs=second[1] if second else 0,
            share=main_imgs / n_img,
        )
        main_emb = np.array(sorted(main[3])) if main else np.array([], dtype=int)
        for ln in lines:
            gf = good_faces(faces[ln])
            own = {f["emb"] for f in gf}
            ref = np.array([e for e in main_emb if e not in own], dtype=int)
            best, best_face = -1.0, None
            if len(ref) and gf:
                for f in gf:
                    s = float(np.max(embs[ref] @ embs[f["emb"]]))
                    if s > best:
                        best, best_face = s, f
            largest = max((f["area_pct"] for f in gf), default=0.0)
            rows.append(dict(
                line=ln, slug=slug, label=labels[ln]["flag"], reasons=labels[ln]["reasons"],
                name=names[ln], n_faces=len(gf), best_sim=best,
                prominence=(best_face["area_pct"] / largest) if best_face and largest else 0.0,
                ambiguous=data[ln]["mentor_cluster"] == "ambiguous",
            ))

    total_rej = sum(1 for r in rows if r["label"] == "rejected")
    print(f"Golden: {len(rows)} ảnh, rejected {total_rej}\n")

    def report(name, pred):
        hit = [r for r in rows if pred(r)]
        if not hit:
            print(f"{name:58} loại   0")
            return
        ok = sum(1 for r in hit if r["label"] == "rejected")
        print(f"{name:58} loại {len(hit):3}  đúng {ok:3}  precision {100 * ok / len(hit):5.1f}%  "
              f"bắt được {100 * ok / total_rej:4.1f}% số rejected")
        return hit

    print("== Rule đơn ==")
    report("R1 tiêu đề có tên khác dấu", lambda r: r["name"] == "variant")
    report("R1b khác dấu VÀ ambiguous", lambda r: r["name"] == "variant" and r["ambiguous"])
    for t in (0.20, 0.30):
        report(f"R5 ambiguous VÀ mặt giống < {t:.2f}", lambda r, t=t: r["ambiguous"] and r["n_faces"] > 0 and r["best_sim"] < t)
    report("R2 không có mặt đủ tốt", lambda r: r["n_faces"] == 0)
    for t in (0.10, 0.15, 0.20, 0.25, 0.30):
        report(f"R3 mặt giống cụm chính < {t:.2f}", lambda r, t=t: r["n_faces"] > 0 and r["best_sim"] < t)
    print("\n== Kết hợp tên + mặt ==")
    for t in (0.20, 0.25, 0.30, 0.35):
        report(f"R4 tiêu đề không có tên VÀ mặt giống < {t:.2f}",
               lambda r, t=t: r["name"] == "no_name" and r["n_faces"] > 0 and r["best_sim"] < t)
    print("\n== Cách 2: mốc danh tính = mặt chính của ảnh có tên khớp đúng ==")
    anchor_sim = anchor_similarity(by_ent, data, faces, embs)
    for r in rows:
        r["anchor_sim"] = anchor_sim.get(r["line"])  # None nếu entity không có mốc
    has_anchor = lambda r: r["anchor_sim"] is not None
    n_no_anchor = sum(1 for r in rows if not has_anchor(r))
    print(f"   ảnh thuộc entity không đủ mốc (→ người duyệt): {n_no_anchor}")
    for t in (0.10, 0.15, 0.20, 0.25):
        report(f"A1 mặt giống mốc < {t:.2f}", lambda r, t=t: has_anchor(r) and r["n_faces"] > 0 and r["anchor_sim"] < t)
    for t in (0.15, 0.20, 0.25, 0.30):
        report(f"A2 không có tên VÀ mặt giống mốc < {t:.2f}",
               lambda r, t=t: has_anchor(r) and r["name"] == "no_name" and r["n_faces"] > 0 and r["anchor_sim"] < t)
    print("   Ca A2 (< 0.25) loại nhầm ảnh approved:")
    for r in rows:
        if has_anchor(r) and r["name"] == "no_name" and r["n_faces"] > 0 and r["anchor_sim"] < 0.25 and r["label"] == "approved":
            print(f"     dòng {r['line']} {r['slug']} sim={r['anchor_sim']:.2f} mặt={r['n_faces']}")

    print("\n== Rule mức entity ==")
    weak = {s for s, e in ent_info.items() if e["main_named"] == 0}
    report("E1 cụm chính không có ảnh nào có tên khớp → loại cả entity", lambda r: r["slug"] in weak)
    print("   entity bị E1 loại:", ", ".join(sorted(weak)))

    print("\n== Ca R3 (< 0.10) loại nhầm ảnh approved ==")
    for r in rows:
        if r["n_faces"] > 0 and r["best_sim"] < 0.10 and r["label"] == "approved":
            print(f"   dòng {r['line']} {r['slug']} sim={r['best_sim']:.2f} mặt={r['n_faces']} tên={r['name']}")

    print("\n== Cảnh báo (không tự loại) ==")
    report("W1 tiêu đề không nhắc tên", lambda r: r["name"] == "no_name")
    report("W3 mentor đánh cluster = ambiguous", lambda r: r["ambiguous"])
    report("W2 mặt khớp không phải mặt lớn nhất (< 50%)", lambda r: r["n_faces"] > 1 and 0 < r["prominence"] < 0.5)

    print("\n== Entity: cụm chính yếu ==")
    for slug, e in sorted(ent_info.items(), key=lambda kv: kv[1]["share"]):
        lab = [labels[ln]["flag"] for ln in by_ent[slug]]
        a = lab.count("approved")
        print(f"  {slug[:40]:40} ảnh {e['n']:2}  cụm chính {e['main_imgs']:2} (tên khớp {e['main_named']:2})"
              f"  cụm 2 {e['second_imgs']:2}  golden approved {a:2}")

    out = os.path.join(GOLDEN, "features", "identity_rows.json")
    json.dump(rows, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\nChi tiết từng ảnh: {out}")


if __name__ == "__main__":
    main()
