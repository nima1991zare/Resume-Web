"""Nima portfolio — FastAPI backend serving the public site, JSON API and admin panel."""
import hashlib
import html as html_mod
import json
import secrets
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Header, Request, UploadFile, File
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .database import (
    get_db, init_db, get_setting, set_setting, hash_password, verify_password,
)

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
UPLOAD_DIR = STATIC_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Nima Portfolio API", docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(GZipMiddleware, minimum_size=500)
init_db()

PUBLIC_SETTINGS = (
    "site_title_en", "site_title_fa", "about_en", "about_fa",
    "phone", "email", "telegram", "github", "linkedin", "whatsapp",
    "site_url",
)

# NOTE: .svg intentionally NOT allowed — SVG files can carry embedded
# scripts and become a stored-XSS vector when served from our origin.
ALLOWED_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".avif"}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024        # 5 MB per image
MAX_BODY_BYTES = 6 * 1024 * 1024          # global request body cap

IMAGE_MAGIC = (
    (".png",  b"\x89PNG\r\n\x1a\n"),
    (".jpg",  b"\xff\xd8\xff"),
    (".jpeg", b"\xff\xd8\xff"),
    (".gif",  b"GIF8"),
)

CSP = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "font-src 'self'; "
    "img-src 'self' data: https:; "
    "connect-src 'self'; "
    "manifest-src 'self'; "
    "worker-src 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "object-src 'none'"
)

# long-lived immutable assets vs. occasionally-edited code
CACHE_LONG = ("/static/fonts/", "/static/icons/", "/static/uploads/")
CACHE_SHORT = ("/static/css/", "/static/js/")


# ------------------------------------------------------------- security layer
class RateLimiter:
    """Small in-memory sliding-window rate limiter (per-process)."""

    def __init__(self) -> None:
        self.hits: dict[str, deque] = defaultdict(deque)

    def allow(self, key: str, limit: int, window_s: float) -> bool:
        now = time.monotonic()
        dq = self.hits[key]
        while dq and now - dq[0] > window_s:
            dq.popleft()
        if len(dq) >= limit:
            return False
        dq.append(now)
        # opportunistic memory cleanup
        if len(self.hits) > 20_000:
            stale = [k for k, v in self.hits.items() if not v or now - v[-1] > 3600]
            for k in stale:
                del self.hits[k]
        return True


limiter = RateLimiter()


def client_ip(request: Request) -> str:
    xf = request.headers.get("x-forwarded-for", "")
    if xf:
        return xf.split(",")[0].strip()[:64]
    return request.client.host if request.client else "unknown"


def rate_limit(request: Request, bucket: str, limit: int, window_s: float) -> None:
    if not limiter.allow(f"{bucket}:{client_ip(request)}", limit, window_s):
        raise HTTPException(status_code=429, detail="Too many requests — try again later")


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    # global body size guard (declared length; upload endpoint re-checks while reading)
    cl = request.headers.get("content-length")
    if cl and cl.isdigit() and int(cl) > MAX_BODY_BYTES:
        return JSONResponse({"detail": "Payload too large"}, status_code=413)

    response = await call_next(request)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"

    ct = response.headers.get("content-type", "")
    path = request.url.path
    if "text/html" in ct:
        response.headers["Content-Security-Policy"] = CSP
    if path.startswith("/api/") or path == "/admin":
        response.headers["Cache-Control"] = "no-store"
    elif path in ("/static/js/admin.js", "/static/css/admin.css"):
        # admin panel code must always be fresh (revalidate every load)
        response.headers["Cache-Control"] = "no-cache"
    elif path.startswith(CACHE_LONG):
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    elif path.startswith(CACHE_SHORT):
        response.headers["Cache-Control"] = "public, max-age=86400"
    return response


# ---------------------------------------------------------------- auth helpers
def _token_hash(token: str) -> str:
    """Sessions are stored hashed so a leaked DB does not expose live tokens."""
    return hashlib.sha256(token.encode()).hexdigest()


def require_admin(authorization: Optional[str]) -> None:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.removeprefix("Bearer ").strip()
    if not token or len(token) > 128:
        raise HTTPException(status_code=401, detail="Not authenticated")
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT token FROM sessions WHERE token=? "
            "AND created_at > datetime('now', '-30 days')", (_token_hash(token),)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=401, detail="Session expired")
    finally:
        conn.close()


