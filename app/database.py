"""SQLite database layer — schema, connection helpers and seed data."""
import sqlite3
import hashlib
import os
import secrets
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "site.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def hash_password(password: str, salt: str | None = None) -> str:
    if salt is None:
        salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000)
    return f"{salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, _ = stored.split("$", 1)
    except ValueError:
        return False
    return secrets.compare_digest(hash_password(password, salt), stored)


SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS apps (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    title_en  TEXT NOT NULL,
    title_fa  TEXT NOT NULL DEFAULT '',
    desc_en   TEXT NOT NULL DEFAULT '',
    desc_fa   TEXT NOT NULL DEFAULT '',
    image     TEXT NOT NULL DEFAULT '',
    tech      TEXT NOT NULL DEFAULT '',
    demo_url  TEXT NOT NULL DEFAULT '',
    price     REAL NOT NULL DEFAULT 0,
    currency  TEXT NOT NULL DEFAULT 'USD',
    buyable   INTEGER NOT NULL DEFAULT 1,
    sort      INTEGER NOT NULL DEFAULT 0,
    active    INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS games (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    title_en  TEXT NOT NULL,
    title_fa  TEXT NOT NULL DEFAULT '',
    desc_en   TEXT NOT NULL DEFAULT '',
    desc_fa   TEXT NOT NULL DEFAULT '',
    image     TEXT NOT NULL DEFAULT '',
    url       TEXT NOT NULL DEFAULT '',
    tech      TEXT NOT NULL DEFAULT '',
    demo_url  TEXT NOT NULL DEFAULT '',
    price     REAL NOT NULL DEFAULT 0,
    currency  TEXT NOT NULL DEFAULT 'USD',
    buyable   INTEGER NOT NULL DEFAULT 1,
    sort      INTEGER NOT NULL DEFAULT 0,
    active    INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS telegram_bots (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    title_en  TEXT NOT NULL,
    title_fa  TEXT NOT NULL DEFAULT '',
    desc_en   TEXT NOT NULL DEFAULT '',
    desc_fa   TEXT NOT NULL DEFAULT '',
    image     TEXT NOT NULL DEFAULT '',
    url       TEXT NOT NULL DEFAULT '',
    tech      TEXT NOT NULL DEFAULT '',
    demo_url  TEXT NOT NULL DEFAULT '',
    price     REAL NOT NULL DEFAULT 0,
    currency  TEXT NOT NULL DEFAULT 'USD',
    buyable   INTEGER NOT NULL DEFAULT 1,
    sort      INTEGER NOT NULL DEFAULT 0,
    active    INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS websites (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    title_en  TEXT NOT NULL,
    title_fa  TEXT NOT NULL DEFAULT '',
    desc_en   TEXT NOT NULL DEFAULT '',
    desc_fa   TEXT NOT NULL DEFAULT '',
    image     TEXT NOT NULL DEFAULT '',
    url       TEXT NOT NULL DEFAULT '',
    tech      TEXT NOT NULL DEFAULT '',
    demo_url  TEXT NOT NULL DEFAULT '',
    demo_only INTEGER NOT NULL DEFAULT 0,
    price     REAL NOT NULL DEFAULT 0,
    currency  TEXT NOT NULL DEFAULT 'USD',
    sort      INTEGER NOT NULL DEFAULT 0,
    active    INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS brands (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    name   TEXT NOT NULL,
    logo   TEXT NOT NULL DEFAULT '',
    url    TEXT NOT NULL DEFAULT '',
    sort   INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS messages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    email      TEXT NOT NULL DEFAULT '',
    phone      TEXT NOT NULL DEFAULT '',
    subject    TEXT NOT NULL DEFAULT '',
    message    TEXT NOT NULL,
    read       INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS visits (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    path       TEXT NOT NULL DEFAULT '/',
    lang       TEXT NOT NULL DEFAULT 'en',
    referrer   TEXT NOT NULL DEFAULT '',
    ua         TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sessions (
    token      TEXT PRIMARY KEY,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

DEFAULT_SETTINGS = {
    "admin_user": "admin",
    # default password: admin123  (change it from the admin panel!)
    "site_title_en": "Nima — Full-Stack Developer",
    "site_title_fa": "نیما — توسعه‌دهنده فول‌استک",
    "about_en": (
        "I'm Nima — a full-stack developer with internationally certified expertise in "
        "Python and Java. I hold a Bachelor's degree in Computer Engineering and I'm "
        "currently pursuing my Master's in the same field. I build complete products "
        "from zero to launch: clean architecture, robust backends, SQL & MongoDB "
        "databases, and pixel-perfect frontends with HTML, CSS and JavaScript. I'm also "
        "proficient in Photoshop, so every visual asset — from UI graphics to full "
        "image editing — is crafted in-house. One person, the whole stack."
    ),
    "about_fa": (
        "من نیما هستم — توسعه‌دهنده فول‌استک با مدرک بین‌المللی پایتون و جاوا. "
        "مدرک کارشناسی مهندسی کامپیوتر دارم و در حال حاضر در مقطع کارشناسی ارشد همین رشته تحصیل می‌کنم. "
        "محصولات را از صفر تا صد می‌سازم: معماری تمیز، بک‌اند قدرتمند، پایگاه‌داده‌های SQL و MongoDB "
        "و فرانت‌اند دقیق با HTML، CSS و جاوااسکریپت. "
        "به فتوشاپ هم مسلط هستم؛ بنابراین تمام گرافیک‌ها و تصاویر پروژه را خودم طراحی و ویرایش می‌کنم. "
        "یک نفر، تمام مسیر توسعه."
    ),
    "phone": "+98 900 000 0000",
    "email": "nima@example.com",
    "telegram": "",
    "github": "",
    "linkedin": "",
    "whatsapp": "",
}

SEED_APPS = [
    ("Inventory Manager Pro", "مدیریت انبار حرفه‌ای",
     "Desktop + web inventory system with barcode support, reports and multi-user roles.",
     "سیستم مدیریت انبار دسکتاپ و وب با پشتیبانی بارکد، گزارش‌گیری و نقش‌های چندکاربره.",
     "", "Python · Java · SQL", 499, "USD"),
    ("Smart POS System", "سیستم فروش هوشمند",
     "Point-of-sale application with real-time dashboard, invoicing and MongoDB sync.",
     "اپلیکیشن صندوق فروش با داشبورد لحظه‌ای، صدور فاکتور و همگام‌سازی MongoDB.",
     "", "Java · MongoDB · JS", 699, "USD"),
]

SEED_WEBSITES = [
    ("Restaurant Ordering Website", "وب‌سایت سفارش رستوران",
     "Full online-ordering site with menu management, cart and admin dashboard.",
     "سایت سفارش آنلاین کامل با مدیریت منو، سبد خرید و پنل مدیریت.",
     "", "", "Python · JS · SQL", 350, "USD"),
    ("Corporate Landing Page", "لندینگ شرکتی",
     "High-performance corporate site with CMS, SEO structure and custom animations.",
     "سایت شرکتی پرسرعت با سیستم مدیریت محتوا، ساختار سئو و انیمیشن‌های اختصاصی.",
     "", "", "HTML · CSS · JS", 200, "USD"),
]

FEATURED_GAMES = [
    ("Shadow Runner", "شدو رانر",
     "A cross-platform 3D stealth runner with six characters, two camera views and 1,000 deterministic levels across 50 districts.",
     "یک رانر مخفی‌کاری سه‌بعدی چندسکویی با شش شخصیت، دو نمای دوربین و ۱۰۰۰ مرحله قطعی در ۵۰ منطقه.",
     "/static/projects/shadow-runner.svg", "",
     "Three.js · JavaScript · Vite · Capacitor · PWA",
     "/static/demos/shadow-runner/index.html", 0, "IRT", 0, 3),
]

FEATURED_BOTS = [
    ("Channel Autopilot", "اتوپایلوت کانال",
     "Automates Telegram content ingestion, deduplication, draft preparation, approval and scheduled publishing.",
     "دریافت محتوا، حذف موارد تکراری، آماده‌سازی پیش‌نویس، تأیید و انتشار زمان‌بندی‌شده کانال تلگرام.",
     "/static/projects/channel-autopilot.svg",
     "https://github.com/nima1991zare/Channel-Autopilot",
     "Python · aiogram · Telethon · SQLAlchemy",
     "/static/demos/channel-autopilot/index.html", 0, "IRT", 0, 1),
    ("SubGate", "ساب‌گیت",
     "Paid-channel subscriptions with watch-only USDT verification on TRON and TON, renewals and automatic expiry handling.",
     "اشتراک کانال خصوصی با تأیید بدون کلید پرداخت USDT روی TRON و TON، تمدید و مدیریت خودکار انقضا.",
     "/static/projects/subgate.svg",
     "https://github.com/nima1991zare/Telegram-Paid-Channel-Subscription-Bot-with-USDT-Auto-Payment",
     "Python · aiogram · USDT · TRON · TON · SQLAlchemy",
     "/static/demos/subgate/index.html", 0, "IRT", 0, 2),
    ("Instagram DM Order Automation", "اتوماسیون سفارش دایرکت اینستاگرام",
     "Persian-first product replies and order capture from Instagram DMs, managed through a Telegram admin bot.",
     "پاسخ‌گویی فارسی و ثبت سفارش از دایرکت اینستاگرام با مدیریت کامل از طریق ربات تلگرام.",
     "/static/projects/instagram-dm-automation.svg",
     "https://github.com/nima1991zare/Instagram-DM-Order-Automation",
     "Python · aiogram · instagrapi · SQLAlchemy · Zarinpal",
     "/static/demos/instagram-dm-automation/index.html", 0, "IRT", 0, 3),
]

FEATURED_WEBSITES = [
    ("KAVA Market", "کاوا مارکت",
     "A streamlined hospitality marketplace for sourcing beans, ingredients, packaging and cafe equipment. Fast category browsing, smart search, delivery planning and order tracking keep daily purchasing simple.",
     "مارکت‌پلیس یکپارچه برای تأمین دانه قهوه، مواد اولیه، بسته‌بندی و تجهیزات کافه. دسته‌بندی سریع، جستجوی هوشمند، برنامه‌ریزی ارسال و پیگیری سفارش، خرید روزانه را ساده می‌کند.",
     "/static/projects/kava-market.svg", "", "HTML · CSS · JavaScript · RTL",
     "/static/demos/kava-market/index.html", 0, "IRT", 0, 10),
    ("Motive Studio", "استودیو موتیو",
     "An expressive portfolio for a multidisciplinary creative studio. A playful modular layout brings together brand strategy, campaigns, digital design, selected work and a clear collaboration process.",
     "پورتفولیوی پویا برای یک استودیوی خلاق چندتخصصی. چیدمان ماژولار و بازیگوش، استراتژی برند، کمپین‌ها، طراحی دیجیتال، پروژه‌های منتخب و فرایند همکاری را کنار هم قرار می‌دهد.",
     "/static/projects/motive-studio.svg", "", "HTML · CSS · JavaScript · RTL",
     "/static/demos/motive-studio/index.html", 0, "IRT", 0, 11),
    ("Serein Coffee", "قهوه سرین",
     "An editorial storefront for a small-batch coffee roaster, pairing origin stories and tasting notes with a calm shopping flow. The warm, tactile interface stays focused from discovery to checkout.",
     "فروشگاهی با حال‌وهوای ادیتوریال برای قهوه‌های رست محدود که داستان خاستگاه و نت‌های طعمی را با خریدی آرام و روان ترکیب می‌کند. رابط گرم و ملموس از کشف محصول تا پرداخت متمرکز باقی می‌ماند.",
     "/static/projects/serein-coffee.svg", "", "HTML · CSS · JavaScript · RTL",
     "/static/demos/serein-coffee/index.html", 0, "IRT", 0, 12),
    ("ROVA Coffee", "قهوه رووا",
     "A modern coffee shop with guided product discovery for beans, brewers and accessories. Useful filters, brew recommendations, account tools and a persistent offline-ready cart support confident purchases.",
     "فروشگاه مدرن قهوه با مسیر انتخاب راهنما برای دانه‌ها، ابزارهای دم‌آوری و لوازم جانبی. فیلترهای کاربردی، پیشنهاد دم‌آوری، ابزارهای حساب کاربری و سبد خرید آفلاین، انتخاب مطمئن‌تری می‌سازند.",
     "/static/projects/rova-coffee.svg", "", "HTML · CSS · JavaScript · PWA · RTL",
     "/static/demos/rova-coffee/index.html", 0, "IRT", 0, 13),
]

FEATURED_BRANDS = [
    ("Depoti", "/static/projects/depoti-site.png", "https://depoti.ir/", 1),
    ("Weenk.ir", "/static/projects/weenk-site.png", "https://weenk.ir/", 2),
    ("ORO Coffee", "/static/projects/oro-site.png", "https://orocoffee.ir/", 3),
    ("Coffite", "/static/projects/coffete-site.png", "https://coffite.ir/", 4),
]

SEED_BRANDS = []


def init_db() -> None:
    conn = get_db()
    try:
        conn.executescript(SCHEMA)
        # migration: add demo_url to content tables created before the column existed
        for table in ("apps", "games", "telegram_bots", "websites"):
            cols = [r["name"] for r in conn.execute(f"PRAGMA table_info({table})")]
            if "demo_url" not in cols:
                conn.execute(
                    f"ALTER TABLE {table} ADD COLUMN demo_url TEXT NOT NULL DEFAULT ''")
        website_cols_existing = [
            r["name"] for r in conn.execute("PRAGMA table_info(websites)")]
        if "demo_only" not in website_cols_existing:
            conn.execute(
                "ALTER TABLE websites ADD COLUMN demo_only INTEGER NOT NULL DEFAULT 0")
        # Preserve existing row IDs when portfolio samples are renamed.
        conn.execute("UPDATE websites SET title_en='KAVA Market' WHERE title_en='Depoti'")
        conn.execute("UPDATE websites SET title_en='Motive Studio' WHERE title_en='Weenk Creative Studio'")
        conn.execute("UPDATE websites SET title_en='Serein Coffee' WHERE title_en='ORO Coffee'")
        conn.execute("UPDATE websites SET title_en='ROVA Coffee' WHERE title_en IN ('Coffeete','Coffite')")
        conn.execute("UPDATE brands SET name='Coffite' WHERE name='Coffeete'")
        # settings seed (only insert missing keys)
        for k, v in DEFAULT_SETTINGS.items():
            conn.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?, ?)", (k, v))
        cur = conn.execute("SELECT value FROM settings WHERE key='admin_pass'")
        if cur.fetchone() is None:
            conn.execute(
                "INSERT INTO settings(key, value) VALUES('admin_pass', ?)",
                (hash_password("admin123"),),
            )
        # content seed only when tables are empty
        if conn.execute("SELECT COUNT(*) c FROM apps").fetchone()["c"] == 0:
            conn.executemany(
                "INSERT INTO apps(title_en,title_fa,desc_en,desc_fa,image,tech,price,currency) "
                "VALUES(?,?,?,?,?,?,?,?)", SEED_APPS)
        if conn.execute("SELECT COUNT(*) c FROM websites").fetchone()["c"] == 0:
            conn.executemany(
                "INSERT INTO websites(title_en,title_fa,desc_en,desc_fa,image,url,tech,price,currency) "
                "VALUES(?,?,?,?,?,?,?,?,?)", SEED_WEBSITES)
        featured_cols = (
            "title_en,title_fa,desc_en,desc_fa,image,url,tech,demo_url,"
            "price,currency,buyable,sort"
        )
        conn.execute(
            "UPDATE telegram_bots SET title_en=? WHERE title_en LIKE ?",
            ("Channel Autopilot", "% Channel Autopilot"),
        )
        for row in FEATURED_GAMES:
            if conn.execute(
                    "SELECT 1 FROM games WHERE title_en=?", (row[0],)).fetchone() is None:
                conn.execute(
                    f"INSERT INTO games({featured_cols}) VALUES({','.join('?' * 12)})", row)
        for row in FEATURED_BOTS:
            existing = conn.execute(
                "SELECT id FROM telegram_bots WHERE title_en=?", (row[0],)).fetchone()
            if existing is None:
                conn.execute(
                    f"INSERT INTO telegram_bots({featured_cols}) VALUES({','.join('?' * 12)})", row)
            else:
                conn.execute(
                    "UPDATE telegram_bots SET title_fa=?,desc_en=?,desc_fa=?,image=?,url=?,tech=?,"
                    "demo_url=?,price=?,currency=?,buyable=?,sort=?,active=1 WHERE id=?",
                    row[1:] + (existing["id"],))
        website_cols = (
            "title_en,title_fa,desc_en,desc_fa,image,url,tech,demo_url,"
            "price,currency,demo_only,sort"
        )
        for row in FEATURED_WEBSITES:
            if conn.execute(
                    "SELECT 1 FROM websites WHERE title_en=?", (row[0],)).fetchone() is None:
                conn.execute(
                    f"INSERT INTO websites({website_cols}) VALUES({','.join('?' * 12)})", row)
            else:
                conn.execute(
                    "UPDATE websites SET title_fa=?,desc_en=?,desc_fa=?,image=?,url=?,tech=?,"
                    "demo_url=?,price=?,currency=?,demo_only=?,sort=?,active=1 WHERE title_en=?",
                    row[1:] + (row[0],))
        conn.execute(
            "UPDATE websites SET active=0 WHERE title_en IN "
            "('Restaurant Ordering Website','Corporate Landing Page')")
        if conn.execute("SELECT COUNT(*) c FROM brands").fetchone()["c"] == 0:
            conn.executemany("INSERT INTO brands(name,logo,url) VALUES(?,?,?)", SEED_BRANDS)
        conn.execute(
            "UPDATE brands SET active=0 WHERE name IN ('Brand One','Brand Two','Brand Three')")
        for name, image, url, sort in FEATURED_BRANDS:
            existing = conn.execute(
                "SELECT id FROM brands WHERE lower(name)=lower(?)", (name,)).fetchone()
            if existing:
                conn.execute(
                    "UPDATE brands SET logo=?,url=?,sort=?,active=1 WHERE id=?",
                    (image, url, sort, existing["id"]))
            else:
                conn.execute(
                    "INSERT INTO brands(name,logo,url,sort,active) VALUES(?,?,?,?,1)",
                    (name, image, url, sort))
        conn.commit()
    finally:
        conn.close()


def get_setting(conn: sqlite3.Connection, key: str, default: str = "") -> str:
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO settings(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )
