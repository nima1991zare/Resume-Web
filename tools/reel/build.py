"""Builds reel.html — a frame-driven 1080x1920 animation for Instagram.

Why generate the HTML instead of writing it by hand: the Persian font has to be
embedded as base64 (Chrome treats file:// as an opaque origin and refuses a
@font-face loaded from a sibling path), and the real figures come from the
Project Finder database rather than being typed in. Both are things a static
file cannot do for itself.

Everything in the animation is a pure function of the frame number, exposed as
window.setFrame(n). No CSS transitions, no Date, no random — the renderer steps
frames one at a time and a single non-deterministic value would make the video
flicker.
"""
from __future__ import annotations

import base64
import pathlib
import sqlite3

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
FPS = 30
SECONDS = 20
W, H = 1080, 1920


def stats() -> dict:
    """Real numbers, or the ones measured on 2026-10-25 if the DB is elsewhere.

    A claim in the video has to be true — it is the whole reason the hook works
    — so these come from the same table the outreach does.
    """
    db = ROOT / "data" / "site.db"
    fallback = {"total": 385, "nosite": 356, "withsite": 29, "dead": 9,
                "insta": 54, "pct": 92}
    if not db.exists():
        return fallback
    try:
        c = sqlite3.connect(db)
        q = lambda s: c.execute(s).fetchone()[0]          # noqa: E731
        total = q("SELECT COUNT(*) FROM leads")
        if not total:
            return fallback
        nosite = q("SELECT COUNT(*) FROM lead_signals WHERE code='NO_WEBSITE'")
        return {
            "total": total,
            "nosite": nosite,
            "withsite": total - nosite,
            "dead": q("SELECT COUNT(*) FROM lead_signals WHERE code='SITE_DEAD'"),
            "insta": q("SELECT COUNT(*) FROM leads WHERE instagram<>''"),
            "pct": round(nosite * 100 / total),
        }
    except sqlite3.Error:
        return fallback


def fa(n) -> str:
    return str(n).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def font_b64() -> str:
    cands = sorted((ROOT / "static" / "fonts").glob("vazirmatn*.woff2"),
                   key=lambda p: p.stat().st_size)
    return base64.b64encode(cands[-1].read_bytes()).decode() if cands else ""


S = stats()
TOTAL_FRAMES = FPS * SECONDS

