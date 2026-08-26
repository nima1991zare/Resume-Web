/* ============================================================
   Coffeete — کافیته | app.js
   ============================================================ */
"use strict";

/* ---------- Utilities ---------- */
const faDigits = ["۰", "۱", "۲", "۳", "۴", "۵", "۶", "۷", "۸", "۹"];
const toFa = (n) => String(n).replace(/\d/g, (d) => faDigits[+d]);
const formatPrice = (n) => toFa(n.toLocaleString("en-US").replace(/,/g, "٬")) + " تومان";

const $ = (sel, ctx = document) => ctx.querySelector(sel);
const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];

/* ---------- SVG product illustrations ---------- */
const ART = {
  bag(color, band) {
    return `<svg viewBox="0 0 120 140" fill="none" role="img" aria-hidden="true">
      <path d="M28 34h64l6 84a10 10 0 0 1-10 11H32a10 10 0 0 1-10-11l6-84Z" fill="${color}"/>
      <path d="M28 34h64l2 26H26l2-26Z" fill="rgba(255,255,255,.18)"/>
      <path d="M40 34V22a20 20 0 0 1 40 0v12" stroke="${band}" stroke-width="6" stroke-linecap="round"/>
      <rect x="34" y="66" width="52" height="40" rx="8" fill="#fff"/>
      <ellipse cx="60" cy="82" rx="12" ry="16" fill="${color}"/>
      <path d="M60 68c-4 6-4 22 0 28" stroke="#fff" stroke-width="3" stroke-linecap="round"/>
      <rect x="40" y="112" width="40" height="6" rx="3" fill="rgba(255,255,255,.4)"/>
    </svg>`;
  },
  machine(color) {
    return `<svg viewBox="0 0 130 140" fill="none" role="img" aria-hidden="true">
      <rect x="18" y="10" width="94" height="26" rx="8" fill="${color}"/>
      <rect x="30" y="36" width="70" height="14" rx="4" fill="#2b3245"/>
      <rect x="46" y="50" width="38" height="26" rx="5" fill="#525c78"/>
      <rect x="56" y="76" width="18" height="10" rx="3" fill="#2b3245"/>
      <rect x="14" y="36" width="14" height="72" rx="6" fill="${color}"/>
      <rect x="102" y="36" width="14" height="72" rx="6" fill="${color}"/>
      <rect x="24" y="108" width="82" height="18" rx="7" fill="${color}"/>
      <path d="M60 86c0 6 4 6 4 12M70 86c0 6-4 6-4 12" stroke="#8b93ad" stroke-width="3" stroke-linecap="round"/>
      <rect x="48" y="96" width="34" height="12" rx="4" fill="#fff"/>
      <circle cx="94" cy="23" r="6" fill="#fff" opacity=".85"/>
      <circle cx="36" cy="23" r="4" fill="#fff" opacity=".5"/>
    </svg>`;
  },
  grinder(color) {
    return `<svg viewBox="0 0 120 140" fill="none" role="img" aria-hidden="true">
      <path d="M38 12h44l-4 26H42l-4-26Z" fill="#525c78"/>
      <rect x="34" y="38" width="52" height="34" rx="8" fill="${color}"/>
      <rect x="42" y="46" width="36" height="18" rx="5" fill="rgba(255,255,255,.25)"/>
      <path d="M40 72h40l-6 54H46l-6-54Z" fill="#dfe5f5"/>
      <ellipse cx="60" cy="98" rx="11" ry="14" fill="${color}"/>
      <path d="M60 86c-3 5-3 19 0 24" stroke="#dfe5f5" stroke-width="2.6" stroke-linecap="round"/>
      <rect x="52" y="4" width="16" height="10" rx="4" fill="${color}"/>
    </svg>`;
  },
  mokapot(color) {
    return `<svg viewBox="0 0 120 140" fill="none" role="img" aria-hidden="true">
      <path d="M40 14h40l6 34H34l6-34Z" fill="${color}"/>
      <path d="M34 48h52l-8 20H42l-8-20Z" fill="rgba(0,0,0,.15)"/>
      <path d="M42 68h36l8 44a8 8 0 0 1-8 10H42a8 8 0 0 1-8-10l8-44Z" fill="${color}"/>
      <path d="M52 4h16v10H52z" rx="3" fill="${color}"/>
      <path d="M88 30c8 2 12 10 8 18l-10-4" fill="${color}"/>
      <path d="M26 60c-6 8-4 20 4 24" stroke="${color}" stroke-width="7" stroke-linecap="round"/>
      <rect x="48" y="86" width="24" height="20" rx="4" fill="rgba(255,255,255,.3)"/>
    </svg>`;
  },
  frenchpress(color) {
    return `<svg viewBox="0 0 120 140" fill="none" role="img" aria-hidden="true">
      <rect x="54" y="6" width="12" height="18" rx="4" fill="${color}"/>
      <rect x="40" y="20" width="40" height="8" rx="4" fill="${color}"/>
      <rect x="57" y="26" width="6" height="40" fill="#8b93ad"/>
      <rect x="34" y="34" width="52" height="88" rx="10" fill="#dfe5f5" opacity=".9"/>
      <rect x="34" y="70" width="52" height="52" rx="10" fill="${color}" opacity=".8"/>
      <rect x="40" y="62" width="40" height="7" rx="3" fill="#8b93ad"/>
      <path d="M86 48h8a10 10 0 0 1 0 34h-8" stroke="${color}" stroke-width="7" stroke-linecap="round"/>
      <rect x="30" y="120" width="60" height="10" rx="5" fill="${color}"/>
    </svg>`;
  },
  cup(color) {
    return `<svg viewBox="0 0 120 140" fill="none" role="img" aria-hidden="true">
      <path d="M24 48h64a5 5 0 0 1 5 5v22a34 34 0 0 1-34 34h-6a34 34 0 0 1-34-34V53a5 5 0 0 1 5-5Z" fill="${color}"/>
      <path d="M93 56h7a14 14 0 0 1 0 28h-7" stroke="${color}" stroke-width="8" stroke-linecap="round"/>
      <ellipse cx="56" cy="58" rx="26" ry="6" fill="#6b4a2f"/>
      <path d="M42 30c0-6 6-6 6-12M56 30c0-6 6-6 6-12M70 30c0-6 6-6 6-12" stroke="${color}" stroke-width="5" stroke-linecap="round"/>
      <rect x="20" y="116" width="76" height="9" rx="4.5" fill="${color}" opacity=".4"/>
    </svg>`;
  },
  scale(color) {
    return `<svg viewBox="0 0 120 140" fill="none" role="img" aria-hidden="true">
      <rect x="16" y="84" width="88" height="36" rx="10" fill="${color}"/>
      <rect x="26" y="94" width="34" height="16" rx="4" fill="#fff"/>
      <text x="43" y="107" font-size="11" text-anchor="middle" fill="${color}" font-weight="bold">۲۵۰g</text>
      <circle cx="86" cy="102" r="8" fill="rgba(255,255,255,.35)"/>
      <rect x="24" y="40" width="72" height="40" rx="8" fill="#dfe5f5"/>
      <ellipse cx="60" cy="42" rx="36" ry="8" fill="#c8d2ec"/>
    </svg>`;
  },
};

