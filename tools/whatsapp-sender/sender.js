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
  // The example file's value is a sentence, not a key. Catching it here turns
  // "401 agent key rejected" twenty seconds later into the one instruction
  // that actually fixes it.
  if (/paste|your[-_ ]?key|admin\s*->|autopilot/i.test(c.agentKey) ||
      c.agentKey.length < 30) {
    console.error("\nagentKey is still the placeholder from the example file.");
    console.error("Copy the real key from:");
    console.error("  Admin → Project Finder → Autopilot → Sender setup");
    console.error('Paste it into "agentKey" in config.json (no spaces).\n');
    process.exit(1);
  }
  c.serverUrl = c.serverUrl.replace(/\/+$/, "");
  c.dryRun = !!c.dryRun;
  // `npm start -- --send` is the one-off override, so trying a real send does
  // not mean editing this file and remembering to put the safety back.
  if (process.argv.includes("--send")) c.dryRun = false;
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
// A local server must never be sent through the proxy, and the proxy variables
// are often set machine-wide for other reasons — reaching 127.0.0.1 through a
// remote tunnel is a confusing way to get "connection refused".
const LOCAL_SERVER = /^https?:\/\/(localhost|127\.0\.0\.1|\[::1\])(:\d+)?(\/|$)/i
  .test(CFG.serverUrl);
const PROXY = CFG.proxy ||
              (!LOCAL_SERVER &&
               (process.env.HTTPS_PROXY || process.env.https_proxy ||
                process.env.HTTP_PROXY || process.env.http_proxy)) || "";

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

// ── reports that did not get through ──────────────────────────────────────
/**
 * A message that was really sent but whose report never reached the server is
 * the worst state this program can be in: the server still thinks it is
 * claimed, the claim expires after ten minutes, and the next poll sends the
 * same text to the same business a second time.
 *
 * So a failed report is written to disk and retried before anything new is
 * claimed — across restarts, too. Losing one HTTP call must never cost a
 * duplicate message to a stranger.
 */
const PENDING = path.join(__dirname, "pending-reports.json");

function readPending() {
  try {
    const list = JSON.parse(fs.readFileSync(PENDING, "utf8"));
    return Array.isArray(list) ? list : [];
  } catch (e) {
    return [];
  }
}

function writePending(list) {
  try {
    fs.writeFileSync(PENDING, JSON.stringify(list, null, 2));
  } catch (e) {
    log("could not save pending-reports.json:", e.message);
  }
}

async function flushPending() {
  const list = readPending();
  if (!list.length) return 0;
  const left = [];
  for (const e of list) {
    try {
      await api("/api/agent/report", e);
      log("  reported the earlier send to " + (e.name || "lead"));
    } catch (err) {
      // 404 means the server does not know this message any more (someone
      // dropped or requeued it in the panel) — retrying forever is pointless.
      if (/HTTP 404/.test(err.message)) continue;
      left.push(e);
    }
  }
  writePending(left);
  return left.length;
}

