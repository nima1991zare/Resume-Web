"""AUTOPILOT — research every lead, queue one message each, hand them out one at a time.

The sender lives on Nima's PC and drives his own WhatsApp session. That makes
this module the only place where pacing can be enforced honestly, because the
sender is a dumb client: it asks for the next message it may send, and this
decides whether there is one.

Everything that keeps the account alive is therefore a property of the queue,
not of the sender's loop:

* **One message per lead, ever.** `UNIQUE(lead_id, channel)` on the outbox, so a
  re-run or a second sender cannot message anyone twice.
* **Due times, not delays.** Each queued message gets a `due_at` spread out with
  jitter. A sender that crashes and restarts cannot replay a burst, because the
  times are already written down.
* **A cap counted from what was sent**, not from what this process remembers.
* **Quiet hours** — nobody cold-messages a business at 02:00, and a number that
  does looks exactly like a bot.
* **Stop on reply.** The moment a lead answers, their status leaves `contacted`
  and nothing further is queued for them.

The sender can be stopped from one place (`auto_enabled`), and that switch is
read on every claim rather than cached.
"""
from __future__ import annotations

import asyncio
import logging
import random
import threading
import time
from datetime import datetime, timedelta

import httpx

from . import research
from .database import get_db, get_setting, set_setting
from .finder import (TIMEOUT, UA, new_client, lead_rows, sender_signature,
                     normalize_domain, _run_set, start_run, active_run)

logger = logging.getLogger("finder.autopilot")

# A message can only be claimed if it is due, and claims expire so a sender that
# dies mid-send does not strand the row forever.
CLAIM_TIMEOUT_MINUTES = 10


# ─────────────────────────────────────────── settings
def config() -> dict:
    conn = get_db()
    try:
        g = lambda k, d="": get_setting(conn, k) or d      # noqa: E731
        return {
            "enabled": g("auto_enabled", "0") == "1",
            "daily_cap": int(g("auto_daily_cap", "25") or 25),
            "min_gap_s": int(g("auto_min_gap_s", "140") or 140),
            "quiet_start": g("auto_quiet_start", "21:30"),
            "quiet_end": g("auto_quiet_end", "09:30"),
            "min_score": int(g("auto_min_score", "55") or 55),
            "channel": g("auto_channel", "whatsapp"),
        }
    finally:
        conn.close()


def set_config(**kw) -> dict:
    keys = {"enabled": "auto_enabled", "daily_cap": "auto_daily_cap",
            "min_gap_s": "auto_min_gap_s", "quiet_start": "auto_quiet_start",
            "quiet_end": "auto_quiet_end", "min_score": "auto_min_score",
            "channel": "auto_channel"}
    conn = get_db()
    try:
        for k, v in kw.items():
            if k not in keys or v is None:
                continue
            if k == "enabled":
                v = "1" if v else "0"
            set_setting(conn, keys[k], str(v))
        conn.commit()
    finally:
        conn.close()
    return config()


def _hhmm(s: str, fallback: str) -> tuple[int, int]:
    try:
        h, m = (s or fallback).split(":")
        return int(h) % 24, int(m) % 60
    except (ValueError, AttributeError):
        h, m = fallback.split(":")
        return int(h), int(m)


def in_quiet_hours(cfg: dict, now: datetime | None = None) -> bool:
    now = now or datetime.now()
    sh, sm = _hhmm(cfg["quiet_start"], "21:30")
    eh, em = _hhmm(cfg["quiet_end"], "09:30")
    start, end = sh * 60 + sm, eh * 60 + em
    cur = now.hour * 60 + now.minute
    # The window normally wraps midnight, which a naive comparison gets wrong
    # in exactly the hours it matters most.
    return (start <= cur or cur < end) if start > end else (start <= cur < end)


