/**
 * Renders reel.html to an MP4, one frame at a time.
 *
 * Deliberately not Remotion: Puppeteer is already installed for the WhatsApp
 * sender and ffmpeg is already on this machine, so the whole pipeline costs
 * nothing extra. The page exposes window.setFrame(n) and every visual is a
 * pure function of n, which is what makes stepping frames produce a smooth
 * video instead of whatever the wall clock happened to be doing.
 *
 *   node render.js            → out/reel.mp4
 *   node render.js --preview  → out/preview/ contact sheet only, no video
 */
"use strict";

const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");

const HERE = __dirname;
const OUT = path.join(HERE, "out");
const FRAMES = path.join(OUT, "frames");
const FPS = 30;
const SECONDS = 20;
const TOTAL = FPS * SECONDS;
const W = 1080, H = 1920;

// Reuse the browser the WhatsApp sender already pulled in.
const puppeteer = require(path.join(HERE, "..", "whatsapp-sender",
                                    "node_modules", "puppeteer"));

function findChrome() {
  const env = process.env;
  const parts = [
    [env.PROGRAMFILES, "Google", "Chrome", "Application", "chrome.exe"],
    [env["PROGRAMFILES(X86)"], "Google", "Chrome", "Application", "chrome.exe"],
    [env.LOCALAPPDATA, "Google", "Chrome", "Application", "chrome.exe"],
    [env.PROGRAMFILES, "Microsoft", "Edge", "Application", "msedge.exe"],
  ];
  for (const p of parts) {
    if (!p[0]) continue;
    const f = path.join(...p);
    if (fs.existsSync(f)) return f;
  }
  for (const f of ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                   "/usr/bin/google-chrome", "/usr/bin/chromium"]) {
    if (fs.existsSync(f)) return f;
  }
  return null;
}

(async () => {
  const previewOnly = process.argv.includes("--preview");
  const html = path.join(HERE, "reel.html");
  if (!fs.existsSync(html)) {
    console.error("reel.html is missing — run:  python build.py");
    process.exit(1);
  }
  const chrome = findChrome();
  if (!chrome) { console.error("No Chrome found."); process.exit(1); }

  fs.rmSync(FRAMES, { recursive: true, force: true });
  fs.mkdirSync(FRAMES, { recursive: true });

  const browser = await puppeteer.launch({
    executablePath: chrome,
    headless: "new",
    args: ["--no-sandbox", "--disable-setuid-sandbox",
           "--force-device-scale-factor=1", "--hide-scrollbars"],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: W, height: H, deviceScaleFactor: 1 });
  await page.goto("file://" + html.replace(/\\/g, "/"), { waitUntil: "load" });
  // The embedded font must be parsed before the first frame, or the opening
  // seconds render in a fallback face and the whole piece looks cheap.
  await page.evaluateHandle("document.fonts.ready");
  await page.waitForFunction("window.__ready === true", { timeout: 15000 });

  if (previewOnly) {
    const dir = path.join(OUT, "preview");
    fs.rmSync(dir, { recursive: true, force: true });
    fs.mkdirSync(dir, { recursive: true });
    const marks = [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 19.5];
    for (const s of marks) {
      await page.evaluate((f) => window.setFrame(f), Math.round(s * FPS));
      await page.screenshot({
        path: path.join(dir, `t${String(s).padStart(4, "0")}.png`) });
    }
    console.log(`preview frames → ${dir}`);
    await browser.close();
    return;
  }

  process.stdout.write(`rendering ${TOTAL} frames `);
  for (let f = 0; f < TOTAL; f++) {
    await page.evaluate((n) => window.setFrame(n), f);
    await page.screenshot({
      path: path.join(FRAMES, String(f).padStart(5, "0") + ".png"),
      optimizeForSpeed: true,
    });
    if (f % 60 === 0) process.stdout.write(".");
  }
  console.log(" done");
  await browser.close();

  const mp4 = path.join(OUT, "reel.mp4");
  // yuv420p + even dimensions, or Instagram re-encodes it badly (or rejects it).
  execFileSync("ffmpeg", [
    "-y", "-framerate", String(FPS),
    "-i", path.join(FRAMES, "%05d.png"),
    "-c:v", "libx264", "-preset", "slow", "-crf", "18",
    "-pix_fmt", "yuv420p", "-movflags", "+faststart",
    "-vf", "scale=1080:1920:flags=lanczos",
    mp4,
  ], { stdio: "inherit" });

  const mb = (fs.statSync(mp4).size / 1048576).toFixed(1);
  console.log(`\n${mp4}  (${mb} MB, ${SECONDS}s, ${W}x${H})`);
  console.log("frames kept in out/frames — delete when you are happy with it");
})().catch((e) => { console.error(e); process.exit(1); });