# ---------------------------------------------------------------------- models
class ContactIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(default="", max_length=200)
    phone: str = Field(default="", max_length=40)
    subject: str = Field(default="", max_length=200)
    message: str = Field(min_length=1, max_length=5000)


class VisitIn(BaseModel):
    path: str = Field(default="/", max_length=300)
    lang: str = Field(default="en", max_length=8)
    referrer: str = Field(default="", max_length=500)


class LoginIn(BaseModel):
    username: str
    password: str


class ItemIn(BaseModel):
    title_en: str = ""
    title_fa: str = ""
    desc_en: str = ""
    desc_fa: str = ""
    image: str = ""
    url: str = ""
    tech: str = ""
    price: float = 0
    currency: str = "USD"
    buyable: int = 1
    sort: int = 0
    active: int = 1


class BrandIn(BaseModel):
    name: str
    logo: str = ""
    url: str = ""
    sort: int = 0
    active: int = 1


class SettingsIn(BaseModel):
    settings: dict[str, str]


def _validate_link(value: str, field: str, allow_local: bool = False) -> str:
    """URLs must be real links (or local uploads for images). Empty is fine."""
    v = (value or "").strip()
    if not v:
        return ""
    ok = v.startswith(("http://", "https://"))
    if allow_local:
        ok = ok or (v.startswith("/static/") and ".." not in v)
    if not ok or len(v) > 500:
        hint = "http(s):// URL or /static/uploads/… path" if allow_local else "http:// or https:// URL"
        raise HTTPException(
            status_code=422,
            detail=f"'{field}' must be a valid {hint} — or leave it empty.")
    return v


class PasswordIn(BaseModel):
    current: str
    new: str = Field(min_length=8)


# ------------------------------------------------------------------ public api
def _load_public_content() -> dict:
    conn = get_db()
    try:
        settings = {k: get_setting(conn, k) for k in PUBLIC_SETTINGS}
        apps = [dict(r) for r in conn.execute(
            "SELECT id,title_en,title_fa,desc_en,desc_fa,image,tech,price,currency,buyable "
            "FROM apps WHERE active=1 ORDER BY sort, id")]
        websites = [dict(r) for r in conn.execute(
            "SELECT id,title_en,title_fa,desc_en,desc_fa,image,url,tech,price,currency "
            "FROM websites WHERE active=1 ORDER BY sort, id")]
        brands = [dict(r) for r in conn.execute(
            "SELECT id,name,logo,url FROM brands WHERE active=1 ORDER BY sort, id")]
        return {"settings": settings, "apps": apps, "websites": websites, "brands": brands}
    finally:
        conn.close()


@app.get("/api/content")
def public_content():
    return _load_public_content()


@app.post("/api/contact")
def submit_contact(data: ContactIn, request: Request):
    rate_limit(request, "contact", limit=5, window_s=600)      # 5 messages / 10 min / IP
    name = data.name.strip()
    message = data.message.strip()
    if not name or not message:
        raise HTTPException(status_code=422, detail="Name and message are required")
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO messages(name,email,phone,subject,message) VALUES(?,?,?,?,?)",
            (name, data.email.strip(), data.phone.strip(),
             data.subject.strip(), message),
        )
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@app.post("/api/visit")
def track_visit(data: VisitIn, request: Request):
    rate_limit(request, "visit", limit=30, window_s=3600)      # 30 hits / hour / IP
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO visits(path,lang,referrer,ua) VALUES(?,?,?,?)",
            (data.path, data.lang, data.referrer,
             request.headers.get("user-agent", "")[:300]),
        )
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


# ------------------------------------------------------------------- admin api
@app.post("/api/admin/login")
def admin_login(data: LoginIn, request: Request):
    rate_limit(request, "login", limit=10, window_s=900)       # 10 attempts / 15 min / IP
    conn = get_db()
    try:
        user = get_setting(conn, "admin_user", "admin")
        stored = get_setting(conn, "admin_pass", "")
        user_ok = secrets.compare_digest(data.username.encode(), user.encode())
        pass_ok = verify_password(data.password, stored)
        if not (user_ok and pass_ok):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        token = secrets.token_urlsafe(32)
        conn.execute("INSERT INTO sessions(token) VALUES(?)", (_token_hash(token),))
        conn.execute("DELETE FROM sessions WHERE created_at < datetime('now', '-30 days')")
        conn.commit()
        return {"token": token}
    finally:
        conn.close()


