const CACHE_NAME = "medusa-cache-v1";
const urlsToCache = [
  "/",
  "/static/output.css",
  "/static/app.js",
  // "/static/images/favicon.png",
  "/static/icons/icon-192x192.png",
  "/static/icons/icon-512x512.png",
];

// نصب Service Worker و کش کردن فایل‌ها
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(urlsToCache))
      .then(() => self.skipWaiting())
  );
});

// فعال‌سازی و پاک کردن کش قدیمی
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) =>
      Promise.all(
        cacheNames.map((cache) => {
          if (cache !== CACHE_NAME) {
            return caches.delete(cache);
          }
        })
      )
    )
  );
  self.clients.claim();
});

// هندل کردن درخواست‌ها
self.addEventListener("fetch", (event) => {
  const requestUrl = new URL(event.request.url);

  // Cache First برای فایل‌های استاتیک
  if (requestUrl.pathname.startsWith("/static/")) {
    event.respondWith(
      caches
        .match(event.request)
        .then((response) => response || fetch(event.request))
    );
    return;
  }

  // Network First برای بقیه درخواست‌ها (API یا صفحات داینامیک)
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        return response;
      })
      .catch(() => caches.match(event.request) || caches.match("/"))
  );
});

// Optional: پیام log هنگام ثبت SW
self.addEventListener("message", (event) => {
  console.log("SW received message:", event.data);
});
