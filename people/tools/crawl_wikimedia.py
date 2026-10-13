"""Layer 1: crawl thêm ảnh cho entity thiếu ảnh từ Wikidata + Wikimedia Commons (miễn phí, chỉ dùng stdlib).

Chạy: python people/tools/crawl_wikimedia.py [--slugs a,b,c | --limit N] [--out people/output-batch4/crawl-extra]
Đầu vào: people/output-batch4/low-image-entities.csv (cột need_more_to_reach_10 = số ảnh tối đa cần thêm, 1–10).
Đầu ra (trong --out): extra-results.csv (cùng schema file gốc, flag để trống chờ duyệt, thêm cột wikidata_*),
candidates.json (các ứng viên Wikidata đã xét, để kiểm tra đúng người), images/<slug>/<sha16>.<ext>.
Ảnh trùng sha256 với approved-results (4).csv hoặc trùng nhau trong lượt chạy sẽ bị bỏ. Chạy lại được: bỏ qua entity đã có kết quả.
"""
import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
B4 = os.environ.get("IMG_BATCH_DIR") or os.path.join(ROOT, "people", "output-batch4")  # thư mục kết xuất của đợt đang làm
SRC = os.environ.get("IMG_SRC_CSV") or os.path.join(B4, "approved-results (4).csv")
LOW = os.environ.get("IMG_LOW_CSV") or os.path.join(B4, "low-image-entities.csv")
UA = "IMG_Verify-research/0.1 (non-commercial dataset verification; https://github.com/dkvippro2k5/IMG_Verify)"
WD = "https://www.wikidata.org/w/api.php"
CM = "https://commons.wikimedia.org/w/api.php"
MIN_SIDE = 300
THUMB_W = 1280
SLEEP = 1.0
VN_HINT = ("vietnam", "việt nam", "vietnamese")


def get_json(base, **params):
    url = base + "?" + urllib.parse.urlencode(dict(params, format="json"))
    for attempt in range(4):
        try:
            time.sleep(SLEEP)
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30) as r:
                return json.load(r)
        except Exception as e:
            if attempt == 3:
                raise
            time.sleep(5 * (attempt + 1))


def fetch_bytes(url):
    for attempt in range(3):
        try:
            time.sleep(SLEEP)
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60) as r:
                return r.read(), None
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            time.sleep(5 * (attempt + 1))
    return None, err


def clean_name(name):
    return re.sub(r"\s*\(.*?\)|\s+[-—–].*$", "", name).strip()


def find_person(name):
    """Trả về (best, candidates). best = ứng viên Wikidata là người, có ảnh, khớp tên nhất."""
    q = clean_name(name)
    ids, seen = [], set()
    for lang in ("vi", "en"):
        res = get_json(WD, action="wbsearchentities", search=q, language=lang, uselang=lang, type="item", limit=8)
        for s in res.get("search", []):
            if s["id"] not in seen:
                seen.add(s["id"])
                ids.append(s["id"])
    if not ids:
        return None, []
    ents = get_json(WD, action="wbgetentities", ids="|".join(ids[:20]), props="claims|labels|descriptions|aliases",
                    languages="vi|en").get("entities", {})
    cands = []
    for qid in ids:
        e = ents.get(qid) or {}
        claims = e.get("claims", {})
        is_human = any(c["mainsnak"].get("datavalue", {}).get("value", {}).get("id") == "Q5" for c in claims.get("P31", []))
        p18 = [c["mainsnak"]["datavalue"]["value"] for c in claims.get("P18", []) if "datavalue" in c["mainsnak"]]
        p373 = [c["mainsnak"]["datavalue"]["value"] for c in claims.get("P373", []) if "datavalue" in c["mainsnak"]]
        labels = {k: v["value"] for k, v in e.get("labels", {}).items()}
        aliases = [a["value"] for v in e.get("aliases", {}).values() for a in v]
        desc = " | ".join(v["value"] for v in e.get("descriptions", {}).values())
        score = 0
        if q in labels.values():
            score += 3
        elif q in aliases:
            score += 1
        if any(h in desc.lower() for h in VN_HINT):
            score += 2
        cands.append(dict(id=qid, label=labels.get("vi") or labels.get("en", ""), desc=desc, human=is_human,
                          p18=p18, p373=p373, score=score))
    ok = [c for c in cands if c["human"] and (c["p18"] or c["p373"])]
    ok.sort(key=lambda c: -c["score"])
    return (ok[0] if ok and ok[0]["score"] >= 3 else None), cands


