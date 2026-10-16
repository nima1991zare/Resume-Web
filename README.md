# Nima — Portfolio Website

Cinematic scroll-morphing portfolio / resume website. A persistent 3D particle background morphs into a different formation for every section as you scroll (nebula → DNA helix → data grid → globe → orbit rings → vortex). Bilingual EN/Persian (RTL/LTR), PWA-capable, with a full admin panel.

## Stack

- **Backend:** Python · FastAPI · SQLite (zero-setup, easy migration to PostgreSQL/MySQL later)
- **Frontend:** Vanilla HTML/CSS/JS (no framework — fastest possible load)
- **PWA:** manifest + service worker (installable, offline shell)

## Run

```bash
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

- Public site: http://localhost:8000
- Admin panel: http://localhost:8000/admin
  - Default login: `admin` / `admin123` — **change the password from Settings immediately.**

## Features

| Area | Details |
|------|---------|
| Background | One persistent 3D particle system that morphs per section on scroll, with color transitions and a side phase-rail |
| Hero | Mega editorial typography (gradient + outline), skill marquee, scroll progress bar, film-grain + vignette |
| About (1) | Bilingual description, editable from admin |
| Applications (2) | Buyable apps with price, currency, tech tags, images — full CRUD + price editing in admin |
| Telegram bots (3) | Bot projects with interactive demos, source links and full CRUD in admin |
| Brands (3) | Logos/names of brands worked with — CRUD in admin |
| Websites (4) | Sample sites with live URL or "order similar" CTA — CRUD in admin |
| Contact | Form saved to DB + phone/email/Telegram/GitHub/LinkedIn channels |
| Admin | Login (PBKDF2-hashed password, session tokens), dashboard with visit analytics (total/today/7-day/30-day chart/by-language), message inbox, image uploads, settings, password change |
| Project Finder | Finds local businesses that need a website, scores them, drafts a Persian WhatsApp pitch — see below |
| i18n | EN ⇄ فارسی switch, automatic `dir="rtl"`/`ltr`, Vazirmatn font for Persian |
| Responsive | Mobile-first, tested breakpoints 375 / 768 / 1024 / 1440 |
| PWA | Installable web app, offline shell caching, never caches API/admin |
| Performance | No JS frameworks; canvas animation is rAF-based, pauses on hidden tab, respects `prefers-reduced-motion` |

## Structure

```
app/
  main.py        FastAPI app — API routes, admin API, page serving
  database.py    SQLite schema, seed data, password hashing
  finder.py      Project Finder — OSM discovery, site profiling, scoring, Persian pitches
static/
  index.html     Public site
  admin.html     Admin panel
  css/           style.css (public) · admin.css
  js/            app.js · i18n.js · morph.js · admin.js
  icons/         favicon + PWA icons
  uploads/       Admin-uploaded images
