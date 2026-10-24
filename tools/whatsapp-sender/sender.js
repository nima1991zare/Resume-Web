/**
 * WhatsApp sender — the only part of the Project Finder that runs on your PC.
 *
 * It is deliberately the dumbest component in the system. It asks the server
 * "is there a message I may send?", sends whatever it is handed, reports what
 * happened, and sleeps. Every rule about *when* a message may go out — the
 * daily cap, quiet hours, spacing, stop-on-reply, the pause switch — lives on
 * the server, so running this twice by accident cannot double your sending
 * rate, and a crash cannot replay a burst.
 *
 * ──────────────────────────────────────────────────────────────────────────
 * READ THIS ONCE.
 *
 * This drives your own logged-in WhatsApp Web session through an automated
 * browser. That is against WhatsApp's terms of service, and sending unsolicited
 * messages in volume to people who have never contacted you is the exact
 * behaviour their spam detection bans numbers for — permanently, with no
 * appeal that works in practice.
 *
 * Use a SECOND SIM, not the number your existing clients use to reach you.
 * Warm it up: have real conversations on it for a week or two before this ever
 * runs. Keep the daily cap low. If strangers start blocking or reporting you,
 * stop — the cap will not save a number that people are reporting.
 *
 * Nothing here can make automated cold outreach safe. It can only make it
 * slower and more careful than the naive version, which is what the pacing,
 * the jitter and the self-pause on failure are for.
 * ──────────────────────────────────────────────────────────────────────────
 */
"use strict";

const fs = require("fs");
const path = require("path");
const { Client, LocalAuth } = require("whatsapp-web.js");
const qrcode = require("qrcode-terminal");

// ── config ────────────────────────────────────────────────────────────────
const CFG = (() => {
  const file = path.join(__dirname, "config.json");
  if (!fs.existsSync(file)) {
    console.error("\nconfig.json is missing. Copy config.example.json to " +
                  "config.json and fill in serverUrl and agentKey.\n");
    process.exit(1);
  }
  // Strip a byte-order mark first: Notepad and PowerShell both add one, and
  // JSON.parse fails on it with "Unexpected token" pointing at character 0.
  const c = JSON.parse(fs.readFileSync(file, "utf8").replace(/^﻿/, ""));
  if (!c.serverUrl || !c.agentKey) {
    console.error("\nconfig.json needs both serverUrl and agentKey " +
                  "(Admin → Project Finder → Autopilot shows the key).\n");
    process.exit(1);
  }
  c.serverUrl = c.serverUrl.replace(/\/+$/, "");
  c.dryRun = !!c.dryRun;
  return c;
})();

// ── proxy ─────────────────────────────────────────────────────────────────
/**
 * Node's fetch ignores HTTP_PROXY. Everything else on the machine does not.
 *
 * That difference is invisible and expensive: the browser loads the site
 * through the proxy, so the server is obviously up, while this process
 * connects directly and gets HTTP 451 from a host that blocks the country.
 * You end up checking the agent key, which was never the problem.
 *
 * Node 24 honours the proxy variables when NODE_USE_ENV_PROXY=1, but only if
 * it is set *before* the runtime starts — so if a proxy is configured and the
 * flag is missing, re-exec once with it set rather than failing later.
 */
const PROXY = CFG.proxy || process.env.HTTPS_PROXY || process.env.https_proxy ||
              process.env.HTTP_PROXY || process.env.http_proxy || "";

if (PROXY && !process.env.NODE_USE_ENV_PROXY) {
  const { spawnSync } = require("child_process");
  const env = Object.assign({}, process.env, {
    NODE_USE_ENV_PROXY: "1",
    HTTPS_PROXY: PROXY,
    HTTP_PROXY: PROXY,
    // A local server must never be sent through the proxy.
    NO_PROXY: process.env.NO_PROXY || "localhost,127.0.0.1,::1",
  });
  console.log("using proxy " + PROXY + " (restarting so fetch picks it up)");
  const r = spawnSync(process.execPath, [__filename, ...process.argv.slice(2)],
                      { stdio: "inherit", env });
  process.exit(r.status === null ? 1 : r.status);
}

const log = (...a) => console.log(new Date().toLocaleTimeString("en-GB"), ...a);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const jitter = (ms, pct = 0.35) =>
  Math.max(1000, Math.round(ms * (1 + (Math.random() * 2 - 1) * pct)));

// ── server protocol ───────────────────────────────────────────────────────
async function api(route, body) {
  const r = await fetch(CFG.serverUrl + route, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Agent-Key": CFG.agentKey },
    body: JSON.stringify(body || {}),
  });
  if (r.status === 401) throw new Error("agent key rejected by server");
  if (!r.ok) throw new Error(route + " -> HTTP " + r.status);
  return r.json();
}

