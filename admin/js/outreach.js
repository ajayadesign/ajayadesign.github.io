/* ═══════════════════════════════════════════════════════
   AjayaDesign Admin — Outreach Agent Tab
   Dual-mode: Full (localhost API) / Light (Firebase-only)
   "Command Center Anywhere" — war room in your pocket
   ═══════════════════════════════════════════════════════ */

(function () {
  'use strict';

  // ── Constants ────────────────────────────────────────
  const API_BASE = 'http://localhost:3001/api/v1';
  const MODE_CHECK_INTERVAL = 30000; // 30s

  // ── State ────────────────────────────────────────────
  let _mode = 'light';
  let _apiAvailable = false;
  let _modeCheckTimer = null;
  let _listeners = {};
  let _initialized = false;
  let _agentStatus = 'unknown';

  // ── Live data buffers (real Firebase data for MC ticker/terminal) ──
  let _liveActivityItems = [];   // last N activity items from outreach/activity
  let _liveLogItems = [];        // last N log items from outreach/log
  let _liveRingData = {};        // current ring data from outreach/rings
  let _liveProspectCities = [];  // real cities from outreach/hot prospects

  // ── Firebase DB ref ──────────────────────────────────
  function _db() {
    return window.__db || null;
  }

  // ── Mode Detection ───────────────────────────────────
  async function detectMode() {
    try {
      const ctrl = new AbortController();
      const timer = setTimeout(() => ctrl.abort(), 3000);
      const res = await fetch(`${API_BASE}/health`, { signal: ctrl.signal });
      clearTimeout(timer);
      if (res.ok) {
        _apiAvailable = true;
        if (_mode !== 'full') {
          _mode = 'full';
          _showBanner('🟢 Local API connected — full dashboard', 'success');
          // Detach Firebase data listeners to stop them overriding local data
          _detachDataListeners();
          _initFullMode();
        }
      }
    } catch {
      _apiAvailable = false;
      if (_mode !== 'light') {
        _mode = 'light';
        _showBanner('☁️ Remote mode — live command center. Use Telegram for direct control.', 'info');
        _teardownFullMode();
        // Re-attach Firebase data listeners for fallback
        _initFirebaseListeners();
      }
    }
  }

  // Detach only Firebase data listeners (keep agent status)
  function _detachDataListeners() {
    const db = _db();
    if (!db) return;
    const dataKeys = ['stats', 'rings', 'activity', 'log', 'alerts', 'funnel', 'hot', 'tplStats', 'industries'];
    for (const key of dataKeys) {
      if (_listeners[key]) {
        try { db.ref(`outreach/${key === 'tplStats' ? 'tpl_stats' : key}`).off(); } catch (e) { /* ignore */ }
        delete _listeners[key];
      }
    }
  }

  function _showBanner(text, type) {
    const $banner = document.getElementById('outreach-mode-banner');
    if (!$banner) return;
    $banner.textContent = text;
    $banner.className = 'px-4 py-2 text-xs font-mono rounded-lg mb-4 ' +
      (type === 'success'
        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
        : 'bg-blue-500/10 text-blue-400 border border-blue-500/20');
    $banner.classList.remove('hidden');
  }

  // ── Firebase Listeners (fallback when API unavailable) ──
  function _initFirebaseListeners() {
    const db = _db();
    if (!db) return;

    // 1. Agent status (always from Firebase — it's the canonical source)
    _listeners.agent = db.ref('outreach/agent').on('value', snap => {
      const data = snap.val() || {};
      _agentStatus = data.status || 'unknown';
      _renderAgentStatus(data);
    });

    // In FULL mode (local API available), skip all Firebase data rendering
    // to prevent stale Firebase data from overriding live localhost data.
    if (_apiAvailable) return;

    // 2. KPI stats — only use Firebase if API is NOT available
    _listeners.stats = db.ref('outreach/stats').on('value', snap => {
      if (_apiAvailable) return; // Guard: API came online since listener was set
      const stats = snap.val() || {};
      _renderKPIs(stats);
      _mcOnStats(stats);
    });

    // 3. Ring progress
    _listeners.rings = db.ref('outreach/rings').on('value', snap => {
      const data = snap.val() || {};
      _renderRingProgress(data);
      _liveRingData = data;
    });

    // 4. Activity feed (last 50)
    _listeners.activity = db.ref('outreach/activity')
      .orderByChild('ts').limitToLast(50)
      .on('value', snap => {
        const raw = snap.val() || {};
        _renderActivityFeed(raw);
        // Populate live buffer for MC ticker/terminal
        _liveActivityItems = Object.values(raw).sort((a, b) => (b.ts || 0) - (a.ts || 0)).slice(0, 30);
      });

    // 5. Agent log (last 200)
    _listeners.log = db.ref('outreach/log')
      .orderByChild('ts').limitToLast(200)
      .on('value', snap => {
        const raw = snap.val() || {};
        _renderAgentLog(raw);
        // Populate live buffer for MC terminal
        _liveLogItems = Object.values(raw).sort((a, b) => (b.ts || 0) - (a.ts || 0)).slice(0, 50);
      });

    // 6. Alerts — real-time badge + feed
    _listeners.alerts = db.ref('outreach/alerts')
      .orderByChild('ts').limitToLast(20)
      .on('value', snap => {
        const alerts = snap.val() || {};
        _renderAlerts(alerts);
      });

    // 7. Pipeline funnel
    _listeners.funnel = db.ref('outreach/funnel').on('value', snap => {
      _renderFunnel(snap.val() || {});
    });

    // 8. Hot prospects
    _listeners.hot = db.ref('outreach/hot').on('value', snap => {
      _renderHotProspects(snap.val() || {});
    });

    // 9. Template leaderboard
    _listeners.tplStats = db.ref('outreach/tpl_stats').on('value', snap => {
      _renderTemplateLeaderboard(snap.val() || {});
    });

    // 10. Industry breakdown
    _listeners.industries = db.ref('outreach/industries').on('value', snap => {
      _renderIndustryBreakdown(snap.val() || {});
    });

    // ── One-shot loads (.once) — infrequently updated nodes ──

    // 11. 90-day sparklines
    db.ref('outreach/snapshots').orderByKey().limitToLast(90)
      .once('value', snap => {
        _renderSparklines(snap.val() || {});
      });

    // 12. Weekly scorecard
    db.ref('outreach/scorecard').orderByKey().limitToLast(12)
      .once('value', snap => {
        _renderWeeklyScorecard(snap.val() || {});
      });

    // 13. Send-time heatmap
    db.ref('outreach/heatmap').once('value', snap => {
      _renderSendTimeHeatmap(snap.val() || {});
    });

    // 14. Agent health timeline (72h)
    db.ref('outreach/health').orderByChild('ts').limitToLast(72)
      .once('value', snap => {
        _renderHealthTimeline(snap.val() || {});
      });
  }

  function _detachListeners() {
    const db = _db();
    if (!db) return;
    for (const [key, _] of Object.entries(_listeners)) {
      try {
        db.ref(`outreach/${key === 'tplStats' ? 'tpl_stats' : key}`).off();
      } catch (e) { /* ignore */ }
    }
    _listeners = {};
  }

  // ── Full Mode (API available) ────────────────────────
  let _liveRefreshTimer = null;
  let _lastStats = null;

  async function _liveRefreshFromAPI() {
    // Lightweight poll: stats + table count + pending emails + tracking — all from localhost
    const stats = await _api('GET', '/outreach/stats');
    if (stats) {
      _lastStats = stats;
      _renderKPIs(stats);
      _mcOnStats(stats);
    }
    // Refresh table to pick up new prospects / status changes
    await _loadProspectsTable();
    // Refresh pending emails count
    await _loadPendingEmails();
    // Refresh email tracking stats
    await _loadEmailTrackingStats();
  }

  function _initFullMode() {
    document.querySelectorAll('.outreach-full-only').forEach(el => el.style.display = '');
    const $light = document.getElementById('outreach-light-panel');
    if ($light) $light.style.display = 'none';
    _loadBusinessTypes();
    // Set initial sort arrow indicator
    const arrow = document.getElementById('sort-arrow-' + _sortCol);
    if (arrow) arrow.textContent = _sortOrder === 'asc' ? ' ▲' : ' ▼';
    // Do one immediate full refresh (stats + table + emails) from localhost API
    _liveRefreshFromAPI();
    // Auto-refresh every 12s from localhost API — real-time feel, zero Firebase bandwidth
    if (_liveRefreshTimer) clearInterval(_liveRefreshTimer);
    _liveRefreshTimer = setInterval(_liveRefreshFromAPI, 12000);
  }

  function _teardownFullMode() {
    document.querySelectorAll('.outreach-full-only').forEach(el => el.style.display = 'none');
    const $light = document.getElementById('outreach-light-panel');
    if ($light) $light.style.display = '';
    if (_liveRefreshTimer) { clearInterval(_liveRefreshTimer); _liveRefreshTimer = null; }
  }

  // ── API helpers ──────────────────────────────────────
  async function _api(method, path, body) {
    try {
      const opts = { method, headers: { 'Content-Type': 'application/json' } };
      if (body) opts.body = JSON.stringify(body);
      const res = await fetch(`${API_BASE}${path}`, opts);
      if (!res.ok) return null;
      return await res.json();
    } catch {
      return null;
    }
  }

  // ── Agent Controls ───────────────────────────────────
  function _pushFirebaseStatus(status, task) {
    const db = _db();
    if (!db) return;
    db.ref('outreach/agent').set({
      status: status,
      current_ring: task || '',
      uptime: 0,
      last_heartbeat: Math.floor(Date.now() / 1000),
    });
    db.ref('outreach/activity').push({
      type: 'system',
      name: `Agent ${status}`,
      detail: '',
      ts: Math.floor(Date.now() / 1000),
    });
  }

  window.outreachAgentStart = async function () {
    // Optimistic UI update immediately
    _agentStatus = 'running';
    _renderAgentStatus({ status: 'running' });
    _startMissionControlEffects();

    if (_apiAvailable) {
      const res = await _api('POST', '/outreach/agent/start');
      if (!res) {
        _agentStatus = 'error';
        _renderAgentStatus({ status: 'error' });
      }
    } else {
      // Light mode — push directly to Firebase
      _pushFirebaseStatus('running');
    }
  };

  window.outreachAgentPause = async function () {
    _agentStatus = 'paused';
    _renderAgentStatus({ status: 'paused' });
    _stopMissionControlEffects();

    if (_apiAvailable) {
      await _api('POST', '/outreach/agent/pause');
    } else {
      _pushFirebaseStatus('paused');
    }
  };

  window.outreachAgentKill = async function () {
    if (!confirm('Are you sure? This will emergency-stop the outreach agent.')) return;
    _agentStatus = 'idle';
    _renderAgentStatus({ status: 'idle' });
    _stopMissionControlEffects();

    if (_apiAvailable) {
      await _api('POST', '/outreach/agent/kill');
    } else {
      _pushFirebaseStatus('idle');
    }
  };

  // ── Prospect List (Full Mode) — Paginated + Filtered ──
  let _prospectPage = 0;
  let _prospectTotal = 0;
  let _noWebsiteFilter = false;
  let _selectedProspects = new Set(); // Track selected prospect IDs
  let _sortCol = 'priority_score';
  let _sortOrder = 'desc';

  async function _loadBusinessTypes() {
    const types = await _api('GET', '/outreach/prospects/types');
    const $sel = document.getElementById('outreach-filter-type');
    if (!$sel || !Array.isArray(types)) return;
    $sel.innerHTML = '<option value="">All Types</option>' +
      types.map(t => `<option value="${_esc(t.type)}">${_esc(t.type.replace(/_/g, ' '))} (${t.count})</option>`).join('');
  }

  async function _loadProspectsTable(resetPage) {
    if (resetPage) _prospectPage = 0;
    const pageSize = parseInt(document.getElementById('outreach-page-size')?.value || '25', 10);
    const status = document.getElementById('outreach-filter-status')?.value || '';
    const search = document.getElementById('outreach-search')?.value || '';
    const bizType = document.getElementById('outreach-filter-type')?.value || '';

    const params = new URLSearchParams({ brief: 'true', limit: String(pageSize), offset: String(_prospectPage * pageSize), sort: _sortCol, order: _sortOrder });
    if (status) params.set('status', status);
    if (search) params.set('search', search);
    if (bizType) params.set('business_type', bizType);
    if (_noWebsiteFilter) params.set('has_website', 'false');

    const resp = await _api('GET', `/outreach/prospects?${params}`);
    const $table = document.getElementById('outreach-prospects-tbody');
    if (!$table || !resp) return;

    const rows = resp.prospects || resp;
    const list = Array.isArray(rows) ? rows : [];
    _prospectTotal = resp.total ?? list.length;

    // Update count badge
    const $count = document.getElementById('outreach-prospects-count');
    if ($count) $count.textContent = `(${_prospectTotal})`;

    if (list.length === 0) {
      $table.innerHTML = '<tr><td colspan="9" class="text-center text-gray-500 py-8 font-mono text-sm">No prospects match your filters.</td></tr>';
    } else {
      $table.innerHTML = list.map(p => `
        <tr class="border-b border-gray-800/50 hover:bg-gray-800/30 cursor-pointer transition ${_selectedProspects.has(p.id) ? 'bg-electric/5' : ''}">
          <td class="px-2 py-2 w-8" onclick="event.stopPropagation()"><input type="checkbox" class="accent-electric cursor-pointer outreach-row-cb" data-id="${p.id}" ${_selectedProspects.has(p.id) ? 'checked' : ''} onchange="outreachToggleRow(this)" /></td>
          <td class="px-3 py-2 font-mono text-sm text-gray-200 truncate max-w-[200px]" onclick="outreachViewProspect('${p.id}')">${_esc(p.business_name || '—')}</td>
          <td class="px-3 py-2 text-xs text-gray-400" onclick="outreachViewProspect('${p.id}')">${_esc((p.business_type || '—').replace(/_/g, ' '))}</td>
          <td class="px-3 py-2 text-xs" onclick="outreachViewProspect('${p.id}')">${_statusBadge(p.status)}</td>
          <td class="px-3 py-2 text-center font-mono text-sm ${_scoreColor(p.priority_score)}" onclick="outreachViewProspect('${p.id}')">${p.priority_score ?? '—'}</td>
          <td class="px-3 py-2 text-center text-sm" onclick="outreachViewProspect('${p.id}')">${p.has_website ? '<span class="text-emerald-400" title="Has website">✓</span>' : '<span class="text-red-400 font-bold" title="NO website — hot prospect!">✗</span>'}</td>
          <td class="px-3 py-2 text-xs text-gray-400" onclick="outreachViewProspect('${p.id}')">${p.city || '—'}</td>
          <td class="px-3 py-2 text-xs text-gray-400" onclick="outreachViewProspect('${p.id}')">${p.google_rating ? `⭐ ${p.google_rating} <span class="text-gray-600">(${p.google_reviews || 0})</span>` : '—'}</td>
          <td class="px-3 py-2 text-xs text-gray-500" onclick="outreachViewProspect('${p.id}')">${_timeAgo(p.created_at)}</td>
        </tr>
      `).join('');
    }

    // Sync "select all" checkbox state
    const $all = document.getElementById('outreach-select-all');
    if ($all) $all.checked = list.length > 0 && list.every(p => _selectedProspects.has(p.id));

    // Update pagination controls
    const maxPage = Math.max(0, Math.ceil(_prospectTotal / pageSize) - 1);
    const $prev = document.getElementById('outreach-prev-page');
    const $next = document.getElementById('outreach-next-page');
    const $info = document.getElementById('outreach-page-info');
    if ($prev) $prev.disabled = _prospectPage <= 0;
    if ($next) $next.disabled = _prospectPage >= maxPage;
    if ($info) {
      const from = _prospectTotal === 0 ? 0 : _prospectPage * pageSize + 1;
      const to = Math.min((_prospectPage + 1) * pageSize, _prospectTotal);
      $info.textContent = `${from}–${to} of ${_prospectTotal}`;
    }
  }

  window.outreachSort = function (col) {
    if (_sortCol === col) {
      _sortOrder = _sortOrder === 'desc' ? 'asc' : 'desc';
    } else {
      _sortCol = col;
      _sortOrder = 'desc';
    }
    // Update sort arrow indicators
    document.querySelectorAll('[id^="sort-arrow-"]').forEach(el => el.textContent = '');
    const arrow = document.getElementById('sort-arrow-' + col);
    if (arrow) arrow.textContent = _sortOrder === 'asc' ? ' ▲' : ' ▼';
    _loadProspectsTable(true);
  };
  window.outreachSearchProspects = function () { _loadProspectsTable(true); };
  window.outreachPrevPage = function () { if (_prospectPage > 0) { _prospectPage--; _loadProspectsTable(); } };
  window.outreachNextPage = function () { _prospectPage++; _loadProspectsTable(); };
  window.outreachToggleNoWebsite = function () {
    _noWebsiteFilter = !_noWebsiteFilter;
    const $btn = document.getElementById('outreach-filter-nosite');
    if ($btn) {
      $btn.classList.toggle('border-red-500/60', _noWebsiteFilter);
      $btn.classList.toggle('text-red-400', _noWebsiteFilter);
      $btn.classList.toggle('bg-red-500/10', _noWebsiteFilter);
      $btn.classList.toggle('text-gray-400', !_noWebsiteFilter);
      $btn.classList.toggle('bg-surface-2', !_noWebsiteFilter);
    }
    _loadProspectsTable(true);
  };

  // ── Bulk Selection ──────────────────────────────────
  function _updateBulkToolbar() {
    const $toolbar = document.getElementById('outreach-bulk-toolbar');
    const $count = document.getElementById('outreach-selected-count');
    if (!$toolbar) return;
    if (_selectedProspects.size > 0) {
      $toolbar.classList.remove('hidden');
      if ($count) $count.textContent = `${_selectedProspects.size} selected`;
    } else {
      $toolbar.classList.add('hidden');
    }
  }

  window.outreachToggleRow = function (cb) {
    const id = cb.dataset.id;
    if (cb.checked) {
      _selectedProspects.add(id);
    } else {
      _selectedProspects.delete(id);
    }
    // Highlight row
    const row = cb.closest('tr');
    if (row) row.classList.toggle('bg-electric/5', cb.checked);
    _updateBulkToolbar();
  };

  window.outreachToggleSelectAll = function () {
    const $all = document.getElementById('outreach-select-all');
    const cbs = document.querySelectorAll('.outreach-row-cb');
    cbs.forEach(cb => {
      cb.checked = $all.checked;
      const id = cb.dataset.id;
      if ($all.checked) _selectedProspects.add(id); else _selectedProspects.delete(id);
      const row = cb.closest('tr');
      if (row) row.classList.toggle('bg-electric/5', $all.checked);
    });
    _updateBulkToolbar();
  };

  window.outreachClearSelection = function () {
    _selectedProspects.clear();
    document.querySelectorAll('.outreach-row-cb').forEach(cb => {
      cb.checked = false;
      const row = cb.closest('tr');
      if (row) row.classList.remove('bg-electric/5');
    });
    const $all = document.getElementById('outreach-select-all');
    if ($all) $all.checked = false;
    _updateBulkToolbar();
  };

  window.outreachBulkAction = async function (action) {
    const ids = [..._selectedProspects];
    if (ids.length === 0) return _toast('No prospects selected', true);

    const actionLabels = { advance: 'Auto-Advance', audit: 'Audit', recon: 'Recon', enqueue: 'Generate Emails' };
    const label = actionLabels[action] || action;

    if (!confirm(`${label} ${ids.length} prospect(s)?\n\nThis will process them through the pipeline. Emails will be created as drafts for your approval — nothing sends without you.`)) return;

    const endpoint = action === 'advance' ? '/outreach/bulk/advance'
      : action === 'audit' ? '/outreach/bulk/audit'
      : action === 'recon' ? '/outreach/bulk/recon'
      : '/outreach/bulk/enqueue';

    const res = await _api('POST', endpoint, { prospect_ids: ids });
    if (res) {
      _toast(`⚡ ${label} started for ${ids.length} prospect(s)`);
      outreachClearSelection();
      // Refresh table after a delay to show progress
      setTimeout(() => _loadProspectsTable(), 5000);
    }
  };

  // ── Pipeline Worker Control ─────────────────────────
  let _pipelineRunning = false;

  async function _loadPipelineStatus() {
    const data = await _api('GET', '/outreach/pipeline/status');
    if (!data) return;
    _pipelineRunning = data.running;
    const $dot = document.getElementById('outreach-pipeline-dot');
    const $status = document.getElementById('outreach-pipeline-status');
    const $toggle = document.getElementById('outreach-pipeline-toggle');
    const $audits = document.getElementById('outreach-pw-audits');
    const $recons = document.getElementById('outreach-pw-recons');
    const $enqueues = document.getElementById('outreach-pw-enqueues');

    if ($dot) {
      $dot.className = `w-2 h-2 rounded-full ${data.running ? 'bg-emerald-400 animate-pulse' : 'bg-gray-600'}`;
    }
    if ($status) {
      const agentInfo = data.agent_count > 1 ? ` · ${data.agent_count} agents` : '';
      $status.textContent = data.running
        ? `Running · Cycle #${data.cycle_count || 0}${agentInfo}${data.last_cycle ? ' · ' + _timeAgo(data.last_cycle) : ''}`
        : 'Stopped';
      $status.className = `text-[0.65rem] font-mono ${data.running ? 'text-emerald-400' : 'text-gray-500'}`;
    }
    if ($toggle) {
      $toggle.textContent = data.running ? 'Stop' : 'Start';
      $toggle.className = data.running
        ? 'px-2 py-0.5 bg-red-600/20 text-red-400 border border-red-600/30 rounded text-[0.6rem] font-mono hover:bg-red-600/30 transition'
        : 'px-2 py-0.5 bg-emerald-600/20 text-emerald-400 border border-emerald-600/30 rounded text-[0.6rem] font-mono hover:bg-emerald-600/30 transition';
    }
    if ($audits) $audits.textContent = data.audits_completed || 0;
    if ($recons) $recons.textContent = data.recons_completed || 0;
    if ($enqueues) $enqueues.textContent = data.enqueues_completed || 0;
    const $crawls = document.getElementById('outreach-pw-crawls');
    if ($crawls) $crawls.textContent = data.crawls_completed || 0;

    // Show DB-sourced totals from the pipeline status endpoint itself
    const dbCounts = data.db_status_counts || {};
    const totalDB = Object.values(dbCounts).reduce((a, b) => a + b, 0);
    const $dbTotal = document.getElementById('outreach-pw-db-total');
    const $dbAudits = document.getElementById('outreach-pw-db-audited');
    const $dbEnriched = document.getElementById('outreach-pw-db-enriched');
    const $dbQueued = document.getElementById('outreach-pw-db-queued');
    if ($dbTotal) $dbTotal.textContent = totalDB;
    if ($dbAudits) $dbAudits.textContent = dbCounts.audited || 0;
    if ($dbEnriched) $dbEnriched.textContent = dbCounts.enriched || 0;
    if ($dbQueued) $dbQueued.textContent = dbCounts.queued || 0;
    // Sync agent count dropdown
    const $agentSel = document.getElementById('outreach-agent-count');
    if ($agentSel && data.agent_count) {
      const cur = data.agent_count.toString();
      for (const opt of $agentSel.options) {
        if (opt.value === cur) { $agentSel.value = cur; break; }
      }
    }
  }

  window.outreachTogglePipeline = async function () {
    const agentCount = parseInt(document.getElementById('outreach-agent-count')?.value || '1');
    if (_pipelineRunning) {
      const res = await _api('POST', '/outreach/pipeline/stop');
      if (res) {
        _toast('Pipeline agents stopped');
        _pipelineRunning = false;
        _loadPipelineStatus();
      }
    } else {
      const res = await _api('POST', '/outreach/pipeline/start', { count: agentCount });
      if (res) {
        _toast(`🚀 Started ${res.agents?.length || 1} pipeline agent(s) — auto-processing prospects`);
        _pipelineRunning = true;
        _loadPipelineStatus();
      }
    }
  };

  window.outreachScaleAgents = async function (count) {
    count = parseInt(count) || 1;
    const res = await _api('POST', '/outreach/pipeline/scale', { count });
    if (res) {
      _toast(`📊 Scaled to ${res.agent_count} agent(s)`);
      _loadPipelineStatus();
    }
  };

  window.outreachRecoverAll = async function () {
    const res = await _api('POST', '/outreach/pipeline/recover');
    if (res) {
      const r = res.recovered || {};
      _toast(`🔧 Recovery: ${r.total || 0} items fixed (${r.orphaned_queued || 0} orphaned, ${r.failed_emails_reset || 0} emails reset)`);
      _loadProspectsTable();
    }
  };

  // Poll pipeline status every 30s
  setInterval(_loadPipelineStatus, 30000);
  // Initial load
  setTimeout(_loadPipelineStatus, 2000);

  // ── Prospect Detail Modal ────────────────────────────
  window.outreachViewProspect = async function (id) {
    if (!id) { outreachCloseProspect(); return; }
    const data = await _api('GET', `/outreach/prospects/${id}`);
    const $modal = document.getElementById('outreach-prospect-modal');
    const $body = document.getElementById('outreach-prospect-modal-body');
    if (!$modal || !$body || !data) return;

    const hasWebsite = data.has_website && data.website_url;
    const googleUrl = data.google_place_id
      ? `https://www.google.com/maps/place/?q=place_id:${encodeURIComponent(data.google_place_id)}`
      : (data.google_maps_url || '');

    $body.innerHTML = `
      <!-- Header -->
      <div class="flex items-start gap-4 mb-5 pr-8">
        <div class="flex-1 min-w-0">
          <h2 class="text-xl font-bold text-gray-100 mb-1">${_esc(data.business_name)}</h2>
          <div class="flex flex-wrap items-center gap-2 text-xs">
            ${_statusBadge(data.status)}
            <span class="text-gray-500">${_esc((data.business_type || '—').replace(/_/g, ' '))}</span>
            <span class="text-gray-600">·</span>
            <span class="text-gray-400">${_esc(data.address || `${data.city || ''}, ${data.state || ''}`)}</span>
          </div>
        </div>
        <div class="text-right">
          <div class="text-3xl font-bold ${_scoreColor(data.priority_score)}">${data.priority_score ?? '—'}</div>
          <div class="text-[0.6rem] text-gray-600 uppercase font-mono">Priority</div>
        </div>
      </div>

      <!-- Info Grid -->
      <div class="grid grid-cols-2 md:grid-cols-3 gap-3 mb-5">
        <div class="bg-surface-2 rounded-lg p-3 border border-border">
          <div class="text-[0.6rem] text-gray-600 uppercase font-mono mb-1">Phone</div>
          <div class="text-sm text-gray-200 font-mono">${data.phone ? _formatPhone(data.phone) : '<span class="text-gray-600">—</span>'}</div>
        </div>
        <div class="bg-surface-2 rounded-lg p-3 border border-border">
          <div class="text-[0.6rem] text-gray-600 uppercase font-mono mb-1">Owner / Contact <button onclick="outreachEditContact('${data.id}')" class="text-gray-600 hover:text-electric ml-1 cursor-pointer" title="Edit">✏️</button></div>
          <div id="prospect-contact-display-${data.id}">
            <div class="text-sm text-gray-200">${_esc(data.owner_name || '—')}</div>
            ${data.owner_email ? `<div class="text-xs text-electric mt-0.5">${_esc(data.owner_email)}</div>` : '<div class="text-xs text-gray-600 mt-0.5">No email</div>'}
          </div>
          <div id="prospect-contact-edit-${data.id}" class="hidden mt-1 space-y-1">
            <input id="edit-owner-name-${data.id}" type="text" value="${_esc(data.owner_name || '')}" placeholder="Owner name" class="w-full bg-surface-1 border border-border rounded px-2 py-1 text-xs text-gray-200 font-mono focus:border-electric outline-none">
            <input id="edit-owner-email-${data.id}" type="email" value="${_esc(data.owner_email || '')}" placeholder="owner@email.com" class="w-full bg-surface-1 border border-border rounded px-2 py-1 text-xs text-gray-200 font-mono focus:border-electric outline-none">
            <div class="flex gap-1">
              <button onclick="outreachSaveContact('${data.id}')" class="px-2 py-0.5 bg-emerald-600/20 text-emerald-400 border border-emerald-600/30 rounded text-[0.6rem] font-mono hover:bg-emerald-600/30">💾 Save</button>
              <button onclick="outreachCancelEditContact('${data.id}')" class="px-2 py-0.5 bg-gray-600/20 text-gray-400 border border-gray-600/30 rounded text-[0.6rem] font-mono hover:bg-gray-600/30">Cancel</button>
            </div>
          </div>
        </div>
        <div class="bg-surface-2 rounded-lg p-3 border border-border">
          <div class="text-[0.6rem] text-gray-600 uppercase font-mono mb-1">Google Rating</div>
          <div class="text-sm text-gray-200">${data.google_rating ? `⭐ ${data.google_rating} <span class="text-gray-500">(${data.google_reviews || 0} reviews)</span>` : '<span class="text-gray-600">—</span>'}</div>
        </div>
        <div class="bg-surface-2 rounded-lg p-3 border border-border col-span-2 md:col-span-2">
          <div class="text-[0.6rem] text-gray-600 uppercase font-mono mb-1">Website</div>
          ${hasWebsite
            ? `<a href="${_esc(data.website_url)}" target="_blank" class="text-sm text-electric hover:underline break-all">${_esc(data.website_url)}</a>`
            : '<div class="text-sm text-red-400 font-semibold">🚫 No website — perfect prospect for a new build!</div>'}
        </div>
        <div class="bg-surface-2 rounded-lg p-3 border border-border">
          <div class="text-[0.6rem] text-gray-600 uppercase font-mono mb-1">Links</div>
          <div class="flex gap-2">
            ${googleUrl ? `<a href="${_esc(googleUrl)}" target="_blank" class="text-xs text-blue-400 hover:underline">📍 Google Maps</a>` : ''}
            ${data.phone ? `<a href="tel:${_esc(data.phone)}" class="text-xs text-emerald-400 hover:underline">📞 Call</a>` : ''}
          </div>
        </div>
      </div>

      ${!hasWebsite ? `
      <div class="bg-red-500/10 border border-red-500/20 rounded-lg p-4 mb-5">
        <div class="flex items-center gap-3">
          <div class="text-2xl">🎯</div>
          <div>
            <div class="text-sm font-semibold text-red-300">High-Value Target — No Website</div>
            <div class="text-xs text-red-400/70 mt-0.5">This business has no online presence. They need a website. Reach out with a free audit offer or portfolio showcase.</div>
          </div>
        </div>
      </div>` : ''}

      <!-- Score Breakdown -->
      ${data.score_breakdown ? (() => {
        const sb = data.score_breakdown;
        const components = ['site_badness','business_health','proximity','industry_value','reachability'];
        const barColors = {
          site_badness: 'from-red-500 to-orange-400',
          business_health: 'from-emerald-500 to-green-400',
          proximity: 'from-blue-500 to-cyan-400',
          industry_value: 'from-purple-500 to-pink-400',
          reachability: 'from-yellow-500 to-amber-400',
        };
        const icons = { site_badness: '🌐', business_health: '⭐', proximity: '📍', industry_value: '🏭', reachability: '📧' };
        return `
      <div class="mb-5">
        <h3 class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3 font-mono">🧬 Score Breakdown — ${sb.total.value} / ${sb.total.max}</h3>
        <div class="space-y-2">
          ${components.map(k => {
            const c = sb[k];
            const pct = Math.round((c.value / c.max) * 100);
            return `
          <div>
            <div class="flex items-center justify-between text-[0.65rem] mb-0.5">
              <span class="text-gray-400 font-mono">${icons[k]} ${c.label}</span>
              <span class="text-gray-500">${c.value} / ${c.max}</span>
            </div>
            <div class="w-full bg-surface-2 rounded-full h-2 overflow-hidden border border-border">
              <div class="h-full rounded-full bg-gradient-to-r ${barColors[k]}" style="width: ${pct}%"></div>
            </div>
            <div class="text-[0.55rem] text-gray-600 mt-0.5">${c.detail}</div>
          </div>`;
          }).join('')}
        </div>
      </div>`;
      })() : ''}

      <!-- Pipeline Status -->
      <div class="mb-5">
        <h3 class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3 font-mono">🚀 Pipeline Status</h3>
        <div class="flex items-center gap-1 mb-3">
          ${['discovered','audited','enriched','queued','contacted'].map((s, i) => {
            const active = data.status === s;
            const done = ['discovered','audited','enriched','queued','contacted'].indexOf(data.status) >= i;
            const colors = done ? 'bg-electric/20 border-electric/40 text-electric' : 'bg-surface-2 border-border text-gray-600';
            return `<div class="flex items-center gap-1">
              <div class="px-2 py-1 rounded text-[0.55rem] font-mono border ${colors} ${active ? 'ring-1 ring-electric' : ''}">${s}</div>
              ${i < 4 ? '<div class="text-gray-700 text-[0.5rem]">→</div>' : ''}
            </div>`;
          }).join('')}
        </div>
        ${data.status === 'discovered' && hasWebsite ? `
        <div class="bg-surface-2 border border-border rounded-lg p-3 text-xs text-gray-400">
          <span class="text-amber-400 font-semibold">Next step:</span> Run a <strong>Website Audit</strong> to analyze site quality and move to "audited" stage.
          <button onclick="outreachTriggerAudit('${data.id}')" class="ml-2 px-3 py-1 bg-amber-600/20 text-amber-400 border border-amber-600/30 rounded text-[0.65rem] font-mono hover:bg-amber-600/30 transition">⚡ Run Audit</button>
        </div>` : ''}
        ${data.status === 'discovered' && !hasWebsite ? `
        <div class="bg-surface-2 border border-border rounded-lg p-3 text-xs text-gray-400">
          <span class="text-amber-400 font-semibold">Next step:</span> Run <strong>Recon</strong> to find owner contact info (no website to audit).
          <button onclick="outreachTriggerRecon('${data.id}')" class="ml-2 px-3 py-1 bg-amber-600/20 text-amber-400 border border-amber-600/30 rounded text-[0.65rem] font-mono hover:bg-amber-600/30 transition">🔍 Run Recon</button>
        </div>` : ''}
        ${data.status === 'audited' ? `
        <div class="bg-surface-2 border border-border rounded-lg p-3 text-xs text-gray-400">
          <span class="text-blue-400 font-semibold">Next step:</span> Run <strong>Recon</strong> to find owner email and enrich the prospect.
          <button onclick="outreachTriggerRecon('${data.id}')" class="ml-2 px-3 py-1 bg-blue-600/20 text-blue-400 border border-blue-600/30 rounded text-[0.65rem] font-mono hover:bg-blue-600/30 transition">🔍 Run Recon</button>
        </div>` : ''}
        ${data.status === 'enriched' && data.owner_email ? `
        <div class="bg-surface-2 border border-border rounded-lg p-3 text-xs text-gray-400">
          <span class="text-emerald-400 font-semibold">Ready!</span> Email found: <span class="text-electric">${_esc(data.owner_email)}</span>. Generate an email draft for approval.
          <button onclick="outreachEnqueue('${data.id}')" class="ml-2 px-3 py-1 bg-emerald-600/20 text-emerald-400 border border-emerald-600/30 rounded text-[0.65rem] font-mono hover:bg-emerald-600/30 transition">📧 Generate Email Draft</button>
        </div>` : ''}
        ${data.status === 'enriched' && !data.owner_email ? `
        <div class="bg-surface-2 border border-border rounded-lg p-3 text-xs text-gray-400">
          <span class="text-red-400 font-semibold">Missing email.</span> Recon did not find an owner email. Add one manually or re-run recon.
        </div>` : ''}
      </div>

      <!-- Audit Scores (if any) -->
      ${data.audits && data.audits.length > 0 ? `
      <div class="mb-5">
        <h3 class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3 font-mono">📊 Latest Audit</h3>
        ${_renderAuditCard(data.audits[0])}
      </div>` : ''}

      <!-- Email History -->
      ${data.emails && data.emails.length > 0 ? `
      <div class="mb-5">
        <h3 class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3 font-mono">📧 Email History (${data.emails.length})</h3>
        <div class="space-y-2 max-h-48 overflow-y-auto">
          ${data.emails.map(e => `
            <div class="bg-surface-2 rounded-lg p-3 border border-border flex items-center gap-3">
              <div class="flex-1 min-w-0">
                <div class="text-xs text-gray-300 truncate">${_esc(e.subject || '—')}</div>
                <div class="text-[0.6rem] text-gray-600 mt-0.5">${_esc(e.template_name || 'email')} · Step ${e.sequence_step || 1} · ${_timeAgo(e.scheduled_for || e.sent_at)}</div>
              </div>
              ${_statusBadge(e.status)}
            </div>
          `).join('')}
        </div>
      </div>` : `
      <div class="mb-5 bg-surface-2 rounded-lg border border-border p-4 text-center">
        <div class="text-gray-600 text-sm font-mono">No emails sent to this prospect yet.</div>
      </div>`}

      <!-- Actions -->
      <div class="flex flex-wrap gap-2 pt-3 border-t border-border">
        <button id="btnTestEmail-${data.id}" onclick="outreachTestEmail('${data.id}')" class="px-4 py-2 bg-cyan-600/20 text-cyan-400 border border-cyan-600/30 rounded-lg text-xs font-mono hover:bg-cyan-600/30 transition">🧪 Generate Test Email</button>
        ${data.status !== 'promoted' ? `<button onclick="outreachPromote('${data.id}')" class="px-4 py-2 bg-emerald-600/20 text-emerald-400 border border-emerald-600/30 rounded-lg text-xs font-mono hover:bg-emerald-600/30 transition">💰 Promote to Lead</button>` : ''}
        ${data.status !== 'do_not_contact' ? `<button onclick="outreachDNC('${data.id}')" class="px-4 py-2 bg-red-600/10 text-red-400/70 border border-red-600/20 rounded-lg text-xs font-mono hover:bg-red-600/20 transition">🚫 Do Not Contact</button>` : ''}
        ${googleUrl ? `<a href="${_esc(googleUrl)}" target="_blank" class="px-4 py-2 bg-blue-600/20 text-blue-400 border border-blue-600/30 rounded-lg text-xs font-mono hover:bg-blue-600/30 transition inline-block">📍 View on Maps</a>` : ''}
        ${hasWebsite ? `<a href="${_esc(data.website_url)}" target="_blank" class="px-4 py-2 bg-purple-600/20 text-purple-400 border border-purple-600/30 rounded-lg text-xs font-mono hover:bg-purple-600/30 transition inline-block">🌐 Visit Site</a>` : ''}
      </div>
    `;

    $modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden'; // Prevent background scroll
  };

  window.outreachCloseProspect = function () {
    const $modal = document.getElementById('outreach-prospect-modal');
    if ($modal) $modal.classList.add('hidden');
    document.body.style.overflow = '';
  };

  window.outreachTestEmail = async function (prospectId) {
    const btn = document.getElementById(`btnTestEmail-${prospectId}`);
    if (btn) { btn.disabled = true; btn.innerHTML = '<span class="animate-spin inline-block">⏳</span> Generating…'; }
    try {
      const res = await fetch(`${API_BASE}/outreach/prospects/${prospectId}/test-email`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ step: 1 }),
      });
      if (!res.ok) throw new Error(await res.text());
      const result = await res.json();
      _toast(`🧪 Test email created: "${result.subject}" — check the Email Approval Queue`);
      // Refresh the modal to show the new email in history
      setTimeout(() => outreachViewProspect(prospectId), 1000);
    } catch (e) {
      _toast('Test email failed: ' + e.message, true);
    } finally {
      if (btn) { btn.disabled = false; btn.innerHTML = '🧪 Generate Test Email'; }
    }
  };

  /* ── Inline Edit Owner/Email ── */
  window.outreachEditContact = function (prospectId) {
    const disp = document.getElementById(`prospect-contact-display-${prospectId}`);
    const edit = document.getElementById(`prospect-contact-edit-${prospectId}`);
    if (disp) disp.classList.add('hidden');
    if (edit) edit.classList.remove('hidden');
    const nameInput = document.getElementById(`edit-owner-name-${prospectId}`);
    if (nameInput) nameInput.focus();
  };

  window.outreachCancelEditContact = function (prospectId) {
    const disp = document.getElementById(`prospect-contact-display-${prospectId}`);
    const edit = document.getElementById(`prospect-contact-edit-${prospectId}`);
    if (disp) disp.classList.remove('hidden');
    if (edit) edit.classList.add('hidden');
  };

  window.outreachSaveContact = async function (prospectId) {
    const name = (document.getElementById(`edit-owner-name-${prospectId}`)?.value || '').trim();
    const email = (document.getElementById(`edit-owner-email-${prospectId}`)?.value || '').trim();
    try {
      const res = await fetch(`${API_BASE}/outreach/prospects/${prospectId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ owner_name: name || null, owner_email: email || null }),
      });
      if (!res.ok) throw new Error(await res.text());
      _toast(`✅ Contact info updated${email ? ' — ' + email : ''}`);
      // Refresh modal
      setTimeout(() => outreachViewProspect(prospectId), 500);
    } catch (e) {
      _toast('Save failed: ' + e.message, true);
    }
  };

  /* ── Send Test Email to Yourself ── */
  window.outreachSendTestToMe = async function (prospectId) {
    // First check if there's a pending email for this prospect
    const btn = document.getElementById(`btnSendTestMe-${prospectId}`);
    if (btn) { btn.disabled = true; btn.innerHTML = '<span class="animate-spin inline-block">⏳</span> Sending…'; }

    try {
      // Get prospect detail to see existing emails
      const data = await _api('GET', `/outreach/prospects/${prospectId}`);
      let emailId = null;

      // Find a pending/approved email
      if (data.emails && data.emails.length > 0) {
        const pending = data.emails.find(e => ['pending_approval', 'approved', 'draft'].includes(e.status));
        if (pending) emailId = pending.id;
      }

      // If no email exists, generate one first
      if (!emailId) {
        const genRes = await fetch(`${API_BASE}/outreach/prospects/${prospectId}/test-email`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ step: 1 }),
        });
        if (!genRes.ok) throw new Error(await genRes.text());
        const genResult = await genRes.json();
        emailId = genResult.email_id;
      }

      // Prompt for email address
      const toEmail = prompt('Send test email to:', '');
      if (!toEmail) {
        if (btn) { btn.disabled = false; btn.innerHTML = '📧 Send Test to Me'; }
        return;
      }

      // Send it
      const sendRes = await fetch(`${API_BASE}/outreach/emails/${emailId}/send-test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ to_email: toEmail }),
      });
      if (!sendRes.ok) throw new Error(await sendRes.text());
      const sendResult = await sendRes.json();
      _toast(`📧 Test sent to ${sendResult.to} — check your inbox!`);
    } catch (e) {
      _toast('Send test failed: ' + e.message, true);
    } finally {
      if (btn) { btn.disabled = false; btn.innerHTML = '📧 Send Test to Me'; }
    }
  };

  window.outreachTriggerAudit = async function (prospectId) {
    try {
      const res = await fetch(`${API_BASE}/outreach/prospects/${prospectId}/audit`, { method: 'POST' });
      if (!res.ok) throw new Error(await res.text());
      _toast('⚡ Audit started — this may take 30-60 seconds');
    } catch (e) { _toast('Audit failed: ' + e.message, true); }
  };

  window.outreachTriggerRecon = async function (prospectId) {
    try {
      const res = await fetch(`${API_BASE}/outreach/prospects/${prospectId}/recon`, { method: 'POST' });
      if (!res.ok) throw new Error(await res.text());
      _toast('🔍 Recon started — looking for owner info');
    } catch (e) { _toast('Recon failed: ' + e.message, true); }
  };

  window.outreachEnqueue = async function (prospectId) {
    try {
      const res = await fetch(`${API_BASE}/outreach/prospects/${prospectId}/enqueue`, { method: 'POST' });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      _toast('📧 Email draft created — check the Approval Queue');
      // Refresh the modal
      outreachViewProspect(prospectId);
    } catch (e) { _toast('Enqueue failed: ' + e.message, true); }
  };

  // Close modal on Escape key or backdrop click
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      const $prospectModal = document.getElementById('outreach-prospect-modal');
      if ($prospectModal && !$prospectModal.classList.contains('hidden')) {
        outreachCloseProspect();
        return;
      }
      const $emailModal = document.getElementById('outreach-email-editor');
      if ($emailModal && !$emailModal.classList.contains('hidden')) {
        outreachCloseEditor();
      }
    }
  });
  document.addEventListener('click', (e) => {
    if (e.target.id === 'outreach-prospect-modal') outreachCloseProspect();
    if (e.target.id === 'outreach-email-editor') outreachCloseEditor();
  });

  function _toast(msg, isError = false) {
    const el = document.createElement('div');
    el.className = `fixed top-4 right-4 z-[99999] px-5 py-3 rounded-lg text-sm font-mono shadow-lg border transition-opacity duration-300 ${isError ? 'bg-red-900/90 border-red-500/40 text-red-200' : 'bg-surface-1/95 border-electric/30 text-gray-200'}`;
    el.textContent = msg;
    document.body.appendChild(el);
    setTimeout(() => { el.style.opacity = '0'; setTimeout(() => el.remove(), 300); }, 3500);
  }

  function _formatPhone(p) {
    if (!p || p.length !== 10) return _esc(p || '');
    return `(${p.slice(0,3)}) ${p.slice(3,6)}-${p.slice(6)}`;
  }

  window.outreachPromote = async function (id) {
    await _api('POST', `/outreach/prospects/${id}/promote`);
    _showBanner('💰 Prospect promoted to Lead!', 'success');
    if (id) window.outreachViewProspect(id);
    _loadProspectsTable();
  };

  window.outreachDNC = async function (id) {
    if (!confirm('Mark as Do Not Contact? This prospect will be excluded from all outreach.')) return;
    await _api('PATCH', `/outreach/prospects/${id}`, { status: 'do_not_contact' });
    _showBanner('🚫 Marked as Do Not Contact', 'info');
    if (id) window.outreachViewProspect(id);
    _loadProspectsTable();
  };

  // ── Email Approval Queue ─────────────────────────────

  let _emailQueueOffset = 0;
  let _emailQueueTotal = 0;

  async function _loadPendingEmails(offset) {
    const limit = parseInt(document.getElementById('email-queue-page-size')?.value || '25', 10);
    if (typeof offset === 'number') _emailQueueOffset = offset;
    const data = await _api('GET', `/outreach/emails/pending?limit=${limit}&offset=${_emailQueueOffset}`);
    const $el = document.getElementById('outreach-pending-emails');
    const $count = document.getElementById('outreach-pending-count');
    const $pag = document.getElementById('email-queue-pagination');
    if (!$el || !data) return;

    const emails = data.emails || [];
    _emailQueueTotal = data.total || 0;
    if ($count) $count.textContent = _emailQueueTotal;

    if (emails.length === 0) {
      $el.innerHTML = '<div class="text-center text-gray-500 py-4 font-mono text-sm">No emails pending approval. 🎉</div>';
      if ($pag) $pag.classList.add('hidden');
      return;
    }

    $el.innerHTML = emails.map(e => `
      <div class="bg-surface-2 rounded-lg border border-border p-3 hover:border-electric/30 transition">
        <div class="flex items-start justify-between mb-2">
          <div>
            <div class="font-mono text-sm text-gray-200">${_esc(e.prospect_name || '—')}</div>
            <div class="text-[0.65rem] text-gray-500 font-mono">${_esc(e.prospect_type || '')} · ${_esc(e.prospect_city || '')} · Score: ${e.prospect_score ?? '—'}</div>
          </div>
          <span class="px-2 py-0.5 bg-amber-500/15 text-amber-400 text-[0.6rem] font-mono rounded-full">pending</span>
        </div>
        <div class="mb-2">
          <div class="text-xs text-gray-400 font-mono">Subject: <span class="text-gray-200">${_esc(e.subject || '—')}</span></div>
          <div class="text-xs text-gray-500 font-mono mt-0.5">To: ${_esc(e.to_email || '—')} · Step ${e.sequence_step || 1}</div>
        </div>
        <div class="flex gap-2">
          <button onclick="outreachEditEmail('${e.id}')" class="px-2.5 py-1 bg-blue-600/20 text-blue-400 border border-blue-600/30 rounded text-[0.65rem] font-mono hover:bg-blue-600/30 transition">✏️ Edit</button>
          <button onclick="outreachApproveOne('${e.id}')" class="px-2.5 py-1 bg-emerald-600/20 text-emerald-400 border border-emerald-600/30 rounded text-[0.65rem] font-mono hover:bg-emerald-600/30 transition">✓ Approve</button>
          <button onclick="outreachRejectEmail('${e.id}')" class="px-2.5 py-1 bg-red-600/20 text-red-400 border border-red-600/30 rounded text-[0.65rem] font-mono hover:bg-red-600/30 transition">✕ Reject</button>
        </div>
      </div>
    `).join('');

    // Update pagination
    if ($pag) {
      $pag.classList.remove('hidden');
      const start = _emailQueueOffset + 1;
      const end = Math.min(_emailQueueOffset + emails.length, _emailQueueTotal);
      document.getElementById('email-queue-page-info').textContent = `${start}–${end} of ${_emailQueueTotal}`;
      document.getElementById('email-queue-prev').disabled = (_emailQueueOffset === 0);
      document.getElementById('email-queue-next').disabled = (end >= _emailQueueTotal);
    }
  }

  window.outreachEmailQueuePageChange = function (offset) {
    _loadPendingEmails(offset);
  };
  window.outreachEmailQueuePrev = function () {
    const limit = parseInt(document.getElementById('email-queue-page-size')?.value || '25', 10);
    _loadPendingEmails(Math.max(0, _emailQueueOffset - limit));
  };
  window.outreachEmailQueueNext = function () {
    const limit = parseInt(document.getElementById('email-queue-page-size')?.value || '25', 10);
    if (_emailQueueOffset + limit < _emailQueueTotal) {
      _loadPendingEmails(_emailQueueOffset + limit);
    }
  };

  window.outreachRefreshPending = async function () {
    const $btn = document.querySelector('[onclick="outreachRefreshPending()"]');
    if ($btn) { $btn.disabled = true; $btn.innerHTML = '<span class="animate-spin inline-block">↻</span> Loading…'; }
    await _loadPendingEmails();
    if ($btn) { $btn.disabled = false; $btn.innerHTML = '↻ Refresh'; }
  };

  // ── Email Tracking Stats ─────────────────────────────
  async function _loadEmailTrackingStats() {
    const data = await _api('GET', '/outreach/email-stats');
    if (!data) return;

    const ov = data.overview || {};
    const eg = data.engagement || {};

    // Update total sent badge
    const $badge = document.getElementById('tracking-total-sent');
    if ($badge) $badge.textContent = `${ov.sent || 0} sent`;

    // Update delivery funnel numbers
    const funnelMap = {
      'ts-pending': { val: ov.pending_approval || 0, color: 'text-amber-400' },
      'ts-scheduled': { val: ov.scheduled || 0, color: 'text-blue-400' },
      'ts-sent': { val: ov.sent || 0, color: 'text-cyan-400' },
      'ts-opened': { val: eg.unique_opens || 0, color: 'text-emerald-400' },
      'ts-clicked': { val: eg.unique_clicks || 0, color: 'text-purple-400' },
      'ts-replied': { val: eg.replied || 0, color: 'text-yellow-400' },
      'ts-bounced': { val: ov.bounced || 0, color: 'text-red-400' },
      'ts-unsub': { val: ov.unsubscribed || 0, color: 'text-gray-400' },
    };
    for (const [id, cfg] of Object.entries(funnelMap)) {
      const $el = document.getElementById(id);
      if ($el) {
        const $num = $el.querySelector('.font-bold');
        if ($num) $num.textContent = cfg.val;
      }
    }

    // Update rates
    const setText = (id, val) => { const $el = document.getElementById(id); if ($el) $el.textContent = val + '%'; };
    setText('rate-open', eg.open_rate || 0);
    setText('rate-click', eg.click_rate || 0);
    setText('rate-reply', eg.reply_rate || 0);
    setText('rate-bounce', eg.bounce_rate || 0);

    // Per-step breakdown table
    const steps = data.per_step || [];
    const $steps = document.getElementById('tracking-steps-table');
    if ($steps && steps.length > 0) {
      const stepNames = { 1: 'Initial Audit', 2: 'Follow-up Value', 3: 'Social Proof', 4: 'Breakup', 5: 'Resurrection' };
      $steps.innerHTML = `
        <div class="grid grid-cols-7 gap-1 text-[0.55rem] text-gray-600 uppercase mb-1 font-semibold">
          <div>Step</div><div>Total</div><div>Sent</div><div>Opened</div><div>Clicked</div><div>Replied</div><div>Bounced</div>
        </div>
        ${steps.map(s => `
          <div class="grid grid-cols-7 gap-1 py-1 border-t border-gray-800/30">
            <div class="text-gray-300">${stepNames[s.step] || 'Step ' + s.step}</div>
            <div>${s.total}</div>
            <div>${s.sent}</div>
            <div class="text-emerald-400">${s.opened}${s.sent > 0 ? ' <span class="text-gray-600">(' + s.open_rate + '%)</span>' : ''}</div>
            <div class="text-purple-400">${s.clicked}${s.sent > 0 ? ' <span class="text-gray-600">(' + s.click_rate + '%)</span>' : ''}</div>
            <div class="text-yellow-400">${s.replied}</div>
            <div class="text-red-400">${s.bounced}</div>
          </div>
        `).join('')}
      `;
    }

    // Recent engagement feed
    const recent = data.recent_engagement || [];
    const $recent = document.getElementById('tracking-recent');
    if ($recent) {
      if (recent.length === 0) {
        $recent.innerHTML = '<div class="text-xs text-gray-500 font-mono text-center py-3">No engagement yet — send some emails first!</div>';
      } else {
        const eventIcons = { opened: '👀', clicked: '🔗', replied: '⭐' };
        const eventColors = { opened: 'text-emerald-400', clicked: 'text-purple-400', replied: 'text-yellow-400' };
        $recent.innerHTML = recent.map(r => `
          <div class="flex items-center gap-2 py-1.5 border-b border-gray-800/20 last:border-0">
            <span class="text-sm">${eventIcons[r.event] || '•'}</span>
            <div class="flex-1 min-w-0">
              <div class="text-xs truncate"><span class="${eventColors[r.event] || 'text-gray-300'} font-semibold">${_esc(r.business)}</span> <span class="text-gray-500">${r.event}</span></div>
              <div class="text-[0.55rem] text-gray-600 truncate">${_esc(r.subject)} · ${r.opens}× opened · ${r.clicks}× clicked</div>
            </div>
            <div class="text-[0.55rem] text-gray-600 whitespace-nowrap">${_timeAgo(r.ts)}</div>
          </div>
        `).join('');
      }
    }
  }

  window.outreachRefreshTracking = async function () {
    const $btn = document.querySelector('[onclick="outreachRefreshTracking()"]');
    if ($btn) { $btn.disabled = true; $btn.innerHTML = '<span class="animate-spin inline-block">↻</span>'; }
    await _loadEmailTrackingStats();
    if ($btn) { $btn.disabled = false; $btn.innerHTML = '↻ Refresh'; }
  };

  window.outreachApproveOne = async function (emailId) {
    const $btn = document.querySelector(`[onclick="outreachApproveOne('${emailId}')"]`);
    if ($btn) { $btn.disabled = true; $btn.innerHTML = '⏳'; }
    const res = await _api('POST', `/outreach/emails/${emailId}/approve`);
    if (res) {
      _showBanner(`✓ Email approved — will send shortly`, 'success');
      _loadPendingEmails();
    } else if ($btn) { $btn.disabled = false; $btn.innerHTML = '✓ Approve'; }
  };

  window.outreachApproveAll = async function () {
    if (!confirm('Approve ALL pending emails? They will be sent at the next queue cycle.')) return;
    const $btn = document.querySelector('[onclick="outreachApproveAll()"]');
    if ($btn) { $btn.disabled = true; $btn.dataset.origHtml = $btn.innerHTML; $btn.innerHTML = '⏳ Approving…'; }
    const res = await _api('POST', '/outreach/emails/batch-approve', { all: true });
    if (res) {
      _showBanner(`✓ ${res.count || 0} emails approved — will send shortly`, 'success');
      _loadPendingEmails();
    }
    if ($btn) { $btn.disabled = false; $btn.innerHTML = $btn.dataset.origHtml || '✓ Approve All'; }
  };

  window.outreachRejectEmail = async function (emailId) {
    if (!confirm('Delete this email draft?')) return;
    await _api('DELETE', `/outreach/emails/${emailId}`);
    _loadPendingEmails();
  };

  window.outreachEditEmail = async function (emailId) {
    const data = await _api('GET', `/outreach/emails/${emailId}`);
    if (!data) return;

    document.getElementById('email-editor-id').value = data.id;
    document.getElementById('email-editor-to').textContent = data.to_email || '—';
    document.getElementById('email-editor-subject').value = data.subject || '';
    document.getElementById('email-editor-body').value = data.body_html || data.body_text || '';
    document.getElementById('email-editor-prospect').textContent = data.prospect_name || data.prospect_id || '';
    document.getElementById('email-editor-scheduled').textContent = 'after approval';

    // Load rendered preview into iframe
    _editorLoadPreview(data.body_html || data.body_text || '');
    // Default to preview mode
    outreachToggleEditorMode('preview');

    document.getElementById('outreach-email-editor').classList.remove('hidden');
  };

  /** Load HTML into the editor iframe and make it editable */
  function _editorLoadPreview(html) {
    const iframe = document.getElementById('email-editor-iframe');
    if (!iframe) return;
    // Write full HTML into iframe (srcdoc approach for same-origin)
    const doc = iframe.contentDocument || iframe.contentWindow.document;
    doc.open();
    doc.write(html);
    doc.close();
    // Make body editable so user can click + type to edit
    doc.body.setAttribute('contenteditable', 'true');
    doc.body.style.outline = 'none';
    doc.body.style.cursor = 'text';
  }

  /** Extract current HTML from iframe (after user edits) */
  function _editorGetPreviewHtml() {
    const iframe = document.getElementById('email-editor-iframe');
    if (!iframe) return '';
    const doc = iframe.contentDocument || iframe.contentWindow.document;
    // Clone full document HTML including <head>, but strip contenteditable
    const clone = doc.documentElement.cloneNode(true);
    const body = clone.querySelector('body');
    if (body) {
      body.removeAttribute('contenteditable');
      body.removeAttribute('style');
    }
    return '<!DOCTYPE html>\n<html>\n' + clone.innerHTML + '\n</html>';
  }

  /** Toggle between preview (iframe) and source (textarea) modes */
  window.outreachToggleEditorMode = function (mode) {
    const $preview = document.getElementById('email-editor-preview-wrap');
    const $source = document.getElementById('email-editor-body');
    const $btnPreview = document.getElementById('email-editor-mode-preview');
    const $btnSource = document.getElementById('email-editor-mode-source');
    if (!$preview || !$source) return;

    if (mode === 'source') {
      // Sync iframe → textarea
      $source.value = _editorGetPreviewHtml();
      $preview.classList.add('hidden');
      $source.classList.remove('hidden');
      $btnSource.className = 'px-2 py-0.5 bg-electric/20 text-electric border border-electric/30 rounded text-[0.6rem] font-mono';
      $btnPreview.className = 'px-2 py-0.5 bg-gray-700/50 text-gray-400 border border-gray-700 rounded text-[0.6rem] font-mono';
    } else {
      // Sync textarea → iframe (if user edited source)
      if (!$source.classList.contains('hidden')) {
        _editorLoadPreview($source.value);
      }
      $source.classList.add('hidden');
      $preview.classList.remove('hidden');
      $btnPreview.className = 'px-2 py-0.5 bg-electric/20 text-electric border border-electric/30 rounded text-[0.6rem] font-mono';
      $btnSource.className = 'px-2 py-0.5 bg-gray-700/50 text-gray-400 border border-gray-700 rounded text-[0.6rem] font-mono';
    }
  };

  window.outreachCloseEditor = function () {
    document.getElementById('outreach-email-editor').classList.add('hidden');
  };

  /** Get the current body HTML from whichever mode is active */
  function _editorGetBodyHtml() {
    const $source = document.getElementById('email-editor-body');
    // If source textarea is visible, use it; otherwise extract from iframe
    if ($source && !$source.classList.contains('hidden')) {
      return $source.value;
    }
    return _editorGetPreviewHtml();
  }

  window.outreachSaveEmail = async function () {
    const emailId = document.getElementById('email-editor-id').value;
    const subject = document.getElementById('email-editor-subject').value;
    const bodyHtml = _editorGetBodyHtml();
    const res = await _api('PATCH', `/outreach/emails/${emailId}`, {
      subject: subject,
      body_html: bodyHtml,
    });
    if (res) {
      _showBanner('💾 Email saved', 'success');
      _loadPendingEmails();
    }
  };

  window.outreachApproveFromEditor = async function () {
    const emailId = document.getElementById('email-editor-id').value;
    // Save changes first
    const subject = document.getElementById('email-editor-subject').value;
    const bodyHtml = _editorGetBodyHtml();
    await _api('PATCH', `/outreach/emails/${emailId}`, {
      subject: subject,
      body_html: bodyHtml,
    });
    // Then approve
    const res = await _api('POST', `/outreach/emails/${emailId}/approve`);
    if (res) {
      _showBanner('✓ Email approved — will send shortly', 'success');
      document.getElementById('outreach-email-editor').classList.add('hidden');
      _loadPendingEmails();
    }
  };

  /** Send a test copy of the current email in the editor to yourself */
  window.outreachSendTestFromEditor = async function () {
    const emailId = document.getElementById('email-editor-id').value;
    if (!emailId) { _toast('No email loaded', true); return; }

    const $btn = document.querySelector('[onclick="outreachSendTestFromEditor()"]');
    if ($btn) { $btn.disabled = true; $btn.innerHTML = '<span class="animate-spin inline-block">⏳</span> Sending…'; }

    try {
      // Save any edits first
      const subject = document.getElementById('email-editor-subject').value;
      const bodyHtml = _editorGetBodyHtml();
      await _api('PATCH', `/outreach/emails/${emailId}`, {
        subject: subject,
        body_html: bodyHtml,
      });

      // Prompt for email address
      const toEmail = prompt('Send test email to:', '');
      if (!toEmail) {
        if ($btn) { $btn.disabled = false; $btn.innerHTML = '📧 Send Test to Me'; }
        return;
      }

      // Send test
      const sendRes = await fetch(`${API_BASE}/outreach/emails/${emailId}/send-test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ to_email: toEmail }),
      });
      if (!sendRes.ok) throw new Error(await sendRes.text());
      const result = await sendRes.json();
      _toast(`📧 Test sent to ${result.to} — check your inbox!`);
    } catch (e) {
      _toast('Send test failed: ' + e.message, true);
    } finally {
      if ($btn) { $btn.disabled = false; $btn.innerHTML = '📧 Send Test to Me'; }
    }
  };

  /** Regenerate this email with current audit data */
  window.outreachRegenEmail = async function () {
    const emailId = document.getElementById('email-editor-id').value;
    if (!emailId) return;
    const $btn = document.querySelector('[onclick="outreachRegenEmail()"]');
    if ($btn) { $btn.disabled = true; $btn.dataset.origHtml = $btn.innerHTML; $btn.innerHTML = '<span class="animate-spin inline-block">🔄</span> Regenerating…'; }
    const res = await _api('POST', `/outreach/emails/${emailId}/regenerate`);
    if (res && res.email) {
      // Reload the editor with fresh content
      document.getElementById('email-editor-subject').value = res.email.subject || '';
      document.getElementById('email-editor-body').value = res.email.body_html || '';
      _editorLoadPreview(res.email.body_html || '');
      outreachToggleEditorMode('preview');
      _showBanner('🔄 Email regenerated with latest audit data', 'success');
    }
    if ($btn) { $btn.disabled = false; $btn.innerHTML = $btn.dataset.origHtml || '🔄 Regen'; }
  };

  /** Batch-regenerate all pending emails */
  window.outreachRegenAllPending = async function () {
    if (!confirm('Regenerate ALL pending emails with current audit data? This will overwrite any manual edits.')) return;
    const $btn = document.querySelector('[onclick="outreachRegenAllPending()"]');
    if ($btn) { $btn.disabled = true; $btn.dataset.origHtml = $btn.innerHTML; $btn.innerHTML = '<span class="animate-spin inline-block">🔄</span> Regenerating…'; }
    const res = await _api('POST', '/outreach/emails/batch-regenerate', { all_pending: true });
    if (res) {
      _showBanner(`🔄 ${res.regenerated || 0} emails regenerated (${res.errors || 0} errors)`, 'success');
      _loadPendingEmails();
    }
    if ($btn) { $btn.disabled = false; $btn.innerHTML = $btn.dataset.origHtml || '🔄 Regen All'; }
  };

  // ── Renderers (Light Mode panels) ───────────────────

  function _renderAgentStatus(data) {
    const $el = document.getElementById('outreach-agent-indicator');
    if (!$el) return;
    const icons = { running: '🟢', paused: '🟡', error: '🔴', idle: '⚪' };
    const icon = icons[data.status] || '❓';
    $el.innerHTML = `
      <div class="text-2xl">${icon}</div>
      <div>
        <div class="text-xs font-mono font-bold uppercase text-gray-200">${_esc(data.status || 'Unknown')}</div>
        <div id="outreach-agent-task" class="text-[0.6rem] font-mono text-gray-600 truncate max-w-[180px]">${_esc(data.current_ring || data.current_task || '')}</div>
      </div>`;
    // Also update Mission Control hero
    _mcOnAgentStatus(data);
  }

  function _renderKPIs(stats) {
    const sc = stats.status_counts || {};
    const items = [
      { id: 'kpi-prospects', icon: '📊', label: 'Prospects', val: stats.total_prospects || 0 },
      { id: 'kpi-audited', icon: '🔍', label: 'Audited', val: sc.audited || 0 },
      { id: 'kpi-enriched', icon: '🧬', label: 'Enriched', val: sc.enriched || 0 },
      { id: 'kpi-contacted', icon: '📧', label: 'Contacted', val: stats.total_contacted || 0 },
      { id: 'kpi-replied', icon: '⭐', label: 'Replied', val: `${stats.total_replied || 0} (${stats.reply_rate || 0}%)` },
      { id: 'kpi-meetings', icon: '📅', label: 'Meetings', val: stats.total_meetings || 0 },
    ];
    items.forEach(({ id, icon, label, val }) => {
      const $el = document.getElementById(id);
      if ($el) $el.innerHTML = `<span class="text-gray-500">${icon} ${label}</span> <span class="text-gray-200 font-mono">${val}</span>`;
    });
  }

  function _renderRingProgress(rings) {
    const $el = document.getElementById('outreach-ring-progress');
    if (!$el) return;
    const entries = Object.values(rings).sort((a, b) => (a.ring_number || 0) - (b.ring_number || 0));
    if (entries.length === 0) {
      $el.innerHTML = '<div class="text-xs text-gray-500 font-mono">No rings configured</div>';
      return;
    }
    $el.innerHTML = entries.map(r => {
      const pct = Math.round(r.pct || 0);
      const radius = r.radius_miles ? `${r.radius_miles} mi` : '';
      const found = r.businesses_found || 0;
      const statusIcon = r.status === 'complete' ? '✅' : r.status === 'active' || r.status === 'crawling' ? '🔵' : '⚪';
      return `
        <div class="mb-2" title="Ring ${r.ring_number || '?'}: ${radius} radius · ${found} businesses found · Status: ${r.status || 'unknown'}">
          <div class="flex justify-between text-xs font-mono mb-0.5">
            <span class="text-gray-400">${statusIcon} ${_esc(r.name || `Ring ${r.ring_number || '?'}`)} <span class="text-gray-600 text-[0.6rem]">(${radius})</span></span>
            <span class="text-gray-500">${pct}% · ${found} biz</span>
          </div>
          <div class="h-1.5 bg-gray-800 rounded-full overflow-hidden">
            <div class="h-full bg-electric rounded-full transition-all" style="width: ${pct}%"></div>
          </div>
        </div>`;
    }).join('');
  }

  function _renderActivityFeed(events) {
    const $el = document.getElementById('outreach-activity-feed');
    if (!$el) return;
    const arr = Object.values(events).sort((a, b) => (b.ts || 0) - (a.ts || 0)).slice(0, 20);
    if (arr.length === 0) {
      $el.innerHTML = '<div class="text-xs text-gray-500 font-mono py-4 text-center">No activity yet</div>';
      return;
    }
    $el.innerHTML = arr.map(e => `
      <div class="flex items-start gap-2 py-1.5 border-b border-gray-800/30 last:border-0">
        <span class="text-sm mt-0.5">${e.icon || '•'}</span>
        <div class="flex-1 min-w-0">
          <div class="text-xs text-gray-300 truncate">${_esc(e.text || '')}</div>
          <div class="text-xs text-gray-600">${_timeAgo(e.ts ? e.ts * 1000 : 0)}</div>
        </div>
      </div>
    `).join('');
  }

  function _renderAgentLog(entries) {
    const $el = document.getElementById('outreach-agent-log');
    if (!$el) return;
    const arr = Object.values(entries).sort((a, b) => (b.ts || 0) - (a.ts || 0)).slice(0, 50);
    if (arr.length === 0) {
      $el.innerHTML = '<div class="text-xs text-gray-500 font-mono py-4 text-center">No log entries</div>';
      return;
    }
    $el.innerHTML = arr.map(e => {
      const lvlClass = e.level === 'ERROR' ? 'text-red-400' : e.level === 'WARN' ? 'text-yellow-400' : 'text-gray-500';
      return `<div class="font-mono text-xs py-0.5"><span class="${lvlClass}">[${e.level || 'INFO'}]</span> <span class="text-gray-600">${_ts(e.ts)}</span> <span class="text-gray-400">${_esc(e.text || '')}</span></div>`;
    }).join('');
  }

  function _renderAlerts(alerts) {
    const arr = Object.values(alerts).sort((a, b) => (b.ts || 0) - (a.ts || 0));
    const unread = arr.filter(a => !a.read).length;

    // Badge
    const $badge = document.getElementById('outreach-alerts-badge');
    if ($badge) {
      $badge.textContent = unread > 0 ? unread : '';
      $badge.classList.toggle('hidden', unread === 0);
    }

    // Feed
    const $el = document.getElementById('outreach-alerts-feed');
    if (!$el) return;
    if (arr.length === 0) {
      $el.innerHTML = '<div class="text-xs text-gray-500 font-mono py-2 text-center">No alerts</div>';
      return;
    }
    const prioColors = { high: 'border-red-500/30 bg-red-500/5', medium: 'border-yellow-500/30 bg-yellow-500/5', low: 'border-gray-600/30 bg-gray-800/30' };
    $el.innerHTML = arr.slice(0, 10).map(a => `
      <div class="rounded-lg border p-2.5 mb-2 ${prioColors[a.priority] || prioColors.low} ${a.read ? 'opacity-60' : ''}">
        <div class="flex items-start gap-2">
          <span class="text-sm">${a.icon || '🔔'}</span>
          <div class="flex-1 min-w-0">
            <div class="text-xs font-semibold text-gray-200">${_esc(a.title || '')}</div>
            <div class="text-xs text-gray-400 mt-0.5">${_esc(a.detail || '')}</div>
            <div class="text-xs text-gray-600 mt-0.5">${_timeAgo(a.ts ? a.ts * 1000 : 0)}</div>
          </div>
        </div>
      </div>
    `).join('');
  }

  function _renderFunnel(data) {
    const $el = document.getElementById('outreach-funnel');
    if (!$el) return;
    const stages = [
      { key: 'discovered', label: 'Discovered', color: 'bg-gray-500' },
      { key: 'qualified', label: 'Qualified', color: 'bg-blue-500' },
      { key: 'contacted', label: 'Contacted', color: 'bg-indigo-500' },
      { key: 'opened', label: 'Opened', color: 'bg-purple-500' },
      { key: 'replied', label: 'Replied', color: 'bg-emerald-500' },
      { key: 'meeting', label: 'Meeting', color: 'bg-yellow-500' },
      { key: 'converted', label: 'Converted', color: 'bg-electric' },
    ];
    const maxVal = Math.max(...stages.map(s => data[s.key] || 0), 1);
    $el.innerHTML = stages.map(s => {
      const val = data[s.key] || 0;
      const pct = Math.round(val / maxVal * 100);
      return `
        <div class="flex items-center gap-2 mb-1.5">
          <span class="text-xs text-gray-400 w-20 text-right font-mono">${val}</span>
          <div class="flex-1 h-4 bg-gray-800 rounded overflow-hidden">
            <div class="${s.color} h-full rounded transition-all" style="width: ${pct}%"></div>
          </div>
          <span class="text-xs text-gray-500 w-20">${s.label}</span>
        </div>`;
    }).join('');
  }

  function _renderHotProspects(data) {
    const $el = document.getElementById('outreach-hot-prospects');
    if (!$el) return;
    const arr = Object.values(data);
    if (arr.length === 0) {
      $el.innerHTML = '<div class="text-xs text-gray-500 font-mono py-2 text-center">No hot leads yet</div>';
      return;
    }
    $el.innerHTML = arr.slice(0, 10).map((p, i) => `
      <div class="flex items-center gap-3 py-1.5 border-b border-gray-800/30 last:border-0">
        <span class="text-xs text-gray-600 font-mono w-4">${i + 1}.</span>
        <span class="text-xs text-gray-200 flex-1 truncate">${_esc(p.name || '—')}</span>
        <span class="text-xs font-mono ${_scoreColor(p.score)}">${Math.round(p.score || 0)}</span>
        <span class="text-xs text-gray-500">${_esc(p.status || '')}</span>
      </div>
    `).join('');
  }

  function _renderSparklines(snapshots) {
    const $el = document.getElementById('outreach-sparklines');
    if (!$el) return;
    const days = Object.entries(snapshots).sort(([a], [b]) => a.localeCompare(b));
    if (days.length === 0) {
      $el.innerHTML = '<div class="text-xs text-gray-500 font-mono py-2 text-center">No data yet</div>';
      return;
    }
    const metrics = ['sent', 'opened', 'replied'];
    const labels = { sent: '📧 Sent', opened: '👀 Opened', replied: '⭐ Replied' };
    $el.innerHTML = metrics.map(m => {
      const vals = days.map(([, d]) => d[m] || 0);
      const spark = _sparkline(vals);
      const last7 = vals.slice(-7).reduce((a, b) => a + b, 0);
      const prev7 = vals.slice(-14, -7).reduce((a, b) => a + b, 0);
      const delta = prev7 > 0 ? Math.round((last7 - prev7) / prev7 * 100) : (last7 > 0 ? 100 : 0);
      const deltaStr = delta >= 0 ? `↑ ${delta}%` : `↓ ${Math.abs(delta)}%`;
      const deltaColor = delta >= 0 ? 'text-emerald-400' : 'text-red-400';
      return `
        <div class="flex items-center gap-3 py-1">
          <span class="text-xs text-gray-400 w-20">${labels[m]}</span>
          <span class="text-sm font-mono text-gray-300 flex-1 tracking-widest">${spark}</span>
          <span class="text-xs ${deltaColor}">${deltaStr}</span>
        </div>`;
    }).join('');
  }

  function _sparkline(vals) {
    if (!vals.length) return '';
    const blocks = '▁▂▃▄▅▆▇█';
    const max = Math.max(...vals, 1);
    return vals.slice(-30).map(v => blocks[Math.min(Math.floor(v / max * 7), 7)]).join('');
  }

  function _renderWeeklyScorecard(scorecards) {
    const $el = document.getElementById('outreach-scorecard');
    if (!$el) return;
    const weeks = Object.entries(scorecards).sort(([a], [b]) => b.localeCompare(a));
    if (weeks.length === 0) {
      $el.innerHTML = '<div class="text-xs text-gray-500 font-mono py-2 text-center">No weekly data yet</div>';
      return;
    }
    const [, curr] = weeks[0];
    $el.innerHTML = `
      <div class="grid grid-cols-2 gap-2 text-xs font-mono">
        <div class="text-gray-400">📧 Sent</div><div class="text-gray-200">${curr.sent || 0} <span class="text-xs ${curr.delta_sent?.startsWith('+') ? 'text-emerald-400' : 'text-red-400'}">${_esc(curr.delta_sent || '')}</span></div>
        <div class="text-gray-400">👀 Opened</div><div class="text-gray-200">${curr.opened || 0}</div>
        <div class="text-gray-400">⭐ Replied</div><div class="text-gray-200">${curr.replied || 0} <span class="text-xs ${curr.delta_replied?.startsWith('+') ? 'text-emerald-400' : 'text-red-400'}">${_esc(curr.delta_replied || '')}</span></div>
        <div class="text-gray-400">🔍 Discovered</div><div class="text-gray-200">${curr.discovered || 0}</div>
      </div>`;
  }

  function _renderSendTimeHeatmap(heatmap) {
    const $el = document.getElementById('outreach-heatmap');
    if (!$el) return;
    const days = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'];
    const dayLabels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    const hours = [9, 10, 11, 12, 13, 14, 15, 16, 17];
    const hourLabels = ['9a', '10a', '11a', '12p', '1p', '2p', '3p', '4p', '5p'];

    if (!Object.keys(heatmap).length) {
      $el.innerHTML = '<div class="text-xs text-gray-500 font-mono py-2 text-center">No email data yet</div>';
      return;
    }

    let html = '<table class="w-full text-xs"><thead><tr><th></th>';
    hourLabels.forEach(h => html += `<th class="text-gray-600 font-normal px-1">${h}</th>`);
    html += '</tr></thead><tbody>';

    days.forEach((day, i) => {
      html += `<tr><td class="text-gray-500 pr-2 font-mono">${dayLabels[i]}</td>`;
      hours.forEach(h => {
        const cell = heatmap[day]?.[String(h)] || {};
        const replied = cell.replied || 0;
        const opened = cell.opened || 0;
        const dot = replied > 0 ? '🟢' : opened > 0 ? '🟡' : (cell.sent > 0 ? '⚪' : '·');
        html += `<td class="text-center px-1">${dot}</td>`;
      });
      html += '</tr>';
    });
    html += '</tbody></table>';
    $el.innerHTML = html;
  }

  function _renderTemplateLeaderboard(tplStats) {
    const $el = document.getElementById('outreach-templates');
    if (!$el) return;
    const entries = Object.entries(tplStats);
    if (entries.length === 0) {
      $el.innerHTML = '<div class="text-xs text-gray-500 font-mono py-2 text-center">No template data yet</div>';
      return;
    }
    $el.innerHTML = entries.map(([name, s]) => `
      <div class="flex items-center gap-2 py-1 border-b border-gray-800/30 last:border-0">
        <span class="text-xs text-gray-400 flex-1 truncate">${_esc(name.replace(/_/g, ' '))}</span>
        <span class="text-xs text-gray-500">${s.open_rate || 0}% open</span>
        <span class="text-xs font-mono ${s.reply_rate >= 5 ? 'text-emerald-400' : 'text-gray-400'}">${s.reply_rate || 0}% reply</span>
      </div>
    `).join('');
  }

  function _renderIndustryBreakdown(industries) {
    const $el = document.getElementById('outreach-industries');
    if (!$el) return;
    const arr = Object.values(industries);
    if (arr.length === 0) {
      $el.innerHTML = '<div class="text-xs text-gray-500 font-mono py-2 text-center">No industry data yet</div>';
      return;
    }
    const maxCount = Math.max(...arr.map(i => i.count || 0), 1);
    $el.innerHTML = arr.map(ind => {
      const pct = Math.round((ind.count || 0) / maxCount * 100);
      return `
        <div class="flex items-center gap-2 py-1">
          <span class="text-xs text-gray-400 w-24 truncate">${_esc(ind.name || '—')}</span>
          <div class="flex-1 h-2 bg-gray-800 rounded overflow-hidden">
            <div class="h-full bg-indigo-500/50 rounded" style="width: ${pct}%"></div>
          </div>
          <span class="text-xs font-mono text-gray-500">${ind.reply_rate || 0}%</span>
        </div>`;
    }).join('');
  }

  function _renderHealthTimeline(health) {
    const $el = document.getElementById('outreach-health');
    if (!$el) return;
    const arr = Object.values(health).sort((a, b) => (a.ts || 0) - (b.ts || 0));
    if (arr.length === 0) {
      $el.innerHTML = '<div class="text-xs text-gray-500 font-mono py-2 text-center">No health data yet</div>';
      return;
    }
    const cpuVals = arr.map(h => h.cpu_pct || 0);
    const memVals = arr.map(h => h.mem_mb || 0);
    const errVals = arr.map(h => h.errors_1h || 0);
    const avgCpu = Math.round(cpuVals.reduce((a, b) => a + b, 0) / cpuVals.length);
    const lastMem = memVals[memVals.length - 1] || 0;

    $el.innerHTML = `
      <div class="space-y-1 text-xs font-mono">
        <div class="flex items-center gap-2">
          <span class="text-gray-500 w-8">CPU</span>
          <span class="text-gray-400 flex-1 tracking-widest">${_sparkline(cpuVals)}</span>
          <span class="text-gray-500">avg ${avgCpu}%</span>
        </div>
        <div class="flex items-center gap-2">
          <span class="text-gray-500 w-8">Mem</span>
          <span class="text-gray-400 flex-1 tracking-widest">${_sparkline(memVals)}</span>
          <span class="text-gray-500">${lastMem} MB</span>
        </div>
        <div class="flex items-center gap-2">
          <span class="text-gray-500 w-8">Err</span>
          <span class="text-gray-400 flex-1 tracking-widest">${_sparkline(errVals)}</span>
          <span class="text-gray-500">${errVals.reduce((a, b) => a + b, 0)} total</span>
        </div>
      </div>`;
  }

  // ── Utility helpers ──────────────────────────────────
  function _esc(s) {
    if (!s) return '';
    const d = document.createElement('div');
    d.textContent = String(s);
    return d.innerHTML;
  }

  function _statusBadge(status) {
    const colors = {
      discovered: 'bg-gray-600/20 text-gray-400',
      audited: 'bg-blue-600/20 text-blue-400',
      enriched: 'bg-indigo-600/20 text-indigo-400',
      queued: 'bg-purple-600/20 text-purple-400',
      contacted: 'bg-cyan-600/20 text-cyan-400',
      follow_up_1: 'bg-cyan-600/20 text-cyan-300',
      follow_up_2: 'bg-cyan-600/20 text-cyan-300',
      follow_up_3: 'bg-cyan-600/20 text-cyan-300',
      replied: 'bg-emerald-600/20 text-emerald-400',
      meeting_booked: 'bg-yellow-600/20 text-yellow-400',
      promoted: 'bg-electric/20 text-electric',
      dead: 'bg-red-600/20 text-red-400',
      do_not_contact: 'bg-red-800/20 text-red-500',
      // Email statuses
      draft: 'bg-gray-600/20 text-gray-400',
      sent: 'bg-blue-600/20 text-blue-400',
      delivered: 'bg-indigo-600/20 text-indigo-400',
      opened: 'bg-emerald-600/20 text-emerald-400',
      clicked: 'bg-yellow-600/20 text-yellow-400',
      bounced: 'bg-red-600/20 text-red-400',
      failed: 'bg-red-600/20 text-red-400',
    };
    const cls = colors[status] || 'bg-gray-600/20 text-gray-400';
    return `<span class="px-2 py-0.5 rounded-full text-xs font-mono ${cls}">${_esc(status || 'unknown')}</span>`;
  }

  function _scoreColor(score) {
    if (score == null) return 'text-gray-500';
    if (score >= 70) return 'text-emerald-400';
    if (score >= 40) return 'text-yellow-400';
    return 'text-red-400';
  }

  function _timeAgo(ts) {
    if (!ts) return '';
    const diff = Date.now() - (typeof ts === 'number' ? ts : new Date(ts).getTime());
    const secs = Math.floor(diff / 1000);
    if (secs < 60) return 'just now';
    if (secs < 3600) return `${Math.floor(secs / 60)}m ago`;
    if (secs < 86400) return `${Math.floor(secs / 3600)}h ago`;
    return `${Math.floor(secs / 86400)}d ago`;
  }

  function _ts(epochSec) {
    if (!epochSec) return '';
    const d = new Date(epochSec * 1000);
    return d.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }

  function _renderAuditCard(audit) {
    if (!audit) return '';
    // Map raw audit fields to display names and scores
    const cards = [
      { label: 'Overall',     score: audit.composite_score },
      { label: 'Performance', score: audit.perf_score },
      { label: 'SEO',         score: audit.seo_score },
      { label: 'Design',      score: audit.design_score },
      { label: 'Security',    score: audit.security_score },
      { label: 'Mobile',      score: audit.mobile_score },
    ];
    const detailRows = [
      audit.cms_platform ? `<span class="px-2 py-0.5 bg-surface-2 border border-border rounded text-[0.6rem] text-gray-400">🛠 ${_esc(audit.cms_platform)}</span>` : '',
      audit.design_era ? `<span class="px-2 py-0.5 bg-surface-2 border border-border rounded text-[0.6rem] text-gray-400">🎨 ${_esc(audit.design_era)}</span>` : '',
      audit.ssl_valid != null ? `<span class="px-2 py-0.5 bg-surface-2 border border-border rounded text-[0.6rem] ${audit.ssl_valid ? 'text-emerald-400' : 'text-red-400'}">${audit.ssl_valid ? '🔒 SSL ✓' : '⚠️ No SSL'}</span>` : '',
      audit.mobile_friendly != null ? `<span class="px-2 py-0.5 bg-surface-2 border border-border rounded text-[0.6rem] ${audit.mobile_friendly ? 'text-emerald-400' : 'text-red-400'}">${audit.mobile_friendly ? '📱 Mobile ✓' : '📱 Not Mobile'}</span>` : '',
      audit.has_title === false ? `<span class="px-2 py-0.5 bg-red-500/10 border border-red-500/20 rounded text-[0.6rem] text-red-400">⚠ No Title</span>` : '',
      audit.has_meta_desc === false ? `<span class="px-2 py-0.5 bg-red-500/10 border border-red-500/20 rounded text-[0.6rem] text-red-400">⚠ No Meta Desc</span>` : '',
    ].filter(Boolean).join(' ');
    const sins = (audit.design_sins || []).slice(0, 3);
    return `
      <div class="grid grid-cols-3 gap-3 mb-3">
        ${cards.map(c => `
        <div class="bg-dark-card rounded-lg p-3 border border-gray-800/50 text-center">
          <div class="text-xs text-gray-500 mb-1">${c.label}</div>
          <div class="text-xl font-bold ${_scoreColor(c.score)}">${c.score ?? '—'}</div>
        </div>`).join('')}
      </div>
      ${detailRows ? `<div class="flex flex-wrap gap-1.5 mb-2">${detailRows}</div>` : ''}
      ${sins.length ? `<div class="text-[0.6rem] text-red-400/70">🚩 ${sins.map(s => _esc(s)).join(' · ')}</div>` : ''}
      ${audit.tech_stack && audit.tech_stack.length ? `<div class="text-[0.6rem] text-gray-600 mt-1">Tech: ${audit.tech_stack.slice(0,5).map(t => _esc(t)).join(', ')}</div>` : ''}`;
  }

  // ═══════════════════════════════════════════════════════
  // MISSION CONTROL — Sci-Fi Real-Time Effects
  // ═══════════════════════════════════════════════════════
  let _mcTimers = {};
  let _mcRunning = false;
  let _mcStartedAt = null;
  let _mcTerminalLines = [];
  const MC_MAX_TERMINAL_LINES = 80;

  // ── Simulated action vocabulary for terminal log ──
  const MC_ACTIONS = [
    { tag: 'CRAWL', cls: 'mc-tag-crawl', msgs: [
      'Scanning Google Maps API — "{biz}" sector',
      'Fetching results page {page} for "{cat}"',
      'Resolved {n} business listings in {city}',
      'Extracting contact details from {url}',
      'Processing Places API response batch #{batch}',
    ]},
    { tag: 'AUDIT', cls: 'mc-tag-audit', msgs: [
      'Lighthouse audit initiated → {url}',
      'Performance: {perf}/100 | SEO: {seo}/100 | Mobile: {mob}/100',
      'Screenshot captured → /data/screens/{slug}.png',
      'SSL cert valid until {date} ✓',
      'Detected {n} accessibility issues on {url}',
    ]},
    { tag: 'RECON', cls: 'mc-tag-recon', msgs: [
      'WHOIS lookup → domain registered {date}',
      'Tech stack: {tech}',
      'Social profiles found: {social}',
      'Enriching contact → {name} ({role})',
      'Revenue estimate: ${rev}/yr — priority score ↑{score}',
    ]},
    { tag: 'EMAIL', cls: 'mc-tag-email', msgs: [
      'Template "{tpl}" selected for {biz}',
      'Personalizing outreach → subject: "{subj}"',
      'Email queued → {email} (send window: {time})',
      'Follow-up #2 triggered for {biz}',
      'Bounce detected → {email} (MX: {mx})',
    ]},
    { tag: 'SCORE', cls: 'mc-tag-score', msgs: [
      'Composite score: {biz} → {score}/100',
      'Priority recalculated — {n} prospects re-ranked',
      'Hot lead threshold triggered → {biz} ({score})',
      'Decay applied: {n} stale prospects downranked',
    ]},
    { tag: 'RING', cls: 'mc-tag-ring', msgs: [
      'Expanding to Ring {ring} ({radius} mi radius)',
      'Ring {ring}: {n}/{total} categories scanned',
      'Ring {ring} complete — {n} new prospects discovered',
      'Geo-fence: {lat}°N, {lng}°W — {city}, {state}',
    ]},
  ];

  // Geo-ring cities: expanding outward from Manor, TX (Ring 0 → Ring 6)
  const MC_CITIES = ['Manor', 'Pflugerville', 'Round Rock', 'Hutto', 'Georgetown', 'Cedar Park', 'Austin', 'Leander', 'Taylor', 'Elgin', 'Bastrop', 'Kyle', 'San Marcos', 'Buda', 'Dripping Springs', 'Lockhart'];
  const MC_CATEGORIES = ['restaurants', 'dental clinics', 'law firms', 'auto repair', 'real estate', 'hair salons', 'yoga studios', 'pet grooming', 'chiropractors', 'plumbers', 'HVAC', 'landscaping'];
  const MC_BIZNAMES = ['Lone Star Plumbing', 'Bluebonnet Dental', 'Capitol Legal Group', 'Texas Auto Pros', 'Hill Country Salon', 'Austin Yoga Co', 'Pecan Street Chiro', 'Lone Star HVAC', 'Live Oak Landscaping', 'Manor Realty', 'Pflugerville Bakery', 'Round Rock Fitness', 'Cedar Park Pets', 'Hutto Family Dental', 'Georgetown Auto'];
  const MC_TECHS = ['WordPress 6.4', 'Shopify', 'Squarespace', 'Wix', 'Custom PHP', 'React + Next.js', 'HTML/CSS only', 'Webflow'];
  const MC_NAMES = ['Sarah Chen', 'Mike Torres', 'Jessica Wu', 'David Patel', 'Amanda Koch', 'Brian Nguyen', 'Rachel Hoffman'];
  // Coordinates: Manor TX center (30.3427, -97.5567) expanding outward through geo-rings
  const MC_COORDS = [
    [30.3427, -97.5567], [30.4436, -97.6200], [30.5083, -97.6789],  // Manor, Pflugerville, Round Rock
    [30.6274, -97.5469], [30.6338, -97.6772], [30.5151, -97.8203],  // Hutto, Georgetown, Cedar Park
    [30.2672, -97.7431], [30.5788, -97.8530], [30.5709, -97.4095],  // Austin, Leander, Taylor
    [30.3491, -97.3697], [30.1103, -97.3152], [29.8833, -97.9414],  // Elgin, Bastrop, San Marcos
    [30.0849, -97.8401], [30.3013, -97.8239], [30.0524, -97.7522],  // Buda, Dripping Springs, Kyle
    [29.8849, -97.6706],  // Lockhart
  ];

  function _mcRand(arr) { return arr[Math.floor(Math.random() * arr.length)]; }
  function _mcRandInt(min, max) { return Math.floor(Math.random() * (max - min + 1)) + min; }

  // Index for consuming real log items in order
  let _liveLogConsumeIdx = 0;
  let _pipelineLogSince = 0;  // Track last fetched timestamp for incremental polling
  let _pipelineLogQueue = []; // Queue of real log entries from API

  /** Fetch real pipeline logs from API (incremental) */
  async function _mcFetchPipelineLogs() {
    try {
      const res = await fetch(`${API_BASE}/outreach/pipeline/logs?since=${_pipelineLogSince}&limit=50`);
      if (!res.ok) return;
      const data = await res.json();
      if (data.logs && data.logs.length > 0) {
        for (const entry of data.logs) {
          _pipelineLogQueue.push(entry);
          if (entry.time && entry.time > _pipelineLogSince) {
            _pipelineLogSince = entry.time;
          }
        }
      }
    } catch { /* ignore — MC still works with simulated fallback */ }
  }

  function _mcGenerateLogLine() {
    // ── 1st priority: Real pipeline log entries from API ──
    if (_pipelineLogQueue.length > 0) {
      const entry = _pipelineLogQueue.shift();
      const tagClsMap = {
        SYS: 'mc-tag-sys', CRAWL: 'mc-tag-crawl', AUDIT: 'mc-tag-audit',
        RECON: 'mc-tag-recon', EMAIL: 'mc-tag-email', SCORE: 'mc-tag-score', RING: 'mc-tag-ring'
      };
      return {
        ts: entry.ts || new Date().toTimeString().slice(0, 8),
        tag: entry.tag || 'SYS',
        cls: tagClsMap[entry.tag] || 'mc-tag-sys',
        msg: entry.msg || 'Processing…',
      };
    }

    // ── 2nd priority: Real log data from Firebase ──
    if (_liveLogItems.length > 0 && _liveLogConsumeIdx < _liveLogItems.length) {
      const item = _liveLogItems[_liveLogConsumeIdx++];
      if (_liveLogConsumeIdx >= _liveLogItems.length) _liveLogConsumeIdx = 0;
      const tagMap = { crawl: 'CRAWL', audit: 'AUDIT', recon: 'RECON', email: 'EMAIL', score: 'SCORE', ring: 'RING', sys: 'SYS' };
      const clsMap = { crawl: 'mc-tag-crawl', audit: 'mc-tag-audit', recon: 'mc-tag-recon', email: 'mc-tag-email', score: 'mc-tag-score', ring: 'mc-tag-ring', sys: 'mc-tag-sys' };
      const logType = (item.type || 'sys').toLowerCase();
      return {
        ts: item.time || new Date().toTimeString().slice(0, 8),
        tag: tagMap[logType] || 'SYS',
        cls: clsMap[logType] || 'mc-tag-sys',
        msg: item.msg || item.text || item.detail || 'Processing…',
      };
    }

    // ── 3rd: Minimal "waiting" message (no more fake business data) ──
    const now = new Date();
    const ts = now.toTimeString().slice(0, 8);
    return { ts, tag: 'SYS', cls: 'mc-tag-sys', msg: 'Awaiting next pipeline cycle…' };
  }

  function _mcAppendTerminalLine(line) {
    const $body = document.getElementById('mc-terminal-body');
    if (!$body) return;
    _mcTerminalLines.push(line);
    if (_mcTerminalLines.length > MC_MAX_TERMINAL_LINES) _mcTerminalLines.shift();

    const lineHtml = `<div class="mc-log-line"><span class="mc-ts">${line.ts}</span> <span class="${line.cls}">[${line.tag}]</span> <span class="mc-msg">${_esc(line.msg)}</span></div>`;

    // Remove cursor from previous last line
    const existingCursor = $body.querySelector('.mc-cursor');
    if (existingCursor) existingCursor.remove();

    $body.insertAdjacentHTML('beforeend', lineHtml + '<span class="mc-cursor"></span>');

    // Auto-scroll to bottom
    $body.scrollTop = $body.scrollHeight;
  }

  function _mcUpdateUptime() {
    if (!_mcStartedAt) return;
    const $el = document.getElementById('mc-uptime');
    if (!$el) return;
    const diff = Math.floor((Date.now() - _mcStartedAt) / 1000);
    const h = String(Math.floor(diff / 3600)).padStart(2, '0');
    const m = String(Math.floor((diff % 3600) / 60)).padStart(2, '0');
    const s = String(diff % 60).padStart(2, '0');
    $el.textContent = `${h}:${m}:${s}`;
  }

  function _mcUpdateHeartbeat() {
    const $el = document.getElementById('mc-heartbeat');
    if (!$el) return;
    $el.style.color = $el.style.color === 'rgb(0, 212, 255)' ? '' : 'rgb(0, 212, 255)';
  }

  function _mcSpawnBlip() {
    const $blips = document.getElementById('mc-blips');
    if (!$blips) return;
    const angle = Math.random() * 360;
    const dist = 10 + Math.random() * 35;
    const x = 50 + dist * Math.cos(angle * Math.PI / 180) - 2;
    const y = 50 + dist * Math.sin(angle * Math.PI / 180) - 2;
    const blip = document.createElement('div');
    blip.className = 'mc-blip';
    blip.style.left = `${x}%`;
    blip.style.top = `${y}%`;
    blip.style.opacity = '1';
    blip.style.transition = 'opacity 3s';
    $blips.appendChild(blip);
    requestAnimationFrame(() => blip.style.opacity = '0');
    setTimeout(() => blip.remove(), 3200);
  }

  function _mcUpdateCoordTicker() {
    const $ticker = document.getElementById('mc-coord-ticker');
    if (!$ticker) return;
    const entries = [];

    // Use real activity data if available (show actual businesses/cities being crawled)
    if (_liveActivityItems.length > 0) {
      const seen = new Set();
      for (const item of _liveActivityItems) {
        if (entries.length >= 8) break;
        const name = item.name || item.text || '';
        const city = item.city || '';
        if (name && !seen.has(name)) {
          seen.add(name);
          const lat = item.lat ? parseFloat(item.lat).toFixed(4) : _mcRand(MC_COORDS)[0].toFixed(4);
          const lng = item.lng ? Math.abs(parseFloat(item.lng)).toFixed(4) : Math.abs(_mcRand(MC_COORDS)[1]).toFixed(4);
          const loc = city || _mcRand(MC_CITIES);
          entries.push(`${lat}°N ${lng}°W [${loc}: ${name}]`);
        }
      }
    }

    // Fill remaining slots with geo-ring cities (real expansion pattern)
    while (entries.length < 8) {
      const c = _mcRand(MC_COORDS);
      const city = _mcRand(MC_CITIES);
      const biz = _mcRand(MC_BIZNAMES);
      entries.push(`${c[0].toFixed(4)}°N ${Math.abs(c[1]).toFixed(4)}°W [${city}: ${biz}]`);
    }

    const text = entries.join('  ◆  ');
    $ticker.innerHTML = `<div class="mc-ticker-inner"><span>${text}  ◆  ${text}</span></div>`;
  }

  function _mcSetStatus(status) {
    const $dot = document.getElementById('mc-status-dot');
    const $dotSidebar = document.getElementById('outreach-sidebar-radar');
    const $text = document.getElementById('mc-status-text');
    const $hero = document.getElementById('mc-hero');

    if ($dot) {
      $dot.className = 'mc-dot ' + (status === 'running' ? '' : status === 'paused' ? 'paused' : status === 'error' ? 'error' : 'idle');
    }
    if ($text) {
      const labels = { running: 'SCANNING', paused: 'PAUSED', error: 'ERROR', idle: 'STANDBY' };
      $text.textContent = labels[status] || 'STANDBY';
      $text.style.color = status === 'running' ? '#00D4FF' : status === 'paused' ? '#FFD600' : status === 'error' ? '#FF6B6B' : '#555';
    }

    // Toggle active class on hero panel and radar
    const isActive = status === 'running';
    if ($hero) $hero.classList.toggle('mc-active', isActive);
    const $radar = document.getElementById('mc-radar');
    if ($radar) $radar.classList.toggle('mc-active', isActive);
    if ($dotSidebar) $dotSidebar.classList.toggle('mc-active', isActive);

    // Activate stat cards
    document.querySelectorAll('.mc-stat-card').forEach(el => el.classList.toggle('mc-active', isActive));
  }

  function _mcUpdateStats(stats) {
    const sc = stats.status_counts || {};
    const qualified = (sc.audited || 0) + (sc.enriched || 0) + (sc.queued || 0);
    const map = {
      'mc-stat-scanned': stats.total_prospects, 'mc-stat-scanned-m': stats.total_prospects,
      'mc-stat-qualified': qualified, 'mc-stat-qualified-m': qualified,
      'mc-stat-contacted': stats.total_contacted, 'mc-stat-contacted-m': stats.total_contacted,
      'mc-stat-replies': stats.total_replied, 'mc-stat-replies-m': stats.total_replied,
    };
    for (const [id, val] of Object.entries(map)) {
      const $el = document.getElementById(id);
      if ($el) $el.textContent = val || 0;
    }
  }

  function _startMissionControlEffects() {
    if (_mcRunning) return;
    _mcRunning = true;
    _mcStartedAt = Date.now();
    _mcSetStatus('running');

    // Clear terminal and add launch sequence
    const $body = document.getElementById('mc-terminal-body');
    if ($body) $body.innerHTML = '';
    const launchLines = [
      { ts: new Date().toTimeString().slice(0, 8), tag: 'SYS', cls: 'mc-tag-sys', msg: '▶ LAUNCH SEQUENCE INITIATED' },
      { ts: new Date().toTimeString().slice(0, 8), tag: 'SYS', cls: 'mc-tag-sys', msg: 'Connecting to Google Maps API…' },
      { ts: new Date().toTimeString().slice(0, 8), tag: 'SYS', cls: 'mc-tag-sys', msg: 'Loading geo-ring configuration…' },
      { ts: new Date().toTimeString().slice(0, 8), tag: 'SYS', cls: 'mc-tag-sys', msg: 'Intel engine online ✓  Recon engine online ✓' },
      { ts: new Date().toTimeString().slice(0, 8), tag: 'SYS', cls: 'mc-tag-sys', msg: 'Template engine loaded (5 templates)' },
      { ts: new Date().toTimeString().slice(0, 8), tag: 'RING', cls: 'mc-tag-ring', msg: 'Starting sweep — Ring 0 (5 mi radius)' },
    ];
    launchLines.forEach((l, i) => setTimeout(() => _mcAppendTerminalLine(l), i * 400));

    // Live log generation
    _mcTimers.log = setInterval(() => {
      _mcAppendTerminalLine(_mcGenerateLogLine());
    }, _mcRandInt(1800, 4000));

    // Poll real pipeline logs from API every 8 seconds
    _mcFetchPipelineLogs(); // Initial fetch
    _mcTimers.pipelineLogs = setInterval(_mcFetchPipelineLogs, 8000);

    // Uptime counter
    _mcTimers.uptime = setInterval(_mcUpdateUptime, 1000);

    // Heartbeat blink
    _mcTimers.heartbeat = setInterval(_mcUpdateHeartbeat, 800);

    // Radar blips
    _mcTimers.blip = setInterval(_mcSpawnBlip, _mcRandInt(1500, 3000));

    // Coord ticker
    _mcUpdateCoordTicker();
    _mcTimers.ticker = setInterval(_mcUpdateCoordTicker, 15000);
  }

  function _stopMissionControlEffects() {
    _mcRunning = false;
    for (const key of Object.keys(_mcTimers)) {
      clearInterval(_mcTimers[key]);
    }
    _mcTimers = {};

    // Add shutdown line to terminal
    const $body = document.getElementById('mc-terminal-body');
    if ($body) {
      const ts = new Date().toTimeString().slice(0, 8);
      _mcAppendTerminalLine({ ts, tag: 'SYS', cls: 'mc-tag-sys', msg: _agentStatus === 'paused' ? '⏸ AGENT PAUSED — awaiting resume' : '🛑 AGENT STOPPED' });
    }
    _mcSetStatus(_agentStatus);
  }

  // Connect MC to Firebase data
  function _mcOnAgentStatus(data) {
    const status = data.status || 'idle';
    _mcSetStatus(status);
    const $task = document.getElementById('mc-current-task');
    if ($task) $task.textContent = data.current_ring || data.current_task || '';

    if (status === 'running' && !_mcRunning) {
      _startMissionControlEffects();
    } else if (status !== 'running' && _mcRunning) {
      _stopMissionControlEffects();
    }
  }

  function _mcOnStats(stats) {
    _mcUpdateStats(stats);
  }

  // ── Public init (called by switchTab) ────────────────
  window.initOutreachTab = async function () {
    if (_initialized) return;
    _initialized = true;
    // Detect mode FIRST — this determines whether to use Firebase or localhost
    await detectMode();
    // THEN set up Firebase listeners (skips data listeners if API is available)
    _initFirebaseListeners();
    _modeCheckTimer = setInterval(detectMode, MODE_CHECK_INTERVAL);
  };

  window.destroyOutreachTab = function () {
    if (!_initialized) return;
    _initialized = false;
    _detachListeners();
    _stopMissionControlEffects();
    if (_modeCheckTimer) {
      clearInterval(_modeCheckTimer);
      _modeCheckTimer = null;
    }
  };

})();
