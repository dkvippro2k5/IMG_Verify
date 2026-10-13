  // ---------- thêm ảnh thủ công: kéo thả từ Google/Bing Images (hoặc trang khác) / dán link ----------
  // Được build_extra_review.py chèn vào cuối IIFE của review.html. Ảnh thêm lưu trong localStorage (state.manual),
  // nạp lại vào DATA lúc mở trang, và được xuất cùng nhãn (cột source_url, origin = "manual"; sha256 để trống, tải về sau).
  state.manual = state.manual || [];
  const GBASE = "https://www.google.com";
  function absUrl(u) { try { return new URL(u, GBASE).href; } catch (e) { return ""; } }
  function isHttp(u) { return /^https?:\/\//i.test(u || ""); }
  function hostOf(u) { try { return new URL(u).hostname; } catch (e) { return ""; } }
  // Trang giao diện của công cụ tìm ảnh (không phải trang nguồn của ảnh).
  function isSearchUi(u) { return /(^|\.)(google\.[a-z.]+|bing\.com)$/i.test(hostOf(u)) && !isThumbHost(u); }
  // Máy chủ ảnh thu nhỏ của công cụ tìm ảnh.
  function isThumbHost(u) { return /(^|\.)(gstatic\.com|bing\.net)$/i.test(hostOf(u)) || hostOf(u) === "th.bing.com"; }
  // Ảnh thu nhỏ của Bing: bỏ tham số kích thước thì Bing trả bản lớn hơn.
  function bingFull(u) {
    try {
      const x = new URL(u);
      if (!(x.hostname === "th.bing.com" || /(^|\.)mm\.bing\.net$/i.test(x.hostname))) return u;
      ["w", "h", "c", "r", "o", "dpr", "rm"].forEach(k => x.searchParams.delete(k));
      return x.href;
    } catch (e) { return u; }
  }
  const BOILER = /^(kết quả hình ảnh cho|image result for|hình ảnh)\b/i;

  function decodeEntities(s) {
    return s.replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">");
  }

  // Lấy URL ảnh gốc + URL trang nguồn + tiêu đề từ sự kiện thả.
  // Google: imgres?imgurl=..&imgrefurl=.. hoặc /url?url=..; Bing: thuộc tính m='{"murl":..,"purl":..,"t":..}' hoặc mediaurl=..
  function extractDrop(dt) {
    const imgs = [], pages = [];
    let title = "";
    const fromQuery = href => {
      try {
        const u = new URL(href, GBASE);
        const iu = u.searchParams.get("imgurl") || u.searchParams.get("mediaurl"), ru = u.searchParams.get("imgrefurl");
        if (iu) { imgs.unshift(iu); if (ru) pages.unshift(ru); return true; }
        if (u.pathname === "/url") {   // liên kết chuyển hướng của Google: trang đích ở tham số url hoặc q
          const t = u.searchParams.get("url") || u.searchParams.get("q");
          if (t && isHttp(t)) { pages.unshift(t); return true; }
        }
      } catch (e) { /* bỏ qua */ }
      return false;
    };
    const html = dt.getData("text/html");
    if (html) {
      // Bing: dữ liệu ảnh gốc nằm trong thuộc tính m của thẻ kết quả.
      const mm = html.match(/\sm=(["'])(\{.*?\})\1/s);
      if (mm) {
        try {
          const j = JSON.parse(decodeEntities(mm[2]));
          if (j.murl) imgs.unshift(j.murl);
          if (j.purl) pages.unshift(j.purl);
          if (j.t) title = j.t;
        } catch (e) { /* bỏ qua */ }
      }
      let doc = null;
      try { doc = new DOMParser().parseFromString(html, "text/html"); } catch (e) { doc = null; }
      if (doc) {
        const a = doc.querySelector("a[href]");
        if (a) {
          const href = absUrl(a.getAttribute("href"));
          if (!fromQuery(href) && isHttp(href) && !isSearchUi(href)) pages.push(href);
          title = title || a.getAttribute("title") || "";
        }
        const im = doc.querySelector("img");
        if (im) {
          const src = im.getAttribute("src") || "";
          if (src) imgs.push(src.startsWith("data:") ? src : absUrl(src));
          const alt = im.getAttribute("alt") || "";
          if (!title && alt && !BOILER.test(alt.trim())) title = alt;
        }
      }
    }
    (dt.getData("text/uri-list") || "").split(/\r?\n/).filter(l => l && !l.startsWith("#")).forEach(l => {
      if (!fromQuery(l) && isHttp(l) && !isSearchUi(l)) imgs.push(l);
    });
    const txt = (dt.getData("text/plain") || "").trim();
    if (isHttp(txt) && !fromQuery(txt) && !isSearchUi(txt)) imgs.push(txt);
    const full = imgs.find(u => isHttp(u) && !isThumbHost(u));          // ưu tiên ảnh gốc
    let img = full || imgs.find(u => isHttp(u)) || imgs.find(u => u.startsWith("data:")) || "";
    if (img && !full && isHttp(img)) img = bingFull(img);
    const page = pages.find(u => isHttp(u) && !isSearchUi(u)) || "";
    return { img, page, title: title.trim(), thumbOnly: !!img && !full && !img.startsWith("data:") };
  }

  function hash31(s) { let h = 7; for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) % 1000000000; return h; }

  function addManual(x) {
    const slug = state.current, rows0 = byEntity[slug];
    if (!rows0) return toast("Chưa chọn entity");
    if (!x.img) return toast("Không lấy được URL ảnh. Thử dán link vào ô bên dưới");
    if (x.img.startsWith("data:")) return toast("Chỉ có ảnh thu nhỏ (data:). Bấm mở ảnh cỡ đầy đủ rồi kéo lại, hoặc dán link ảnh");
    if (rows0.some(r => r.image_url === x.img)) return toast("Ảnh này đã có trong entity");
    const base = rows0[0];
    let ln = 3000000000 + hash31(slug + "|" + x.img);
    const used = new Set(DATA.map(r => r.line_no));
    while (used.has(ln)) ln++;
    const r = {
      line_no: ln, entity_id: base.entity_id, slug, canonical_name: base.canonical_name, category: base.category,
      query: base.query, sha256: "", image_url: x.img, local_image: "", description: x.title || "", width: "", height: "",
      face_count: "", face_area_pct: "", source_url: x.page || "", source_domain: x.page ? hostOf(x.page) : "mở ảnh (không có link nguồn)",
      auto_flag: "", audit: "0", rules: "", warnings: "", batch: base.batch, crawled: 1, origin: "manual", trust: "manual",
      id_sim: "", ref_type: ""
    };
    state.manual.push(r);
    DATA.push(r);
    byEntity[slug].push(r);
    setLabel(r, { flag: "approved", identity: "match", reasons: [] });   // ảnh do bạn chủ động chọn: mặc định approved, bỏ chọn nếu cần
    save();
    render();
    toast((x.thumbOnly ? "Đã thêm (chỉ có link ảnh thu nhỏ của công cụ tìm kiếm, ảnh có thể mờ)" : "Đã thêm ảnh vào " + base.canonical_name)
      + (x.page ? "" : " · không lấy được link trang nguồn"));
  }

  function removeManual(line) {
    const i = state.manual.findIndex(r => r.line_no === line);
    if (i < 0) return;
    const r = state.manual[i];
    state.manual.splice(i, 1);
    DATA.splice(DATA.indexOf(r), 1);
    byEntity[r.slug].splice(byEntity[r.slug].indexOf(r), 1);
    delete state.labels[line];
    save();
    render();
  }

  function updateZone() {
    const z = $("dropZone");
    if (!z) return;
    const rows = byEntity[state.current] || [];
    const n = rows.filter(r => r.origin === "manual").length;
    $("dzTarget").textContent = rows[0] ? rows[0].canonical_name : "";
    $("dzCount").textContent = n ? ` · đã thêm ${n} ảnh thủ công` : "";
  }

  $("dzAdd").onclick = () => {
    addManual({ img: $("dzImg").value.trim(), page: $("dzPage").value.trim(), title: "" });
    $("dzImg").value = ""; $("dzPage").value = "";
  };
  $("dzImg").addEventListener("keydown", e => { if (e.key === "Enter") $("dzAdd").click(); });
  $("dzPage").addEventListener("keydown", e => { if (e.key === "Enter") $("dzAdd").click(); });
  $("grid").addEventListener("click", e => {
    const b = e.target.closest('[data-act="delmanual"]');
    if (!b) return;
    e.stopPropagation();
    removeManual(Number(b.dataset.line));
  }, true);

  // Sửa/dán link bài viết ngay trên thẻ ảnh thêm thủ công (không vẽ lại cả trang để khỏi mất vị trí cuộn/ô đang gõ).
  $("grid").addEventListener("change", e => {
    const inp = e.target.closest(".srcin");
    if (!inp) return;
    const r = state.manual.find(x => x.line_no === Number(inp.dataset.line));
    if (!r) return;
    const v = inp.value.trim();
    if (v && !/^https?:\/\//i.test(v)) return toast("Link bài viết phải bắt đầu bằng http:// hoặc https://");
    r.source_url = v;
    r.source_domain = v ? hostOf(v) : "mở ảnh (không có link nguồn)";
    const card = inp.closest(".card"), link = card && card.querySelector(".facts a");
    if (link) { link.href = v || r.image_url; link.textContent = r.source_domain; }
    save();
    toast(v ? "Đã lưu link bài viết" : "Đã xoá link bài viết");
  });

  const dropTypes = dt => dt && Array.prototype.some.call(dt.types || [], t => /uri-list|html|plain/.test(t));
  let dragDepth = 0;
  window.addEventListener("dragenter", e => { if (dropTypes(e.dataTransfer)) { dragDepth++; document.body.classList.add("dz-active"); } });
  window.addEventListener("dragleave", () => { dragDepth = Math.max(0, dragDepth - 1); if (!dragDepth) document.body.classList.remove("dz-active"); });
  window.addEventListener("dragover", e => { if (dropTypes(e.dataTransfer)) e.preventDefault(); });
  window.addEventListener("drop", e => {
    dragDepth = 0; document.body.classList.remove("dz-active");
    if (!dropTypes(e.dataTransfer)) return;
    e.preventDefault();
    const dt = e.dataTransfer;
    const got = {};
    Array.prototype.forEach.call(dt.types || [], t => { try { got[t] = dt.getData(t); } catch (err) { /* bỏ qua */ } });
    console.log("[kéo thả] dữ liệu nhận được:", got);   // để chẩn đoán khi không lấy được link nguồn
    addManual(extractDrop(dt));
  });

  // ---------- đẩy entity chưa duyệt lên đầu danh sách (tính lúc mở/F5 trang) ----------
  function isDone(r) { return !!effective(r).flag; }
  function pending(slug) { return byEntity[slug].some(r => !isDone(r)); }
  (function reorderEntities() {
    const idx = new Map(entities.map((s, i) => [s, i]));
    const pend = new Map(entities.map(s => [s, pending(s)]));
    entities.sort((a, b) => (pend.get(a) ? 0 : 1) - (pend.get(b) ? 0 : 1) || idx.get(a) - idx.get(b));
    entities.forEach(s => {
      const lab = pend.get(s) ? "⏳ Chưa duyệt" : "✓ Đã duyệt xong";
      byEntity[s].forEach(r => { r.batch = lab; });
    });
    if (!pend.get(state.current)) { const first = entities.find(s => pend.get(s)); if (first) { state.current = first; state.focus = 0; } }
  })();