/* ---------- Data (fallback — replaced by /api/data when server runs) ---------- */
let PRODUCTS = [
  { id: 1,  cat: "beans",     art: "bag:#2b36a9:#ffd88a", name: "دانه قهوه عربیکا اتیوپی یرگاچف", meta: "رست روشن • ۲۵۰ گرم", price: 385000, old: 450000, rating: 4.8, badge: "پرفروش", featured: true },
  { id: 2,  cat: "beans",     art: "bag:#1b2145:#f59e0b", name: "دانه قهوه ربوستا ویتنام", meta: "رست دارک • ۲۵۰ گرم", price: 295000, old: null, rating: 4.6, badge: null, featured: false },
  { id: 3,  cat: "beans",     art: "bag:#4553cc:#ffffff", name: "ترکیب ۷۰/۳۰ عربیکا-ربوستا", meta: "رست مدیوم • ۵۰۰ گرم", price: 520000, old: 610000, rating: 4.9, badge: "تخفیف", featured: true },
  { id: 4,  cat: "beans",     art: "bag:#222b8b:#ffd88a", name: "دانه قهوه کلمبیا سوپریمو", meta: "رست مدیوم • ۲۵۰ گرم", price: 410000, old: null, rating: 4.7, badge: null, featured: false },
  { id: 5,  cat: "beans",     art: "bag:#14194a:#ffffff", name: "ترکیب ۵۰/۵۰ اسپرسو بار", meta: "رست دارک • ۱ کیلوگرم", price: 890000, old: 990000, rating: 4.8, badge: "اقتصادی", featured: true },
  { id: 6,  cat: "ground",    art: "bag:#5b3a1e:#ffd88a", name: "قهوه ترک آسیاب‌شده", meta: "آسیاب ریز • ۲۰۰ گرم", price: 245000, old: null, rating: 4.5, badge: null, featured: false },
  { id: 7,  cat: "ground",    art: "bag:#7a5c3e:#ffffff", name: "قهوه فرانسه آسیاب‌شده", meta: "آسیاب متوسط • ۲۵۰ گرم", price: 268000, old: 310000, rating: 4.6, badge: "تخفیف", featured: false },
  { id: 8,  cat: "machine",   art: "machine:#2b36a9", name: "اسپرسوساز خانگی کافیته مدل K۱۰", meta: "تک‌گروپ • پمپ ۲۰ بار", price: 14800000, old: 16500000, rating: 4.7, badge: "پیشنهاد", featured: true },
  { id: 9,  cat: "machine",   art: "machine:#1b2145", name: "اسپرسوساز نیمه‌صنعتی مدل Pro", meta: "دوگروپ • بویلر مسی", price: 42500000, old: null, rating: 4.9, badge: null, featured: true },
  { id: 10, cat: "machine",   art: "grinder:#2b36a9", name: "آسیاب قهوه برقی کافیته", meta: "تیغه فلت • ۴۰ درجه آسیاب", price: 6900000, old: 7800000, rating: 4.6, badge: "تخفیف", featured: false },
  { id: 11, cat: "accessory", art: "mokapot:#4c5178", name: "موکاپات ۳ کاپ", meta: "آلومینیوم • مناسب گاز", price: 980000, old: null, rating: 4.5, badge: null, featured: false },
  { id: 12, cat: "accessory", art: "frenchpress:#2b36a9", name: "فرنچ‌پرس ۶۰۰ میلی‌لیتر", meta: "شیشه بروسیلیکات", price: 720000, old: 850000, rating: 4.7, badge: "تخفیف", featured: false },
  { id: 13, cat: "accessory", art: "cup:#2b36a9", name: "ست ۲ عددی ماگ سرامیکی کافیته", meta: "۳۳۰ میلی‌لیتر", price: 540000, old: null, rating: 4.8, badge: "جدید", featured: true },
  { id: 14, cat: "accessory", art: "scale:#2b36a9", name: "ترازوی دیجیتال باریستا", meta: "دقت ۰.۱ گرم • تایمر", price: 1650000, old: null, rating: 4.6, badge: null, featured: false },
];