/** Record what happened, or keep trying until the server has certainly heard. */
async function report(entry, label) {
  try {
    await api("/api/agent/report", entry);
  } catch (e) {
    const list = readPending();
    list.push(entry);
    writePending(list);
    log("  " + label + " sent, but the report failed (" + e.message +
        ") — will report before the next send");
  }
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
let readyAt = 0;              // when the page last said it was ready
let readyRepeats = 0;
let consecutiveFailures = 0;  // real send failures
let transientFailures = 0;    // page vanished under a send

// whatsapp-web.js reloads the tab once after pairing, and WhatsApp itself
// reloads it after a long sleep. A send that is in flight when that happens
// dies with "Execution context was destroyed" even though nothing is wrong
// with the account. Claiming a message and then waiting for the new page to
// settle is the difference between one failed attempt per reload and a queue
// that actually moves.
const SETTLE_MS = 8000;

client.on("qr", (qr) => {
  console.log("\nScan this with WhatsApp → Linked devices → Link a device:\n");
  qrcode.generate(qr, { small: true });
  console.log("\nThe session is saved, so this only happens once.\n");
});
client.on("authenticated", () => log("authenticated"));
client.on("ready", () => {
  ready = true;
  readyAt = Date.now();
  if (readyRepeats++ === 0) {
    log("WhatsApp is ready");
    return;
  }
  log("WhatsApp is ready again (" + readyRepeats + ") — waiting for the page to settle");
  if (readyRepeats === 4) {
    log("");
    log("The WhatsApp tab keeps reloading. Nothing can be sent while it does.");
    log("If this does not stop: close this window, delete the .session folder");
    log("in this directory, and run npm run send to link the phone again.");
    log("");
  }
});
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
    const from = String(msg.from || "");
    if (msg.fromMe || msg.isStatus) return;
    // Only a one-to-one chat with a real phone number is a lead writing back.
    // These are not people, and treating them as people is expensive: the
    // @newsletter (channel) and @lid ids are long numbers whose last ten
    // digits can collide with a real lead, so one broadcast post would stop
    // that lead's message and mark them "replied" for no reason.
    if (!/@c\.us$/i.test(from)) {
      if (/@(g\.us|broadcast|newsletter|lid)$/i.test(from)) {
        log("ignoring a message from " + from.split("@")[1] + " (not a one-to-one chat)");
      }
      return;
    }
    const fromDigits = from.replace(/@.*$/, "").replace(/\D/g, "");
    if (!/^\d{8,15}$/.test(fromDigits)) return;
    // An opt-out has to be honoured on the spot and loudly.
    const text = (msg.body || "").toLowerCase();
    const optout = /stop|unsubscribe|لغو|مزاحم|قطع|نفرست/.test(text);
    log("reply from +" + fromDigits + (optout ? " — OPT-OUT" : "") +
        " — that lead is yours now");
    // Tell the server, so anything still queued for them is dropped. This is
    // the only way the queue can know a human answered.
    await api("/api/agent/replied", { phone: fromDigits, optout }).catch((e) =>
      log("  could not record the reply:", e.message));
  } catch (e) { /* never let a reply handler kill the sender */ }
});

/** A page-level failure, not a WhatsApp-level refusal. Retrying is right;
 * reporting it as a failed attempt would burn one of three tries per reload. */
function isTransient(e) {
  return /Execution context was destroyed|Protocol error|Target closed|Session closed|detached Frame|Cannot find context/i
    .test(String((e && e.message) || e));
}

/** Wait until the page says "ready" again (plus its settle time), or until
 * `maxMs` — whichever comes first. Returns null on timeout. */
function recoveryWait(maxMs) {
  return new Promise((resolve) => {
    let finished = false;
    const finish = (ms) => {
      if (finished) return;
      finished = true;
      clearTimeout(timer);
      client.removeListener("ready", onReady);
      resolve(ms);
    };
    const onReady = () => finish(jitter(SETTLE_MS + 4000, 0.15));
    const timer = setTimeout(() => finish(null), maxMs);
    client.on("ready", onReady);
  });
}

// ── the loop ──────────────────────────────────────────────────────────────
/**
 * Dry run: read the queue, print it, touch nothing.
 *
 * It deliberately does not claim. Claiming and reporting "sent" used to mark
 * every message as delivered — consuming the daily cap and the one-message-
 * per-lead guarantee while nothing had actually been sent. A dry run must be
 * free to repeat.
 */
const drySeen = new Set();

async function dryTick() {
  let printed = 0;
  let reason = "";
  let nextDue = null;
  for (let i = 0; i < 25; i++) {
    let res;
    try {
      res = await api("/api/agent/claim?channel=whatsapp&peek=1&offset=" + i);
    } catch (e) {
      log("claim failed:", e.message);
      return 30000;
    }
    if (!res.message) {
      if (i === 0) { reason = res.reason || "nothing"; nextDue = res.next_due; }
      break;
    }
    const m = res.message;
    // Re-worded messages must be re-printed: the whole point of the dry run is
    // reading the text that would actually go out.
    const key = m.id + "|" + m.body;
    if (drySeen.has(key)) continue;
    drySeen.add(key);
    printed++;
    log(`DRY RUN — would send to ${m.name} (+${m.to}) — ${m.need} ` +
        `[${(res.sent_today || 0) + printed}/${res.cap}]`);
    log(m.body + "\n");
  }
  if (printed === 0) {
    const why = reason ? explain({ reason, next_due: nextDue }) : "nothing new";
    if (why !== lastReason) { log("waiting:", why); lastReason = why; }
  } else {
    lastReason = "";
  }
  return printed ? 60000 : 120000;
}

