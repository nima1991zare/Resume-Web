"""Project Finder — finds local businesses that need a website, so you can sell them one.

This is lead generation for freelance *projects*, not a job search. It looks for
businesses that already exist, already have customers, and visibly lack the thing
you build. The method is borrowed from Harvey (github.com/ethanplusai/harvey) and
adapted for Shiraz:

  DISCOVER  which businesses exist here          (OpenStreetMap / Overpass — free)
  PROFILE   what their web presence actually is  (3 HTTP requests, no model calls)
  SCORE     how good a prospect that makes them  (deterministic weights)
  PITCH     a Persian message naming the real gap (templates, no model calls)

Two principles are kept from Harvey and they are the ones that matter:

* **Every fact is a row, never a column.** A signal lands in `lead_signals`, so a
  new signal needs no migration, history is free, and the evidence for a claim
  travels with the claim. A pitch that says "your site has no HTTPS" can point at
  the URL that proved it.
* **Nothing goes out without you.** Harvey holds email in an outbox for approval.
  Here it goes further: there is no sending at all. Every lead produces a drafted
  Persian message and a wa.me link; you read it, edit it, and press send yourself.
  That is deliberate — unsolicited bulk messaging to Iranian SMBs would burn the
  phone number this all depends on.

What was deliberately dropped from Harvey: email as a channel (OSM almost never
carries an email for a Shiraz business, and Gmail's API is unreachable from Iran),
and the model-written copy (the `claude` CLI cannot run on the deploy host).
"""
from __future__ import annotations

import asyncio
import ipaddress
import json
import logging
import os
import re
import socket
import threading
import time
from dataclasses import dataclass, field
from urllib.parse import urlparse, quote

import httpx

from .database import get_db, get_setting

logger = logging.getLogger("finder")

UA = "NimaPortfolio-ProjectFinder/1.0 (+https://github.com/nima1991zare; local business research)"
TIMEOUT = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0)


# ── outbound network ──────────────────────────────────────────────────
# PythonAnywhere (where the live site runs) allows no direct outbound
# connections: everything goes through a proxy. Consoles get `http_proxy` and
# `https_proxy` in their environment, so a hand-run test there succeeds — but
# the web app process does not get them, so the same code inside the running
# site fails with "All connection attempts failed". Trusting the environment
# alone therefore works exactly where you test it and nowhere that matters.
#
# The proxy hostname only resolves on hosts that actually have one, which makes
# resolution a cheap and precise test for "am I somewhere that requires it"
# — no environment sniffing, no wasted HTTP request, and a no-op on a laptop.
PROXY_HOST = "proxy.server"
PROXY_URL = f"http://{PROXY_HOST}:3128"


def proxy_url() -> str | None:
    """The proxy this machine needs, or None to connect directly."""
    if any(os.environ.get(k) for k in
           ("https_proxy", "HTTPS_PROXY", "http_proxy", "HTTP_PROXY")):
        return None          # httpx reads these itself (trust_env)
    try:
        socket.gethostbyname(PROXY_HOST)
    except OSError:
        return None          # no such proxy here — direct is correct
    logger.info("routing outbound traffic through %s", PROXY_URL)
    return PROXY_URL


def new_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=TIMEOUT, proxy=proxy_url())


# ─────────────────────────────────────────────────────── categories
# Harvey's OSM provider ships 9 US trades (roofer, plumber, HVAC…). None of them
# describe a Shiraz high street, and its code deliberately refuses to fall back to
# a catch-all — so the map has to be rebuilt for this market rather than extended.
#
# Chosen for one reason: these are businesses that live or die on walk-in and
# phone custom, so a website is a revenue argument rather than a vanity one.
CATEGORIES: list[dict] = [
    {"key": "food",      "fa": "رستوران و کافه",      "en": "Restaurants & cafés",
     "tags": ["amenity=restaurant", "amenity=cafe", "amenity=fast_food", "amenity=ice_cream"]},
    {"key": "bakery",    "fa": "نان و شیرینی",          "en": "Bakeries & confectionery",
     "tags": ["shop=bakery", "shop=confectionery", "shop=pastry", "shop=chocolate"]},
    {"key": "dental",    "fa": "دندان‌پزشکی",           "en": "Dental clinics",
     "tags": ["amenity=dentist"]},
    {"key": "medical",   "fa": "پزشک و کلینیک",         "en": "Doctors & clinics",
     "tags": ["amenity=clinic", "amenity=doctors", "healthcare=laboratory",
              "amenity=veterinary", "shop=optician", "healthcare=physiotherapist"]},
    {"key": "pharmacy",  "fa": "داروخانه",              "en": "Pharmacies",
     "tags": ["amenity=pharmacy"]},
    {"key": "beauty",    "fa": "آرایشگاه و سالن زیبایی", "en": "Salons & beauty",
     "tags": ["shop=beauty", "shop=hairdresser", "shop=massage", "shop=tattoo"]},
    {"key": "fitness",   "fa": "باشگاه ورزشی",          "en": "Gyms & fitness",
     "tags": ["leisure=fitness_centre", "leisure=sports_centre", "shop=sports"]},
    {"key": "hotel",     "fa": "هتل و اقامتگاه",        "en": "Hotels & guest houses",
     "tags": ["tourism=hotel", "tourism=guest_house", "tourism=hostel", "tourism=apartment"]},
    {"key": "travel",    "fa": "آژانس مسافرتی",         "en": "Travel agencies",
     "tags": ["office=travel_agent", "shop=travel_agency"]},
    {"key": "furniture", "fa": "مبلمان و دکوراسیون",    "en": "Furniture & decor",
     "tags": ["shop=furniture", "shop=interior_decoration", "shop=carpet",
              "shop=kitchen", "shop=curtain", "shop=lighting"]},
    {"key": "fashion",   "fa": "پوشاک و طلا",           "en": "Clothing & jewellery",
     "tags": ["shop=clothes", "shop=shoes", "shop=jewelry", "shop=bag",
              "shop=boutique", "shop=watches"]},
    {"key": "tech",      "fa": "موبایل و کامپیوتر",      "en": "Mobile & computer shops",
     "tags": ["shop=mobile_phone", "shop=computer", "shop=electronics",
              "shop=hifi", "shop=camera"]},
    {"key": "auto",      "fa": "خودرو و تعمیرگاه",       "en": "Car dealers & repair",
     "tags": ["shop=car", "shop=car_repair", "shop=car_parts", "shop=tyres",
              "shop=motorcycle"]},
    {"key": "realestate", "fa": "املاک",                "en": "Real estate agents",
     "tags": ["office=estate_agent"]},
    {"key": "pro",       "fa": "خدمات تخصصی و شرکت‌ها",  "en": "Professional services",
     "tags": ["office=lawyer", "office=accountant", "office=insurance",
              "office=company", "office=architect", "office=engineer",
              "office=advertising_agency", "office=it"]},
    {"key": "education", "fa": "آموزشگاه",              "en": "Schools & academies",
     "tags": ["amenity=language_school", "amenity=driving_school",
              "amenity=music_school", "amenity=prep_school"]},
    {"key": "retail",    "fa": "سوپرمارکت و خرده‌فروشی", "en": "Supermarkets & retail",
     "tags": ["shop=supermarket", "shop=greengrocer", "shop=butcher",
              "shop=florist", "shop=toys", "shop=stationery", "shop=books",
              "shop=hardware", "shop=photo", "shop=copyshop", "shop=gift"]},
]