HTML = """<!doctype html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8">
<style>
@font-face {
  font-family: 'Vazirmatn';
  src: url(data:font/woff2;base64,@@FONT@@) format('woff2');
  font-weight: 100 900; font-display: block;
}
* { margin:0; padding:0; box-sizing:border-box; }
html,body { width:@@W@@px; height:@@H@@px; overflow:hidden; background:#070b11; }
body { font-family:'Vazirmatn',system-ui,sans-serif; color:#eef4fb; }
#stage { position:relative; width:@@W@@px; height:@@H@@px; overflow:hidden; }

/* a quiet moving field so the frame is never dead, but never competes */
#grid { position:absolute; inset:-10%; opacity:.05;
  background-image:linear-gradient(#22c55e 1px,transparent 1px),
                   linear-gradient(90deg,#22c55e 1px,transparent 1px);
  background-size:90px 90px; }
#glow { position:absolute; width:1400px; height:1400px; border-radius:50%;
  left:-160px; top:300px; filter:blur(180px); opacity:.22;
  background:radial-gradient(circle,#22c55e 0%,transparent 62%); }

.scene { position:absolute; inset:0; display:flex; flex-direction:column;
  justify-content:center; padding:0 92px; will-change:opacity,transform; }
.kicker { font-size:34px; letter-spacing:.18em; color:#6b8299; font-weight:600; }
.lead { font-size:62px; line-height:1.35; font-weight:600; }
.huge { font-size:300px; font-weight:900; line-height:.92; letter-spacing:-.03em;
  color:#22c55e; font-variant-numeric:tabular-nums; }
.mid { font-size:150px; font-weight:800; line-height:1; color:#22c55e;
  font-variant-numeric:tabular-nums; }
.sub { font-size:50px; line-height:1.5; color:#9fb3c8; font-weight:500; }
.accent { color:#22c55e; }
.dim { color:#6b8299; }

/* 385 dots: the stat as an object you can count rather than a claim */
#dots { display:grid; grid-template-columns:repeat(22,1fr); gap:13px;
  margin-top:54px; }
#dots i { width:28px; height:28px; border-radius:50%; background:#1b2735; display:block; }

.card { background:#0e151f; border:1px solid rgba(148,163,184,.16);
  border-radius:26px; padding:34px 38px; margin-top:26px; }
.card b { font-size:46px; display:block; }
.card span { font-size:34px; color:#7d93a9; }

.bar { height:16px; border-radius:12px; background:#16202c; overflow:hidden; margin-top:26px; }
.bar i { display:block; height:100%; background:linear-gradient(90deg,#22c55e,#4ade80); }

#handle { font-size:66px; font-weight:800; color:#22c55e; direction:ltr; }
#site { font-size:40px; color:#7d93a9; direction:ltr; margin-top:10px; }
.pill { display:inline-block; font-size:36px; padding:16px 38px; border-radius:999px;
  background:rgba(34,197,94,.14); color:#22c55e; border:1px solid rgba(34,197,94,.3);
  margin-top:40px; font-weight:700; }
#progress { position:absolute; left:0; bottom:0; height:8px; background:#22c55e; }
</style></head><body>
<div id="stage">
  <div id="grid"></div><div id="glow"></div>

  <section class="scene" id="s1">
    <div class="kicker">پروژه‌یاب · شیراز</div>
    <div class="lead" style="margin-top:28px">من <span class="accent" id="n-total">@@TOTAL_FA@@</span> کسب‌وکار شیراز را<br>یکی‌یکی بررسی کردم.</div>
    <div class="sub" style="margin-top:34px">رستوران، کافه، مطب، هتل، آرایشگاه، فروشگاه.</div>
  </section>

  <section class="scene" id="s2">
    <div class="kicker">نتیجه</div>
    <div class="huge" id="n-pct">٪۰</div>
    <div class="lead" style="margin-top:10px">اصلاً وبسایت ندارند.</div>
    <div id="dots"></div>
  </section>

  <section class="scene" id="s3">
    <div class="kicker">و آن‌هایی که داشتند؟</div>
    <div class="lead" style="margin-top:30px">از <span class="accent">@@WITHSITE_FA@@</span> سایتی که پیدا کردم،</div>
    <div class="mid" id="n-dead" style="margin-top:18px">۰</div>
    <div class="lead">تا اصلاً باز نمی‌شد.</div>
    <div class="bar"><i id="deadbar" style="width:0%"></i></div>
    <div class="sub" style="margin-top:22px">یعنی تقریباً یک‌سوم سایت‌های موجود، خراب بودند.</div>
  </section>

  <section class="scene" id="s4">
    <div class="kicker">این یعنی چه؟</div>
    <div class="card" id="c1"><b>مشتری اسم شما را در گوگل می‌زند</b><span>ساعت ۱۱ شب، وقتی تصمیم گرفته</span></div>
    <div class="card" id="c2"><b>چیزی پیدا نمی‌کند</b><span>نه منو، نه قیمت، نه نوبت</span></div>
    <div class="card" id="c3"><b>سراغ رقیب شما می‌رود</b><span>و دیگر برنمی‌گردد</span></div>
  </section>

  <section class="scene" id="s5">
    <div class="kicker">کاری که می‌کنم</div>
    <div class="lead" style="margin-top:26px">سایت و اپلیکیشن برای<br>کسب‌وکارهای شیراز.</div>
    <div class="sub" style="margin-top:28px">سریع، موبایل‌پسند، با نوبت‌دهی و سفارش آنلاین.</div>
    <div class="pill">اسم کسب‌وکارت را دایرکت بده</div>
    <div class="sub" style="margin-top:46px">رایگان نگاه می‌کنم و می‌گویم چه چیزی کم دارد.</div>
  </section>

  <section class="scene" id="s6">
    <div id="handle">@@@HANDLE@@</div>
    <div id="site">@@SITE@@</div>
  </section>

  <div id="progress"></div>
</div>

<script>
"use strict";
var FPS = @@FPS@@, TOTAL = @@TOTAL_FRAMES@@;
var S = { total:@@TOTAL@@, nosite:@@NOSITE@@, withsite:@@WITHSITE@@, dead:@@DEAD@@, pct:@@PCT@@ };

/* ---- easing: the taste rules, as functions ---- */
function bez(p1x, p1y, p2x, p2y) {
  return function (t) {
    if (t <= 0) return 0; if (t >= 1) return 1;
    var lo = 0, hi = 1, u = t, x;
    for (var i = 0; i < 24; i++) {
      u = (lo + hi) / 2;
      x = 3*(1-u)*(1-u)*u*p1x + 3*(1-u)*u*u*p2x + u*u*u;
      if (x < t) lo = u; else hi = u;
    }
    return 3*(1-u)*(1-u)*u*p1y + 3*(1-u)*u*u*p2y + u*u*u;
  };
}
var easeOut = bez(0.16, 1, 0.3, 1);       // things arriving
var easeIn  = bez(0.6, 0, 0.9, 0.35);     // things leaving, fast
var easeIO  = bez(0.65, 0, 0.35, 1);

function prog(f, a, b, ease) {
  if (b <= a) return f >= b ? 1 : 0;
  var t = Math.max(0, Math.min(1, (f - a) / (b - a)));
  return (ease || easeOut)(t);
}
function fa(n) {
  return String(n).replace(/[0-9]/g, function (d) { return "۰۱۲۳۴۵۶۷۸۹"[+d]; });
}

/* ---- the timeline, in seconds ---- */
var TL = {
  s1: [0.0,  3.6],
  s2: [3.4,  8.0],
  s3: [7.8, 12.2],
  s4: [12.0, 16.2],
  s5: [16.0, 19.0],
  s6: [18.8, 20.0]
};
/* Scenes overlap by ~0.2s on purpose: a hard gap reads as "loading". */

var dots = document.getElementById("dots");
(function () {
  for (var i = 0; i < S.total; i++) dots.appendChild(document.createElement("i"));
})();
var dotEls = dots.children;

function scene(id, f, a, b, slide) {
  var el = document.getElementById(id);
  var inP  = prog(f, a * FPS, (a + 0.75) * FPS, easeOut);
  var outP = prog(f, (b - 0.45) * FPS, b * FPS, easeIn);
  var vis = inP * (1 - outP);
  el.style.opacity = vis;
  var y = (1 - inP) * (slide || 60) - outP * 40;
  el.style.transform = "translateY(" + y.toFixed(2) + "px)";
  el.style.visibility = vis < 0.003 ? "hidden" : "visible";
  return { inP: inP, outP: outP, vis: vis };
}

window.setFrame = function (f) {
  var t = f / FPS;

  /* background drifts linearly — the one place linear is right */
  document.getElementById("grid").style.transform =
    "translate(" + (-t * 14).toFixed(2) + "px," + (-t * 9).toFixed(2) + "px)";
  document.getElementById("glow").style.transform =
    "translateY(" + (Math.sin(t * 0.45) * 90).toFixed(2) + "px)";

  scene("s1", f, TL.s1[0], TL.s1[1]);
  /* the count ticks up rather than appearing: a number that moves is read */
  var c1 = Math.round(prog(f, 0.5 * FPS, 2.6 * FPS, easeOut) * S.total);
  document.getElementById("n-total").textContent = fa(c1);

  var sc2 = scene("s2", f, TL.s2[0], TL.s2[1]);
  var pctP = prog(f, (TL.s2[0] + 0.3) * FPS, (TL.s2[0] + 2.0) * FPS, easeOut);
  document.getElementById("n-pct").textContent = "٪" + fa(Math.round(pctP * S.pct));
  /* dots fill in over a beat, so the proportion is felt, not just stated */
  var lit = Math.round(prog(f, (TL.s2[0] + 0.9) * FPS, (TL.s2[0] + 3.1) * FPS, easeIO) * S.nosite);
  for (var i = 0; i < dotEls.length; i++) {
    dotEls[i].style.background = i < lit ? "#22c55e" : "#1b2735";
    dotEls[i].style.opacity = sc2.vis;
  }

  scene("s3", f, TL.s3[0], TL.s3[1]);
  var dP = prog(f, (TL.s3[0] + 0.5) * FPS, (TL.s3[0] + 2.0) * FPS, easeOut);
  document.getElementById("n-dead").textContent = fa(Math.round(dP * S.dead));
  document.getElementById("deadbar").style.width =
    (dP * (S.dead / Math.max(1, S.withsite)) * 100).toFixed(1) + "%";

  scene("s4", f, TL.s4[0], TL.s4[1]);
  /* the three cards land one after another, 0.22s apart */
  ["c1", "c2", "c3"].forEach(function (id, i) {
    var p = prog(f, (TL.s4[0] + 0.45 + i * 0.22) * FPS,
                    (TL.s4[0] + 1.15 + i * 0.22) * FPS, easeOut);
    var el = document.getElementById(id);
    el.style.opacity = p;
    el.style.transform = "translateX(" + ((1 - p) * -46).toFixed(2) + "px)";
  });

  scene("s5", f, TL.s5[0], TL.s5[1]);
  scene("s6", f, TL.s6[0], TL.s6[1], 30);

  document.getElementById("progress").style.width = (f / TOTAL * 100).toFixed(3) + "%";
};

window.setFrame(0);
window.__ready = true;
</script></body></html>
"""


