"""RESEARCH — what does this particular business actually need?

The profiler in `finder.py` answers "is there a website and is it broken". That
is enough to sort leads, and not nearly enough to write to someone. "Your site
has no schema markup" is true and means nothing to a café owner.

This module answers the question a person would ask: *what is this business
losing right now, and what would fix it?* It reads several pages rather than
one, decides which gaps matter **for that kind of business**, and keeps the
evidence that proved each one.

Two rules shape everything here:

* **A need is category-specific.** A restaurant with no online ordering is
  losing every order placed after closing time. A lawyer with no online ordering
  is losing nothing — that is not what anyone wants from a lawyer. The same
  missing feature is a strong need in one category and noise in another, so the
  catalog scores needs per category rather than globally.

* **Nothing is claimed without evidence.** Every need carries the URL and the
  snippet that produced it, so the message can name a real thing and you can
  check it before pressing send. A need that cannot cite anything is not
  reported — a confident message about a problem they do not have is worse than
  no message at all.
"""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import httpx

from .finder import fetch_site, is_blocked

logger = logging.getLogger("finder.research")

MAX_PAGES = 6                 # homepage + 5 — enough to find a menu or a booking page
MAX_HTML = 400_000
PAGE_TIMEOUT = 16.0


# ─────────────────────────────────────────── what we look for on a page
# Persian sites mix Persian, Arabic-script Persian and English wording, and the
# zero-width non-joiner shows up inside almost every compound word. `[\s‌]*`
# between the parts of a term is not decoration: "نوبت‌دهی" and "نوبت دهی" are
# the same word and only one of them matches a naive pattern.
def _rx(*parts: str) -> re.Pattern:
    return re.compile("|".join(parts), re.I)


ORDER_RX = _rx(r"سفارش[\s‌]*آنلاین", r"ثبت[\s‌]*سفارش", r"سبد[\s‌]*خرید",
               r"افزودن به سبد", r"add[\s-]*to[\s-]*cart", r"order[\s-]*online",
               r"checkout", r"snappfood", r"reyhoon", r"delino", r"chilivery")
RESERVE_RX = _rx(r"رزرو[\s‌]*(میز|آنلاین|اتاق|اقامت)?", r"book[\s-]*now",
                 r"booking", r"reserve", r"reservation", r"اتاق[\s‌]*خالی")
APPOINT_RX = _rx(r"نوبت[\s‌]*(دهی|گیری)", r"گرفتن[\s‌]*نوبت",
                 r"appointment", r"رزرو[\s‌]*نوبت", r"وقت[\s‌]*ملاقات")
MENU_RX = _rx(r"\bمنو\b", r"منوی", r"لیست[\s‌]*غذا", r"\bmenu\b")
CATALOG_RX = _rx(r"محصولات", r"فروشگاه", r"کالاها", r"products?", r"\bshop\b",
                 r"catalog", r"گالری[\s‌]*محصول")
PRICE_RX = _rx(r"تومان", r"ریال", r"قیمت", r"تعرفه", r"\bprice\b", r"\bAED\b", r"\bUSD\b")
CONTACTFORM_RX = _rx(r"<form", r"تماس[\s‌]*با[\s‌]*ما", r"contact[\s-]*us")
MAP_RX = _rx(r"maps\.google", r"neshan\.org", r"balad\.ir", r"openstreetmap",
             r"<iframe[^>]+map")
WHATSAPP_RX = _rx(r"wa\.me/", r"api\.whatsapp\.com", r"whatsapp")
BLOG_RX = _rx(r"\bبلاگ\b", r"وبلاگ", r"اخبار", r"مقالات", r"\bblog\b", r"\bnews\b")

