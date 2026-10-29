# Project Finder — how it works

A tool that finds businesses in Shiraz that need a website, works out what each
one is actually missing, writes a Persian message about that one thing, and
sends it on Instagram or WhatsApp. You handle the replies.

---

## The shape of it

```
   ┌──────────┐   ┌──────────┐   ┌─────────┐   ┌────────┐   ┌────────────┐
   │ DISCOVER │ → │ RESEARCH │ → │  SCORE  │ → │ WRITE  │ → │   OUTBOX   │
   └──────────┘   └──────────┘   └─────────┘   └────────┘   └─────┬──────┘
    OpenStreetMap  reads 6 pages   weights per   one need,         │
    free, no key   of their site   signal        one message       │
                                                            ┌─────┴─────┐
                                                            ▼           ▼
                                                      ┌──────────┐ ┌──────────┐
                                                      │ Instagram│ │ WhatsApp │
                                                      │  sender  │ │  sender  │
                                                      └──────────┘ └──────────┘
                                                         on YOUR PC, not the server
```

Three of these run on the website. The two senders run on your own machine,
because they drive your own logged-in accounts.

---

## 1. Discover — who exists

Asks OpenStreetMap for every business of the types you tick within N km of
Shiraz. Free, no account, no key.

One query **per category**, not one big one: a combined query is three times
the size and a busy Overpass server refuses it whole, losing the restaurants
because the hotel part made it too big. If a category fails you are told which.

The mirrors are chosen for two things — they must be reachable from
PythonAnywhere's allowlist, and they must carry the whole planet. A regional
mirror answers a question about Shiraz with "200 OK, zero results", which looks
exactly like "there are no cafés in Shiraz". An empty answer is now
cross-checked against another mirror before it is believed.

**What you get:** name, phone, Instagram handle, website, address, category.

## 2. Research — what do they need

This is the part that makes the messages worth sending.

For a business **with a website**, it reads up to six pages — homepage, menu,
booking, products, prices, contact — and checks what is missing. For one
**without**, the need comes from its trade and whether it runs on Instagram.

The rule that matters: **a need is category-specific.**

| Business | Missing online ordering | Verdict |
|---|---|---|
| Café | every order placed after closing is lost | **strong need** |
| Lawyer | nobody wants to order from a lawyer | **not a need** |

So a dentist gets *online appointment booking*, a café gets *menu and ordering*,
a guest house gets *reservation*, a furniture shop gets *a product catalogue*.
Same tool, different conclusion.

**Nothing is claimed without evidence.** Every need carries the URL and the
snippet that proved it. A need that cannot cite anything is dropped — a
confident message about a problem they do not have is worse than no message.

## 3. Score — is this worth your time

Deterministic weights over the signals found. No website is +40, an
Instagram-only business is +22 on top, a dead site is +45, a mobile number you
can actually reach is +12. Already having a good site is **−25**, and no way to
contact them at all is **−30**.

Above 70 is hot, 45–69 warm. Autopilot only touches leads above the threshold
you set (default 55).

## 4. Write — one thing, not five

Four lines, in this order:

1. **What I saw** — specific and checkable
2. **What it costs them** — concrete, not a benefit claim
3. **What I'd do** — named as a deliverable
4. **One question**

Opening with yourself is what everyone does and why most of these go unread, so
the first line is about them.

The channel changes the register, not the content:

**WhatsApp** — a note to a business, with your signature.

> سلام، وقت بخیر
> دیدم نوبت گرفتن از دکتر هانیه راز فقط تلفنی ممکن است.
> کسی که شب تصمیم می‌گیرد نوبت بگیرد تا صبح منتظر می‌ماند…
> نیما زارع | nimabuilds.pythonanywhere.com

**Instagram** — shorter, says you were on their page, **no signature**. A DM
from a stranger lands in Message Requests next to real spam, and a signature
block is exactly what makes it look forwarded.

> سلام 👋
> صفحه‌تون رو دیدم. برای نوبت گرفتن راهی جز تماس یا دایرکت نیست.
> …
> اگر خواستید یک نمونه بفرستم؟

## 5. Outbox — where the safety lives

The senders are deliberately the dumbest part of the system. They ask "is there
a message I may send?", send it, report back, sleep. **Every rule about *when*
lives in the queue**, so running a sender twice cannot double your rate and a
crash cannot replay a burst.

- **One message per lead per channel, ever** — enforced by the database.
- **Scheduled send times with jitter**, written down in advance. A perfectly
  regular interval is a bot signature.
- **A daily cap counted from rows actually sent today**, not from what the
  sender remembers.
- **Quiet hours** — the schedule walks forward past them rather than queueing
  into the night.
- **Stop on reply.** The moment someone answers, nothing further goes to them.
- **Claims expire**, so a sender that dies mid-send does not strand a message.
- **A kill switch** re-read on every claim.

### Channel order

Instagram is tried first, WhatsApp second. A business that runs on Instagram
reads its DMs; an unexpected WhatsApp message from a stranger is an
interruption on a personal phone.