def main() -> None:
    # Plain token replacement, not str.format: the template is mostly
    # JavaScript and CSS, so every { and } in it would have to be doubled and
    # a single missed brace fails the whole build with a message that points
    # at the format call rather than the character.
    values = {
        "FONT": font_b64(), "W": W, "H": H, "FPS": FPS,
        "TOTAL_FRAMES": TOTAL_FRAMES, "TOTAL": S["total"],
        "NOSITE": S["nosite"], "WITHSITE": S["withsite"],
        "DEAD": S["dead"], "PCT": S["pct"],
        # Persian digits for anything the viewer reads as prose. The JS
        # rewrites most counters every frame, but not these two.
        "TOTAL_FA": fa(S["total"]), "WITHSITE_FA": fa(S["withsite"]),
        "HANDLE": "nima.z.are", "SITE": "nimabuilds.pythonanywhere.com",
    }
    out = HTML
    for key, val in values.items():
        out = out.replace("@@" + key + "@@", str(val))
    assert "@@" not in out, "a template token was left unreplaced"
    (HERE / "reel.html").write_text(out, encoding="utf-8")
    print(f"reel.html written — {TOTAL_FRAMES} frames at {FPS}fps ({SECONDS}s)")
    print(f"  using: {S['total']} businesses, {S['pct']}% with no site, "
          f"{S['dead']} of {S['withsite']} sites dead")


if __name__ == "__main__":
    main()
