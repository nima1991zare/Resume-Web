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
  const c = JSON.parse(fs.readFileSync(file, "utf8"));
  if (!c.serverUrl || !c.agentKey) {
    console.error("\nconfig.json needs both serverUrl and agentKey " +
                  "(Admin → Project Finder → Autopilot shows the key).\n");
    process.exit(1);
  }
  c.serverUrl = c.serverUrl.replace(/\/+$/, "");
  c.dryRun = !!c.dryRun;
  return c;
})();

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

// ── WhatsApp ──────────────────────────────────────────────────────────────
const client = new Client({
  authStrategy: new LocalAuth({ dataPath: path.join(__dirname, ".session") }),
  puppeteer: {
    headless: CFG.headless !== false,
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
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

log("connecting to WhatsApp…");
log("server:", CFG.serverUrl, CFG.dryRun ? "(DRY RUN)" : "");
client.initialize();
loop();
