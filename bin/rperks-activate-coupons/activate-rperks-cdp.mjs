#!/usr/bin/env node
/**
 * Attach to an already-running Chrome via DevTools Protocol and activate
 * every coupon on the RPerks pages.
 *
 * You stay logged in with your normal Chrome profile. This script does not
 * ask for or store credentials.
 *
 * 1. Quit Chrome completely, then start it with remote debugging:
 *
 *    Linux:
 *      google-chrome --remote-debugging-port=9222 --user-data-dir="$HOME/.config/google-chrome"
 *
 *    If that profile is locked because Chrome is still running, use a copy:
 *      google-chrome --remote-debugging-port=9222 --user-data-dir="$HOME/.config/rperks-chrome"
 *      (sign in once in that profile)
 *
 *    macOS:
 *      /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
 *        --remote-debugging-port=9222 --user-data-dir="$HOME/Library/Application Support/Google/Chrome"
 *
 *    Windows (PowerShell):
 *      & "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
 *
 * 2. In that Chrome window, sign in at https://rperks.shopridleys.com
 *
 * 3. npm install puppeteer-core   # verify: npm view puppeteer-core
 * 4. node activate-rperks-cdp.mjs
 *
 * Flags:
 *   --port=9222          CDP port (default 9222)
 *   --delay=450          ms between Activate clicks
 *   --dry-run            list matching buttons, do not click
 */

import puppeteer from "puppeteer-core";

const PAGES = [
  "https://rperks.shopridleys.com/pages/personal-ad",
  "https://rperks.shopridleys.com/pages/collections/collection/DigitalOffers",
  "https://rperks.shopridleys.com/pages/collections/collection/MoreCoupons",
  "https://rperks.shopridleys.com/pages/cashback",
];

const args = Object.fromEntries(
  process.argv.slice(2).map((a) => {
    const [k, v] = a.replace(/^--/, "").split("=");
    return [k, v === undefined ? true : v];
  })
);

const PORT = Number(args.port || process.env.CDP_PORT || 9222);
const DELAY_MS = Number(args.delay || 450);
const DRY_RUN = Boolean(args["dry-run"]);

const INJECTED_ACTIVATOR = `
async function activateRperksCoupons(opts = {}) {
  const DELAY_MS = opts.delayMs ?? 450;
  const DRY_RUN = !!opts.dryRun;
  const ACTIVATE_RE = /^(activate|clip|add|load|load to card|add to card|clip coupon)$/i;
  const SKIP_RE = /activated|clipped|added|loaded|deactivate|remove|details|view|shop now|sign|add to list|see more|information/i;
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const visibleText = (el) => (el.innerText || el.textContent || "").replace(/\\s+/g, " ").trim();
  const isVisible = (el) => {
    if (!el || el.disabled) return false;
    const style = window.getComputedStyle(el);
    if (style.display === "none" || style.visibility === "hidden" || style.opacity === "0") return false;
    const rect = el.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
  };
  const findActivateButtons = () => {
    const nodes = document.querySelectorAll("div.r-btn, .r-btn, div.innerbtn, div.detail, button, a, [role='button'], input[type='button'], input[type='submit']");
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
  const clickLoadMore = () => {
    for (const el of document.querySelectorAll("button, a, [role='button']")) {
      const label = visibleText(el).toLowerCase();
      if (!isVisible(el)) continue;
      if (label === "load more" || label === "show more" || label === "see more" || label === "view more" || label.includes("load more")) {
        el.scrollIntoView({ block: "center" });
        el.click();
        return true;
      }
    }
    return false;
  };

  for (let i = 0; i < 20; i++) {
    const before = document.body.scrollHeight;
    const clicked = clickLoadMore();
    window.scrollTo(0, document.body.scrollHeight);
    await sleep(450);
    if (!clicked && document.body.scrollHeight === before && i > 2) break;
  }
  window.scrollTo(0, 0);
  await sleep(300);

  const buttons = findActivateButtons();
  const labels = buttons.map(visibleText);
  if (DRY_RUN) {
    return { activated: 0, failed: 0, leftover: buttons.length, labels, dryRun: true, href: location.href };
  }

  let activated = 0;
  let failed = 0;
  for (const btn of buttons) {
    try {
      btn.scrollIntoView({ block: "center", behavior: "instant" });
      await sleep(80);
      btn.click();
      activated += 1;
    } catch (err) {
      failed += 1;
    }
    await sleep(DELAY_MS);
  }
  return {
    activated,
    failed,
    leftover: findActivateButtons().length,
    labels,
    href: location.href,
  };
}
`;

