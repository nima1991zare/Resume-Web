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
import re
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

# How recently a sender must have asked for work to count as "running". The
# Instagram sender sleeps up to 30 minutes when it hits its daily cap, so this
# has to be comfortably longer than one idle poll — otherwise a live sender is
# mistaken for a dead one and its queue is moved to the other channel.
SENDER_LIVE_MINUTES = 45

CHANNELS = ("instagram", "whatsapp")

SQL_DT = "%Y-%m-%d %H:%M:%S"


# Every timestamp in the database is UTC, because the claim compares due_at
# against SQLite's datetime('now'). But "quiet hours", "sent today" and the
# daily cap are human ideas and have to be answered in the sender's own
# timezone — the server runs UTC, so asking datetime.now() shifted a
# 21:30-09:30 window to 01:00-13:00 local: silent all morning, awake at night.
#
# A fixed offset rather than a zoneinfo name on purpose: Iran dropped DST in
# 2022, so +03:30 is correct year-round, and it needs no tzdata package on
# either the server or a Windows laptop.
def tz_offset() -> int:
    conn = get_db()
    try:
        raw = get_setting(conn, "auto_tz_offset_min") or "210"
    finally:
        conn.close()
    try:
        return max(-840, min(840, int(raw)))
    except ValueError:
        return 210


def utc_now() -> datetime:
    """Naive UTC, which is what SQLite's datetime('now') returns."""
    return datetime.utcnow()


def local_now(offset: int | None = None) -> datetime:
    """Naive wall-clock time where the businesses are."""
    off = tz_offset() if offset is None else offset
    return utc_now() + timedelta(minutes=off)


def local_at(naive_utc: datetime, offset: int | None = None) -> datetime:
    """A stored UTC timestamp, as wall-clock time for the business."""
    off = tz_offset() if offset is None else offset
    return naive_utc + timedelta(minutes=off)


def dt_str(dt: datetime) -> str:
    return dt.strftime(SQL_DT)


def cap_for(cfg: dict, channel: str) -> int:
    return cfg["ig_daily_cap"] if channel == "instagram" else cfg["daily_cap"]


def gap_for(cfg: dict, channel: str) -> int:
    return cfg["ig_min_gap_s"] if channel == "instagram" else cfg["min_gap_s"]


def sender_key(channel: str) -> str:
    return f"agent_seen_{channel}"


def sender_status(conn, cfg: dict) -> dict:
    """Which senders have asked for work recently.

    A queue is only useful if something is on the other end of it. The panel
    shows this, and `channel_for` uses it so a message is not parked on
    Instagram for days because that sender was never started while the
    WhatsApp one is running and idle.
    """
    now = utc_now()
    out = {}
    for ch in CHANNELS:
        raw = get_setting(conn, sender_key(ch)) or ""
        seen = None
        if raw:
            try:
                seen = datetime.strptime(raw, SQL_DT)
            except ValueError:
                seen = None
        live = bool(seen and now - seen <= timedelta(minutes=SENDER_LIVE_MINUTES))
        out[ch] = {"last_seen": raw or None, "live": live,
                   "enabled": ch in cfg["channels"]}
    return out


def mark_sender_seen(channel: str) -> None:
    conn = get_db()
    try:
        set_setting(conn, sender_key(channel), dt_str(utc_now()))
        conn.commit()
    finally:
        conn.close()


def channel_for(lead: dict, cfg: dict, exclude: tuple = (),
                live: tuple | list = ()) -> str:
    """Which channel to use for this lead, honouring the configured order.

    Instagram first by default: a business that runs on Instagram reads its
    DMs, and an unexpected WhatsApp message from a stranger is an interruption
    on a personal phone. Falls through to whatever the lead actually has.

    Senders that are actually running come first. If only the WhatsApp process
    is up, that is where a message has a chance of being delivered today; the
    documented order still decides between two live senders, and still decides
    when nothing has checked in at all.
    """
    order = list(cfg["channels"])
    if live:
        order = ([c for c in order if c in live] +
                 [c for c in order if c not in live])
    for ch in order:
        if ch in exclude:
            continue
        if ch == "instagram" and lead.get("instagram"):
            return ch
        if ch == "whatsapp" and lead.get("is_mobile") and lead.get("phone_e164"):
            return ch
    return ""


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
            "channels": [c.strip() for c in
                         (g("auto_channels", "instagram,whatsapp")).split(",")
                         if c.strip() in CHANNELS],
            "ig_daily_cap": int(g("auto_ig_daily_cap", "12") or 12),
            "ig_min_gap_s": int(g("auto_ig_min_gap_s", "420") or 420),
            "fallback": g("auto_fallback", "1") == "1",
            "tz_offset_min": int(g("auto_tz_offset_min", "210") or 210),
        }
    finally:
        conn.close()


