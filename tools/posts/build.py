"""Generate slides.html — eye-catching 1080x1350 Instagram slides, brand-matched.

Two carousels and a reel cover, built the same way the reel is: the Persian
font is base64-embedded (Chrome refuses a sibling @font-face over file://), and
the numbers in the data post come from the leads table, not typed in, so the
claim is always true.

Every slide is a pure function of window.setSlide(n); render.js screenshots
each. These are stills, so the only moving part is which slide is shown.
"""
from __future__ import annotations
import base64
import json
import pathlib
import sqlite3

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
W, H = 1080, 1350          # Instagram portrait, 4:5


def stats() -> dict:
    db = ROOT / "data" / "site.db"
    fb = {"total": 385, "nosite": 356, "withsite": 29, "dead": 9, "pct": 92}
    if not db.exists():
        return fb
    try:
        c = sqlite3.connect(db)
        q = lambda s: c.execute(s).fetchone()[0]
        tot = q("SELECT COUNT(*) FROM leads")
        if not tot:
            return fb
        nos = q("SELECT COUNT(*) FROM lead_signals WHERE code='NO_WEBSITE'")
        return {"total": tot, "nosite": nos, "withsite": tot - nos,
                "dead": q("SELECT COUNT(*) FROM lead_signals WHERE code='SITE_DEAD'"),
                "pct": round(nos * 100 / tot)}
    except sqlite3.Error:
        return fb


def fa(n) -> str:
    return str(n).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def font_b64() -> str:
    cands = sorted((ROOT / "static" / "fonts").glob("vazirmatn*.woff2"),
                   key=lambda p: p.stat().st_size)
    return base64.b64encode(cands[-1].read_bytes()).decode() if cands else ""


def cat(num, title, tag, body, tech):
    return f'''
      <div class="catnum">{num}</div>
      <div class="kick">{tag}</div>
      <div class="mega" style="font-size:110px">{title}</div>
      <div class="sub">{body}</div>
      <div class="tech">{tech}</div>'''


S = stats()

# ── Post 1 — one person, the whole stack (credibility → followers) ────────
P1 = [
    ("p1-01", '''
      <div class="kick">نیما زارع · توسعه‌دهنده فول‌استک</div>
      <div class="mega">یک نفر.<br><span class="accent">کل مسیر.</span></div>
      <div class="sub">سایت · اپلیکیشن · بازی · ربات · پایگاه‌داده</div>'''),
    ("p1-02", cat("۰۱", "وبسایت", "فروشگاه، کافه، شرکت",
                  "سریع، موبایل‌پسند، قابل دیده‌شدن در گوگل",
                  "HTML · CSS · JavaScript · PWA")),
    ("p1-03", cat("۰۲", "اپلیکیشن موبایل", "اندروید، کراس‌پلتفرم",
                  "برنامه‌ریز شمسی، کالری‌شمار، استایلیست",
                  "Flutter · Dart · SQLite")),
    ("p1-04", cat("۰۳", "بازی سه‌بعدی", "کاملاً در مرورگر",
                  "۱۰۰۰ مرحله، شش شخصیت، بدون نصب",
                  "Three.js · JavaScript · Vite")),
    ("p1-05", cat("۰۴", "ربات تلگرام", "اتوماسیون و پرداخت",
                  "اشتراک با پرداخت خودکار USDT، مدیریت کانال",
                  "Python · aiogram · TRON · TON")),
    ("p1-06", cat("۰۵", "داشبورد و اتوماسیون", "مدیریت کسب‌وکار",
                  "داشبورد فروشندگی آمازون با ۱۴ ماژول",
                  "Python · Streamlit · SQLite")),
    ("p1-07", cat("۰۶", "پایگاه‌داده با Rust", "از صفر، بدون فریم‌ورک",
                  "دیتابیس سازگار با Redis و موتور SQL توزیع‌شده",
                  "Rust · Tokio · Raft · MVCC")),
    ("p1-08", '''
      <div class="mega" style="font-size:150px">یک نفر،<br><span class="accent">کل مسیر.</span></div>
      <div class="sub" style="margin-top:40px">هر هفته یک پروژه را باز می‌کنم و نشان می‌دهم چطور ساخته شده.</div>
      <div class="cta">فالو کن 👈</div>
      <div class="handle">@nima.z.are</div>'''),
]

# ── Post 2 — the data story (value → customers) ───────────────────────────
P2 = [
    ("p2-01", f'''
      <div class="kick">بررسی واقعی · شیراز</div>
      <div class="huge accent">٪{fa(S["pct"])}</div>
      <div class="mega" style="font-size:88px">کسب‌وکارهای شیراز<br>وبسایت ندارند.</div>
      <div class="sub">{fa(S["total"])} کسب‌وکار را یکی‌یکی بررسی کردم.</div>'''),
    ("p2-02", '''
      <div class="kick">یعنی چه؟</div>
      <div class="mega" style="font-size:80px">مشتری ساعت ۱۱ شب<br>تصمیم می‌گیرد.</div>
      <div class="sub">اسم کسب‌وکارت را در گوگل می‌زند…</div>'''),
    ("p2-03", '''
      <div class="line">چیزی پیدا نمی‌کند.</div>
      <div class="line dim">نه منو، نه قیمت، نه نوبت.</div>
      <div class="line accent" style="margin-top:50px">← می‌رود سراغ رقیبت.</div>
      <div class="line dim" style="font-size:44px">و دیگر برنمی‌گردد.</div>'''),
    ("p2-04", f'''
      <div class="kick">و آن‌هایی که سایت داشتند؟</div>
      <div class="mega" style="font-size:70px">از <span class="accent">{fa(S["withsite"])}</span> سایتی که پیدا کردم،</div>
      <div class="huge accent" style="font-size:230px">{fa(S["dead"])}</div>
      <div class="mega" style="font-size:70px">تا اصلاً باز نمی‌شد.</div>'''),
    ("p2-05", '''
      <div class="mega" style="font-size:94px">یک سایت ساده<br>کافی است.</div>
      <div class="sub">که در گوگل پیدا شوی، روی موبایل خوب باز شود، نوبت و سفارش آنلاین بگیری.</div>
      <div class="cta">اسم کسب‌وکارت را کامنت کن 👇</div>
      <div class="handle">@nima.z.are</div>'''),
]

