/* Service worker
   - fonts/icons/uploads (immutable): cache-first
   - CSS/JS: stale-while-revalidate (instant load, silently refreshed â€”
     code updates always arrive by the next visit, never stuck stale)
   - pages: network-first with offline fallback
   - API and the entire admin panel: NEVER touched by this worker */
var CACHE = "nima-v12";
var PRECACHE = [
  "/",
  "/static/css/fonts.css",
  "/static/css/style.css",
  "/static/js/app.js",
  "/static/js/i18n.js",
  "/static/js/morph.js",
  "/static/fonts/spacegrotesk_v22_V8mDoQDjQSkFtoMM3T6r8E7mPbF4Cw.woff2",
  "/static/fonts/dmsans_v17_rP2Yp2ywxg089UriI5-g4vlH9VoD8Cmcqbu0-K4.woff2",
  "/static/icons/favicon.svg",
  "/manifest.json"
];
var IMMUTABLE = ["/static/fonts/", "/static/icons/", "/static/uploads/"];

self.addEventListener("install", function (e) {
  e.waitUntil(
    caches.open(CACHE).then(function (c) { return c.addAll(PRECACHE); })
      .then(function () { return self.skipWaiting(); })
  );
});

self.addEventListener("activate", function (e) {
  e.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.filter(function (k) { return k !== CACHE; })
        .map(function (k) { return caches.delete(k); }));
    }).then(function () { return self.clients.claim(); })
  );
});

function isImmutable(pathname) {
  for (var i = 0; i < IMMUTABLE.length; i++) {
    if (pathname.indexOf(IMMUTABLE[i]) === 0) return true;
  }
  return false;
}

self.addEventListener("fetch", function (e) {
  var url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;

  // API and admin panel (page + its css/js): always straight to network
  if (url.pathname.startsWith("/api/") ||
      url.pathname.startsWith("/admin") ||
      url.pathname === "/static/js/admin.js" ||
      url.pathname === "/static/css/admin.css") {
    return;
  }

  // immutable assets: cache-first
  if (isImmutable(url.pathname)) {
    e.respondWith(
      caches.match(e.request).then(function (hit) {
        return hit || fetch(e.request).then(function (res) {
          if (res.ok) {
            var copy = res.clone();
            caches.open(CACHE).then(function (c) { c.put(e.request, copy); });
          }
          return res;
        });
      })
    );
    return;
  }

  // CSS/JS/manifest: stale-while-revalidate
  if (url.pathname.startsWith("/static/") || url.pathname === "/manifest.json") {
    e.respondWith(
      caches.open(CACHE).then(function (c) {
        return c.match(e.request).then(function (hit) {
          var refresh = fetch(e.request).then(function (res) {
            if (res.ok) c.put(e.request, res.clone());
            return res;
          }).catch(function () { return hit; });
          return hit || refresh;
        });
      })
    );
    return;
  }

  // pages: network-first, offline fallback to cached shell
  e.respondWith(
    fetch(e.request).then(function (res) {
      if (res.ok) {
        var copy = res.clone();
        caches.open(CACHE).then(function (c) { c.put(e.request, copy); });
      }
      return res;
    }).catch(function () {
      return caches.match(e.request).then(function (hit) {
        return hit || caches.match("/");
      });
    })
  );
});


