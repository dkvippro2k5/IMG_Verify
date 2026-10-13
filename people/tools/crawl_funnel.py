"""Crawl thêm ảnh cho entity thiếu ảnh theo phễu: thu thập nhiều ảnh thô (Commons + DuckDuckGo, nhiều mẫu query) rồi lọc dần.

Phễu: URL thô -> tải được -> đủ kích thước -> đúng 1 mặt rõ -> đúng người (so ArcFace với ảnh đã approved) -> khử trùng -> top N.
Chạy: .venv/Scripts/python people/tools/crawl_funnel.py [--slugs a,b | --limit N] [--out people/output-batch4/crawl-extra-v2] [--force]
Đầu vào: people/output-batch4/low-image-entities.csv + DuongVanKien_merged-batch4-results.csv (ảnh approved làm ảnh tham chiếu danh tính).
Đầu ra: extra-results.csv (schema file gốc + cột phụ, flag để trống chờ duyệt), funnel.json (số ảnh qua từng tầng của từng entity), images/<slug>/.
Chạy lại được: entity đã có trong funnel.json thì bỏ qua (trừ khi --force).
"""
import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
from itertools import zip_longest
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from io import BytesIO

import numpy as np
from PIL import Image, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crawl_wikimedia as wm  # noqa: E402
from extract_faces import SCRFD, ArcFace, find_model, process  # noqa: E402
import cv2  # noqa: E402
from apply_rules import ROLE_WORDS  # noqa: E402

ROOT = wm.ROOT
B4 = wm.B4
MERGED = os.environ.get("IMG_LABELS_CSV") or os.path.join(B4, "DuongVanKien_merged-batch4-results.csv")  # cần cột entity_id, flag, image_url
UA = wm.UA
BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

ROLE = {"historic": "nhân vật lịch sử", "singer": "ca sĩ", "politicer": "chính trị gia", "athletes": "vận động viên",
        "scientist": "nhà khoa học", "writer": "nhà văn", "businessman": "doanh nhân", "celeb": "nghệ sĩ"}
MAX_DOWNLOADS = 90         # số URL thô tối đa tải cho mỗi entity (đổi bằng --max-dl)
DDG_N = 40                 # số kết quả mỗi query DuckDuckGo (đổi bằng --ddg-n)
SKIP_WIKI = False          # --skip-wiki: bỏ Wikidata/Commons (entity người nổi tiếng gần như không có ảnh ở đó, tiết kiệm ~20 giây/entity)
MIN_SIDE = 400
MAX_BYTES = 8_000_000
FACE_SCORE = 0.6
MIN_FACE_PX = 50
MIN_FACE_AREA_PCT = 2.0
DOMINANCE = 2.0            # mặt chính phải lớn gấp đôi mặt thứ hai
ID_HARD = 0.25             # dưới ngưỡng này coi là người khác
ID_GOOD = 0.40
MIN_BLUR = 15.0
MAX_REFS = 6
SAME_FACE = 0.85           # hai ảnh được chọn có mặt giống đến mức này thì coi là cùng một bức ảnh/tranh, chỉ giữ một
EXTRA_QUERIES = False        # --more-queries: thêm mẫu query để lấy nhiều ảnh thô khác loại
DROP_LOW = False             # --drop-low: không ghi ảnh trust=low
PSEUDO_SIM = 0.5           # hai mặt giống nhau từ ngưỡng này thì coi là cùng người khi dựng ảnh tham chiếu giả
PSEUDO_MIN = 3             # cụm tối thiểu để tin là ảnh tham chiếu giả


def norm(t):
    t = unicodedata.normalize("NFD", (t or "").lower().replace("đ", "d"))
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def name_in(name, *texts):
    """Tên đầy đủ (bỏ dấu, bỏ phần trong ngoặc) có xuất hiện nguyên cụm trong tiêu đề/URL không."""
    n = norm(wm.clean_name(name))
    hay = " " + " ".join(norm(urllib.parse.unquote(t)) for t in texts) + " "
    return bool(n) and f" {n} " in hay


NON_PHOTO = ["tượng", "đài tưởng niệm", "bia mộ", "mộ phần", "lăng mộ", "đường phố", "tên đường", "tranh vẽ", "vẽ", "minh họa",
             "hoạt hình", "mô phỏng", "cartoon", "illustration", "statue", "monument", "tombstone", "logo", "sticker", "fanart"]


def non_photo(*texts):
    hay = " " + " ".join(re.sub(r"[^\w\s]", " ", urllib.parse.unquote(t or "").lower()) for t in texts) + " "
    return any(f" {w} " in hay for w in NON_PHOTO)