**Live senders win.** Every sender checks in when it claims a message, and the
server remembers the last time each channel was seen (45 minutes). A message is
only handed to a channel that is actually running, so if you only start the
WhatsApp sender, everything goes to WhatsApp instead of piling up on an
Instagram channel nobody is watching. When both are running, the documented
Instagram-first order is preserved.

A message already parked on a channel whose sender has gone quiet is adopted by
the next live sender and re-worded for that channel. Nothing gets stranded.

If a channel fails **permanently** — no such account, not a WhatsApp number —
the lead falls back to the other channel, re-worded for it. Permanent failures
fail immediately rather than burning three retries over an hour.

---

## Running it

### On the website

1. **Project Finder → Find businesses.** Pick categories, radius, city.
2. **Research & queue messages.** Reads sites, decides needs, queues one message
   per lead on the best channel.
3. **Show outbox** and read ten of them. *This is the step that decides whether
   any of this works.* A specific claim that is wrong is worse than a generic one.
4. **Autopilot on** when you are satisfied.

### On your PC

Both senders live in `tools/`. Each needs the agent key, and the panel now hands
you the whole file: **Autopilot → Sender setup → Download config.json**, then
drop it into the sender's folder. Typing the key by hand is where this used to
fail — a placeholder left in place looks exactly like a queue that sends nothing.
A sender still holding the placeholder refuses to start and says so.

```powershell
cd C:\Users\nima1\OneDrive\Desktop\WEB\tools\whatsapp-sender
npm install
npm run check   # proves everything except WhatsApp (reads the queue, claims nothing)
npm start       # dry run: prints exactly what it would send, sends nothing
npm run send    # the real thing — scan the QR once
```

`check` and a plain `start` never take a message out of the queue, so you can run
them as often as you like without losing anything. `npm run send` is the only
command that talks to real people; you can also make that permanent by setting
`"dryRun": false` in `config.json`.

Both senders refuse to run against a server that does not understand `peek` —
an older build would treat that check as a real claim and quietly mark the queue
as sent.

If WhatsApp accepts a message but the report back to the server fails, the sender
keeps that report on disk and retries it before asking for the next message. The
claim would otherwise expire and the same text would go to the same business a
second time.

```powershell
cd C:\Users\nima1\OneDrive\Desktop\WEB\tools\instagram-sender
pip install -r requirements.txt
copy config.example.json config.json   # + igUsername / igPassword
python sender.py --check
python sender.py --send
```

Both default to `dryRun: true`. Leave it there until the messages read right.

### If you are behind a proxy

You are — V2Ray on `127.0.0.1:10808`. Node and Python both ignore the system
proxy by default, so they connect directly, and PythonAnywhere answers **451**
to an Iranian IP while your browser sees a working site. Both senders detect the
proxy and route through it. If you ever see 451, that is what it means — not a
bad key.

The research run is the opposite problem. Many Iranian business sites refuse
addresses outside Iran, so a request that leaves through a VPN exit is refused
with 403/451/52x — and a crawler that treats any error status as proof would
then tell that business its website is down. Two things prevent it:

* `fetch_site()` retries any refused or failed request **with no proxy at all**
  before believing it, so a site that only answers inside Iran is still read.
* A refusal is recorded as "could not verify", never as "the site is dead".
  Only a real error page (`404`, `410`, `500`…) counts as proof.

Messages already queued with a "your site is down" claim can be re-derived:
**Autopilot → Re-check "site is down" messages**. Working sites get a true
message instead, sites we cannot verify have the message dropped, and genuinely
broken sites keep theirs.

---

## The honest part

Both senders automate accounts in ways the platforms forbid.

**WhatsApp** — automating WhatsApp Web is against its terms. Unsolicited bulk
messaging is what gets numbers permanently banned. **Use a second SIM**, never
the number your clients already use.

**Instagram is worse.** It action-blocks before it bans — "please wait a few
minutes" is a warning, and the sender treats it as a stop for the day rather
than something to retry, because retrying through it is how a temporary block
becomes permanent. DMs to non-followers land in Message Requests, so the reply
rate will be lower than WhatsApp. **Do not raise the cap to compensate** —
that is the move that gets the account restricted. Defaults are 12 a day, seven
minutes apart, on purpose.

Nothing here makes automated cold outreach safe. It makes it slower and more
careful than the naive version, which is a different thing.

If people start blocking or reporting you, the message is wrong. Stop and
change it — no cap saves an account that people report.

---

## Where things live

| Path | What |
|---|---|
| `app/finder.py` | discovery, site profiling, scoring |
| `app/research.py` | needs per category, message wording |
| `app/autopilot.py` | outbox, pacing, the sender protocol |
| `tools/whatsapp-sender/` | Node sender, runs on your PC |
| `tools/instagram-sender/` | Python sender, runs on your PC |

Change the wording in `app/research.py` (`OPENERS`, `COSTS`, `OFFERS`,
`IG_OPENERS`), then press **Rewrite queued** in the panel to apply it to
messages already in the queue.