async function connect() {
  const browserURL = `http://127.0.0.1:${PORT}`;
  try {
    return await puppeteer.connect({ browserURL, defaultViewport: null });
  } catch (err) {
    console.error(`Cannot attach to Chrome DevTools at ${browserURL}`);
    console.error("Start Chrome with --remote-debugging-port=" + PORT + " and sign in first.");
    console.error(String(err.message || err));
    process.exit(1);
  }
}

async function looksLoggedOut(page) {
  const url = page.url();
  if (/sign-?in|login|auth/i.test(url)) return true;
  return page.evaluate(() => {
    const text = document.body ? document.body.innerText : "";
    const hasActivate = /activate/i.test(text);
    const hasSignIn = /sign in|log in|create my account/i.test(text);
    return hasSignIn && !hasActivate;
  });
}

async function runPage(browser, url) {
  const page = await browser.newPage();
  page.setDefaultTimeout(60000);
  console.log("\n→", url);
  try {
    await page.goto(url, { waitUntil: "networkidle2", timeout: 60000 });
  } catch (err) {
    console.warn("  navigation warning:", err.message);
  }
  await page.waitForSelector("body", { timeout: 15000 }).catch(() => {});
  await new Promise((r) => setTimeout(r, 2500));
  if (/cashback/i.test(url)) {
    await page.waitForSelector("#KacuIframe", { timeout: 15000 }).catch(() => {});
    await new Promise((r) => setTimeout(r, 3000));
  }

  if (await looksLoggedOut(page)) {
    console.warn("  Not signed in on this tab. Sign in in the attached Chrome, then rerun.");
    await page.close();
    return { url, skipped: true, reason: "not-signed-in" };
  }

  const frameResults = [];
  for (const frame of page.frames()) {
    const frameUrl = frame.url();
    try {
      await frame.evaluate(INJECTED_ACTIVATOR);
      const result = await frame.evaluate(
        async (delayMs, dryRun) => activateRperksCoupons({ delayMs, dryRun }),
        DELAY_MS,
        DRY_RUN
      );
      frameResults.push({ frameUrl, ...result });
      console.log(
        `  [${frameUrl.slice(0, 80)}] activated=${result.activated} leftover=${result.leftover}` +
          (result.dryRun ? " (dry-run)" : "")
      );
      if (result.labels && result.labels.length && (DRY_RUN || result.activated === 0)) {
        console.log("    buttons:", result.labels.slice(0, 20).join(" | ") || "(none)");
      }
    } catch (err) {
      console.warn("  skip frame", frameUrl, err.message);
    }
  }
  const result = frameResults.reduce(
    (acc, r) => ({
      activated: acc.activated + (r.activated || 0),
      leftover: acc.leftover + (r.leftover || 0),
      failed: acc.failed + (r.failed || 0),
      frames: frameResults,
    }),
    { activated: 0, leftover: 0, failed: 0 }
  );
  await page.close();
  return { url, ...result };
}

async function main() {
  console.log(`Connecting to Chrome DevTools on port ${PORT}` + (DRY_RUN ? " (dry-run)" : ""));
  const browser = await connect();
  const results = [];
  try {
    for (const url of PAGES) {
      results.push(await runPage(browser, url));
    }
  } finally {
    browser.disconnect();
  }

  const activated = results.reduce((n, r) => n + (r.activated || 0), 0);
  console.log("\nDone. Total Activate clicks:", activated);
  if (results.some((r) => r.reason === "not-signed-in")) {
    process.exitCode = 2;
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
