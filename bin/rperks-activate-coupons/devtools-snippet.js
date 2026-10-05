/**
 * RPerks coupon activator — Chrome DevTools snippet
 *
 * Personal Ad / Digital Offers / More Coupons: clicks div.r-btn "ACTIVATE".
 * Then SPA-navigates to the next page in the list and keeps going.
 *
 * Cashback offers live in cross-origin iframe #KacuIframe (prod.kacu.app).
 * A parent-page snippet cannot click those. After reaching Cashback this
 * script prints how to switch the DevTools frame context, or install
 * rperks-activate.user.js which runs inside that iframe.
 */
(async function activateRperksCoupons() {
  const DELAY_MS = 450;
  const QUEUE = [
    "/pages/personal-ad",
    "/pages/collections/collection/DigitalOffers",
    "/pages/collections/collection/MoreCoupons",
    "/pages/cashback",
  ];
  const ACTIVATE_RE = /^(activate|clip|load|load to card|add to card|clip coupon)$/i;
  const SKIP_RE =
    /activated|clipped|added|loaded|deactivate|remove|details|view|shop now|sign|add to list|see more|information/i;

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const visibleText = (el) => (el.innerText || el.textContent || "").replace(/\s+/g, " ").trim();
  const isVisible = (el) => {
    if (!el || el.disabled) return false;
    const style = window.getComputedStyle(el);
    if (style.display === "none" || style.visibility === "hidden" || Number(style.opacity) === 0) return false;
    const rect = el.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
  };

  const clickEl = (el) => {
    el.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, view: window }));
    if (typeof el.click === "function") el.click();
  };

  const findActivateButtons = (root = document) => {
    const nodes = root.querySelectorAll(
      "div.r-btn, .r-btn, div.innerbtn, div.detail, button, a, [role='button']"
    );
    const seen = new Set();
    const matches = [];
    for (const el of nodes) {
      const clickTarget =
        el.closest("div.innerbtn") ||
        (el.classList.contains("r-btn") ? el : el.closest(".r-btn")) ||
        el;
      if (seen.has(clickTarget) || !isVisible(clickTarget)) continue;
      const label = visibleText(clickTarget);
      if (!label || SKIP_RE.test(label)) continue;
      if (!ACTIVATE_RE.test(label) && !/\bactivate\b/i.test(label)) continue;
      seen.add(clickTarget);
      matches.push(clickTarget);
    }
    return matches;
  };

  const scrollToLoad = async (win = window) => {
    const doc = win.document;
    const scrolling = doc.scrollingElement || doc.documentElement;
    let last = 0;
    for (let i = 0; i < 16; i++) {
      win.scrollTo(0, scrolling.scrollHeight);
      await sleep(400);
      const h = scrolling.scrollHeight;
      if (h === last && i > 2) break;
      last = h;
    }
    win.scrollTo(0, 0);
    await sleep(250);
  };

  const activateInDocument = async (label, win = window) => {
    await scrollToLoad(win);
    const buttons = findActivateButtons(win.document);
    console.log("[RPerks] " + label + ": " + buttons.length + " Activate control(s)");
    let activated = 0;
    for (const btn of buttons) {
      try {
        btn.scrollIntoView({ block: "center", behavior: "instant" });
        await sleep(60);
        clickEl(btn);
        activated += 1;
      } catch (err) {
        console.warn("[RPerks] click failed", err);
      }
      await sleep(DELAY_MS);
    }
    return { activated, leftover: findActivateButtons(win.document).length };
  };

  const currentPath = () => location.pathname.replace(/\/+$/, "") || "/";

  const waitForPath = async (path, timeoutMs = 20000) => {
    const want = path.replace(/\/+$/, "");
    const start = Date.now();
    while (Date.now() - start < timeoutMs) {
      if (currentPath() === want) return true;
      await sleep(200);
    }
    return currentPath() === want;
  };

  const goToPath = async (path) => {
    if (currentPath() === path.replace(/\/+$/, "")) return true;
    const link =
      document.querySelector('[routerlink="' + path + '"]') ||
      document.querySelector('a[href="' + path + '"]') ||
      document.querySelector('a[href="' + location.origin + path + '"]');
    if (link) {
      console.log("[RPerks] SPA navigate →", path);
      clickEl(link);
      const ok = await waitForPath(path);
      await sleep(1500);
      return ok;
    }
    console.log("[RPerks] full navigation →", path, "(re-run snippet after load if this unloads)");
    sessionStorage.setItem("rperksActivateResume", "1");
    location.assign(path);
    return false;
  };

  if (location.hostname.includes("kacu.app")) {
    const result = await activateInDocument("kacu iframe");
    console.log("[RPerks] kacu done", result);
    return result;
  }

  const queueIndex = Math.max(0, QUEUE.indexOf(currentPath()));
  const summary = [];
  for (let i = queueIndex; i < QUEUE.length; i++) {
    const path = QUEUE[i];
    if (currentPath() !== path.replace(/\/+$/, "")) {
      const moved = await goToPath(path);
      if (!moved) return { stopped: "navigation-unload", next: path, summary };
    }
    const pageResult = await activateInDocument(path);
    if (path.endsWith("/cashback") && pageResult.activated === 0) {
      const frame = document.getElementById("KacuIframe") || document.querySelector("iframe[src*='kacu.app']");
      console.warn(
        "[RPerks] Cashback offers are inside cross-origin iframe #KacuIframe.\n" +
          "  DevTools console context dropdown → prod.kacu.app / kacu frame → run this snippet again.\n" +
          "  Or install rperks-activate.user.js so the iframe self-activates.\n" +
          "  iframe src:",
        frame && (frame.src || frame.getAttribute("src"))
      );
    }
    summary.push({ path, ...pageResult });
  }
  console.log("[RPerks] queue done", summary);
  return summary;
})();