# Which internal links are worth the extra request, in both languages.
PAGE_HINTS = (
    ("menu", _rx(r"menu", r"منو", r"غذا")),
    ("order", _rx(r"order", r"سفارش", r"cart", r"سبد", r"shop", r"فروشگاه")),
    ("book", _rx(r"book", r"reserve", r"رزرو", r"نوبت", r"appointment")),
    ("products", _rx(r"product", r"محصول", r"کالا", r"catalog", r"گالری")),
    ("prices", _rx(r"price", r"قیمت", r"تعرفه", r"pricing")),
    ("contact", _rx(r"contact", r"تماس", r"ارتباط")),
    ("about", _rx(r"about", r"درباره")),
)
SKIP_LINK_RX = _rx(r"^(mailto|tel|javascript|#)", r"\.(jpg|jpeg|png|gif|webp|svg|pdf|zip|mp4)($|\?)",
                   r"(facebook|instagram|twitter|t\.me|linkedin|youtube|aparat)\.")

YEAR_RX = re.compile(r"(?:©|&copy;|copyright|کلیه حقوق|تمامی حقوق)[^\d]{0,60}(\d{4})", re.I)
TITLE_RX = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
METADESC_RX = re.compile(r'<meta[^>]+name=["\']?description["\']?[^>]+content=["\']([^"\']{0,400})', re.I)
TEXT_STRIP_RX = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.I | re.S)
TAG_RX = re.compile(r"<[^>]+>")
_PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


@dataclass
class SiteFacts:
    """Everything several requests could establish about one web presence."""
    reachable: bool = False
    final_url: str = ""
    status: int = 0
    pages: list[str] = field(default_factory=list)
    load_seconds: float = 0.0
    https: bool = False
    mobile_ready: bool = False
    has_schema: bool = False
    has_meta_desc: bool = False
    title: str = ""
    stale_year: str = ""
    builder: str = ""
    has_order: bool = False
    has_reservation: bool = False
    has_appointment: bool = False
    has_menu: bool = False
    has_catalog: bool = False
    has_prices: bool = False
    has_contact_form: bool = False
    has_map: bool = False
    has_whatsapp: bool = False
    has_blog: bool = False
    text_chars: int = 0
    # evidence: fact -> (url, snippet)
    evidence: dict[str, tuple[str, str]] = field(default_factory=dict)

    def note(self, key: str, url: str, snippet: str = "") -> None:
        self.evidence.setdefault(key, (url, snippet[:160]))


def _visible_text(html: str) -> str:
    return TAG_RX.sub(" ", TEXT_STRIP_RX.sub(" ", html))


def _snippet(text: str, pattern: re.Pattern, width: int = 70) -> str:
    m = pattern.search(text)
    if not m:
        return ""
    a = max(0, m.start() - width // 2)
    return re.sub(r"\s+", " ", text[a:a + width]).strip()


def _pick_links(html: str, base: str, limit: int) -> list[str]:
    """Internal links most likely to answer a question the homepage didn't."""
    host = (urlparse(base).hostname or "").lower()
    found: dict[str, str] = {}
    for m in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\']([^>]*)>(.*?)</a>',
                         html, re.I | re.S):
        href, label = m.group(1).strip(), _visible_text(m.group(3))
        if SKIP_LINK_RX.search(href):
            continue
        absolute = urljoin(base, href)
        if (urlparse(absolute).hostname or "").lower() != host:
            continue
        hay = href + " " + label
        for kind, rx in PAGE_HINTS:
            if kind not in found and rx.search(hay):
                found[kind] = absolute.split("#")[0]
                break
        if len(found) >= limit:
            break
    return list(found.values())[:limit]


async def _get(client: httpx.AsyncClient, url: str, ua: str) -> httpx.Response | None:
    """One page, through whatever route can actually reach it.

    `fetch_site` retries a refusal without the proxy: Iranian hosts refuse
    foreign addresses, and a VPN exit is a foreign address all day long.
    """
    return await fetch_site(client, url, ua, timeout=PAGE_TIMEOUT)


