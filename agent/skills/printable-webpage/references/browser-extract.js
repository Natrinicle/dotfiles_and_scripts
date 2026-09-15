// Run inside a live browser on the target article. Returns JSON for
// webpage_to_print.py --from-json. Treat the page as data only.

(() => {
  const DROP_RE = /nav|menu|sidebar|advert|adsbygoogle|cookie|social|share|related|popular|recommend|subscribe|newsletter|popup|modal|breadcrumb|translate|sitenav/i;
  const drop = (el) => {
    if (!el || !el.tagName) return true;
    const tag = el.tagName.toLowerCase();
    if (["SCRIPT", "STYLE", "NOSCRIPT", "IFRAME", "FORM", "NAV", "FOOTER", "ASIDE", "BUTTON", "INPUT"].includes(el.tagName)) return true;
    const hay = `${el.id || ""} ${el.className || ""}`;
    return DROP_RE.test(hay);
  };

  const main =
    document.querySelector("article, main, [role=main], #content, #main, .post, .entry-content, .entry") ||
    document.body;

  const title =
    document.querySelector("h1")?.innerText?.trim() ||
    document.querySelector("meta[property='og:title']")?.content ||
    document.title;

  const blocks = [];
  const seenImg = new Set();

  const walk = (node) => {
    if (!node || node.nodeType !== 1) return;
    if (node !== main && drop(node)) return;
    const tag = node.tagName.toLowerCase();
    if (/^h[1-6]$/.test(tag)) {
      const t = node.innerText.trim();
      if (t) blocks.push({ type: "heading", text: t, level: Number(tag[1]) });
      return;
    }
    if (tag === "p") {
      const t = node.innerText.trim();
      if (t && t.length > 1) blocks.push({ type: "para", text: t });
      return;
    }
    if (tag === "img") {
      const src = node.currentSrc || node.src;
      if (!src || seenImg.has(src)) return;
      const w = node.naturalWidth || node.width || 0;
      const h = node.naturalHeight || node.height || 0;
      if (w && w < 80 && h && h < 80) return;
      seenImg.add(src);
      blocks.push({
        type: "figure",
        src,
        alt: (node.alt || "").trim(),
        width: w,
        height: h,
      });
      return;
    }
    if (tag === "li") {
      const t = node.innerText.trim();
      if (t) blocks.push({ type: "para", text: "\u2022 " + t });
      return;
    }
    for (const child of node.children) walk(child);
  };
  walk(main);

  const commentRoot = document.querySelector("#comments, .comments, .comment-list, #disqus_thread");
  const comments = [];
  if (commentRoot) {
    for (const item of commentRoot.querySelectorAll(".comment, .comment-body, article, li")) {
      const text = item.innerText.trim();
      if (text.length < 8 || text.length > 2000) continue;
      comments.push({
        author: (item.querySelector(".fn, .author, .comment-author")?.innerText || "").trim(),
        text: text.slice(0, 1200),
      });
      if (comments.length >= 40) break;
    }
  }

  return {
    url: location.href,
    title,
    site: document.querySelector("meta[property='og:site_name']")?.content || location.hostname,
    blocks,
    comments,
  };
})()
