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
        "demo_url": "/static/demos/calcounter/index.html",
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
        "demo_url": "/static/demos/aura-stylist/index.html",
        "tech": "Flutter · Dart · SQLite · Camera",
        "price": 4000000, "currency": "IRT", "buyable": 1, "sort": 2,
    },
    {
        "title_en": "Crypto Trade Panel",
        "title_fa": "پنل معاملات کریپتو",
        "desc_en": ("Full-stack crypto trading terminal with live market data and charts, "
                    "wallet and portfolio analytics, money management, a trading journal, "
                    "backtesting and price alerts. React frontend, Node.js + SQLite backend."),
        "desc_fa": ("ترمینال معاملاتی فول‌استک کریپتو با دیتای زنده بازار و نمودار، تحلیل کیف پول و "
                    "پرتفوی، مدیریت سرمایه، ژورنال معاملات، بک‌تست و هشدار قیمت. "
                    "فرانت React و بک‌اند Node.js + SQLite."),
        "image": "/static/projects/trade-panel.png",
        "demo_url": "/static/demos/trade-panel/index.html",
        "tech": "React · Node.js · SQLite",
        "price": 9000000, "currency": "IRT", "buyable": 1, "sort": 3,
    },
    {
        "title_en": "TODO_Liat",
        "title_fa": "تودو لیات",
        "desc_en": ("Feature-rich Android to-do list app written in Java. Create tasks "
                    "with date, time and event labels, stored locally with Room (SQLite). "
                    "Exact alarms and notifications remind you at the due time — plus an "
                    "early reminder 10 minutes before — and survive device reboots. "
                    "Includes a calendar view that highlights every day with a task."),
        "desc_fa": ("اپ لیست کارهای اندرویدی کامل با جاوا. ساخت وظیفه با تاریخ، ساعت و برچسب "
                    "رویداد، ذخیره‌سازی محلی با Room (SQLite). آلارم دقیق و نوتیفیکیشن در زمان "
                    "سررسید — به‌علاوه یادآور ۱۰ دقیقه زودتر — حتی بعد از ری‌استارت گوشی. "
                    "همراه نمای تقویم که روزهای دارای وظیفه را مشخص می‌کند."),
        "image": "/static/projects/todo-liat.png",
        "demo_url": "/static/demos/todo-liat/index.html",
        "tech": "Java · Android · Room · AlarmManager",
        "price": 3000000, "currency": "IRT", "buyable": 1, "sort": 4,
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
        "demo_url": "/static/demos/terrain-painter/index.html",
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
        "demo_url": "/static/demos/sound-dash/index.html",
        "url": "",
        "tech": "Godot 4 · GDScript · Audio DSP",
        "price": 3000000, "currency": "IRT", "buyable": 1, "sort": 2,
    },
    {
        "title_en": "Shadow Runner",
        "title_fa": "شدو رانر",
        "desc_en": ("A cross-platform 3D stealth runner set in a city where safety moves "
                    "with the sun. Survive exposure, dash between shadows, collect relics "
                    "and master 1,000 deterministic levels across 50 districts. Includes "
                    "six characters, two camera views, touch controls and offline PWA support."),
        "desc_fa": ("یک رانر مخفی‌کاری سه‌بعدی چندسکویی در شهری که منطقه امن آن با خورشید جابه‌جا "
                    "می‌شود. بین سایه‌ها حرکت کنید، از نور جان سالم به در ببرید و در ۱۰۰۰ مرحله قطعی "
                    "در ۵۰ منطقه پیش بروید. دارای شش شخصیت، دو نمای دوربین، کنترل لمسی و اجرای آفلاین."),
        "image": "/static/projects/shadow-runner.svg",
        "demo_url": "/static/demos/shadow-runner/index.html",
        "url": "",
        "tech": "Three.js · JavaScript · Vite · Capacitor · PWA",
        "price": 0, "currency": "IRT", "buyable": 0, "sort": 3,
    },
]

