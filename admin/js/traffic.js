/**
 * AjayaDesign Admin — Traffic Dashboard
 * ======================================
 * Reads from /site_analytics/ in Firebase RTDB.
 * Renders: live visitors, traffic chart, top pages, traffic sources,
 * scroll depth, click heatmap, performance metrics, sessions.
 */
;(function () {
  'use strict';

  var PREFIX = '/site_analytics';
  var chartInstances = {};

  /* ── Helpers ── */
  function fbRef(path) {
    if (!window.__db) return null;
    return window.__db.ref(PREFIX + path);
  }

  function getToday() {
    var d = new Date();
    return d.getFullYear() + '-' +
      String(d.getMonth() + 1).padStart(2, '0') + '-' +
      String(d.getDate()).padStart(2, '0');
  }

  function getDateOffset(daysAgo) {
    var d = new Date();
    d.setDate(d.getDate() - daysAgo);
    return d.getFullYear() + '-' +
      String(d.getMonth() + 1).padStart(2, '0') + '-' +
      String(d.getDate()).padStart(2, '0');
  }

  function fmt(n) { return n == null ? '—' : Number(n).toLocaleString('en-US'); }

  function fmtDuration(s) {
    if (!s || s < 0) return '0s';
    if (s < 60) return Math.round(s) + 's';
    var m = Math.floor(s / 60), r = Math.round(s % 60);
    return m + 'm ' + r + 's';
  }

  function fmtTimeAgo(ts) {
    if (!ts) return '—';
    var diff = Date.now() - new Date(ts).getTime();
    var m = Math.floor(diff / 60000);
    if (m < 1) return 'Just now';
    if (m < 60) return m + 'm ago';
    var h = Math.floor(m / 60);
    if (h < 24) return h + 'h ago';
    return Math.floor(h / 24) + 'd ago';
  }

  function slugToPath(slug) {
    if (!slug || slug === 'home') return '/';
    return '/' + slug.replace(/-/g, '/') + '/';
  }

  var COLORS = ['#00d4ff', '#ff6b6b', '#51cf66', '#ffd43b', '#cc5de8', '#ff922b', '#20c997', '#a9e34b'];
  function color(i) { return COLORS[i % COLORS.length]; }

  /* ── Chart factory with dark theme defaults ── */
  function makeChart(canvasId, type, data, opts) {
    if (chartInstances[canvasId]) chartInstances[canvasId].destroy();
    var ctx = document.getElementById(canvasId);
    if (!ctx) return null;

    var defaults = {
      responsive: true,
      maintainAspectRatio: true,
      plugins: { legend: { labels: { color: '#9ca3af', font: { family: 'ui-monospace, monospace', size: 11 } } } },
      scales: {}
    };
    if (['line', 'bar'].includes(type)) {
      defaults.scales = {
        x: { ticks: { color: '#6b7280' }, grid: { color: 'rgba(75,85,99,0.25)' } },
        y: { ticks: { color: '#6b7280' }, grid: { color: 'rgba(75,85,99,0.25)' }, beginAtZero: true }
      };
    }
    var merged = Object.assign({}, defaults);
    if (opts) {
      if (opts.plugins) merged.plugins = Object.assign({}, defaults.plugins, opts.plugins);
      if (opts.scales) merged.scales = Object.assign({}, defaults.scales, opts.scales);
      Object.keys(opts).forEach(function (k) {
        if (k !== 'plugins' && k !== 'scales') merged[k] = opts[k];
      });
    }

    chartInstances[canvasId] = new Chart(ctx, { type: type, data: data, options: merged });
    return chartInstances[canvasId];
  }

  /* ═══════════════════════════════════════════════════════════════════════
     DATA FETCHERS
     ═══════════════════════════════════════════════════════════════════════ */

  async function fetchTrafficHistory(days) {
    days = days || 30;
    var results = {};
    var promises = [];
    for (var i = days - 1; i >= 0; i--) {
      (function (d) {
        var r = fbRef('/pageViews/' + d);
        if (!r) return;
        promises.push(
          r.once('value').then(function (snap) {
            var data = snap.val();
            var count = 0;
            if (data) Object.values(data).forEach(function (pg) {
              if (typeof pg === 'object') count += Object.keys(pg).length;
            });
            results[d] = count;
          })
        );
      })(getDateOffset(i));
    }
    await Promise.all(promises);
    return results;
  }

  async function fetchTodayData() {
    var today = getToday();
    var r = fbRef('/pageViews/' + today);
    if (!r) return { total: 0, sessions: new Set(), pages: {}, sources: {}, referrers: {} };
    var snap = await r.once('value');
    var data = snap.val();
    // Fall back to yesterday if today has no data (timezone edge)
    if (!data) {
      var r2 = fbRef('/pageViews/' + getDateOffset(1));
      if (r2) { snap = await r2.once('value'); data = snap.val(); }
    }
    if (!data) return { total: 0, sessions: new Set(), pages: {}, sources: {}, referrers: {} };

    var sessions = new Set(), total = 0, pages = {}, sources = {}, referrers = {};
    Object.entries(data).forEach(function (entry) {
      var slug = entry[0], pageData = entry[1];
      if (typeof pageData === 'object') {
        var count = Object.keys(pageData).length;
        total += count;
        pages[slug] = (pages[slug] || 0) + count;
        Object.values(pageData).forEach(function (pv) {
          if (pv.sessionId) sessions.add(pv.sessionId);
          var src = pv.source || 'direct';
          sources[src] = (sources[src] || 0) + 1;
          var ref = pv.referrer || 'Direct';
          var host = 'Direct';
          if (ref !== 'Direct' && ref) {
            try { host = new URL(ref).hostname; } catch (_) { host = ref; }
          }
          referrers[host] = (referrers[host] || 0) + 1;
        });
      }
    });
    return { total: total, sessions: sessions, pages: pages, sources: sources, referrers: referrers };
  }

  async function fetchScrollDepth() {
    // Try today first, fall back to yesterday (timezone edge)
    var r = fbRef('/scrollDepth/' + getToday());
    if (!r) return {};
    var snap = await r.once('value');
    var data = snap.val();
    if (!data) {
      var r2 = fbRef('/scrollDepth/' + getDateOffset(1));
      if (r2) { snap = await r2.once('value'); data = snap.val(); }
    }
    return data || {};
  }

  async function fetchClicks(pageSlug) {
    var r = fbRef('/clicks/' + getToday() + '/' + pageSlug);
    if (!r) return [];
    var snap = await r.once('value');
    var data = snap.val();
    if (!data) {
      // Try yesterday (timezone edge)
      var r2 = fbRef('/clicks/' + getDateOffset(1) + '/' + pageSlug);
      if (r2) { snap = await r2.once('value'); data = snap.val(); }
    }
    if (!data) return [];
    return Object.values(data);
  }

  async function fetchPerformance() {
    var results = [];
    // Try today + yesterday to handle timezone edge cases
    for (var d = 0; d <= 1; d++) {
      var r = fbRef('/performance/' + getDateOffset(d));
      if (!r) continue;
      var snap = await r.once('value');
      var data = snap.val();
      if (data) results = results.concat(Object.values(data));
      if (results.length > 0 && d === 0) break;  // today has data, skip yesterday
    }
    return results;
  }

  async function fetchSessions() {
    var results = [];
    // Try today + yesterday to handle timezone edge cases
    for (var d = 0; d <= 1; d++) {
      var r = fbRef('/sessions/' + getDateOffset(d));
      if (!r) continue;
      var snap = await r.once('value');
      var data = snap.val();
      if (data) results = results.concat(Object.values(data));
      if (results.length > 0 && d === 0) break;
    }
    return results;
  }

  /* ═══════════════════════════════════════════════════════════════════════
     RENDERERS
     ═══════════════════════════════════════════════════════════════════════ */

  /* ── Live Visitors (real-time) ── */
  var presenceUnsub = null;

  function subscribeLiveVisitors() {
    if (presenceUnsub) return; // already subscribed
    var presRef = fbRef('/presence/');
    if (!presRef) return;

    presenceUnsub = presRef.on('value', function (snap) {
      var data = snap.val() || {};
      var entries = Object.entries(data);

      // Update KPI in sidebar + main panel
      var el = document.getElementById('traffic-kpi-live');
      if (el) el.textContent = entries.length;
      var el2 = document.getElementById('traffic-live-count');
      if (el2) el2.textContent = entries.length;

      // Update table
      var container = document.getElementById('traffic-live-table');
      if (!container) return;

      if (entries.length === 0) {
        container.innerHTML = '<p class="text-gray-500 text-xs font-mono text-center py-6">No visitors currently online</p>';
        return;
      }

      var html = '<div class="space-y-1">';
      entries.forEach(function (e) {
        var vid = e[0], info = e[1];
        var timeOn = info.timestamp ? fmtDuration((Date.now() - info.timestamp) / 1000) : '—';
        html += '<div class="flex items-center gap-2 py-1.5 px-2 bg-surface rounded-lg text-xs font-mono min-w-0">';
        html += '<span class="text-electric truncate w-16 shrink-0">' + vid.substring(0, 8) + '…</span>';
        html += '<span class="text-gray-400 truncate flex-1">' + (info.page || '/') + '</span>';
        html += '<span class="text-gray-500 hidden sm:block w-14 shrink-0">' + (info.device || '—') + '</span>';
        html += '<span class="text-gray-500 w-14 shrink-0 text-right">' + timeOn + '</span>';
        html += '</div>';
      });
      html += '</div>';
      container.innerHTML = html;
    }, function (err) {
      console.error('[Traffic] Presence listener error:', err.message);
      // Reset so we can retry
      presenceUnsub = null;
    });
  }

  /* ── KPI Cards ── */
  async function renderKPIs() {
    try {
      var today = await fetchTodayData();
      var el;
      el = document.getElementById('traffic-kpi-visitors');
      if (el) el.textContent = fmt(today.sessions.size);
      el = document.getElementById('traffic-kpi-pageviews');
      if (el) el.textContent = fmt(today.total);
      el = document.getElementById('traffic-kpi-pages');
      if (el) el.textContent = fmt(Object.keys(today.pages).length);
    } catch (_) {}

    // Sessions
    try {
      var sess = await fetchSessions();
      var el2 = document.getElementById('traffic-kpi-sessions');
      if (el2) el2.textContent = fmt(sess.length);
      // Avg duration
      if (sess.length > 0) {
        var avgDur = sess.reduce(function (a, s) { return a + (s.duration || 0); }, 0) / sess.length;
        var el3 = document.getElementById('traffic-kpi-avg-duration');
        if (el3) el3.textContent = fmtDuration(avgDur);
      }
    } catch (_) {}
  }

  /* ── Traffic Chart (30-day) ── */
  async function renderTrafficChart() {
    try {
      var history = await fetchTrafficHistory(30);
      var labels = Object.keys(history).map(function (d) {
        var p = d.split('-');
        return p[1] + '/' + p[2];
      });
      var values = Object.values(history);

      makeChart('traffic-chart-overview', 'line', {
        labels: labels,
        datasets: [{
          label: 'Pageviews',
          data: values,
          borderColor: '#00d4ff',
          backgroundColor: 'rgba(0,212,255,0.08)',
          fill: true,
          tension: 0.4,
          pointRadius: 2,
          pointBackgroundColor: '#00d4ff',
          borderWidth: 2
        }]
      }, { plugins: { legend: { display: false } } });
    } catch (err) { console.warn('Traffic chart error:', err); }
  }

  /* ── Top Pages ── */
  async function renderTopPages() {
    var container = document.getElementById('traffic-top-pages');
    if (!container) return;
    try {
      var today = await fetchTodayData();
      var sorted = Object.entries(today.pages).sort(function (a, b) { return b[1] - a[1]; }).slice(0, 8);
      if (sorted.length === 0) {
        container.innerHTML = '<p class="text-gray-500 text-xs font-mono py-4">No page views yet today</p>';
        return;
      }
      var max = sorted[0][1];
      var html = '';
      sorted.forEach(function (entry, i) {
        var pct = Math.round((entry[1] / max) * 100);
        html += '<div class="flex items-center gap-2 mb-1.5">';
        html += '<span class="text-xs font-mono text-gray-400 w-32 truncate">' + slugToPath(entry[0]) + '</span>';
        html += '<div class="flex-1 h-4 bg-surface rounded-full overflow-hidden">';
        html += '<div class="h-full rounded-full" style="width:' + pct + '%;background:' + color(i) + ';opacity:0.7;"></div>';
        html += '</div>';
        html += '<span class="text-xs font-mono text-white w-8 text-right">' + entry[1] + '</span>';
        html += '</div>';
      });
      container.innerHTML = html;
    } catch (err) { console.error('[Traffic] Top pages error:', err); container.innerHTML = '<p class="text-gray-500 text-xs font-mono">No page data yet</p>'; }
  }

  /* ── Traffic Sources (pie) ── */
  async function renderTrafficSources() {
    try {
      var today = await fetchTodayData();
      var src = today.sources;
      var labels = Object.keys(src);
      var values = Object.values(src);
      if (labels.length === 0) return;

      makeChart('traffic-chart-sources', 'doughnut', {
        labels: labels.map(function (l) { return l.charAt(0).toUpperCase() + l.slice(1); }),
        datasets: [{
          data: values,
          backgroundColor: labels.map(function (_, i) { return color(i); }),
          borderWidth: 0
        }]
      }, {
        plugins: { legend: { position: 'bottom' } },
        cutout: '60%'
      });
    } catch (_) {}
  }

  /* ── Top Referrers ── */
  async function renderReferrers() {
    var container = document.getElementById('traffic-top-referrers');
    if (!container) return;
    try {
      var today = await fetchTodayData();
      var sorted = Object.entries(today.referrers).sort(function (a, b) { return b[1] - a[1]; }).slice(0, 5);
      if (sorted.length === 0) {
        container.innerHTML = '<p class="text-gray-500 text-xs font-mono py-2">No referrers yet</p>';
        return;
      }
      var html = '<div class="space-y-1">';
      sorted.forEach(function (entry) {
        html += '<div class="flex items-center justify-between text-xs font-mono py-1">';
        html += '<span class="text-gray-300 truncate max-w-[70%]">' + entry[0] + '</span>';
        html += '<span class="text-electric">' + entry[1] + '</span>';
        html += '</div>';
      });
      html += '</div>';
      container.innerHTML = html;
    } catch (_) {}
  }

  /* ── Scroll Depth ── */
  async function renderScrollDepth() {
    try {
      var data = await fetchScrollDepth();
      // Aggregate across all pages
      var totals = { 25: 0, 50: 0, 75: 0, 100: 0 };
      Object.values(data).forEach(function (page) {
        if (typeof page === 'object') {
          [25, 50, 75, 100].forEach(function (t) {
            totals[t] += (page[t] || 0);
          });
        }
      });

      makeChart('traffic-chart-scroll', 'bar', {
        labels: ['25%', '50%', '75%', '100%'],
        datasets: [{
          label: 'Visitors reaching depth',
          data: [totals[25], totals[50], totals[75], totals[100]],
          backgroundColor: ['rgba(0,212,255,0.6)', 'rgba(81,207,102,0.6)', 'rgba(255,212,59,0.6)', 'rgba(255,107,107,0.6)'],
          borderRadius: 6
        }]
      }, { plugins: { legend: { display: false } } });
    } catch (_) {}
  }

  /* ── Click Heatmap ── */
  async function renderClickHeatmap() {
    var select = document.getElementById('traffic-heatmap-page');
    var container = document.getElementById('traffic-chart-clicks');
    if (!select || !container) return;

    // Populate page selector from today + yesterday clicks
    try {
      var allPages = {};
      for (var d = 0; d <= 1; d++) {
        var cr = fbRef('/clicks/' + getDateOffset(d));
        if (!cr) continue;
        var snap = await cr.once('value');
        var dd = snap.val();
        if (dd) Object.keys(dd).forEach(function (p) { allPages[p] = true; });
      }
      var pages = Object.keys(allPages);

      select.innerHTML = '<option value="">Select page…</option>';
      pages.forEach(function (p) {
        var opt = document.createElement('option');
        opt.value = p;
        opt.textContent = slugToPath(p);
        select.appendChild(opt);
      });
    } catch (_) {}
  }

  async function loadHeatmapForPage() {
    var select = document.getElementById('traffic-heatmap-page');
    var canvas = document.getElementById('traffic-chart-clicks');
    if (!select || !canvas) return;
    var page = select.value;
    if (!page) return;

    try {
      var clicks = await fetchClicks(page);
      if (clicks.length === 0) return;

      // Scatter chart: x% vs y%
      var points = clicks.map(function (c) {
        return { x: c.x || 0, y: c.clientY || c.y || 0 };
      });

      makeChart('traffic-chart-clicks', 'scatter', {
        datasets: [{
          label: 'Clicks on ' + slugToPath(page),
          data: points,
          backgroundColor: 'rgba(255,107,107,0.5)',
          pointRadius: 4,
          pointHoverRadius: 6
        }]
      }, {
        scales: {
          x: { min: 0, max: 100, title: { display: true, text: 'X position (%)', color: '#6b7280' } },
          y: { min: 0, max: 100, reverse: true, title: { display: true, text: 'Y position (%)', color: '#6b7280' } }
        },
        plugins: { legend: { display: false } }
      });
    } catch (_) {}
  }
  window.loadTrafficHeatmap = loadHeatmapForPage;

  /* ── Performance Metrics ── */
  async function renderPerformance() {
    var container = document.getElementById('traffic-perf-grid');
    if (!container) return;
    try {
      var entries = await fetchPerformance();
      if (entries.length === 0) {
        container.innerHTML = '<p class="text-gray-500 text-xs font-mono text-center py-6 col-span-full">No performance data yet today</p>';
        return;
      }
      // Average metrics
      var sum = { ttfb: 0, fcp: 0, domLoad: 0, fullLoad: 0 };
      entries.forEach(function (e) {
        sum.ttfb += (e.ttfb || 0);
        sum.fcp += (e.fcp || 0);
        sum.domLoad += (e.domLoad || 0);
        sum.fullLoad += (e.fullLoad || 0);
      });
      var n = entries.length;
      var metrics = [
        { label: 'TTFB', value: Math.round(sum.ttfb / n) + 'ms', good: sum.ttfb / n < 800 },
        { label: 'FCP', value: Math.round(sum.fcp / n) + 'ms', good: sum.fcp / n < 1800 },
        { label: 'DOM Load', value: Math.round(sum.domLoad / n) + 'ms', good: sum.domLoad / n < 3000 },
        { label: 'Full Load', value: Math.round(sum.fullLoad / n) + 'ms', good: sum.fullLoad / n < 5000 },
        { label: 'Samples', value: fmt(n), good: true }
      ];

      var html = '';
      metrics.forEach(function (m) {
        var dotColor = m.good ? 'bg-green-400' : 'bg-yellow-400';
        html += '<div class="bg-surface rounded-xl border border-border p-3 text-center">';
        html += '<div class="flex items-center justify-center gap-1.5 mb-1">';
        html += '<span class="w-2 h-2 rounded-full ' + dotColor + '"></span>';
        html += '<span class="font-mono text-[0.65rem] text-gray-500 uppercase">' + m.label + '</span>';
        html += '</div>';
        html += '<div class="font-mono text-lg font-bold text-white">' + m.value + '</div>';
        html += '</div>';
      });
      container.innerHTML = html;
    } catch (_) {
      container.innerHTML = '<p class="text-gray-500 text-xs font-mono text-center py-6 col-span-full">No performance data yet</p>';
    }
  }

  /* ── Sessions Table ── */
  async function renderSessions() {
    var container = document.getElementById('traffic-sessions-list');
    if (!container) return;
    try {
      var sessions = await fetchSessions();
      if (sessions.length === 0) {
        container.innerHTML = '<p class="text-gray-500 text-xs font-mono text-center py-6">No sessions recorded today</p>';
        return;
      }
      // Sort by duration desc
      sessions.sort(function (a, b) { return (b.duration || 0) - (a.duration || 0); });
      var html = '<div class="space-y-1">';
      sessions.slice(0, 20).forEach(function (s) {
        html += '<div class="flex items-center gap-2 py-1.5 px-2 bg-surface rounded-lg text-xs font-mono min-w-0">';
        html += '<span class="text-electric truncate w-16 shrink-0">' + (s.visitorId || '').substring(0, 8) + '…</span>';
        html += '<span class="text-gray-400 w-14 shrink-0 hidden sm:block">' + (s.device || '—') + '</span>';
        html += '<span class="text-gray-400 w-10 shrink-0">' + (s.pages || 0) + ' pg</span>';
        html += '<span class="text-white w-14 shrink-0">' + fmtDuration(s.duration || 0) + '</span>';
        html += '<span class="text-gray-500 w-14 shrink-0 hidden sm:block">' + (s.source || 'direct') + '</span>';
        html += '<span class="text-gray-500 flex-1 text-right">' + fmtTimeAgo(s.timestamp) + '</span>';
        html += '</div>';
      });
      html += '</div>';
      container.innerHTML = html;
    } catch (err) {
      console.error('[Traffic] Sessions error:', err);
      container.innerHTML = '<p class="text-gray-500 text-xs font-mono text-center py-6">No session data yet</p>';
    }
  }

  /* ── Device Breakdown ── */
  async function renderDeviceBreakdown() {
    try {
      var sess = await fetchSessions();
      var devices = {};
      sess.forEach(function (s) {
        var d = s.device || 'unknown';
        devices[d] = (devices[d] || 0) + 1;
      });
      var labels = Object.keys(devices);
      var values = Object.values(devices);
      if (labels.length === 0) return;

      makeChart('traffic-chart-devices', 'doughnut', {
        labels: labels.map(function (l) { return l.charAt(0).toUpperCase() + l.slice(1); }),
        datasets: [{
          data: values,
          backgroundColor: labels.map(function (_, i) { return color(i); }),
          borderWidth: 0
        }]
      }, {
        plugins: { legend: { position: 'bottom' } },
        cutout: '60%'
      });
    } catch (_) {}
  }

  /* ═══════════════════════════════════════════════════════════════════════
     PUBLIC: refreshTraffic() — called by switchTab('traffic')
     ═══════════════════════════════════════════════════════════════════════ */
  window.refreshTraffic = async function () {
    subscribeLiveVisitors();
    await Promise.allSettled([
      renderKPIs(),
      renderTrafficChart(),
      renderTopPages(),
      renderTrafficSources(),
      renderReferrers(),
      renderScrollDepth(),
      renderClickHeatmap(),
      renderPerformance(),
      renderSessions(),
      renderDeviceBreakdown()
    ]);
  };

  /* ── scrollTraffic – sidebar "Jump to" helper ── */
  window.scrollTraffic = function (id) {
    var el = document.getElementById(id);
    var container = document.getElementById('traffic-scroll');
    if (el && container) {
      var offset = el.offsetTop - container.offsetTop;
      container.scrollTo({ top: offset, behavior: 'smooth' });
    }
    // Close sidebar on mobile
    if (window.innerWidth < 768) {
      var sb = document.getElementById('sidebar');
      if (sb && sb.classList.contains('translate-x-0')) {
        if (typeof toggleMobileSidebar === 'function') toggleMobileSidebar();
      }
    }
  };

})();
