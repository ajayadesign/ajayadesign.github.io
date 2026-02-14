/* ═══════════════════════════════════════════════════════
   AjayaDesign Admin Dashboard — Client JS
   Firebase Auth, RTDB leads, SSE build streaming
   ═══════════════════════════════════════════════════════ */

// ── Configuration ──────────────────────────────────────
// Change this when Cloudflare Tunnel is set up:
//   e.g. 'https://api.ajayadesign.com'
const API_BASE = window.location.hostname === 'localhost'
  ? 'http://localhost:3456'
  : 'http://localhost:3456'; // TODO: replace with tunnel URL

const POLL_INTERVAL = 5000;
const ALLOWED_EMAIL = 'ajayadahal1000@gmail.com'; // Only this user can access admin

// ── State ──────────────────────────────────────────────
let selectedBuildId = null;
let eventSource = null;
let builds = [];
let currentStepData = { current: 0, total: 6 };
let aiEvents = [];
let logLines = [];
let pollTimer = null;
let leads = [];
let selectedLeadId = null;
let currentUser = null;

// ── Step definitions ───────────────────────────────────
const STEPS = [
  { key: 'repo',      label: 'Repo',      icon: '🏗️', short: 'Repo' },
  { key: 'council',   label: 'Council',   icon: '🏛️', short: 'Council' },
  { key: 'design',    label: 'Design',    icon: '🎨', short: 'Design' },
  { key: 'generate',  label: 'Generate',  icon: '🤖', short: 'Pages' },
  { key: 'assemble',  label: 'Assemble',  icon: '📎', short: 'Assemble' },
  { key: 'test',      label: 'Test',      icon: '🧪', short: 'Test' },
  { key: 'deploy',    label: 'Deploy',    icon: '🚀', short: 'Deploy' },
  { key: 'notify',    label: 'Notify',    icon: '📬', short: 'Notify' },
];

// ── DOM refs ───────────────────────────────────────────
const $buildList     = document.getElementById('build-list');
const $emptyState    = document.getElementById('empty-state');
const $buildDetail   = document.getElementById('build-detail');
const $buildHeader   = document.getElementById('build-header');
const $buildClient   = document.getElementById('build-client');
const $buildStatus   = document.getElementById('build-status-badge');
const $buildId       = document.getElementById('build-id-display');
const $buildTime     = document.getElementById('build-time');
const $buildMeta     = document.getElementById('build-meta');
const $stepProgress  = document.getElementById('step-progress');
const $aiPanel       = document.getElementById('ai-panel');
const $logPanel      = document.getElementById('log-panel');
const $logCount      = document.getElementById('log-count');
const $autoScroll    = document.getElementById('auto-scroll');

// Content tab panels
const $contentPipeline = document.getElementById('content-pipeline');
const $contentAI       = document.getElementById('content-ai');
const $contentLog      = document.getElementById('content-log');
let activeContentTab   = 'pipeline';
const $connDot       = document.getElementById('conn-dot');
const $connText      = document.getElementById('conn-text');
const $statTotal     = document.getElementById('stat-total');
const $statSuccess   = document.getElementById('stat-success');
const $statFailed    = document.getElementById('stat-failed');
const $loginScreen   = document.getElementById('login-screen');
const $loginBtn      = document.getElementById('google-login-btn');
const $loginError    = document.getElementById('login-error');

// ═══════════════════════════════════════════════════════
//  Firebase Auth
// ═══════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
  // Auth state listener
  window.__auth.onAuthStateChanged((user) => {
    if (user && user.email === ALLOWED_EMAIL) {
      currentUser = user;
      $loginScreen.classList.add('hidden');
      initDashboard();
    } else if (user) {
      // Wrong account — sign out and show error
      window.__auth.signOut();
      $loginError.textContent = `Access denied for ${user.email}. Only ${ALLOWED_EMAIL} can access this dashboard.`;
      $loginError.classList.remove('hidden');
      $loginScreen.classList.remove('hidden');
    } else {
      currentUser = null;
      $loginScreen.classList.remove('hidden');
    }
  });

  // Google sign-in button
  $loginBtn.addEventListener('click', async () => {
    try {
      const provider = new firebase.auth.GoogleAuthProvider();
      provider.setCustomParameters({ login_hint: ALLOWED_EMAIL });
      await window.__auth.signInWithPopup(provider);
    } catch (err) {
      console.error('[Admin] Login failed:', err);
      $loginError.textContent = `Login failed: ${err.message}`;
      $loginError.classList.remove('hidden');
    }
  });
});