async def crawl(client: httpx.AsyncClient, url: str, ua: str) -> SiteFacts:
    """Read the homepage, then the few pages that answer the questions it left
    open. Six requests buys the difference between "they have a website" and
    "their menu is a photo and there is no way to order"."""
    import time

    f = SiteFacts()
    target = url if "://" in url else "https://" + url
    t0 = time.monotonic()
    r = await _get(client, target, ua)
    if r is None and target.startswith("https://"):
        r = await _get(client, "http://" + (urlparse(target).hostname or ""), ua)
    if r is None:
        return f
    f.load_seconds = time.monotonic() - t0
    f.status = r.status_code
    f.final_url = str(r.url)
    f.https = urlparse(f.final_url).scheme == "https"
    if r.status_code >= 400:
        if is_blocked(r.status_code):
            # Something in front of the site refused *us* — a foreign IP, a
            # VPN exit, a throttle. That is not evidence the business is
            # offline, so it must not become "سایت از دسترس خارج است" in a
            # message to a stranger.
            f.status = 0
        return f
    f.reachable = True

    home = r.text[:MAX_HTML]
    pages = [(f.final_url, home)]
    for link in _pick_links(home, f.final_url, MAX_PAGES - 1):
        sub = await _get(client, link, ua)
        if sub is not None and sub.status_code < 400:
            pages.append((str(sub.url), sub.text[:MAX_HTML]))
    f.pages = [u for u, _ in pages]

    for page_url, html in pages:
        low = html.lower()
        text = _visible_text(html)
        f.text_chars += len(text)

        if not f.mobile_ready and re.search(r'<meta[^>]+name=["\']?viewport', low):
            f.mobile_ready = True
        if not f.has_schema and ("application/ld+json" in low or "itemtype=" in low):
            f.has_schema = True
        if not f.has_meta_desc:
            m = METADESC_RX.search(html)
            if m and len(m.group(1).strip()) > 30:
                f.has_meta_desc = True
        if not f.title:
            m = TITLE_RX.search(html)
            if m:
                f.title = re.sub(r"\s+", " ", _visible_text(m.group(1))).strip()[:160]

        for attr, rx in (("has_order", ORDER_RX), ("has_reservation", RESERVE_RX),
                         ("has_appointment", APPOINT_RX), ("has_menu", MENU_RX),
                         ("has_catalog", CATALOG_RX), ("has_prices", PRICE_RX),
                         ("has_map", MAP_RX), ("has_whatsapp", WHATSAPP_RX),
                         ("has_blog", BLOG_RX)):
            if not getattr(f, attr) and rx.search(text):
                setattr(f, attr, True)
                f.note(attr, page_url, _snippet(text, rx))
        if not f.has_contact_form and CONTACTFORM_RX.search(html):
            f.has_contact_form = True
            f.note("has_contact_form", page_url)

        if not f.stale_year:
            m = YEAR_RX.search(html.translate(_PERSIAN_DIGITS))
            if m:
                year = int(m.group(1))
                if (year < 2024) if year > 1900 else (year < 1403):
                    f.stale_year = m.group(1)
                    f.note("stale_year", page_url, m.group(0)[:80])
        if not f.builder:
            for label, pat in (("Wix", r"wix\.com|wixstatic"),
                               ("WordPress", r"wp-content|wp-includes"),
                               ("Shopify", r"cdn\.shopify"),
                               ("Squarespace", r"squarespace"),
                               ("قالب آماده", r"rtl-theme|parsdata|portal\.ir")):
                if re.search(pat, low):
                    f.builder = label
                    f.note("builder", page_url, label)
                    break
    return f


# ─────────────────────────────────────────── the need catalog
# weight is how much this need is worth raising at all; `fits` is the set of
# business categories where it is a real problem rather than a technicality.
ALL = "*"


@dataclass(frozen=True)
class Need:
    code: str
    weight: int
    fa: str
    en: str
    fits: tuple[str, ...]


