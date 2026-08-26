/* ============================================================
   Coffeete — کافیته | shop.js (products.html)
   ============================================================ */
"use strict";

const faDigits = ["۰", "۱", "۲", "۳", "۴", "۵", "۶", "۷", "۸", "۹"];
const toFa = (n) => String(n).replace(/\d/g, (d) => faDigits[+d]);
const formatPrice = (n) => toFa(n.toLocaleString("en-US").replace(/,/g, "٬")) + " تومان";
const $ = (s, c = document) => c.querySelector(s);
const $$ = (s, c = document) => [...c.querySelectorAll(s)];

/* ---------- SVG art (same set as homepage) ---------- */
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
    </svg>`;
  },
  grinder(color) {
    return `<svg viewBox="0 0 120 140" fill="none" role="img" aria-hidden="true">
      <path d="M38 12h44l-4 26H42l-4-26Z" fill="#525c78"/>
      <rect x="34" y="38" width="52" height="34" rx="8" fill="${color}"/>
      <rect x="42" y="46" width="36" height="18" rx="5" fill="rgba(255,255,255,.25)"/>
      <path d="M40 72h40l-6 54H46l-6-54Z" fill="#dfe5f5"/>
      <ellipse cx="60" cy="98" rx="11" ry="14" fill="${color}"/>
      <rect x="52" y="4" width="16" height="10" rx="4" fill="${color}"/>
    </svg>`;
  },
  mokapot(color) {
    return `<svg viewBox="0 0 120 140" fill="none" role="img" aria-hidden="true">
      <path d="M40 14h40l6 34H34l6-34Z" fill="${color}"/>
      <path d="M34 48h52l-8 20H42l-8-20Z" fill="rgba(0,0,0,.15)"/>
      <path d="M42 68h36l8 44a8 8 0 0 1-8 10H42a8 8 0 0 1-8-10l8-44Z" fill="${color}"/>
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
    </svg>`;
  },
  scale(color) {
    return `<svg viewBox="0 0 120 140" fill="none" role="img" aria-hidden="true">
      <rect x="16" y="84" width="88" height="36" rx="10" fill="${color}"/>
      <rect x="26" y="94" width="34" height="16" rx="4" fill="#fff"/>
      <circle cx="86" cy="102" r="8" fill="rgba(255,255,255,.35)"/>
      <rect x="24" y="40" width="72" height="40" rx="8" fill="#dfe5f5"/>
      <ellipse cx="60" cy="42" rx="36" ry="8" fill="#c8d2ec"/>
    </svg>`;
  },
};

/* ---------- Fallback data (same as homepage) ---------- */
let PRODUCTS = [
  { id: 1,  cat: "beans",     art: "bag:#2b36a9:#ffd88a", name: "دانه قهوه عربیکا اتیوپی یرگاچف", meta: "رست روشن • ۲۵۰ گرم", price: 385000, old: 450000, rating: 4.8, badge: "پرفروش", taste: "fruity", caffeine: "med" },
  { id: 2,  cat: "beans",     art: "bag:#1b2145:#f59e0b", name: "دانه قهوه ربوستا ویتنام", meta: "رست دارک • ۲۵۰ گرم", price: 295000, old: null, rating: 4.6, badge: null, taste: "bitter", caffeine: "high" },
  { id: 3,  cat: "beans",     art: "bag:#4553cc:#ffffff", name: "ترکیب ۷۰/۳۰ عربیکا-ربوستا", meta: "رست مدیوم • ۵۰۰ گرم", price: 520000, old: 610000, rating: 4.9, badge: "تخفیف", taste: "balanced", caffeine: "high" },
  { id: 4,  cat: "beans",     art: "bag:#222b8b:#ffd88a", name: "دانه قهوه کلمبیا سوپریمو", meta: "رست مدیوم • ۲۵۰ گرم", price: 410000, old: null, rating: 4.7, badge: null, taste: "balanced", caffeine: "med" },
  { id: 5,  cat: "beans",     art: "bag:#14194a:#ffffff", name: "ترکیب ۵۰/۵۰ اسپرسو بار", meta: "رست دارک • ۱ کیلوگرم", price: 890000, old: 990000, rating: 4.8, badge: "اقتصادی", taste: "bitter", caffeine: "high" },
  { id: 6,  cat: "ground",    art: "bag:#5b3a1e:#ffd88a", name: "قهوه ترک آسیاب‌شده", meta: "آسیاب ریز • ۲۰۰ گرم", price: 245000, old: null, rating: 4.5, badge: null, taste: "bitter", caffeine: "med" },
  { id: 7,  cat: "ground",    art: "bag:#7a5c3e:#ffffff", name: "قهوه فرانسه آسیاب‌شده", meta: "آسیاب متوسط • ۲۵۰ گرم", price: 268000, old: 310000, rating: 4.6, badge: "تخفیف", taste: "balanced", caffeine: "med" },
  { id: 8,  cat: "machine",   art: "machine:#2b36a9", name: "اسپرسوساز خانگی کافیته مدل K۱۰", meta: "تک‌گروپ • پمپ ۲۰ بار", price: 14800000, old: 16500000, rating: 4.7, badge: "پیشنهاد" },
  { id: 9,  cat: "machine",   art: "machine:#1b2145", name: "اسپرسوساز نیمه‌صنعتی مدل Pro", meta: "دوگروپ • بویلر مسی", price: 42500000, old: null, rating: 4.9, badge: null },
  { id: 10, cat: "machine",   art: "grinder:#2b36a9", name: "آسیاب قهوه برقی کافیته", meta: "تیغه فلت • ۴۰ درجه آسیاب", price: 6900000, old: 7800000, rating: 4.6, badge: "تخفیف" },
  { id: 11, cat: "accessory", art: "mokapot:#4c5178", name: "موکاپات ۳ کاپ", meta: "آلومینیوم • مناسب گاز", price: 980000, old: null, rating: 4.5, badge: null },
  { id: 12, cat: "accessory", art: "frenchpress:#2b36a9", name: "فرنچ‌پرس ۶۰۰ میلی‌لیتر", meta: "شیشه بروسیلیکات", price: 720000, old: 850000, rating: 4.7, badge: "تخفیف" },
  { id: 13, cat: "accessory", art: "cup:#2b36a9", name: "ست ۲ عددی ماگ سرامیکی کافیته", meta: "۳۳۰ میلی‌لیتر", price: 540000, old: null, rating: 4.8, badge: "جدید" },
  { id: 14, cat: "accessory", art: "scale:#2b36a9", name: "ترازوی دیجیتال باریستا", meta: "دقت ۰.۱ گرم • تایمر", price: 1650000, old: null, rating: 4.6, badge: null },
];
let BRANDS = [];

function artOf(p) {
  if (p.image) return `<img src="${p.image}" alt="${p.name}" loading="lazy" />`;
  const [type, c1, c2] = String(p.art || "bag:#2b36a9:#ffd88a").split(":");
  return (ART[type] || ART.bag)(c1 || "#2b36a9", c2 || "#ffd88a");
}
const brandNameOf = (p) => (BRANDS.find((b) => b.id === p.brandId) || {}).name || null;

/* ---------- Filters state ---------- */
let fCats = new Set();
let fBrands = new Set();
let fSearch = "";
let fTaste = null;      // active taste-finder filter {taste, caf}

/* Preselect category from ?cat= */
const urlCat = new URLSearchParams(location.search).get("cat");
if (urlCat) fCats.add(urlCat);

/* ---------- Render ---------- */
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

function filteredList() {
  return PRODUCTS.filter((p) => {
    if (fTaste) {
      if (p.taste !== fTaste.taste) return false;
      if (fTaste.caf && p.caffeine !== fTaste.caf) return false;
    }
    if (fCats.size && !fCats.has(p.cat)) return false;
    if (fBrands.size && !fBrands.has(p.brandId)) return false;
    if (fSearch && !(p.name.includes(fSearch) || (p.meta || "").includes(fSearch))) return false;
    return true;
  });
}

function renderProducts() {
  const list = filteredList();
  $("#productsGrid").innerHTML = list.map(productCard).join("");
  $("#productsEmpty").hidden = list.length > 0;
  $("#shopCount").textContent = `${toFa(list.length)} محصول`;
}

function renderBrandChecks() {
  const q = $("#brandSearch").value.trim();
  const brands = BRANDS.filter((b) => !q || b.name.includes(q));
  $("#brandChecks").innerHTML = brands.length
    ? brands.map((b) => `
      <label class="fcheck"><input type="checkbox" value="${b.id}" data-fbrand ${fBrands.has(b.id) ? "checked" : ""} /> ${b.name}</label>
    `).join("")
    : `<p class="t-muted" style="font-size:.82rem;color:var(--ink-mute)">برندی پیدا نشد</p>`;
}

/* ---------- Filter events ---------- */
$$("[data-fcat]").forEach((cb) => {
  cb.checked = fCats.has(cb.value);
  cb.addEventListener("change", () => {
    cb.checked ? fCats.add(cb.value) : fCats.delete(cb.value);
    renderProducts();
  });
});

document.addEventListener("change", (e) => {
  const cb = e.target.closest("[data-fbrand]");
  if (!cb) return;
  const id = Number(cb.value);
  cb.checked ? fBrands.add(id) : fBrands.delete(id);
  renderProducts();
});

$("#brandSearch").addEventListener("input", renderBrandChecks);

$("#shopSearch").addEventListener("input", (e) => {
  fSearch = e.target.value.trim();
  renderProducts();
});

$("#clearFilters").addEventListener("click", () => {
  fCats.clear();
  fBrands.clear();
  fSearch = "";
  $("#shopSearch").value = "";
  $("#brandSearch").value = "";
  $$("[data-fcat]").forEach((cb) => (cb.checked = false));
  renderBrandChecks();
  renderProducts();
  history.replaceState(null, "", "products.html");
});

/* ---------- Taste finder ---------- */
let pickedTaste = null;
let pickedCaf = null;

const TASTE_LABELS = { bitter: "تلخ و قوی", balanced: "متعادل و شکلاتی", fruity: "میوه‌ای و ترش" };
const CAF_LABELS = { high: "کافئین زیاد", med: "کافئین متوسط", low: "کافئین کم" };

function syncTasteUI() {
  $$("#tasteChips .taste-chip").forEach((c) => c.classList.toggle("is-active", c.dataset.taste === pickedTaste));
  $$("#cafChips .taste-chip").forEach((c) => c.classList.toggle("is-active", c.dataset.caf === pickedCaf));
  $("#tasteApply").disabled = !(pickedTaste && pickedCaf);
}

$("#tasteChips").addEventListener("click", (e) => {
  const c = e.target.closest("[data-taste]");
  if (!c) return;
  pickedTaste = pickedTaste === c.dataset.taste ? null : c.dataset.taste;
  syncTasteUI();
});
$("#cafChips").addEventListener("click", (e) => {
  const c = e.target.closest("[data-caf]");
  if (!c) return;
  pickedCaf = pickedCaf === c.dataset.caf ? null : c.dataset.caf;
  syncTasteUI();
});

function applyTaste(save = true) {
  if (!(pickedTaste && pickedCaf)) return;
  fTaste = { taste: pickedTaste, caf: pickedCaf };
  let matches = filteredList();
  let relaxed = false;
  if (!matches.length) {
    // relax caffeine, keep taste
    fTaste = { taste: pickedTaste, caf: null };
    matches = filteredList();
    relaxed = true;
  }
  renderProducts();
  const result = $("#tasteResult");
  result.hidden = false;
  if (matches.length) {
    result.textContent = relaxed
      ? `با ${CAF_LABELS[pickedCaf]} دقیقاً چیزی نداشتیم، اما این‌ها با سلیقه «${TASTE_LABELS[pickedTaste]}» جورند: ${toFa(matches.length)} محصول ↓`
      : `بر اساس سلیقه شما (${TASTE_LABELS[pickedTaste]} + ${CAF_LABELS[pickedCaf]})، ${toFa(matches.length)} محصول پیدا شد ↓`;
  } else {
    result.textContent = "فعلاً محصولی با این سلیقه نداریم — به‌زودی اضافه می‌شود!";
    fTaste = null;
    renderProducts();
  }
  $("#tasteClear").hidden = false;
  if (save) localStorage.setItem("coffeete-taste", JSON.stringify({ taste: pickedTaste, caf: pickedCaf }));
  $("#shopCount").scrollIntoView({ behavior: "smooth", block: "center" });
}

$("#tasteApply").addEventListener("click", () => applyTaste());

$("#tasteClear").addEventListener("click", () => {
  pickedTaste = null;
  pickedCaf = null;
  fTaste = null;
  localStorage.removeItem("coffeete-taste");
  $("#tasteResult").hidden = true;
  $("#tasteClear").hidden = true;
  syncTasteUI();
  renderProducts();
});

/* Restore saved taste per user */
const savedTaste = JSON.parse(localStorage.getItem("coffeete-taste") || "null");
if (savedTaste && savedTaste.taste && savedTaste.caf) {
  pickedTaste = savedTaste.taste;
  pickedCaf = savedTaste.caf;
  syncTasteUI();
}

/* Mobile filters toggle */
const filtersPanel = $("#filtersPanel");
const filtersToggle = $("#filtersToggle");
function syncFiltersVisibility() {
  if (window.innerWidth >= 900) { filtersPanel.hidden = false; }
  else if (filtersToggle.getAttribute("aria-expanded") !== "true") { filtersPanel.hidden = true; }
}
filtersToggle.addEventListener("click", () => {
  const open = filtersPanel.hidden;
  filtersPanel.hidden = !open;
  filtersToggle.setAttribute("aria-expanded", open);
});
window.addEventListener("resize", syncFiltersVisibility);
syncFiltersVisibility();

/* ---------- Cart (shared with homepage via localStorage) ---------- */
let cart = JSON.parse(localStorage.getItem("coffeete-cart") || "[]");
const saveCart = () => localStorage.setItem("coffeete-cart", JSON.stringify(cart));

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
}
function closeCart() {
  drawer.classList.remove("is-open");
  overlay.classList.remove("is-open");
  document.body.style.overflow = "";
  setTimeout(() => { drawer.hidden = true; overlay.hidden = true; }, 300);
}
$("#cartOpenBtn").addEventListener("click", openCart);
const mobileCartBtn = $("#cartOpenBtnMobile");
if (mobileCartBtn) mobileCartBtn.addEventListener("click", openCart);
$("#cartCloseBtn").addEventListener("click", closeCart);
overlay.addEventListener("click", closeCart);
document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !drawer.hidden) closeCart(); });
$("#cartEmptyShopBtn").addEventListener("click", closeCart);
$("#checkoutBtn").addEventListener("click", async () => {
  if (!cart.length) return;
  showToast("ثبت سفارش در نسخه نمایشی غیرفعال است");
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

function updateCartUI() {
  const known = cart.filter((i) => PRODUCTS.some((p) => p.id === i.id));
  const count = known.reduce((s, i) => s + i.qty, 0);
  const total = known.reduce((s, i) => s + PRODUCTS.find((p) => p.id === i.id).price * i.qty, 0);

  $("#cartBadge").textContent = toFa(count);
  $("#cartTotalHeader").textContent = formatPrice(total);
  const mBadge = $("#cartBadgeMobile");
  if (mBadge) { mBadge.hidden = count === 0; mBadge.textContent = toFa(count); }

  const isEmpty = known.length === 0;
  $("#cartEmpty").style.display = isEmpty ? "grid" : "none";
  $("#cartFoot").hidden = isEmpty;

  $("#cartItems").innerHTML = known.map((i) => {
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
  if (rem) { cart = cart.filter((i) => i.id !== +rem.dataset.remove); saveCart(); updateCartUI(); return; }
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

/* ---------- Load data ---------- */
async function load() {
  renderBrandChecks();
  renderProducts();
  updateCartUI();
}

renderProducts();
updateCartUI();
load();