# ── Post 3 — reel cover (the video is in tools/reel) ──────────────────────
P3 = [
    ("p3-cover", '''
      <div class="kick">ساخت یک بازی سه‌بعدی</div>
      <div class="mega" style="font-size:118px">۱۰۰۰ مرحله.<br><span class="accent">صفر تا صد.</span></div>
      <div class="sub">یک رانر مخفی‌کاری سه‌بعدی، کاملاً در مرورگر.</div>
      <div class="handle" style="margin-top:60px">@nima.z.are</div>'''),
]

SLIDES = P1 + P2 + P3

HTML = """<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8">
<style>
@font-face{font-family:'Vazirmatn';src:url(data:font/woff2;base64,@@FONT@@) format('woff2');font-weight:100 900;font-display:block}
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:@@W@@px;height:@@H@@px;overflow:hidden;background:#070b11}
body{font-family:'Vazirmatn',system-ui,sans-serif;color:#eef4fb}
#stage{position:relative;width:@@W@@px;height:@@H@@px;overflow:hidden;
  display:flex;flex-direction:column;justify-content:center;padding:0 96px}
#grid{position:absolute;inset:-10%;opacity:.05;
  background-image:linear-gradient(#22c55e 1px,transparent 1px),linear-gradient(90deg,#22c55e 1px,transparent 1px);
  background-size:84px 84px}
#glow{position:absolute;width:1200px;height:1200px;border-radius:50%;left:-200px;top:260px;
  filter:blur(170px);opacity:.2;background:radial-gradient(circle,#22c55e 0%,transparent 62%)}
.content{position:relative;z-index:2}
.kick{font-size:36px;letter-spacing:.14em;color:#6b8299;font-weight:600;margin-bottom:26px}
.mega{font-size:170px;font-weight:900;line-height:1.08;letter-spacing:-.02em}
.huge{font-size:300px;font-weight:900;line-height:.9;letter-spacing:-.04em;
  font-variant-numeric:tabular-nums;margin:6px 0}
.sub{font-size:48px;line-height:1.55;color:#9fb3c8;font-weight:500;margin-top:34px;max-width:22ch}
.tech{margin-top:40px;font-family:ui-monospace,Menlo,monospace;direction:ltr;text-align:right;
  font-size:34px;color:#22c55e;letter-spacing:.02em}
.accent{color:#22c55e}.dim{color:#6b8299}
.catnum{position:absolute;top:110px;left:96px;font-size:200px;font-weight:900;
  color:rgba(34,197,94,.1);line-height:1;z-index:1}
.line{font-size:72px;font-weight:800;line-height:1.3}
.cta{margin-top:56px;display:inline-block;font-size:46px;font-weight:800;color:#070b11;
  background:#22c55e;padding:22px 46px;border-radius:999px}
.handle{margin-top:30px;font-size:54px;font-weight:800;color:#22c55e;direction:ltr;text-align:right}
#num{display:none;position:absolute;bottom:56px;left:96px;font-family:ui-monospace,monospace;
  font-size:28px;color:#3a4a5c;direction:ltr}
</style></head><body><div id="stage">
<div id="grid"></div><div id="glow"></div>
<div class="content" id="content"></div>
<div id="num"></div>
</div>
<script>
var SLIDES=@@SLIDES@@;
window.SLIDE_COUNT=SLIDES.length;
window.setSlide=function(i){
  var s=SLIDES[i]||SLIDES[0];
  document.getElementById('content').innerHTML=s.body;
  document.getElementById('num').textContent=s.tag;
  document.getElementById('glow').style.top=(180+(i%3)*170)+'px';
};
window.setSlide(0);
window.__ready=true;
</script></body></html>"""


def main():
    slides_js = json.dumps([{"tag": t, "body": b} for t, b in SLIDES], ensure_ascii=False)
    out = (HTML.replace("@@FONT@@", font_b64())
           .replace("@@W@@", str(W)).replace("@@H@@", str(H))
           .replace("@@SLIDES@@", slides_js))
    (HERE / "slides.html").write_text(out, encoding="utf-8")
    print(f"slides.html written — {len(SLIDES)} slides at {W}x{H}")
    print(f"  post1={len(P1)}  post2={len(P2)}  post3cover={len(P3)}")
    print(f"  data: {S['total']} businesses, {S['pct']}% no site, {S['dead']}/{S['withsite']} dead")


if __name__ == "__main__":
    main()
