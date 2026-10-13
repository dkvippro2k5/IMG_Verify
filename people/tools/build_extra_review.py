"""Dựng tool duyệt cho ảnh crawl thêm: people/output-batch4/review-extra/review.html + data.js.

Trong mỗi entity: ảnh crawl mới lên đầu (có huy hiệu trust/id_sim/nguồn), ảnh batch4 cũ đứng sau kèm nhãn đã duyệt
(hiện như "golden") để so sánh. Chỉ đưa vào entity đã có ít nhất 1 ảnh crawl. Chạy lại được bất cứ lúc nào khi crawl đang chạy;
line_no của ảnh crawl suy ra từ sha256 nên nhãn đã duyệt trong trình duyệt (localStorage) không bị lệch khi dựng lại.

Chạy: python people/tools/build_extra_review.py
"""
import csv
import glob
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
B4 = os.environ.get("IMG_BATCH_DIR") or os.path.join(ROOT, "people", "output-batch4")  # đợt khác: đặt IMG_BATCH_DIR, IMG_CRAWL_DIRS, IMG_MERGED_CSV, IMG_LABELS_CSV, IMG_REVIEW_KEY
OUT = os.path.join(B4, "review-extra")
TEMPLATE = os.path.join(ROOT, "people", "tools", "review_template.html")  # giao diện duyệt đang dùng (có box best_sim, modal ảnh chưa xong, phím ↑/↓)
CRAWL_DIRS = [d for d in os.environ.get("IMG_CRAWL_DIRS", "crawl-extra-v7,crawl-extra-ref,crawl-extra-ref2,crawl-extra-rej,crawl-extra-noref").split(",") if d]  # IMG_CRAWL_DIRS="" = không đọc thư mục crawl nào
ENTITY_LIST = os.environ.get("IMG_ENTITY_LIST")
FILL_REASON = os.environ.get("IMG_FILL_REASON", "")  # lý do điền cho ảnh cũ bị reject mà không ghi lý do (batch6: "wrong_person"); chỉ áp dụng trong trang duyệt
MERGED = os.environ.get("IMG_MERGED_CSV") or os.path.join(B4, "DuongVanKien_merged-batch4-results.csv")
LABELS = os.environ.get("IMG_LABELS_CSV") or os.path.join(B4, "scope-labels-kien-DuongVanKien-2026-10-10.csv")
TRUST_ORDER = {"high": 0, "mid": 1, "low": 2}


def read(path):
    return list(csv.DictReader(open(path, encoding="utf-8-sig", newline="")))


