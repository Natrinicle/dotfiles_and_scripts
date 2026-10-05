#!/usr/bin/env node
/**
 * Launch (or attach to) Chrome, sign into YOUR RPerks account if needed,
 * then activate coupons on Personal Ad, Digital Offers, More Coupons, and
 * Cashback (including the prod.kacu.app iframe).
 *
 * Credentials are read from, in order:
 *   1. env RPERKS_USERNAME / RPERKS_PASSWORD  (preferred)
 *   2. ./config.json  (gitignored; copy from config.example.json)
 *
 * Never put a real password in this file.
 *
 *   cp config.example.json config.json
 *   npm view puppeteer-core
 *   npm install
 *   node run-rperks.mjs
 *   node run-rperks.mjs --dry-run
 */

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import puppeteer from "puppeteer-core";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ORIGIN = "https://rperks.shopridleys.com";
const PAGES = [
  `${ORIGIN}/pages/personal-ad`,
  `${ORIGIN}/pages/collections/collection/DigitalOffers`,
  `${ORIGIN}/pages/collections/collection/MoreCoupons`,
  `${ORIGIN}/pages/cashback`,
];

const argv = Object.fromEntries(
  process.argv.slice(2).map((a) => {
    const [k, v] = a.replace(/^--/, "").split("=");
    return [k, v === undefined ? true : v];
  })
);

function expandHome(p) {
  if (!p) return p;
  return p.startsWith("~/") ? path.join(os.homedir(), p.slice(2)) : p;
}

