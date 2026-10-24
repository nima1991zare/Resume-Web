"""Instagram sender — the Instagram half of the Project Finder's outbox.

Same shape as the WhatsApp sender: ask the server for the next message it may
send on the `instagram` channel, send it, report what happened, sleep. Every
rule about *when* lives on the server, so this process holds no state and
cannot outrun its own limits.

──────────────────────────────────────────────────────────────────────────────
READ THIS. INSTAGRAM IS NOT WHATSAPP.

This drives Instagram's private mobile API with your own account. Instagram
polices automation far more aggressively than WhatsApp does, and the failure
mode is different:

  * It **action-blocks before it bans.** You will usually get "Please wait a
    few minutes" long before anything permanent. That warning is the signal to
    stop for the day, not to retry — this script treats it that way.
  * DMs to people who do not follow you land in **Message Requests**, a folder
    many business owners never open. Expect a much lower reply rate than
    WhatsApp, and do not raise the cap to compensate. That is the move that
    gets the account restricted.
  * A new or lightly-used account doing this is the clearest possible signal.
    Use an account with real history and real posts.

Defaults here are deliberately small: 12 a day, seven minutes apart. That is
not timidity, it is the difference between an account that works next month
and one that does not.
──────────────────────────────────────────────────────────────────────────────

Install:  pip install instagrapi
Run:      python sender.py --check     (proves the server half, sends nothing)
          python sender.py
"""
from __future__ import annotations

import json
import os
import pathlib
import random
import sys
import time
import urllib.error
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
SESSION = HERE / "session.json"
CHANNEL = "instagram"

# Instagram's own words when it wants you to stop. Treated as a hard stop for
# the day rather than an error to retry, because retrying is what escalates a
# temporary block into a permanent one.
BLOCK_SIGNS = ("please wait a few minutes", "challenge_required", "feedback_required",
               "spam", "rate limit", "login_required", "checkpoint")


def log(*a) -> None:
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def load_config() -> dict:
    f = HERE / "config.json"
    if not f.exists():
        sys.exit("config.json is missing. Copy config.example.json to config.json "
                 "and fill in serverUrl, agentKey, igUsername and igPassword.")
    c = json.loads(f.read_text(encoding="utf-8"))
    for k in ("serverUrl", "agentKey"):
        if not c.get(k):
            sys.exit(f"config.json needs {k}.")
    c["serverUrl"] = c["serverUrl"].rstrip("/")
    c.setdefault("dryRun", True)
    return c


CFG = load_config()


# ── the proxy ────────────────────────────────────────────────────────────
# Same trap as the WhatsApp sender: the browser reaches the site through a
# local proxy while a bare Python process does not, and the host answers 451.
# urllib honours these variables, but only if they are actually set, so take
# the one from config when it is given.
if CFG.get("proxy"):
    os.environ.setdefault("HTTP_PROXY", CFG["proxy"])
    os.environ.setdefault("HTTPS_PROXY", CFG["proxy"])
_PROXY = os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY") or ""