let BRANDS = [];
let SETTINGS = null;
let BANNERS = [];

/* Fallback blog posts — replaced by /api/data when the server runs */
let BLOGS = [
  { slug: "arabica-vs-robusta", title: "عربیکا یا ربوستا؟ تفاوت دو گونه اصلی قهوه دنیا", excerpt: "کافئین بیشتر یا عطر پیچیده‌تر؟ کرمای غلیظ یا اسیدیته لطیف؟ مقایسه کامل عربیکا و ربوستا برای انتخابی آگاهانه.", cover: null, date: "2026-08-18", dateFa: "۲۷ مرداد ۱۴۰۵", tags: ["عربیکا", "ربوستا", "دانه قهوه"] },
  { slug: "coffee-roast-levels", title: "تفاوت رست روشن، مدیوم و دارک؛ کدام برای شما مناسب است؟", excerpt: "درجه رست شخصیت قهوه را می‌سازد؛ از اسیدیته میوه‌ای رست روشن تا تلخی قدرتمند رست دارک. راهنمای انتخاب رست مناسب سلیقه شما.", cover: null, date: "2026-08-14", dateFa: "۲۳ مرداد ۱۴۰۵", tags: ["رست قهوه", "راهنمای خرید"] },
  { slug: "espresso-brewing-guide", title: "راهنمای کامل دم‌آوری اسپرسو در خانه", excerpt: "از انتخاب دانه و درجه آسیاب تا نسبت طلایی و زمان عصاره‌گیری؛ هر آنچه برای یک شات اسپرسوی بی‌نقص در خانه لازم دارید.", cover: null, date: "2026-08-10", dateFa: "۱۹ مرداد ۱۴۰۵", tags: ["اسپرسو", "آموزش دم‌آوری"] },
];

/* Render product visual: uploaded image or SVG art string "type:color1[:color2]" */
function artOf(p) {
  if (p.image) {
    return `<img src="${p.image}" alt="${p.name}" loading="lazy" />`;
  }
  const [type, c1, c2] = String(p.art || "bag:#2b36a9:#ffd88a").split(":");
  const fn = ART[type] || ART.bag;
  return fn(c1 || "#2b36a9", c2 || "#ffd88a");
}

function brandNameOf(p) {
  const b = BRANDS.find((b) => b.id === p.brandId);
  return b ? b.name : null;
}