CATEGORY_KEYS = {c["key"] for c in CATEGORIES}
CATEGORY_FA = {c["key"]: c["fa"] for c in CATEGORIES}
# Default: the categories where "no website" most reliably means lost money.
DEFAULT_CATEGORIES = ["food", "dental", "medical", "beauty", "fitness",
                      "hotel", "furniture", "fashion", "travel"]


# ─────────────────────────────────────────────────────── signals
# code -> (weight, persian label, english label)
# Positive weight = a reason to pitch them. Negative = a reason not to bother.
SIGNALS: dict[str, tuple[int, str, str]] = {
    # ── the gap you sell into
    "NO_WEBSITE":        (40, "وبسایت ندارد", "No website at all"),
    "INSTAGRAM_ONLY":    (22, "فقط اینستاگرام دارد", "Instagram-only presence"),
    "SITE_DEAD":         (45, "سایت باز نمی‌شود", "Website is down (server answered with an error)"),
    "SITE_UNREACHABLE":  (18, "سایت در دسترس نبود (دستی بررسی شود)",
                          "Could not be reached — may be your network, check by hand"),
    "SITE_NOT_MOBILE":   (25, "سایت موبایل‌پسند نیست", "Not mobile-friendly"),
    "SITE_NO_HTTPS":     (15, "سایت HTTPS ندارد", "No HTTPS — browsers warn visitors"),
    "SITE_STALE":        (18, "سایت سال‌ها به‌روز نشده", "Site not updated in years"),
    "SITE_BUILDER":      (10, "سایت روی قالب آماده", "Built on a page builder"),
    "SITE_NO_SCHEMA":     (5, "بدون داده ساختاریافته (SEO)", "No schema markup"),
    "SITE_NO_BOOKING":    (8, "بدون رزرو/سفارش آنلاین", "No online booking or ordering"),
    "SITE_SLOW":         (10, "سایت کند است", "Slow homepage"),
    # ── can you actually reach them
    "PHONE_MOBILE":      (12, "موبایل دارد (واتساپ)", "Mobile number — WhatsApp works"),
    "PHONE_LANDLINE":     (5, "تلفن ثابت دارد", "Landline only"),
    "HAS_INSTAGRAM":      (6, "اینستاگرام دارد", "Has Instagram"),
    "NO_CONTACT":       (-30, "راه تماسی ندارد", "No way to contact them"),
    # ── reasons to walk away
    "SITE_MODERN":      (-25, "سایت خوبی دارد", "Already has a solid modern site"),
}

TIER_HOT, TIER_WARM, TIER_COLD = "hot", "warm", "cold"


def tier_for(score: int) -> str:
    if score >= 70:
        return TIER_HOT
    if score >= 45:
        return TIER_WARM
    return TIER_COLD


# ─────────────────────────────────────────────────────── phones
# OSM carries Iranian numbers in every shape: "+98 71 3234 5678", "071-32345678",
# "09171234567", "+989171234567", sometimes two numbers in one field. WhatsApp only
# answers on mobiles, so the landline/mobile split decides which button the panel
# can even offer — getting it wrong means a dead link on the lead you cared about.
_PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def normalize_phone(raw: str) -> tuple[str, bool]:
    """-> (E.164 digits without '+', is_mobile). ('', False) when unusable."""
    if not raw:
        return "", False
    # Multiple numbers arrive separated by ; or , — take the first usable one.
    for part in re.split(r"[;,/]| or ", raw.translate(_PERSIAN_DIGITS)):
        d = re.sub(r"\D", "", part)
        if not d:
            continue
        if d.startswith("0098"):
            d = d[4:]
        elif d.startswith("98") and len(d) >= 11:
            d = d[2:]
        elif d.startswith("0"):
            d = d[1:]
        if not (9 <= len(d) <= 10):
            continue
        # Iranian mobiles are 9xx + 7 digits; everything else is a landline.
        return "98" + d, d.startswith("9") and len(d) == 10
    return "", False


def wa_link(phone_e164: str, message: str) -> str:
    """A click-to-chat link with the pitch pre-filled. Mobiles only."""
    if not phone_e164:
        return ""
    return f"https://wa.me/{phone_e164}?text={quote(message)}"


def ig_link(handle: str) -> str:
    """A link that opens the DM thread with this account.

    Instagram has no equivalent of wa.me's `?text=` — a message cannot be
    pre-filled by URL, by anyone, at all. So the panel copies the pitch to the
    clipboard and opens the thread; the paste is the one manual step, and
    pretending otherwise would just produce an empty DM box.

    This matters more than it sounds: plenty of Shiraz businesses list a mobile
    that turns out not to be on WhatsApp, and Instagram is where they actually
    answer.
    """
    return f"https://ig.me/m/{handle}" if handle else ""


# ─────────────────────────────────────────────────────── domains
JUNK_DOMAIN_PATTERNS = tuple(re.compile(p, re.I) for p in (
    # Social and directory links get tagged as `website` on OSM constantly. A
    # business whose "website" is its Instagram page has no website — that is the
    # single most valuable fact this whole module produces, so it must not be lost
    # to a sloppy domain check.
    r"(^|\.)(instagram|facebook|telegram|whatsapp|t\.me|twitter|x|linkedin)\.",
    r"(^|\.)(youtube|tiktok|pinterest|aparat|virgool)\.",
    r"(^|\.)(google|goo\.gl|maps\.app|balad|neshan|waze)\.",
    r"(^|\.)(wikipedia|wikimapia|foursquare|tripadvisor|yelp)\.",
    r"(^|\.)(eghamat24|snapptrip|alibaba\.ir|jabama|otaghak)\.",   # OTA listings
    r"(^|\.)(digikala|basalam|torob|emalls)\.",                    # marketplaces
    r"(^|\.)(linktr\.ee|zil\.ink|bio\.link|yek\.link)\.?",         # link-in-bio
))


def normalize_domain(url_or_domain: str) -> str:
    if not url_or_domain:
        return ""
    raw = url_or_domain.strip().lower()
    if "://" not in raw:
        raw = "http://" + raw
    host = (urlparse(raw).hostname or "").strip(".")
    return host[4:] if host.startswith("www.") else host


def is_real_website(url: str) -> bool:
    """False for social links, directories and bare IPs masquerading as a site."""
    d = normalize_domain(url)
    if not d or "." not in d or re.fullmatch(r"[\d.]+", d):
        return False
    return not any(p.search(d) for p in JUNK_DOMAIN_PATTERNS)


def instagram_handle(value: str) -> str:
    """Accepts a handle, a URL, or '@handle'. Returns a bare handle."""
    v = (value or "").strip()
    if not v:
        return ""
    if "instagram.com" in v.lower():
        path = urlparse(v if "://" in v else "https://" + v).path
        v = path.strip("/").split("/")[0]
    v = v.lstrip("@").strip()
    return v if re.fullmatch(r"[A-Za-z0-9._]{1,40}", v) else ""


def clean_name(raw: str) -> str:
    """The business name as it should be used to address them.

    OSM often holds a bilingual name in one field —
    "هتل بین‌المللی پارسه,Shiraz International Parseh Hotel" — and pasting that
    whole string into a Persian greeting reads like a database leak. When one
    half is Persian, that half is the name.
    """
    name = (raw or "").strip()
    if "," not in name and "/" not in name:
        return name
    parts = [x.strip() for x in re.split(r"[,/]", name) if x.strip()]
    persian = [x for x in parts if re.search(r"[؀-ۿ]", x)]
    return (persian[0] if persian else parts[0] if parts else name)


