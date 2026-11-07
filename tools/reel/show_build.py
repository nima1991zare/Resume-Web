"""Builds show.html — a 15s capability showreel, frame-driven for Instagram.

A different subject from the data reel: not "here is the problem" but "here is
what I can build for you." Seven scenes slide through the things a business
actually wants — a shop site, an app, online booking, a bot — and end on a
contact line. Same engine as the data reel: every visual is a pure function of
window.setFrame(n), so stepping frames renders smooth motion with no clock.
"""
from __future__ import annotations
import base64
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
FPS, SECONDS, W, H = 30, 15, 1080, 1920
TOTAL = FPS * SECONDS


def font_b64() -> str:
    cands = sorted((ROOT / "static" / "fonts").glob("vazirmatn*.woff2"),
                   key=lambda p: p.stat().st_size)
    return base64.b64encode(cands[-1].read_bytes()).decode() if cands else ""


# each scene: [start, end] seconds · kicker · big title · tech/sub · accent rgb
SCENES = [
    [0.0, 2.6, "برای کسب‌وکارت", "چه می‌تونم<br>برات بسازم؟", "", "74,222,128"],
    [2.4, 4.6, "۰۱", "وبسایت فروشگاهی", "سبد خرید · پرداخت · پنل مدیریت", "96,165,250"],
    [4.4, 6.6, "۰۲", "اپلیکیشن موبایل", "Flutter · اندروید · iOS", "167,139,250"],
    [6.4, 8.6, "۰۳", "نوبت‌دهی و سفارش آنلاین", "۲۴ ساعته · وصل به واتساپ", "45,212,191"],
    [8.4, 10.6, "۰۴", "ربات تلگرام", "پرداخت خودکار · اتوماسیون", "251,191,36"],
    [10.4, 12.6, "۰۵", "حتی بازی و پایگاه‌داده", "Three.js · Rust · از صفر", "251,113,133"],
    [12.4, 15.0, "بزن بریم", "ایده‌ات را<br>بگو.", "", "74,222,128"],
]

HTML = """<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8">
<style>
@font-face{font-family:'Vazirmatn';src:url(data:font/woff2;base64,@@FONT@@) format('woff2');font-weight:100 900;font-display:block}
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:@@W@@px;height:@@H@@px;overflow:hidden;background:#070b11}
body{font-family:'Vazirmatn',system-ui,sans-serif;color:#eef4fb}
#stage{position:relative;width:@@W@@px;height:@@H@@px;overflow:hidden}
#grid{position:absolute;inset:-10%;opacity:.05;
  background-image:linear-gradient(#4ade80 1px,transparent 1px),linear-gradient(90deg,#4ade80 1px,transparent 1px);
  background-size:92px 92px}
#glow{position:absolute;width:1300px;height:1300px;border-radius:50%;left:-150px;top:360px;
  filter:blur(180px);opacity:.22}
.scene{position:absolute;inset:0;display:flex;flex-direction:column;justify-content:center;
  padding:0 96px;will-change:opacity,transform}
.kick{font-size:40px;letter-spacing:.14em;color:#6b8299;font-weight:600;margin-bottom:26px}
.catn{font-family:ui-monospace,monospace;color:var(--ac);font-size:44px;margin-bottom:18px;direction:ltr;text-align:right}
.title{font-size:140px;font-weight:900;line-height:1.08;letter-spacing:-.02em}
.sub{font-size:46px;color:#9fb3c8;font-weight:500;margin-top:34px;font-family:ui-monospace,monospace;direction:ltr;text-align:right}
.ac{color:var(--ac)}
#handle{position:absolute;bottom:150px;right:96px;font-size:58px;font-weight:800;color:#4ade80;direction:ltr}
#prog{position:absolute;left:0;bottom:0;height:8px;background:#4ade80}
</style></head><body><div id="stage">
<div id="grid"></div><div id="glow"></div>
<div class="scene" id="scene"></div>
<div id="handle">nimazare.dev</div>
<div id="prog"></div>
</div>
<script>
var FPS=@@FPS@@,TOTAL=@@TOTAL@@,SCENES=@@SCENES@@;
function bez(a,b,c,d){return function(t){if(t<=0)return 0;if(t>=1)return 1;var lo=0,hi=1,u=t,x;
 for(var i=0;i<22;i++){u=(lo+hi)/2;x=3*(1-u)*(1-u)*u*a+3*(1-u)*u*u*c+u*u*u;if(x<t)lo=u;else hi=u;}
 return 3*(1-u)*(1-u)*u*b+3*(1-u)*u*u*d+u*u*u;};}
var easeOut=bez(0.16,1,0.3,1),easeIn=bez(0.6,0,0.9,0.35);
function prog(f,a,b,e){if(b<=a)return f>=b?1:0;var t=Math.max(0,Math.min(1,(f-a)/(b-a)));return (e||easeOut)(t);}
window.setFrame=function(f){
  var t=f/FPS;
  document.getElementById('grid').style.transform="translate("+(-t*16).toFixed(1)+"px,"+(-t*10).toFixed(1)+"px)";
  // which scene is active
  var idx=0;for(var i=0;i<SCENES.length;i++){if(t>=SCENES[i][0])idx=i;}
  var sc=SCENES[idx],ac=sc[5];
  document.getElementById('glow').style.background="radial-gradient(circle,rgba("+ac+",1) 0%,transparent 62%)";
  document.getElementById('glow').style.transform="translateY("+(Math.sin(t*0.6)*80).toFixed(1)+"px)";
  var inP=prog(f,sc[0]*FPS,(sc[0]+0.6)*FPS,easeOut);
  var outP=prog(f,(sc[1]-0.4)*FPS,sc[1]*FPS,easeIn);
  var el=document.getElementById('scene');
  el.style.setProperty('--ac','rgb('+ac+')');
  el.style.opacity=inP*(1-outP);
  el.style.transform="translateY("+((1-inP)*70-outP*44).toFixed(1)+"px)";
  el.innerHTML=(sc[2]?(/^[۰-۹0-9]+$/.test(sc[2])?'<div class="catn">'+sc[2]+'</div>':'<div class="kick">'+sc[2]+'</div>'):'')+
    '<div class="title">'+sc[3]+'</div>'+(sc[4]?'<div class="sub">'+sc[4]+'</div>':'');
  document.getElementById('prog').style.width=(f/TOTAL*100).toFixed(2)+'%';
};
window.setFrame(0);window.__ready=true;
</script></body></html>"""


def main():
    import json
    out = (HTML.replace("@@FONT@@", font_b64())
           .replace("@@W@@", str(W)).replace("@@H@@", str(H))
           .replace("@@FPS@@", str(FPS)).replace("@@TOTAL@@", str(TOTAL))
           .replace("@@SCENES@@", json.dumps(SCENES, ensure_ascii=False)))
    (HERE / "show.html").write_text(out, encoding="utf-8")
    print(f"show.html written — {TOTAL} frames at {FPS}fps ({SECONDS}s), {len(SCENES)} scenes")


if __name__ == "__main__":
    main()