BOTS = [
    {
        "title_en": "Channel Autopilot",
        "title_fa": "اتوپایلوت کانال",
        "desc_en": ("Runs Telegram channels automatically: ingests RSS, YouTube and public "
                    "Telegram sources, deduplicates stories, prepares rewritten and translated "
                    "drafts, then publishes on a schedule or sends them for admin approval."),
        "desc_fa": ("مدیریت خودکار کانال تلگرام: دریافت محتوا از RSS، یوتیوب و کانال‌های عمومی، "
                    "حذف مطالب تکراری، آماده‌سازی پیش‌نویس بازنویسی و ترجمه‌شده و انتشار زمان‌بندی‌شده یا "
                    "ارسال پیش‌نویس برای تأیید مدیر."),
        "image": "/static/projects/channel-autopilot.svg",
        "demo_url": "/static/demos/channel-autopilot/index.html",
        "url": "https://github.com/nima1991zare/Channel-Autopilot",
        "tech": "Python · aiogram · Telethon · SQLAlchemy",
        "price": 0, "currency": "IRT", "buyable": 0, "sort": 1,
    },
    {
        "title_en": "SubGate",
        "title_fa": "ساب‌گیت",
        "desc_en": ("Paid-channel subscription bot with automated watch-only USDT payments on "
                    "TRON and TON. It verifies transfers on-chain, issues single-use invites, "
                    "tracks renewals and removes expired members without handling private keys."),
        "desc_fa": ("ربات اشتراک کانال خصوصی با پرداخت خودکار USDT روی شبکه‌های TRON و TON. "
                    "تراکنش را روی زنجیره تأیید می‌کند، لینک دعوت یک‌بارمصرف می‌سازد، تمدیدها را "
                    "پیگیری می‌کند و بدون دسترسی به کلید خصوصی اعضای منقضی را حذف می‌کند."),
        "image": "/static/projects/subgate.svg",
        "demo_url": "/static/demos/subgate/index.html",
        "url": "https://github.com/nima1991zare/Telegram-Paid-Channel-Subscription-Bot-with-USDT-Auto-Payment",
        "tech": "Python · aiogram · USDT · TRON · TON · SQLAlchemy",
        "price": 0, "currency": "IRT", "buyable": 0, "sort": 2,
    },
    {
        "title_en": "Instagram DM Order Automation",
        "title_fa": "اتوماسیون سفارش دایرکت اینستاگرام",
        "desc_en": ("Persian-first sales workflow that answers product questions, captures "
                    "orders from Instagram DMs and sends each order to a Telegram admin bot for "
                    "approval, payment and fulfilment, with strict safety controls."),
        "desc_fa": ("فرایند فروش فارسی که به سؤال‌های محصول پاسخ می‌دهد، سفارش را از دایرکت "
                    "اینستاگرام ثبت می‌کند و برای تأیید، پرداخت و ارسال به ربات مدیریت تلگرام می‌فرستد؛ "
                    "همراه با کنترل‌های سخت‌گیرانه ایمنی."),
        "image": "/static/projects/instagram-dm-automation.svg",
        "demo_url": "/static/demos/instagram-dm-automation/index.html",
        "url": "https://github.com/nima1991zare/Instagram-DM-Order-Automation",
        "tech": "Python · aiogram · instagrapi · SQLAlchemy · Zarinpal",
        "price": 0, "currency": "IRT", "buyable": 0, "sort": 3,
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
        "demo_url": "/static/demos/fama/index.html",
        "url": "",
        "tech": "HTML · CSS · JavaScript · RTL",
        "price": 4000000, "currency": "IRT", "demo_only": 0, "sort": 1,
    },
    {
        "title_en": "Depoti", "title_fa": "دیپوتی",
        "desc_en": "", "desc_fa": "", "image": "/static/projects/depoti-site.png",
        "demo_url": "https://depoti.ir/", "url": "", "tech": "",
        "price": 0, "currency": "IRT", "demo_only": 1, "sort": 10,
    },
    {
        "title_en": "Weenk Creative Studio", "title_fa": "استودیو وینک",
        "desc_en": "", "desc_fa": "", "image": "/static/projects/weenk-site.png",
        "demo_url": "https://weenk.ir/", "url": "", "tech": "",
        "price": 0, "currency": "IRT", "demo_only": 1, "sort": 11,
    },
    {
        "title_en": "ORO Coffee", "title_fa": "قهوه ارو",
        "desc_en": "", "desc_fa": "", "image": "/static/projects/oro-site.png",
        "demo_url": "https://orocoffee.ir/", "url": "", "tech": "",
        "price": 0, "currency": "IRT", "demo_only": 1, "sort": 12,
    },
    {
        "title_en": "Coffeete", "title_fa": "کافیته",
        "desc_en": "", "desc_fa": "", "image": "/static/projects/coffete-site.png",
        "demo_url": "/static/demos/coffete/index.html", "url": "", "tech": "",
        "price": 0, "currency": "IRT", "demo_only": 1, "sort": 13,
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
        conn.execute(
            "UPDATE telegram_bots SET title_en=? WHERE title_en LIKE ?",
            ("Channel Autopilot", "% Channel Autopilot"))

        app_cols = ["title_en", "title_fa", "desc_en", "desc_fa", "image", "tech",
                    "demo_url", "price", "currency", "buyable", "sort"]
        game_cols = app_cols[:5] + ["url", "tech", "demo_url", "price", "currency",
                                    "buyable", "sort"]
        bot_cols = game_cols
        web_cols = ["title_en", "title_fa", "desc_en", "desc_fa", "image", "url", "tech",
                    "demo_url", "demo_only", "price", "currency", "sort"]

        for item in APPS:
            print("apps:", item["title_en"], "->", upsert(conn, "apps", item, app_cols))
        for item in GAMES:
            print("games:", item["title_en"], "->", upsert(conn, "games", item, game_cols))
        for item in BOTS:
            print("bots:", item["title_en"], "->", upsert(conn, "telegram_bots", item, bot_cols))
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
