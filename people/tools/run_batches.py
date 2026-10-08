"""Chạy phạm vi làm việc theo từng batch (~400 ảnh, trọn entity) để người duyệt làm song song.

Mỗi batch: tải ảnh → trích đặc trưng → áp rule → cập nhật scope/review.html + scope/data.js.
Batch xong thì mở/tải lại (F5) scope/review.html là thấy; nhãn đã duyệt vẫn giữ.
Kết quả rule chỉ phụ thuộc từng entity nên chạy theo batch cho kết quả giống chạy một lần.
Chạy lại được khi bị dừng: batch đã xong được bỏ qua.

Chạy: .venv/Scripts/python -u tools/run_batches.py [--retry-missing]
  --retry-missing: thử tải lại ảnh lỗi của các batch đã xong (mặc định bỏ qua, chỉ tính lại rule).
"""
import csv
import json
import os
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from apply_rules import AUDIT_RATE, SEED, decide  # noqa: E402
from build_golden import FIELDS, download_to, ext_of  # noqa: E402
import build_review  # noqa: E402
import extract_faces as ef  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(ROOT, "data", "approved-results (1).csv")
SCOPE = os.path.join(ROOT, "scope")
IMG_DIR = os.path.join(SCOPE, "images")
BATCH_DIR = os.path.join(SCOPE, "batches")
START_LINE, END_LINE = 13325, 19988
BATCH_TARGET = 400
NET_FAIL_RATE = 0.30  # quá tỉ lệ tải lỗi này thì coi là mạng có sự cố
MAX_NET_WAITS = 6
# False: không tự cập nhật scope/review.html sau mỗi batch (tránh trang đang mở bị tải lại giữa chừng).
# Người duyệt tự cập nhật bằng cap-nhat-tool.bat (chạy tools/build_review.py) rồi F5.
AUTO_PUBLISH = False