function initDashboard() {
  refreshBuilds();
  pollTimer = setInterval(refreshBuilds, POLL_INTERVAL);
  checkConnection();
  subscribeToLeads();
}

// ── Tab switching ──────────────────────────────────────
function switchTab(tab) {
  const $tabBuilds = document.getElementById('tab-builds');
  const $tabLeads  = document.getElementById('tab-leads');
  const $buildsTab = document.getElementById('builds-tab');
  const $leadsPanel = document.getElementById('leads-panel');

  if (tab === 'leads') {
    $tabBuilds.className  = 'flex-1 py-3 text-xs font-mono font-semibold uppercase tracking-widest text-center border-b-2 border-transparent text-gray-500 hover:text-gray-300 transition';
    $tabLeads.className   = 'flex-1 py-3 text-xs font-mono font-semibold uppercase tracking-widest text-center border-b-2 border-electric text-electric transition';
    $buildsTab.classList.add('hidden');
    $leadsPanel.classList.remove('hidden');
    // Show lead detail if one was selected, otherwise empty state
    $buildDetail.classList.add('hidden');
    if (selectedLeadId) {
      $emptyState.classList.add('hidden');
      document.getElementById('lead-detail').classList.remove('hidden');
    } else {
      $emptyState.classList.remove('hidden');
      document.getElementById('lead-detail').classList.add('hidden');
    }
    renderLeadsPanel();
  } else {
    $tabBuilds.className  = 'flex-1 py-3 text-xs font-mono font-semibold uppercase tracking-widest text-center border-b-2 border-electric text-electric transition';
    $tabLeads.className   = 'flex-1 py-3 text-xs font-mono font-semibold uppercase tracking-widest text-center border-b-2 border-transparent text-gray-500 hover:text-gray-300 transition';
    $buildsTab.classList.remove('hidden');
    $leadsPanel.classList.add('hidden');
    // Show build detail if one was selected, otherwise empty state
    document.getElementById('lead-detail').classList.add('hidden');
    if (selectedBuildId) {
      $emptyState.classList.add('hidden');
      $buildDetail.classList.remove('hidden');
    } else {
      $emptyState.classList.remove('hidden');
    }
  }
}

// ── Content tab switching (Pipeline / AI / Log) ────────
function switchContentTab(tab) {
  activeContentTab = tab;
  const tabs = ['pipeline', 'ai', 'log'];
  tabs.forEach(t => {
    const $tab = document.getElementById('ctab-' + t);
    const $panel = document.getElementById('content-' + t);
    if (t === tab) {
      $tab.className = 'px-5 py-2.5 text-xs font-mono font-semibold uppercase tracking-widest border-b-2 border-electric text-electric transition';
      $panel.classList.remove('hidden');
    } else {
      $tab.className = 'px-5 py-2.5 text-xs font-mono font-semibold uppercase tracking-widest border-b-2 border-transparent text-gray-500 hover:text-gray-300 transition';
      $panel.classList.add('hidden');
    }
  });
}

// ── Connection check ───────────────────────────────────
async function checkConnection() {
  try {
    const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(3000) });
    if (res.ok) {
      $connDot.className = 'w-2 h-2 rounded-full bg-neon-green live-dot';
      $connText.textContent = 'Connected';
      $connText.className = 'text-neon-green';
    }
  } catch {
    $connDot.className = 'w-2 h-2 rounded-full bg-gray-600';
    $connText.textContent = 'Disconnected';
    $connText.className = 'text-gray-500';
  }
  setTimeout(checkConnection, 10000);
}

