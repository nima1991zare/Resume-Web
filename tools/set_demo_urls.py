# -*- coding: utf-8 -*-
"""Set demo URLs on the LIVE database — safe for production.

Unlike seed_projects.py, this script ONLY:
  1. sets the demo_url column (matched by English title) — it never touches
     prices, images, descriptions or anything you edited in the admin panel;
  2. inserts the TODO_Liat app if it does not exist yet (insert only, never update).

Run inside the container:   docker exec <container> python tools/set_demo_urls.py
Or from the project root:   python tools/set_demo_urls.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.database import get_db, init_db

DEMOS = {
    "apps": {
        "CalCounter": "/static/demos/calcounter/",
        "Aura Stylist": "/static/demos/aura-stylist/",
        "Crypto Trade Panel": "/static/demos/trade-panel/",
        "TODO_Liat": "/static/demos/todo-liat/",
    },
    "games": {
        "Terrain Painter": "/static/demos/terrain-painter/",
        "Sound Dash": "/static/demos/sound-dash/",
    },
    "websites": {
        "FAMA Store": "/static/demos/fama/",
    },
}

TODO_LIAT = {
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
    "tech": "Java · Android · Room · AlarmManager",
    "demo_url": "/static/demos/todo-liat/",
    "price": 3000000, "currency": "IRT", "buyable": 1, "sort": 4,
}


def main():
    init_db()   # runs the demo_url column migration if needed
    conn = get_db()
    try:
        # insert TODO_Liat only if missing — never update an existing row
        row = conn.execute(
            "SELECT id FROM apps WHERE title_en=?", (TODO_LIAT["title_en"],)).fetchone()
        if row is None:
            cols = list(TODO_LIAT.keys()) + ["active"]
            conn.execute(
                f"INSERT INTO apps({','.join(cols)}) "
                f"VALUES({','.join(':' + c for c in TODO_LIAT)},1)", TODO_LIAT)
            print("apps: TODO_Liat -> inserted")
        else:
            print("apps: TODO_Liat -> already exists (untouched)")

        # set demo_url only — nothing else is modified
        for table, mapping in DEMOS.items():
            for title, demo in mapping.items():
                cur = conn.execute(
                    f"UPDATE {table} SET demo_url=? WHERE title_en=?", (demo, title))
                status = "demo_url set" if cur.rowcount else "NOT FOUND — skipped"
                print(f"{table}: {title} -> {status}")
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
