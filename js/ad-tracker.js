/**
 * AjayaDesign — Client-Side Analytics Tracker
 * =============================================
 * Lightweight analytics for Firebase Realtime Database.
 * Tracks: page views, live presence, scroll depth, clicks, performance.
 * All data stored under /site_analytics/ in Firebase RTDB.
 *
 * Usage: include after Firebase SDK init on any page:
 *   <script src="js/ad-tracker.js" defer></script>
 */
;(function () {
  'use strict';

  /* ─── 0. CONFIG ─── */
  var PREFIX = '/site_analytics';
  var CLICK_THROTTLE = 300;
  var SCROLL_DEBOUNCE = 300;
  var BATCH_INTERVAL = 20000; // flush every 20s

  /* ─── 1. UTILITIES ─── */
  function uuid() {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) return crypto.randomUUID();
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
      var r = (Math.random() * 16) | 0;
      return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
    });
  }

  function todayStr() {
    var d = new Date();
    return d.getFullYear() + '-' +
      String(d.getMonth() + 1).padStart(2, '0') + '-' +
      String(d.getDate()).padStart(2, '0');
  }

  function nowISO() { return new Date().toISOString(); }

  function pageSlug(path) {
    return (path || location.pathname)
      .replace(/^\/|\/$/g, '')
      .replace(/\//g, '-')
      .replace(/[.#$\[\]]/g, '-')
      || 'home';
  }

  function debounce(fn, ms) {
    var t;
    return function () {
      var ctx = this, args = arguments;
      clearTimeout(t);
      t = setTimeout(function () { fn.apply(ctx, args); }, ms);
    };
  }

  function throttle(fn, ms) {
    var last = 0;
    return function () {
      var n = Date.now();
      if (n - last >= ms) { last = n; fn.apply(this, arguments); }
    };
  }

  function trunc(s, max) {
    if (!s) return '';
    return s.length > max ? s.substring(0, max) : s;
  }

  function deviceType() {
    var w = window.innerWidth || screen.width;
    if (w < 768) return 'mobile';
    if (w < 1024) return 'tablet';
    return 'desktop';
  }

  function trafficSource() {
    var params = new URLSearchParams(location.search);
    var utm = params.get('utm_source');
    if (utm) return 'campaign';

    var ref = document.referrer;
    if (!ref) return 'direct';

    var host;
    try { host = new URL(ref).hostname; } catch (_) { return 'direct'; }
    if (host === location.hostname) return 'direct';

    var search = /google\.|bing\.|yahoo\.|duckduckgo\.|baidu\.|yandex\./i;
    if (search.test(host)) return 'organic';

    var social = /facebook\.|instagram\.|twitter\.|x\.com|tiktok\.|pinterest\.|linkedin\.|youtube\.|threads\.net|reddit\./i;
    if (social.test(host)) return 'social';

    return 'referral';
  }

  /* ─── 2. STATE ─── */
  var db = null;
  var ready = false;
  var date = todayStr();
  var slug = pageSlug();
  var visitorId, sessionId, sessionStart, pagesViewed;
  var batchQueue = [];
  var scrollFired = {};

  function initVisitor() {
    try { visitorId = localStorage.getItem('ad_vid'); } catch (_) {}
    if (!visitorId) {
      visitorId = uuid();
      try { localStorage.setItem('ad_vid', visitorId); } catch (_) {}
    }
  }

  function initSession() {
    try { sessionId = sessionStorage.getItem('ad_sid'); } catch (_) {}
    if (sessionId) {
      sessionStart = Number(sessionStorage.getItem('ad_sstart')) || Date.now();
      pagesViewed = Number(sessionStorage.getItem('ad_spv')) || 0;
    } else {
      sessionId = uuid();
      sessionStart = Date.now();
      pagesViewed = 0;
      try {
        sessionStorage.setItem('ad_sid', sessionId);
        sessionStorage.setItem('ad_sstart', String(sessionStart));
      } catch (_) {}
    }
    pagesViewed++;
    try { sessionStorage.setItem('ad_spv', String(pagesViewed)); } catch (_) {}
  }

  /* ─── 3. DB HELPERS ─── */
  function ref(path) { return db.ref(PREFIX + path); }

  function enqueue(op) { batchQueue.push(op); }

  function flushBatch() {
    if (!ready || batchQueue.length === 0) return;
    var ops = batchQueue.splice(0);
    var updates = {};
    ops.forEach(function (op) {
      if (op.type === 'increment') {
        ref(op.path).transaction(function (v) { return (v || 0) + 1; });
      } else if (op.type === 'push') {
        var key = db.ref(PREFIX + op.path).push().key;
        updates[PREFIX + op.path + '/' + key] = op.data;
      } else if (op.type === 'set') {
        updates[PREFIX + op.path] = op.data;
      }
    });
    if (Object.keys(updates).length) {
      db.ref().update(updates);
    }
  }

  /* ─── 4. PAGE VIEW ─── */
  function trackPageView() {
    enqueue({
      type: 'push',
      path: '/pageViews/' + date + '/' + slug,
      data: {
        url: location.href,
        path: location.pathname,
        title: document.title,
        referrer: document.referrer || null,
        timestamp: nowISO(),
        sessionId: sessionId,
        visitorId: visitorId,
        device: deviceType(),
        source: trafficSource(),
        screenW: window.innerWidth,
        screenH: window.innerHeight
      }
    });
  }

  /* ─── 5. PRESENCE ─── */
  function setupPresence() {
    if (!ready) return;
    var presRef = ref('/presence/' + visitorId);
    var connRef = db.ref('.info/connected');

    connRef.on('value', function (snap) {
      if (snap.val() === true) {
        presRef.onDisconnect().remove();
        presRef.set({
          page: location.pathname,
          slug: slug,
          device: deviceType(),
          sessionId: sessionId,
          timestamp: firebase.database.ServerValue.TIMESTAMP,
          referrer: document.referrer || null
        });
      }
    });
  }

  /* ─── 6. SCROLL DEPTH ─── */
  function setupScrollTracking() {
    scrollFired = {};
    var thresholds = [25, 50, 75, 100];

    var handler = debounce(function () {
      var scrollTop = window.pageYOffset || document.documentElement.scrollTop;
      var docHeight = Math.max(
        document.body.scrollHeight, document.documentElement.scrollHeight,
        document.body.offsetHeight, document.documentElement.offsetHeight
      );
      var winHeight = window.innerHeight;
      var scrollable = docHeight - winHeight;
      if (scrollable <= 0) return;
      var pct = Math.round((scrollTop / scrollable) * 100);

      thresholds.forEach(function (t) {
        if (pct >= t && !scrollFired[t]) {
          scrollFired[t] = true;
          enqueue({ type: 'increment', path: '/scrollDepth/' + date + '/' + slug + '/' + t });
        }
      });
    }, SCROLL_DEBOUNCE);

    window.addEventListener('scroll', handler, { passive: true });
  }

  /* ─── 7. CLICK TRACKING ─── */
  function setupClickTracking() {
    var handler = throttle(function (e) {
      var target = e.target || {};
      var vw = window.innerWidth || 1;
      var vh = window.innerHeight || 1;
      var scrollY = window.pageYOffset || document.documentElement.scrollTop;
      enqueue({
        type: 'push',
        path: '/clicks/' + date + '/' + slug,
        data: {
          x: Math.round((e.clientX / vw) * 10000) / 100,
          y: Math.round(((e.clientY + scrollY) / document.documentElement.scrollHeight) * 10000) / 100,
          clientY: Math.round((e.clientY / vh) * 10000) / 100,
          tag: (target.tagName || '').toLowerCase(),
          cls: trunc(target.className || '', 80),
          id: target.id || null,
          text: trunc((target.textContent || '').trim(), 40),
          href: target.href || target.closest('a')?.href || null,
          ts: nowISO()
        }
      });
    }, CLICK_THROTTLE);

    document.addEventListener('click', handler, true);
  }

  /* ─── 8. PERFORMANCE ─── */
  function trackPerformance() {
    // Wait for page load to complete
    if (document.readyState !== 'complete') {
      window.addEventListener('load', function () { setTimeout(trackPerformance, 100); });
      return;
    }

    var perf = window.performance;
    if (!perf || !perf.getEntriesByType) return;
    var nav = perf.getEntriesByType('navigation')[0];
    if (!nav) return;

    var paint = perf.getEntriesByType('paint');
    var fcp = 0;
    paint.forEach(function (p) { if (p.name === 'first-contentful-paint') fcp = Math.round(p.startTime); });

    enqueue({
      type: 'push',
      path: '/performance/' + date,
      data: {
        slug: slug,
        device: deviceType(),
        dns: Math.round(nav.domainLookupEnd - nav.domainLookupStart),
        tcp: Math.round(nav.connectEnd - nav.connectStart),
        ttfb: Math.round(nav.responseStart - nav.requestStart),
        domLoad: Math.round(nav.domContentLoadedEventEnd - nav.navigationStart),
        fullLoad: Math.round(nav.loadEventEnd - nav.navigationStart),
        fcp: fcp,
        transferSize: nav.transferSize || 0,
        timestamp: nowISO()
      }
    });
  }

  /* ─── 9. SESSION SUMMARY (on unload) ─── */
  function trackSessionEnd() {
    var duration = Math.round((Date.now() - sessionStart) / 1000);
    var data = {
      visitorId: visitorId,
      sessionId: sessionId,
      device: deviceType(),
      pages: pagesViewed,
      duration: duration,
      source: trafficSource(),
      entryPage: slug,
      timestamp: nowISO()
    };
    // Best-effort write
    if (ready && db) {
      try { db.ref(PREFIX + '/sessions/' + date).push(data); } catch (_) {}
    }
  }

  /* ─── 10. BOOTSTRAP ─── */
  function boot() {
    // Skip on admin pages
    if (location.pathname.indexOf('/admin') === 0) return;

    // Require Firebase
    if (typeof firebase === 'undefined' || !window.__db) {
      // Retry once after a short delay
      setTimeout(function () {
        if (typeof firebase !== 'undefined' && window.__db) {
          db = window.__db;
          ready = true;
          run();
        }
      }, 500);
      return;
    }

    db = window.__db;
    ready = true;
    run();
  }

  function run() {
    initVisitor();
    initSession();
    trackPageView();
    setupPresence();
    setupScrollTracking();
    setupClickTracking();
    trackPerformance();

    // Batch flusher
    setInterval(flushBatch, BATCH_INTERVAL);
    // Immediate first flush after 2s
    setTimeout(flushBatch, 2000);

    // Session end tracking
    window.addEventListener('beforeunload', function () {
      flushBatch();
      trackSessionEnd();
    });

    // Visibility change — flush when tab is hidden
    document.addEventListener('visibilitychange', function () {
      if (document.visibilityState === 'hidden') flushBatch();
    });
  }

  // Start when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }

})();