def read_extra(path):
    """Đọc extra-results.csv chịu được file có dòng dài hơn tiêu đề đúng 2 cột (batch6: hai cột line_no, reject_reason chèn sau flag
    khi file nhãn đổi cột giữa các lần chạy); các dòng đó được cắt bỏ 2 cột thừa trước khi ghép với tiêu đề."""
    rows = list(csv.reader(open(path, encoding="utf-8-sig", newline="")))
    head, out = rows[0], []
    cut = head.index("flag") + 1 if "flag" in head else len(head)
    for r in rows[1:]:
        if len(r) == len(head) + 2:
            r = r[:cut] + r[cut + 2:]
        if len(r) == len(head):
            out.append(dict(zip(head, r)))
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    crawled, seen = [], set()
    for d in CRAWL_DIRS:
        for path in sorted(glob.glob(os.path.join(B4, d, "**", "extra-results.csv"), recursive=True)):
            base = os.path.relpath(os.path.dirname(path), OUT).replace("\\", "/")
            for r in read_extra(path):
                k = (r["entity_id"], r["sha256"])
                if k in seen:
                    continue
                seen.add(k)
                r["_img"] = f"{base}/{r['local_path']}"
                crawled.append(r)
    by_ent = {}
    for r in crawled:
        by_ent.setdefault(r["entity_id"], []).append(r)
    # IMG_ENTITY_LIST: CSV cột entity_id; đưa các entity này vào trang kể cả khi chưa có ảnh crawl (để thêm ảnh thủ công bằng kéo thả).
    listed = [r["entity_id"] for r in read(ENTITY_LIST)] if ENTITY_LIST else []
    for e in listed:
        by_ent.setdefault(e, [])
    pos = {e: i for i, e in enumerate(listed)}

    line_of = {(r["entity_id"], r["sha256"]): int(r["line_no"]) for r in read(LABELS)}
    existing = {}
    for r in read(MERGED):
        if r["entity_id"] in by_ent:
            existing.setdefault(r["entity_id"], []).append(r)

    used, out, order = set(), [], []
    for eid in sorted(by_ent, key=lambda e: (-len(by_ent[e]), pos.get(e, 10**9))):
        rows = sorted(by_ent[eid], key=lambda r: (TRUST_ORDER.get(r.get("trust", "low"), 2), -float(r.get("id_sim") or 0)))
        if not rows and not existing.get(eid):
            continue
        first = rows[0] if rows else existing[eid][0]
        n_ap = sum(1 for r in existing.get(eid, []) if r["flag"] == "approved")
        batch = f"{first['category']} · {len(rows)} ảnh crawl mới · {n_ap} ảnh approved"
        order.append(first["slug"])
        for r in rows:
            ln = 2_000_000_000 + int(r["sha256"][:8], 16)
            while ln in used:
                ln += 1
            used.add(ln)
            out.append(dict(
                line_no=ln, entity_id=eid, slug=r["slug"], canonical_name=r["canonical_name"], category=r["category"],
                query=r["query"], sha256=r["sha256"], image_url=r["image_url"], local_image=r["_img"],
                description=r["description"], width=r["width"], height=r["height"], face_count=r["face_count"],
                face_area_pct=r["face_area_pct"], source_url=r["source_url"], source_domain=r["source_domain"],
                auto_flag="", audit="0", rules="", warnings="", batch=batch, crawled=1,
                trust=r.get("trust", ""), id_sim=r.get("id_sim", ""), best_sim=r.get("id_sim", ""), n_faces=1, origin=r.get("origin", ""),
                ref_type=r.get("ref_type", ""), name_match=r.get("name_match", ""), license=r.get("license", "")))
        for r in existing.get(eid, []):
            ln = line_of.get((eid, r["sha256"]))
            if ln is None:
                continue
            ok = r["flag"] == "approved"
            out.append(dict(
                line_no=ln, entity_id=eid, slug=r["slug"], canonical_name=r["canonical_name"], category=r["category"],
                query=r["query"], sha256=r["sha256"], image_url=r["image_url"], local_image="",
                description=r["description"], width=r["width"], height=r["height"], face_count=r["face_count"],
                face_area_pct=r["face_area_pct"], source_url=r["source_url"], source_domain=r["source_domain"],
                auto_flag="", audit="0", rules="", warnings="", batch=batch, crawled=0,
                gold_flag=r["flag"], gold_reasons=r["reject_reason"] or (FILL_REASON if r["flag"] == "rejected" else ""), gold_identity="match" if ok else "other"))

    with open(os.path.join(OUT, "data.js"), "w", encoding="utf-8") as f:
        f.write("window.GOLDEN_DATA = ")
        json.dump(out, f, ensure_ascii=False)
        f.write(";\n")

    html = open(TEMPLATE, encoding="utf-8").read()
    cfg = '<script>window.REVIEW_CONFIG = { storeKey: "%s", filePrefix: "%s"' % (os.environ.get("IMG_REVIEW_KEY") or "extra-review-kien-v1", os.environ.get("IMG_REVIEW_PREFIX") or "extra-labels-kien") + ' };</script>\n'
    html = html.replace("<title>Scope Review</title>", "<title>Duyệt ảnh crawl thêm</title>")
    html = html.replace("<h1>Duyệt phạm vi</h1>", "<h1>Duyệt ảnh crawl thêm</h1>")
    old_cfg = re.search(r"<script>window\.REVIEW_CONFIG = .*?</script>\n", html)
    assert old_cfg
    html = html.replace(old_cfg.group(0), cfg)
    old_rank = "function rank(r) { return isAuto(r) ? 3 : r.gold_flag ? 2 : isSuggest(r) ? 1 : 0; }"
    assert old_rank in html
    html = html.replace(old_rank, "function rank(r) { return r.crawled ? -1 : isAuto(r) ? 3 : r.gold_flag ? 2 : isSuggest(r) ? 1 : 0; }")
    anchor = '    if (r.gold_flag) badges.push('
    assert anchor in html
    crawl_badges = (
        '    if (r.crawled) badges.push(`<span class="badge" style="background:#e6f0ff;color:#1a4fa0">CRAWL MỚI · ${esc(r.origin)}</span>`);\n'
        '    if (r.crawled) badges.push(`<span class="badge ${r.trust === "low" ? "bad" : "mut"}">tin cậy ${esc(r.trust)}${r.ref_type ? " · tham chiếu " + esc(r.ref_type) : ""}</span>`);\n'
        '    if (r.crawled && r.license) badges.push(`<span class="badge mut">${esc(r.license)}</span>`);\n')
    html = html.replace(anchor, crawl_badges + MANUAL_BADGE + anchor, 1)
    html = html.replace('<span>dòng ${r.line_no}</span>', '<span>${r.crawled ? "crawl mới" : "%s"}</span>' % os.environ.get("IMG_OLD_LABEL", "batch4 cũ"), 1)
    html = inject_manual_drop(html)
    open(os.path.join(OUT, "review.html"), "w", encoding="utf-8").write(html)

    n_new = sum(1 for r in out if r["crawled"])
    print(f"{len(order)} entity, {n_new} ảnh crawl mới, {len(out) - n_new} ảnh batch4 cũ để so sánh -> {OUT}")


