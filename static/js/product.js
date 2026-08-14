/* Product detail page — bilingual rendering + CTAs */
(function () {
  "use strict";

  var P;
  try {
    P = JSON.parse(document.getElementById("product-data").textContent);
  } catch (e) { return; }

  var EXTRA = {
    en: {
      "pd.back": "← Back to portfolio",
      "pd.buy": "Buy Source Code",
      "pd.order": "Order a Similar One",
      "pd.visit": "Open Live",
      "pd.demo": "View Demo",
      "pd.note": "Purchase includes the complete source code — and I customize the design for you before delivery.",
      "pd.type.apps": "APPLICATION",
      "pd.type.games": "GAME",
      "pd.type.websites": "WEBSITE"
    },
    fa: {
      "pd.back": "→ بازگشت به نمونه‌کارها",
      "pd.buy": "خرید سورس‌کد",
      "pd.order": "سفارش نمونه مشابه",
      "pd.visit": "مشاهده زنده",
      "pd.demo": "مشاهده دمو",
      "pd.note": "خرید شامل سورس‌کد کامل است — و طراحی را پیش از تحویل مطابق سلیقه شما شخصی‌سازی می‌کنم.",
      "pd.type.apps": "اپلیکیشن",
      "pd.type.games": "بازی",
      "pd.type.websites": "وب‌سایت"
    }
  };
  Object.assign(window.I18N.en, EXTRA.en);
  Object.assign(window.I18N.fa, EXTRA.fa);

  var LANG_KEY = "nima_lang";
  var saved = localStorage.getItem(LANG_KEY);
  // Persian is the default; a visitor's explicit choice is remembered
  var lang = (saved === "fa" || saved === "en") ? saved : "fa";

  function t(key) {
    var d = window.I18N[lang] || window.I18N.en;
    return d[key] !== undefined ? d[key] : (window.I18N.en[key] || key);
  }
  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function fmtPrice(price, currency) {
    if (!price || price <= 0) return "";
    var locale = lang === "fa" ? "fa-IR" : "en-US";
    if (currency === "IRT") {   // Toman — not an ISO code, format manually
      var n = new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(price);
      return lang === "fa" ? n + " تومان" : n + " Toman";
    }
    try {
      return new Intl.NumberFormat(locale, {
        style: "currency", currency: currency || "USD", maximumFractionDigits: 0
      }).format(price);
    } catch (e) { return price + " " + (currency || ""); }
  }

  function render() {
    var html = document.documentElement;
    html.lang = lang;
    html.dir = lang === "fa" ? "rtl" : "ltr";
    document.querySelectorAll(".lang-opt").forEach(function (el) {
      el.classList.toggle("on", el.getAttribute("data-lang") === lang);
    });

    var title = (lang === "fa" && P.title_fa) ? P.title_fa : P.title_en;
    var desc = (lang === "fa" && P.desc_fa) ? P.desc_fa : P.desc_en;

    document.title = title + " — Nima";
    document.getElementById("pd-back").textContent = t("pd.back");
    document.getElementById("pd-badge").textContent = t("pd.type." + P.type);
    document.getElementById("pd-title").textContent = title;
    document.getElementById("pd-desc").textContent = desc;
    document.getElementById("pd-price").textContent = fmtPrice(P.price, P.currency);

    var note = document.getElementById("pd-note");
    if (P.buyable) {
      note.hidden = false;
      note.textContent = t("pd.note");
    }

    var actions = [];
    var subject = encodeURIComponent(P.title_en);
    if (P.demo_url && (/^https?:\/\//i.test(P.demo_url) || P.demo_url.indexOf("/static/") === 0)) {
      actions.push('<a class="btn btn-ghost" href="' + esc(P.demo_url) + '" target="_blank" rel="noopener">' + t("pd.demo") + "</a>");
    }
    if (P.url && /^https?:\/\//i.test(P.url)) {
      actions.push('<a class="btn btn-ghost" href="' + esc(P.url) + '" target="_blank" rel="noopener">' + t("pd.visit") + "</a>");
    }
    if (P.buyable) {
      actions.push('<a class="btn btn-primary" href="/?subject=' + subject + '#contact">' + t("pd.buy") + "</a>");
    } else {
      actions.push('<a class="btn btn-primary" href="/?subject=' + subject + '#contact">' + t("pd.order") + "</a>");
    }
    document.getElementById("pd-actions").innerHTML = actions.join("");
  }

  document.getElementById("lang-switch").addEventListener("click", function () {
    lang = lang === "en" ? "fa" : "en";
    localStorage.setItem(LANG_KEY, lang);
    render();
  });

  document.getElementById("year").textContent = new Date().getFullYear();
  render();

  // set the morphing background to this product type's formation
  var PHASES = { apps: 2, games: 3, websites: 4 };
  var tries = 0;
  (function setPhase() {
    if (window.MORPH && window.MORPH.setPhase) {
      window.MORPH.setPhase(PHASES[P.type] || 0);
    } else if (tries++ < 20) {
      setTimeout(setPhase, 100);
    }
  })();
})();