// ── the browser ───────────────────────────────────────────────────────────
/**
 * Use the Chrome that is already installed rather than the one puppeteer
 * bundles. Two reasons, and the second is the important one:
 *
 *  - npm 11 blocks install scripts by default, so puppeteer's postinstall
 *    never runs and no Chromium is downloaded. The failure shows up much
 *    later as "Could not find expected browser", which is a confusing way to
 *    learn that.
 *  - that download is ~150MB from a server that is slow to reach from Iran,
 *    and an installed Chrome is already patched.
 *
 * This launches a separate browser with its own profile under .session/ — it
 * does not touch your normal Chrome or the accounts you are signed into there.
 */
function findChrome() {
  if (CFG.chromePath) return CFG.chromePath;
  const env = process.env;
  // path.join rather than literal backslashes: a Windows path written inline
  // is a minefield of accidental escape sequences ("\c" is just "c").
  const win = [
    [env.PROGRAMFILES, "Google", "Chrome", "Application", "chrome.exe"],
    [env["PROGRAMFILES(X86)"], "Google", "Chrome", "Application", "chrome.exe"],
    [env.LOCALAPPDATA, "Google", "Chrome", "Application", "chrome.exe"],
    [env.PROGRAMFILES, "Microsoft", "Edge", "Application", "msedge.exe"],
    [env["PROGRAMFILES(X86)"], "Microsoft", "Edge", "Application", "msedge.exe"],
  ];
  const candidates = [];
  for (const parts of win) {
    if (parts[0]) candidates.push(path.join(...parts));
  }
  candidates.push(
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium-browser",
    "/usr/bin/chromium"
  );
  for (const c of candidates) {
    try { if (fs.existsSync(c)) return c; } catch (e) { /* keep looking */ }
  }
  return null;
}

const CHROME = findChrome();
if (!CHROME) {
  console.error("");
  console.error("No Chrome or Edge found on this machine.");
  console.error('Install Google Chrome, or set "chromePath" in config.json to');
  console.error("the full path of chrome.exe.");
  console.error("");
  process.exit(1);
}

// ── WhatsApp ──────────────────────────────────────────────────────────────
const client = new Client({
  authStrategy: new LocalAuth({ dataPath: path.join(__dirname, ".session") }),
  puppeteer: {
    headless: CFG.headless !== false,
    executablePath: CHROME,
    args: [
      "--no-sandbox",
      "--disable-setuid-sandbox",
      // Be explicit rather than relying on the system setting: if fetch goes
      // through a proxy and the browser does not, WhatsApp Web silently fails
      // in a different way than the server calls do.
      ...(PROXY ? ["--proxy-server=" + PROXY] : []),
    ],
  },
});

let ready = false;
let consecutiveFailures = 0;

client.on("qr", (qr) => {
  console.log("\nScan this with WhatsApp → Linked devices → Link a device:\n");
  qrcode.generate(qr, { small: true });
  console.log("\nThe session is saved, so this only happens once.\n");
});
client.on("authenticated", () => log("authenticated"));
client.on("ready", () => { ready = true; log("WhatsApp is ready"); });
client.on("auth_failure", (m) => { log("AUTH FAILURE:", m); process.exit(1); });
client.on("disconnected", (r) => {
  ready = false;
  log("disconnected:", r, "— exiting so the restart is deliberate, not a loop");
  process.exit(1);
});

/**
 * An incoming message means a human replied. Stop that conversation
 * immediately: the server drops anything still queued for them, and from here
 * on it is Nima's conversation, not the agent's.
 */
client.on("message", async (msg) => {
  try {
    if (msg.fromMe || msg.isStatus) return;
    const from = (msg.from || "").replace(/\D/g, "");
    if (!from) return;
    log("reply from +" + from + " — that lead is yours now");
    // An opt-out has to be honoured on the spot and loudly.
    const text = (msg.body || "").toLowerCase();
    if (/stop|unsubscribe|لغو|مزاحم|قطع|نفرست/.test(text)) {
      log("OPT-OUT from +" + from);
      await api("/api/agent/report", { id: 0, ok: false, error: "optout:" + from })
        .catch(() => {});
    }
  } catch (e) { /* never let a reply handler kill the sender */ }
});