def build_manifest():
    with open(CSV_PATH, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    items = []
    for i, r in enumerate(rows):
        line_no = i + 2
        if START_LINE <= line_no <= END_LINE:
            it = {k: r[k] for k in FIELDS}
            it.update(line_no=line_no, mentor_cluster=r["cluster"], download_error="",
                      image_file=r["sha256"][:16] + ext_of(r["image_url"]))
            items.append(it)
    return items


def split_batches(items):
    batches, cur, cur_slug = [], [], None
    for it in items:
        if cur and it["slug"] != cur_slug and len(cur) >= BATCH_TARGET:
            batches.append(cur)
            cur = []
        cur.append(it)
        cur_slug = it["slug"]
    if cur:
        batches.append(cur)
    return batches


def load_features():
    faces = {}
    path = os.path.join(SCOPE, "features", "faces.jsonl")
    with open(path, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            faces[(r["entity_id"], r["sha256"])] = r
    embs = np.fromfile(os.path.join(SCOPE, "features", "embeddings.f32"), dtype=np.float32).reshape(-1, 512)
    return faces, embs


def main():
    os.makedirs(IMG_DIR, exist_ok=True)
    os.makedirs(BATCH_DIR, exist_ok=True)
    items = build_manifest()
    batches = split_batches(items)
    labels = {}
    for k, b in enumerate(batches, 1):
        label = f"Batch {k}/{len(batches)} · dòng {b[0]['line_no']}–{b[-1]['line_no']}"
        for it in b:
            labels[it["slug"]] = label
    json.dump(labels, open(os.path.join(SCOPE, "batch_labels.json"), "w", encoding="utf-8"), ensure_ascii=False)
    print(f"{len(items)} ảnh → {len(batches)} batch: " + ", ".join(str(len(b)) for b in batches), flush=True)

    det = rec = None
    for k, b in enumerate(batches, 1):
        done_flag = os.path.join(BATCH_DIR, f"batch_{k:02d}.csv")
        rules_only = False
        if os.path.exists(done_flag):
            prev = list(csv.DictReader(open(done_flag, encoding="utf-8-sig")))
            if "--retry-missing" not in sys.argv or not any("no_image" in r["warnings"].split(";") for r in prev):
                # Batch đã xong: chỉ tính lại rule từ đặc trưng đã lưu (nhanh), để áp rule mới nếu có.
                rules_only = True
                for it in b:
                    if not os.path.exists(os.path.join(IMG_DIR, it["image_file"])):
                        it["download_error"] = "missing"
            else:
                print(f"[Batch {k}] còn ảnh chưa tải được trước đó, làm lại batch này", flush=True)
        t0 = time.time()
        if rules_only:
            n_err = sum(1 for it in b if it["download_error"])
            t_dl = t_ex = 0.0

        # 1. Tải ảnh (dùng lại ảnh đã có). CDN ngắt kết nối khi mở quá nhiều luồng,
        #    nên dùng ít luồng và thử lại vài vòng có giãn cách.
        def fetch(batch_items):
            pending = list(batch_items)
            for rnd in range(4):
                with ThreadPoolExecutor(max_workers=6) as pool:
                    errs = list(pool.map(lambda it: download_to(it["image_url"], os.path.join(IMG_DIR, it["image_file"])), pending))
                for it, e in zip(pending, errs):
                    it["download_error"] = e or ""
                pending = [it for it in pending if it["download_error"]]
                if not pending:
                    break
                time.sleep(10 * (rnd + 1))
            return len(pending)

        missing = fetch(b) if not rules_only else 0
        # Mạng tới CDN có lúc bị chặn hẳn: lỗi nhiều thì đợi rồi thử lại trước khi xử lý batch.
        for wait in range(MAX_NET_WAITS):
            if missing <= NET_FAIL_RATE * len(b):
                break
            print(f"[Batch {k}] tải lỗi {missing}/{len(b)}, có thể mạng tới CDN đang bị chặn; đợi 5 phút "
                  f"(lần {wait + 1}/{MAX_NET_WAITS})", flush=True)
            time.sleep(300)
            missing = fetch([it for it in b if it["download_error"]])
        if not rules_only:
            n_err = sum(1 for it in b if it["download_error"])
            t_dl = time.time() - t0

            # 2. Trích đặc trưng.
            if det is None:
                det = ef.SCRFD(ef.find_model("det_10g.onnx"))
                rec = ef.ArcFace(ef.find_model("w600k_r50.onnx"))
            ef.run_scope(det, rec, b)
            t_ex = time.time() - t0 - t_dl

        # 3. Áp rule cho batch.
        faces_all, embs = load_features()
        data = {it["line_no"]: it for it in b}
        faces = {it["line_no"]: faces_all[(it["entity_id"], it["sha256"])] for it in b}
        rows = decide(data, faces, embs)
        rej = [r for r in rows if r["auto_flag"] == "rejected"]
        for r in rows:
            r["audit"] = 0
        rng = random.Random(SEED + k)
        for r in rng.sample(rej, max(1, round(AUDIT_RATE * len(rej)))) if rej else []:
            r["audit"] = 1
        with open(done_flag, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)

        # 4. Gộp kết quả các batch đã xong, cập nhật manifest và tool duyệt.
        merged = []
        for name in sorted(os.listdir(BATCH_DIR)):
            if name.endswith(".csv"):
                merged += list(csv.DictReader(open(os.path.join(BATCH_DIR, name), encoding="utf-8-sig")))
        with open(os.path.join(SCOPE, "auto_labels.csv"), "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(merged[0].keys()))
            w.writeheader()
            w.writerows(merged)
        with open(os.path.join(SCOPE, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False)
        if AUTO_PUBLISH:
            build_review.main()

        n_sug = sum(1 for r in rows if r["auto_flag"] == "suggest_approved")
        print(f"[Batch {k}/{len(batches)}] {len(b)} ảnh, tải lỗi {n_err}, tự loại {len(rej)}, gợi ý approved {n_sug}, "
              f"mẫu kiểm tra {sum(r['audit'] for r in rows)} · tải {t_dl:.0f}s, trích {t_ex:.0f}s "
              f"· {'tính lại rule' if rules_only else 'XONG'}", flush=True)


if __name__ == "__main__":
    main()