const CATEGORIES = [
  { id: "beans", name: "دانه قهوه", icon: `<svg viewBox="0 0 24 24" width="34" height="34" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><ellipse cx="12" cy="12" rx="7" ry="9.5" transform="rotate(24 12 12)"/><path d="M9.5 4.5c4 4 1 10 5 15" transform="rotate(24 12 12)"/></svg>` },
  { id: "ground", name: "قهوه آسیاب‌شده", icon: `<svg viewBox="0 0 24 24" width="34" height="34" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M7 3h10l-1.5 7h-7L7 3Z"/><path d="M8.5 10 7 21h10l-1.5-11"/><circle cx="12" cy="16" r="2"/></svg>` },
  { id: "machine", name: "اسپرسوساز", icon: `<svg viewBox="0 0 24 24" width="34" height="34" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="3" width="16" height="4" rx="1.5"/><path d="M6 7v13a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V7"/><path d="M10 7h4v3h-4z"/><path d="M9 16h6v3H9z"/><path d="M12 10v3"/></svg>` },
  { id: "accessory", name: "لوازم جانبی", icon: `<svg viewBox="0 0 24 24" width="34" height="34" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 8h13a2 2 0 0 1 2 2v3a7 7 0 0 1-7 7h-1a7 7 0 0 1-7-7V8Z"/><path d="M19 10h1a2.5 2.5 0 0 1 0 5h-1"/><path d="M8 5c0-1 1-1 1-2M12 5c0-1 1-1 1-2"/></svg>` },
];

const TESTIMONIALS = [
  { name: "سارا محمدی", role: "خریدار دانه قهوه", text: "قهوه‌ها واقعاً تازه‌رست هستن، تاریخ رست روی بسته می‌خوره و عطرش موقع باز کردن بسته فوق‌العاده‌ست. دیگه از جای دیگه خرید نمی‌کنم." },
  { name: "امیر رضایی", role: "باریستای خانگی", text: "اسپرسوساز K۱۰ رو گرفتم و بعد از ۶ ماه استفاده روزانه هنوز عالی کار می‌کنه. پشتیبانی کافیته هم همیشه پاسخگوئه." },
  { name: "نگار احمدی", role: "خریدار ترکیب ۷۰/۳۰", text: "ارسالش خیلی سریع بود، سفارش صبح دادم و عصر همون روز رسید. کرمای ترکیب ۷۰/۳۰ برای اسپرسو بی‌نظیره." },
];

/* ---------- State ---------- */
let cart = JSON.parse(localStorage.getItem("coffeete-cart") || "[]");
let activeFilter = "all";
let searchQuery = "";

const saveCart = () => localStorage.setItem("coffeete-cart", JSON.stringify(cart));

/* ---------- Render: categories ---------- */
function renderCategories() {
  $("#categoryList").innerHTML = CATEGORIES.map((c) => `
    <button class="category-card" data-cat="${c.id}" aria-label="مشاهده دسته ${c.name}">
      <span class="category-card__icon">${c.icon}</span>
      <h3>${c.name}</h3>
    </button>`).join("");

  $$(".category-card").forEach((el) => {
    el.addEventListener("click", () => {
      setFilter(el.dataset.cat);
      $("#products").scrollIntoView({ behavior: "smooth" });
    });
  });
}

/* ---------- Render: product card ---------- */
function productCard(p) {
  const stars = `<svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M12 2l2.4 7.2H22l-6 4.5 2.3 7.3-6.3-4.5-6.3 4.5L8 13.7 2 9.2h7.6z"/></svg>`;
  return `
    <article class="product-card" data-id="${p.id}" role="button" tabindex="0" aria-label="مشاهده ${p.name}">
      <div class="product-card__media">
        ${p.badge ? `<span class="product-card__badge">${p.badge}</span>` : ""}
        ${artOf(p)}
      </div>
      <div class="product-card__body">
        <h3 class="product-card__title">${p.name}</h3>
        <span class="product-card__meta">${brandNameOf(p) ? brandNameOf(p) + " • " : ""}${p.meta}</span>
        <span class="product-card__rating">${stars} ${toFa(p.rating)}</span>
      </div>
      <div class="product-card__foot">
        <span class="product-card__price">
          ${p.old ? `<s>${toFa(p.old.toLocaleString("en-US").replace(/,/g, "٬"))}</s>` : ""}
          <strong>${formatPrice(p.price)}</strong>
        </span>
        <button class="add-btn" data-add="${p.id}" aria-label="افزودن ${p.name} به سبد خرید">
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>
        </button>
      </div>
    </article>`;
}

/* ---------- Product detail modal ---------- */
function ensureProductModal() {
  let modal = $("#productModal");
  if (modal) return modal;
  modal = document.createElement("div");
  modal.id = "productModal";
  modal.className = "product-modal";
  modal.hidden = true;
  modal.setAttribute("role", "dialog");
  modal.setAttribute("aria-modal", "true");
  document.body.appendChild(modal);
  modal.addEventListener("click", (e) => {
    if (e.target === modal || e.target.closest("[data-close-product]")) closeProductModal();
  });
  return modal;
}