def _is_public_host(host: str) -> bool:
    """Profiling fetches URLs that came from third-party map data, so the
    resolved address has to be checked before the request — otherwise an OSM
    `website=http://169.254.169.254/…` turns an admin button into an SSRF."""
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return False
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            return False
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
            return False
    return True


# ─────────────────────────────────────────────────────── discover
NOMINATIM = "https://nominatim.openstreetmap.org/search"
# Two things had to be true of every mirror here, and they are not the same
# thing:
#
# 1. It is on PythonAnywhere's outbound allowlist, because that is what the live
#    site runs on and an un-allowlisted host is simply unreachable from there,
#    however healthy it is. (https://www.pythonanywhere.com/whitelist/)
# 2. It actually carries the whole planet. Several public Overpass instances are
#    regional — overpass.osm.ch is allowlisted, healthy, and answers a query
#    about Shiraz with HTTP 200 and zero results, because it only holds
#    Switzerland. That is the worst possible failure: it is indistinguishable
#    from "there are no pharmacies in Shiraz" unless you go looking.
#
# Each of these three was probed with a known-good Shiraz query and returned
# real results. The empty-result cross-check in overpass() below is the backstop
# in case that ever stops being true.
OVERPASS_ENDPOINTS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.fr/api/interpreter",
)
OVERPASS_BACKOFF = 8.0
OVERPASS_ROUNDS = 3          # 3 passes over 5 mirrors, backing off between
OVERPASS_INTERVAL = 2.0      # between per-category queries: modest volume, no parallelism


@dataclass
class Business:
    osm_id: str
    name: str
    category: str
    osm_category: str = ""
    phone: str = ""
    website: str = ""
    instagram: str = ""
    telegram: str = ""
    email: str = ""
    address: str = ""
    city: str = ""
    lat: float | None = None
    lon: float | None = None


async def geocode_city(client: httpx.AsyncClient, city: str) -> tuple[float, float, str] | None:
    """'Shiraz, Iran' -> (29.606, 52.5378, 'شیراز').

    The third value is the place's own name as Nominatim holds it, and it is the
    reason this returns three things instead of two: the city is typed in Latin
    ("Shiraz, Iran") but it gets written into a Persian sentence, and
    «کسب‌وکارهای Shiraz, Iran» reads like a mail-merge accident. Nominatim
    already knows the local name, so use it.

    Cached in settings forever: Nominatim permits single place lookups, not
    repeated bulk ones.
    """
    key = f"finder_geo:{city.strip().lower()}"
    conn = get_db()
    try:
        cached = get_setting(conn, key)
    finally:
        conn.close()
    if cached:
        try:
            c = json.loads(cached)
            return float(c["lat"]), float(c["lon"]), c.get("name") or city
        except (ValueError, KeyError, TypeError):
            pass        # pre-JSON cache entry — look it up again

    r = await client.get(NOMINATIM, params={"q": city, "format": "json", "limit": 1},
                         headers={"User-Agent": UA})
    r.raise_for_status()
    rows = r.json()
    if not rows:
        return None
    lat, lon = float(rows[0]["lat"]), float(rows[0]["lon"])
    local = (rows[0].get("name") or "").strip() or city
    conn = get_db()
    try:
        conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)",
                     (key, json.dumps({"lat": lat, "lon": lon, "name": local},
                                      ensure_ascii=False)))
        conn.commit()
    finally:
        conn.close()
    return lat, lon, local


async def overpass(client: httpx.AsyncClient, body: str,
                   note=None) -> dict:
    """Walk the public mirrors, several rounds, then raise.

    A single pass over the mirrors is not enough. The main instance answers "at
    capacity" with a 502 and tells you in the body to retry with exponential
    backoff — which is a queue being full, not a server being down, and it clears
    within a minute or two. Walking past it once turns a busy moment into an
    empty result.

    And it must raise rather than return []: "every mirror is busy" would
    otherwise look identical to "this city has no businesses in it", which is the
    one failure mode that silently wastes an afternoon.
    """
    last = ""
    delay = OVERPASS_BACKOFF
    # "busy" and "blocked" need different advice, so count which is happening.
    blocked = 0
    attempts = 0
    empty = None        # an unconfirmed "no results here", pending a second opinion
    for round_no in range(OVERPASS_ROUNDS):
        for endpoint in OVERPASS_ENDPOINTS:
            attempts += 1
            try:
                r = await client.post(endpoint, content=body.encode(),
                                      headers={"User-Agent": UA})
            except httpx.HTTPError as e:
                blocked += 1
                last = f"{endpoint}: unreachable ({e})"
                logger.warning("overpass %s", last)
                continue
            if r.status_code == 200:
                try:
                    data = r.json()
                except json.JSONDecodeError:
                    last = f"{endpoint}: 200 but not JSON"
                    logger.warning("overpass %s", last)
                    continue
                if data.get("elements"):
                    return data
                # A successful but empty answer is not yet believed: a regional
                # mirror returns exactly this for a city it does not hold. Keep
                # it, try the others, and only accept "nothing here" if no
                # mirror can produce anything.
                empty = data
                last = f"{endpoint}: 200 but empty"
                logger.info("overpass %s — cross-checking another mirror", last)
                continue
            # A proxy refusing the host looks like 403/407, not a busy queue.
            if r.status_code in (401, 403, 407):
                blocked += 1
            last = f"{endpoint}: HTTP {r.status_code}"
            logger.warning("overpass %s (round %d)", last, round_no + 1)
        if round_no < OVERPASS_ROUNDS - 1:
            # Say so in the UI: a silent minute looks like a hang.
            if note:
                note(f"سرورهای نقشه شلوغ‌اند — تلاش {round_no + 2} از "
                     f"{OVERPASS_ROUNDS}…")
            await asyncio.sleep(delay)
            delay *= 2          # 8s, 16s, 32s — the queue usually drains by then
    if empty is not None:
        # Every reachable mirror agreed there is nothing here. Now it is a fact
        # about the map rather than a fact about one mirror.
        return empty
    if blocked == attempts:
        # Never once got a reply. On a host that whitelists outbound traffic
        # (PythonAnywhere's free tier does) this is the normal outcome, and
        # telling him to "wait a few minutes" would waste his afternoon.
        raise RuntimeError(
            "به سرورهای OpenStreetMap اصلاً دسترسی نبود. اگر سایت روی هاست "
            "اشتراکی اجرا می‌شود، احتمالاً اینترنت خروجی محدود است (مثلاً "
            "PythonAnywhere رایگان فقط دامنه‌های مجاز را باز می‌کند). "
            f"جست‌وجو را روی کامپیوتر خودتان اجرا کنید. ({last})")
    raise RuntimeError(
        "سرورهای OpenStreetMap پاسخ ندادند (شلوغ هستند). این سرویس رایگان و "
        f"داوطلبانه است — چند دقیقه بعد دوباره تلاش کنید. ({last})")