data/site.db     SQLite database (created on first run)
```

## Project Finder

Lead generation for freelance **projects** — it looks for businesses to sell a
website to, not jobs to apply for. Adapted from
[Harvey](https://github.com/ethanplusai/harvey), an autonomous sales agent, with
its email channel replaced by WhatsApp: OSM almost never holds an email for an
Iranian SMB, and Gmail's API is unreachable from Iran anyway.

Open **Project Finder** in the admin panel and press **Find businesses**.

### The pipeline

| Stage | What it does | Cost |
|---|---|---|
| **Discover** | OpenStreetMap (Overpass) — every business of the chosen types within N km of your city | free, no account |
| **Profile** | 3 HTTP requests per site that has one: is it up, mobile-friendly, HTTPS, stale, on a page builder, bookable | free, no model calls |
| **Score** | Deterministic weights over the signals found → 0–100 and hot / warm / cold | free |
| **Pitch** | A Persian message naming the specific gap, plus a `wa.me` link with it pre-filled | free |

**Nothing is ever sent.** There is no sending code. Every lead ends as a draft
you read, edit and send yourself — deliberately, because bulk-messaging local
businesses would burn the number the whole thing depends on.

Two ways out, because one is never enough: **WhatsApp** when the listing has a
mobile (a `wa.me` link with the pitch pre-filled), and **Instagram DM** when it
does not — plenty of Shiraz businesses list only a landline, or a mobile that
turns out not to be on WhatsApp, while their Instagram is plainly active.
Instagram cannot pre-fill a message from a URL (no one can, it isn't a feature),
so that button copies the pitch and opens the thread; the paste is one keystroke.
The **Instagram only** filter and stat card isolate exactly that pile.

### What makes a lead good

Weights live in `SIGNALS` in `app/finder.py`; edit them and the next run re-scores.

- `NO_WEBSITE` (+40) — on the map with a phone and no site. The highest-intent
  signal there is when you sell websites.
- `INSTAGRAM_ONLY` (+22) — running the business off Instagram. The strongest
  pitch in Iran: one filtering and their only channel is gone.
- `SITE_DEAD` (+45) — the server answered with an error. Proof.
- `SITE_UNREACHABLE` (+18) — *we* could not reach it, which may be your
  connection. Scored lower and pitched as a question, never as a claim.
- `PHONE_MOBILE` (+12) — a 09xx number, so WhatsApp actually works.
- `NO_CONTACT` (−30) / `SITE_MODERN` (−25) — no way to reach them, or they
  already have a good site. Not a lead.

### Notes

- **Overpass is free volunteer infrastructure.** It returns "at capacity" often.
  The finder queries one category at a time and retries with backoff, so a busy
  moment costs one category rather than the whole run — and it says which
  category failed instead of quietly reporting fewer businesses.
- **Re-running is safe.** The OSM id is the identity, so a second run updates
  facts and re-scores, but never duplicates a lead and never overwrites a status,
  a note, or a message you edited by hand.
- **Signals are rows, not columns** (`lead_signals`), so a new signal needs no
  migration and the evidence URL that proved a claim is stored with the claim.
- City, radius, business types and the name that signs your messages are all set
  in the panel (the signature lives in **Settings → Project Finder**).

## Security

| Layer | Protection |
|-------|-----------|
| Passwords | PBKDF2-HMAC-SHA256, 200,000 iterations, per-password salt, constant-time comparison |
| Sessions | 32-byte random Bearer tokens, stored **SHA-256 hashed** in DB, 7-day expiry, revoked on logout/password change |
| Brute force | Login rate-limited: 5 attempts / 15 min / IP (HTTP 429) |
| Spam/flood | Contact form 5 / 10 min / IP · visit tracking 30 / hour / IP · uploads 30 / hour |
| SQL injection | All queries parameterized; table names validated against a whitelist |
| XSS | All user/admin content HTML-escaped in both frontends; strict CSP (`script-src 'self'`, no inline scripts) |
| Uploads | Admin-only, extension whitelist (**SVG banned** — script-injection vector), magic-byte content validation, 5 MB cap, random filenames |
| Headers | CSP, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy`, `Permissions-Policy`, `Cross-Origin-Opener-Policy` |
| CSRF | Not applicable — no cookies; auth via Bearer token in header |
| DoS | 6 MB global request body cap; streamed uploads with size enforcement |
| Caching | `Cache-Control: no-store` on all API responses; service worker never caches `/api/` or `/admin` |
| Info leak | Swagger/OpenAPI docs disabled; generic error messages; admin page `noindex` |
| Misc | Admin dashboard shows a red warning until the default password is changed |

## Production notes

- **Change the default admin password immediately** (the dashboard warns until you do).
- Run behind HTTPS (required for PWA install + service worker on a domain). With HTTPS, also add HSTS at the reverse proxy: `Strict-Transport-Security: max-age=31536000`.
- Suggested: `uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-server-header` behind Nginx/Caddy reverse proxy.
- The rate limiter is in-memory (per process) — run a single worker, or move limits to the proxy for multi-worker setups.
- Back up `data/site.db` and `static/uploads/`.