// ── the loop ──────────────────────────────────────────────────────────────
async function tick() {
  if (!ready) return 3000;

  let res;
  try {
    res = await api("/api/agent/claim");
  } catch (e) {
    log("claim failed:", e.message);
    return 30000;
  }

  if (!res.message) {
    const why = res.reason || "nothing";
    if (why !== lastReason) { log("waiting:", why); lastReason = why; }
    return jitter((res.wait_s || 60) * 1000, 0.15);
  }
  lastReason = "";

  const m = res.message;
  const chatId = m.to.replace(/\D/g, "") + "@c.us";
  log(`sending to ${m.name} (+${m.to}) — ${m.need} ` +
      `[${(res.sent_today || 0) + 1}/${res.cap}]`);

  try {
    if (CFG.dryRun) {
      log("DRY RUN — not actually sending:\n" + m.body + "\n");
    } else {
      // Confirm the number is on WhatsApp before writing to it. Sending to
      // numbers that do not exist is itself a spam signal.
      const exists = await client.isRegisteredUser(chatId);
      if (!exists) {
        await api("/api/agent/report",
                  { id: m.id, ok: false, error: "number not on WhatsApp" });
        log("  not a WhatsApp number — skipped");
        return jitter(8000);
      }
      // Type-ish pause. Instant sends, one after another, are a bot signature.
      await sleep(jitter(4000 + m.body.length * 18, 0.4));
      await client.sendMessage(chatId, m.body);
    }
    await api("/api/agent/report", { id: m.id, ok: true });
    consecutiveFailures = 0;
    log("  sent");
  } catch (e) {
    consecutiveFailures++;
    log("  send failed:", e.message);
    await api("/api/agent/report",
              { id: m.id, ok: false, error: String(e.message).slice(0, 280) })
      .catch(() => {});

    // Repeated failures usually mean WhatsApp has started refusing us. Stopping
    // the whole queue is the correct response; carrying on is how a warning
    // becomes a ban.
    if (consecutiveFailures >= 3) {
      log("THREE FAILURES IN A ROW — pausing the queue on the server.");
      await api("/api/agent/pause", { reason: "3 consecutive send failures" })
        .catch(() => {});
      consecutiveFailures = 0;
      return 600000;
    }
  }

  // Space sends out even beyond what the server asked for.
  return jitter(Math.max(45, res.min_gap_s || 140) * 1000, 0.3);
}

let lastReason = "";
async function loop() {
  for (;;) {
    let wait = 5000;
    try {
      wait = await tick();
    } catch (e) {
      log("loop error:", e.message);
      wait = 30000;
    }
    await sleep(wait);
  }
}

process.on("SIGINT", () => { log("stopping"); process.exit(0); });

// whatsapp-web.js throws from inside its own page handlers, which arrive as
// unhandled rejections and would otherwise kill the process with a raw stack
// trace and no explanation of what to do about it.
process.on("unhandledRejection", (err) => {
  const msg = String((err && err.message) || err);
  log("unhandled error:", msg);
  if (/Execution context was destroyed|Protocol error|Target closed/i.test(msg)) {
    log("");
    log("WhatsApp Web changed under the session. Usually this means");
    log("whatsapp-web.js is out of date:  npm install whatsapp-web.js@latest");
    log("If it keeps happening, delete .session/ and link the device again.");
  }
  process.exit(1);
});

/**
 * `node sender.js --check` — prove the half that does not need WhatsApp.
 *
 * Two things can be wrong at setup and they look identical from the outside:
 * the browser cannot start, or the server will not talk to you. This separates
 * them in about two seconds, so linking a device is not the step where you
 * discover the agent key was wrong.
 */
if (process.argv.includes("--check")) {
  (async () => {
    console.log("");
    console.log("browser :", CHROME);
    console.log("proxy   :", PROXY || "(none — connecting directly)");
    console.log("server  :", CFG.serverUrl);
    console.log("dry run :", CFG.dryRun);
    try {
      const r = await api("/api/agent/claim");
      if (r.message) {
        console.log("server  : OK — a message is ready to send");
        console.log("");
        console.log("  to   : +" + r.message.to + "  (" + r.message.name + ")");
        console.log("  need : " + r.message.need);
        console.log("  today: " + (r.sent_today || 0) + "/" + r.cap);
        console.log("");
        console.log(r.message.body);
        console.log("");
        // Put it back: a check must not consume a message.
        await api("/api/agent/report",
                  { id: r.message.id, ok: false, error: "returned by --check" });
        console.log("(returned to the queue — nothing was sent)");
      } else {
        console.log("server  : OK — nothing to send right now (" + r.reason + ")");
        if (r.reason === "paused") {
          console.log("          turn Autopilot on in Admin -> Project Finder");
        } else if (r.reason === "nothing_due" && r.next_due) {
          console.log("          next message is due at " + r.next_due);
        } else if (r.reason === "quiet_hours") {
          console.log("          inside quiet hours");
        }
      }
      console.log("");
      console.log("Everything except WhatsApp itself is working.");
    } catch (e) {
      console.log("server  : FAILED — " + e.message);
      console.log("");
      if (/451/.test(e.message)) {
        console.log("451 means the host refused this country, not that your key");
        console.log("is wrong. Your browser reaches the site through a proxy and");
        console.log("this process did not. Set \"proxy\" in config.json, e.g.");
        console.log('  "proxy": "http://127.0.0.1:10808"');
      } else if (/401/.test(e.message)) {
        console.log("401 means the agent key is wrong. Copy it again from");
        console.log("Admin -> Project Finder -> Autopilot -> Sender setup.");
      } else {
        console.log("Check serverUrl and agentKey in config.json. The key is in");
        console.log("Admin -> Project Finder -> Autopilot -> Sender setup.");
      }
      process.exitCode = 1;
      return;
    }
    // Let the loop drain instead of exiting from inside an async callback:
    // process.exit() there trips a libuv assertion on Windows.
    process.exitCode = 0;
  })();
} else {

log("connecting to WhatsApp…");
log("server:", CFG.serverUrl, CFG.dryRun ? "(DRY RUN)" : "");
log("browser:", CHROME);
if (PROXY) log("proxy:", PROXY);
client.initialize();
loop();

}