async def discover(client: httpx.AsyncClient, city: str, cat_keys: list[str],
                   radius_km: int, limit: int, note=None) -> tuple[list[Business], list[str]]:
    """-> (businesses, names of categories that failed).

    One query per category, not one query for all of them. A single combined
    query is three times the size and gets refused by a busy Overpass instance as
    a unit — so a hundred restaurants are lost because the hotel clauses made the
    request too big. Per-category queries are small enough to get served, and a
    category that still fails costs only itself.
    """
    try:
        coords = await geocode_city(client, city)
    except httpx.HTTPError as e:
        # The first outbound call of a run, so it is where a blocked network
        # shows up — and a bare "All connection attempts failed" tells nobody
        # what to do about it.
        raise RuntimeError(
            "اتصال به اینترنت برقرار نشد (جست‌وجوی مختصات شهر شکست خورد). "
            "اگر سایت روی هاست اشتراکی اجرا می‌شود، ترافیک خروجی باید از پراکسی "
            f"عبور کند. ({type(e).__name__})") from e
    if not coords:
        raise RuntimeError(f"شهر «{city}» روی نقشه پیدا نشد.")
    lat, lon, city_local = coords
    radius_m = int(max(1, min(radius_km, 60)) * 1000)

    chosen = [c for c in CATEGORIES if c["key"] in set(cat_keys)] or CATEGORIES
    per_cat = max(40, int(limit) // max(1, len(chosen)))

    elements: list[tuple[dict, str]] = []
    failed: list[str] = []
    first_error = ""
    for i, cat in enumerate(chosen):
        if i:
            await asyncio.sleep(OVERPASS_INTERVAL)   # community rate etiquette
        if note:
            note(f"جست‌وجوی «{cat['fa']}» ({i + 1} از {len(chosen)})…")
        # `nwr` matches nodes, ways and relations in one clause — a third of the
        # query size of spelling each out.
        clauses = "".join(
            f'nwr[{tag.partition("=")[0]}={tag.partition("=")[2]}]'
            f'(around:{radius_m},{lat},{lon});'
            for tag in cat["tags"])
        body = f"[out:json][timeout:60];({clauses});out center {per_cat};"
        try:
            data = await overpass(client, body, note=note)
        except RuntimeError as e:
            logger.warning("discover: category %s failed: %s", cat["key"], e)
            failed.append(cat["fa"])
            first_error = first_error or str(e)
            continue
        # Carry the query's own category with each element. Resolving it from
        # the tags instead files a guest house that also serves coffee under
        # "restaurants", because `amenity` is read before `tourism`.
        elements.extend((el, cat["key"]) for el in (data.get("elements") or []))

    if failed and not elements:
        # Pass the real reason up. Overwriting it with a generic "busy" here
        # would hide the "outbound traffic is blocked" diagnosis the fetcher
        # already worked out.
        raise RuntimeError(first_error or
                           "سرورهای OpenStreetMap پاسخ ندادند (شلوغ هستند).")

    # Which of our categories a raw OSM tag belongs to.
    tag_to_cat = {t: c["key"] for c in chosen for t in c["tags"]}

    out: list[Business] = []
    seen: set[str] = set()
    for el, query_cat in elements:
        osm_id = f"{el.get('type')}/{el.get('id')}"
        if osm_id in seen:
            continue        # tagged under two of our categories — one business
        tags = el.get("tags") or {}
        name = clean_name(tags.get("name:fa") or tags.get("name") or "")
        if not name:
            continue        # an unnamed point is not a business you can contact
        seen.add(osm_id)

        osm_cat = ""
        for k in ("amenity", "shop", "office", "leisure", "tourism", "healthcare", "craft"):
            if k in tags:
                osm_cat = f"{k}={tags[k]}"
                break
        # Prefer the raw tag when it is one we asked for; otherwise trust the
        # query that returned this row.
        cat_key = tag_to_cat.get(osm_cat) or query_cat

        site_raw = (tags.get("website") or tags.get("contact:website")
                    or tags.get("url") or "").strip()
        website = site_raw if is_real_website(site_raw) else ""
        # A social URL in the website field is not a website — but it *is* a
        # contact channel, so it moves rather than being discarded.
        insta = instagram_handle(tags.get("contact:instagram") or tags.get("instagram")
                                 or (site_raw if "instagram" in site_raw.lower() else ""))
        tg = (tags.get("contact:telegram") or "").strip()
        if not tg and "t.me/" in site_raw.lower():
            tg = site_raw

        centre = el.get("center") or {}
        out.append(Business(
            osm_id=osm_id,
            name=name[:200],
            category=cat_key,
            osm_category=osm_cat,
            phone=(tags.get("phone") or tags.get("contact:phone")
                   or tags.get("contact:mobile") or "")[:80],
            website=website[:400],
            instagram=insta,
            telegram=tg[:120],
            email=(tags.get("email") or tags.get("contact:email") or "")[:200],
            address=", ".join(x for x in (
                " ".join(y for y in (tags.get("addr:street"),
                                     tags.get("addr:housenumber")) if y),
                # kept as address detail, never as the city in a sentence
                tags.get("addr:city") if (tags.get("addr:city") or "") != city_local else "",
            ) if x)[:200],
            city=city_local[:80],
            lat=el.get("lat") or centre.get("lat"),
            lon=el.get("lon") or centre.get("lon"),
        ))
    return out, failed


# ─────────────────────────────────────────────────────── profile
BUILDER_FINGERPRINTS = (
    ("wix", r"wix\.com|wixstatic"),
    ("WordPress", r"wp-content|wp-includes"),
    ("Shopify", r"cdn\.shopify"),
    ("Squarespace", r"squarespace"),
    ("Webflow", r"webflow"),
    ("پرتال/قالب آماده", r"portal\.ir|rtl-theme|parsdata|mihanwebhost"),
)
BOOKING_WORDS = (r"رزرو", r"نوبت[\s‌]*دهی", r"نوبت[\s‌]*گیری", r"سفارش[\s‌]*آنلاین",
                 r"سبد[\s‌]*خرید", r"book[\s-]*now", r"reserve", r"appointment",
                 r"order[\s-]*online", r"add[\s-]*to[\s-]*cart")
# Both Gregorian and Jalali years appear in Iranian site footers.
YEAR_RE = re.compile(r"(?:©|&copy;|copyright|کلیه حقوق|تمامی حقوق)[^\d]{0,60}(\d{4})", re.I)
MAILTO_RE = re.compile(r"mailto:([A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})", re.I)
INSTA_RE = re.compile(r"instagram\.com/([A-Za-z0-9._]{2,40})", re.I)
MAX_HTML = 500_000


@dataclass
class Profile:
    """What three HTTP requests can prove about a web presence."""
    signals: list[tuple[str, str, str]] = field(default_factory=list)  # (code, value, evidence)
    email: str = ""
    instagram: str = ""

    def add(self, code: str, value: str = "", evidence: str = "") -> None:
        self.signals.append((code, value, evidence))


async def profile_site(client: httpx.AsyncClient, url: str) -> Profile:
    """Free. No browser, no model call. The highest value-per-effort stage there
    is, because it turns "they have a website" into a specific, checkable claim
    you can put in the first line of a message.

    The one distinction this function exists to protect: **"their site is broken"
    and "I could not reach their site" are not the same claim.** A server that
    answers 404 is proof. A DNS failure or a refused connection is just as likely
    to be this machine's network, a filtered resolver, or a host that blocks
    foreign IPs — and plenty of Iranian sites do. Telling a dentist their website
    is down when it loads fine for everyone in Shiraz loses the project in the
    first sentence, so an unverified failure gets its own, visibly hedged signal
    and a message that asks instead of asserting.
    """
    p = Profile()
    target = url if "://" in url else "https://" + url
    host = urlparse(target).hostname or ""
    if not host:
        p.add("SITE_UNREACHABLE", "no host", target)
        return p
    if not _is_public_host(host):
        # Either the name does not resolve here, or it resolves to something
        # private — which is also the SSRF guard.
        p.add("SITE_UNREACHABLE", "DNS", target)
        return p

    started = time.monotonic()
    r = None
    last_err = ""
    # https first, then plain http: a working http-only site is a finding
    # (SITE_NO_HTTPS), not an unreachable one.
    for attempt in (target, "http://" + host if target.startswith("https://") else ""):
        if not attempt:
            break
        try:
            r = await client.get(attempt, headers={"User-Agent": UA},
                                 follow_redirects=True)
            break
        except httpx.HTTPError as e:
            last_err = type(e).__name__
    if r is None:
        p.add("SITE_UNREACHABLE", last_err or "connect failed", target)
        return p
    elapsed = time.monotonic() - started

    if r.status_code >= 400:
        # The server answered. This one is proof.
        p.add("SITE_DEAD", f"HTTP {r.status_code}", str(r.url))
        return p

    final = str(r.url)
    html = r.text[:MAX_HTML]
    low = html.lower()

    if urlparse(final).scheme != "https":
        p.add("SITE_NO_HTTPS", "", final)
    if elapsed > 4.0:
        p.add("SITE_SLOW", f"{elapsed:.1f}s", final)
    if not re.search(r'<meta[^>]+name=["\']?viewport', low):
        p.add("SITE_NOT_MOBILE", "no viewport meta", final)
    if "application/ld+json" not in low and "itemtype=" not in low:
        p.add("SITE_NO_SCHEMA", "", final)
    if not any(re.search(w, html, re.I) for w in BOOKING_WORDS):
        p.add("SITE_NO_BOOKING", "", final)

    for label, pattern in BUILDER_FINGERPRINTS:
        if re.search(pattern, low):
            p.add("SITE_BUILDER", label, final)
            break

    m = YEAR_RE.search(html.translate(_PERSIAN_DIGITS))
    if m:
        year = int(m.group(1))
        # 2026 Gregorian / 1405 Jalali — anything two years behind is abandoned.
        stale = (year < 2024) if year > 1900 else (year < 1403)
        if stale:
            p.add("SITE_STALE", m.group(1), final)

    if mail := MAILTO_RE.search(html):
        p.email = mail.group(1)[:200]
    if insta := INSTA_RE.search(html):
        p.instagram = instagram_handle(insta.group(1))

    # Nothing wrong found: they already have a working, modern, indexed site.
    # Say so plainly and score them down rather than inventing a complaint.
    gaps = {c for c, _, _ in p.signals} - {"SITE_NO_SCHEMA", "SITE_NO_BOOKING"}
    if not gaps:
        p.add("SITE_MODERN", "", final)
    return p


# ─────────────────────────────────────────────────────── score
def score_lead(codes: set[str]) -> tuple[int, str]:
    total = sum(SIGNALS[c][0] for c in codes if c in SIGNALS)
    score = max(0, min(100, total))
    return score, tier_for(score)


def derive_contact_signals(lead: dict) -> list[str]:
    codes = []
    if lead.get("is_mobile"):
        codes.append("PHONE_MOBILE")
    elif lead.get("phone_e164"):
        codes.append("PHONE_LANDLINE")
    if lead.get("instagram"):
        codes.append("HAS_INSTAGRAM")
    if not lead.get("phone_e164") and not lead.get("instagram") and not lead.get("email"):
        codes.append("NO_CONTACT")
    if not lead.get("website"):
        codes.append("NO_WEBSITE")
        if lead.get("instagram"):
            codes.append("INSTAGRAM_ONLY")
    return codes


# ─────────────────────────────────────────────────────── pitch
# Harvey's writer rules, kept: lead with the specific observation, never with
# yourself; one idea per message; a soft question as the close; no superlatives and
# no "I hope this message finds you well". The difference is these are templates
# filled from signals rather than model output — which means they run on the deploy
# host, cost nothing, and say only what the profiler actually proved.
#
# Ordered by strength: the first matching template wins.
PITCH_TEMPLATES: list[tuple[str, str]] = [
    ("SITE_DEAD", """سلام، وقت بخیر
من سایت {domain} رو باز کردم و بالا نیومد — احتمالاً خودتون هم خبر ندارید که مشتری‌هاتون همین صفحه خطا رو می‌بینند.
کسی که اسم {name} رو در گوگل جست‌وجو می‌کند و به سایت خراب برمی‌خورد، معمولاً سراغ نفر بعدی می‌رود.
من برای کسب‌وکارهای {city} سایت می‌سازم؛ می‌تونم همین سایت رو درست کنم یا یک نسخه سریع و موبایل‌پسند براتون بسازم.
اگر بخواهید، نمونه کار و قیمت بفرستم؟
{sender}"""),

    ("SITE_UNREACHABLE", """سلام، وقت بخیر
می‌خواستم سایت {domain} رو ببینم ولی برای من باز نشد (ممکنه مشکل از سمت من باشه).
اگر از سمت بقیه هم همین‌طور باشه، یعنی مشتری‌هایی که اسم {name} رو در گوگل جست‌وجو می‌کنند به صفحه خطا می‌رسند.
من برای کسب‌وکارهای {city} سایت می‌سازم و می‌تونم همین مورد رو هم بررسی کنم.
اگر دوست داشتید نگاهی بیندازم و نتیجه رو بگم؟
{sender}"""),

    ("INSTAGRAM_ONLY", """سلام، وقت بخیر
صفحه اینستاگرام {name} رو دیدم ({instagram}) — کارتون خوبه، ولی دیدم وبسایت ندارید.
مشتری‌ای که اسم شما رو در گوگل می‌زند چیزی پیدا نمی‌کند، و اینستاگرام هم که فیلتر یا پایین بیاید، راه ارتباطی‌تون قطع می‌شود.
من برای کسب‌وکارهای {city} سایت می‌سازم: سریع، موبایل‌پسند، با امکان دیده‌شدن در گوگل و وصل به همین صفحه اینستاگرام.
اگر بخواهید یک نمونه کار و قیمت براتون بفرستم؟
{sender}"""),

    ("NO_WEBSITE", """سلام، وقت بخیر
{name} رو روی نقشه پیدا کردم و دیدم هنوز وبسایت ندارید.
خیلی از مشتری‌ها قبل از مراجعه، اسم کسب‌وکار رو در گوگل جست‌وجو می‌کنند؛ وقتی چیزی پیدا نمی‌کنند، سراغ جایی می‌روند که پیدا کردند.
من برای کسب‌وکارهای {city} سایت می‌سازم — ساده، سریع، موبایل‌پسند، با آدرس و شماره و خدمات شما روی گوگل.
اگر بخواهید یک نمونه کار و قیمت براتون بفرستم؟
{sender}"""),

    ("SITE_NOT_MOBILE", """سلام، وقت بخیر
سایت {domain} رو روی موبایل باز کردم و درست نمایش داده نمی‌شه (برای موبایل طراحی نشده).
امروز بیشتر از ۸۰ درصد بازدیدها از گوشی است، و گوگل هم سایت‌هایی که روی موبایل خوب نیستند را پایین‌تر نشان می‌دهد.
من همین سایت رو می‌تونم موبایل‌پسند و سریع بازطراحی کنم، بدون اینکه محتوای فعلی‌تون از دست برود.
اگر بخواهید، نمونه قبل/بعد و قیمت بفرستم؟
{sender}"""),

    ("SITE_STALE", """سلام، وقت بخیر
سایت {domain} رو دیدم — پایین صفحه سال {stale_year} ثبت شده، یعنی چند سالی به‌روز نشده.
سایتی که به‌روز نمی‌شود کم‌کم از نتایج گوگل عقب می‌افتد، و بازدیدکننده هم از سال قدیمی برداشت می‌کند که کسب‌وکار دیگر فعال نیست.
می‌تونم به‌روزرسانی و بازطراحی‌اش را انجام بدهم، یا یک نسخه تازه بسازم.
اگر بخواهید نمونه کار و قیمت بفرستم؟
{sender}"""),

    ("SITE_NO_HTTPS", """سلام، وقت بخیر
سایت {domain} گواهی امنیتی (HTTPS) ندارد؛ کروم و سایر مرورگرها به بازدیدکننده‌ها هشدار «ناامن» نشان می‌دهند.
این هشدار باعث می‌شود بخشی از مشتری‌ها قبل از دیدن صفحه، سایت را ببندند — و گوگل هم این سایت‌ها را پایین‌تر رتبه می‌دهد.
درست کردنش کار سختی نیست؛ می‌تونم همین را حل کنم و در همان مرحله سرعت و نمایش موبایلش را هم بهتر کنم.
اگر بخواهید، توضیح و قیمتش را بفرستم؟
{sender}"""),

    ("SITE_NO_BOOKING", """سلام، وقت بخیر
سایت {domain} رو دیدم؛ راه رزرو یا سفارش آنلاین ندارد و همه‌چیز به تماس تلفنی وابسته است.
یعنی هر مشتری‌ای که شب یا ساعت تعطیل تصمیم می‌گیرد، تا فردا منتظر می‌ماند — و خیلی‌هاشون منتظر نمی‌مانند.
من می‌تونم رزرو/سفارش آنلاین را به سایتتان اضافه کنم، وصل به واتساپ یا پنل خودتان.
اگر بخواهید نمونه کار و قیمت بفرستم؟
{sender}"""),

    ("SITE_BUILDER", """سلام، وقت بخیر
سایت {domain} رو دیدم — روی قالب آماده ({builder}) ساخته شده.
قالب‌های آماده معمولاً کند هستند، شبیه بقیه‌اند و در گوگل سخت بالا می‌آیند؛ برای یک کسب‌وکار جاافتاده حیف است.
من سایت‌های اختصاصی و سریع برای کسب‌وکارهای {city} می‌سازم.
اگر بخواهید نمونه کار و قیمت بفرستم؟
{sender}"""),
]

PITCH_FALLBACK = """سلام، وقت بخیر
{name} رو روی نقشه {city} دیدم و نگاهی به حضور اینترنتی‌تون انداختم.
من طراحی و ساخت وبسایت و اپلیکیشن برای کسب‌وکارهای {city} انجام می‌دهم — سریع، موبایل‌پسند و قابل دیده‌شدن در گوگل.
اگر بخواهید یک نمونه کار و قیمت براتون بفرستم؟
{sender}"""


def build_pitch(lead: dict, codes: set[str], signal_values: dict[str, str],
                sender: str) -> str:
    ctx = {
        "name": lead.get("name") or "کسب‌وکار شما",
        "city": lead.get("city") or "شیراز",
        "domain": lead.get("domain") or normalize_domain(lead.get("website") or ""),
        "instagram": "@" + lead["instagram"] if lead.get("instagram") else "",
        "stale_year": signal_values.get("SITE_STALE", ""),
        "builder": signal_values.get("SITE_BUILDER", "قالب آماده"),
        "sender": sender,
    }
    for code, template in PITCH_TEMPLATES:
        if code in codes:
            return template.format(**ctx).strip()
    return PITCH_FALLBACK.format(**ctx).strip()


def sender_signature() -> str:
    """Signature from the site's own settings, so it stays correct if they change."""
    conn = get_db()
    try:
        name = get_setting(conn, "finder_sender_name") or get_setting(conn, "site_title_fa") or "نیما"
        site = get_setting(conn, "site_url") or ""
    finally:
        conn.close()
    return f"{name} | {site}".strip(" |") if site else name


# ─────────────────────────────────────────────────────── persistence
def _save_signals(conn, lead_id: int, pairs: list[tuple[str, str, str]]) -> None:
    for code, value, evidence in pairs:
        if code not in SIGNALS:
            continue    # the vocabulary is governed: a typo must not invent a signal
        conn.execute(
            "INSERT INTO lead_signals(lead_id,code,value,evidence) VALUES(?,?,?,?) "
            "ON CONFLICT(lead_id,code) DO UPDATE SET "
            "value=excluded.value, evidence=excluded.evidence, observed_at=datetime('now')",
            (lead_id, code, value[:120], evidence[:400]))


def _refresh_lead(conn, lead_id: int) -> tuple[int, str]:
    """Re-score from the signal rows and regenerate the pitch. Never overwrites a
    message you have edited by hand — `pitch_edited` is the flag that protects it."""
    lead = dict(conn.execute("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchone())
    rows = conn.execute("SELECT code,value FROM lead_signals WHERE lead_id=?",
                        (lead_id,)).fetchall()
    codes = {r["code"] for r in rows}
    values = {r["code"]: r["value"] for r in rows}
    score, tier = score_lead(codes)
    if lead["pitch_edited"]:
        conn.execute("UPDATE leads SET score=?,tier=?,updated_at=datetime('now') "
                     "WHERE id=?", (score, tier, lead_id))
    else:
        pitch = build_pitch(lead, codes, values, sender_signature())
        conn.execute("UPDATE leads SET score=?,tier=?,pitch=?,updated_at=datetime('now') "
                     "WHERE id=?", (score, tier, pitch, lead_id))
    return score, tier


def upsert_business(conn, b: Business) -> tuple[int, bool]:
    """-> (lead_id, is_new). Re-running discovery must never duplicate or clobber:
    the OSM id is the identity, and status/notes you set by hand survive."""
    phone_e164, is_mobile = normalize_phone(b.phone)
    row = conn.execute("SELECT id FROM leads WHERE osm_id=?", (b.osm_id,)).fetchone()
    data = (b.name, b.category, b.osm_category, b.phone, phone_e164, int(is_mobile),
            b.website, normalize_domain(b.website), b.instagram, b.telegram, b.email,
            b.address, b.city, b.lat, b.lon)
    if row:
        lead_id = row["id"]
        conn.execute(
            "UPDATE leads SET name=?,category=?,osm_category=?,phone=?,phone_e164=?,"
            "is_mobile=?,website=?,domain=?,instagram=?,telegram=?,email=?,address=?,"
            "city=?,lat=?,lon=?,updated_at=datetime('now') WHERE id=?",
            (*data, lead_id))
        is_new = False
    else:
        cur = conn.execute(
            "INSERT INTO leads(name,category,osm_category,phone,phone_e164,is_mobile,"
            "website,domain,instagram,telegram,email,address,city,lat,lon,osm_id) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (*data, b.osm_id))
        lead_id = cur.lastrowid
        is_new = True

    lead = {"phone_e164": phone_e164, "is_mobile": is_mobile, "website": b.website,
            "instagram": b.instagram, "email": b.email}
    # Contact/website facts are re-derived, so a business that has since added a
    # site stops being pitched a site.
    conn.execute("DELETE FROM lead_signals WHERE lead_id=? AND code IN "
                 "('NO_WEBSITE','INSTAGRAM_ONLY','PHONE_MOBILE','PHONE_LANDLINE',"
                 "'HAS_INSTAGRAM','NO_CONTACT')", (lead_id,))
    _save_signals(conn, lead_id, [(c, "", "openstreetmap")
                                  for c in derive_contact_signals(lead)])
    _refresh_lead(conn, lead_id)
    return lead_id, is_new


# ─────────────────────────────────────────────────────── runs
def _run_set(run_id: int, **fields) -> None:
    if not fields:
        return
    cols = ", ".join(f"{k}=?" for k in fields)
    conn = get_db()
    try:
        conn.execute(f"UPDATE finder_runs SET {cols} WHERE id=?",
                     (*fields.values(), run_id))
        conn.commit()
    finally:
        conn.close()


def start_run(kind: str, city: str = "", categories: str = "") -> int:
    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO finder_runs(kind,city,categories) VALUES(?,?,?)",
            (kind, city, categories))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def active_run() -> dict | None:
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM finder_runs WHERE status='running' "
            "ORDER BY id DESC LIMIT 1").fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


async def _discover_job(run_id: int, city: str, cat_keys: list[str],
                        radius_km: int, limit: int, do_profile: bool) -> None:
    async with new_client() as client:
        _run_set(run_id, message="در حال جست‌وجوی نقشه…")
        businesses, failed = await discover(
            client, city, cat_keys, radius_km, limit,
            note=lambda m: _run_set(run_id, message=m))
        _run_set(run_id, found=len(businesses),
                 message=f"{len(businesses)} کسب‌وکار پیدا شد — در حال ذخیره…")

        added = 0
        conn = get_db()
        try:
            for b in businesses:
                _, is_new = upsert_business(conn, b)
                added += is_new
            conn.commit()
        finally:
            conn.close()
        # A category that could not be fetched is said out loud. Silence here
        # would read as "there are no hotels in Shiraz".
        _normalize_cities(city, businesses)
        warn = (f" ({', '.join(failed)} ناموفق بود — دوباره تلاش کنید)"
                if failed else "")
        _run_set(run_id, added=added, message=f"{added} لید جدید ذخیره شد.{warn}")

        if do_profile:
            n = await _profile_pending(client, run_id, limit=120)
            _run_set(run_id, profiled=n,
                     message=f"{added} لید جدید، {n} سایت بررسی شد.{warn}")


def _normalize_cities(raw_query: str, businesses: list[Business]) -> None:
    """Rewrite the Latin search string left in older rows.

    Early runs stored whatever was typed into the city box ("Shiraz, Iran"), and
    that string went straight into a Persian sentence. Rows are repaired here
    rather than in a migration because the correct value is the place name
    Nominatim returned for *this* run, which a migration would not have.
    """
    if not businesses:
        return
    local = businesses[0].city
    if not local or local == raw_query:
        return
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT id FROM leads WHERE city<>? AND lower(trim(city)) IN (?,?)",
            (local, raw_query.strip().lower(),
             raw_query.split(",")[0].strip().lower())).fetchall()
        for row in rows:
            conn.execute("UPDATE leads SET city=? WHERE id=?", (local, row["id"]))
            _refresh_lead(conn, row["id"])     # the pitch quotes the city
        conn.commit()
        if rows:
            logger.info("normalized city on %d older leads -> %s", len(rows), local)
    finally:
        conn.close()


async def _profile_pending(client: httpx.AsyncClient, run_id: int, limit: int) -> int:
    """Profile leads that claim a website but have not been checked yet."""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT id,website FROM leads WHERE website<>'' AND profiled_at IS NULL "
            "ORDER BY score DESC LIMIT ?", (limit,)).fetchall()
        targets = [(r["id"], r["website"]) for r in rows]
        # Nothing new to check? Re-check whatever was previously judged broken
        # or unreachable, oldest first. "Unreachable" is a statement about the
        # connection as much as the site, so it deserves a retry from a better
        # one; and a site that was genuinely 404 last month may be back. Either
        # way this is what the button should do, rather than reporting
        # "nothing to do" and leaving a stale verdict in a pitch.
        if not targets:
            rows = conn.execute(
                "SELECT DISTINCT l.id, l.website FROM leads l "
                "JOIN lead_signals s ON s.lead_id=l.id "
                "WHERE l.website<>'' AND s.code IN ('SITE_UNREACHABLE','SITE_DEAD') "
                "ORDER BY l.profiled_at LIMIT ?",
                (limit,)).fetchall()
            targets = [(r["id"], r["website"]) for r in rows]
    finally:
        conn.close()
    if not targets:
        return 0

    done = 0
    sem = asyncio.Semaphore(6)       # polite to small Iranian hosts

    async def one(lead_id: int, url: str):
        nonlocal done
        async with sem:
            try:
                prof = await profile_site(client, url)
            except Exception as e:                      # never let one site kill the run
                logger.warning("profile %s failed: %s", url, e)
                prof = Profile()
                # Our failure, not a proven fact about their site.
                prof.add("SITE_UNREACHABLE", type(e).__name__, url)
        conn = get_db()
        try:
            # Drop the previous verdict first: a site that was "unreachable" on a
            # bad connection must not keep that tag once it loads.
            conn.execute("DELETE FROM lead_signals WHERE lead_id=? AND code LIKE 'SITE_%'",
                         (lead_id,))
            _save_signals(conn, lead_id, prof.signals)
            if prof.email:
                conn.execute("UPDATE leads SET email=COALESCE(NULLIF(email,''),?) "
                             "WHERE id=?", (prof.email, lead_id))
            if prof.instagram:
                conn.execute("UPDATE leads SET instagram=COALESCE(NULLIF(instagram,''),?) "
                             "WHERE id=?", (prof.instagram, lead_id))
            conn.execute("UPDATE leads SET profiled_at=datetime('now') WHERE id=?",
                         (lead_id,))
            _refresh_lead(conn, lead_id)
            conn.commit()
        finally:
            conn.close()
        done += 1
        if done % 10 == 0:
            _run_set(run_id, profiled=done, message=f"{done} سایت بررسی شد…")

    await asyncio.gather(*(one(i, u) for i, u in targets))
    return done


