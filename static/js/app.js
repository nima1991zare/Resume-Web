/* NIMA V2 — scroll engine + content + i18n */
(function () {
  "use strict";

  /* ---------------- extra i18n keys for v2 ---------------- */
  var EXTRA = {
    en: {
      "v2.r0": "Intro",
      "v2.hero1": "I BUILD",
      "v2.hero2": "DIGITAL",
      "v2.hero3": "UNIVERSES",
      "v2.heroSub": "Nima — Python & Java engineer. UX, UI, databases, backends, servers. One person. The whole stack. Zero to launch.",
      "v2.begin": "Begin the journey",
      "v2.v1": "View V1 design",
      "v2.scroll": "SCROLL",
      "v2.aboutTag": "THE CODE IN MY DNA",
      "v2.brandsTag": "IN THEIR ORBIT",
      "v2.chPhone": "Phone",
      "v2.chEmail": "Email",
      "v2.chTelegram": "Telegram",
      "v2.chGithub": "GitHub",
      "v2.chLinkedin": "LinkedIn"
    },
    fa: {
      "v2.r0": "شروع",
      "v2.hero1": "من می‌سازم",
      "v2.hero2": "دنیاهای",
      "v2.hero3": "دیجیتال",
      "v2.heroSub": "نیما — مهندس پایتون و جاوا. UX، UI، پایگاه‌داده، بک‌اند و سرور. یک نفر، تمام مسیر. از صفر تا اجرا.",
      "v2.begin": "شروع سفر",
      "v2.v1": "مشاهده طراحی نسخه ۱",
      "v2.scroll": "اسکرول",
      "v2.aboutTag": "کد در دی‌ان‌ای من",
      "v2.brandsTag": "در مدارِ آن‌ها",
      "v2.chPhone": "تلفن",
      "v2.chEmail": "ایمیل",
      "v2.chTelegram": "تلگرام",
      "v2.chGithub": "گیت‌هاب",
      "v2.chLinkedin": "لینکدین"
    }
  };
  Object.assign(window.I18N.en, EXTRA.en);
  Object.assign(window.I18N.fa, EXTRA.fa);

  var LANG_KEY = "nima_lang";
  var savedLang = localStorage.getItem(LANG_KEY);
  var autoLang = (navigator.language || "").toLowerCase().indexOf("fa") === 0 ? "fa" : "en";
  var state = {
    lang: (savedLang === "fa" || savedLang === "en") ? savedLang : autoLang,
    content: null
  };

  function t(key) {
    var dict = window.I18N[state.lang] || window.I18N.en;
    return dict[key] !== undefined ? dict[key] : (window.I18N.en[key] || key);
  }

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function isLink(u) {
    return typeof u === "string" && /^https?:\/\//i.test(u);
  }

  /* ---------------- language ---------------- */
  function applyLang() {
    var html = document.documentElement;
    html.lang = state.lang;
    html.dir = state.lang === "fa" ? "rtl" : "ltr";
    document.querySelectorAll("[data-i18n]").forEach(function (el) {
      el.textContent = t(el.getAttribute("data-i18n"));
    });
    document.querySelectorAll(".lang-opt").forEach(function (el) {
      el.classList.toggle("on", el.getAttribute("data-lang") === state.lang);
    });
    document.title = state.lang === "fa"
      ? "نیما — توسعه‌دهنده فول‌استک"
      : "Nima — Full-Stack Developer";
    if (state.content) renderContent();
  }

  document.getElementById("lang-switch").addEventListener("click", function () {
    state.lang = state.lang === "en" ? "fa" : "en";
    localStorage.setItem(LANG_KEY, state.lang);
    applyLang();
  });

  /* ---------------- scroll → morph phase ----------------
     Works on VISIBLE sections only; the background formation index is
     read from data-phase, so hiding an empty section keeps every
     remaining section paired with its own animation. */
  var allStages = Array.prototype.slice.call(document.querySelectorAll(".stage"));
  var allRail = Array.prototype.slice.call(document.querySelectorAll(".rail a"));
  var progressBar = document.getElementById("progress-bar");
  var ticking = false;
  var stages = [], phaseOf = [], C = [];

  function rebuildStages() {
    stages = allStages.filter(function (s) { return !s.hidden; });
    phaseOf = stages.map(function (s) { return Number(s.getAttribute("data-phase")) || 0; });
  }

  function recalc() {
    rebuildStages();
    C = stages.map(function (s) {
      var r = s.getBoundingClientRect();
      return r.top + window.scrollY + r.height / 2;
    });
  }

  function onScroll() {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(function () {
      ticking = false;
      if (!C.length) return;
      var mid = window.scrollY + window.innerHeight / 2;

      // interpolate between visible stage centers → real formation phase
      var idx = 0, frac = 0;
      if (mid <= C[0]) { idx = 0; frac = 0; }
      else if (mid >= C[C.length - 1]) { idx = C.length - 1; frac = 0; }
      else {
        for (var i = 0; i < C.length - 1; i++) {
          if (mid >= C[i] && mid < C[i + 1]) {
            idx = i;
            frac = (mid - C[i]) / (C[i + 1] - C[i]);
            break;
          }
        }
      }
      var nextPhase = phaseOf[Math.min(idx + 1, phaseOf.length - 1)];
      var p = phaseOf[idx] + (nextPhase - phaseOf[idx]) * frac;
      if (window.MORPH) window.MORPH.setPhase(p);

      // rail active state (match by section id)
      var activeStage = stages[frac > 0.5 ? Math.min(idx + 1, stages.length - 1) : idx];
      allRail.forEach(function (a) {
        a.classList.toggle("on", a.getAttribute("href") === "#" + activeStage.id);
      });

      // progress bar
      var doc = document.documentElement;
      var total = doc.scrollHeight - window.innerHeight;
      progressBar.style.width = (total > 0 ? (window.scrollY / total) * 100 : 0) + "%";
    });
  }

  /* ---------------- auto-hide empty sections ---------------- */
  function setSectionVisible(id, visible) {
    var sec = document.getElementById(id);
    if (sec) sec.hidden = !visible;
    document.querySelectorAll('.rail a[href="#' + id + '"], .nav-links a[href="#' + id + '"]')
      .forEach(function (a) { a.hidden = !visible; });
  }

  function updateSectionVisibility(c) {
    setSectionVisible("apps", c.apps.length > 0);
    setSectionVisible("games", (c.games || []).length > 0);
    setSectionVisible("websites", c.websites.length > 0);
    setSectionVisible("brands", c.brands.length > 0);
    // renumber the visible section headers (01, 02, …)
    var n = 0;
    allStages.forEach(function (s) {
      var num = s.querySelector(".stage-num");
      if (num && !s.hidden) {
        n++;
        num.textContent = (n < 10 ? "0" : "") + n;
      }
    });
    recalc();
  }

  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", function () { recalc(); onScroll(); }, { passive: true });
  recalc();
  onScroll();

  /* ---------------- marquee ----------------
     rAF-driven at constant px/s, clones its content to cover any
     screen width, and keeps moving regardless of OS motion settings. */
  (function () {
    var track = document.getElementById("marquee-track");
    if (!track) return;
    var baseSet = track.querySelector(".marquee-set");
    if (!baseSet) return;
    var setW = 0, offset = 0, last = null;
    var SPEED = 42; // pixels per second

    function build() {
      while (track.children.length > 1) track.removeChild(track.lastChild);
      setW = baseSet.getBoundingClientRect().width;
      if (!setW) return;
      var copies = Math.max(2, Math.ceil((window.innerWidth + setW) / setW));
      for (var i = 0; i < copies; i++) track.appendChild(baseSet.cloneNode(true));
    }

    function step(now) {
      if (last === null) last = now;
      var dt = Math.min(64, now - last);
      last = now;
      if (setW > 0) {
        offset = (offset + SPEED * dt / 1000) % setW;
        track.style.transform = "translate3d(" + (-offset).toFixed(2) + "px,0,0)";
      }
      requestAnimationFrame(step);
    }

    var buildTimer = null;
    window.addEventListener("resize", function () {
      clearTimeout(buildTimer);
      buildTimer = setTimeout(build, 150);
    }, { passive: true });
    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(build);   // re-measure once real fonts load
    }
    build();
    requestAnimationFrame(step);
  })();

  /* ---------------- animated anchor scrolling ----------------
     JS-driven (works even when the OS reduced-motion setting
     disables CSS smooth scrolling), expo easing, cancellable. */
  var scrollAnim = null;

  function animateScrollTo(targetY) {
    var startY = window.scrollY;
    var dist = targetY - startY;
    if (Math.abs(dist) < 2) return;
    var dur = Math.min(1500, 550 + Math.abs(dist) * 0.25);
    var t0 = null;
    if (scrollAnim) cancelAnimationFrame(scrollAnim);

    function easeInOutCubic(t) {
      return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
    }
    function tick(now) {
      if (t0 === null) t0 = now;
      var k = Math.min(1, (now - t0) / dur);
      window.scrollTo(0, startY + dist * easeInOutCubic(k));
      scrollAnim = k < 1 ? requestAnimationFrame(tick) : null;
    }
    scrollAnim = requestAnimationFrame(tick);
  }

  // let the user take back control mid-animation
  ["wheel", "touchstart"].forEach(function (ev) {
    window.addEventListener(ev, function () {
      if (scrollAnim) { cancelAnimationFrame(scrollAnim); scrollAnim = null; }
    }, { passive: true });
  });
  window.addEventListener("keydown", function (e) {
    if (scrollAnim && ["ArrowUp", "ArrowDown", "PageUp", "PageDown", "Home", "End", " "].indexOf(e.key) >= 0) {
      cancelAnimationFrame(scrollAnim); scrollAnim = null;
    }
  }, { passive: true });

  // one delegated handler covers nav links, rail dots, hero CTAs and
  // dynamically-rendered buy/order buttons
  document.addEventListener("click", function (e) {
    var a = e.target.closest ? e.target.closest('a[href^="#"]') : null;
    if (!a) return;
    var id = a.getAttribute("href").slice(1);
    var el = id && document.getElementById(id);
    if (!el) return;
    e.preventDefault();
    animateScrollTo(el.getBoundingClientRect().top + window.scrollY);
    if (history.pushState) history.pushState(null, "", "#" + id);
  });

  /* ---------------- reveal ---------------- */
  function observeReveals() {
    var els = document.querySelectorAll(".reveal:not(.in)");
    if (!("IntersectionObserver" in window)) {
      els.forEach(function (el) { el.classList.add("in"); });
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) {
          e.target.classList.add("in");
          io.unobserve(e.target);
        }
      });
    }, { threshold: 0.15 });
    els.forEach(function (el) { io.observe(el); });
  }
  observeReveals();

  /* ---------------- content ---------------- */
  function pick(item, field) {
    var v = state.lang === "fa" ? item[field + "_fa"] : item[field + "_en"];
    return v || item[field + "_en"] || "";
  }

  function fmtPrice(price, currency) {
    if (!price || price <= 0) return "";
    var locale = state.lang === "fa" ? "fa-IR" : "en-US";
    if (currency === "IRT") {   // Toman — not an ISO code, format manually
      var n = new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(price);
      return state.lang === "fa" ? n + " تومان" : n + " Toman";
    }
    try {
      return new Intl.NumberFormat(locale, {
        style: "currency", currency: currency || "USD", maximumFractionDigits: 0
      }).format(price);
    } catch (e) { return price + " " + (currency || ""); }
  }

  function media(item) {
    if (item.image) return '<img src="' + esc(item.image) + '" alt="' + esc(pick(item, "title")) + '" loading="lazy">';
    return '<span class="ph" aria-hidden="true">&lt;/&gt;</span>';
  }

  function tech(v) {
    if (!v) return "";
    return '<div class="vtech">' + v.split(/[·,]/).map(function (x) {
      x = x.trim();
      return x ? "<span>" + esc(x) + "</span>" : "";
    }).join("") + "</div>";
  }

  function pad(n) { return n < 10 ? "0" + n : "" + n; }

  function renderContent() {
    var c = state.content;
    if (!c) return;

    var aboutKey = state.lang === "fa" ? "about_fa" : "about_en";
    document.getElementById("about-body").textContent = c.settings[aboutKey] || c.settings.about_en || "";

    document.getElementById("apps-grid").innerHTML = c.apps.map(function (a, i) {
      var link = "/p/apps/" + a.id;
      return '<article class="vcard reveal in">' +
        '<a class="vcard-media" href="' + link + '">' + media(a) +
          '<span class="vcard-index">APP/' + pad(i + 1) + "</span>" +
          (a.buyable ? '<span class="vbadge">' + t("apps.buyable") + "</span>" : "") +
        "</a>" +
        '<div class="vcard-body"><h3><a href="' + link + '">' + esc(pick(a, "title")) + "</a></h3>" +
          '<p class="desc">' + esc(pick(a, "desc")) + "</p>" + tech(a.tech) +
          '<div class="vfoot"><span class="vprice">' + fmtPrice(a.price, a.currency) + "</span>" +
            (a.buyable ? '<a class="btn btn-primary" href="#contact" data-subject="' + esc(pick(a, "title")) + '">' + t("apps.buy") + "</a>" : "") +
          "</div></div></article>";
    }).join("");

    document.getElementById("games-grid").innerHTML = (c.games || []).map(function (g, i) {
      var link = "/p/games/" + g.id;
      return '<article class="vcard reveal in">' +
        '<a class="vcard-media" href="' + link + '">' + media(g) +
          '<span class="vcard-index">GAME/' + pad(i + 1) + "</span>" +
          (g.buyable ? '<span class="vbadge">' + t("apps.buyable") + "</span>" : "") +
        "</a>" +
        '<div class="vcard-body"><h3><a href="' + link + '">' + esc(pick(g, "title")) + "</a></h3>" +
          '<p class="desc">' + esc(pick(g, "desc")) + "</p>" + tech(g.tech) +
          '<div class="vfoot"><span class="vprice">' + fmtPrice(g.price, g.currency) + "</span>" +
            (isLink(g.url)
              ? '<a class="btn btn-ghost" href="' + esc(g.url) + '" target="_blank" rel="noopener">' + t("web.visit") + "</a>"
              : (g.buyable ? '<a class="btn btn-primary" href="#contact" data-subject="' + esc(pick(g, "title")) + '">' + t("apps.buy") + "</a>" : "")) +
          "</div></div></article>";
    }).join("");

    document.getElementById("websites-grid").innerHTML = c.websites.map(function (w, i) {
      var link = "/p/websites/" + w.id;
      return '<article class="vcard reveal in">' +
        '<a class="vcard-media" href="' + link + '">' + media(w) +
          '<span class="vcard-index">WEB/' + pad(i + 1) + "</span></a>" +
        '<div class="vcard-body"><h3><a href="' + link + '">' + esc(pick(w, "title")) + "</a></h3>" +
          '<p class="desc">' + esc(pick(w, "desc")) + "</p>" + tech(w.tech) +
          '<div class="vfoot"><span class="vprice">' + fmtPrice(w.price, w.currency) + "</span>" +
            (isLink(w.url)
              ? '<a class="btn btn-ghost" href="' + esc(w.url) + '" target="_blank" rel="noopener">' + t("web.visit") + "</a>"
              : '<a class="btn btn-ghost" href="#contact" data-subject="' + esc(pick(w, "title")) + '">' + t("web.order") + "</a>") +
          "</div></div></article>";
    }).join("");

    document.getElementById("brands-row").innerHTML = c.brands.map(function (b) {
      var inner = (b.logo ? '<img src="' + esc(b.logo) + '" alt="' + esc(b.name) + '" loading="lazy">' : "") +
        "<span>" + esc(b.name) + "</span>";
      return isLink(b.url)
        ? '<a class="brand" href="' + esc(b.url) + '" target="_blank" rel="noopener">' + inner + "</a>"
        : '<div class="brand">' + inner + "</div>";
    }).join("");

    var s = c.settings;
    var ch = [];
    if (s.phone) ch.push(['v2.chPhone', s.phone, "tel:" + String(s.phone).replace(/\s+/g, "")]);
    if (s.email) ch.push(['v2.chEmail', s.email, "mailto:" + s.email]);
    if (s.telegram) ch.push(['v2.chTelegram', "@telegram", s.telegram]);
    if (s.github) ch.push(['v2.chGithub', "github", s.github]);
    if (s.linkedin) ch.push(['v2.chLinkedin', "linkedin", s.linkedin]);
    document.getElementById("channels").innerHTML = ch.map(function (x) {
      var ext = x[2].indexOf("http") === 0;
      return '<a href="' + esc(x[2]) + '"' + (ext ? ' target="_blank" rel="noopener"' : "") + ">" +
        '<span class="ch-label">' + t(x[0]) + "</span>" +
        '<span class="ch-value">' + esc(x[1]) + "</span></a>";
    }).join("");

    document.querySelectorAll("[data-subject]").forEach(function (el) {
      el.addEventListener("click", function () {
        var sub = document.getElementById("f-subject");
        sub.value = el.getAttribute("data-subject");
        sub.dispatchEvent(new Event("input"));
      });
    });

    recalc();
  }

  function hydrate(data) {
    state.content = data;
    renderContent();
    updateSectionVisibility(data);
    applyLang();
    observeReveals();
    recalc();
    onScroll();
  }

  // content is embedded in the page by the server (zero extra round-trips,
  // and search engines see everything immediately)
  (function () {
    var inline = document.getElementById("content-data");
    if (inline) {
      try {
        hydrate(JSON.parse(inline.textContent));
        return;
      } catch (e) { /* fall through to fetch */ }
    }
    fetch("/api/content")
      .then(function (r) { return r.json(); })
      .then(hydrate)
      .catch(function () {});
  })();

  /* ---------------- contact form ---------------- */
  var form = document.getElementById("contact-form");
  var statusEl = document.getElementById("form-status");
  var submitBtn = document.getElementById("form-submit");

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var name = form.name.value.trim();
    var message = form.message.value.trim();
    form.name.classList.toggle("err", !name);
    form.message.classList.toggle("err", !message);
    if (!name || !message) {
      statusEl.textContent = t("form.required");
      statusEl.className = "form-status bad";
      return;
    }
    submitBtn.disabled = true;
    submitBtn.textContent = t("form.sending");
    fetch("/api/contact", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: name,
        email: form.email.value.trim(),
        phone: form.phone.value.trim(),
        subject: form.subject.value.trim(),
        message: message
      })
    })
      .then(function (r) { if (!r.ok) throw new Error(); return r.json(); })
      .then(function () {
        statusEl.textContent = t("form.ok");
        statusEl.className = "form-status ok";
        form.reset();
      })
      .catch(function () {
        statusEl.textContent = t("form.bad");
        statusEl.className = "form-status bad";
      })
      .finally(function () {
        submitBtn.disabled = false;
        submitBtn.textContent = t("form.send");
      });
  });

  /* ---------------- visit tracking ---------------- */
  try {
    var KEY = "nima_visit_ts";
    var last = Number(sessionStorage.getItem(KEY) || 0);
    if (Date.now() - last > 30 * 60 * 1000) {
      sessionStorage.setItem(KEY, String(Date.now()));
      fetch("/api/visit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: location.pathname, lang: state.lang, referrer: document.referrer || "" })
      }).catch(function () {});
    }
  } catch (e) {}

  // prefill contact subject from ?subject= (used by product pages)
  try {
    var qsub = new URLSearchParams(location.search).get("subject");
    if (qsub) document.getElementById("f-subject").value = qsub;
  } catch (e) { /* ignore */ }

  document.getElementById("year").textContent = new Date().getFullYear();

  /* ---------------- PWA ---------------- */
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("/sw.js").catch(function () {});
    });
  }
  applyLang();
})();