function optionalCoord(v) {
  if (v === undefined || v === null || v === "") return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function loadConfig() {
  const raw = {};
  const cfgPath = path.join(HERE, "config.json");
  if (fs.existsSync(cfgPath)) {
    Object.assign(raw, JSON.parse(fs.readFileSync(cfgPath, "utf8")));
  }
  const username = process.env.RPERKS_USERNAME || raw.username || "";
  const password = process.env.RPERKS_PASSWORD || raw.password || "";
  if (!username || !password || password === "replace-me") {
    console.error(
      "Set RPERKS_USERNAME and RPERKS_PASSWORD, or copy config.example.json to config.json and fill them in."
    );
    process.exit(1);
  }
  return {
    username,
    password,
    delayMs: Number(argv.delay || raw.delayMs || 450),
    // --headless=false overrides config.json so a scheduled headless run
    // can still be watched in a real window.
    headless:
      argv.headless === undefined
        ? raw.headless === true
        : argv.headless === true || argv.headless === "true" || argv.headless === "1",
    userDataDir: expandHome(raw.userDataDir || "~/.config/rperks-chrome"),
    dryRun: Boolean(argv["dry-run"]),
    fresh: argv.fresh === true || argv.fresh === "true",
    chromePath: raw.chromePath || process.env.CHROME_PATH || detectChrome(),
    latitude: optionalCoord(raw.latitude),
    longitude: optionalCoord(raw.longitude),
  };
}

function detectChrome() {
  const candidates = [
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium-browser",
    "/usr/bin/chromium",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
  ];
  return candidates.find((p) => fs.existsSync(p)) || "google-chrome";
}

const INJECTED = `
async function activateRperksCoupons(opts = {}) {
  const DELAY_MS = opts.delayMs ?? 450;
  const DRY_RUN = !!opts.dryRun;
  const ACTIVATE_RE = /^(activate|clip|load|load to card|add to card|clip coupon)$/i;
  const SKIP_RE = /activated|clipped|added|loaded|deactivate|remove|details|view|shop now|sign|add to list|see more|information/i;
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const visibleText = (el) => (el.innerText || el.textContent || "").replace(/\\s+/g, " ").trim();
  const isVisible = (el) => {
    if (!el || el.disabled) return false;
    const style = window.getComputedStyle(el);
    if (style.display === "none" || style.visibility === "hidden" || Number(style.opacity) === 0) return false;
    const rect = el.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
  };
  const findActivateButtons = () => {
    const nodes = document.querySelectorAll("div.r-btn, .r-btn, div.innerbtn, div.detail, button, a, [role='button']");
    const seen = new Set();
    const matches = [];
    for (const el of nodes) {
      const clickEl = el.closest("div.innerbtn") || (el.classList.contains("r-btn") ? el : el.closest(".r-btn")) || el;
      if (seen.has(clickEl) || !isVisible(clickEl)) continue;
      const label = visibleText(clickEl);
      if (!label || SKIP_RE.test(label)) continue;
      if (!ACTIVATE_RE.test(label) && !/\\bactivate\\b/i.test(label)) continue;
      seen.add(clickEl);
      matches.push(clickEl);
    }
    return matches;
  };
  const scrolling = document.scrollingElement || document.documentElement;
  let last = 0;
  for (let i = 0; i < 14; i++) {
    window.scrollTo(0, scrolling.scrollHeight);
    await sleep(350);
    if (scrolling.scrollHeight === last && i > 2) break;
    last = scrolling.scrollHeight;
  }
  window.scrollTo(0, 0);
  await sleep(200);
  const buttons = findActivateButtons();
  const labels = buttons.map(visibleText);
  if (DRY_RUN) return { activated: 0, leftover: buttons.length, labels, dryRun: true, href: location.href };
  let activated = 0;
  let failed = 0;
  for (const btn of buttons) {
    try {
      btn.scrollIntoView({ block: "center", behavior: "instant" });
      btn.click();
      activated += 1;
    } catch { failed += 1; }
    await sleep(DELAY_MS);
  }
  return { activated, failed, leftover: findActivateButtons().length, labels, href: location.href };
}
`;

async function pageText(page) {
  return page.evaluate(() => (document.body && document.body.innerText) || "");
}

async function isLoggedIn(page) {
  return page.evaluate(() => {
    const text = (document.body && document.body.innerText) || "";
    const hasSignInCta = /\b(sign in|log in|create my account|sign up)\b/i.test(text);
    const hasSession = /\b(log out|sign out)\b/i.test(text) || /^hi\s+[a-z]/im.test(text);
    const hasOffers = !!document.querySelector("div.r-btn, #KacuIframe");
    if (hasSignInCta && !hasSession && !hasOffers) return false;
    return hasSession || hasOffers;
  });
}

async function grantLocation(page, cfg) {
  const origins = [ORIGIN, "https://prod.kacu.app", "https://ridleys.immapi.com"];
  const ctx = page.browserContext();
  for (const origin of origins) {
    try {
      await ctx.overridePermissions(origin, ["geolocation"]);
    } catch (err) {
      console.warn("permission override failed for", origin, err.message);
    }
  }
  if (Number.isFinite(cfg.latitude) && Number.isFinite(cfg.longitude)) {
    await page.setGeolocation({
      latitude: cfg.latitude,
      longitude: cfg.longitude,
      accuracy: 80,
    });
  } else {
    console.warn("No store latitude/longitude in config; skipping geolocation override.");
  }
}

async function settle(page, ms = 2000) {
  await page.waitForNetworkIdle({ idleTime: 800, timeout: 15000 }).catch(() => {});
  await new Promise((r) => setTimeout(r, ms));
}

async function clickMatching(page, re) {
  return page.evaluate((pattern) => {
    const rx = new RegExp(pattern, "i");
    const nodes = [...document.querySelectorAll("a, button, [role='button'], ion-button, ion-item")];
    const el = nodes.find((n) => {
      const label = (n.innerText || "").replace(/\s+/g, " ").trim();
      if (!rx.test(label) || n.offsetParent === null) return false;
      const href = (n.getAttribute("href") || n.getAttribute("routerlink") || "").toLowerCase();
      if (href.includes("/login") || href.includes("sign-in")) return false;
      return true;
    });
    if (!el) return false;
    el.click();
    return true;
  }, re.source);
}

async function clickLoginSubmit(page) {
  const clicked = await page.evaluate(() => {
    const labelOf = (n) => (n.innerText || n.textContent || "").replace(/\s+/g, " ").trim();
    const isSignIn = (n) => /^(sign[\s-]?in|log[\s-]?in|submit)$/i.test(labelOf(n));
    const candidates = [
      ...document.querySelectorAll("form ion-button, form button, form [type='submit']"),
      ...document.querySelectorAll("ion-button, button, [type='submit'], [role='button']"),
    ];
    const pass = document.querySelector('input[placeholder="Password"], ion-input[placeholder="Password"]');
    const passTop = pass ? pass.getBoundingClientRect().top : 0;
    const el = candidates.find((n) => {
      if (!isSignIn(n)) return false;
      const href = (n.getAttribute("href") || n.getAttribute("routerlink") || "").toLowerCase();
      if (href.includes("/login")) return false;
      const header = n.closest("ion-header, ion-toolbar, header, nav");
      if (header) return false;
      if (passTop && n.getBoundingClientRect().top < passTop - 20) return false;
      return true;
    });
    if (!el) return null;
    el.scrollIntoView({ block: "center" });
    el.click();
    const native = el.shadowRoot && el.shadowRoot.querySelector("button");
    if (native) native.click();
    return { tag: el.tagName, text: labelOf(el).slice(0, 40) };
  });
  console.log("  submit click:", clicked || "no form Sign In button found");
  return Boolean(clicked);
}

async function describeLoginFields(page) {
  const info = await page.evaluate(() => {
    const walk = [];
    const visit = (root, path) => {
      if (!root) return;
      for (const el of root.querySelectorAll("input, ion-input, textarea")) {
        walk.push({
          tag: el.tagName.toLowerCase(),
          type: (el.getAttribute("type") || el.type || "").toLowerCase(),
          name: el.getAttribute("name") || "",
          placeholder: el.getAttribute("placeholder") || "",
          path,
        });
        if (el.shadowRoot) visit(el.shadowRoot, path + ">" + el.tagName.toLowerCase());
      }
    };
    visit(document, "doc");
    return walk;
  });
  console.log("  login fields:", JSON.stringify(info));
}

async function fillByPlaceholder(page, placeholderRe, value) {
  const handle = await page.evaluateHandle((pattern) => {
    const rx = new RegExp(pattern, "i");
    const pick = (el) => {
      const ph = (el.getAttribute("placeholder") || el.placeholder || "").trim();
      const label = (el.getAttribute("aria-label") || "").trim();
      return rx.test(ph) || rx.test(label);
    };
    for (const ion of document.querySelectorAll("ion-input")) {
      if (!pick(ion)) continue;
      const inner =
        (ion.shadowRoot && ion.shadowRoot.querySelector("input")) ||
        ion.querySelector("input") ||
        document.querySelector(`input[name="${ion.querySelector("input")?.name || ""}"]`);
      const named = document.querySelector("input[placeholder]") ;
      if (ion.shadowRoot) {
        const s = ion.shadowRoot.querySelector("input");
        if (s) return s;
      }
      const sibling = ion.querySelector("input");
      if (sibling) return sibling;
    }
    for (const el of document.querySelectorAll("input, textarea")) {
      if (pick(el)) return el;
    }
    return null;
  }, placeholderRe.source);
  const el = handle.asElement();
  if (!el) {
    await handle.dispose();
    return false;
  }
  try {
    await el.click({ clickCount: 3 });
    await page.keyboard.down("Control");
    await page.keyboard.press("KeyA");
    await page.keyboard.up("Control");
    await el.type(value, { delay: 20 });
    await page.evaluate((node, val) => {
      const proto = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value");
      if (proto && proto.set) proto.set.call(node, val);
      else node.value = val;
      node.dispatchEvent(new InputEvent("input", { bubbles: true, data: val }));
      node.dispatchEvent(new Event("change", { bubbles: true }));
    }, el, value);
    return true;
  } catch (err) {
    console.warn("  fill failed:", err.message);
    return false;
  } finally {
    await handle.dispose();
  }
}

function isRperksHomepage(url) {
  try {
    const parsed = new URL(url);
    if (parsed.origin !== ORIGIN) return false;
    const path = parsed.pathname.replace(/\/+$/, "") || "/";
    return path === "/" || path === "/welcome";
  } catch {
    return false;
  }
}

async function clickSignInEntry(page) {
  return page.evaluate(() => {
    const nodes = [];
    const walk = (root) => {
      if (!root) return;
      for (const el of root.querySelectorAll("a, button, [role='button'], ion-button, ion-item")) {
        nodes.push(el);
        if (el.shadowRoot) walk(el.shadowRoot);
      }
    };
    walk(document);
    const el = nodes.find((n) => {
      const label = (n.innerText || n.textContent || "").replace(/\s+/g, " ").trim();
      if (!/^(sign in|log in)$/i.test(label)) return false;
      const rect = n.getBoundingClientRect();
      return rect.width > 1 && rect.height > 1;
    });
    if (!el) return null;
    el.click();
    return (el.innerText || el.textContent || "").replace(/\s+/g, " ").trim().slice(0, 40);
  });
}

async function submitLoginForm(page, cfg) {
  if (!/\/login/i.test(page.url())) {
    await clickMatching(page, /^(sign in|log in)$/);
    await settle(page, 1200);
    if (!/\/login/i.test(page.url())) {
      await page.goto(`${ORIGIN}/login`, { waitUntil: "networkidle2", timeout: 30000 }).catch(() => {});
      await settle(page, 1500);
    }
  }

  // Headless loads of /login sometimes commit, then the SPA sends the
  // window back to /. Click Sign In on that page, and open /login again
  // if the click did not stay there. One extra try per login attempt.
  if (cfg.headless && isRperksHomepage(page.url())) {
    console.log("  headless login returned to the homepage; trying Sign In once more.");
    const clicked = await clickSignInEntry(page);
    console.log("  second sign-in click:", clicked || "not found");
    await settle(page, 1200);
    if (!/\/login/i.test(page.url())) {
      await page.goto(`${ORIGIN}/login`, { waitUntil: "domcontentloaded", timeout: 30000 }).catch(() => {});
    }
    await page
      .waitForSelector("input[placeholder='Email'], ion-input[placeholder='Email']", { timeout: 10000 })
      .catch(() => {});
    await settle(page, 800);
  }

  await page.waitForSelector("ion-input, input", { timeout: 10000 }).catch(() => {});
  console.log("  login url:", page.url());
  console.log(
    "  frames:",
    page
      .frames()
      .map((frame) => frame.url())
      .filter((url) => url && url !== "about:blank")
      .join(" | ") || "(none)"
  );
  await describeLoginFields(page);
  const preview = (await pageText(page)).replace(/\s+/g, " ").trim().slice(0, 400);
  console.log("  page text:", preview || "(empty)");

  const userFilled = await fillByPlaceholder(page, /email|username|phone/i, cfg.username);
  console.log("  username filled:", userFilled);

  const passFilled = await fillByPlaceholder(page, /^password$/i, cfg.password);
  console.log("  password filled:", passFilled);

  if (!userFilled || !passFilled) return false;

  const passHandle = await page.$('input[placeholder="Password"]');
  if (passHandle) {
    await passHandle.click();
    await page.keyboard.press("Enter");
    console.log("  pressed Enter on password field");
    await settle(page, 2000);
  }
  if (!(await isLoggedIn(page))) {
    await clickLoginSubmit(page);
    await settle(page, 3000);
  }
  return true;
}

async function loginIfNeeded(page, cfg) {
  await settle(page, 1500);
  if (await isLoggedIn(page)) {
    console.log("Already signed in (saved Chrome profile).");
    return;
  }

  for (let attempt = 1; attempt <= 3; attempt++) {
    console.log(`Not signed in — login attempt ${attempt}.`);
    const submitted = await submitLoginForm(page, cfg);
    if (!submitted) {
      console.warn("Login fields not found (page may have refreshed for location). Waiting and retrying.");
      await settle(page, 2500);
      if (await isLoggedIn(page)) {
        console.log("Signed in after refresh.");
        return;
      }
      continue;
    }

    if (await isLoggedIn(page)) {
      console.log("Signed in.");
      return;
    }

    const extra = await pageText(page);
    if (/code|verif|authenticate|2fa|one.time/i.test(extra)) {
      console.warn("Second factor requested. Complete it in the Chrome window; waiting 90s.");
      await new Promise((r) => setTimeout(r, 90000));
      if (await isLoggedIn(page)) {
        console.log("Signed in after 2FA.");
        return;
      }
    }

    console.warn("Still signed out after submit; site may have reloaded for geolocation.");
    await settle(page, 2500);
    if (await isLoggedIn(page)) {
      console.log("Signed in after geolocation reload.");
      return;
    }
  }

  throw new Error("Still not signed in after login retries. Check the Chrome window.");
}

async function activateAllFrames(page, cfg) {
  const frameResults = [];
  for (const frame of page.frames()) {
    const frameUrl = frame.url();
    if (!frameUrl || frameUrl === "about:blank") continue;
    try {
      await frame.evaluate(INJECTED);
      const result = await frame.evaluate(
        async (delayMs, dryRun) => activateRperksCoupons({ delayMs, dryRun }),
        cfg.delayMs,
        cfg.dryRun
      );
      frameResults.push({ frameUrl, ...result });
      console.log(
        `  [${frameUrl.slice(0, 72)}] activated=${result.activated} leftover=${result.leftover}` +
          (result.dryRun ? " (dry-run)" : "")
      );
    } catch (err) {
      console.warn("  skip frame", frameUrl.slice(0, 72), err.message);
    }
  }
  return frameResults;
}

async function clickVisibleLabel(page, pattern) {
  return page.evaluate((source) => {
    const rx = new RegExp(source, "i");
    const nodes = [];
    const walk = (root) => {
      if (!root) return;
      for (const el of root.querySelectorAll("*")) {
        nodes.push(el);
        if (el.shadowRoot) walk(el.shadowRoot);
      }
    };
    walk(document);
    const el = nodes.find((n) => {
      const label = (n.innerText || n.textContent || "").replace(/\s+/g, " ").trim();
      if (!label || label.length > 80 || !rx.test(label)) return false;
      const rect = n.getBoundingClientRect();
      return rect.width > 1 && rect.height > 1;
    });
    if (!el) return null;
    el.click();
    return (el.innerText || el.textContent || "").replace(/\s+/g, " ").trim().slice(0, 60);
  }, pattern);
}

async function wipeProfileSession(page) {
  const client = await page.createCDPSession();
  await client.send("Network.clearBrowserCookies");
  await client.send("Network.clearBrowserCache");
  await client.detach();
  const origins = [ORIGIN, "https://prod.kacu.app", "https://ridleys.immapi.com"];
  for (const origin of origins) {
    await page.goto(origin, { waitUntil: "domcontentloaded", timeout: 30000 }).catch((err) => {
      console.warn("  storage clear skipped", origin, err.message);
    });
    await page
      .evaluate(async () => {
        try {
          localStorage.clear();
        } catch {
          /* cross-origin or blocked */
        }
        try {
          sessionStorage.clear();
        } catch {
          /* cross-origin or blocked */
        }
        if (!indexedDB.databases) return;
        const dbs = await indexedDB.databases();
        await Promise.all(
          dbs.map(
            (db) =>
              new Promise((resolve) => {
                if (!db.name) {
                  resolve();
                  return;
                }
                const req = indexedDB.deleteDatabase(db.name);
                req.onsuccess = req.onerror = req.onblocked = () => resolve();
              })
          )
        );
      })
      .catch(() => {});
  }
}

async function signOutFresh(page) {
  console.log("Fresh start: signing out and clearing the RPerks profile session.");
  const direct = await clickVisibleLabel(page, "^(sign out|log out)$");
  console.log("  sign out click:", direct || "not visible yet");
  if (!direct) {
    const menu = await clickVisibleLabel(page, "^hi\\s+\\S+");
    console.log("  account menu:", menu || "not found");
    await settle(page, 800);
    const second = await clickVisibleLabel(page, "sign out|log out");
    console.log("  sign out click:", second || "not found");
  }
  await settle(page, 1500);
  await wipeProfileSession(page);
  await page.goto(ORIGIN, { waitUntil: "networkidle2", timeout: 60000 }).catch(() => {});
  await settle(page, 1500);
  const stillIn = await isLoggedIn(page);
  console.log("  signed in after wipe:", stillIn, "url:", page.url());
  if (stillIn) {
    throw new Error("Profile still looks signed in after sign-out and cookie wipe.");
  }
}

async function main() {
  const cfg = loadConfig();
  fs.mkdirSync(cfg.userDataDir, { recursive: true });
  console.log("Chrome:", cfg.chromePath);
  console.log("Profile:", cfg.userDataDir);
  console.log("User:", cfg.username);

  const launchArgs = ["--disable-blink-features=AutomationControlled"];
  if (!cfg.headless) {
    launchArgs.push("--start-maximized", "--window-position=40,40", "--window-size=1400,900");
    if (process.env.WAYLAND_DISPLAY) launchArgs.push("--ozone-platform=wayland");
  }
  const browser = await puppeteer.launch({
    executablePath: cfg.chromePath,
    headless: cfg.headless,
    userDataDir: cfg.userDataDir,
    defaultViewport: null,
    args: launchArgs,
  });

  const page = await browser.newPage();
  page.setDefaultTimeout(45000);
  await grantLocation(page, cfg);
  page.on("framenavigated", (frame) => {
    if (frame === page.mainFrame()) {
      console.log("navigated:", frame.url());
    }
  });
  try {
    await page.goto(ORIGIN, { waitUntil: "networkidle2", timeout: 60000 }).catch(() => {});
    await settle(page, 2000);
    await grantLocation(page, cfg);
    if (cfg.fresh) {
      await signOutFresh(page);
      await grantLocation(page, cfg);
    }
    await loginIfNeeded(page, cfg);
    if (!(await isLoggedIn(page))) {
      throw new Error("Refusing to clip: session is not logged in.");
    }

    const summary = [];
    for (const url of PAGES) {
      console.log("\n→", url);
      await page.goto(url, { waitUntil: "networkidle2", timeout: 60000 }).catch((err) => {
        console.warn("  nav warning:", err.message);
      });
      await settle(page, 2000);
      if (!(await isLoggedIn(page))) {
        console.warn("  session lost after navigation — signing in again");
        await loginIfNeeded(page, cfg);
        await page.goto(url, { waitUntil: "networkidle2", timeout: 60000 }).catch(() => {});
        await settle(page, 2000);
      }
      if (/cashback/i.test(url)) {
        await page.waitForSelector("#KacuIframe", { timeout: 15000 }).catch(() => {});
        await settle(page, 3000);
      }
      summary.push({ url, frames: await activateAllFrames(page, cfg) });
    }
    const activated = summary.flatMap((s) => s.frames).reduce((n, f) => n + (f.activated || 0), 0);
    console.log("\nDone. Total Activate clicks:", activated);
    if (!cfg.headless) {
      console.log("Leaving the window open for 20s so you can see the last page.");
      await new Promise((r) => setTimeout(r, 20000));
    }
  } catch (err) {
    if (!cfg.headless) {
      const shot = "/tmp/rperks-watch.png";
      await page.screenshot({ path: shot, fullPage: false }).catch(() => {});
      console.error("Headed debug: window stays open for 8 minutes.", page.url(), "screenshot", shot);
      await new Promise((r) => setTimeout(r, 8 * 60 * 1000));
    }
    throw err;
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