def image_infos(titles):
    """titles: danh sách 'File:...'. Trả về dict title -> info."""
    out = {}
    for i in range(0, len(titles), 40):
        res = get_json(CM, action="query", titles="|".join(titles[i:i + 40]), prop="imageinfo",
                       iiprop="url|size|mime|extmetadata", iiurlwidth=THUMB_W)
        for p in res.get("query", {}).get("pages", {}).values():
            ii = (p.get("imageinfo") or [None])[0]
            if ii:
                out[p["title"]] = ii
    return out


def commons_files(cand):
    titles = ["File:" + f for f in cand["p18"]]
    for cat in cand["p373"][:1]:
        res = get_json(CM, action="query", list="categorymembers", cmtitle="Category:" + cat, cmtype="file", cmlimit=60)
        titles += [m["title"] for m in res.get("query", {}).get("categorymembers", [])]
    return list(dict.fromkeys(titles))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slugs")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--out", default=os.path.join(B4, "crawl-extra"))
    a = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    os.makedirs(os.path.join(a.out, "images"), exist_ok=True)

    src = list(csv.DictReader(open(SRC, encoding="utf-8-sig", newline="")))
    cols = list(src[0].keys())
    known = {r["sha256"] for r in src}
    first_row = {}
    for r in src:
        first_row.setdefault(r["entity_id"], r)
    low = list(csv.DictReader(open(LOW, encoding="utf-8-sig", newline="")))
    if a.slugs:
        want = a.slugs.split(",")
        low = [r for r in low if r["slug"] in want]
    else:
        low = low[:a.limit]

    res_path = os.path.join(a.out, "extra-results.csv")
    cand_path = os.path.join(a.out, "candidates.json")
    extra_cols = ["source_batch", "wikidata_id", "wikidata_label", "wikidata_desc", "license"]
    done = set()
    if os.path.exists(res_path):
        for r in csv.DictReader(open(res_path, encoding="utf-8-sig", newline="")):
            done.add(r["entity_id"]); known.add(r["sha256"])
    log = json.load(open(cand_path, encoding="utf-8")) if os.path.exists(cand_path) else {}
    new_file = not os.path.exists(res_path)
    fout = open(res_path, "a", encoding="utf-8-sig" if new_file else "utf-8", newline="")
    w = csv.DictWriter(fout, fieldnames=cols + extra_cols)
    if new_file:
        w.writeheader()

    for ent in low:
        slug, name, need = ent["slug"], ent["canonical_name"], int(ent["need_more_to_reach_10"])
        if ent["entity_id"] in done:
            print(f"- {name}: đã có kết quả, bỏ qua"); continue
        best, cands = find_person(name)
        log[slug] = dict(name=name, need=need, chosen=best["id"] if best else None, candidates=cands)
        if not best:
            print(f"- {name}: KHÔNG tìm được ứng viên đủ chắc ({len(cands)} ứng viên)"); continue
        infos = image_infos(commons_files(best))
        base = first_row.get(ent["entity_id"], {})
        got = 0
        for title, ii in infos.items():
            if got >= need:
                break
            if ii.get("mime") not in ("image/jpeg", "image/png") or min(ii["width"], ii["height"]) < MIN_SIDE:
                continue
            url = ii.get("thumburl") if ii["width"] > THUMB_W else ii["url"]
            data, err = fetch_bytes(url)
            if err:
                print(f"    lỗi tải {title}: {err}"); continue
            sha = hashlib.sha256(data).hexdigest()
            if sha in known:
                continue
            known.add(sha)
            ext = ".png" if ii["mime"] == "image/png" else ".jpg"
            rel = f"images/{slug}/{sha[:16]}{ext}"
            os.makedirs(os.path.join(a.out, "images", slug), exist_ok=True)
            open(os.path.join(a.out, rel), "wb").write(data)
            meta = ii.get("extmetadata", {})
            row = {c: "" for c in cols}
            row.update(entity_id=ent["entity_id"], slug=slug, canonical_name=name, category=ent["category"],
                       kind_hint=base.get("kind_hint", ""), query=clean_name(name), local_path=rel, sha256=sha,
                       image_url=url, source_url=ii.get("descriptionurl", ""), source_domain="commons.wikimedia.org",
                       description=title, width=ii["thumbwidth"] if url != ii["url"] else ii["width"],
                       height=ii["thumbheight"] if url != ii["url"] else ii["height"], bytes=len(data),
                       crawled_at=datetime.now(timezone.utc).isoformat(), from_db=0,
                       source_batch="extra", wikidata_id=best["id"], wikidata_label=best["label"],
                       wikidata_desc=best["desc"], license=meta.get("LicenseShortName", {}).get("value", ""))
            w.writerow(row); fout.flush()
            got += 1
        print(f"- {name} -> {best['id']} ({best['label']}; {best['desc'][:60]}): {got}/{need} ảnh")
        json.dump(log, open(cand_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(log, open(cand_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    fout.close()


if __name__ == "__main__":
    main()