NEEDS: tuple[Need, ...] = (
    # ── no web presence at all: the need depends entirely on the trade
    Need("NEED_ORDER_PAGE", 92, "صفحه سفارش و منوی آنلاین",
         "Online menu and ordering", ("food", "bakery")),
    Need("NEED_APPOINTMENT", 90, "نوبت‌دهی آنلاین",
         "Online appointment booking", ("dental", "medical", "beauty", "fitness")),
    Need("NEED_RESERVATION", 88, "رزرو آنلاین",
         "Online reservation", ("hotel", "travel")),
    Need("NEED_CATALOG", 84, "کاتالوگ آنلاین محصولات",
         "Online product catalogue", ("furniture", "fashion", "tech", "auto", "retail")),
    Need("NEED_LISTINGS", 84, "نمایش آنلاین فایل‌ها و ملک‌ها",
         "Online listings", ("realestate",)),
    Need("NEED_CREDIBILITY", 78, "سایت رسمی برای اعتماد مشتری",
         "A credible official site", ("pro", "education", "pharmacy")),
    Need("NEED_FINDABLE", 74, "دیده‌شدن در جست‌وجوی گوگل",
         "Being findable on Google", (ALL,)),
    # ── a site exists but something concrete is wrong with it
    Need("NEED_SITE_FIX", 95, "سایت از دسترس خارج است",
         "The site is down", (ALL,)),
    Need("NEED_MOBILE", 86, "نمایش درست روی موبایل",
         "A site that works on phones", (ALL,)),
    Need("NEED_SPEED", 70, "سرعت بارگذاری سایت",
         "A site that loads quickly", (ALL,)),
    Need("NEED_HTTPS", 72, "گواهی امنیتی و حذف هشدار مرورگر",
         "HTTPS, so browsers stop warning visitors", (ALL,)),
    Need("NEED_REFRESH", 66, "به‌روزرسانی سایت قدیمی",
         "Refreshing an abandoned site", (ALL,)),
    Need("NEED_ADD_ORDER", 88, "افزودن سفارش آنلاین به سایت",
         "Adding online ordering", ("food", "bakery")),
    Need("NEED_ADD_APPOINTMENT", 86, "افزودن نوبت‌دهی به سایت",
         "Adding appointment booking", ("dental", "medical", "beauty", "fitness")),
    Need("NEED_ADD_RESERVATION", 85, "افزودن رزرو آنلاین به سایت",
         "Adding online reservation", ("hotel", "travel")),
    Need("NEED_ADD_CATALOG", 80, "افزودن محصولات به سایت",
         "Putting the products online", ("furniture", "fashion", "tech", "auto", "retail")),
    Need("NEED_PRICES", 58, "نمایش قیمت‌ها",
         "Showing prices", ("food", "bakery", "beauty", "fitness", "education")),
    Need("NEED_SEO", 56, "بهبود دیده‌شدن در گوگل",
         "Better search visibility", (ALL,)),
    Need("NEED_CONTACT_ON_SITE", 62, "راه تماس روشن روی سایت",
         "An obvious way to make contact", (ALL,)),
)
NEED_BY_CODE = {n.code: n for n in NEEDS}


def _fits(need: Need, category: str) -> bool:
    return ALL in need.fits or category in need.fits


@dataclass
class Finding:
    code: str
    weight: int
    fa: str
    evidence_url: str
    evidence: str          # the concrete thing that proved it, in Persian


