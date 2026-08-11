# -*- coding: utf-8 -*-
"""Seed/repair the real portfolio projects in the database.

Idempotent UPSERT: if an item with the same English title exists, its texts,
image, tech and price are UPDATED (this also repairs any corrupted rows);
otherwise it is inserted.

Run from the project root:  python tools/seed_projects.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.database import get_db, init_db

APPS = [
    {
        "title_en": "CalCounter",
        "title_fa": "کال‌کانتر",
        "desc_en": ("Complete calorie & nutrition tracker. Food diary with 35+ tracked "
                    "micronutrients, barcode scanner, recipes, exercise, water and "
                    "biometrics — everything stored offline in SQLite. Cross-platform "
                    "Flutter app for Android, iOS and Windows."),
        "desc_fa": ("ردیاب کامل کالری و تغذیه. دفترچه غذایی با بیش از ۳۵ ریزمغذی، اسکنر بارکد، "
                    "دستور پخت، ورزش، آب و شاخص‌های بدنی — همه به‌صورت آفلاین در SQLite. "
                    "اپ فلاتر چندسکویی برای اندروید، iOS و ویندوز."),
        "image": "/static/projects/calcounter.png",
        "tech": "Flutter · Dart · SQLite",
        "price": 4500000, "currency": "IRT", "buyable": 1, "sort": 1,
    },
    {
        "title_en": "Aura Stylist",
        "title_fa": "آئورا استایلیست",
        "desc_en": ("Your on-device personal stylist. Rates your outfits with the camera, "
                    "gives colour and body-type advice, and builds outfit combinations "
                    "from your own wardrobe. 100% private — no cloud, everything runs "
                    "and stays on the phone."),
        "desc_fa": ("استایلیست شخصی روی گوشی شما. با دوربین به استایل شما امتیاز می‌دهد، "
                    "توصیه رنگ و فرم بدن ارائه می‌کند و از کمد لباس خودتان ترکیب پیشنهاد می‌دهد. "
                    "کاملاً خصوصی — بدون کلاود، همه‌چیز روی گوشی."),
        "image": "/static/projects/aura-stylist.png",
        "tech": "Flutter · Dart · SQLite · Camera",
        "price": 4000000, "currency": "IRT", "buyable": 1, "sort": 2,
    },
    {
        "title_en": "Crypto Trade Panel",
        "title_fa": "پنل معاملات کریپتو",
        "desc_en": ("Full-stack crypto trading terminal: live market data and charts, "
                    "AI chart-image analysis, wallet & portfolio analytics, money "
                    "management, trading journal, backtesting and price alerts — with a "
                    "built-in AI trading assistant. React frontend, Node.js + SQLite backend."),
        "desc_fa": ("ترمینال معاملاتی فول‌استک کریپتو: دیتای زنده بازار و نمودار، تحلیل تصویر چارت با "
                    "هوش مصنوعی، تحلیل کیف پول و پرتفوی، مدیریت سرمایه، ژورنال معاملات، بک‌تست و "
                    "هشدار قیمت — همراه دستیار معاملاتی هوشمند. فرانت React و بک‌اند Node.js + SQLite."),
        "image": "/static/projects/trade-panel.png",
        "tech": "React · Node.js · SQLite · AI",
        "price": 9000000, "currency": "IRT", "buyable": 1, "sort": 3,
    },
]

GAMES = [
    {
        "title_en": "Terrain Painter",
        "title_fa": "نقاش زمین",
        "desc_en": ("Draw the ground under a rolling ball to keep it alive. Ink is limited, "
                    "strokes crumble after seconds, and the physics run at a fixed 120 Hz. "
                    "A complete HTML5 arcade game in a single file — touch and mouse ready, "
                    "zero dependencies."),
        "desc_fa": ("زیر توپِ در حال حرکت زمین بکشید تا زنده بماند. جوهر محدود است، خط‌ها بعد از چند "
                    "ثانیه فرو می‌ریزند و فیزیک بازی با نرخ ثابت ۱۲۰ هرتز اجرا می‌شود. یک بازی آرکید "
                    "کامل HTML5 در یک فایل — سازگار با لمس و ماوس، بدون هیچ وابستگی."),
        "image": "/static/projects/terrain-painter.png",
        "url": "",
        "tech": "HTML5 Canvas · JavaScript · Web Audio",
        "price": 1500000, "currency": "IRT", "buyable": 1, "sort": 1,
    },
    {
        "title_en": "Sound Dash",
        "title_fa": "ساند دَش",
        "desc_en": ("A 3D lane-runner driven by YOUR music. Pick any song on your device — "
                    "the game analyses beats, BPM and energy offline, then builds an obstacle "
                    "course perfectly synced to the track. Endless content, fully offline. "
                    "Built in Godot 4."),
        "desc_fa": ("یک بازی سه‌بعدی لِین‌رانر که با موسیقیِ خودِ شما اجرا می‌شود. هر آهنگی را انتخاب کنید — "
                    "بازی ضرب‌ها، BPM و انرژی را آفلاین تحلیل می‌کند و مسیر موانع را دقیقاً هماهنگ با آهنگ "
                    "می‌سازد. محتوای بی‌پایان، کاملاً آفلاین. ساخته‌شده با Godot 4."),
        "image": "/static/projects/sound-dash.png",
        "url": "",
        "tech": "Godot 4 · GDScript · Audio DSP",
        "price": 3000000, "currency": "IRT", "buyable": 1, "sort": 2,
    },
]

WEBSITES = [
    {
        "title_en": "FAMA Store",
        "title_fa": "فروشگاه فاما",
        "desc_en": ("Persian RTL e-commerce storefront for original cosmetics: category "
                    "browsing, product search, product pages, shopping cart and special "
                    "offers. Hand-coded HTML/CSS/JavaScript — fast, framework-free and "
                    "fully responsive."),
        "desc_fa": ("فروشگاه اینترنتی لوازم آرایشی اورجینال با طراحی راست‌به‌چپ: دسته‌بندی محصولات، "
                    "جستجو، صفحه محصول، سبد خرید و پیشنهادهای ویژه. کدنویسی دستی با HTML/CSS/JS — "
                    "سریع، بدون فریم‌ورک و کاملاً واکنش‌گرا."),
        "image": "/static/projects/fama.png",
        "url": "",
        "tech": "HTML · CSS · JavaScript · RTL",
        "price": 4000000, "currency": "IRT", "sort": 1,
    },
]

PLACEHOLDER_APPS = ("Inventory Manager Pro", "Smart POS System")
PLACEHOLDER_WEBSITES = ("Restaurant Ordering Website", "Corporate Landing Page")


def upsert(conn, table, item, cols):
    exists = conn.execute(
        f"SELECT id FROM {table} WHERE title_en=?", (item["title_en"],)).fetchone()
    if exists:
        sets = ",".join(f"{c}=:{c}" for c in cols if c != "title_en")
        conn.execute(f"UPDATE {table} SET {sets}, active=1 WHERE title_en=:title_en", item)
        return "updated"
    fields = ",".join(cols) + ",active"
    values = ",".join(f":{c}" for c in cols) + ",1"
    conn.execute(f"INSERT INTO {table}({fields}) VALUES({values})", item)
    return "inserted"


def seed():
    init_db()
    conn = get_db()
    try:
        conn.execute(
            f"UPDATE apps SET active=0 WHERE title_en IN ({','.join('?' * len(PLACEHOLDER_APPS))})",
            PLACEHOLDER_APPS)
        conn.execute(
            f"UPDATE websites SET active=0 WHERE title_en IN ({','.join('?' * len(PLACEHOLDER_WEBSITES))})",
            PLACEHOLDER_WEBSITES)

        app_cols = ["title_en", "title_fa", "desc_en", "desc_fa", "image", "tech",
                    "price", "currency", "buyable", "sort"]
        game_cols = app_cols[:5] + ["url", "tech", "price", "currency", "buyable", "sort"]
        web_cols = ["title_en", "title_fa", "desc_en", "desc_fa", "image", "url", "tech",
                    "price", "currency", "sort"]

        for item in APPS:
            print("apps:", item["title_en"], "->", upsert(conn, "apps", item, app_cols))
        for item in GAMES:
            print("games:", item["title_en"], "->", upsert(conn, "games", item, game_cols))
        for item in WEBSITES:
            print("websites:", item["title_en"], "->", upsert(conn, "websites", item, web_cols))
        conn.commit()

        # verify Persian text is intact (no mojibake)
        row = conn.execute("SELECT title_fa FROM games WHERE title_en='Terrain Painter'").fetchone()
        ok = row and row["title_fa"] == "نقاش زمین"
        print("persian integrity check:", "OK" if ok else "FAILED")
    finally:
        conn.close()


if __name__ == "__main__":
    seed()