@app.post("/api/admin/logout")
def admin_logout(authorization: Optional[str] = Header(None)):
    require_admin(authorization)
    token = authorization.removeprefix("Bearer ").strip()
    conn = get_db()
    try:
        conn.execute("DELETE FROM sessions WHERE token=?", (_token_hash(token),))
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@app.get("/api/admin/stats")
def admin_stats(authorization: Optional[str] = Header(None)):
    require_admin(authorization)
    conn = get_db()
    try:
        total = conn.execute("SELECT COUNT(*) c FROM visits").fetchone()["c"]
        today = conn.execute(
            "SELECT COUNT(*) c FROM visits WHERE date(created_at)=date('now')").fetchone()["c"]
        week = conn.execute(
            "SELECT COUNT(*) c FROM visits WHERE created_at > datetime('now','-7 days')"
        ).fetchone()["c"]
        by_day = [dict(r) for r in conn.execute(
            "SELECT date(created_at) d, COUNT(*) c FROM visits "
            "WHERE created_at > datetime('now','-30 days') GROUP BY d ORDER BY d")]
        by_lang = [dict(r) for r in conn.execute(
            "SELECT lang, COUNT(*) c FROM visits GROUP BY lang ORDER BY c DESC")]
        unread = conn.execute("SELECT COUNT(*) c FROM messages WHERE read=0").fetchone()["c"]
        default_pw = verify_password("admin123", get_setting(conn, "admin_pass", ""))
        return {"total": total, "today": today, "week": week,
                "by_day": by_day, "by_lang": by_lang, "unread_messages": unread,
                "default_password": default_pw}
    finally:
        conn.close()


TABLES = {"apps": "apps", "websites": "websites"}


@app.get("/api/admin/items/{table}")
def admin_list_items(table: str, authorization: Optional[str] = Header(None)):
    require_admin(authorization)
    if table not in TABLES:
        raise HTTPException(status_code=404)
    conn = get_db()
    try:
        return [dict(r) for r in conn.execute(
            f"SELECT * FROM {TABLES[table]} ORDER BY sort, id")]
    finally:
        conn.close()


@app.post("/api/admin/items/{table}")
def admin_create_item(table: str, data: ItemIn, authorization: Optional[str] = Header(None)):
    require_admin(authorization)
    if table not in TABLES:
        raise HTTPException(status_code=404)
    data.url = _validate_link(data.url, "Live URL")
    data.image = _validate_link(data.image, "Image", allow_local=True)
    conn = get_db()
    try:
        if table == "apps":
            cur = conn.execute(
                "INSERT INTO apps(title_en,title_fa,desc_en,desc_fa,image,tech,price,currency,buyable,sort,active) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (data.title_en, data.title_fa, data.desc_en, data.desc_fa, data.image,
                 data.tech, data.price, data.currency, data.buyable, data.sort, data.active))
        else:
            cur = conn.execute(
                "INSERT INTO websites(title_en,title_fa,desc_en,desc_fa,image,url,tech,price,currency,sort,active) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (data.title_en, data.title_fa, data.desc_en, data.desc_fa, data.image,
                 data.url, data.tech, data.price, data.currency, data.sort, data.active))
        conn.commit()
        return {"id": cur.lastrowid}
    finally:
        conn.close()