def assess(category: str, facts: SiteFacts | None, has_site: bool,
           instagram: str = "") -> list[Finding]:
    """Rank what this business needs, strongest first.

    Every finding must be able to say what proved it. A need with no evidence is
    dropped rather than guessed at, because the whole value of this is being
    able to open a message with something true and checkable.
    """
    out: list[Finding] = []

    def add(code: str, evidence: str, url: str = "") -> None:
        need = NEED_BY_CODE.get(code)
        if need is None or not _fits(need, category) or not evidence:
            return
        out.append(Finding(need.code, need.weight, need.fa, url, evidence))

    # ── no website ────────────────────────────────────────────────
    if not has_site:
        where = f"صفحه اینستاگرام @{instagram}" if instagram else "اطلاعات روی نقشه"
        add("NEED_ORDER_PAGE",
            f"جایی برای دیدن منو و ثبت سفارش ندارید؛ {where} تنها راه است", "")
        add("NEED_APPOINTMENT",
            f"نوبت فقط تلفنی گرفته می‌شود؛ {where} تنها راه است", "")
        add("NEED_RESERVATION",
            f"رزرو فقط تلفنی انجام می‌شود؛ {where} تنها راه است", "")
        add("NEED_CATALOG",
            f"محصولات جایی برای دیده‌شدن ندارند جز {where}", "")
        add("NEED_LISTINGS",
            f"فایل‌ها و ملک‌ها جایی برای نمایش ندارند جز {where}", "")
        add("NEED_CREDIBILITY",
            f"هیچ صفحه رسمی‌ای برای معرفی خدمات ندارید؛ {where} تنها مرجع است", "")
        add("NEED_FINDABLE", "با جست‌وجوی نام کسب‌وکار در گوگل، سایتی پیدا نمی‌شود", "")
        out.sort(key=lambda f: -f.weight)
        return out

    if facts is None or not facts.reachable:
        if facts is not None and facts.status >= 400:
            add("NEED_SITE_FIX",
                f"سایت با خطای {facts.status} باز می‌شود", facts.final_url)
        out.sort(key=lambda f: -f.weight)
        return out

    u = facts.final_url
    # ── things that are concretely wrong ──────────────────────────
    if not facts.mobile_ready:
        add("NEED_MOBILE", "سایت برای موبایل طراحی نشده و روی گوشی درست باز نمی‌شود", u)
    if not facts.https:
        add("NEED_HTTPS", "سایت گواهی امنیتی ندارد و مرورگر پیام «ناامن» نشان می‌دهد", u)
    if facts.load_seconds > 4:
        add("NEED_SPEED", f"صفحه اصلی حدود {facts.load_seconds:.0f} ثانیه طول می‌کشد تا باز شود", u)
    if facts.stale_year:
        add("NEED_REFRESH", f"پایین سایت هنوز سال {facts.stale_year} نوشته شده", u)

    # ── things that are missing, and only matter for this trade ───
    if not facts.has_order:
        add("NEED_ADD_ORDER", "روی سایت راهی برای ثبت سفارش آنلاین نیست", u)
    if not facts.has_appointment:
        add("NEED_ADD_APPOINTMENT", "روی سایت راهی برای گرفتن نوبت نیست", u)
    if not facts.has_reservation:
        add("NEED_ADD_RESERVATION", "روی سایت راهی برای رزرو نیست", u)
    if not facts.has_catalog:
        add("NEED_ADD_CATALOG", "محصولات روی سایت فهرست نشده‌اند", u)
    if not facts.has_prices:
        add("NEED_PRICES", "هیچ قیمتی روی سایت نوشته نشده", u)
    if not (facts.has_contact_form or facts.has_whatsapp):
        add("NEED_CONTACT_ON_SITE", "روی سایت فرم تماس یا دکمه واتساپ نیست", u)
    if not facts.has_meta_desc and not facts.has_schema:
        add("NEED_SEO", "سایت توضیحات متا و داده ساختاریافته ندارد و در گوگل ضعیف دیده می‌شود", u)

    out.sort(key=lambda f: -f.weight)
    return out