function openProductModal(id) {
  const p = PRODUCTS.find((p) => p.id === id);
  if (!p) return;
  const modal = ensureProductModal();
  modal.innerHTML = `
    <article class="product-modal__card">
      <button class="icon-btn product-modal__close" data-close-product aria-label="بستن">
        <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12"/></svg>
      </button>
      <div class="product-modal__media">${artOf(p)}</div>
      <div class="product-modal__body">
        ${brandNameOf(p) ? `<span class="product-modal__brand">${brandNameOf(p)}</span>` : ""}
        <h2 class="product-modal__title">${p.name}</h2>
        <p class="product-modal__meta">${p.meta || ""}</p>
        <div class="product-modal__price">
          <strong>${formatPrice(p.price)}</strong>
          ${p.old ? `<s>${formatPrice(p.old)}</s>` : ""}
        </div>
        <div class="product-modal__actions">
          <button class="btn btn--primary btn--block" data-add="${p.id}">افزودن به سبد خرید</button>
        </div>
      </div>
    </article>`;
  modal.hidden = false;
  document.body.style.overflow = "hidden";
  requestAnimationFrame(() => modal.classList.add("is-open"));
  modal.querySelector("[data-close-product]").focus();
}

function closeProductModal() {
  const modal = $("#productModal");
  if (!modal || modal.hidden) return;
  modal.classList.remove("is-open");
  document.body.style.overflow = "";
  setTimeout(() => { modal.hidden = true; }, 220);
}

function renderFeatured() {
  $("#featuredList").innerHTML = PRODUCTS.filter((p) => p.featured).map(productCard).join("");
}

function renderProducts() {
  let list = PRODUCTS;
  if (activeFilter !== "all") list = list.filter((p) => p.cat === activeFilter);
  if (searchQuery) {
    const q = searchQuery.trim();
    list = list.filter((p) => p.name.includes(q) || p.meta.includes(q));
  }
  $("#productsGrid").innerHTML = list.map(productCard).join("");
  $("#productsEmpty").hidden = list.length > 0;
}

/* ---------- Render: testimonials ---------- */
function renderTestimonials() {
  const star = `<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M12 2l2.4 7.2H22l-6 4.5 2.3 7.3-6.3-4.5-6.3 4.5L8 13.7 2 9.2h7.6z"/></svg>`;
  $("#testimonialList").innerHTML = TESTIMONIALS.map((t) => `
    <article class="testimonial">
      <div class="testimonial__stars" aria-label="امتیاز ۵ از ۵">${star.repeat(5)}</div>
      <p class="testimonial__text">«${t.text}»</p>
      <div class="testimonial__person">
        <span class="testimonial__avatar" aria-hidden="true">${t.name.charAt(0)}</span>
        <div><strong>${t.name}</strong><span>${t.role}</span></div>
      </div>
    </article>
  `).join("");
  $("#tDots").innerHTML = TESTIMONIALS.map((_, i) => `<button class="hero-banner__dot${i === 0 ? " is-active" : ""}" data-tdot="${i}" aria-label="نظر ${toFa(i + 1)}"></button>`).join("");
}

/* Testimonials carousel behavior */
let tIndex = 0;
let tTimer = null;

function tShow(i) {
  const track = $("#testimonialList");
  const count = TESTIMONIALS.length;
  tIndex = (i + count) % count;
  const w = track.clientWidth;
  // RTL: scrollLeft is 0 at start and goes negative
  track.scrollTo({ left: -tIndex * w, behavior: "smooth" });
  $$("#tDots .hero-banner__dot").forEach((d, idx) => d.classList.toggle("is-active", idx === tIndex));
}

function tRestart() {
  clearInterval(tTimer);
  tTimer = setInterval(() => tShow(tIndex + 1), 6000);
}

$("#tNext").addEventListener("click", () => { tShow(tIndex + 1); tRestart(); });
$("#tPrev").addEventListener("click", () => { tShow(tIndex - 1); tRestart(); });
$("#tDots").addEventListener("click", (e) => {
  const d = e.target.closest("[data-tdot]");
  if (d) { tShow(+d.dataset.tdot); tRestart(); }
});
$("#testimonialList").addEventListener("scroll", () => {
  const track = $("#testimonialList");
  const idx = Math.round(Math.abs(track.scrollLeft) / track.clientWidth);
  if (idx !== tIndex && idx < TESTIMONIALS.length) {
    tIndex = idx;
    $$("#tDots .hero-banner__dot").forEach((d, i) => d.classList.toggle("is-active", i === tIndex));
  }
}, { passive: true });
tRestart();

