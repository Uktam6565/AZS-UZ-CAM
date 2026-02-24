// frontend/service-worker.js
// GasQ PWA Service Worker (SAFE VERSION, API BYPASS)

const CACHE_NAME = "gasq-v4"; // ⬅️ увеличили версию
const ASSETS = [
  "/manifest.json",
  "/i18n.js",
  "/auth.js",
  "/pwa-install.js",
  "/qr.js",

  "/driver/index.html",
  "/terminal/index.html",
  "/admin/login.html",
  "/admin/operator.html",
  "/admin/index.html",

  "/icons/icon-192.png",
  "/icons/icon-512.png",
  "/icons/maskable-192.png",
  "/icons/maskable-512.png",
  "/icons/screenshot-1.png",
  "/icons/screenshot-2.png"
];

// --------------------
// INSTALL
// --------------------
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS))
  );
  self.skipWaiting();
});

// --------------------
// ACTIVATE
// --------------------
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.map((k) => (k !== CACHE_NAME ? caches.delete(k) : null))
      )
    )
  );
  self.clients.claim();
});

// --------------------
// FETCH
// --------------------
self.addEventListener("fetch", (event) => {
  const req = event.request;
  const url = new URL(req.url);

  // 🚫 НИКОГДА не трогаем API
  if (url.pathname.startsWith("/api/")) {
    return; // browser fetch, без кэша
  }

  // 🚫 не кэшируем не-GET
  if (req.method !== "GET") {
    return;
  }

  // ✅ UI / static assets
  event.respondWith(
    caches.match(req).then((cached) => {
      if (cached) return cached;

      return fetch(req)
        .then((res) => {
          // кэшируем только обычные 200-ответы
          if (res && res.status === 200 && res.type === "basic") {
            const copy = res.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(req, copy));
          }
          return res;
        })
        .catch(() => cached);
    })
  );
});