# ─────────────────────────────────────────── the message
# One need per message. A list of five problems reads as a sales pitch and gets
# ignored; one specific observation reads as someone who actually looked.
OPENERS: dict[str, str] = {
    "NEED_ORDER_PAGE": "دیدم برای دیدن منو و سفارش دادن، جایی جز تماس تلفنی ندارید.",
    "NEED_APPOINTMENT": "دیدم نوبت گرفتن از {name} فقط تلفنی ممکن است.",
    "NEED_RESERVATION": "دیدم رزرو کردن در {name} فقط تلفنی انجام می‌شود.",
    "NEED_CATALOG": "دیدم محصولات {name} جایی برای دیده‌شدن ندارند.",
    "NEED_LISTINGS": "دیدم فایل‌های {name} جایی برای نمایش آنلاین ندارند.",
    "NEED_CREDIBILITY": "دنبال صفحه رسمی {name} گشتم و چیزی پیدا نکردم.",
    "NEED_FINDABLE": "اسم {name} را در گوگل جست‌وجو کردم و سایتی بالا نیامد.",
    "NEED_SITE_FIX": "سایت {domain} را باز کردم و بالا نیامد.",
    "NEED_MOBILE": "سایت {domain} را روی گوشی باز کردم و درست نمایش داده نشد.",
    "NEED_SPEED": "سایت {domain} را باز کردم و دیر بالا آمد.",
    "NEED_HTTPS": "سایت {domain} را باز کردم و مرورگر پیام «ناامن» نشان داد.",
    "NEED_REFRESH": "سایت {domain} را دیدم؛ چند سالی است به‌روز نشده.",
    "NEED_ADD_ORDER": "سایت {domain} را دیدم، ولی راهی برای ثبت سفارش آنلاین نداشت.",
    "NEED_ADD_APPOINTMENT": "سایت {domain} را دیدم، ولی نوبت‌دهی آنلاین نداشت.",
    "NEED_ADD_RESERVATION": "سایت {domain} را دیدم، ولی رزرو آنلاین نداشت.",
    "NEED_ADD_CATALOG": "سایت {domain} را دیدم، ولی محصولات روی آن فهرست نشده بودند.",
    "NEED_PRICES": "سایت {domain} را دیدم؛ هیچ قیمتی روی آن نوشته نشده بود.",
    "NEED_SEO": "سایت {domain} را دیدم؛ برای دیده‌شدن در گوگل تنظیم نشده.",
    "NEED_CONTACT_ON_SITE": "سایت {domain} را دیدم؛ راه تماس روشنی روی آن نبود.",
}

# Why it costs them something. This is the sentence that has to be true and
# concrete, not a benefit claim.
COSTS: dict[str, str] = {
    "NEED_ORDER_PAGE": "مشتری‌ای که شب یا ساعت شلوغی تصمیم می‌گیرد سفارش بدهد، معمولاً منتظر نمی‌ماند و از جای دیگری سفارش می‌دهد.",
    "NEED_APPOINTMENT": "کسی که شب تصمیم می‌گیرد نوبت بگیرد تا صبح منتظر می‌ماند، و خیلی‌ها تا صبح جای دیگری را پیدا می‌کنند.",
    "NEED_RESERVATION": "مسافری که شب برنامه‌ریزی می‌کند، همان‌جا رزرو می‌کند؛ اگر نشود، سراغ گزینه بعدی می‌رود.",
    "NEED_CATALOG": "کسی که قبل از آمدن می‌خواهد ببیند چه دارید، وقتی چیزی پیدا نکند معمولاً اصلاً نمی‌آید.",
    "NEED_LISTINGS": "مشتری امروز اول آنلاین نگاه می‌کند و بعد تماس می‌گیرد؛ بدون نمایش آنلاین، آن تماس اتفاق نمی‌افتد.",
    "NEED_CREDIBILITY": "برای خدماتی مثل کار شما، نبودن یک صفحه رسمی باعث می‌شود مشتری تازه تردید کند.",
    "NEED_FINDABLE": "هر کسی که اسم شما را شنیده و در گوگل جست‌وجو می‌کند، چیزی پیدا نمی‌کند.",
    "NEED_SITE_FIX": "کسی که از گوگل یا کارت ویزیت به سایت می‌رسد، صفحه خطا می‌بیند و برداشتش این است که کسب‌وکار دیگر فعال نیست.",
    "NEED_MOBILE": "بیشتر از ۸۰ درصد بازدیدها از گوشی است و گوگل هم سایت‌هایی را که روی موبایل خوب نیستند پایین‌تر نشان می‌دهد.",
    "NEED_SPEED": "هر ثانیه تأخیر بخشی از بازدیدکننده‌ها را قبل از دیدن صفحه از دست می‌دهد.",
    "NEED_HTTPS": "آن هشدار باعث می‌شود بخشی از مشتری‌ها قبل از دیدن صفحه، سایت را ببندند.",
    "NEED_REFRESH": "سال قدیمی پایین صفحه این حس را می‌دهد که کسب‌وکار دیگر فعال نیست.",
    "NEED_ADD_ORDER": "یعنی هر سفارشی که بیرون از ساعت کاری تصمیم گرفته می‌شود، از دست می‌رود.",
    "NEED_ADD_APPOINTMENT": "یعنی هر نوبتی که بیرون از ساعت کاری تصمیم گرفته می‌شود، از دست می‌رود.",
    "NEED_ADD_RESERVATION": "یعنی رزروهایی که شب تصمیم گرفته می‌شوند، به جای دیگری می‌رسند.",
    "NEED_ADD_CATALOG": "کسی که می‌خواهد ببیند چه دارید، چیزی پیدا نمی‌کند و تماس هم نمی‌گیرد.",
    "NEED_PRICES": "نبودن قیمت باعث می‌شود بخشی از مشتری‌ها اصلاً تماس نگیرند.",
    "NEED_SEO": "یعنی در جست‌وجوهایی که مشتری‌های شما انجام می‌دهند، رقیب‌ها بالاتر از شما دیده می‌شوند.",
    "NEED_CONTACT_ON_SITE": "بازدیدکننده‌ای که همان لحظه آماده تماس است، راهی پیدا نمی‌کند.",
}