/* ---------- Filters ---------- */
function setFilter(f) {
  activeFilter = f;
  $$("#filterTabs .filter-chip").forEach((chip) => {
    const on = chip.dataset.filter === f;
    chip.classList.toggle("is-active", on);
    chip.setAttribute("aria-pressed", on);
  });
  renderProducts();
}

$("#filterTabs").addEventListener("click", (e) => {
  const chip = e.target.closest(".filter-chip");
  if (chip) setFilter(chip.dataset.filter);
});

/* ---------- Search (mobile + desktop fields) ---------- */
const searchInputs = [$("#searchInputMobile"), $("#searchInputDesktop")].filter(Boolean);

searchInputs.forEach((input) => {
  input.addEventListener("input", () => {
    searchQuery = input.value;
    // keep both fields in sync
    searchInputs.forEach((other) => { if (other !== input) other.value = input.value; });
    renderProducts();
    if (searchQuery) $("#products").scrollIntoView({ behavior: "smooth", block: "start" });
  });
});

/* ---------- City picker (mobile + desktop) ---------- */
const cityNameEls = [$("#cityName"), $("#cityNameDesktop")].filter(Boolean);
const cityPickers = [
  { btn: $("#locationBtn"), pop: $("#cityPop") },
  { btn: $("#locationBtnDesktop"), pop: $("#cityPopDesktop") },
].filter((p) => p.btn && p.pop);

const savedCity = localStorage.getItem("coffeete-city");
if (savedCity) cityNameEls.forEach((el) => (el.textContent = savedCity));

function closeAllCityPops() {
  cityPickers.forEach(({ btn, pop }) => {
    pop.hidden = true;
    btn.setAttribute("aria-expanded", "false");
  });
}

cityPickers.forEach(({ btn, pop }) => {
  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    const willOpen = pop.hidden;
    closeAllCityPops();
    if (willOpen) {
      pop.hidden = false;
      btn.setAttribute("aria-expanded", "true");
      $$("button", pop).forEach((b) =>
        b.classList.toggle("is-selected", b.dataset.city === cityNameEls[0].textContent)
      );
    }
  });

  $$("button", pop).forEach((b) => {
    b.addEventListener("click", () => {
      cityNameEls.forEach((el) => (el.textContent = b.dataset.city));
      localStorage.setItem("coffeete-city", b.dataset.city);
      closeAllCityPops();
      showToast(`شهر شما به «${b.dataset.city}» تغییر کرد`);
    });
  });
});

document.addEventListener("click", (e) => {
  if (!e.target.closest(".m-header__location-wrap") && !e.target.closest(".d-location-wrap")) {
    closeAllCityPops();
  }
});

/* ---------- Header buttons (mobile + desktop) ---------- */
[$("#notifBtn"), $("#notifBtnDesktop")].filter(Boolean).forEach((b) =>
  b.addEventListener("click", () => showToast("اعلان جدیدی ندارید"))
);

/* ---------- User account ---------- */
const currentUser = JSON.parse(localStorage.getItem("coffeete-user") || "null");

const loginBtn = $("#loginBtn");
if (currentUser) {
  loginBtn.innerHTML = `
    <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="4"/><path d="M5 21c0-3.7 3.1-6 7-6s7 2.3 7 6"/></svg>
    ${currentUser.name}`;
}
loginBtn.addEventListener("click", () => {
  location.href = "login.html";
});

$("#profileBtn").addEventListener("click", () => {
  location.href = "login.html";
});

[$("#chipOrders"), $("#chipOrdersDesktop")].filter(Boolean).forEach((b) =>
  b.addEventListener("click", () => showToast("برای مشاهده سفارش‌ها ابتدا وارد شوید"))
);

/* ---------- Categories mega menu (desktop) ---------- */
const catMenuBtn = $("#catMenuBtn");
const catMenu = $("#catMenu");
if (catMenuBtn && catMenu) {
  catMenuBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    const open = catMenu.hidden;
    catMenu.hidden = !open;
    catMenuBtn.setAttribute("aria-expanded", open);
  });
  document.addEventListener("click", (e) => {
    if (!catMenu.hidden && !e.target.closest(".catmenu-wrap")) {
      catMenu.hidden = true;
      catMenuBtn.setAttribute("aria-expanded", "false");
    }
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !catMenu.hidden) {
      catMenu.hidden = true;
      catMenuBtn.setAttribute("aria-expanded", "false");
    }
  });
}

/* ---------- Cart ---------- */
const drawer = $("#cartDrawer");
const overlay = $("#overlay");

