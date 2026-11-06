/**
 * Render slides.html to one PNG per slide, named by its tag (p1-01, p2-03…).
 *
 * Reuses the Puppeteer that the WhatsApp sender already pulled in and the
 * Chrome that is already installed, so there is nothing new to download. Each
 * slide is a pure function of window.setSlide(n): set it, screenshot it, next.
 *
 *   node render.js            → out/ (all slides as PNG, grouped by post)
 */
"use strict";
const fs = require("fs");
const path = require("path");

const HERE = __dirname;
const OUT = path.join(HERE, "out");
const W = 1080, H = 1350;

function findChrome() {
  const e = process.env;
  const c = [
    e.PROGRAMFILES && path.join(e.PROGRAMFILES, "Google/Chrome/Application/chrome.exe"),
    e["PROGRAMFILES(X86)"] && path.join(e["PROGRAMFILES(X86)"], "Google/Chrome/Application/chrome.exe"),
    e.LOCALAPPDATA && path.join(e.LOCALAPPDATA, "Google/Chrome/Application/chrome.exe"),
    e.PROGRAMFILES && path.join(e.PROGRAMFILES, "Microsoft/Edge/Application/msedge.exe"),
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome", "/usr/bin/chromium",
  ].filter(Boolean);
  for (const p of c) { try { if (fs.existsSync(p)) return p; } catch (e) {} }
  return null;
}

(async () => {
  const html = path.join(HERE, "slides.html");
  if (!fs.existsSync(html)) { console.error("run:  python build.py"); process.exit(1); }
  const chrome = findChrome();
  if (!chrome) { console.error("No Chrome found."); process.exit(1); }

  // puppeteer was installed next to the WhatsApp sender; fall back to the
  // normal resolver (NODE_PATH, a local install) if that copy is not there.
  let puppeteer;
  for (const where of [
    path.join(HERE, "..", "whatsapp-sender", "node_modules", "puppeteer"),
    path.join(HERE, "node_modules", "puppeteer"),
    "puppeteer",
  ]) {
    try { puppeteer = require(where); break; } catch (e) { /* try next */ }
  }
  if (!puppeteer) {
    console.error("puppeteer not found. Run this once in tools/whatsapp-sender:  npm install");
    process.exit(1);
  }
  fs.rmSync(OUT, { recursive: true, force: true });
  fs.mkdirSync(OUT, { recursive: true });

  const browser = await puppeteer.launch({
    executablePath: chrome, headless: "new",
    args: ["--no-sandbox", "--disable-setuid-sandbox", "--force-device-scale-factor=1"],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: W, height: H, deviceScaleFactor: 1 });
  await page.goto("file://" + html.replace(/\\/g, "/"), { waitUntil: "load" });
  await page.evaluateHandle("document.fonts.ready");
  await page.waitForFunction("window.__ready === true", { timeout: 15000 });

  const n = await page.evaluate("window.SLIDE_COUNT");
  for (let i = 0; i < n; i++) {
    const tag = await page.evaluate((k) => { window.setSlide(k); return SLIDES[k].tag; }, i);
    await new Promise((r) => setTimeout(r, 120));      // let layout settle
    await page.screenshot({ path: path.join(OUT, tag + ".png") });
    process.stdout.write(tag + " ");
  }
  console.log("\n" + n + " slides → " + OUT);
  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