@app.put("/api/admin/items/{table}/{item_id}")
def admin_update_item(table: str, item_id: int, data: ItemIn,
                      authorization: Optional[str] = Header(None)):
    require_admin(authorization)
    if table not in TABLES:
        raise HTTPException(status_code=404)
    data.url = _validate_link(data.url, "Live URL")
    data.image = _validate_link(data.image, "Image", allow_local=True)
    conn = get_db()
    try:
        if table == "apps":
            conn.execute(
                "UPDATE apps SET title_en=?,title_fa=?,desc_en=?,desc_fa=?,image=?,tech=?,"
                "price=?,currency=?,buyable=?,sort=?,active=? WHERE id=?",
                (data.title_en, data.title_fa, data.desc_en, data.desc_fa, data.image,
                 data.tech, data.price, data.currency, data.buyable, data.sort,
                 data.active, item_id))
        else:
            conn.execute(
                "UPDATE websites SET title_en=?,title_fa=?,desc_en=?,desc_fa=?,image=?,url=?,"
                "tech=?,price=?,currency=?,sort=?,active=? WHERE id=?",
                (data.title_en, data.title_fa, data.desc_en, data.desc_fa, data.image,
                 data.url, data.tech, data.price, data.currency, data.sort,
                 data.active, item_id))
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@app.delete("/api/admin/items/{table}/{item_id}")
def admin_delete_item(table: str, item_id: int, authorization: Optional[str] = Header(None)):
    require_admin(authorization)
    if table not in TABLES:
        raise HTTPException(status_code=404)
    conn = get_db()
    try:
        conn.execute(f"DELETE FROM {TABLES[table]} WHERE id=?", (item_id,))
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@app.get("/api/admin/brands")
def admin_list_brands(authorization: Optional[str] = Header(None)):
    require_admin(authorization)
    conn = get_db()
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM brands ORDER BY sort, id")]
    finally:
        conn.close()


@app.post("/api/admin/brands")
def admin_create_brand(data: BrandIn, authorization: Optional[str] = Header(None)):
    require_admin(authorization)
    data.url = _validate_link(data.url, "Website URL")
    data.logo = _validate_link(data.logo, "Logo", allow_local=True)
    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO brands(name,logo,url,sort,active) VALUES(?,?,?,?,?)",
            (data.name, data.logo, data.url, data.sort, data.active))
        conn.commit()
        return {"id": cur.lastrowid}
    finally:
        conn.close()


@app.put("/api/admin/brands/{brand_id}")
def admin_update_brand(brand_id: int, data: BrandIn,
                       authorization: Optional[str] = Header(None)):
    require_admin(authorization)
    data.url = _validate_link(data.url, "Website URL")
    data.logo = _validate_link(data.logo, "Logo", allow_local=True)
    conn = get_db()
    try:
        conn.execute(
            "UPDATE brands SET name=?,logo=?,url=?,sort=?,active=? WHERE id=?",
            (data.name, data.logo, data.url, data.sort, data.active, brand_id))
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@app.delete("/api/admin/brands/{brand_id}")
def admin_delete_brand(brand_id: int, authorization: Optional[str] = Header(None)):
    require_admin(authorization)
    conn = get_db()
    try:
        conn.execute("DELETE FROM brands WHERE id=?", (brand_id,))
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@app.get("/api/admin/messages")
def admin_list_messages(authorization: Optional[str] = Header(None)):
    require_admin(authorization)
    conn = get_db()
    try:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM messages ORDER BY id DESC LIMIT 500")]
    finally:
        conn.close()


@app.put("/api/admin/messages/{msg_id}/read")
def admin_mark_read(msg_id: int, authorization: Optional[str] = Header(None)):
    require_admin(authorization)
    conn = get_db()
    try:
        conn.execute("UPDATE messages SET read=1 WHERE id=?", (msg_id,))
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@app.delete("/api/admin/messages/{msg_id}")
def admin_delete_message(msg_id: int, authorization: Optional[str] = Header(None)):
    require_admin(authorization)
    conn = get_db()
    try:
        conn.execute("DELETE FROM messages WHERE id=?", (msg_id,))
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@app.get("/api/admin/settings")
def admin_get_settings(authorization: Optional[str] = Header(None)):
    require_admin(authorization)
    conn = get_db()
    try:
        return {k: get_setting(conn, k) for k in PUBLIC_SETTINGS}
    finally:
        conn.close()


@app.put("/api/admin/settings")
def admin_update_settings(data: SettingsIn, authorization: Optional[str] = Header(None)):
    require_admin(authorization)
    conn = get_db()
    try:
        for k, v in data.settings.items():
            if k in PUBLIC_SETTINGS:
                set_setting(conn, k, v)
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@app.put("/api/admin/password")
def admin_change_password(data: PasswordIn, authorization: Optional[str] = Header(None)):
    require_admin(authorization)
    conn = get_db()
    try:
        stored = get_setting(conn, "admin_pass", "")
        if not verify_password(data.current, stored):
            raise HTTPException(status_code=400, detail="Current password is wrong")
        set_setting(conn, "admin_pass", hash_password(data.new))
        conn.execute("DELETE FROM sessions")  # force re-login everywhere
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