function openCart() {
  drawer.hidden = false;
  overlay.hidden = false;
  requestAnimationFrame(() => {
    drawer.classList.add("is-open");
    overlay.classList.add("is-open");
  });
  document.body.style.overflow = "hidden";
  $("#cartCloseBtn").focus();
}

function closeCart() {
  drawer.classList.remove("is-open");
  overlay.classList.remove("is-open");
  document.body.style.overflow = "";
  setTimeout(() => { drawer.hidden = true; overlay.hidden = true; }, 300);
}

$("#cartOpenBtn").addEventListener("click", openCart);
$("#cartOpenBtnMobile").addEventListener("click", openCart);
$("#cartCloseBtn").addEventListener("click", closeCart);
overlay.addEventListener("click", closeCart);
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !drawer.hidden) closeCart();
});
$("#cartEmptyShopBtn").addEventListener("click", () => {
  closeCart();
  $("#products").scrollIntoView({ behavior: "smooth" });
});

function addToCart(id) {
  const item = cart.find((i) => i.id === id);
  if (item) item.qty += 1;
  else cart.push({ id, qty: 1 });
  saveCart();
  updateCartUI();
  const p = PRODUCTS.find((p) => p.id === id);
  showToast(`«${p.name}» به سبد اضافه شد`);
}

function changeQty(id, delta) {
  const item = cart.find((i) => i.id === id);
  if (!item) return;
  item.qty += delta;
  if (item.qty <= 0) cart = cart.filter((i) => i.id !== id);
  saveCart();
  updateCartUI();
}

function removeItem(id) {
  cart = cart.filter((i) => i.id !== id);
  saveCart();
  updateCartUI();
}

function updateCartUI() {
  const count = cart.reduce((s, i) => s + i.qty, 0);
  const total = cart.reduce((s, i) => {
    const p = PRODUCTS.find((p) => p.id === i.id);
    return s + p.price * i.qty;
  }, 0);

  // Desktop cart pill: always-visible count + total
  $("#cartBadge").textContent = toFa(count);
  $("#cartTotalHeader").textContent = formatPrice(total);

  // Mobile floating cart badge: hidden when empty
  const mobileBadge = $("#cartBadgeMobile");
  mobileBadge.hidden = count === 0;
  mobileBadge.textContent = toFa(count);

  const body = $("#cartItems");
  const isEmpty = cart.length === 0;
  $("#cartEmpty").style.display = isEmpty ? "grid" : "none";
  $("#cartFoot").hidden = isEmpty;

  body.innerHTML = cart.map((i) => {
    const p = PRODUCTS.find((p) => p.id === i.id);
    return `
      <div class="cart-item">
        <span class="cart-item__thumb">${artOf(p)}</span>
        <div class="cart-item__info">
          <strong>${p.name}</strong>
          <span>${formatPrice(p.price)}</span>
        </div>
        <div class="cart-item__qty">
          <div class="qty-controls">
            <button class="qty-btn" data-inc="${p.id}" aria-label="افزایش تعداد">+</button>
            <span class="qty-num">${toFa(i.qty)}</span>
            <button class="qty-btn" data-dec="${p.id}" aria-label="کاهش تعداد">−</button>
          </div>
          <button class="cart-item__remove" data-remove="${p.id}">حذف</button>
        </div>
      </div>`;
  }).join("");

  $("#cartTotal").textContent = formatPrice(total);
}

document.addEventListener("click", (e) => {
  const add = e.target.closest("[data-add]");
  if (add) { addToCart(+add.dataset.add); return; }
  const inc = e.target.closest("[data-inc]");
  if (inc) { changeQty(+inc.dataset.inc, 1); return; }
  const dec = e.target.closest("[data-dec]");
  if (dec) { changeQty(+dec.dataset.dec, -1); return; }
  const rem = e.target.closest("[data-remove]");
  if (rem) { removeItem(+rem.dataset.remove); return; }
  const card = e.target.closest(".product-card[data-id]");
  if (card) openProductModal(+card.dataset.id);
});

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeProductModal();
  if ((e.key === "Enter" || e.key === " ") && e.target.matches(".product-card[data-id]")) {
    e.preventDefault();
    openProductModal(+e.target.dataset.id);
  }
});

$("#checkoutBtn").addEventListener("click", async () => {
  if (!cart.length) return;
  showToast("ثبت سفارش در نسخه نمایشی غیرفعال است");
});

/* ---------- Toast ---------- */
let toastTimer;
function showToast(msg) {
  const toast = $("#toast");
  toast.textContent = msg;
  toast.hidden = false;
  requestAnimationFrame(() => toast.classList.add("is-visible"));
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    toast.classList.remove("is-visible");
    setTimeout(() => (toast.hidden = true), 300);
  }, 2600);
}

