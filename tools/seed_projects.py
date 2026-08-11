# -*- coding: utf-8 -*-
"""Seed the real portfolio projects into the database (idempotent â€” safe to
re-run; existing items with the same English title are skipped).

Run from the project root:  python tools/seed_projects.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.database import get_db, init_db

APPS = [
    {
        "title_en": "CalCounter",
        "title_fa": "Ú©Ø§Ù„â€ŒÚ©Ø§Ù†ØªØ±",
        "desc_en": ("Complete calorie & nutrition tracker. Food diary with 35+ tracked "
                    "micronutrients, barcode scanner, recipes, exercise, water and "
                    "biometrics â€” everything stored offline in SQLite. Cross-platform "
                    "Flutter app for Android, iOS and Windows."),
        "desc_fa": ("Ø±Ø¯ÛŒØ§Ø¨ Ú©Ø§Ù…Ù„ Ú©Ø§Ù„Ø±ÛŒ Ùˆ ØªØºØ°ÛŒÙ‡. Ø¯ÙØªØ±Ú†Ù‡ ØºØ°Ø§ÛŒÛŒ Ø¨Ø§ Ø¨ÛŒØ´ Ø§Ø² Û³Ûµ Ø±ÛŒØ²Ù…ØºØ°ÛŒØŒ Ø§Ø³Ú©Ù†Ø± Ø¨Ø§Ø±Ú©Ø¯ØŒ "
                    "Ø¯Ø³ØªÙˆØ± Ù¾Ø®ØªØŒ ÙˆØ±Ø²Ø´ØŒ Ø¢Ø¨ Ùˆ Ø´Ø§Ø®Øµâ€ŒÙ‡Ø§ÛŒ Ø¨Ø¯Ù†ÛŒ â€” Ù‡Ù…Ù‡ Ø¨Ù‡â€ŒØµÙˆØ±Øª Ø¢ÙÙ„Ø§ÛŒÙ† Ø¯Ø± SQLite. "
                    "Ø§Ù¾ ÙÙ„Ø§ØªØ± Ú†Ù†Ø¯Ø³Ú©ÙˆÛŒÛŒ Ø¨Ø±Ø§ÛŒ Ø§Ù†Ø¯Ø±ÙˆÛŒØ¯ØŒ iOS Ùˆ ÙˆÛŒÙ†Ø¯ÙˆØ²."),
        "image": "/static/projects/calcounter.png",
        "tech": "Flutter Â· Dart Â· SQLite",
        "price": 4500000, "currency": "IRT", "buyable": 1, "sort": 1,
    },
    {
        "title_en": "Aura Stylist",
        "title_fa": "Ø¢Ø¦ÙˆØ±Ø§ Ø§Ø³ØªØ§ÛŒÙ„ÛŒØ³Øª",
        "desc_en": ("Your on-device personal stylist. Rates your outfits with the camera, "
                    "gives colour and body-type advice, and builds outfit combinations "
                    "from your own wardrobe. 100% private â€” no cloud, everything runs "
                    "and stays on the phone."),
        "desc_fa": ("Ø§Ø³ØªØ§ÛŒÙ„ÛŒØ³Øª Ø´Ø®ØµÛŒ Ø±ÙˆÛŒ Ú¯ÙˆØ´ÛŒ Ø´Ù…Ø§. Ø¨Ø§ Ø¯ÙˆØ±Ø¨ÛŒÙ† Ø¨Ù‡ Ø§Ø³ØªØ§ÛŒÙ„ Ø´Ù…Ø§ Ø§Ù…ØªÛŒØ§Ø² Ù…ÛŒâ€ŒØ¯Ù‡Ø¯ØŒ "
                    "ØªÙˆØµÛŒÙ‡ Ø±Ù†Ú¯ Ùˆ ÙØ±Ù… Ø¨Ø¯Ù† Ø§Ø±Ø§Ø¦Ù‡ Ù…ÛŒâ€ŒÚ©Ù†Ø¯ Ùˆ Ø§Ø² Ú©Ù…Ø¯ Ù„Ø¨Ø§Ø³ Ø®ÙˆØ¯ØªØ§Ù† ØªØ±Ú©ÛŒØ¨ Ù¾ÛŒØ´Ù†Ù‡Ø§Ø¯ Ù…ÛŒâ€ŒØ¯Ù‡Ø¯. "
                    "Ú©Ø§Ù…Ù„Ø§Ù‹ Ø®ØµÙˆØµÛŒ â€” Ø¨Ø¯ÙˆÙ† Ú©Ù„Ø§ÙˆØ¯ØŒ Ù‡Ù…Ù‡â€ŒÚ†ÛŒØ² Ø±ÙˆÛŒ Ú¯ÙˆØ´ÛŒ."),
        "image": "/static/projects/aura-stylist.png",
        "tech": "Flutter Â· Dart Â· SQLite Â· Camera",
        "price": 4000000, "currency": "IRT", "buyable": 1, "sort": 2,
    },
    {
        "title_en": "Crypto Trade Panel",
        "title_fa": "Ù¾Ù†Ù„ Ù…Ø¹Ø§Ù…Ù„Ø§Øª Ú©Ø±ÛŒÙ¾ØªÙˆ",
        "desc_en": ("Full-stack crypto trading terminal: live market data and charts, "
                    "AI chart-image analysis, wallet & portfolio analytics, money "
                    "management, trading journal, backtesting and price alerts â€” with a "
                    "built-in AI trading assistant. React frontend, Node.js + SQLite backend."),
        "desc_fa": ("ØªØ±Ù…ÛŒÙ†Ø§Ù„ Ù…Ø¹Ø§Ù…Ù„Ø§ØªÛŒ ÙÙˆÙ„â€ŒØ§Ø³ØªÚ© Ú©Ø±ÛŒÙ¾ØªÙˆ: Ø¯ÛŒØªØ§ÛŒ Ø²Ù†Ø¯Ù‡ Ø¨Ø§Ø²Ø§Ø± Ùˆ Ù†Ù…ÙˆØ¯Ø§Ø±ØŒ ØªØ­Ù„ÛŒÙ„ ØªØµÙˆÛŒØ± Ú†Ø§Ø±Øª Ø¨Ø§ "
                    "Ù‡ÙˆØ´ Ù…ØµÙ†ÙˆØ¹ÛŒØŒ ØªØ­Ù„ÛŒÙ„ Ú©ÛŒÙ Ù¾ÙˆÙ„ Ùˆ Ù¾Ø±ØªÙÙˆÛŒØŒ Ù…Ø¯ÛŒØ±ÛŒØª Ø³Ø±Ù…Ø§ÛŒÙ‡ØŒ Ú˜ÙˆØ±Ù†Ø§Ù„ Ù…Ø¹Ø§Ù…Ù„Ø§ØªØŒ Ø¨Ú©â€ŒØªØ³Øª Ùˆ "
                    "Ù‡Ø´Ø¯Ø§Ø± Ù‚ÛŒÙ…Øª â€” Ù‡Ù…Ø±Ø§Ù‡ Ø¯Ø³ØªÛŒØ§Ø± Ù…Ø¹Ø§Ù…Ù„Ø§ØªÛŒ Ù‡ÙˆØ´Ù…Ù†Ø¯. ÙØ±Ø§Ù†Øª React Ùˆ Ø¨Ú©â€ŒØ§Ù†Ø¯ Node.js + SQLite."),
        "image": "/static/projects/trade-panel.png",
        "tech": "React Â· Node.js Â· SQLite Â· AI",
        "price": 9000000, "currency": "IRT", "buyable": 1, "sort": 3,
    },
]

GAMES = [
    {
        "title_en": "Terrain Painter",
        "title_fa": "Ù†Ù‚Ø§Ø´ Ø²Ù…ÛŒÙ†",
        "desc_en": ("Draw the ground under a rolling ball to keep it alive. Ink is limited, "
                    "strokes crumble after seconds, and the physics run at a fixed 120 Hz. "
                    "A complete HTML5 arcade game in a single file â€” touch and mouse ready, "
                    "zero dependencies."),
        "desc_fa": ("Ø²ÛŒØ± ØªÙˆÙ¾Ù Ø¯Ø± Ø­Ø§Ù„ Ø­Ø±Ú©Øª Ø²Ù…ÛŒÙ† Ø¨Ú©Ø´ÛŒØ¯ ØªØ§ Ø²Ù†Ø¯Ù‡ Ø¨Ù…Ø§Ù†Ø¯. Ø¬ÙˆÙ‡Ø± Ù…Ø­Ø¯ÙˆØ¯ Ø§Ø³ØªØŒ Ø®Ø·â€ŒÙ‡Ø§ Ø¨Ø¹Ø¯ Ø§Ø² Ú†Ù†Ø¯ "
                    "Ø«Ø§Ù†ÛŒÙ‡ ÙØ±Ùˆ Ù…ÛŒâ€ŒØ±ÛŒØ²Ù†Ø¯ Ùˆ ÙÛŒØ²ÛŒÚ© Ø¨Ø§Ø²ÛŒ Ø¨Ø§ Ù†Ø±Ø® Ø«Ø§Ø¨Øª Û±Û²Û° Ù‡Ø±ØªØ² Ø§Ø¬Ø±Ø§ Ù…ÛŒâ€ŒØ´ÙˆØ¯. ÛŒÚ© Ø¨Ø§Ø²ÛŒ Ø¢Ø±Ú©ÛŒØ¯ "
                    "Ú©Ø§Ù…Ù„ HTML5 Ø¯Ø± ÛŒÚ© ÙØ§ÛŒÙ„ â€” Ø³Ø§Ø²Ú¯Ø§Ø± Ø¨Ø§ Ù„Ù…Ø³ Ùˆ Ù…Ø§ÙˆØ³ØŒ Ø¨Ø¯ÙˆÙ† Ù‡ÛŒÚ† ÙˆØ§Ø¨Ø³ØªÚ¯ÛŒ."),
        "image": "/static/projects/terrain-painter.png",
        "url": "",
        "tech": "HTML5 Canvas Â· JavaScript Â· Web Audio",
        "price": 1500000, "currency": "IRT", "buyable": 1, "sort": 1,
    },
    {
        "title_en": "Sound Dash",
        "title_fa": "Ø³Ø§Ù†Ø¯ Ø¯ÙŽØ´",
        "desc_en": ("A 3D lane-runner driven by YOUR music. Pick any song on your device â€” "
                    "the game analyses beats, BPM and energy offline, then builds an obstacle "
                    "course perfectly synced to the track. Endless content, fully offline. "
                    "Built in Godot 4."),
        "desc_fa": ("ÛŒÚ© Ø¨Ø§Ø²ÛŒ Ø³Ù‡â€ŒØ¨Ø¹Ø¯ÛŒ Ù„ÙÛŒÙ†â€ŒØ±Ø§Ù†Ø± Ú©Ù‡ Ø¨Ø§ Ù…ÙˆØ³ÛŒÙ‚ÛŒÙ Ø®ÙˆØ¯Ù Ø´Ù…Ø§ Ø§Ø¬Ø±Ø§ Ù…ÛŒâ€ŒØ´ÙˆØ¯. Ù‡Ø± Ø¢Ù‡Ù†Ú¯ÛŒ Ø±Ø§ Ø§Ù†ØªØ®Ø§Ø¨ Ú©Ù†ÛŒØ¯ â€” "
                    "Ø¨Ø§Ø²ÛŒ Ø¶Ø±Ø¨â€ŒÙ‡Ø§ØŒ BPM Ùˆ Ø§Ù†Ø±Ú˜ÛŒ Ø±Ø§ Ø¢ÙÙ„Ø§ÛŒÙ† ØªØ­Ù„ÛŒÙ„ Ù…ÛŒâ€ŒÚ©Ù†Ø¯ Ùˆ Ù…Ø³ÛŒØ± Ù…ÙˆØ§Ù†Ø¹ Ø±Ø§ Ø¯Ù‚ÛŒÙ‚Ø§Ù‹ Ù‡Ù…Ø§Ù‡Ù†Ú¯ Ø¨Ø§ Ø¢Ù‡Ù†Ú¯ "
                    "Ù…ÛŒâ€ŒØ³Ø§Ø²Ø¯. Ù…Ø­ØªÙˆØ§ÛŒ Ø¨ÛŒâ€ŒÙ¾Ø§ÛŒØ§Ù†ØŒ Ú©Ø§Ù…Ù„Ø§Ù‹ Ø¢ÙÙ„Ø§ÛŒÙ†. Ø³Ø§Ø®ØªÙ‡â€ŒØ´Ø¯Ù‡ Ø¨Ø§ Godot 4."),
        "image": "/static/projects/sound-dash.png",
        "url": "",
        "tech": "Godot 4 Â· GDScript Â· Audio DSP",
        "price": 3000000, "currency": "IRT", "buyable": 1, "sort": 2,
    },
]

WEBSITES = [
    {
        "title_en": "FAMA Store",
        "title_fa": "ÙØ±ÙˆØ´Ú¯Ø§Ù‡ ÙØ§Ù…Ø§",
        "desc_en": ("Persian RTL e-commerce storefront for original cosmetics: category "
                    "browsing, product search, product pages, shopping cart and special "
                    "offers. Hand-coded HTML/CSS/JavaScript â€” fast, framework-free and "
                    "fully responsive."),
        "desc_fa": ("ÙØ±ÙˆØ´Ú¯Ø§Ù‡ Ø§ÛŒÙ†ØªØ±Ù†ØªÛŒ Ù„ÙˆØ§Ø²Ù… Ø¢Ø±Ø§ÛŒØ´ÛŒ Ø§ÙˆØ±Ø¬ÛŒÙ†Ø§Ù„ Ø¨Ø§ Ø·Ø±Ø§Ø­ÛŒ Ø±Ø§Ø³Øªâ€ŒØ¨Ù‡â€ŒÚ†Ù¾: Ø¯Ø³ØªÙ‡â€ŒØ¨Ù†Ø¯ÛŒ Ù…Ø­ØµÙˆÙ„Ø§ØªØŒ "
                    "Ø¬Ø³ØªØ¬ÙˆØŒ ØµÙØ­Ù‡ Ù…Ø­ØµÙˆÙ„ØŒ Ø³Ø¨Ø¯ Ø®Ø±ÛŒØ¯ Ùˆ Ù¾ÛŒØ´Ù†Ù‡Ø§Ø¯Ù‡Ø§ÛŒ ÙˆÛŒÚ˜Ù‡. Ú©Ø¯Ù†ÙˆÛŒØ³ÛŒ Ø¯Ø³ØªÛŒ Ø¨Ø§ HTML/CSS/JS â€” "
                    "Ø³Ø±ÛŒØ¹ØŒ Ø¨Ø¯ÙˆÙ† ÙØ±ÛŒÙ…â€ŒÙˆØ±Ú© Ùˆ Ú©Ø§Ù…Ù„Ø§Ù‹ ÙˆØ§Ú©Ù†Ø´â€ŒÚ¯Ø±Ø§."),
        "image": "/static/projects/fama.png",
        "url": "",
        "tech": "HTML Â· CSS Â· JavaScript Â· RTL",
        "price": 4000000, "currency": "IRT", "sort": 1,
    },
]


PLACEHOLDER_APPS = ("Inventory Manager Pro", "Smart POS System")
PLACEHOLDER_WEBSITES = ("Restaurant Ordering Website", "Corporate Landing Page")


def seed():
    init_db()
    conn = get_db()
    added = 0
    try:
        # hide demo placeholders that shipped with the very first seed
        conn.execute(
            f"UPDATE apps SET active=0 WHERE title_en IN ({','.join('?' * len(PLACEHOLDER_APPS))})",
            PLACEHOLDER_APPS)
        conn.execute(
            f"UPDATE websites SET active=0 WHERE title_en IN ({','.join('?' * len(PLACEHOLDER_WEBSITES))})",
            PLACEHOLDER_WEBSITES)
        for item in APPS:
            if conn.execute("SELECT 1 FROM apps WHERE title_en=?", (item["title_en"],)).fetchone():
                continue
            conn.execute(
                "INSERT INTO apps(title_en,title_fa,desc_en,desc_fa,image,tech,price,currency,buyable,sort,active) "
                "VALUES(:title_en,:title_fa,:desc_en,:desc_fa,:image,:tech,:price,:currency,:buyable,:sort,1)", item)
            added += 1
        for item in GAMES:
            if conn.execute("SELECT 1 FROM games WHERE title_en=?", (item["title_en"],)).fetchone():
                continue
            conn.execute(
                "INSERT INTO games(title_en,title_fa,desc_en,desc_fa,image,url,tech,price,currency,buyable,sort,active) "
                "VALUES(:title_en,:title_fa,:desc_en,:desc_fa,:image,:url,:tech,:price,:currency,:buyable,:sort,1)", item)
            added += 1
        for item in WEBSITES:
            if conn.execute("SELECT 1 FROM websites WHERE title_en=?", (item["title_en"],)).fetchone():
                continue
            conn.execute(
                "INSERT INTO websites(title_en,title_fa,desc_en,desc_fa,image,url,tech,price,currency,sort,active) "
                "VALUES(:title_en,:title_fa,:desc_en,:desc_fa,:image,:url,:tech,:price,:currency,:sort,1)", item)
            added += 1
        conn.commit()
        print(f"seeded {added} new project(s)")
        for t in ("apps", "games", "websites"):
            n = conn.execute(f"SELECT COUNT(*) FROM {t} WHERE active=1").fetchone()[0]
            print(f"  active {t}: {n}")
    finally:
        conn.close()


if __name__ == "__main__":
    seed()