def role_state(category, *texts):
    """own: tiêu đề có chức danh của category; other: chỉ có chức danh của category khác (vd MC với politicer); none: không có."""
    hay = " " + " ".join(norm(urllib.parse.unquote(t)) for t in texts) + " "
    if any(f" {w} " in hay for w in ROLE_WORDS.get(category, [])):
        return "own"
    if any(f" {w} " in hay for c, ws in ROLE_WORDS.items() if c != category for w in ws):
        return "other"
    return "none"


def bootstrap_refs(items):
    """Chỉ số các ảnh thuộc cụm mặt lớn (>= PSEUDO_MIN) trong số ảnh có tên và không lệch chức danh,
    (đã loại ảnh có chức danh thuộc category khác)."""
    named = [i for i, it in enumerate(items) if it["nm"] and it["role"] != "other"]
    if len(named) < PSEUDO_MIN:
        return []
    E = np.stack([items[i]["emb"] for i in named])
    S = E @ E.T
    for seed in np.argsort(-(S >= PSEUDO_SIM).sum(axis=1)):
        cluster = [named[j] for j in range(len(named)) if S[seed, j] >= PSEUDO_SIM]
        if len(cluster) < PSEUDO_MIN:
            return []
        return cluster
    return []


def trust_of(ref_type, sim, nm, role):
    """Mức tin cậy để sắp xếp khi duyệt tay: high = giống ảnh tham chiếu thật; mid = cụm mặt có tên, hoặc tên + chức danh đúng nhóm; low = còn lại."""
    if ref_type == "real" and sim is not None and sim >= ID_GOOD:
        return "high"
    if (ref_type == "pseudo" and nm and sim is not None and sim >= ID_GOOD) or (nm and role == "own"):
        return "mid"
    return "low"


def queries_for(name, category):
    base = wm.clean_name(name)
    paren = re.findall(r"\((.*?)\)", name)
    qs = [base, f"{base} chân dung", f"{base} portrait", f"{base} {ROLE.get(category, '')}".strip()]
    if EXTRA_QUERIES:
        qs += [f"{base} sự kiện", f"{base} phỏng vấn", f"{base} 2025", f"{base} Vietnam", f"{base} ảnh đời thường"]
    for p in paren:
        year = re.search(r"\d{4}", p)
        qs.append(f"{base} {year.group(0)}" if year else f"{base} {p}")
    return list(dict.fromkeys(qs))


def ddg_images(query, n=None):
    n = n or DDG_N
    from ddgs import DDGS
    for attempt in range(3):
        try:
            time.sleep(2)
            return DDGS().images(query, region="vn-vi", safesearch="off", max_results=n) or []
        except Exception as e:
            print(f"    ddgs lỗi ({query}): {type(e).__name__}", flush=True)
            time.sleep(8 * (attempt + 1))
    return []


def commons_search(name, n=30):
    res = wm.get_json(wm.CM, action="query", list="search", srsearch=name, srnamespace=6, srlimit=n)
    titles = [s["title"] for s in res.get("query", {}).get("search", [])]
    return wm.image_infos(titles)


def collect(ent):
    """Trả về (danh sách ứng viên thô, wikidata chosen, danh sách URL ảnh tham chiếu từ P18)."""
    name, cat = ent["canonical_name"], ent["category"]
    cands, refs = [], []
    best, infos = (None, {}) if SKIP_WIKI else (wm.find_person(name)[0], {})
    if best:
        infos.update(wm.image_infos(wm.commons_files(best)))
        refs = [i["url"] if i["width"] <= wm.THUMB_W else i["thumburl"]
                for t, i in wm.image_infos(["File:" + f for f in best["p18"]]).items()
                if i.get("mime") in ("image/jpeg", "image/png")]
    if not SKIP_WIKI:
        infos.update(commons_search(wm.clean_name(name)))
    for title, ii in infos.items():
        if ii.get("mime") not in ("image/jpeg", "image/png"):
            continue
        url = ii["thumburl"] if ii["width"] > wm.THUMB_W else ii["url"]
        cands.append(dict(url=url, source_url=ii.get("descriptionurl", ""), title=title, origin="commons", query="",
                          license=ii.get("extmetadata", {}).get("LicenseShortName", {}).get("value", "")))
    per_query = []
    for q in queries_for(name, cat):
        lst = [dict(url=r["image"], source_url=r.get("url", ""), title=r.get("title", ""), origin="ddg", query=q, license="")
               for r in ddg_images(q) if r.get("image")]
        per_query.append(lst)
    for group in zip_longest(*per_query):  # xen kẽ các query để phần bị cắt bởi --max-dl vẫn đa dạng
        cands += [c for c in group if c]
    seen, uniq = set(), []
    for c in cands:
        if c["url"] not in seen:
            seen.add(c["url"]); uniq.append(c)
    return uniq, best, refs