/* ---------- Blog (homepage cards) ---------- */
function renderBlogCards() {
  const section = $("#blog");
  if (!BLOGS.length) { section.hidden = true; return; }
  section.hidden = false;
  // On static hosting (no server) blog pages don't exist — keep cards visible anyway.
  $("#blogList").innerHTML = BLOGS.slice(0, 3).map((b) => `
    <article class="blog-card">
      <a href="#blog" class="blog-card__cover">
        ${b.cover ? `<img src="${b.cover}" alt="${b.title}" loading="lazy" />` : `<span class="blog-card__ph" aria-hidden="true"></span>`}
      </a>
      <div class="blog-card__body">
        <time class="blog-card__date" datetime="${b.date || ""}">${b.dateFa || ""}</time>
        <h3 class="blog-card__title"><a href="#blog">${b.title}</a></h3>
        <p class="blog-card__excerpt">${b.excerpt}</p>
        <div class="blog-card__tags">${(b.tags || []).map((t) => `<span class="blog-tag">${t}</span>`).join("")}</div>
      </div>
    </article>
  `).join("");
}

/* ---------- Settings (admin-editable texts) ---------- */
function applySettings() {
  if (!SETTINGS) return;
  const s = SETTINGS;
  if (s.siteTitle) document.title = s.siteTitle;
  if (s.siteDescription) {
    const md = document.querySelector('meta[name="description"]');
    if (md) md.setAttribute("content", s.siteDescription);
  }
  if (s.phone) {
    $$('a[href^="tel:"]').forEach((a) => (a.href = `tel:${s.phone}`));
  }
}

/* ---------- Banner slider ---------- */
let bannerIndex = 0;
let bannerTimer = null;

function bannerSlides() {
  if (BANNERS.length) {
    return BANNERS.map((b) => {
      const img = `<img src="${b.image}" alt="${b.title || "بنر کافیته"}" loading="lazy" />`;
      return b.link
        ? `<a class="hero-banner__slide" href="${b.link}">${img}</a>`
        : `<div class="hero-banner__slide">${img}</div>`;
    });
  }
  // Default branded slide (when no banner uploaded yet)
  const t1 = (SETTINGS && SETTINGS.heroTitle1) || "قهوه به اندازه،";
  const t2 = (SETTINGS && SETTINGS.heroTitle2) || "به قیمتِ درست";
  const sub = (SETTINGS && SETTINGS.heroSubtitle) || "دانه‌های قهوه تازه‌رست، اسپرسوساز و لوازم جانبی — همه در کافیته.";
  return [`
    <a class="hero-banner__slide" href="products.html">
      <div class="hero-banner__default">
        <h2>${t1} <span>${t2}</span></h2>
        <p>${sub}</p>
      </div>
    </a>`];
}

function showBanner(i) {
  const slides = $$("#bannerTrack .hero-banner__slide");
  if (!slides.length) return;
  bannerIndex = (i + slides.length) % slides.length;
  slides.forEach((s, idx) => s.classList.toggle("is-active", idx === bannerIndex));
  $$("#bannerDots .hero-banner__dot").forEach((d, idx) => d.classList.toggle("is-active", idx === bannerIndex));
}

function restartBannerTimer() {
  clearInterval(bannerTimer);
  const count = $$("#bannerTrack .hero-banner__slide").length;
  if (count > 1) bannerTimer = setInterval(() => showBanner(bannerIndex + 1), 5000);
}

function renderBanners() {
  const slides = bannerSlides();
  $("#bannerTrack").innerHTML = slides.join("");
  const many = slides.length > 1;
  $("#bannerPrev").hidden = !many;
  $("#bannerNext").hidden = !many;
  $("#bannerDots").innerHTML = many
    ? slides.map((_, i) => `<button class="hero-banner__dot" data-dot="${i}" aria-label="بنر ${toFa(i + 1)}"></button>`).join("")
    : "";
  showBanner(0);
  restartBannerTimer();
}

$("#bannerNext").addEventListener("click", () => { showBanner(bannerIndex + 1); restartBannerTimer(); });
$("#bannerPrev").addEventListener("click", () => { showBanner(bannerIndex - 1); restartBannerTimer(); });
$("#bannerDots").addEventListener("click", (e) => {
  const dot = e.target.closest("[data-dot]");
  if (dot) { showBanner(+dot.dataset.dot); restartBannerTimer(); }
});


/* ---------- Data loading ---------- */
function renderAll() {
  renderCategories();
  renderFeatured();
  renderProducts();
  renderTestimonials();
  renderBlogCards();
  renderBanners();
  updateCartUI();
}

/* ---------- Init ---------- */
renderAll();