def _magic_matches(ext: str, head: bytes) -> bool:
    """Verify file content actually looks like the claimed image type."""
    for e, magic in IMAGE_MAGIC:
        if e == ext:
            return head.startswith(magic)
    if ext == ".webp":
        return head[:4] == b"RIFF" and head[8:12] == b"WEBP"
    if ext == ".avif":
        return b"ftyp" in head[:16]
    return False


@app.post("/api/admin/upload")
def admin_upload(request: Request, file: UploadFile = File(...),
                 authorization: Optional[str] = Header(None)):
    require_admin(authorization)
    rate_limit(request, "upload", limit=30, window_s=3600)
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_IMAGE_EXT:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    head = file.file.read(16)
    if not _magic_matches(ext, head):
        raise HTTPException(status_code=400, detail="File content does not match its type")

    name = f"{secrets.token_hex(8)}{ext}"
    dest = UPLOAD_DIR / name
    written = 0
    try:
        with dest.open("wb") as out:
            out.write(head)
            written = len(head)
            while True:
                chunk = file.file.read(64 * 1024)
                if not chunk:
                    break
                written += len(chunk)
                if written > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="Image too large (max 5 MB)")
                out.write(chunk)
    except HTTPException:
        dest.unlink(missing_ok=True)
        raise
    except Exception:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Upload failed")
    return {"url": f"/static/uploads/{name}"}


# ------------------------------------------------------------------ SEO layer
def _base_url(request: Request, settings: dict) -> str:
    configured = (settings.get("site_url") or "").strip().rstrip("/")
    if configured.startswith(("http://", "https://")):
        return configured
    return str(request.base_url).rstrip("/")


def _esc(s: str) -> str:
    return html_mod.escape(str(s or ""), quote=True)


def _json_for_script(data) -> str:
    # "</" must never appear raw inside a <script> block
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


def _build_jsonld(content: dict, base: str) -> str:
    s = content["settings"]
    same_as = [u for u in (s.get("github"), s.get("linkedin"), s.get("telegram")) if u]
    person = {
        "@type": "Person",
        "@id": base + "/#person",
        "name": "Nima",
        "jobTitle": "Full-Stack Developer",
        "description": s.get("about_en", ""),
        "url": base + "/",
        "knowsAbout": ["Python", "Java", "JavaScript", "HTML", "CSS",
                       "SQL", "MongoDB", "UX Design", "UI Design", "Photoshop"],
    }
    if s.get("email"):
        person["email"] = "mailto:" + s["email"]
    if s.get("phone"):
        person["telephone"] = s["phone"]
    if same_as:
        person["sameAs"] = same_as

    website = {
        "@type": "WebSite",
        "@id": base + "/#website",
        "url": base + "/",
        "name": s.get("site_title_en") or "Nima — Full-Stack Developer",
        "inLanguage": ["en", "fa"],
        "publisher": {"@id": base + "/#person"},
    }

    products = []
    for a in content["apps"]:
        if not a.get("buyable"):
            continue
        p = {
            "@type": "Product",
            "name": a["title_en"],
            "description": a["desc_en"],
            "offers": {
                "@type": "Offer",
                "price": str(a["price"]),
                "priceCurrency": a["currency"],
                "availability": "https://schema.org/InStock",
            },
        }
        if a.get("image"):
            img = a["image"]
            p["image"] = img if img.startswith("http") else base + img
        products.append(p)

    graph = [person, website]
    if products:
        graph.append({
            "@type": "ItemList",
            "name": "Applications for sale",
            "itemListElement": [
                {"@type": "ListItem", "position": i + 1, "item": p}
                for i, p in enumerate(products)
            ],
        })
    return ('<script type="application/ld+json">'
            + _json_for_script({"@context": "https://schema.org", "@graph": graph})
            + "</script>")