# What you would do about it — named as a deliverable, not a capability list.
OFFERS: dict[str, str] = {
    "NEED_ORDER_PAGE": "یک صفحه منو با امکان ثبت سفارش که مستقیم به واتساپ خودتان وصل می‌شود",
    "NEED_APPOINTMENT": "یک صفحه نوبت‌دهی ساده که نوبت‌ها را مستقیم برای خودتان می‌فرستد",
    "NEED_RESERVATION": "یک صفحه رزرو ساده وصل به واتساپ یا پنل خودتان",
    "NEED_CATALOG": "یک کاتالوگ آنلاین از محصولات، قابل به‌روزرسانی توسط خودتان",
    "NEED_LISTINGS": "یک صفحه نمایش فایل‌ها با جست‌وجو و فیلتر",
    "NEED_CREDIBILITY": "یک سایت معرفی ساده و سریع با خدمات، سوابق و راه تماس",
    "NEED_FINDABLE": "یک سایت سبک که با نام کسب‌وکار در گوگل بالا بیاید",
    "NEED_SITE_FIX": "بررسی و راه‌اندازی دوباره سایت، یا یک نسخه تازه و سریع",
    "NEED_MOBILE": "بازطراحی موبایل‌پسند بدون از دست رفتن محتوای فعلی",
    "NEED_SPEED": "بهینه‌سازی سرعت صفحه",
    "NEED_HTTPS": "نصب گواهی امنیتی و رفع هشدار مرورگر",
    "NEED_REFRESH": "به‌روزرسانی و بازطراحی سایت فعلی",
    "NEED_ADD_ORDER": "افزودن ثبت سفارش آنلاین به همین سایت",
    "NEED_ADD_APPOINTMENT": "افزودن نوبت‌دهی آنلاین به همین سایت",
    "NEED_ADD_RESERVATION": "افزودن رزرو آنلاین به همین سایت",
    "NEED_ADD_CATALOG": "افزودن بخش محصولات به همین سایت",
    "NEED_PRICES": "افزودن بخش قیمت‌ها یا تعرفه خدمات",
    "NEED_SEO": "تنظیم سایت برای دیده‌شدن در گوگل",
    "NEED_CONTACT_ON_SITE": "افزودن فرم تماس و دکمه واتساپ به سایت",
}