MANUAL_BADGE = (
    '    if (r.origin === "manual") badges.push(`<button class="btn bad" data-act="delmanual" data-line="${r.line_no}">&#10005; xoá ảnh thêm</button>`);\n'
    # Hiện đủ hai URL của ảnh thêm thủ công; ô nhập cho phép dán/sửa link bài viết sau khi thêm.
    '    if (r.origin === "manual") badges.push(`<div style="width:100%;font-size:12px;word-break:break-all">URL ảnh: <a href="${esc(r.image_url)}" target="_blank" rel="noopener noreferrer">${esc(r.image_url)}</a></div>`);\n'
    '    if (r.origin === "manual") badges.push(`<div style="width:100%;font-size:12px">URL bài viết: <input class="srcin" data-line="${r.line_no}" value="${esc(r.source_url)}" placeholder="chưa có — dán link bài viết vào đây" style="width:100%;padding:4px 6px;margin-top:2px;border:1px solid var(--line);border-radius:6px;background:#fff;color:#000"></div>`);\n'
)

MANUAL_CSS = """
#dropZone { margin: 0 0 14px; padding: 10px 14px; border: 2px dashed var(--line); border-radius: 10px; background: var(--bg); }
#dropZone .dz-title { font-weight: 600; font-size: 13.5px; }
#dropZone .dz-row { display: flex; gap: 8px; margin-top: 8px; flex-wrap: wrap; }
#dropZone input { flex: 1 1 260px; padding: 6px 8px; border: 1px solid var(--line); border-radius: 6px; background: #fff; color: #000; }
body.dz-active #dropZone { border-color: var(--ok); background: var(--ok-bg); }
"""

MANUAL_ZONE = """<div id="dropZone">
      <div class="dz-title">Kéo thả ảnh từ Google Images vào bất kỳ chỗ nào trên trang này &rarr; thêm vào: <b id="dzTarget"></b><span id="dzCount"></span></div>
      <div class="dz-row">
        <input id="dzImg" placeholder="hoặc dán link ảnh (https://...) rồi Enter">
        <input id="dzPage" placeholder="link trang nguồn (tuỳ chọn)">
        <button class="btn" id="dzAdd">Thêm</button>
      </div>
    </div>
    """


def inject_manual_drop(html):
    """Thêm luồng kéo thả / dán link ảnh thủ công vào review.html (JS ở tools/review_manual_drop.js)."""
    js = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "review_manual_drop.js"), encoding="utf-8").read()

    def sub(old, new):
        nonlocal html
        assert old in html, old[:60]
        html = html.replace(old, new, 1)

    sub("</style>", MANUAL_CSS + "</style>")
    # Ảnh thêm thủ công có thể không có link trang nguồn: href rỗng sẽ mở lại chính trang duyệt, nên rơi về link ảnh.
    sub('href="${esc(r.source_url)}"', 'href="${esc(r.source_url || r.image_url)}"')
    sub('<div class="grid" id="grid"></div>', MANUAL_ZONE + '<div class="grid" id="grid"></div>')
    sub("  const entities = [];", "  (state.manual || []).forEach(r => DATA.push(r));\n  const entities = [];")
    sub("  function render() { renderSide(); renderHead(); renderGrid(); }", "  function render() { renderSide(); renderHead(); renderGrid(); updateZone(); }")
    sub('"rules", "audit"];', '"rules", "audit", "source_url", "origin"];')
    sub('r.rules || "", r.audit || ""].map(csvCell)', 'r.rules || "", r.audit || "", r.source_url || "", r.origin || ""].map(csvCell)')
    sub("  render();\n})();", js + "  render();\n})();")
    return html


if __name__ == "__main__":
    main()