def _build_noscript(content: dict) -> str:
    s = content["settings"]
    parts = ["<noscript><main>"]
    parts.append("<h2>About Nima</h2><p>" + _esc(s.get("about_en", "")) + "</p>")
    parts.append('<p lang="fa" dir="rtl">' + _esc(s.get("about_fa", "")) + "</p>")
    if content["apps"]:
        parts.append("<h2>Applications for sale</h2><ul>")
        for a in content["apps"]:
            price = f' — {a["price"]:g} {a["currency"]}' if a.get("price") else ""
            parts.append("<li><strong>" + _esc(a["title_en"]) + "</strong>: "
                         + _esc(a["desc_en"]) + _esc(price) + "</li>")
        parts.append("</ul>")
    if content["websites"]:
        parts.append("<h2>Websites built</h2><ul>")
        for w in content["websites"]:
            link = (' — <a href="' + _esc(w["url"]) + '">' + _esc(w["url"]) + "</a>") if w.get("url") else ""
            parts.append("<li><strong>" + _esc(w["title_en"]) + "</strong>: "
                         + _esc(w["desc_en"]) + link + "</li>")
        parts.append("</ul>")
    if content["brands"]:
        parts.append("<h2>Brands worked with</h2><ul>"
                     + "".join("<li>" + _esc(b["name"]) + "</li>" for b in content["brands"])
                     + "</ul>")
    contact_bits = [x for x in (s.get("email"), s.get("phone")) if x]
    if contact_bits:
        parts.append("<h2>Contact</h2><p>" + _esc(" · ".join(contact_bits)) + "</p>")
    parts.append("</main></noscript>")
    return "".join(parts)


def _render_index(request: Request) -> str:
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    content = _load_public_content()
    base = _base_url(request, content["settings"])

    html = html.replace("<!--SEO:CANONICAL-->",
                        '<link rel="canonical" href="' + _esc(base) + '/">')
    html = html.replace("<!--SEO:OG_URL-->",
                        '<meta property="og:url" content="' + _esc(base) + '/">\n'
                        '  <meta property="og:image" content="' + _esc(base) + '/static/icons/og-image.png">\n'
                        '  <meta property="og:image:width" content="1200">\n'
                        '  <meta property="og:image:height" content="630">')
    html = html.replace("<!--SEO:TWITTER_IMAGE-->",
                        '<meta name="twitter:image" content="' + _esc(base) + '/static/icons/og-image.png">')
    html = html.replace("<!--SEO:JSONLD-->", _build_jsonld(content, base))
    html = html.replace("<!--SEO:NOSCRIPT-->", _build_noscript(content))
    html = html.replace("<!--SEO:DATA-->",
                        '<script id="content-data" type="application/json">'
                        + _json_for_script(content) + "</script>")
    return html


# ----------------------------------------------------------------- page routes
@app.get("/", include_in_schema=False)
def index(request: Request):
    return HTMLResponse(_render_index(request))


@app.get("/robots.txt", include_in_schema=False)
def robots(request: Request):
    conn = get_db()
    try:
        settings = {"site_url": get_setting(conn, "site_url")}
    finally:
        conn.close()
    base = _base_url(request, settings)
    return PlainTextResponse(
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /admin\n"
        "Disallow: /api/\n"
        f"Sitemap: {base}/sitemap.xml\n"
    )


@app.get("/sitemap.xml", include_in_schema=False)
def sitemap(request: Request):
    conn = get_db()
    try:
        settings = {"site_url": get_setting(conn, "site_url")}
    finally:
        conn.close()
    base = _base_url(request, settings)
    today = time.strftime("%Y-%m-%d")
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"  <url><loc>{base}/</loc><lastmod>{today}</lastmod>"
        "<changefreq>weekly</changefreq><priority>1.0</priority></url>\n"
        "</urlset>\n"
    )
    return Response(content=xml, media_type="application/xml")


@app.get("/admin", include_in_schema=False)
def admin_page():
    return FileResponse(STATIC_DIR / "admin.html")


@app.get("/manifest.json", include_in_schema=False)
def manifest():
    return FileResponse(STATIC_DIR / "manifest.json", media_type="application/manifest+json")


@app.get("/sw.js", include_in_schema=False)
def service_worker():
    return FileResponse(STATIC_DIR / "sw.js", media_type="application/javascript")


@app.exception_handler(404)
async def not_found(request: Request, exc):
    if request.url.path.startswith(("/api/", "/static/")):
        return JSONResponse({"detail": "Not found"}, status_code=404)
    # SPA fallback keeps 404 status so search engines don't index junk URLs
    return HTMLResponse(_render_index(request), status_code=404)


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