def launch(kind: str, **kwargs) -> dict:
    """Start a run on a background thread. One at a time — Overpass etiquette is
    modest volume and no parallelism, and two concurrent runs would also race on
    the same SQLite file for no benefit."""
    running = active_run()
    if running:
        raise RuntimeError("یک جست‌وجو همین حالا در حال اجراست.")

    if kind == "discover":
        city = kwargs.get("city") or "Shiraz, Iran"
        cats = kwargs.get("categories") or DEFAULT_CATEGORIES
        cats = [c for c in cats if c in CATEGORY_KEYS] or DEFAULT_CATEGORIES
        run_id = start_run("discover", city, ",".join(cats))
        coro_factory = lambda: _discover_job(          # noqa: E731
            run_id, city, cats, int(kwargs.get("radius_km") or 20),
            int(kwargs.get("limit") or 400), bool(kwargs.get("profile", True)))
    elif kind == "profile":
        run_id = start_run("profile")

        async def _job():
            async with new_client() as client:
                n = await _profile_pending(client, run_id, int(kwargs.get("limit") or 200))
                _run_set(run_id, profiled=n, message=f"{n} سایت بررسی شد.")
        coro_factory = _job
    else:
        raise RuntimeError(f"unknown run kind {kind!r}")

    def worker():
        try:
            asyncio.run(coro_factory())
            _run_set(run_id, status="done", finished_at=time.strftime("%Y-%m-%d %H:%M:%S"))
        except Exception as e:
            logger.exception("finder run %s failed", run_id)
            _run_set(run_id, status="error", message=str(e)[:500],
                     finished_at=time.strftime("%Y-%m-%d %H:%M:%S"))

    threading.Thread(target=worker, name=f"finder-{run_id}", daemon=True).start()
    conn = get_db()
    try:
        return dict(conn.execute("SELECT * FROM finder_runs WHERE id=?",
                                 (run_id,)).fetchone())
    finally:
        conn.close()