def download(url):
    for ua in (BROWSER_UA, UA):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept": "image/*,*/*;q=0.8"})
            with urllib.request.urlopen(req, timeout=25) as r:
                data = r.read(MAX_BYTES + 1)
            if 0 < len(data) <= MAX_BYTES:
                return data
        except Exception:
            continue
    return None


def decode(data):
    try:
        with Image.open(BytesIO(data)) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            return cv2.cvtColor(np.asarray(im), cv2.COLOR_RGB2BGR)
    except Exception:
        return None


def dhash(img):
    g = cv2.resize(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (9, 8))
    return (g[:, 1:] > g[:, :-1]).flatten()


def main_face(img, det, rec):
    """Phân tích ảnh. Trả về (mặt chính hoặc None, số mặt đạt ngưỡng, embedding mặt chính, lý do loại)."""
    faces, feats = process(img, det, rec, {"det": 0.0, "rec": 0.0})
    idx = [i for i, f in enumerate(faces) if f["score"] >= FACE_SCORE]
    if not idx:
        return None, 0, None, "no_face"
    idx.sort(key=lambda i: -faces[i]["area_pct"])
    m = faces[idx[0]]
    if len(idx) > 1 and faces[idx[1]]["area_pct"] * DOMINANCE > m["area_pct"]:
        return m, len(idx), feats[idx[0]], "multi_face"
    if m["size_px"] < MIN_FACE_PX or m["area_pct"] < MIN_FACE_AREA_PCT:
        return m, len(idx), feats[idx[0]], "face_small"
    if m["blur"] < MIN_BLUR:
        return m, len(idx), feats[idx[0]], "blurry"
    return m, len(idx), feats[idx[0]], ""


def reference_embeddings(ent_id, approved_urls, p18_urls, det, rec, user_urls=()):
    embs = []
    for url in user_urls:  # ảnh do người duyệt đưa: nhận mặt lớn nhất kể cả khi ảnh có nhiều mặt
        data = download(url)
        img = decode(data) if data else None
        if img is None:
            continue
        m, n, e, why = main_face(img, det, rec)
        if e is not None and why in ("", "face_small", "blurry", "multi_face"):
            embs.append(e)
    for url in (p18_urls + approved_urls)[:MAX_REFS * 2]:
        if len(embs) >= MAX_REFS:
            break
        data = download(url)
        img = decode(data) if data else None
        if img is None:
            continue
        m, n, e, why = main_face(img, det, rec)
        if e is not None and why in ("", "face_small", "blurry") and n == 1:
            embs.append(e)
    return np.array(embs, dtype=np.float32) if embs else np.zeros((0, 512), dtype=np.float32)