// ── Fetch build history ────────────────────────────────
async function refreshBuilds() {
  try {
    const res = await fetch(`${API_BASE}/builds`, { signal: AbortSignal.timeout(5000) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    builds = await res.json();
    renderBuildList();
    updateStats();
  } catch (err) {
    // Silently fail — might just be offline
    console.warn('[Admin] Failed to fetch builds:', err.message);
  }
}

function updateStats() {
  $statTotal.textContent = builds.length;
  $statSuccess.textContent = builds.filter(b => b.status === 'success').length;
  $statFailed.textContent = builds.filter(b => b.status === 'failed').length;
}

// ── Render build list ──────────────────────────────────
function renderBuildList() {
  if (builds.length === 0) {
    $buildList.innerHTML = `
      <div class="text-center py-8">
        <div class="text-3xl mb-2 opacity-30">📭</div>
        <div class="text-xs font-mono text-gray-600">No builds yet</div>
      </div>`;
    return;
  }

  $buildList.innerHTML = builds.map(b => {
    const isSelected = b.id === selectedBuildId;
    const statusIcon = b.status === 'running' ? '🔄' : b.status === 'success' ? '✅' : '❌';
    const statusClass = b.status === 'running' ? 'text-electric' : b.status === 'success' ? 'text-neon-green' : 'text-brand-link';
    const time = formatTime(b.started);
    const duration = b.finished ? formatDuration(b.started, b.finished) : b.status === 'running' ? 'running...' : '';

    return `
      <button onclick="selectBuild('${b.id}')"
        class="build-item w-full text-left p-3 rounded-lg border transition
          ${isSelected ? 'selected border-electric/30 bg-electric/5' : 'border-transparent hover:border-border'}">
        <div class="flex items-center justify-between mb-1">
          <span class="font-mono text-sm font-semibold text-white truncate max-w-[160px]">${esc(b.client || 'Unknown')}</span>
          <span class="text-xs ${statusClass}">${statusIcon}</span>
        </div>
        <div class="flex items-center justify-between">
          <span class="text-[0.65rem] font-mono text-gray-500">${b.id}</span>
          <span class="text-[0.65rem] text-gray-600">${time}</span>
        </div>
        ${duration ? `<div class="text-[0.65rem] text-gray-600 mt-1">⏱ ${duration}</div>` : ''}
        ${b.status === 'running' ? '<div class="mt-1.5 h-1 bg-surface-3 rounded-full overflow-hidden"><div class="h-full bg-electric rounded-full animate-pulse" style="width:60%"></div></div>' : ''}
      </button>`;
  }).join('');
}

// ── Select a build ─────────────────────────────────────
async function selectBuild(buildId) {
  selectedBuildId = buildId;
  renderBuildList(); // Update selection highlight

  // Close existing SSE
  if (eventSource) {
    eventSource.close();
    eventSource = null;
  }

  // Reset panels
  aiEvents = [];
  logLines = [];
  currentStepData = { current: 0, total: 6 };

  // Reset pipeline graph
  if (typeof resetPipeline === 'function') {
    resetPipeline();
    renderPipeline();
  }

  // Show detail panel
  $emptyState.classList.add('hidden');
  $buildDetail.classList.remove('hidden');
  document.getElementById('lead-detail').classList.add('hidden');

  // Fetch build details
  try {
    const res = await fetch(`${API_BASE}/builds/${buildId}`);
    const build = await res.json();

    // Populate header
    $buildClient.textContent = build.client || 'Unknown Client';
    $buildId.textContent = `#${build.id}`;
    $buildTime.textContent = formatTime(build.started);

    // Status badge
    const statusMap = {
      running: { text: 'RUNNING', cls: 'bg-electric/20 text-electric' },
      success: { text: 'SUCCESS', cls: 'bg-neon-green/20 text-neon-green' },
      failed:  { text: 'FAILED',  cls: 'bg-brand-link/20 text-brand-link' },
    };
    const s = statusMap[build.status] || { text: build.status, cls: 'bg-gray-800 text-gray-400' };
    $buildStatus.textContent = s.text;
    $buildStatus.className = `px-2.5 py-1 rounded-full text-xs font-mono font-semibold ${s.cls}`;

    // Meta
    const metas = [];
    if (build.niche) metas.push(`<span>🏷 ${esc(build.niche)}</span>`);
    if (build.email) metas.push(`<span>📧 ${esc(build.email)}</span>`);
    if (build.liveUrl) metas.push(`<a href="${build.liveUrl}" target="_blank" class="text-electric hover:underline">🔗 ${build.liveUrl}</a>`);
    $buildMeta.innerHTML = metas.join('');

    // Render initial step progress
    renderStepProgress(0);

    // Process existing log lines
    if (build.log && build.log.length > 0) {
      build.log.forEach(line => processLogLine(line, false));
      renderLog();
      renderAI();
      scrollLogToBottom();
    }

    // Open SSE for live updates (works for running AND completed builds)
    connectSSE(buildId);

  } catch (err) {
    console.error('[Admin] Failed to load build:', err);
    $logPanel.innerHTML = `<div class="text-brand-link">Failed to load build details: ${err.message}</div>`;
  }
}

// ── SSE Connection ─────────────────────────────────────
function connectSSE(buildId) {
  const url = `${API_BASE}/builds/${buildId}/stream`;
  eventSource = new EventSource(url);

  eventSource.onopen = () => {
    console.log('[Admin] SSE connected for build', buildId);
  };

  eventSource.addEventListener('log', (e) => {
    const data = JSON.parse(e.data);
    processLogLine(data.raw || data.line, true);
    // Feed to pipeline graph for metadata extraction
    if (typeof pipelineHandleLog === 'function') pipelineHandleLog(data.raw || data.line);
    renderLog();
    if ($autoScroll.checked) scrollLogToBottom();
  });

  eventSource.addEventListener('step', (e) => {
    const data = JSON.parse(e.data);
    currentStepData = { current: data.current, total: data.total };
    renderStepProgress(data.current);
    // Feed to pipeline graph
    if (typeof pipelineHandleStep === 'function') pipelineHandleStep(data);
    // Also add as log line
    processLogLine(data.raw || `[STEP:${data.current}:${data.total}:${data.stepName}] ${data.message}`, true);
    renderLog();
    if ($autoScroll.checked) scrollLogToBottom();
  });

  eventSource.addEventListener('ai', (e) => {
    const data = JSON.parse(e.data);
    aiEvents.push(data);
    renderAI();
    // Feed to pipeline graph
    if (typeof pipelineHandleAI === 'function') pipelineHandleAI(data);
  });

  eventSource.addEventListener('test', (e) => {
    const data = JSON.parse(e.data);
    // Add to AI panel as well for visibility
    aiEvents.push({ ...data, type: 'test' });
    renderAI();
    // Feed to pipeline graph
    if (typeof pipelineHandleTest === 'function') pipelineHandleTest(data);
    processLogLine(data.raw || `[TEST:${data.action}] ${data.message}`, true);
    renderLog();
    if ($autoScroll.checked) scrollLogToBottom();
  });

  eventSource.addEventListener('done', (e) => {
    const data = JSON.parse(e.data);
    // Update header status
    const s = data.status === 'success'
      ? { text: 'SUCCESS', cls: 'bg-neon-green/20 text-neon-green' }
      : { text: 'FAILED', cls: 'bg-brand-link/20 text-brand-link' };
    $buildStatus.textContent = s.text;
    $buildStatus.className = `px-2.5 py-1 rounded-full text-xs font-mono font-semibold ${s.cls}`;

    if (data.status === 'success') renderStepProgress(6);
    // Feed to pipeline graph
    if (typeof pipelineHandleDone === 'function') pipelineHandleDone(data);
    refreshBuilds();
    eventSource.close();
  });

  eventSource.addEventListener('catch-up-done', () => {
    // All historical lines have been sent; now receiving live data
    console.log('[Admin] Catch-up complete, streaming live');
  });

  eventSource.onerror = () => {
    console.warn('[Admin] SSE error/closed');
    // Don't auto-reconnect for completed builds
    setTimeout(() => {
      const build = builds.find(b => b.id === buildId);
      if (build && build.status === 'running') {
        connectSSE(buildId);
      }
    }, 3000);
  };
}

// ── Process a log line ─────────────────────────────────
function processLogLine(line, isLive) {
  if (!line) return;

  // Deduplicate
  if (logLines.length > 0 && logLines[logLines.length - 1].raw === line) return;

  const entry = { raw: line, cssClass: 'text-gray-400' };

  // Classify
  if (/\[STEP:\d+:\d+:\w+\]/.test(line)) {
    entry.cssClass = 'log-step';
    // Parse step
    const m = line.match(/\[STEP:(\d+):(\d+)/);
    if (m) {
      currentStepData = { current: parseInt(m[1]), total: parseInt(m[2]) };
      if (!isLive) renderStepProgress(currentStepData.current);
    }
  } else if (/\[AI:/.test(line)) {
    entry.cssClass = 'log-ai';
    // Also add to AI events
    const m = line.match(/\[AI:(\w+)(?::(\d+))?\]\s*(.*)/);
    if (m) {
      aiEvents.push({
        type: 'ai',
        action: m[1].toLowerCase(),
        attempt: m[2] ? parseInt(m[2]) : undefined,
        message: m[3],
        timestamp: new Date().toISOString(),
      });
    }
  } else if (/\[TEST:PASS/.test(line)) {
    entry.cssClass = 'log-test-pass';
  } else if (/\[TEST:FAIL/.test(line)) {
    entry.cssClass = 'log-test-fail';
  } else if (/\[TEST:/.test(line)) {
    entry.cssClass = 'text-neon-yellow';
    // Add test events to AI panel
    const m = line.match(/\[TEST:(\w+)(?::(\d+))?\]\s*(.*)/);
    if (m) {
      aiEvents.push({
        type: 'test',
        action: m[1].toLowerCase(),
        attempt: m[2] ? parseInt(m[2]) : undefined,
        message: m[3],
        timestamp: new Date().toISOString(),
      });
    }
  } else if (/\[DEPLOY\]/.test(line)) {
    entry.cssClass = 'log-deploy';
  } else if (/STDERR:|❌|Error|error/.test(line)) {
    entry.cssClass = 'log-error';
  } else if (/✅/.test(line)) {
    entry.cssClass = 'log-test-pass';
  } else if (/⚠️/.test(line)) {
    entry.cssClass = 'text-neon-orange';
  }

  logLines.push(entry);
}

// ── Render functions ───────────────────────────────────

function renderStepProgress(current) {
  $stepProgress.innerHTML = STEPS.map((step, i) => {
    const num = i + 1;
    const isDone = num < current;
    const isActive = num === current;
    const isPending = num > current;

    let dotClass = 'w-9 h-9 rounded-full flex items-center justify-center text-sm font-mono font-bold transition-all duration-300 ';
    if (isDone) dotClass += 'bg-neon-green/20 text-neon-green step-dot done';
    else if (isActive) dotClass += 'bg-electric/20 text-electric step-dot active border-2 border-electric';
    else dotClass += 'bg-surface-3 text-gray-600 step-dot';

    const connector = i < STEPS.length - 1
      ? `<div class="flex-1 h-0.5 mx-1 rounded step-connector ${isDone ? 'bg-neon-green/40' : isActive ? 'bg-electric/30' : 'bg-surface-3'}"></div>`
      : '';

    return `
      <div class="flex items-center ${i < STEPS.length - 1 ? 'flex-1' : ''}">
        <div class="flex flex-col items-center">
          <div class="${dotClass}">
            ${isDone ? '✓' : step.icon}
          </div>
          <span class="text-[0.6rem] font-mono mt-1 ${isActive ? 'text-electric' : isDone ? 'text-neon-green/60' : 'text-gray-600'}">${step.short}</span>
        </div>
        ${connector}
      </div>`;
  }).join('');
}

function renderLog() {
  const html = logLines.map((entry, i) => {
    return `<div class="log-line ${entry.cssClass} py-0.5 px-2 rounded">${escHTML(entry.raw)}</div>`;
  }).join('');
  if ($logPanel) $logPanel.innerHTML = html || '<div class="text-gray-600">Waiting for build output...</div>';
  if ($logCount) $logCount.textContent = logLines.length;
}

function renderAI() {
  if (aiEvents.length === 0) {
    $aiPanel.innerHTML = '<div class="text-center text-gray-600 text-xs font-mono py-8">No AI activity yet</div>';
    return;
  }

  const html = aiEvents.map(ev => {
    if (ev.type === 'test') {
      const icon = ev.action === 'pass' ? '✅' : ev.action === 'fail' ? '❌' : '🧪';
      const color = ev.action === 'pass' ? 'border-neon-green/30 bg-neon-green/5' : ev.action === 'fail' ? 'border-brand-link/30 bg-brand-link/5' : 'border-neon-yellow/30 bg-neon-yellow/5';
      return `
        <div class="ai-bubble rounded-lg border ${color} p-3">
          <div class="flex items-center gap-2 mb-1">
            <span>${icon}</span>
            <span class="font-mono text-xs font-semibold text-gray-300">Test ${ev.action?.toUpperCase() || ''}${ev.attempt ? ` #${ev.attempt}` : ''}</span>
          </div>
          <p class="text-xs text-gray-400">${escHTML(ev.message || '')}</p>
        </div>`;
    }

    // AI events
    const actionConfig = {
      call:     { icon: '📡', label: 'API Call',    color: 'border-neon-purple/30 bg-neon-purple/5' },
      done:     { icon: '✨', label: 'Generated',   color: 'border-neon-green/30 bg-neon-green/5' },
      fix:      { icon: '🔧', label: 'Auto-Fix',    color: 'border-neon-orange/30 bg-neon-orange/5' },
      prompt:   { icon: '💬', label: 'Prompt',       color: 'border-electric/30 bg-electric/5' },
      response: { icon: '🤖', label: 'Response',     color: 'border-neon-purple/30 bg-neon-purple/5' },
      error:    { icon: '⚠️', label: 'API Error',    color: 'border-brand-link/30 bg-brand-link/5' },
      fallback: { icon: '📄', label: 'Fallback',     color: 'border-neon-yellow/30 bg-neon-yellow/5' },
    };
    const cfg = actionConfig[ev.action] || { icon: '🔵', label: ev.action || 'AI', color: 'border-border bg-surface-2' };

    return `
      <div class="ai-bubble rounded-lg border ${cfg.color} p-3">
        <div class="flex items-center gap-2 mb-1">
          <span>${cfg.icon}</span>
          <span class="font-mono text-xs font-semibold text-gray-300">${cfg.label}${ev.attempt ? ` #${ev.attempt}` : ''}</span>
          ${ev.timestamp ? `<span class="text-[0.6rem] text-gray-600 ml-auto">${new Date(ev.timestamp).toLocaleTimeString()}</span>` : ''}
        </div>
        <p class="text-xs text-gray-400 break-words">${escHTML(ev.message || '')}</p>
      </div>`;
  }).join('');

  if ($aiPanel) $aiPanel.innerHTML = html;
}

function scrollLogToBottom() {
  requestAnimationFrame(() => {
    // Scroll the log container
    const $logContainer = document.getElementById('content-log');
    if ($logContainer) $logContainer.scrollTop = $logContainer.scrollHeight;
    // Also scroll AI panel
    const $aiContainer = document.getElementById('content-ai');
    if ($aiContainer) $aiContainer.scrollTop = $aiContainer.scrollHeight;
  });
}

// ── Helpers ────────────────────────────────────────────

function esc(str) {
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
const escHTML = esc;

function formatTime(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) + ' ' +
    d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
}

function formatDuration(startIso, endIso) {
  if (!startIso || !endIso) return '';
  const ms = new Date(endIso) - new Date(startIso);
  const sec = Math.floor(ms / 1000);
  if (sec < 60) return `${sec}s`;
  const min = Math.floor(sec / 60);
  const remSec = sec % 60;
  return `${min}m ${remSec}s`;
}

// ── Keyboard shortcut: R to refresh ────────────────────
document.addEventListener('keydown', (e) => {
  if (e.key === 'r' && !e.ctrlKey && !e.metaKey && document.activeElement.tagName !== 'INPUT') {
    refreshBuilds();
  }
});

// ═══════════════════════════════════════════════════════
//  Firebase RTDB — Real-time leads
// ═══════════════════════════════════════════════════════
function subscribeToLeads() {
  if (!window.__db) return;
  window.__db.ref('leads').orderByChild('timestamp').on('value', (snapshot) => {
    leads = [];
    snapshot.forEach((child) => {
      leads.push({ id: child.key, ...child.val() });
    });
    leads.reverse(); // newest first
    renderLeadStats();
    // If leads tab is visible, re-render
    if (document.getElementById('leads-panel') && !document.getElementById('leads-panel').classList.contains('hidden')) {
      renderLeadsPanel();
    }
  });
}

function renderLeadStats() {
  const $statLeads = document.getElementById('stat-leads');
  if ($statLeads) $statLeads.textContent = leads.length;
}

function renderLeadsPanel() {
  const panel = document.getElementById('leads-panel-content');
  if (!panel) return;

  if (leads.length === 0) {
    panel.innerHTML = `
      <div class="text-center py-12">
        <div class="text-4xl mb-3 opacity-30">📭</div>
        <p class="text-gray-500 font-mono text-sm">No leads yet</p>
        <p class="text-gray-600 text-xs mt-1">Submissions from the intake form will appear here</p>
      </div>`;
    return;
  }

  panel.innerHTML = leads.map(lead => {
    const statusColors = {
      'new':         'bg-electric/20 text-electric',
      'contacted':   'bg-neon-yellow/20 text-neon-yellow',
      'building':    'bg-neon-purple/20 text-neon-purple',
      'deployed':    'bg-neon-green/20 text-neon-green',
      'archived':    'bg-gray-800 text-gray-500',
    };
    const statusCls = statusColors[lead.status] || statusColors['new'];
    const time = lead.submitted_at ? formatTime(lead.submitted_at) : 'Unknown date';
    const isSelected = lead.id === selectedLeadId;

    return `
      <div onclick="selectLead('${lead.id}')" class="p-4 bg-surface-2 rounded-xl border cursor-pointer transition animate-fade-in
        ${isSelected ? 'border-electric bg-electric/5' : 'border-border hover:border-border-glow'}">
        <div class="flex items-center justify-between mb-3">
          <h3 class="font-mono text-sm font-bold text-white">${esc(lead.business_name || 'Unknown')}</h3>
          <div class="flex items-center gap-2" onclick="event.stopPropagation()">
            <select onchange="updateLeadStatus('${lead.id}', this.value)"
              class="text-[0.65rem] font-mono px-2 py-1 rounded-full border-0 cursor-pointer ${statusCls}">
              ${['new','contacted','building','deployed','archived'].map(s =>
                `<option value="${s}" ${lead.status === s ? 'selected' : ''} class="bg-surface text-gray-300">${s.toUpperCase()}</option>`
              ).join('')}
            </select>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-2 text-xs mb-3">
          <div><span class="text-gray-600">Niche:</span> <span class="text-gray-400">${esc(lead.niche || '-')}</span></div>
          <div><span class="text-gray-600">Email:</span> <span class="text-gray-400">${esc(lead.email || '-')}</span></div>
        </div>
        <p class="text-xs text-gray-500 mb-3">${esc(lead.goals || '-')}</p>
        <div class="flex items-center justify-between">
          <span class="text-[0.65rem] text-gray-600">${time}</span>
          <span class="text-[0.65rem] text-gray-600 font-mono">${lead.source || 'direct'}</span>
        </div>
      </div>`;
  }).join('');
}

function updateLeadStatus(leadId, newStatus) {
  if (!window.__db) return;
  window.__db.ref(`leads/${leadId}/status`).set(newStatus)
    .then(() => {
      console.log(`[Admin] Lead ${leadId} → ${newStatus}`);
      // If this lead is selected, refresh its detail view
      if (leadId === selectedLeadId) renderLeadDetail();
    })
    .catch(err => console.error('[Admin] Failed to update lead:', err));
}

// ── Select a lead ──────────────────────────────────────
function selectLead(leadId) {
  selectedLeadId = leadId;
  renderLeadsPanel(); // Update selection highlight

  // Hide other main panels, show lead detail
  document.getElementById('empty-state').classList.add('hidden');
  document.getElementById('build-detail').classList.add('hidden');
  document.getElementById('lead-detail').classList.remove('hidden');

  renderLeadDetail();
}

function renderLeadDetail() {
  const lead = leads.find(l => l.id === selectedLeadId);
  if (!lead) return;

  const statusColors = {
    'new':       { cls: 'bg-electric/20 text-electric',       text: 'NEW' },
    'contacted': { cls: 'bg-neon-yellow/20 text-neon-yellow', text: 'CONTACTED' },
    'building':  { cls: 'bg-neon-purple/20 text-neon-purple', text: 'BUILDING' },
    'deployed':  { cls: 'bg-neon-green/20 text-neon-green',   text: 'DEPLOYED' },
    'archived':  { cls: 'bg-gray-800 text-gray-500',          text: 'ARCHIVED' },
  };
  const s = statusColors[lead.status] || statusColors['new'];

  // Badge
  const $badge = document.getElementById('lead-status-badge');
  $badge.textContent = s.text;
  $badge.className = `px-2.5 py-1 rounded-full text-xs font-mono font-semibold ${s.cls}`;

  // Header
  document.getElementById('lead-business').textContent = lead.business_name || 'Unknown';

  // Status dropdown
  document.getElementById('lead-status-select').value = lead.status || 'new';

  // Meta
  const metas = [];
  if (lead.niche)  metas.push(`<span>🏷 ${esc(lead.niche)}</span>`);
  if (lead.email)  metas.push(`<span>📧 ${esc(lead.email)}</span>`);
  if (lead.source) metas.push(`<span>🌐 ${esc(lead.source)}</span>`);
  document.getElementById('lead-meta').innerHTML = metas.join('');

  // Content
  document.getElementById('lead-goals').textContent = lead.goals || 'No goals specified';
  document.getElementById('lead-email').textContent = lead.email || '-';
  document.getElementById('lead-niche').textContent = lead.niche || '-';
  document.getElementById('lead-time').textContent = lead.submitted_at ? formatTime(lead.submitted_at) : 'Unknown';
  document.getElementById('lead-source').textContent = lead.source || 'direct';

  // Email link
  if (lead.email) {
    const subject = encodeURIComponent(`AjayaDesign — Your website for ${lead.business_name || 'your business'}`);
    document.getElementById('lead-email-link').href = `mailto:${lead.email}?subject=${subject}`;
  }
}

function updateLeadStatusFromDetail(newStatus) {
  if (!selectedLeadId) return;
  updateLeadStatus(selectedLeadId, newStatus);
}

function triggerBuildForLead() {
  const lead = leads.find(l => l.id === selectedLeadId);
  if (!lead) return;

  if (!confirm(`Trigger a build for "${lead.business_name}"?`)) return;

  // Update status to building
  updateLeadStatus(selectedLeadId, 'building');

  // POST to runner
  fetch(`${API_BASE}/build`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      business_name: lead.business_name,
      niche: lead.niche,
      goals: lead.goals,
      email: lead.email,
    }),
  })
    .then(res => res.json())
    .then(data => {
      console.log('[Admin] Build triggered:', data);
      // Switch to builds tab and select the new build
      switchTab('builds');
      if (data.id) {
        setTimeout(() => selectBuild(data.id), 1000);
      }
      refreshBuilds();
    })
    .catch(err => {
      console.error('[Admin] Failed to trigger build:', err);
      alert(`Failed to trigger build: ${err.message}`);
    });
}

function archiveLead() {
  if (!selectedLeadId) return;
  const lead = leads.find(l => l.id === selectedLeadId);
  if (!lead) return;
  if (!confirm(`Archive lead "${lead.business_name}"?`)) return;
  updateLeadStatus(selectedLeadId, 'archived');
}

// ── Sign out ───────────────────────────────────────────
function signOut() {
  if (window.__auth) window.__auth.signOut();
}