# ─────────────────────────────────────────────────────── reads
STATUSES = ("new", "contacted", "replied", "quoted", "won", "lost", "skip")
STATUS_FA = {"new": "جدید", "contacted": "پیام داده شد", "replied": "پاسخ داد",
             "quoted": "قیمت داده شد", "won": "پروژه گرفته شد", "lost": "از دست رفت",
             "skip": "رد شد"}


# How a lead can actually be contacted. "ig_only" is the pile that matters most
# in practice: no mobile at all, or a number that is not on WhatsApp, but an
# Instagram account that is clearly active.
REACH = ("wa", "ig", "ig_only", "none")


def lead_rows(status: str = "", tier: str = "", category: str = "",
              q: str = "", reach: str = "", limit: int = 200, offset: int = 0,
              _only_id: int | None = None) -> list[dict]:
    where, args = ["1=1"], []
    if _only_id is not None:
        where.append("id=?"); args.append(_only_id)
    if reach == "wa":
        where.append("is_mobile=1")
    elif reach == "ig":
        where.append("instagram<>''")
    elif reach == "ig_only":
        where.append("instagram<>'' AND is_mobile=0")
    elif reach == "none":
        where.append("instagram='' AND phone_e164=''")
    if status in STATUSES:
        where.append("status=?"); args.append(status)
    if tier in (TIER_HOT, TIER_WARM, TIER_COLD):
        where.append("tier=?"); args.append(tier)
    if category in CATEGORY_KEYS:
        where.append("category=?"); args.append(category)
    if q:
        where.append("(name LIKE ? OR domain LIKE ? OR phone LIKE ?)")
        args += [f"%{q}%"] * 3

    conn = get_db()
    try:
        rows = conn.execute(
            f"SELECT * FROM leads WHERE {' AND '.join(where)} "
            "ORDER BY CASE status WHEN 'new' THEN 0 ELSE 1 END, score DESC, id DESC "
            "LIMIT ? OFFSET ?", (*args, int(limit), int(offset))).fetchall()
        out = []
        for r in rows:
            lead = dict(r)
            sig = conn.execute(
                "SELECT code,value,evidence FROM lead_signals WHERE lead_id=? ",
                (lead["id"],)).fetchall()
            lead["signals"] = [
                {"code": s["code"], "value": s["value"], "evidence": s["evidence"],
                 "fa": SIGNALS[s["code"]][1], "weight": SIGNALS[s["code"]][0]}
                for s in sig if s["code"] in SIGNALS
            ]
            lead["signals"].sort(key=lambda s: -s["weight"])
            lead["wa"] = wa_link(lead["phone_e164"], lead["pitch"]) if lead["is_mobile"] else ""
            lead["ig"] = ig_link(lead["instagram"])
            lead["category_fa"] = CATEGORY_FA.get(lead["category"], lead["category"])
            lead["status_fa"] = STATUS_FA.get(lead["status"], lead["status"])
            out.append(lead)
        return out
    finally:
        conn.close()