def api(path: str, payload: dict | None = None) -> dict:
    req = urllib.request.Request(CFG["serverUrl"] + path, method="POST")
    req.add_header("X-Agent-Key", CFG["agentKey"])
    req.add_header("Content-Type", "application/json")
    req.data = json.dumps(payload or {}).encode()
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:160]
        raise RuntimeError(f"{path} -> HTTP {e.code} {body}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"{path} -> {e.reason}") from e


# ── Instagram ────────────────────────────────────────────────────────────
def connect():
    try:
        from instagrapi import Client
    except ImportError:
        sys.exit("instagrapi is not installed.  pip install instagrapi")

    cl = Client()
    if _PROXY:
        cl.set_proxy(_PROXY)
    # Looking like one consistent device matters: a session that changes
    # fingerprint between runs is treated as a compromised login.
    if SESSION.exists():
        try:
            cl.load_settings(SESSION)
            cl.login(CFG["igUsername"], CFG["igPassword"])
            cl.get_timeline_feed()           # cheap call that proves the session
            log("reused the saved session")
            return cl
        except Exception as e:
            log("saved session rejected:", str(e)[:120])
    cl.login(CFG["igUsername"], CFG["igPassword"])
    cl.dump_settings(SESSION)
    log("logged in, session saved")
    return cl


def looks_blocked(err: str) -> bool:
    low = err.lower()
    return any(sign in low for sign in BLOCK_SIGNS)


def send_one(cl, msg: dict) -> None:
    handle = msg["to"].lstrip("@")
    uid = cl.user_id_from_username(handle)
    # A pause roughly proportional to the message, because instant sends one
    # after another are the easiest automation signature there is.
    time.sleep(random.uniform(4, 9) + len(msg["body"]) * 0.02)
    cl.direct_send(msg["body"], user_ids=[int(uid)])


# ── check mode ───────────────────────────────────────────────────────────
def check() -> int:
    print()
    print("server  :", CFG["serverUrl"])
    print("proxy   :", _PROXY or "(none — connecting directly)")
    print("account :", CFG.get("igUsername") or "(not set)")
    print("dry run :", CFG["dryRun"])
    try:
        r = api(f"/api/agent/claim?channel={CHANNEL}")
    except RuntimeError as e:
        print("server  : FAILED —", e)
        print()
        if "451" in str(e):
            print('451 means the host refused this country, not a bad key.')
            print('Set "proxy" in config.json, e.g. "http://127.0.0.1:10808".')
        elif "401" in str(e):
            print("401 means the agent key is wrong — copy it again from")
            print("Admin → Project Finder → Autopilot → Sender setup.")
        return 1

    if r.get("message"):
        m = r["message"]
        print("server  : OK — a message is ready")
        print()
        print(f"  to    : @{m['to']}  ({m['name']})")
        print(f"  need  : {m['need']}")
        print(f"  today : {r.get('sent_today', 0)}/{r.get('cap')}")
        print()
        print(m["body"])
        print()
        api("/api/agent/report", {"id": m["id"], "ok": False,
                                  "error": "returned by --check"})
        print("(returned to the queue — nothing was sent)")
    else:
        print("server  : OK — nothing to send (" + str(r.get("reason")) + ")")
        if r.get("reason") == "channel_disabled":
            print("          Instagram is not in the channel list;")
            print("          turn it on in Admin → Project Finder → Autopilot.")
        elif r.get("reason") == "paused":
            print("          Autopilot is off.")
        elif r.get("next_due"):
            print("          next message due at " + str(r["next_due"]))
    print()
    print("Everything except Instagram itself is working.")
    return 0


# ── the loop ─────────────────────────────────────────────────────────────
def main() -> int:
    if "--check" in sys.argv:
        return check()

    if not CFG.get("igUsername") or not CFG.get("igPassword"):
        sys.exit("config.json needs igUsername and igPassword.")

    log("server:", CFG["serverUrl"], "(DRY RUN)" if CFG["dryRun"] else "")
    if _PROXY:
        log("proxy:", _PROXY)
    cl = None if CFG["dryRun"] else connect()

    failures = 0
    last_reason = ""
    while True:
        try:
            r = api(f"/api/agent/claim?channel={CHANNEL}")
        except RuntimeError as e:
            log("claim failed:", e)
            time.sleep(45)
            continue

        msg = r.get("message")
        if not msg:
            reason = r.get("reason", "nothing")
            if reason != last_reason:
                log("waiting:", reason)
                last_reason = reason
            time.sleep(min(900, max(30, r.get("wait_s", 90))))
            continue
        last_reason = ""

        log(f"sending to @{msg['to']} ({msg['name']}) — {msg['need']} "
            f"[{r.get('sent_today', 0) + 1}/{r.get('cap')}]")
        try:
            if CFG["dryRun"]:
                log("DRY RUN — not sending:\n" + msg["body"] + "\n")
            else:
                send_one(cl, msg)
            api("/api/agent/report", {"id": msg["id"], "ok": True})
            failures = 0
            log("  sent")
        except Exception as e:
            err = str(e)[:280]
            failures += 1
            log("  failed:", err)
            try:
                api("/api/agent/report", {"id": msg["id"], "ok": False, "error": err})
            except RuntimeError:
                pass

            # Instagram asking you to wait is not an error to push through.
            if looks_blocked(err):
                log("")
                log("Instagram is pushing back. Pausing the queue and stopping")
                log("for today — retrying through this is how a temporary block")
                log("becomes a permanent one.")
                try:
                    api("/api/agent/pause?reason=instagram+rate+limit")
                except RuntimeError:
                    pass
                return 2
            if failures >= 3:
                log("three failures in a row — pausing the queue")
                try:
                    api("/api/agent/pause?reason=3+consecutive+instagram+failures")
                except RuntimeError:
                    pass
                return 2

        gap = max(120, r.get("min_gap_s", 420))
        time.sleep(gap * random.uniform(0.75, 1.5))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        log("stopping")
        sys.exit(0)
