/* ============================================================
   FAMA — منطق فروشگاه (سبد خرید، رندر محصولات، تعاملات)
   ============================================================ */

(function () {
  'use strict';

  /* ---------- Helpers ---------- */
  const $ = (s, c) => (c || document).querySelector(s);
  const $$ = (s, c) => Array.from((c || document).querySelectorAll(s));

  const faNum = new Intl.NumberFormat('fa-IR');
  const formatPrice = (n) => faNum.format(n);

  const CAT_NAME = Object.fromEntries(FAMA_CATEGORIES.map((c) => [c.id, c.name]));

  /* ---------- SVG product art ---------- */
  let gradSeq = 0;

  function art(type, hue) {
    const id = 'g' + ++gradSeq;
    const [a, b] = hue;
    const grad = `<defs><linearGradient id="${id}" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="${a}"/><stop offset="1" stop-color="${b}"/></linearGradient></defs>`;
    const shapes = {
      lipstick: `<rect x="38" y="52" width="24" height="38" rx="5" fill="#4A0D2C"/>
        <rect x="41" y="44" width="18" height="12" rx="3" fill="#D4A5BC"/>
        <path d="M43 46 L43 22 Q43 14 51 14 L57 20 L57 46 Z" fill="url(#${id})"/>`,
      foundation: `<rect x="34" y="34" width="32" height="54" rx="8" fill="url(#${id})"/>
        <rect x="34" y="52" width="32" height="18" fill="#FFFFFF" opacity="0.25"/>
        <rect x="42" y="22" width="16" height="14" rx="3" fill="#4A0D2C"/>
        <rect x="46" y="12" width="8" height="12" rx="2" fill="#4A0D2C"/>
        <rect x="54" y="14" width="12" height="5" rx="2.5" fill="#4A0D2C"/>`,
      mascara: `<rect x="40" y="40" width="20" height="48" rx="6" fill="url(#${id})"/>
        <rect x="44" y="24" width="12" height="16" rx="3" fill="#4A0D2C"/>
        <rect x="47.5" y="8" width="5" height="18" rx="2.5" fill="#6B2145"/>
        <g stroke="#6B2145" stroke-width="1.6" stroke-linecap="round">
          <line x1="44" y1="11" x2="56" y2="11"/><line x1="44" y1="15" x2="56" y2="15"/>
          <line x1="44" y1="19" x2="56" y2="19"/></g>`,
      palette: `<rect x="16" y="26" width="68" height="48" rx="10" fill="url(#${id})"/>
        <g fill="#FFF" opacity="0.85">
          <circle cx="32" cy="42" r="7"/><circle cx="50" cy="42" r="7"/><circle cx="68" cy="42" r="7"/>
          <circle cx="32" cy="60" r="7"/><circle cx="50" cy="60" r="7"/><circle cx="68" cy="60" r="7"/></g>
        <rect x="16" y="78" width="68" height="6" rx="3" fill="#4A0D2C" opacity="0.5"/>`,
      serum: `<path d="M36 44 Q36 38 42 38 L58 38 Q64 38 64 44 L64 80 Q64 88 56 88 L44 88 Q36 88 36 80 Z" fill="url(#${id})"/>
        <rect x="44" y="26" width="12" height="12" rx="2" fill="#4A0D2C"/>
        <path d="M48 26 L48 14 L52 14 L52 26 Z" fill="#6B2145"/>
        <path d="M50 46 Q56 54 50 60 Q44 54 50 46 Z" fill="#FFF" opacity="0.6"/>`,
      cream: `<rect x="28" y="42" width="44" height="42" rx="10" fill="url(#${id})"/>
        <rect x="26" y="30" width="48" height="14" rx="7" fill="#4A0D2C"/>
        <ellipse cx="50" cy="63" rx="13" ry="9" fill="#FFF" opacity="0.4"/>`,
      perfume: `<circle cx="50" cy="60" r="26" fill="url(#${id})"/>
        <circle cx="42" cy="52" r="8" fill="#FFF" opacity="0.35"/>
        <rect x="44" y="24" width="12" height="12" rx="3" fill="#4A0D2C"/>
        <rect x="46" y="14" width="8" height="10" rx="2" fill="#6B2145"/>
        <circle cx="63" cy="16" r="2" fill="${b}"/><circle cx="70" cy="12" r="1.6" fill="${b}"/>
        <circle cx="68" cy="20" r="1.3" fill="${b}"/>`,
      liner: `<g transform="rotate(38 50 50)">
        <rect x="44" y="16" width="12" height="52" rx="4" fill="url(#${id})"/>
        <path d="M46 68 L54 68 L50 86 Z" fill="#4A0D2C"/>
        <rect x="44" y="10" width="12" height="8" rx="3" fill="#4A0D2C"/></g>`,
      highlighter: `<circle cx="50" cy="52" r="30" fill="url(#${id})"/>
        <circle cx="50" cy="52" r="21" fill="#FFF" opacity="0.28"/>
        <path d="M50 34 L53 46 L65 49 L53 52 L50 64 L47 52 L35 49 L47 46 Z" fill="#FFF" opacity="0.85"/>
        <rect x="26" y="20" width="48" height="7" rx="3.5" fill="#4A0D2C" opacity="0.45"/>`,
      mask: `<rect x="24" y="24" width="52" height="60" rx="9" fill="url(#${id})"/>
        <path d="M24 40 Q37 32 50 40 Q63 48 76 40 L76 33 Q63 41 50 33 Q37 25 24 33 Z" fill="#FFF" opacity="0.35"/>
        <circle cx="42" cy="56" r="3" fill="#4A0D2C" opacity="0.55"/>
        <circle cx="58" cy="56" r="3" fill="#4A0D2C" opacity="0.55"/>
        <path d="M43 68 Q50 74 57 68" stroke="#4A0D2C" stroke-width="2.4" fill="none" opacity="0.55" stroke-linecap="round"/>`,
      polish: `<path d="M38 52 Q38 46 44 46 L56 46 Q62 46 62 52 L62 80 Q62 88 54 88 L46 88 Q38 88 38 80 Z" fill="url(#${id})"/>
        <rect x="44" y="16" width="12" height="30" rx="4" fill="#4A0D2C"/>
        <path d="M44 56 Q50 62 44 70 Z" fill="#FFF" opacity="0.5"/>`,
      brush: `<g transform="rotate(30 50 50)">
        <rect x="45" y="42" width="10" height="44" rx="4" fill="#4A0D2C"/>
        <rect x="44" y="34" width="12" height="10" rx="2" fill="#D4A5BC"/>
        <path d="M44 34 Q42 16 50 10 Q58 16 56 34 Z" fill="url(#${id})"/></g>`,
    };
    return `<svg class="product-art" viewBox="0 0 100 100" aria-hidden="true" focusable="false">${grad}${shapes[type] || shapes.cream}</svg>`;
  }

  function mediaBg(hue) {
    return `background: linear-gradient(140deg, ${hue[0]}26, ${hue[1]}14);`;
  }

  /* ---------- Icons ---------- */
  const ICONS = {
    star: '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>',
    heart: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>',
    cartAdd: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/></svg>',
    check: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>',
    trash: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>',
    bag: '<svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/></svg>',
  };

  function starRow(rating) {
    let s = '<span class="stars" aria-hidden="true">';
    for (let i = 1; i <= 5; i++) {
      s += `<span style="opacity:${i <= Math.round(rating) ? 1 : 0.25}">${ICONS.star}</span>`;
    }
    return s + '</span>';
  }

  /* ---------- Wishlist ---------- */
  const wishKey = 'fama_wishlist';
  let wishlist = JSON.parse(localStorage.getItem(wishKey) || '[]');

  function toggleWish(id, btn) {
    const i = wishlist.indexOf(id);
    if (i > -1) wishlist.splice(i, 1);
    else wishlist.push(id);
    localStorage.setItem(wishKey, JSON.stringify(wishlist));
    btn.classList.toggle('active', wishlist.includes(id));
    btn.setAttribute('aria-pressed', wishlist.includes(id));
  }

  /* ---------- Cart ---------- */
  const cartKey = 'fama_cart';
  let cart = JSON.parse(localStorage.getItem(cartKey) || '[]');

  const saveCart = () => localStorage.setItem(cartKey, JSON.stringify(cart));

  function addToCart(id) {
    const item = cart.find((c) => c.id === id);
    if (item) item.qty++;
    else cart.push({ id, qty: 1 });
    saveCart();
    renderCart();
    showToast('به سبد خرید اضافه شد');
  }

  function setQty(id, qty) {
    const item = cart.find((c) => c.id === id);
    if (!item) return;
    item.qty = qty;
    if (item.qty <= 0) cart = cart.filter((c) => c.id !== id);
    saveCart();
    renderCart();
  }

  function cartTotal() {
    return cart.reduce((sum, c) => {
      const p = FAMA_PRODUCTS.find((x) => x.id === c.id);
      return sum + (p ? p.price * c.qty : 0);
    }, 0);
  }

  function renderCart() {
    const countEl = $('#cartCount');
    const items = $('#cartItems');
    const totalEl = $('#cartTotal');
    const count = cart.reduce((s, c) => s + c.qty, 0);
    if (countEl) {
      countEl.textContent = faNum.format(count);
      countEl.style.display = count ? 'flex' : 'none';
    }
    if (!items) return;

    if (!cart.length) {
      items.innerHTML = `<div class="cart-empty">${ICONS.bag}<p>سبد خرید شما خالی است</p>
        <a href="products.html" class="btn btn-primary btn-sm">مشاهده محصولات</a></div>`;
    } else {
      items.innerHTML = cart.map((c) => {
        const p = FAMA_PRODUCTS.find((x) => x.id === c.id);
        if (!p) return '';
        return `<div class="cart-item">
          <div class="cart-item-media" style="${mediaBg(p.hue)}">${art(p.art, p.hue)}</div>
          <div class="cart-item-info">
            <h4>${p.name}</h4>
            <span class="price">${formatPrice(p.price)} <small>تومان</small></span>
            <div class="qty-row">
              <div class="qty">
                <button type="button" data-qty="${p.id}:1" aria-label="افزایش تعداد">+</button>
                <span>${faNum.format(c.qty)}</span>
                <button type="button" data-qty="${p.id}:-1" aria-label="کاهش تعداد">−</button>
              </div>
              <button type="button" class="remove-btn" data-remove="${p.id}" aria-label="حذف از سبد">${ICONS.trash}</button>
            </div>
          </div>
        </div>`;
      }).join('');
    }
    if (totalEl) totalEl.innerHTML = `${formatPrice(cartTotal())} <small>تومان</small>`;
  }

  /* ---------- Toast ---------- */
  let toastTimer;
  function showToast(msg) {
    let t = $('#toast');
    if (!t) {
      t = document.createElement('div');
      t.id = 'toast';
      t.className = 'toast';
      t.setAttribute('role', 'status');
      document.body.appendChild(t);
    }
    t.innerHTML = `${ICONS.check}<span>${msg}</span>`;
    t.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.remove('show'), 2400);
  }

  /* ---------- Product card ---------- */
  function productCard(p) {
    const badges = { sale: ['badge-sale', 'تخفیف'], new: ['badge-new', 'جدید'], hot: ['badge-hot', 'پرفروش'] };
    const badge = p.badge ? `<span class="badge ${badges[p.badge][0]}">${badges[p.badge][1]}</span>` : '';
    const oldP = p.oldPrice ? `<span class="price-old">${formatPrice(p.oldPrice)}</span>` : '';
    const wished = wishlist.includes(p.id) ? ' active' : '';
    return `<article class="product-card">
      ${badge}
      <button type="button" class="wish-btn${wished}" data-wish="${p.id}" aria-pressed="${wishlist.includes(p.id)}" aria-label="افزودن به علاقه‌مندی‌ها">${ICONS.heart}</button>
      <a class="product-media" href="product.html?id=${p.id}" style="${mediaBg(p.hue)}" aria-label="${p.name}">
        ${art(p.art, p.hue)}
      </a>
      <div class="product-body">
        <span class="product-cat">${CAT_NAME[p.cat]}</span>
        <h3 class="product-name"><a href="product.html?id=${p.id}">${p.name}</a></h3>
        <div class="product-rating">${starRow(p.rating)}<span>(${faNum.format(p.reviews)} نظر)</span></div>
        <div class="product-foot">
          <div class="price-wrap">${oldP}<span class="price">${formatPrice(p.price)} <small>تومان</small></span></div>
          <button type="button" class="add-btn" data-add="${p.id}">${ICONS.cartAdd}<span>افزودن</span></button>
        </div>
      </div>
    </article>`;
  }

  /* ---------- Home page ---------- */
  function initHome() {
    const featured = $('#featuredGrid');
    if (featured) featured.innerHTML = FAMA_PRODUCTS.slice(0, 8).map(productCard).join('');
    const news = $('#newGrid');
    if (news) {
      news.innerHTML = FAMA_PRODUCTS.filter((p) => p.badge === 'new' || p.badge === 'hot')
        .concat(FAMA_PRODUCTS.slice(8))
        .slice(0, 4).map(productCard).join('');
    }
  }

  /* ---------- Shop page ---------- */
  function initShop() {
    const grid = $('#shopGrid');
    if (!grid) return;

    const params = new URLSearchParams(location.search);
    let activeCat = params.get('cat') || 'all';
    let query = (params.get('q') || '').trim();
    let sort = 'default';

    const searchInput = $('#searchInput');
    if (searchInput && query) searchInput.value = query;

    function filtered() {
      let list = FAMA_PRODUCTS.slice();
      if (activeCat !== 'all') list = list.filter((p) => p.cat === activeCat);
      if (query) list = list.filter((p) => p.name.includes(query) || p.desc.includes(query));
      if (sort === 'cheap') list.sort((a, b) => a.price - b.price);
      if (sort === 'expensive') list.sort((a, b) => b.price - a.price);
      if (sort === 'popular') list.sort((a, b) => b.reviews - a.reviews);
      if (sort === 'rating') list.sort((a, b) => b.rating - a.rating);
      return list;
    }

    function renderFilters() {
      const wrap = $('#filterList');
      if (!wrap) return;
      const cats = [{ id: 'all', name: 'همه محصولات' }].concat(FAMA_CATEGORIES);
      wrap.innerHTML = cats.map((c) => {
        const n = c.id === 'all' ? FAMA_PRODUCTS.length : FAMA_PRODUCTS.filter((p) => p.cat === c.id).length;
        return `<li><button type="button" data-cat="${c.id}" class="${c.id === activeCat ? 'active' : ''}">
          <span>${c.name}</span><span class="count">${faNum.format(n)}</span></button></li>`;
      }).join('');
    }

    function render() {
      const list = filtered();
      grid.innerHTML = list.length
        ? list.map(productCard).join('')
        : `<p style="grid-column:1/-1;text-align:center;color:var(--color-muted-fg);padding-block:60px">محصولی مطابق جستجوی شما پیدا نشد.</p>`;
      const rc = $('#resultCount');
      if (rc) rc.textContent = `${faNum.format(list.length)} محصول`;
      renderFilters();
    }

    document.addEventListener('click', (e) => {
      const catBtn = e.target.closest('[data-cat]');
      if (catBtn) {
        activeCat = catBtn.dataset.cat;
        const url = new URL(location.href);
        if (activeCat === 'all') url.searchParams.delete('cat');
        else url.searchParams.set('cat', activeCat);
        history.replaceState(null, '', url);
        render();
      }
    });

    const sortSel = $('#sortSelect');
    if (sortSel) sortSel.addEventListener('change', () => { sort = sortSel.value; render(); });

    render();
  }

  /* ---------- Product detail page ---------- */
  function initProductPage() {
    const wrap = $('#productDetail');
    if (!wrap) return;
    const id = parseInt(new URLSearchParams(location.search).get('id'), 10) || 1;
    const p = FAMA_PRODUCTS.find((x) => x.id === id) || FAMA_PRODUCTS[0];

    document.title = `${p.name} | فروشگاه فاما`;

    const oldP = p.oldPrice ? `<span class="price-old">${formatPrice(p.oldPrice)} تومان</span>` : '';
    wrap.innerHTML = `
      <div class="pd-media" style="${mediaBg(p.hue)}">${art(p.art, p.hue)}</div>
      <div class="pd-info">
        <span class="product-cat">${CAT_NAME[p.cat]}</span>
        <h1>${p.name}</h1>
        <div class="pd-meta">
          <span class="product-rating">${starRow(p.rating)} <b>${faNum.format(p.rating)}</b></span>
          <span>${faNum.format(p.reviews)} دیدگاه کاربران</span>
          <span style="color:var(--color-success);font-weight:600">موجود در انبار</span>
        </div>
        <p class="pd-desc">${p.desc}</p>
        <ul class="pd-features">
          <li>${ICONS.check}<span>اورجینال و دارای مجوز بهداشت</span></li>
          <li>${ICONS.check}<span>ارسال سریع به سراسر کشور</span></li>
          <li>${ICONS.check}<span>ضمانت ۷ روزه بازگشت کالا</span></li>
          <li>${ICONS.check}<span>فاقد پارابن — تست‌نشده روی حیوانات</span></li>
        </ul>
        <div class="pd-price-box">
          <div class="price-wrap">${oldP}<span class="price">${formatPrice(p.price)} <small>تومان</small></span></div>
          <div class="pd-actions">
            <button type="button" class="btn btn-primary" data-add="${p.id}">${ICONS.cartAdd} افزودن به سبد خرید</button>
            <button type="button" class="btn btn-outline wish-btn-lg" data-wish="${p.id}">${ICONS.heart} علاقه‌مندی</button>
          </div>
        </div>
      </div>`;

    const crumb = $('#crumbName');
    if (crumb) crumb.textContent = p.name;

    const rel = $('#relatedGrid');
    if (rel) {
      rel.innerHTML = FAMA_PRODUCTS.filter((x) => x.cat === p.cat && x.id !== p.id)
        .concat(FAMA_PRODUCTS.filter((x) => x.cat !== p.cat))
        .slice(0, 4).map(productCard).join('');
    }
  }

  /* ---------- Global events ---------- */
  document.addEventListener('click', (e) => {
    const addBtn = e.target.closest('[data-add]');
    if (addBtn) { addToCart(parseInt(addBtn.dataset.add, 10)); return; }

    const wishBtn = e.target.closest('[data-wish]');
    if (wishBtn) { toggleWish(parseInt(wishBtn.dataset.wish, 10), wishBtn); return; }

    const qtyBtn = e.target.closest('[data-qty]');
    if (qtyBtn) {
      const [id, d] = qtyBtn.dataset.qty.split(':').map(Number);
      const item = cart.find((c) => c.id === id);
      if (item) setQty(id, item.qty + d);
      return;
    }

    const rmBtn = e.target.closest('[data-remove]');
    if (rmBtn) { setQty(parseInt(rmBtn.dataset.remove, 10), 0); return; }
  });

  /* Cart drawer */
  function setDrawer(open) {
    $('#cartDrawer')?.classList.toggle('open', open);
    $('#overlay')?.classList.toggle('open', open);
    document.body.style.overflow = open ? 'hidden' : '';
  }
  $('#cartOpen')?.addEventListener('click', () => setDrawer(true));
  $('#cartClose')?.addEventListener('click', () => setDrawer(false));
  $('#overlay')?.addEventListener('click', () => setDrawer(false));
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') setDrawer(false); });

  /* Mobile menu */
  $('#menuToggle')?.addEventListener('click', () => {
    const nav = $('#mainNav');
    const open = nav.classList.toggle('open');
    $('#menuToggle').setAttribute('aria-expanded', open);
  });

  /* Search */
  $('#searchForm')?.addEventListener('submit', (e) => {
    e.preventDefault();
    const q = $('#searchInput')?.value.trim();
    location.href = 'products.html' + (q ? `?q=${encodeURIComponent(q)}` : '');
  });

  /* Newsletter */
  $('#newsForm')?.addEventListener('submit', (e) => {
    e.preventDefault();
    showToast('عضویت شما در خبرنامه ثبت شد');
    e.target.reset();
  });

  /* ---------- Init ---------- */
  renderCart();
  initHome();
  initShop();
  initProductPage();
})();
