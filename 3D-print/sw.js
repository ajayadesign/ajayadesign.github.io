/**
 * 3D Print Academy — Service Worker
 * Provides offline access to portal pages and module content.
 * Strategy: Network-first for HTML, cache-first for static assets.
 */
var CACHE_NAME = 'ad3d-v2';
var PRECACHE = [
  '/3D-print/portal/',
  '/3D-print/portal/index.html',
  '/3D-print/portal/portal-auth.js',
  '/3D-print/portal/module-1.html',
  '/3D-print/portal/module-2.html',
  '/3D-print/portal/module-3.html',
  '/3D-print/portal/module-4.html',
  '/3D-print/portal/module-5.html',
  '/3D-print/portal/module-6.html',
  '/3D-print/portal/downloads.html',
  '/3D-print/tools/calculator.html',
  '/3D-print/tools/checklist.html',
  '/3D-print/tools/materials.html',
  '/js/firebase-config.js',
  '/favicon.svg'
];

self.addEventListener('install', function(e) {
  e.waitUntil(
    caches.open(CACHE_NAME).then(function(cache) {
      return cache.addAll(PRECACHE);
    }).then(function() {
      return self.skipWaiting();
    })
  );
});

self.addEventListener('activate', function(e) {
  e.waitUntil(
    caches.keys().then(function(names) {
      return Promise.all(
        names.filter(function(n) { return n !== CACHE_NAME; })
             .map(function(n) { return caches.delete(n); })
      );
    }).then(function() {
      return self.clients.claim();
    })
  );
});

self.addEventListener('fetch', function(e) {
  var url = new URL(e.request.url);

  // Skip non-GET, cross-origin, and Firebase/Stripe/Calendly requests
  if (e.request.method !== 'GET') return;
  if (url.origin !== self.location.origin) return;

  // HTML pages: network-first, fall back to cache
  if (e.request.headers.get('accept') && e.request.headers.get('accept').indexOf('text/html') !== -1) {
    e.respondWith(
      fetch(e.request).then(function(resp) {
        var clone = resp.clone();
        caches.open(CACHE_NAME).then(function(cache) { cache.put(e.request, clone); });
        return resp;
      }).catch(function() {
        return caches.match(e.request).then(function(cached) {
          return cached || new Response('<html><body style="background:#0A0A0F;color:#e5e7eb;font-family:monospace;padding:40px;text-align:center"><h1>Offline</h1><p>Connect to the internet to access the 3D Print Academy.</p></body></html>', {
            headers: { 'Content-Type': 'text/html' }
          });
        });
      })
    );
    return;
  }

  // Static assets: cache-first, fall back to network
  e.respondWith(
    caches.match(e.request).then(function(cached) {
      if (cached) return cached;
      return fetch(e.request).then(function(resp) {
        if (resp.ok) {
          var clone = resp.clone();
          caches.open(CACHE_NAME).then(function(cache) { cache.put(e.request, clone); });
        }
        return resp;
      });
    })
  );
});
