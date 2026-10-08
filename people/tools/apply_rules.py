"""Áp rule tự loại (phương án B, 97,8% trên golden) và sinh nhãn sơ bộ.

Rule tự loại (rejected):
  R1  tiêu đề có tên khác dấu với canonical_name                          → name_mismatch
  A2  tiêu đề không có tên VÀ mặt giống ảnh mốc < 0,25                     → wrong_person
  R4  tiêu đề không có tên VÀ mặt giống cụm chính < 0,30                   → wrong_person
Gợi ý approved (P4, 216/216 trên golden; KHÔNG tự duyệt, người duyệt xác nhận):
  tiêu đề có tên khớp đúng VÀ mặt giống cụm chính ≥ 0,5 VÀ giống ảnh mốc ≥ 0,5
  VÀ mặt chính trội (một mặt, hoặc lớn gấp 2 mặt thứ hai) VÀ mặt ≥ 64px VÀ mentor không đánh ambiguous
Còn lại: to_review (người duyệt), kèm cảnh báo.
Mẫu kiểm tra: 10% ảnh bị tự loại (seed cố định) đánh dấu audit=1 để người duyệt xem lại.

Chạy:
  .venv/Scripts/python tools/apply_rules.py scope    → scope/auto_labels.csv
  .venv/Scripts/python tools/apply_rules.py golden   → kiểm tra lại precision trên golden
"""
import csv
import json
import os
import random
import sys
from collections import defaultdict

import numpy as np

from eval_identity import anchor_similarity, cluster_entity, good_faces, name_status

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A2_THRESH = 0.25
P4_SIM = 0.50
P4_MIN_PX = 64
P4_DOMINANCE = 2.0
R4_THRESH = 0.30
AUDIT_RATE = 0.10
SEED = 20261007