def _next_due(conn, cfg: dict) -> datetime:
    """When the next queued message may go out.

    Spaced from the last one already in the queue rather than from now, so
    queueing forty messages at once still produces forty well-separated send
    times instead of forty messages due immediately.
    """
    row = conn.execute(
        "SELECT MAX(due_at) d FROM outbox WHERE status IN ('queued','claimed')"
    ).fetchone()
    base = datetime.now()
    if row and row["d"]:
        try:
            last = datetime.strptime(row["d"], "%Y-%m-%d %H:%M:%S")
            base = max(base, last)
        except ValueError:
            pass
    gap = max(45, cfg["min_gap_s"])
    # Jitter both ways. A perfectly regular interval is a signature.
    due = base + timedelta(seconds=gap + random.randint(-gap // 4, gap // 2))

    # Walk out of quiet hours rather than queueing into them.
    for _ in range(48):
        if not in_quiet_hours(cfg, due):
            break
        due += timedelta(minutes=30)
    return due


def sent_today(conn) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM outbox WHERE status='sent' "
        "AND date(sent_at)=date('now','localtime')").fetchone()[0]


# ─────────────────────────────────────────── research + queue
async def _research_and_queue(run_id: int, limit: int) -> tuple[int, int]:
    """-> (researched, queued)"""
    cfg = config()
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT id FROM leads WHERE researched_at IS NULL "
            "AND status='new' AND score>=? ORDER BY score DESC LIMIT ?",
            (cfg["min_score"], limit)).fetchall()
        ids = [r["id"] for r in rows]
    finally:
        conn.close()
    if not ids:
        return 0, 0

    done = queued = 0
    sem = asyncio.Semaphore(4)           # polite to small Iranian hosts
    sender = sender_signature()

    async with new_client() as client:
        async def one(lead_id: int):
            nonlocal done, queued
            conn = get_db()
            try:
                row = conn.execute("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchone()
                lead = dict(row) if row else None
            finally:
                conn.close()
            if not lead:
                return
            async with sem:
                try:
                    r = await research.research_lead(client, lead, UA)
                except Exception as e:            # one bad site must not stop a run
                    logger.warning("research %s failed: %s", lead_id, e)
                    r = {"need": "", "need_fa": "", "evidence": "",
                         "evidence_url": "", "pages": 0}

            conn = get_db()
            try:
                conn.execute(
                    "UPDATE leads SET need=?,need_fa=?,need_evidence=?,"
                    "need_evidence_url=?,pages_seen=?,researched_at=datetime('now') "
                    "WHERE id=?",
                    (r["need"], r["need_fa"], r["evidence"][:400],
                     r["evidence_url"][:400], r["pages"], lead_id))
                done += 1

                if r["need"] and not lead["pitch_edited"]:
                    finding = research.Finding(
                        r["need"], 0, r["need_fa"], r["evidence_url"], r["evidence"])
                    body = research.compose(
                        lead["name"], lead["domain"] or normalize_domain(lead["website"]),
                        lead["city"], finding, sender)
                    conn.execute("UPDATE leads SET pitch=? WHERE id=?", (body, lead_id))

                    to_addr = lead["phone_e164"] if lead["is_mobile"] else ""
                    if cfg["channel"] == "whatsapp" and to_addr:
                        due = _next_due(conn, cfg)
                        try:
                            conn.execute(
                                "INSERT INTO outbox(lead_id,channel,to_addr,body,need,due_at)"
                                " VALUES(?,?,?,?,?,?)",
                                (lead_id, "whatsapp", to_addr, body, r["need"],
                                 due.strftime("%Y-%m-%d %H:%M:%S")))
                            queued += 1
                        except Exception:
                            pass          # UNIQUE(lead_id,channel): already queued
                conn.commit()
            finally:
                conn.close()
            if done % 5 == 0:
                _run_set(run_id, profiled=done,
                         message=f"{done} کسب‌وکار بررسی شد، {queued} پیام در صف")

        await asyncio.gather(*(one(i) for i in ids))
    return done, queued


def launch_research(limit: int = 60) -> dict:
    """Research the best un-researched leads and queue a message for each."""
    if active_run():
        raise RuntimeError("یک اجرا همین حالا در حال انجام است.")
    run_id = start_run("research")

    def worker():
        try:
            done, queued = asyncio.run(_research_and_queue(run_id, limit))
            _run_set(run_id, status="done", profiled=done,
                     message=f"{done} کسب‌وکار بررسی شد، {queued} پیام در صف قرار گرفت.",
                     finished_at=time.strftime("%Y-%m-%d %H:%M:%S"))
        except Exception as e:
            logger.exception("research run failed")
            _run_set(run_id, status="error", message=str(e)[:500],
                     finished_at=time.strftime("%Y-%m-%d %H:%M:%S"))

    threading.Thread(target=worker, name=f"research-{run_id}", daemon=True).start()
    conn = get_db()
    try:
        return dict(conn.execute("SELECT * FROM finder_runs WHERE id=?",
                                 (run_id,)).fetchone())
    finally:
        conn.close()


# ─────────────────────────────────────────── the sender protocol
def claim_next() -> dict:
    """Hand the sender one message, or tell it why there is none.

    Every guard is re-read here rather than trusted from the caller, because the
    caller is a separate process on another machine that may be running an old
    build, may have been started twice, or may simply be wrong.
    """
    cfg = config()
    if not cfg["enabled"]:
        return {"message": None, "reason": "paused", "wait_s": 120}
    if in_quiet_hours(cfg):
        return {"message": None, "reason": "quiet_hours", "wait_s": 600}

    conn = get_db()
    try:
        used = sent_today(conn)
        if used >= cfg["daily_cap"]:
            return {"message": None, "reason": "daily_cap",
                    "sent_today": used, "cap": cfg["daily_cap"], "wait_s": 1800}

        # Release anything a dead sender claimed and never reported.
        conn.execute(
            "UPDATE outbox SET status='queued', claimed_at=NULL "
            "WHERE status='claimed' AND claimed_at < datetime('now', ?)",
            (f"-{CLAIM_TIMEOUT_MINUTES} minutes",))

        row = conn.execute(
            "SELECT o.*, l.name, l.status AS lead_status FROM outbox o "
            "JOIN leads l ON l.id=o.lead_id "
            "WHERE o.status='queued' AND o.due_at<=datetime('now') "
            "ORDER BY o.due_at LIMIT 1").fetchone()
        if row is None:
            nxt = conn.execute(
                "SELECT MIN(due_at) d FROM outbox WHERE status='queued'").fetchone()
            conn.commit()
            return {"message": None, "reason": "nothing_due",
                    "next_due": nxt["d"] if nxt else None, "wait_s": 90}

        # A lead who already replied is off the list — that conversation is his.
        if row["lead_status"] not in ("new", "contacted"):
            conn.execute("UPDATE outbox SET status='skipped', "
                         "error='lead already answered' WHERE id=?", (row["id"],))
            conn.commit()
            return {"message": None, "reason": "skipped", "wait_s": 2}

        conn.execute(
            "UPDATE outbox SET status='claimed', claimed_at=datetime('now'), "
            "attempts=attempts+1 WHERE id=?", (row["id"],))
        conn.commit()
        return {"message": {"id": row["id"], "lead_id": row["lead_id"],
                            "name": row["name"], "to": row["to_addr"],
                            "body": row["body"], "need": row["need"],
                            "attempt": row["attempts"] + 1},
                "sent_today": used, "cap": cfg["daily_cap"],
                "min_gap_s": cfg["min_gap_s"]}
    finally:
        conn.close()


def report(outbox_id: int, ok: bool, error: str = "") -> dict:
    """The sender tells us what happened. A send marks the lead contacted."""
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM outbox WHERE id=?", (outbox_id,)).fetchone()
        if row is None:
            raise LookupError("no such message")
        if ok:
            conn.execute("UPDATE outbox SET status='sent', sent_at=datetime('now'), "
                         "error='' WHERE id=?", (outbox_id,))
            conn.execute("UPDATE leads SET status='contacted', "
                         "updated_at=datetime('now') WHERE id=? AND status='new'",
                         (row["lead_id"],))
        else:
            # Three honest attempts, then stop retrying it forever.
            final = row["attempts"] >= 3
            conn.execute(
                "UPDATE outbox SET status=?, error=?, due_at=datetime('now','+20 minutes') "
                "WHERE id=?", ("failed" if final else "queued", error[:300], outbox_id))
        conn.commit()
        return {"ok": True, "status": "sent" if ok else "failed"}
    finally:
        conn.close()


def pause(reason: str = "") -> dict:
    """The kill switch. The sender sees it on its next claim, within seconds."""
    set_config(enabled=False)
    logger.warning("autopilot paused: %s", reason or "manual")
    return config()


# ─────────────────────────────────────────── views
def outbox_rows(status: str = "", limit: int = 100) -> list[dict]:
    where, args = ["1=1"], []
    if status in ("queued", "claimed", "sent", "failed", "skipped"):
        where.append("o.status=?")
        args.append(status)
    conn = get_db()
    try:
        return [dict(r) for r in conn.execute(
            f"SELECT o.*, l.name, l.score, l.need_fa, l.instagram "
            f"FROM outbox o JOIN leads l ON l.id=o.lead_id "
            f"WHERE {' AND '.join(where)} "
            f"ORDER BY CASE o.status WHEN 'queued' THEN 0 WHEN 'claimed' THEN 1 "
            f"ELSE 2 END, o.due_at DESC LIMIT ?", (*args, int(limit)))]
    finally:
        conn.close()


def status() -> dict:
    cfg = config()
    conn = get_db()
    try:
        counts = {r["status"]: r["n"] for r in conn.execute(
            "SELECT status, COUNT(*) n FROM outbox GROUP BY status")}
        nxt = conn.execute(
            "SELECT MIN(due_at) d FROM outbox WHERE status='queued'").fetchone()
        unresearched = conn.execute(
            "SELECT COUNT(*) FROM leads WHERE researched_at IS NULL AND status='new' "
            "AND score>=?", (cfg["min_score"],)).fetchone()[0]
        researched = conn.execute(
            "SELECT COUNT(*) FROM leads WHERE researched_at IS NOT NULL").fetchone()[0]
        return {
            "config": cfg,
            "quiet_now": in_quiet_hours(cfg),
            "sent_today": sent_today(conn),
            "counts": counts,
            "queued": counts.get("queued", 0),
            "sent": counts.get("sent", 0),
            "failed": counts.get("failed", 0),
            "next_due": nxt["d"] if nxt else None,
            "unresearched": unresearched,
            "researched": researched,
        }
    finally:
        conn.close()


def requeue(outbox_id: int) -> dict:
    conn = get_db()
    try:
        conn.execute("UPDATE outbox SET status='queued', attempts=0, error='', "
                     "due_at=datetime('now') WHERE id=?", (outbox_id,))
        conn.commit()
    finally:
        conn.close()
    return {"ok": True}


def drop(outbox_id: int) -> dict:
    conn = get_db()
    try:
        conn.execute("DELETE FROM outbox WHERE id=?", (outbox_id,))
        conn.commit()
    finally:
        conn.close()
    return {"ok": True}