/** Is this number on WhatsApp? Unknown answers are given the benefit of the
 * doubt — refusing to try would silently drop a real business. */
async function isOnWhatsApp(digits) {
  try {
    if (typeof client.getNumberId === "function") {
      const id = await client.getNumberId(digits);
      return !!id;
    }
  } catch (e) { /* fall through to the older call */ }
  try {
    return await client.isRegisteredUser(digits + "@c.us");
  } catch (e) {
    return true;
  }
}

/** An old server would still claim on `peek=1` — and then report a dry run as
 * a real send. Refuse to talk to one rather than eat the queue silently. */
let protocolOk = false;
async function ensureProtocol() {
  if (protocolOk) return;
  const r = await api("/api/agent/claim?channel=whatsapp&peek=1").catch((e) => ({ error: e }));
  if (r.error) throw r.error;
  if (r.peek !== true) {
    console.error("");
    console.error("The server does not understand peek=1 — it is running an older");
    console.error("build, which would treat this check as a real claim.");
    console.error("Deploy the current version of the site, then start this again.");
    console.error("");
    process.exit(1);
  }
  protocolOk = true;
}

/** Turn the server's machine reasons into a sentence that says what to do. */
function explain(res) {
  switch (res.reason) {
    case "paused":
      return "Autopilot is off — turn it on in Admin → Project Finder → Autopilot.";
    case "channel_disabled":
      return "WhatsApp is switched off in the channel list — tick it in the panel.";
    case "daily_cap":
      return "Daily cap reached (" + (res.sent_today || 0) + "/" + (res.cap || 0) +
             ") — resumes after midnight, local time.";
    case "quiet_hours":
      return "Quiet hours — nothing goes out until " + (res.quiet_end || "morning") +
             " local time.";
    case "nothing_due":
      return res.next_due ? "nothing due until " + res.next_due + " UTC" : "queue is empty";
    default:
      return res.reason || "nothing to send";
  }
}

/** Put a claimed message back in the queue without burning one of its three
 * attempts — for the case where our side broke, not the send. */
async function release(id) {
  try {
    await api("/api/agent/release", { id });
    return true;
  } catch (e) {
    log("  could not release the message:", e.message);
    return false;
  }
}

/** Did that exact text already go out? Both wrong answers are expensive: a
 * false "sent" loses the lead for good, a false "not sent" sends the same
 * stranger a second copy. `null` means the page was gone and we cannot tell. */
async function delivered(chatId, body) {
  try {
    const chat = await client.getChatById(chatId);
    const msgs = await chat.fetchMessages({ limit: 10 });
    const want = String(body || "").trim();
    return msgs.some((x) => x.fromMe && String(x.body || "").trim() === want);
  } catch (e) {
    return null;
  }
}

/** Ask the dead page a question at our own pace: the call itself may hang. */
function withTimeout(promise, ms) {
  return Promise.race([promise, sleep(ms).then(() => null)]);
}