def load_scope():
    scope = os.path.join(ROOT, "scope")
    items = json.load(open(os.path.join(scope, "manifest.json"), encoding="utf-8"))
    data = {it["line_no"]: it for it in items}
    faces = {}
    with open(os.path.join(scope, "features", "faces.jsonl"), encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            faces[r["line_no"]] = r
    embs = np.fromfile(os.path.join(scope, "features", "embeddings.f32"), dtype=np.float32).reshape(-1, 512)
    missing = [ln for ln in data if ln not in faces]
    if missing:
        sys.exit(f"Chưa trích đặc trưng xong: còn {len(missing)} ảnh")
    return data, faces, embs


def load_golden():
    from eval_identity import load
    data, faces, embs, labels = load()
    for ln, r in data.items():
        r["mentor_cluster"] = r.get("mentor_cluster", "")
    return data, faces, embs, labels


def decide(data, faces, embs):
    by_ent = defaultdict(list)
    for ln, r in data.items():
        by_ent[r["entity_id"]].append(ln)

    names = {ln: name_status(r["description"], r["canonical_name"]) for ln, r in data.items()}
    anchor_sim = anchor_similarity(by_ent, data, faces, embs)

    out = []
    for ent, lines in by_ent.items():
        clusters = cluster_entity(lines, faces, embs, names)
        main = clusters[0] if clusters else None
        main_emb = sorted(main[3]) if main else []
        for ln in lines:
            gf = good_faces(faces[ln])
            own = {f["emb"] for f in gf}
            ref = np.array([e for e in main_emb if e not in own], dtype=int)
            best = max((float(np.max(embs[ref] @ embs[f["emb"]])) for f in gf), default=-1.0) if len(ref) else -1.0
            largest = max((f["area_pct"] for f in gf), default=0.0)
            areas = sorted((f["area_pct"] for f in gf), reverse=True)
            dominance = areas[0] / areas[1] if len(areas) > 1 and areas[1] > 0 else float("inf")
            main_px = max(gf, key=lambda f: f["area_pct"])["size_px"] if gf else 0
            a_sim = anchor_sim.get(ln)
            name = names[ln]

            reasons, rules = [], []
            if name == "variant":
                rules.append("R1"); reasons.append("name_mismatch")
            if name == "no_name" and gf and a_sim is not None and a_sim < A2_THRESH:
                rules.append("A2"); reasons.append("wrong_person")
            if name == "no_name" and gf and len(ref) and best < R4_THRESH:
                rules.append("R4")
                if "wrong_person" not in reasons:
                    reasons.append("wrong_person")

            warns = []
            if faces[ln].get("error"):
                warns.append("no_image")
            elif not gf:
                warns.append("no_good_face")
            if name == "no_name":
                warns.append("title_no_name")
            if data[ln].get("mentor_cluster") == "ambiguous":
                warns.append("mentor_ambiguous")
            if len(gf) > 1:
                warns.append("multi_face")
            if gf and largest < 2.0:
                warns.append("small_face")
            if a_sim is None:
                warns.append("entity_no_anchor")

            out.append(dict(
                line_no=ln, entity_id=data[ln]["entity_id"], slug=data[ln]["slug"],
                canonical_name=data[ln]["canonical_name"], sha256=data[ln]["sha256"],
                image_url=data[ln]["image_url"],
                auto_flag="rejected" if rules else ("suggest_approved" if (
                    name == "exact" and best >= P4_SIM and a_sim is not None and a_sim >= P4_SIM
                    and dominance >= P4_DOMINANCE and main_px >= P4_MIN_PX
                    and data[ln].get("mentor_cluster") != "ambiguous") else "to_review"),
                auto_reasons=";".join(reasons), rules=";".join(rules), warnings=";".join(warns),
                name_status=name, n_faces=len(gf),
                best_sim=round(best, 3), anchor_sim="" if a_sim is None else round(a_sim, 3),
                audit=0,
            ))
    rej = sorted((r for r in out if r["auto_flag"] == "rejected"), key=lambda r: r["line_no"])
    rng = random.Random(SEED)
    for r in rng.sample(rej, max(1, round(AUDIT_RATE * len(rej)))) if rej else []:
        r["audit"] = 1
    return sorted(out, key=lambda r: r["line_no"])


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "scope"
    if target == "golden":
        data, faces, embs, labels = load_golden()
        rows = decide(data, faces, embs)
        rej = [r for r in rows if r["auto_flag"] == "rejected"]
        ok = sum(1 for r in rej if labels[r["line_no"]]["flag"] == "rejected")
        total = sum(1 for r in rows if labels[r["line_no"]]["flag"] == "rejected")
        print(f"Golden: {len(rows)} ảnh, tự loại {len(rej)}, đúng {ok} ({100 * ok / max(len(rej), 1):.1f}%), "
              f"bắt được {100 * ok / total:.1f}% số rejected")
        sug = [r for r in rows if r["auto_flag"] == "suggest_approved"]
        ok = sum(1 for r in sug if labels[r["line_no"]]["flag"] == "approved")
        total = sum(1 for r in rows if labels[r["line_no"]]["flag"] == "approved")
        print(f"Gợi ý approved {len(sug)}, đúng {ok} ({100 * ok / max(len(sug), 1):.1f}%), "
              f"phủ {100 * ok / total:.1f}% số approved")
        return
    data, faces, embs = load_scope()
    rows = decide(data, faces, embs)
    path = os.path.join(ROOT, "scope", "auto_labels.csv")
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    rej = sum(1 for r in rows if r["auto_flag"] == "rejected")
    by_rule = defaultdict(int)
    for r in rows:
        for x in filter(None, r["rules"].split(";")):
            by_rule[x] += 1
    print(f"{len(rows)} ảnh: tự loại {rej} ({100 * rej / len(rows):.1f}%), người duyệt {len(rows) - rej}, "
          f"mẫu kiểm tra {sum(r['audit'] for r in rows)}. Theo rule: {dict(by_rule)}")
    print(f"→ {path}")


if __name__ == "__main__":
    main()