def lead_by_id(lead_id: int) -> dict:
    conn = get_db()
    try:
        row = conn.execute("SELECT id FROM leads WHERE id=?", (lead_id,)).fetchone()
    finally:
        conn.close()
    if not row:
        return {}
    rows = lead_rows(limit=1, _only_id=lead_id)
    return rows[0] if rows else {}


def summary() -> dict:
    conn = get_db()
    try:
        def one(sql, args=()):
            return conn.execute(sql, args).fetchone()[0]
        by_status = {r["status"]: r["n"] for r in conn.execute(
            "SELECT status, COUNT(*) n FROM leads GROUP BY status")}
        by_tier = {r["tier"]: r["n"] for r in conn.execute(
            "SELECT tier, COUNT(*) n FROM leads GROUP BY tier")}
        return {
            "total": one("SELECT COUNT(*) FROM leads"),
            "hot": by_tier.get(TIER_HOT, 0),
            "warm": by_tier.get(TIER_WARM, 0),
            "no_website": one("SELECT COUNT(*) FROM lead_signals WHERE code='NO_WEBSITE'"),
            "reachable": one("SELECT COUNT(*) FROM leads WHERE is_mobile=1"),
            "ig_only": one("SELECT COUNT(*) FROM leads WHERE instagram<>'' "
                           "AND is_mobile=0"),
            "unprofiled": one("SELECT COUNT(*) FROM leads WHERE website<>'' "
                              "AND profiled_at IS NULL"),
            "by_status": by_status,
            "by_tier": by_tier,
        }
    finally:
        conn.close()