async function tick() {
  await ensureProtocol();
  if (CFG.dryRun) return dryTick();
  if (!ready) return 3000;
  // A page that has only just said "ready" is still finishing its own setup.
  // Sending into it is how the first message of a session dies.
  if (Date.now() - readyAt < SETTLE_MS) return 2000;

  // Anything we sent but could not report must be settled first, or the server
  // will hand the same message out again once the claim expires.
  const unsent = await flushPending();
  if (unsent) {
    log("waiting for the server to accept " + unsent + " earlier report(s) — not claiming more");
    return 30000;
  }

  let res;
  try {
    res = await api("/api/agent/claim?channel=whatsapp");
  } catch (e) {
    log("claim failed:", e.message);
    return 30000;
  }

  if (!res.message) {
    const why = explain(res);
    if (why !== lastReason) { log("waiting:", why); lastReason = why; }
    return jitter((res.wait_s || 60) * 1000, 0.15);
  }
  lastReason = "";

  const m = res.message;
  const digits = m.to.replace(/\D/g, "");
  const chatId = digits + "@c.us";
  log(`sending to ${m.name} (+${m.to}) — ${m.need} ` +
      `[${(res.sent_today || 0) + 1}/${res.cap}]`);

  try {
    // Confirm the number is on WhatsApp before writing to it. Sending to
    // numbers that do not exist is itself a spam signal.
    if (!(await isOnWhatsApp(digits))) {
      await report({ id: m.id, ok: false, error: "not on WhatsApp", name: m.name },
                   "not a WhatsApp number —");
      log("  not a WhatsApp number — skipped");
      return jitter(8000);
    }
    // Type-ish pause. Instant sends, one after another, are a bot signature.
    await sleep(jitter(4000 + m.body.length * 18, 0.4));
    await client.sendMessage(chatId, m.body);
    await report({ id: m.id, ok: true, name: m.name }, "message");
    consecutiveFailures = 0;
    log("  sent");
  } catch (e) {
    if (isTransient(e)) {
      // The page reloaded (WhatsApp does this after pairing and after a long
      // sleep). That is not WhatsApp refusing the message, so it must not burn
      // one of the lead's three attempts — and the message may in fact have
      // been written before the page vanished.
      transientFailures++;
      const state = await withTimeout(delivered(chatId, m.body), 6000);
      if (state === true) {
        log("  the page reloaded just after sending — confirmed in the chat");
        await report({ id: m.id, ok: true, name: m.name }, "message");
        consecutiveFailures = 0;
        transientFailures = 0;
        return jitter(SETTLE_MS + 5000);
      }
      log("  the WhatsApp page reloaded mid-send — message released, will retry");
      const putBack = await release(m.id);
      if (!putBack) {
        // Without a release the claim sits until it expires; reporting a
        // failure would at least make that visible in the panel.
        await report({ id: m.id, ok: false, error: "page reloaded mid-send" }, "message");
      }
      if (transientFailures >= 3) {
        log("");
        log("The WhatsApp page has gone away three times in a row. Nothing was");
        log("reported as failed — the messages are still queued and no attempt");
        log("was used up. Pausing for ten minutes.");
        log("If this keeps happening, stop this window, delete the .session");
        log("folder in this directory, and run npm run send to link again.");
        log("");
        transientFailures = 0;
        return 600000;
      }
      // Give the new page time to say ready; if it does, come back sooner
      // rather than sitting out the full wait.
      const wait = jitter(75000, 0.2);
      return (await recoveryWait(wait)) || wait;
    }

    consecutiveFailures++;
    log("  send failed:", e.message);
    await report({ id: m.id, ok: false, error: String(e.message).slice(0, 280) },
                 "message");

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
  if (isTransient(err)) {
    // The page reloaded under us. whatsapp-web.js throws from its own handlers
    // and there is nothing to fix — the loop releases whatever was in flight
    // and retries. Killing the process here is how one reload became a night
    // of nothing being sent.
    readyAt = Date.now();   // let the page settle before claiming anything new
    log("WhatsApp reloaded its page. Carrying on — if this repeats, delete");
    log(".session/ and link the phone again.");
    return;
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
      await ensureProtocol();
      const r = await api("/api/agent/claim?channel=whatsapp&peek=1");
      if (r.message) {
        console.log("server  : OK — a message is ready to send");
        console.log("");
        console.log("  to   : +" + r.message.to + "  (" + r.message.name + ")");
        console.log("  need : " + r.message.need);
        console.log("  today: " + (r.sent_today || 0) + "/" + r.cap);
        console.log("");
        console.log(r.message.body);
        console.log("");
        console.log("(peeked — nothing was claimed or sent)");
      } else {
        console.log("server  : OK — nothing to send right now");
        console.log("          " + explain(r));
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
if (CFG.dryRun) {
  log("");
  log("DRY RUN — messages are printed to this window and NOT sent.");
  log('When the text reads right, set "dryRun": false in config.json');
  log("and restart. Nothing in the queue is consumed while dryRun is true.");
  log("");
}
client.initialize();
loop();

}
