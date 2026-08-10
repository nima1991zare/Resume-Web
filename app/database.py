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

SEED_BRANDS = [
    ("Brand One", "", ""),
    ("Brand Two", "", ""),
    ("Brand Three", "", ""),
]


def init_db() -> None:
    conn = get_db()
    try:
        conn.executescript(SCHEMA)
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
        if conn.execute("SELECT COUNT(*) c FROM brands").fetchone()["c"] == 0:
            conn.executemany("INSERT INTO brands(name,logo,url) VALUES(?,?,?)", SEED_BRANDS)
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