def set_config(**kw) -> dict:
    keys = {"enabled": "auto_enabled", "daily_cap": "auto_daily_cap",
            "min_gap_s": "auto_min_gap_s", "quiet_start": "auto_quiet_start",
            "quiet_end": "auto_quiet_end", "min_score": "auto_min_score",
            "channels": "auto_channels", "ig_daily_cap": "auto_ig_daily_cap",
            "ig_min_gap_s": "auto_ig_min_gap_s", "fallback": "auto_fallback",
            "tz_offset_min": "auto_tz_offset_min"}
    conn = get_db()
    try:
        for k, v in kw.items():
            if k not in keys or v is None:
                continue
            if k in ("enabled", "fallback"):
                v = "1" if v else "0"
            elif k == "channels" and isinstance(v, (list, tuple)):
                v = ",".join(x for x in v if x in CHANNELS)
            set_setting(conn, keys[k], str(v))
        conn.commit()
    finally:
        conn.close()
    cfg = config()
    if "channels" in kw:
        reroute_disabled(cfg)
    return cfg


def reroute_disabled(cfg: dict) -> int:
    """Move messages queued on a channel that is now switched off.

    Turning Instagram off would otherwise strand every lead already queued
    there: the claim refuses a disabled channel, and the fallback only fires on
    a *failed send*, which can never happen for a message nobody is allowed to
    claim. Those leads would sit in the queue looking scheduled and never go
    anywhere.
    """
    live = [c for c in CHANNELS if c in cfg["channels"]]
    dead = [c for c in CHANNELS if c not in cfg["channels"]]
    if not live or not dead:
        return 0

    moved = 0
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT o.*, l.instagram, l.phone_e164, l.is_mobile, l.name, l.domain, "
            "l.city, l.need, l.need_fa, l.need_evidence, l.need_evidence_url "
            "FROM outbox o JOIN leads l ON l.id=o.lead_id "
            f"WHERE o.status='queued' AND o.channel IN ({','.join('?' * len(dead))})",
            dead).fetchall()
        sender = sender_signature()
        for r in rows:
            lead = dict(r)
            other = channel_for(lead, cfg)
            if not other:
                # Nothing else reaches them — drop it rather than leave a
                # message pretending it is still on its way.
                conn.execute("UPDATE outbox SET status='skipped', "
                             "error='channel turned off, no other way to reach them' "
                             "WHERE id=?", (r["id"],))
                continue
            to_addr = lead["instagram"] if other == "instagram" else lead["phone_e164"]
            body = r["body"]
            if lead["need"]:
                finding = research.Finding(lead["need"], 0, lead["need_fa"],
                                           lead["need_evidence_url"], lead["need_evidence"])
                body = research.compose(lead["name"], lead["domain"], lead["city"],
                                        finding, sender, channel=other)
            due = _next_due(conn, cfg, other)
            try:
                conn.execute(
                    "UPDATE outbox SET channel=?, to_addr=?, body=?, due_at=?, "
                    "attempts=0, error='' WHERE id=?",
                    (other, to_addr, body, due.strftime("%Y-%m-%d %H:%M:%S"), r["id"]))
                conn.commit()        # so the next due time sees this one
                moved += 1
            except Exception:
                # Already queued on the other channel for this lead.
                conn.execute("UPDATE outbox SET status='skipped', "
                             "error='already queued on the other channel' "
                             "WHERE id=?", (r["id"],))
        conn.commit()
        if moved:
            logger.info("rerouted %d queued messages off %s", moved, ",".join(dead))
    finally:
        conn.close()
    return moved


def _hhmm(s: str, fallback: str) -> tuple[int, int]:
    try:
        h, m = (s or fallback).split(":")
        return int(h) % 24, int(m) % 60
    except (ValueError, AttributeError):
        h, m = fallback.split(":")
        return int(h), int(m)


def in_quiet_hours(cfg: dict, now: datetime | None = None) -> bool:
    """`now` is business-local wall time; callers pass UTC due times through
    `local_at` first."""
    now = now or local_now(cfg.get("tz_offset_min"))
    sh, sm = _hhmm(cfg["quiet_start"], "21:30")
    eh, em = _hhmm(cfg["quiet_end"], "09:30")
    start, end = sh * 60 + sm, eh * 60 + em
    cur = now.hour * 60 + now.minute
    # The window normally wraps midnight, which a naive comparison gets wrong
    # in exactly the hours it matters most.
    return (start <= cur or cur < end) if start > end else (start <= cur < end)


def _next_due(conn, cfg: dict, channel: str) -> datetime:
    """When the next queued message may go out.

    Spaced from the last one already in the queue rather than from now, so
    queueing forty messages at once still produces forty well-separated send
    times instead of forty messages due immediately.

    Stored in UTC because every due_at comparison is against SQLite's
    datetime('now'), which is UTC too.
    """
    row = conn.execute(
        "SELECT MAX(due_at) d FROM outbox WHERE status IN ('queued','claimed') "
        "AND channel=?", (channel,)).fetchone()
    base = utc_now()
    if row and row["d"]:
        try:
            last = datetime.strptime(row["d"], SQL_DT)
            base = max(base, last)
        except ValueError:
            pass
    gap = max(45, gap_for(cfg, channel))
    # Jitter both ways. A perfectly regular interval is a signature.
    due = base + timedelta(seconds=gap + random.randint(-gap // 4, gap // 2))

    # Walk out of quiet hours rather than queueing into them. `due` is UTC, so
    # it has to be converted before asking a question about the local clock.
    off = cfg.get("tz_offset_min", 210)
    for _ in range(48):
        if not in_quiet_hours(cfg, local_at(due, off)):
            break
        due += timedelta(minutes=30)
    return due


def sent_today(conn, channel: str = "") -> int:
    """Count sends inside the sender's local day.

    sent_at is UTC, so the local day has to be expressed as a UTC window.
    date('now','localtime') asked the *server* what day it was, which on a
    UTC host rolls the cap over at 03:30 local — the cap would reset in the
    middle of the night and then run out mid-afternoon.
    """
    off = tz_offset()
    midnight = local_now(off).replace(hour=0, minute=0, second=0, microsecond=0)
    start = midnight - timedelta(minutes=off)
    end = start + timedelta(days=1)
    sql = ("SELECT COUNT(*) FROM outbox WHERE status='sent' "
           "AND sent_at >= ? AND sent_at < ?")
    args: tuple = (dt_str(start), dt_str(end))
    if channel:
        sql += " AND channel=?"
        args = args + (channel,)
    return conn.execute(sql, args).fetchone()[0]


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
                # Which senders are up right now decides where this message is
                # queued, so it is read with the lead rather than once per run.
                live = [c for c in cfg["channels"] if sender_status(conn, cfg)[c]["live"]]
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

                if r["need"]:
                    finding = research.Finding(
                        r["need"], 0, r["need_fa"], r["evidence_url"], r["evidence"])
                    domain = lead["domain"] or normalize_domain(lead["website"])
                    channel = channel_for(lead, cfg, live=live)
                    body = research.compose(lead["name"], domain, lead["city"],
                                            finding, sender, channel=channel or "whatsapp")
                    if not lead["pitch_edited"]:
                        conn.execute("UPDATE leads SET pitch=? WHERE id=?", (body, lead_id))

                    to_addr = (lead["instagram"] if channel == "instagram"
                               else lead["phone_e164"])
                    if channel and to_addr:
                        due = _next_due(conn, cfg, channel)
                        try:
                            conn.execute(
                                "INSERT INTO outbox(lead_id,channel,to_addr,body,need,due_at)"
                                " VALUES(?,?,?,?,?,?)",
                                (lead_id, channel, to_addr, body, r["need"],
                                 due.strftime(SQL_DT)))
                            # Commit before the next lead is scheduled. _next_due
                            # reads MAX(due_at) on a *different* connection, and
                            # an uncommitted row is invisible to it — leaving
                            # every concurrently-researched lead scheduled for
                            # the same instant, which is the burst the spacing
                            # exists to prevent.
                            conn.commit()
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


async def _recheck_site_claims(run_id: int) -> dict:
    """Re-crawl the sites behind queued "your site is down" messages.

    Those messages are the most damaging kind of wrong: a business whose site
    loads perfectly for every customer in Shiraz is told it does not. They were
    produced by a crawl that could not tell "broken" from "the network this ran
    on is not allowed to see it" — a VPN exit, or a host that blocks foreign
    IPs. `fetch_site` now separates the two, so the messages written before it
    did have to be re-derived rather than sent.
    """
    conn = get_db()
    try:
        ids = [r["lead_id"] for r in conn.execute(
            "SELECT DISTINCT o.lead_id FROM outbox o JOIN leads l ON l.id=o.lead_id "
            "WHERE o.status='queued' AND (o.need='NEED_SITE_FIX' OR "
            "l.need='NEED_SITE_FIX')").fetchall()]
    finally:
        conn.close()

    sender = sender_signature()
    counted = {"checked": 0, "rewritten": 0, "dropped": 0, "kept": 0}
    sem = asyncio.Semaphore(3)

    async with new_client() as client:
        async def one(lead_id: int) -> None:
            conn = get_db()
            try:
                row = conn.execute("SELECT * FROM leads WHERE id=?",
                                   (lead_id,)).fetchone()
                lead = dict(row) if row else None
            finally:
                conn.close()
            if not lead:
                return
            async with sem:
                try:
                    r = await research.research_lead(client, lead, UA)
                except Exception:
                    counted["kept"] += 1
                    return
            conn = get_db()
            try:
                out = conn.execute(
                    "SELECT id, channel FROM outbox WHERE lead_id=? AND status='queued'",
                    (lead_id,)).fetchone()
                if not out:
                    return
                counted["checked"] += 1
                if not r["need"]:
                    # It opens. The claim was wrong, so the message is deleted
                    # rather than reworded — nobody is told about a problem
                    # they do not have.
                    conn.execute("DELETE FROM outbox WHERE id=?", (out["id"],))
                    conn.execute("UPDATE leads SET need='', need_fa='', "
                                 "need_evidence='', need_evidence_url='' WHERE id=?",
                                 (lead_id,))
                    counted["dropped"] += 1
                else:
                    finding = research.Finding(r["need"], 0, r["need_fa"],
                                               r["evidence_url"], r["evidence"])
                    body = research.compose(
                        lead["name"], lead["domain"] or normalize_domain(lead["website"]),
                        lead["city"], finding, sender, channel=out["channel"])
                    conn.execute("UPDATE leads SET need=?,need_fa=?,need_evidence=?,"
                                 "need_evidence_url=? WHERE id=?",
                                 (r["need"], r["need_fa"], r["evidence"][:400],
                                  r["evidence_url"][:400], lead_id))
                    conn.execute("UPDATE outbox SET body=?, need=? WHERE id=?",
                                 (body, r["need"], out["id"]))
                    counted["rewritten"] += 1
                conn.commit()
            finally:
                conn.close()

        await asyncio.gather(*(one(i) for i in ids))
    return counted


def launch_recheck() -> dict:
    """Re-verify every queued "site is down" message. Safe to run twice."""
    if active_run():
        raise RuntimeError("یک اجرا همین حالا در حال انجام است.")
    run_id = start_run("recheck")

    def worker():
        try:
            r = asyncio.run(_recheck_site_claims(run_id))
            _run_set(run_id, status="done", profiled=r["checked"],
                     message=(f"{r['checked']} پیام «سایت خراب است» دوباره بررسی شد — "
                              f"{r['rewritten']} اصلاح، {r['dropped']} حذف، "
                              f"{r['kept']} هنوز درست بود."),
                     finished_at=time.strftime("%Y-%m-%d %H:%M:%S"))
        except Exception as e:
            logger.exception("recheck run failed")
            _run_set(run_id, status="error", message=str(e)[:500],
                     finished_at=time.strftime("%Y-%m-%d %H:%M:%S"))

    threading.Thread(target=worker, name=f"recheck-{run_id}", daemon=True).start()
    conn = get_db()
    try:
        return dict(conn.execute("SELECT * FROM finder_runs WHERE id=?",
                                 (run_id,)).fetchone())
    finally:
        conn.close()


# ─────────────────────────────────────────── the sender protocol
def _reroute_to_live(conn, cfg: dict, live: list, target: str,
                     limit: int = 6) -> int:
    """Move queued messages off a channel whose sender is not running.

    The panel tries Instagram first, and on a fresh install the Instagram
    sender is often not started at all. Those messages would sit in the queue
    forever while the WhatsApp sender asks for work and is told there is none.
    A live sender may therefore adopt a handful of messages the dead channel
    was sitting on — re-worded for the new channel, and paced from that
    channel's own queue so adopting them cannot produce a burst.
    """
    dead = [c for c in cfg["channels"] if c not in live and c != target]
    if not dead:
        return 0
    rows = conn.execute(
        "SELECT o.id AS oid, o.body, o.need, l.* FROM outbox o "
        "JOIN leads l ON l.id=o.lead_id "
        f"WHERE o.status='queued' AND o.channel IN ({','.join('?' * len(dead))}) "
        "ORDER BY o.due_at LIMIT ?", (*dead, limit)).fetchall()
    if not rows:
        return 0
    sender = sender_signature()
    moved = 0
    for r in rows:
        lead = dict(r)
        if lead["status"] not in ("new", "contacted"):
            continue
        if channel_for(lead, cfg, live=live) != target:
            continue
        to_addr = lead["instagram"] if target == "instagram" else lead["phone_e164"]
        if not to_addr:
            continue
        body = r["body"]
        if r["need"]:
            finding = research.Finding(r["need"], 0, lead["need_fa"],
                                       lead["need_evidence_url"], lead["need_evidence"])
            body = research.compose(lead["name"], lead["domain"], lead["city"],
                                    finding, sender, channel=target)
        due = _next_due(conn, cfg, target)
        try:
            conn.execute(
                "UPDATE outbox SET channel=?, to_addr=?, body=?, attempts=0, "
                "error='', due_at=? WHERE id=?",
                (target, to_addr, body, dt_str(due), r["oid"]))
            conn.commit()
            moved += 1
        except Exception:
            # UNIQUE(lead_id,channel): it is already queued on the target.
            conn.execute("UPDATE outbox SET status='skipped', "
                         "error='already queued on the other channel' WHERE id=?",
                         (r["oid"],))
    if moved:
        logger.info("adopted %d queued messages from %s onto %s",
                    moved, ",".join(dead), target)
    return moved


def claim_next(channel: str = "whatsapp", peek: bool = False,
               offset: int = 0) -> dict:
    """Hand the sender one message, or tell it why there is none.

    Every guard is re-read here rather than trusted from the caller, because the
    caller is a separate process on another machine that may be running an old
    build, may have been started twice, or may simply be wrong.

    `peek` is what the dry run and the --check mode use: it shows exactly what
    would go out next without claiming it, incrementing the attempt counter or
    marking anything as sent. A check that consumed the queue would be worse
    than no check at all.
    """
    if channel not in CHANNELS:
        return {"message": None, "reason": "bad_channel", "wait_s": 600, "peek": bool(peek)}
    if not peek:
        mark_sender_seen(channel)

    cfg = config()
    if not cfg["enabled"]:
        return {"message": None, "reason": "paused", "wait_s": 120, "peek": bool(peek)}
    if channel not in cfg["channels"]:
        return {"message": None, "reason": "channel_disabled", "wait_s": 600, "peek": bool(peek)}
    if in_quiet_hours(cfg):
        return {"message": None, "reason": "quiet_hours", "wait_s": 600,
                "quiet_end": cfg["quiet_end"], "peek": bool(peek)}

    cap = cap_for(cfg, channel)
    conn = get_db()
    try:
        used = sent_today(conn, channel)
        if used >= cap:
            return {"message": None, "reason": "daily_cap",
                    "sent_today": used, "cap": cap, "wait_s": 1800, "peek": bool(peek)}

        # Release anything a dead sender claimed and never reported.
        conn.execute(
            "UPDATE outbox SET status='queued', claimed_at=NULL "
            "WHERE status='claimed' AND claimed_at < datetime('now', ?)",
            (f"-{CLAIM_TIMEOUT_MINUTES} minutes",))

        if not peek:
            seen = sender_status(conn, cfg)
            if seen[channel]["live"]:
                live = [c for c in cfg["channels"] if seen[c]["live"]]
                _reroute_to_live(conn, cfg, live, channel)
                conn.commit()

        row = conn.execute(
            "SELECT o.*, l.name, l.status AS lead_status FROM outbox o "
            "JOIN leads l ON l.id=o.lead_id "
            "WHERE o.status='queued' AND o.channel=? AND o.due_at<=datetime('now') "
            "ORDER BY o.due_at LIMIT 1 OFFSET ?",
            (channel, max(0, int(offset)))).fetchone()
        if row is None:
            nxt = conn.execute(
                "SELECT MIN(due_at) d FROM outbox WHERE status='queued' "
                "AND channel=?", (channel,)).fetchone()
            conn.commit()
            return {"message": None, "reason": "nothing_due",
                    "next_due": nxt["d"] if nxt else None, "wait_s": 90, "peek": bool(peek)}

        # A lead who already replied is off the list — that conversation is his.
        if row["lead_status"] not in ("new", "contacted"):
            if not peek:
                conn.execute("UPDATE outbox SET status='skipped', "
                             "error='lead already answered' WHERE id=?", (row["id"],))
                conn.commit()
            return {"message": None, "reason": "skipped", "wait_s": 2, "peek": bool(peek)}

        if not peek:
            conn.execute(
                "UPDATE outbox SET status='claimed', claimed_at=datetime('now'), "
                "attempts=attempts+1 WHERE id=?", (row["id"],))
            conn.commit()
        return {"message": {"id": row["id"], "lead_id": row["lead_id"],
                            "name": row["name"], "to": row["to_addr"],
                            "body": row["body"], "need": row["need"],
                            "channel": row["channel"],
                            "attempt": row["attempts"] + 1},
                "sent_today": used, "cap": cap, "peek": peek,
                "min_gap_s": gap_for(cfg, channel)}
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
            # Three honest attempts for a failure that might pass — but a
            # missing account or a number that is not on WhatsApp will never
            # succeed, and spending an hour retrying it delays every lead
            # behind it while the fallback channel sits unused.
            final = row["attempts"] >= 3 or is_permanent(error)
            conn.execute(
                "UPDATE outbox SET status=?, error=?, due_at=datetime('now','+20 minutes') "
                "WHERE id=?", ("failed" if final else "queued", error[:300], outbox_id))
            if final:
                _fallback(conn, row, error)
        conn.commit()
        return {"ok": True, "status": "sent" if ok else "failed"}
    finally:
        conn.close()


def release(outbox_id: int) -> dict:
    """Put a claimed message back exactly as it was.

    Used by --check and by the dry run. Reporting `ok: false` would have
    incremented the attempt counter and eventually marked a perfectly good
    message as failed — three checks and the queue quietly ate the lead.
    """
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM outbox WHERE id=?", (outbox_id,)).fetchone()
        if row is None:
            raise LookupError("no such message")
        if row["status"] == "claimed":
            conn.execute(
                "UPDATE outbox SET status='queued', claimed_at=NULL, "
                "attempts=MAX(attempts-1,0) WHERE id=?", (outbox_id,))
            conn.commit()
        return {"ok": True, "status": "queued"}
    finally:
        conn.close()


def replied(phone: str, optout: bool = False) -> dict:
    """A human answered. Stop everything still queued for that number.

    This is the one signal the sender can produce that the queue cannot infer:
    the moment a business writes back, the conversation belongs to Nima and
    any further automated message would be an intrusion. An opt-out says so
    explicitly and also stops the lead being picked up by a later research run.
    """
    digits = re.sub(r"\D", "", phone or "")
    if digits.startswith("00"):
        digits = digits[2:]
    if digits.startswith("0"):
        digits = digits[1:]
    if len(digits) < 8:
        raise ValueError("bad phone number")
    last10 = digits[-10:]

    status = "skip" if optout else "replied"
    conn = get_db()
    try:
        leads = conn.execute(
            "SELECT id FROM leads WHERE phone_e164=? OR phone_e164 LIKE ?",
            (digits, f"%{last10}")).fetchall()
        ids = [r["id"] for r in leads]
        if not ids:
            return {"ok": True, "leads": 0, "stopped": 0}
        marks = ",".join("?" * len(ids))
        conn.execute(f"UPDATE leads SET status=?, updated_at=datetime('now') "
                     f"WHERE id IN ({marks})", (status, *ids))
        cur = conn.execute(
            f"UPDATE outbox SET status='skipped', error=? "
            f"WHERE lead_id IN ({marks}) AND status IN ('queued','claimed')",
            ("opted out" if optout else "lead replied", *ids))
        conn.commit()
        if cur.rowcount:
            logger.info("lead %s replied — %d queued message(s) stopped",
                        digits, cur.rowcount)
        return {"ok": True, "leads": len(ids), "stopped": cur.rowcount}
    finally:
        conn.close()


# Failures that will still be failures in twenty minutes.
PERMANENT_SIGNS = (
    "not found", "no such", "does not exist", "not on whatsapp",
    "invalid user", "user_not_found", "unregistered", "blocked",
    "deactivated", "not a whatsapp number",
)


def is_permanent(error: str) -> bool:
    low = (error or "").lower()
    return any(sign in low for sign in PERMANENT_SIGNS)


def _fallback(conn, row, error: str) -> None:
    """A channel that failed for good is not the same as a lead you cannot reach.

    If Instagram will not take the message — no such account, DMs closed — the
    business may still have a mobile. Queue the other channel rather than
    dropping the lead. Only after a *final* failure, so a temporary glitch
    never produces two messages to the same business.
    """
    cfg = config()
    if not cfg["fallback"]:
        return
    lead = conn.execute("SELECT * FROM leads WHERE id=?", (row["lead_id"],)).fetchone()
    if lead is None or lead["status"] not in ("new", "contacted"):
        return
    other = channel_for(dict(lead), cfg, exclude=(row["channel"],))
    if not other:
        return
    to_addr = lead["instagram"] if other == "instagram" else lead["phone_e164"]
    if not to_addr:
        return
    body = row["body"]
    if other != row["channel"]:
        # Re-word for the channel it is actually going to.
        finding = research.Finding(lead["need"], 0, lead["need_fa"],
                                   lead["need_evidence_url"], lead["need_evidence"])
        if lead["need"]:
            body = research.compose(lead["name"], lead["domain"], lead["city"],
                                    finding, sender_signature(), channel=other)
    due = _next_due(conn, cfg, other)
    try:
        conn.execute(
            "INSERT INTO outbox(lead_id,channel,to_addr,body,need,due_at) "
            "VALUES(?,?,?,?,?,?)",
            (row["lead_id"], other, to_addr, body, row["need"],
             due.strftime("%Y-%m-%d %H:%M:%S")))
        logger.info("lead %s: %s failed (%s) -> queued on %s",
                    row["lead_id"], row["channel"], error[:60], other)
    except Exception:
        pass          # already queued there


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
        per_channel = {}
        senders = sender_status(conn, cfg)
        for ch in CHANNELS:
            per_channel[ch] = {
                "queued": conn.execute(
                    "SELECT COUNT(*) FROM outbox WHERE status='queued' AND channel=?",
                    (ch,)).fetchone()[0],
                "sent": conn.execute(
                    "SELECT COUNT(*) FROM outbox WHERE status='sent' AND channel=?",
                    (ch,)).fetchone()[0],
                "sent_today": sent_today(conn, ch),
                "cap": cap_for(cfg, ch),
                "enabled": ch in cfg["channels"],
                "live": senders[ch]["live"],
                "last_seen": senders[ch]["last_seen"],
            }
        return {
            "config": cfg,
            "channels": per_channel,
            "senders": senders,
            "quiet_now": in_quiet_hours(cfg),
            "local_time": local_now(cfg["tz_offset_min"]).strftime("%Y-%m-%d %H:%M"),
            "server_time": utc_now().strftime("%Y-%m-%d %H:%M") + " UTC",
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


def rebuild_queued() -> dict:
    """Recompose every queued message from its lead's stored need.

    The wording lives in research.py, so editing a template — or fixing how a
    name is written — leaves the already-queued bodies stale. Nothing is
    re-researched here; only the text is rebuilt from facts already on the lead.
    """
    sender = sender_signature()
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT o.id AS outbox_id, l.* FROM outbox o JOIN leads l ON l.id=o.lead_id "
            "WHERE o.status='queued' AND l.need<>''").fetchall()
        n = 0
        for r in rows:
            lead = dict(r)
            finding = research.Finding(lead["need"], 0, lead["need_fa"],
                                       lead["need_evidence_url"], lead["need_evidence"])
            body = research.compose(lead["name"], lead["domain"], lead["city"],
                                    finding, sender)
            conn.execute("UPDATE outbox SET body=? WHERE id=?",
                         (body, lead["outbox_id"]))
            if not lead["pitch_edited"]:
                conn.execute("UPDATE leads SET pitch=? WHERE id=?", (body, lead["id"]))
            n += 1
        conn.commit()
        return {"ok": True, "rebuilt": n}
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
