// ==UserScript==
// @name         RPerks Activate Coupons
// @namespace    local.rperks
// @version      1.1.0
// @description  Activate RPerks coupons on Personal Ad / Digital Offers / More Coupons and inside the Kacu cashback iframe
// @match        https://rperks.shopridleys.com/*
// @match        https://prod.kacu.app/*
// @run-at       document-idle
// @grant        none
// ==/UserScript==

(async function () {
  const DELAY_MS = 450;
  const QUEUE = [
    "/pages/personal-ad",
    "/pages/collections/collection/DigitalOffers",
    "/pages/collections/collection/MoreCoupons",
    "/pages/cashback",
  ];
  const FLAG = "rperksActivateWalk";
  const ACTIVATE_RE = /^(activate|clip|load|load to card|add to card|clip coupon)$/i;
  const SKIP_RE =
    /activated|clipped|added|loaded|deactivate|remove|details|view|shop now|sign|add to list|see more|information/i;

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const visibleText = (el) => (el.innerText || el.textContent || "").replace(/\s+/g, " ").trim();
  const walking = () => sessionStorage.getItem(FLAG) === "1";
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

  const findActivateButtons = () => {
    const nodes = document.querySelectorAll("div.r-btn, .r-btn, div.innerbtn, div.detail, button, a, [role='button']");
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

  const scrollToLoad = async () => {
    const scrolling = document.scrollingElement || document.documentElement;
    let last = 0;
    for (let i = 0; i < 16; i++) {
      window.scrollTo(0, scrolling.scrollHeight);
      await sleep(400);
      const h = scrolling.scrollHeight;
      if (h === last && i > 2) break;
      last = h;
    }
    window.scrollTo(0, 0);
    await sleep(300);
  };

  const activateHere = async (label) => {
    await scrollToLoad();
    const buttons = findActivateButtons();
    console.log(`[RPerks] ${label}: ${buttons.length} Activate control(s)`);
    let activated = 0;
    for (const btn of buttons) {
      btn.scrollIntoView({ block: "center" });
      clickEl(btn);
      activated += 1;
      await sleep(DELAY_MS);
    }
    return activated;
  };

  if (location.hostname.includes("kacu.app")) {
    // Iframe loads after the parent hits /pages/cashback. Always clip here.
    await sleep(800);
    await activateHere("kacu");
    return;
  }

  const currentPath = () => location.pathname.replace(/\/+$/, "") || "/";

  const goToPath = (path) => {
    const link =
      document.querySelector(`[routerlink="${path}"]`) ||
      document.querySelector(`a[href="${path}"]`);
    if (link) {
      clickEl(link);
      return;
    }
    location.assign(path);
  };

  window.rperksActivateAll = async function rperksActivateAll() {
    sessionStorage.setItem(FLAG, "1");
    let idx = QUEUE.indexOf(currentPath());
    if (idx < 0) idx = 0;
    for (let i = idx; i < QUEUE.length; i++) {
      const path = QUEUE[i];
      if (currentPath() !== path) {
        goToPath(path);
        for (let t = 0; t < 50 && currentPath() !== path; t++) await sleep(200);
        await sleep(1500);
      }
      await activateHere(path);
      if (path.endsWith("/cashback")) {
        await sleep(2500);
        console.log("[RPerks] cashback parent done; kacu iframe userscript should clip inside the frame");
      }
    }
    sessionStorage.removeItem(FLAG);
    console.log("[RPerks] walk finished");
  };

  if (walking()) {
    await sleep(1200);
    window.rperksActivateAll();
  } else {
    console.log("[RPerks] userscript loaded. Run rperksActivateAll() in the console, or use the DevTools snippet.");
  }
})();