def main():
    global MAX_DOWNLOADS, DDG_N, EXTRA_QUERIES, SKIP_WIKI, DROP_LOW
    ap = argparse.ArgumentParser()
    ap.add_argument("--slugs")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--out", default=os.path.join(B4, "crawl-extra-v3"))
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--max-dl", type=int, default=MAX_DOWNLOADS, help="số URL thô tối đa tải mỗi entity")
    ap.add_argument("--ddg-n", type=int, default=DDG_N, help="số kết quả mỗi query DuckDuckGo")
    ap.add_argument("--more-queries", action="store_true", help="thêm mẫu query (sự kiện, phỏng vấn, năm, tiếng Anh...)")
    ap.add_argument("--skip-wiki", action="store_true", help="bỏ Wikidata/Commons")
    ap.add_argument("--drop-low", action="store_true", help="không ghi ảnh trust=low")
    ap.add_argument("--min-approved", type=int, default=0, help="chỉ lấy entity có ít nhất ngần này ảnh approved (>=1: entity có ảnh tham chiếu)")
    ap.add_argument("--skip-done-in", help="thư mục gốc chứa các funnel.json của lần chạy trước; entity đã có ở đó thì bỏ qua")
    ap.add_argument("--shard", help="k/n: chia danh sách thành n phần và chỉ chạy phần k (1..n), để chạy song song nhiều tiến trình")
    ap.add_argument("--refs-csv", help="CSV slug,ref_url: ảnh tham chiếu do người duyệt cung cấp (ưu tiên hơn ảnh tự tìm)")
    a = ap.parse_args()
    MAX_DOWNLOADS, DDG_N, EXTRA_QUERIES, SKIP_WIKI, DROP_LOW = a.max_dl, a.ddg_n, a.more_queries, a.skip_wiki, a.drop_low
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    os.makedirs(os.path.join(a.out, "images"), exist_ok=True)

    src = list(csv.DictReader(open(wm.SRC, encoding="utf-8-sig", newline="")))
    cols = list(src[0].keys())
    known = {r["sha256"] for r in src}
    first_row = {}
    for r in src:
        first_row.setdefault(r["entity_id"], r)
    approved = {}
    for r in csv.DictReader(open(MERGED, encoding="utf-8-sig", newline="")):
        if r["flag"] == "approved":
            approved.setdefault(r["entity_id"], []).append(r["image_url"])

    user_refs = {}
    if a.refs_csv:
        for r in csv.DictReader(open(a.refs_csv, encoding="utf-8-sig", newline="")):
            user_refs.setdefault(r["slug"], []).append(r["ref_url"])
    low = list(csv.DictReader(open(wm.LOW, encoding="utf-8-sig", newline="")))
    if a.slugs:
        want = a.slugs.split(",")
        low = [r for r in low if r["slug"] in want]
    elif a.min_approved or a.shard:
        low = [r for r in low if int(r["approved"]) >= a.min_approved]
    else:
        low = low[:a.limit]
    if a.skip_done_in:
        done_slugs = set()
        for root, _, files in os.walk(a.skip_done_in):
            if "funnel.json" in files:
                done_slugs |= set(json.load(open(os.path.join(root, "funnel.json"), encoding="utf-8")))
        low = [r for r in low if r["slug"] not in done_slugs]
    if a.shard:
        k, n = map(int, a.shard.split("/"))
        low = low[k - 1::n]

    res_path = os.path.join(a.out, "extra-results.csv")
    fun_path = os.path.join(a.out, "funnel.json")
    extra_cols = ["source_batch", "origin", "search_query", "wikidata_id", "id_sim", "ref_type", "name_match", "role_match", "trust", "license"]
    fun = json.load(open(fun_path, encoding="utf-8")) if os.path.exists(fun_path) else {}
    new_file = not os.path.exists(res_path)
    fout = open(res_path, "a", encoding="utf-8-sig" if new_file else "utf-8", newline="")
    w = csv.DictWriter(fout, fieldnames=cols + extra_cols)
    if new_file:
        w.writeheader()
    else:
        for r in csv.DictReader(open(res_path, encoding="utf-8-sig", newline="")):
            known.add(r["sha256"])

    det = SCRFD(find_model("det_10g.onnx"))
    rec = ArcFace(find_model("w600k_r50.onnx"))

    for ent in low:
        slug, name, need = ent["slug"], ent["canonical_name"], int(ent["need_more_to_reach_10"])
        if slug in fun and not a.force:
            print(f"- {name}: đã chạy, bỏ qua", flush=True); continue
        st = dict(name=name, need=need, raw_urls=0, downloaded=0, size_ok=0, one_face=0, identity_ok=0, kept=0,
                  refs=0, rejected={}, wikidata=None)
        print(f"- {name} (cần {need})", flush=True)
        cands, best, p18 = collect(ent)
        st["raw_urls"] = len(cands); st["wikidata"] = best["id"] if best else None
        cands = cands[:MAX_DOWNLOADS]
        with ThreadPoolExecutor(max_workers=8) as pool:
            blobs = list(pool.map(lambda c: download(c["url"]), cands))
        refs = reference_embeddings(ent["entity_id"], approved.get(ent["entity_id"], []), p18, det, rec, user_refs.get(slug, []))
        st["refs"] = len(refs)

        def rej(why):
            st["rejected"][why] = st["rejected"].get(why, 0) + 1

        items, hashes = [], []
        for c, data in zip(cands, blobs):
            img = decode(data) if data else None
            if img is None:
                rej("download_fail"); continue
            st["downloaded"] += 1
            h, wd = img.shape[:2]
            if min(h, wd) < MIN_SIDE:
                rej("too_small"); continue
            st["size_ok"] += 1
            sha = hashlib.sha256(data).hexdigest()
            dh = dhash(img)
            if sha in known or any((dh != x).sum() <= 4 for x in hashes):
                rej("duplicate"); continue
            m, n, emb, why = main_face(img, det, rec)
            if why:
                rej(why); continue
            st["one_face"] += 1
            hashes.append(dh)
            if non_photo(c["title"], c["source_url"], c["url"]):
                rej("non_photo"); continue
            nm = name_in(name, c["title"], c["source_url"], c["url"])
            role = role_state(ent["category"], c["title"], c["source_url"])
            items.append(dict(c=c, data=data, sha=sha, shp=img.shape, m=m, n=n, emb=emb, nm=nm, role=role, sim=None))
        # Tầng danh tính: ảnh tham chiếu thật; nếu không có thì dựng ảnh tham chiếu giả từ cụm mặt lớn nhất trong số ảnh có tên.
        ref_type = "real" if len(refs) else "none"
        pseudo = []
        if not len(refs):
            pseudo = bootstrap_refs(items)
            if pseudo:
                ref_type = "pseudo"
            st["pseudo_refs"] = len(pseudo)
        st["ref_type"] = ref_type
        passed = []
        for it in items:
            if ref_type == "real":
                it["sim"] = float((refs @ it["emb"]).max())
            elif ref_type == "pseudo":
                others = [j for j in pseudo if items[j] is not it]
                it["sim"] = float(max(items[j]["emb"] @ it["emb"] for j in others)) if others else None
            if ref_type != "none" and it["sim"] is not None and it["sim"] < ID_HARD:
                rej("other_person"); continue
            if ref_type != "real" and it["role"] == "other":
                rej("role_mismatch"); continue
            if ref_type == "none" and not it["nm"]:
                rej("no_context"); continue  # không có tham chiếu nào: ít nhất phải có tên trong ngữ cảnh
            if ref_type == "pseudo" and not it["nm"] and (it["sim"] is None or it["sim"] < ID_GOOD):
                rej("no_context"); continue
            st["identity_ok"] += 1
            sim, c, m = it["sim"], it["c"], it["m"]
            score = (sim if sim is not None else 0.0) + 0.15 * min(m["area_pct"], 30) / 30 + (0.05 if c["origin"] == "commons" else 0) + (0.1 if it["nm"] else 0)
            passed.append((score, sim, c, it["data"], it["sha"], it["shp"], m, it["n"], it["nm"], ref_type, it["emb"], it["role"]))
        if DROP_LOW:
            kept_p = []
            for t in passed:
                if trust_of(t[9], t[1], t[8], t[11] if len(t) > 11 else "none") == "low":
                    rej("low_trust")
                else:
                    kept_p.append(t)
            passed = kept_p
        passed.sort(key=lambda t: -t[0])
        chosen, chosen_embs = [], []
        for t in passed:
            if len(chosen) >= need:
                break
            e = t[10]
            if any(float(e @ x) >= SAME_FACE for x in chosen_embs):
                rej("same_face"); continue
            chosen.append(t); chosen_embs.append(e)
        for score, sim, c, data, sha, shp, m, n, nm, rtype, _e, role in chosen:
            ext = ".png" if data[:4] == b"\x89PNG" else ".jpg"
            rel = f"images/{slug}/{sha[:16]}{ext}"
            os.makedirs(os.path.join(a.out, "images", slug), exist_ok=True)
            open(os.path.join(a.out, rel), "wb").write(data)
            known.add(sha)
            row = {k: "" for k in cols}
            row.update(entity_id=ent["entity_id"], slug=slug, canonical_name=name, category=ent["category"],
                       kind_hint=first_row.get(ent["entity_id"], {}).get("kind_hint", ""), query=c["query"] or wm.clean_name(name),
                       local_path=rel, sha256=sha, image_url=c["url"], source_url=c["source_url"],
                       source_domain=urllib.parse.urlparse(c["source_url"] or c["url"]).netloc, description=c["title"],
                       width=shp[1], height=shp[0], bytes=len(data), crawled_at=datetime.now(timezone.utc).isoformat(),
                       has_face=1, face_count=n, face_area_pct=m["area_pct"], from_db=0, source_batch="extra",
                       origin=c["origin"], search_query=c["query"], wikidata_id=st["wikidata"] or "",
                       id_sim="" if sim is None else round(sim, 3), license=c["license"],
                       ref_type=rtype, name_match=int(nm), role_match=role,
                       trust=trust_of(rtype, sim, nm, role))
            w.writerow(row); fout.flush()
            st["kept"] += 1
        print(f"    thô {st['raw_urls']} -> tải {st['downloaded']} -> cỡ {st['size_ok']} -> 1 mặt {st['one_face']} "
              f"-> đúng người {st['identity_ok']} -> giữ {st['kept']}/{need} (ref {st['refs']}) loại: {st['rejected']}", flush=True)
        fun[slug] = st
        json.dump(fun, open(fun_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    fout.close()


if __name__ == "__main__":
    main()