def recent_runs(limit: int = 8) -> list[dict]:
    conn = get_db()
    try:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM finder_runs ORDER BY id DESC LIMIT ?", (limit,))]
    finally:
        conn.close()


def update_lead(lead_id: int, status: str = "", note: str | None = None,
                pitch: str | None = None) -> dict:
    conn = get_db()
    try:
        row = conn.execute("SELECT id FROM leads WHERE id=?", (lead_id,)).fetchone()
        if not row:
            raise LookupError("lead not found")
        if status:
            if status not in STATUSES:
                raise ValueError("bad status")
            conn.execute("UPDATE leads SET status=?,updated_at=datetime('now') "
                         "WHERE id=?", (status, lead_id))
        if note is not None:
            conn.execute("UPDATE leads SET note=? WHERE id=?", (note[:2000], lead_id))
        if pitch is not None:
            # Editing by hand pins the message: later re-scoring must not silently
            # replace words you chose. Saving the modal unchanged is not an edit,
            # though — the panel always posts the current text, and pinning on
            # every save used to stop that lead being queued automatically.
            current = conn.execute("SELECT pitch FROM leads WHERE id=?",
                                   (lead_id,)).fetchone()["pitch"]
            if pitch != current:
                conn.execute("UPDATE leads SET pitch=?,pitch_edited=1 WHERE id=?",
                             (pitch[:3000], lead_id))
            else:
                conn.execute("UPDATE leads SET pitch=? WHERE id=?",
                             (pitch[:3000], lead_id))
        conn.commit()
    finally:
        conn.close()
    return lead_by_id(lead_id)


def regenerate_pitch(lead_id: int) -> str:
    """Throw away a hand-edited message and rebuild it from the signals."""
    conn = get_db()
    try:
        conn.execute("UPDATE leads SET pitch_edited=0 WHERE id=?", (lead_id,))
        _refresh_lead(conn, lead_id)
        conn.commit()
        row = conn.execute("SELECT pitch FROM leads WHERE id=?", (lead_id,)).fetchone()
        return row["pitch"] if row else ""
    finally:
        conn.close()


def delete_lead(lead_id: int) -> None:
    conn = get_db()
    try:
        conn.execute("DELETE FROM leads WHERE id=?", (lead_id,))
        conn.commit()
    finally:
        conn.close()


def export_csv() -> str:
    import csv
    import io
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["name", "category", "score", "tier", "status", "phone", "whatsapp",
                "instagram", "instagram_dm", "website", "address", "city",
                "signals", "osm"])
    for lead in lead_rows(limit=5000):
        w.writerow([
            lead["name"], lead["category_fa"], lead["score"], lead["tier"],
            lead["status"], lead["phone"],
            f"+{lead['phone_e164']}" if lead["is_mobile"] else "",
            f"@{lead['instagram']}" if lead["instagram"] else "",
            lead["ig"], lead["website"], lead["address"], lead["city"],
            " | ".join(s["code"] for s in lead["signals"]),
            f"https://www.openstreetmap.org/{lead['osm_id']}",
        ])
    return buf.getvalue()