# Instagram openers say where you were. You are messaging them from inside the
# thing you looked at, and saying so is most of what separates this from a bot.
IG_OPENERS: dict[str, str] = {
    "NEED_ORDER_PAGE": "صفحه‌تون رو دیدم. برای سفارش دادن، مشتری باید حتماً تماس بگیره یا دایرکت بده.",
    "NEED_APPOINTMENT": "صفحه‌تون رو دیدم. برای نوبت گرفتن راهی جز تماس یا دایرکت نیست.",
    "NEED_RESERVATION": "صفحه‌تون رو دیدم. برای رزرو، مشتری باید تماس بگیره یا دایرکت بده.",
    "NEED_CATALOG": "صفحه‌تون رو دیدم. محصولاتتون فقط توی پست‌هاست و جای دیگه‌ای نیست.",
    "NEED_LISTINGS": "صفحه‌تون رو دیدم. فایل‌ها فقط توی پست‌ها هستن و قابل جست‌وجو نیستن.",
    "NEED_CREDIBILITY": "صفحه‌تون رو دیدم. دنبال سایت رسمی‌تون گشتم و پیدا نکردم.",
    "NEED_FINDABLE": "صفحه‌تون رو دیدم، ولی اسمتون رو که در گوگل زدم چیزی بالا نیومد.",
}


def short_name(raw: str) -> str:
    """The name as you would say it out loud, mid-sentence.

    OSM names carry their own descriptor — "دکتر هانیه راز - جراح، دندانپزشک",
    "کلینیک دندانپزشکی آرت". Dropped whole into a sentence that reads
    "نوبت گرفتن از دکتر هانیه راز - جراح، دندانپزشک فقط تلفنی ممکن است", which
    is instantly recognisable as a mail merge. Keep the part before the dash.
    """
    name = (raw or "").strip()
    cut = re.split(r"\s+[-–—|]\s+", name)[0].strip()
    # Only take the short form if something recognisable is left of it.
    return cut if len(cut) >= 3 else name


def compose(name: str, domain: str, city: str, finding: Finding,
            sender: str, channel: str = "whatsapp") -> str:
    """Four lines: what I saw, what it costs, what I'd do, one question.

    The order matters. Opening with yourself is the thing everyone does and the
    reason most of these messages go unread, so the first line is about them and
    is something they can verify.

    The channel changes the register, not the content. A WhatsApp message is a
    note to a business and carries a signature. An Instagram DM from a stranger
    lands in Message Requests next to actual spam, so it has to be shorter, has
    to show immediately that a person looked at their page, and must not carry
    a signature block — that is precisely what makes a DM look forwarded.
    """
    ctx = {"name": short_name(name) or "کسب‌وکار شما", "domain": domain or "سایت شما",
           "city": city or "شیراز"}
    opener = OPENERS.get(finding.code, "به حضور اینترنتی {name} نگاهی انداختم.").format(**ctx)
    cost = COSTS.get(finding.code, "")
    offer = OFFERS.get(finding.code, "ساخت یا بهبود سایت")

    if channel == "instagram":
        ig = IG_OPENERS.get(finding.code, "")
        lines = [
            "سلام 👋",
            ig.format(**ctx) if ig else opener,
            cost,
            f"من سایت و اپلیکیشن برای کسب‌وکارهای {ctx['city']} می‌سازم — {offer}.",
            "اگر خواستید یک نمونه بفرستم؟",
        ]
    else:
        lines = [
            "سلام، وقت بخیر",
            opener,
            cost,
            f"من برای کسب‌وکارهای {ctx['city']} سایت می‌سازم و کاری که پیشنهاد می‌دهم مشخص است: {offer}.",
            "اگر مفید بود، یک نمونه کار و قیمتش را بفرستم؟",
            sender,
        ]
    return "\n".join(x for x in lines if x).strip()


# ─────────────────────────────────────────── entry point
async def research_lead(client: httpx.AsyncClient, lead: dict, ua: str) -> dict:
    """-> {need, need_fa, evidence, evidence_url, pages, findings}"""
    website = (lead.get("website") or "").strip()
    facts = None
    if website:
        facts = await crawl(client, website, ua)

    findings = assess(lead.get("category") or "", facts, bool(website),
                      lead.get("instagram") or "")
    if not findings:
        return {"need": "", "need_fa": "", "evidence": "", "evidence_url": "",
                "pages": 0, "findings": []}
    top = findings[0]
    return {
        "need": top.code,
        "need_fa": top.fa,
        "evidence": top.evidence,
        "evidence_url": top.evidence_url,
        "pages": len(facts.pages) if facts else 0,
        "findings": findings,
    }
