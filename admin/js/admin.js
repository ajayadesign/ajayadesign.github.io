/* ═══════════════════════════════════════════════════════
   AjayaDesign Admin Dashboard — Client JS
   Firebase Auth, RTDB leads, SSE build streaming
   ═══════════════════════════════════════════════════════ */

// ── Configuration ──────────────────────────────────────
// Change this when Cloudflare Tunnel is set up:
//   e.g. 'https://api.ajayadesign.com'
// API_BASE points to the local Docker API.
// When the admin is opened remotely (e.g. GitHub Pages), API calls will fail
// gracefully and fall back to Firebase RTDB commands that the server polls for.
const API_BASE = 'http://localhost:3001/api/v1';

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
let leadsSubTab = 'active'; // 'active' or 'archived'

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
  initConnectionMonitor();
  subscribeToLeads();
  subscribeToBuildsFirebase();
  if (typeof loadPortfolio === 'function') loadPortfolio();
}

// ── Tab switching ──────────────────────────────────────
function switchTab(tab) {
  const $tabBuilds = document.getElementById('tab-builds');
  const $tabLeads  = document.getElementById('tab-leads');
  const $tabPortfolio = document.getElementById('tab-portfolio');
  const $tabHistory = document.getElementById('tab-history');
  const $tabAnalytics = document.getElementById('tab-analytics');
  const $tabTraffic = document.getElementById('tab-traffic');
  const $buildsTab = document.getElementById('builds-tab');
  const $leadsPanel = document.getElementById('leads-panel');
  const $portfolioPanel = document.getElementById('portfolio-panel');
  const $historyPanel = document.getElementById('history-panel');
  const $analyticsSidebar = document.getElementById('analytics-sidebar');
  const $trafficSidebar = document.getElementById('traffic-sidebar');

  const inactiveClass = 'flex-1 py-3 text-xs font-mono font-semibold uppercase tracking-widest text-center border-b-2 border-transparent text-gray-500 hover:text-gray-300 transition';
  const activeClass   = 'flex-1 py-3 text-xs font-mono font-semibold uppercase tracking-widest text-center border-b-2 border-electric text-electric transition';

  // Reset all tabs to inactive
  $tabBuilds.className = inactiveClass;
  $tabLeads.className  = inactiveClass;
  if ($tabPortfolio) $tabPortfolio.className = inactiveClass;
  if ($tabHistory) $tabHistory.className = inactiveClass;
  if ($tabAnalytics) $tabAnalytics.className = inactiveClass;
  if ($tabTraffic) $tabTraffic.className = inactiveClass;

  // Hide all sidebar panels
  $buildsTab.classList.add('hidden');
  $leadsPanel.classList.add('hidden');
  if ($portfolioPanel) $portfolioPanel.classList.add('hidden');
  if ($historyPanel) $historyPanel.classList.add('hidden');
  if ($analyticsSidebar) $analyticsSidebar.classList.add('hidden');
  if ($trafficSidebar) $trafficSidebar.classList.add('hidden');

  // Hide all main panels
  $buildDetail.classList.add('hidden');
  document.getElementById('lead-detail').classList.add('hidden');
  const $portfolioDetail = document.getElementById('portfolio-detail');
  const $contractDetail  = document.getElementById('contract-detail');
  const $invoiceDetail   = document.getElementById('invoice-detail');
  const $analyticsPanel  = document.getElementById('analytics-panel');
  const $trafficPanel    = document.getElementById('traffic-panel');
  if ($portfolioDetail) $portfolioDetail.classList.add('hidden');
  if ($contractDetail)  $contractDetail.classList.add('hidden');
  if ($invoiceDetail)   $invoiceDetail.classList.add('hidden');
  if ($analyticsPanel)  $analyticsPanel.classList.add('hidden');
  if ($trafficPanel)    $trafficPanel.classList.add('hidden');

  if (tab === 'leads') {
    $tabLeads.className = activeClass;
    $leadsPanel.classList.remove('hidden');
    if (selectedLeadId) {
      $emptyState.classList.add('hidden');
      document.getElementById('lead-detail').classList.remove('hidden');
    } else {
      $emptyState.classList.remove('hidden');
    }
    renderLeadsPanel();
  } else if (tab === 'portfolio') {
    if ($tabPortfolio) $tabPortfolio.className = activeClass;
    if ($portfolioPanel) $portfolioPanel.classList.remove('hidden');
    if (typeof selectedPortfolioId !== 'undefined' && selectedPortfolioId) {
      $emptyState.classList.add('hidden');
      if ($portfolioDetail) $portfolioDetail.classList.remove('hidden');
    } else {
      $emptyState.classList.remove('hidden');
    }
    if (typeof loadPortfolio === 'function') loadPortfolio();
  } else if (tab === 'history') {
    if ($tabHistory) $tabHistory.className = activeClass;
    if ($historyPanel) $historyPanel.classList.remove('hidden');
    $emptyState.classList.remove('hidden');
    if (typeof loadActivityLog === 'function') loadActivityLog();
  } else if (tab === 'analytics') {
    if ($tabAnalytics) $tabAnalytics.className = activeClass;
    if ($analyticsSidebar) $analyticsSidebar.classList.remove('hidden');
    $emptyState.classList.add('hidden');
    if ($analyticsPanel) $analyticsPanel.classList.remove('hidden');
    if (typeof refreshAnalytics === 'function') refreshAnalytics();
  } else if (tab === 'traffic') {
    if ($tabTraffic) $tabTraffic.className = activeClass;
    if ($trafficSidebar) $trafficSidebar.classList.remove('hidden');
    $emptyState.classList.add('hidden');
    if ($trafficPanel) $trafficPanel.classList.remove('hidden');
    if (typeof refreshTraffic === 'function') refreshTraffic();
  } else {
    // builds (default)
    $tabBuilds.className = activeClass;
    $buildsTab.classList.remove('hidden');
    if (selectedBuildId) {
      $emptyState.classList.add('hidden');
      $buildDetail.classList.remove('hidden');
    } else {
      $emptyState.classList.remove('hidden');
    }
  }

  // ── Sync mobile bottom tab bar ──
  document.querySelectorAll('#mobile-tab-bar .mobile-tab').forEach(el => {
    el.classList.remove('text-electric');
    el.classList.add('text-gray-500');
  });
  const $mtab = document.getElementById('mtab-' + tab);
  if ($mtab) { $mtab.classList.remove('text-gray-500'); $mtab.classList.add('text-electric'); }

  // ── Auto-close sidebar on tab switch (mobile only) ──
  if (window.innerWidth < 768) {
    const sb = document.getElementById('sidebar');
    if (sb && sb.classList.contains('translate-x-0')) {
      toggleMobileSidebar();
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
  // On mobile, open the slide-up panel when a tab is tapped
  if (window.innerWidth < 768) sheetSnapTo('half');
}

// ═══════════════════════════════════════════════════════
//  Mobile bottom-sheet — 3-state gesture-driven drawer
//  States: peek (tabs only) → half (~50%) → full (~90%)
// ═══════════════════════════════════════════════════════

const SHEET_STATES = ['peek', 'half', 'full'];
let _sheetState = 'peek';          // current snap state
let _sheetDragging = false;
let _sheetStartY = 0;
let _sheetStartH = 0;
let _sheetVelocity = 0;
let _sheetLastY = 0;
let _sheetLastTime = 0;
let _sheetInitialized = false;

/** Heights (px) for each state — computed once on init */
function _sheetHeights() {
  const navH = 48;  // h-12 bottom nav
  const safeBottom = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--safe-area-bottom') || '0') || 0;
  const available = window.innerHeight - navH - safeBottom;
  const handleH = document.getElementById('content-handle')?.offsetHeight || 16;
  const dotsH = document.getElementById('sheet-dots')?.offsetHeight || 15;
  const tabsH = document.querySelector('#content-wrapper .sheet-tabs')?.offsetHeight || 42;
  const peekH = handleH + dotsH + tabsH + 2;  // show handle + dots + tabs
  return {
    peek: Math.min(peekH, available * 0.15),
    half: available * 0.50,
    full: available * 0.90,
    max: available
  };
}

function _sheetHeight(state) {
  return _sheetHeights()[state] || _sheetHeights().peek;
}

/** Update the three indicator dots */
function _sheetUpdateDots(state) {
  const dots = document.querySelectorAll('#sheet-dots .dot');
  if (!dots.length) return;
  const idx = SHEET_STATES.indexOf(state);
  dots.forEach((d, i) => d.classList.toggle('active', i === idx));
}

/** Update overlay visibility */
function _sheetUpdateOverlay(state) {
  const overlay = document.getElementById('content-overlay');
  if (!overlay) return;
  if (state === 'peek') {
    overlay.classList.add('hidden');
    overlay.classList.remove('visible', 'fading');
  } else {
    overlay.classList.remove('hidden', 'fading');
    overlay.classList.add('visible');
  }
}

/** Snap the sheet to a state with spring animation */
function sheetSnapTo(state, skipGlow) {
  if (window.innerWidth >= 768) return;  // desktop: no-op
  const wrap = document.getElementById('content-wrapper');
  if (!wrap) return;

  _initSheet();

  const h = _sheetHeight(state);
  _sheetState = state;

  // Prevent body scroll when sheet is expanded
  document.body.style.overflow = (state === 'peek') ? '' : 'hidden';

  // Animate
  wrap.classList.remove('sheet-dragging');
  wrap.classList.add('sheet-animating');
  wrap.style.height = h + 'px';

  _sheetUpdateDots(state);
  _sheetUpdateOverlay(state);

  // Clean up animation class after transition
  const cleanup = () => {
    wrap.classList.remove('sheet-animating');
    wrap.removeEventListener('transitionend', cleanup);
  };
  wrap.addEventListener('transitionend', cleanup, { once: true });
  setTimeout(cleanup, 400);  // fallback
}

/** Keep old names working for onclick handlers in HTML */
function openContentPanel() { sheetSnapTo('half'); }
function closeContentPanel() { sheetSnapTo('peek'); }

/** Init gesture tracking — called once */
function _initSheet() {
  if (_sheetInitialized || window.innerWidth >= 768) return;
  _sheetInitialized = true;

  const wrap = document.getElementById('content-wrapper');
  const handle = document.getElementById('content-handle');
  const tabsBar = document.querySelector('#content-wrapper .sheet-tabs');
  if (!wrap) return;

  // Set initial peek height
  requestAnimationFrame(() => {
    wrap.style.height = _sheetHeight('peek') + 'px';
    _sheetUpdateDots('peek');
  });

  // ── Touch events on handle AND tabs bar ──
  const touchTargets = [handle, tabsBar].filter(Boolean);
  touchTargets.forEach(target => {
    target.addEventListener('touchstart', _onSheetTouchStart, { passive: true });
    target.addEventListener('touchmove', _onSheetTouchMove, { passive: false });
    target.addEventListener('touchend', _onSheetTouchEnd, { passive: true });
  });

  // Also allow dragging from the top edge of content areas
  wrap.addEventListener('touchstart', (e) => {
    // Only start drag from within ~20px of the top of the sheet body
    const bodyEl = wrap.querySelector('.sheet-body');
    if (!bodyEl) return;
    // If body is scrolled to top and swiping down, take over
    if (bodyEl.scrollTop <= 0 && _sheetState !== 'peek') {
      // Will handle in touchmove if direction is down
      _sheetEdgeDragReady = true;
      _sheetEdgeDragStartY = e.touches[0].clientY;
    }
  }, { passive: true });

  wrap.addEventListener('touchmove', (e) => {
    if (!_sheetEdgeDragReady) return;
    const dy = e.touches[0].clientY - _sheetEdgeDragStartY;
    if (dy > 10 && !_sheetDragging) {
      // Swiping down from scroll-top → start sheet drag
      _sheetStartY = e.touches[0].clientY;
      _sheetStartH = wrap.offsetHeight;
      _sheetLastY = _sheetStartY;
      _sheetLastTime = Date.now();
      _sheetDragging = true;
      wrap.classList.add('sheet-dragging');
      wrap.classList.remove('sheet-animating');
    }
    if (_sheetDragging) {
      e.preventDefault();
      _onSheetDrag(e.touches[0].clientY, wrap);
    }
  }, { passive: false });

  wrap.addEventListener('touchend', (e) => {
    _sheetEdgeDragReady = false;
    if (_sheetDragging) {
      _onSheetRelease(wrap);
    }
  }, { passive: true });
}

let _sheetEdgeDragReady = false;
let _sheetEdgeDragStartY = 0;

function _onSheetTouchStart(e) {
  const wrap = document.getElementById('content-wrapper');
  if (!wrap) return;
  const t = e.touches[0];
  _sheetStartY = t.clientY;
  _sheetStartH = wrap.offsetHeight;
  _sheetLastY = t.clientY;
  _sheetLastTime = Date.now();
  _sheetVelocity = 0;
  _sheetDragging = true;
  wrap.classList.add('sheet-dragging');
  wrap.classList.remove('sheet-animating');
}

function _onSheetTouchMove(e) {
  if (!_sheetDragging) return;
  e.preventDefault();
  const wrap = document.getElementById('content-wrapper');
  if (!wrap) return;
  _onSheetDrag(e.touches[0].clientY, wrap);
}

function _onSheetDrag(currentY, wrap) {
  const dy = _sheetStartY - currentY;  // positive = dragging up
  const heights = _sheetHeights();
  let newH = Math.max(heights.peek * 0.5, Math.min(heights.max, _sheetStartH + dy));

  // Rubber-band effect past limits
  if (newH > heights.full) {
    const over = newH - heights.full;
    newH = heights.full + over * 0.15;
  }

  wrap.style.height = newH + 'px';

  // Track velocity
  const now = Date.now();
  const dt = now - _sheetLastTime;
  if (dt > 0) {
    _sheetVelocity = (currentY - _sheetLastY) / dt;  // px/ms, negative = up
  }
  _sheetLastY = currentY;
  _sheetLastTime = now;

  // Update dots based on current height proximity
  const mid1 = (heights.peek + heights.half) / 2;
  const mid2 = (heights.half + heights.full) / 2;
  if (newH < mid1) _sheetUpdateDots('peek');
  else if (newH < mid2) _sheetUpdateDots('half');
  else _sheetUpdateDots('full');

  // Update overlay opacity proportionally
  const overlay = document.getElementById('content-overlay');
  if (overlay) {
    const progress = Math.max(0, Math.min(1, (newH - heights.peek) / (heights.half - heights.peek)));
    if (progress > 0.05) {
      overlay.classList.remove('hidden');
      overlay.style.opacity = Math.min(1, progress);
    } else {
      overlay.classList.add('hidden');
    }
  }
}

function _onSheetTouchEnd(e) {
  if (!_sheetDragging) return;
  const wrap = document.getElementById('content-wrapper');
  if (!wrap) return;
  _onSheetRelease(wrap);
}

function _onSheetRelease(wrap) {
  _sheetDragging = false;
  wrap.classList.remove('sheet-dragging');

  const currentH = wrap.offsetHeight;
  const heights = _sheetHeights();
  const v = _sheetVelocity;  // px/ms — negative = swiped up

  // Fling detection: fast swipe overrides position
  const FLING_THRESHOLD = 0.4;  // px/ms
  let target;

  if (Math.abs(v) > FLING_THRESHOLD) {
    // Fast swipe
    if (v < 0) {
      // Swiped UP → go to next higher state
      if (_sheetState === 'peek') target = 'half';
      else target = 'full';
    } else {
      // Swiped DOWN → go to next lower state
      if (_sheetState === 'full') target = 'half';
      else target = 'peek';
    }
  } else {
    // Slow drag — snap to nearest
    const distances = SHEET_STATES.map(s => ({
      state: s,
      dist: Math.abs(currentH - _sheetHeight(s))
    }));
    distances.sort((a, b) => a.dist - b.dist);
    target = distances[0].state;
  }

  sheetSnapTo(target);
}

/** Flash the sheet border to attract attention (called when a build is selected) */
function sheetGlow() {
  if (window.innerWidth >= 768) return;
  const wrap = document.getElementById('content-wrapper');
  if (!wrap) return;
  _initSheet();
  wrap.classList.remove('sheet-glow');
  void wrap.offsetWidth;  // force reflow
  wrap.classList.add('sheet-glow');
  setTimeout(() => wrap.classList.remove('sheet-glow'), 3100);
}

/** Re-compute sheet heights on resize/orientation change */
window.addEventListener('resize', () => {
  if (_sheetInitialized && window.innerWidth < 768) {
    const wrap = document.getElementById('content-wrapper');
    if (wrap) {
      wrap.style.height = _sheetHeight(_sheetState) + 'px';
    }
  }
  // Reset init if crossing breakpoint
  if (window.innerWidth >= 768) {
    const wrap = document.getElementById('content-wrapper');
    if (wrap) {
      wrap.style.height = '';
      wrap.classList.remove('sheet-dragging', 'sheet-animating', 'sheet-glow');
    }
    _sheetInitialized = false;
    document.body.style.overflow = '';
  }
});

// ── Connection check (Firebase-first, API fallback) ───
let firebaseConnected = false;
let apiConnected = false;

function initConnectionMonitor() {
  // Firebase real-time connection status
  if (window.__db) {
    window.__db.ref('.info/connected').on('value', (snap) => {
      firebaseConnected = !!snap.val();
      updateConnectionUI();
    });
  }
  // Also check Python API periodically (for build streaming)
  checkApiConnection();
}

async function checkApiConnection() {
  try {
    const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(3000) });
    apiConnected = res.ok;
  } catch {
    apiConnected = false;
  }
  updateConnectionUI();
  setTimeout(checkApiConnection, 15000);
}

function updateConnectionUI() {
  if (apiConnected) {
    $connDot.className = 'w-2 h-2 rounded-full bg-neon-green live-dot';
    $connText.textContent = 'Build System Online';
    $connText.className = 'text-neon-green';
  } else if (firebaseConnected) {
    $connDot.className = 'w-2 h-2 rounded-full bg-electric live-dot';
    $connText.textContent = 'Connected';
    $connText.className = 'text-electric';
  } else {
    $connDot.className = 'w-2 h-2 rounded-full bg-gray-600';
    $connText.textContent = 'Offline';
    $connText.className = 'text-gray-500';
  }
}

// ── Fetch build history (API-first, Firebase RTDB fallback) ──
async function refreshBuilds() {
  let loaded = false;
  try {
    const res = await fetch(`${API_BASE}/builds`, { signal: AbortSignal.timeout(5000) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    builds = (data.builds || []).map(b => ({
      id: b.short_id,
      client: b.client_name,
      status: b.status === 'complete' ? 'success' : b.status,
      niche: b.niche,
      email: b.email,
      started: b.created_at || b.started_at,
      finished: b.finished_at,
      liveUrl: b.live_url,
      protected: !!b.protected,
      repoFull: b.repo_full || '',
    }));
    loaded = true;
  } catch (err) {
    console.warn('[Admin] API builds fetch failed:', err.message);
  }

  // Fallback: read from Firebase RTDB when API is unreachable
  if (!loaded && window.__db) {
    try {
      const snap = await window.__db.ref('builds').orderByChild('created_at').limitToLast(50).once('value');
      const fbBuilds = [];
      snap.forEach((child) => {
        const b = child.val();
        fbBuilds.push({
          id: child.key,
          client: b.client_name || b.clientName || 'Unknown',
          status: b.status === 'complete' ? 'success' : b.status,
          niche: b.niche || '',
          email: b.email || '',
          started: b.created_at || b.started_at,
          finished: b.finished_at,
          liveUrl: b.live_url || '',
        });
      });
      fbBuilds.reverse();
      if (fbBuilds.length > 0) {
        builds = fbBuilds;
        loaded = true;
        console.info('[Admin] Loaded %d builds from Firebase', builds.length);
      }
    } catch (fbErr) {
      console.warn('[Admin] Firebase builds fallback failed:', fbErr.message);
    }
  }

  renderBuildList();
  updateStats();
}

function updateStats() {
  $statTotal.textContent = builds.length;
  $statSuccess.textContent = builds.filter(b => b.status === 'success' || b.status === 'complete').length;
  $statFailed.textContent = builds.filter(b => b.status === 'failed' || b.status === 'stalled').length;
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
    const isSuccess = b.status === 'success' || b.status === 'complete';
    const isStalled = b.status === 'stalled';
    const statusIcon = b.status === 'queued' ? '⏳' : b.status === 'running' ? '🔄' : isStalled ? '⚠️' : isSuccess ? '✅' : '❌';
    const statusClass = b.status === 'queued' ? 'text-gray-500' : b.status === 'running' ? 'text-electric' : isStalled ? 'text-neon-orange' : isSuccess ? 'text-neon-green' : 'text-brand-link';
    const lockIcon = b.protected ? '<span title="Protected" class="text-neon-yellow">🔒</span>' : '';
    const time = formatTime(b.started);
    const duration = b.finished ? formatDuration(b.started, b.finished) : b.status === 'running' ? 'running...' : '';

    return `
      <button onclick="selectBuild('${b.id}')"
        class="build-item w-full text-left p-3 rounded-lg border transition
          ${isSelected ? 'selected border-electric/30 bg-electric/5' : 'border-transparent hover:border-border'}">
        <div class="flex items-center justify-between mb-1">
          <span class="font-mono text-sm font-semibold text-white truncate max-w-[160px]">${esc(b.client || 'Unknown')}</span>
          <span class="text-xs flex items-center gap-1">${lockIcon}<span class="${statusClass}">${statusIcon}</span></span>
        </div>
        <div class="flex items-center justify-between">
          <span class="text-[0.65rem] font-mono text-gray-500">${b.id}</span>
          <span class="text-[0.65rem] text-gray-600">${time}</span>
        </div>
        ${duration ? `<div class="text-[0.65rem] text-gray-600 mt-1">⏱ ${duration}</div>` : ''}
        ${b.status === 'running' ? '<div class="mt-1.5 h-1 bg-surface-3 rounded-full overflow-hidden"><div class="h-full bg-electric rounded-full animate-pulse" style="width:60%"></div></div>' : ''}
        ${isStalled ? '<div class="text-[0.6rem] text-neon-orange mt-1">⚠️ Interrupted — tap to retry</div>' : ''}
      </button>`;
  }).join('');
}

// ── Select a build ─────────────────────────────────────
let _firebaseBuildRef = null;  // Active Firebase listener for build detail
let _firebaseLogRef = null;    // Active Firebase listener for log lines
let _seenLogKeys = new Set();  // Dedup: tracks seen log sequence numbers or message fingerprints

async function selectBuild(buildId) {
  selectedBuildId = buildId;
  renderBuildList(); // Update selection highlight

  // Close existing SSE and Firebase listeners
  if (eventSource) { eventSource.close(); eventSource = null; }
  _detachFirebaseBuildListeners();

  // Reset panels
  aiEvents = [];
  logLines = [];
  _seenLogKeys = new Set();
  currentStepData = { current: 0, total: 8 };

  // Immediately render the empty state so stale content from the previous build is cleared
  renderLog();
  renderAI();

  // Reset pipeline graph
  if (typeof resetPipeline === 'function') {
    resetPipeline();
    renderPipeline();
  }

  // Show detail panel
  $emptyState.classList.add('hidden');
  $buildDetail.classList.remove('hidden');
  document.getElementById('lead-detail').classList.add('hidden');

  // Mobile: initialize sheet & glow to attract attention
  if (window.innerWidth < 768) {
    _initSheet();
    setTimeout(sheetGlow, 300);
  }

  // ── Strategy: Try API first, fall back to Firebase ──
  let loaded = false;

  try {
    const res = await fetch(`${API_BASE}/builds/${buildId}`, { signal: AbortSignal.timeout(5000) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const build = await res.json();
    _populateBuildHeader(build);

    // Process existing log lines from API
    if (build.log && build.log.length > 0) {
      build.log.forEach(line => processLogLine(line, false));
      renderLog();
      renderAI();
      scrollLogToBottom();
    }

    // Hydrate pipeline graph from stored phases (works for completed/failed builds)
    if (build.phases && build.phases.length > 0) {
      _hydrateFromPhases(build.phases, build.status);
    }

    // Populate extra pipeline context from build metadata
    if (build.client_name) {
      pipeline.clientName = build.client_name;
      pipeline.niche = build.niche || '';
      pipeline.liveUrl = build.live_url || '';
      if (pipeline.nodes.request.status === 'done') {
        pipeline.nodes.request.detail = build.client_name;
      }
      if (build.live_url && pipeline.nodes.deploy.status === 'done') {
        pipeline.nodes.deploy.detail = 'GitHub Pages live';
      }
      if (typeof renderPipeline === 'function') renderPipeline();
    }

    // SSE for live updates when API is reachable
    connectSSE(buildId);
    loaded = true;

  } catch (err) {
    console.warn('[Admin] API unavailable, using Firebase for build:', err.message);
  }

  // Always attach Firebase listener for real-time updates (primary in prod)
  _attachFirebaseBuildListeners(buildId, !loaded);
}

/** Populate the build detail header from build data (works with both API and Firebase shapes). */
function _populateBuildHeader(build) {
  $buildClient.textContent = build.client_name || build.clientName || 'Unknown Client';
  $buildId.textContent = `#${build.short_id || build.shortId || selectedBuildId}`;
  $buildTime.textContent = formatTime(build.created_at || build.started_at || build.createdAt);

  _updateBuildStatusBadge(build.status);

  // Show/hide retry button for stalled or failed builds
  const $retryBtn = document.getElementById('build-retry-btn');
  if ($retryBtn) {
    if (build.status === 'stalled' || build.status === 'failed') {
      $retryBtn.classList.remove('hidden');
    } else {
      $retryBtn.classList.add('hidden');
    }
  }

  // Show protect/delete buttons
  _updateProtectDeleteButtons(build);

  const metas = [];
  if (build.niche) metas.push(`<span>🏷 ${esc(build.niche)}</span>`);
  if (build.email) metas.push(`<span>📧 ${esc(build.email)}</span>`);
  const liveUrl = build.live_url || build.liveUrl;
  if (liveUrl) metas.push(`<a href="${liveUrl}" target="_blank" class="text-electric hover:underline">🔗 ${liveUrl}</a>`);
  $buildMeta.innerHTML = metas.join('');

  renderStepProgress(0);
}

function _updateBuildStatusBadge(status) {
  const displayStatus = status === 'complete' ? 'success' : status;
  const statusMap = {
    queued:  { text: 'QUEUED',  cls: 'bg-gray-800 text-gray-400' },
    running: { text: 'RUNNING', cls: 'bg-electric/20 text-electric' },
    success: { text: 'SUCCESS', cls: 'bg-neon-green/20 text-neon-green' },
    complete:{ text: 'SUCCESS', cls: 'bg-neon-green/20 text-neon-green' },
    stalled: { text: 'STALLED', cls: 'bg-neon-orange/20 text-neon-orange' },
    failed:  { text: 'FAILED',  cls: 'bg-brand-link/20 text-brand-link' },
  };
  const s = statusMap[displayStatus] || { text: (status || '').toUpperCase(), cls: 'bg-gray-800 text-gray-400' };
  $buildStatus.textContent = s.text;
  $buildStatus.className = `px-2.5 py-1 rounded-full text-xs font-mono font-semibold ${s.cls}`;
}

/** Retry a stalled or failed build — tries API first, falls back to Firebase RTDB. */
async function retryBuild() {
  if (!selectedBuildId) return;

  const $btn = document.getElementById('build-retry-btn');
  if ($btn) {
    $btn.disabled = true;
    $btn.textContent = '⏳ Retrying...';
  }

  let apiOk = false;

  // ── Attempt 1: direct API call ──
  try {
    const res = await fetch(`${API_BASE}/builds/${selectedBuildId}/retry`, {
      method: 'POST',
      signal: AbortSignal.timeout(10000),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    apiOk = true;
  } catch (err) {
    console.warn('[Admin] API retry failed, trying Firebase fallback:', err.message);
  }

  // ── Attempt 2: Firebase RTDB command (picked up by server-side poller) ──
  if (!apiOk && window.__db) {
    try {
      const cmdRef = window.__db.ref('commands/retry').push();
      await cmdRef.set({
        build_id: selectedBuildId,
        status: 'pending',
        requested_at: new Date().toISOString(),
        requested_by: currentUser ? currentUser.email : 'admin',
      });
      console.info('[Admin] Retry command written to Firebase — server will pick it up');
      apiOk = true; // treat as success; server-side will process
    } catch (fbErr) {
      console.error('[Admin] Firebase retry fallback also failed:', fbErr);
      alert(`Retry failed: API unreachable and Firebase write failed.\n${fbErr.message}`);
      if ($btn) { $btn.disabled = false; $btn.textContent = '🔄 Retry Build'; }
      return;
    }
  }

  if (!apiOk) {
    alert('Retry failed: API unreachable and Firebase is not connected.');
    if ($btn) { $btn.disabled = false; $btn.textContent = '🔄 Retry Build'; }
    return;
  }

  // ── Success path — reset UI ──
  if (typeof resetPipeline === 'function') {
    resetPipeline();
    renderPipeline();
  }

  aiEvents = [];
  logLines = [];
  renderLog();
  renderAI();

  _updateBuildStatusBadge('queued');
  if ($btn) { $btn.classList.add('hidden'); }

  // Reconnect SSE for the retried build
  if (eventSource) { eventSource.close(); eventSource = null; }
  connectSSE(selectedBuildId);

  // Refresh build list
  setTimeout(refreshBuilds, 1000);
}

/** Update the protect & delete button states in the build detail header. */
function _updateProtectDeleteButtons(build) {
  const $protectBtn = document.getElementById('build-protect-btn');
  const $deleteBtn  = document.getElementById('build-delete-btn');
  const isProtected = !!(build.protected);
  const isRunning = build.status === 'running' || build.status === 'queued';

  // Always show protect button for completed/stalled/failed builds
  if ($protectBtn) {
    if (!isRunning) {
      $protectBtn.classList.remove('hidden');
      if (isProtected) {
        $protectBtn.textContent = '🔒 Protected';
        $protectBtn.className = 'px-3 py-1 rounded-lg text-xs font-mono font-semibold bg-neon-yellow/20 text-neon-yellow border border-neon-yellow/30 hover:bg-neon-yellow/30 transition';
        $protectBtn.title = 'Click to unprotect (allow deletion)';
      } else {
        $protectBtn.textContent = '🔓 Unprotected';
        $protectBtn.className = 'px-3 py-1 rounded-lg text-xs font-mono font-semibold bg-gray-800 text-gray-400 border border-gray-700 hover:bg-gray-700 transition';
        $protectBtn.title = 'Click to protect (prevent deletion)';
      }
    } else {
      $protectBtn.classList.add('hidden');
    }
  }

  // Show delete button only for unprotected, non-running builds
  if ($deleteBtn) {
    if (!isProtected && !isRunning) {
      $deleteBtn.classList.remove('hidden');
    } else {
      $deleteBtn.classList.add('hidden');
    }
  }
}

/** Toggle build protection (lock/unlock). */
async function toggleProtection() {
  if (!selectedBuildId) return;

  const $btn = document.getElementById('build-protect-btn');
  if ($btn) { $btn.disabled = true; $btn.textContent = '⏳...'; }

  let apiOk = false;

  // ── Attempt 1: direct API call ──
  try {
    const res = await fetch(`${API_BASE}/builds/${selectedBuildId}/protect`, {
      method: 'PATCH',
      signal: AbortSignal.timeout(10000),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    const data = await res.json();

    // Update local build state
    const build = builds.find(b => b.id === selectedBuildId);
    if (build) build.protected = data.protected;

    // Update UI
    _updateProtectDeleteButtons({ protected: data.protected, status: build?.status || 'complete' });
    renderBuildList();
    apiOk = true;
  } catch (err) {
    console.warn('[Admin] API protect toggle failed, trying Firebase fallback:', err.message);
  }

  // ── Attempt 2: Firebase RTDB command (server picks it up on next poll / startup) ──
  if (!apiOk && window.__db) {
    try {
      const cmdRef = window.__db.ref('commands/protect').push();
      await cmdRef.set({
        build_id: selectedBuildId,
        status: 'pending',
        requested_at: new Date().toISOString(),
        requested_by: currentUser ? currentUser.email : 'admin',
      });
      console.info('[Admin] Protect command written to Firebase — server will pick it up');
      alert('Server unreachable — protection toggle queued. It will apply when the server comes back online.');
      apiOk = true;
    } catch (fbErr) {
      console.error('[Admin] Firebase protect fallback also failed:', fbErr);
      alert(`Toggle protection failed: API unreachable and Firebase write failed.\n${fbErr.message}`);
    }
  }

  if (!apiOk && !window.__db) {
    alert('Toggle protection failed: API unreachable and Firebase is not connected.');
  }

  if ($btn) $btn.disabled = false;
}

/** Delete a build — confirms, calls API, cleans up GitHub repo + submodule. */
async function deleteBuild() {
  if (!selectedBuildId) return;

  const build = builds.find(b => b.id === selectedBuildId);
  if (!build) return;

  if (build.protected) {
    alert('This build is protected. Unprotect it first before deleting.');
    return;
  }

  const name = build.client || 'this build';
  const repo = build.repoFull || '';
  const msg = `⚠️ DELETE BUILD: "${name}" (${selectedBuildId})\n\n`
    + `This will permanently:\n`
    + `• Remove from database\n`
    + (repo ? `• Delete GitHub repo: ${repo}\n` : '')
    + `• Remove git submodule\n`
    + `• Remove from Firebase\n\n`
    + `Type "DELETE" to confirm:`;

  const input = prompt(msg);
  if (input !== 'DELETE') {
    if (input !== null) alert('Deletion cancelled. You must type DELETE to confirm.');
    return;
  }

  const $btn = document.getElementById('build-delete-btn');
  if ($btn) { $btn.disabled = true; $btn.textContent = '⏳ Deleting...'; }

  let apiOk = false;

  // ── Attempt 1: direct API call ──
  try {
    const res = await fetch(`${API_BASE}/builds/${selectedBuildId}`, {
      method: 'DELETE',
      signal: AbortSignal.timeout(60000), // submodule cleanup may take time
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    const data = await res.json();

    // Show result
    let resultMsg = `✅ Build "${data.client_name}" deleted.`;
    if (data.repo_deleted) resultMsg += `\n📦 GitHub repo deleted: ${data.repo_deleted}`;
    if (data.cleanup_errors && data.cleanup_errors.length > 0) {
      resultMsg += `\n\n⚠️ Some cleanup steps had issues:\n` + data.cleanup_errors.join('\n');
    }
    alert(resultMsg);
    apiOk = true;
  } catch (err) {
    console.warn('[Admin] API delete failed, trying Firebase fallback:', err.message);
  }

  // ── Attempt 2: Firebase RTDB command (server picks it up on next poll / startup) ──
  if (!apiOk && window.__db) {
    try {
      const cmdRef = window.__db.ref('commands/delete').push();
      await cmdRef.set({
        build_id: selectedBuildId,
        client_name: name,
        status: 'pending',
        requested_at: new Date().toISOString(),
        requested_by: currentUser ? currentUser.email : 'admin',
      });
      console.info('[Admin] Delete command written to Firebase — server will pick it up');
      alert(`Server unreachable — delete command for "${name}" queued.\nIt will be processed when the server comes back online (repo + submodule cleanup included).`);
      apiOk = true;
    } catch (fbErr) {
      console.error('[Admin] Firebase delete fallback also failed:', fbErr);
      alert(`Delete failed: API unreachable and Firebase write failed.\n${fbErr.message}`);
      if ($btn) { $btn.disabled = false; $btn.textContent = '🗑️ Delete'; }
      return;
    }
  }

  if (!apiOk) {
    alert('Delete failed: API unreachable and Firebase is not connected.');
    if ($btn) { $btn.disabled = false; $btn.textContent = '🗑️ Delete'; }
    return;
  }

  // Reset UI
  selectedBuildId = null;
  _detachFirebaseBuildListeners();
  if (eventSource) { eventSource.close(); eventSource = null; }
  $buildDetail.classList.add('hidden');
  $emptyState.classList.remove('hidden');

  // Refresh
  await refreshBuilds();
}

/** Attach Firebase real-time listeners for a build's status, phases, and logs. */
function _attachFirebaseBuildListeners(buildId, isPrimary) {
  if (!window.__db) return;

  const buildRef = window.__db.ref('builds/' + buildId);
  _firebaseBuildRef = buildRef;

  // Listen to build metadata (status, phases)
  buildRef.on('value', (snap) => {
    const data = snap.val();
    if (!data) return;

    // If Firebase is primary data source, populate header
    if (isPrimary) {
      _populateBuildHeader(data);
    }

    // Always update status badge in real-time
    _updateBuildStatusBadge(data.status);

    // Show/hide retry button based on Firebase status
    const $retryBtn = document.getElementById('build-retry-btn');
    if ($retryBtn) {
      if (data.status === 'stalled' || data.status === 'failed') {
        $retryBtn.classList.remove('hidden');
        $retryBtn.disabled = false;
        $retryBtn.textContent = '🔄 Retry Build';
      } else {
        $retryBtn.classList.add('hidden');
      }
    }

    // Update protect/delete buttons from Firebase state
    _updateProtectDeleteButtons(data);

    // Update pipeline graph + step progress from Firebase phases
    if (data.phases) {
      _hydrateFromPhases(data.phases, data.status);
    }

    // Populate pipeline metadata from Firebase
    if (data.client_name && pipeline) {
      pipeline.clientName = data.client_name || pipeline.clientName;
      pipeline.niche = data.niche || pipeline.niche;
      pipeline.liveUrl = data.live_url || pipeline.liveUrl;
      if (pipeline.nodes.request.status === 'done') {
        pipeline.nodes.request.detail = data.client_name;
      }
      if (data.live_url && pipeline.nodes.deploy.status === 'done') {
        pipeline.nodes.deploy.detail = 'GitHub Pages live';
      }
      if (typeof renderPipeline === 'function') renderPipeline();
    }

    // Build finished or stalled — update stats
    if (data.status === 'complete' || data.status === 'failed' || data.status === 'stalled') {
      refreshBuilds();
    }
  });

  // Listen to log lines (child_added for real-time streaming)
  const logRef = window.__db.ref('builds/' + buildId + '/log');
  _firebaseLogRef = logRef;

  logRef.orderByChild('seq').on('child_added', (snap) => {
    const entry = snap.val();
    if (!entry || !entry.msg) return;

    // Pass full structured entry (msg, cat, lvl, ts) so processLogLine can extract AI events by category
    processLogLine(entry, true);

    if (typeof pipelineHandleLog === 'function') pipelineHandleLog(entry.msg);
    renderLog();
    renderAI();   // AI events are extracted inside processLogLine — re-render
    if ($autoScroll && $autoScroll.checked) scrollLogToBottom();
  });
}

/** Detach Firebase listeners when switching builds. */
function _detachFirebaseBuildListeners() {
  if (_firebaseBuildRef) { _firebaseBuildRef.off(); _firebaseBuildRef = null; }
  if (_firebaseLogRef) { _firebaseLogRef.off(); _firebaseLogRef = null; }
}

// ── SSE Connection ─────────────────────────────────────
function connectSSE(buildId) {
  const url = `${API_BASE}/builds/${buildId}/stream`;
  eventSource = new EventSource(url);

  eventSource.onopen = () => {
    console.log('[Admin] SSE connected for build', buildId);
  };

  // FastAPI sends generic "data:" events — dispatch by event.type field
  eventSource.onmessage = (e) => {
    let data;
    try { data = JSON.parse(e.data); } catch { return; }

    const type = data.type;

    if (type === 'log') {
      processLogLine(data.raw || data.message || data.line, true);
      if (typeof pipelineHandleLog === 'function') pipelineHandleLog(data.raw || data.message || data.line);
      renderLog();
      if ($autoScroll.checked) scrollLogToBottom();

    } else if (type === 'step') {
      currentStepData = { current: data.current, total: data.total };
      renderStepProgress(data.current);
      if (typeof pipelineHandleStep === 'function') pipelineHandleStep(data);
      processLogLine(data.raw || `[STEP:${data.current}:${data.total}:${data.stepName || data.step_name}] ${data.message || ''}`, true);
      renderLog();
      if ($autoScroll.checked) scrollLogToBottom();

    } else if (type === 'ai') {
      aiEvents.push(data);
      renderAI();
      if (typeof pipelineHandleAI === 'function') pipelineHandleAI(data);

    } else if (type === 'test') {
      aiEvents.push({ ...data, type: 'test' });
      renderAI();
      if (typeof pipelineHandleTest === 'function') pipelineHandleTest(data);
      processLogLine(data.raw || `[TEST:${data.action}] ${data.message || ''}`, true);
      renderLog();
      if ($autoScroll.checked) scrollLogToBottom();

    } else if (type === 'done' || type === 'timeout') {
      const finalStatus = data.status === 'complete' ? 'success' : data.status;
      const s = finalStatus === 'success'
        ? { text: 'SUCCESS', cls: 'bg-neon-green/20 text-neon-green' }
        : { text: 'FAILED', cls: 'bg-brand-link/20 text-brand-link' };
      $buildStatus.textContent = s.text;
      $buildStatus.className = `px-2.5 py-1 rounded-full text-xs font-mono font-semibold ${s.cls}`;

      if (finalStatus === 'success') renderStepProgress(8);
      if (typeof pipelineHandleDone === 'function') pipelineHandleDone(data);
      refreshBuilds();
      eventSource.close();
    }
  };

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
// Accepts either a plain string OR a structured log object:
//   API shape:     { sequence, level, category, message, created_at }
//   Firebase shape: { seq, msg, cat, lvl, ts }
function processLogLine(lineOrObj, isLive) {
  if (!lineOrObj) return;

  // Normalise: extract message string + optional category
  let line, category, level, timestamp;
  if (typeof lineOrObj === 'object') {
    line = lineOrObj.message || lineOrObj.msg || '';
    category = (lineOrObj.category || lineOrObj.cat || '').toLowerCase();
    level = (lineOrObj.level || lineOrObj.lvl || '').toLowerCase();
    timestamp = lineOrObj.created_at || (lineOrObj.ts ? new Date(lineOrObj.ts).toISOString() : null);
  } else {
    line = lineOrObj;
    category = '';
    level = '';
    timestamp = null;
  }
  if (!line) return;

  // Deduplicate using sequence number or message fingerprint
  const dedupKey = (typeof lineOrObj === 'object')
    ? (lineOrObj.sequence || lineOrObj.seq || line)
    : line;
  if (_seenLogKeys.has(dedupKey)) return;
  _seenLogKeys.add(dedupKey);

  const entry = { raw: line, cssClass: 'text-gray-400' };

  // ── AI-relevant categories → aiEvents ──
  const AI_CATEGORIES = { council: true, design: true, generate: true };
  if (AI_CATEGORIES[category]) {
    entry.cssClass = 'log-ai';
    const action = _inferAIAction(line);
    aiEvents.push({
      type: 'ai',
      action: action,
      message: line,
      category: category,
      timestamp: timestamp || new Date().toISOString(),
    });
  } else if (category === 'test') {
    const action = _inferTestAction(line);
    entry.cssClass = action === 'pass' ? 'log-test-pass' : action === 'fail' ? 'log-test-fail' : 'text-neon-yellow';
    aiEvents.push({
      type: 'test',
      action: action,
      message: line,
      timestamp: timestamp || new Date().toISOString(),
    });
  } else if (category === 'deploy') {
    entry.cssClass = 'log-deploy';
  // ── Legacy tag-based parsing (SSE) ──
  } else if (/\[STEP:\d+:\d+:\w+\]/.test(line)) {
    entry.cssClass = 'log-step';
    const m = line.match(/\[STEP:(\d+):(\d+)/);
    if (m) {
      currentStepData = { current: parseInt(m[1]), total: parseInt(m[2]) };
      if (!isLive) renderStepProgress(currentStepData.current);
    }
  } else if (/\[AI:/.test(line)) {
    entry.cssClass = 'log-ai';
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
  } else if (/\[TEST:/.test(line)) {
    const m = line.match(/\[TEST:(\w+)(?::(\d+))?\]\s*(.*)/);
    entry.cssClass = /PASS/.test(line) ? 'log-test-pass' : /FAIL/.test(line) ? 'log-test-fail' : 'text-neon-yellow';
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
  // ── General styling ──
  } else if (/STDERR:|❌|Error|error/.test(line)) {
    entry.cssClass = 'log-error';
  } else if (/✅/.test(line)) {
    entry.cssClass = 'log-test-pass';
  } else if (/⚠️/.test(line)) {
    entry.cssClass = 'text-neon-orange';
  }

  logLines.push(entry);
}

/** Infer AI action from message content (emoji/keyword patterns). */
function _inferAIAction(msg) {
  if (/🧠/.test(msg)) return 'call';
  if (/🎨|✨/.test(msg)) return 'done';
  if (/🔧/.test(msg)) return 'fix';
  if (/💬|📝/.test(msg)) return 'prompt';
  if (/✅/.test(msg)) return 'done';
  if (/❌|⚠️/.test(msg)) return 'error';
  if (/📄/.test(msg)) return 'fallback';
  if (/📡/.test(msg)) return 'call';
  if (/generat/i.test(msg)) return 'done';
  if (/creat|built/i.test(msg)) return 'done';
  return 'response';
}

/** Infer test action from message content. */
function _inferTestAction(msg) {
  if (/✅|pass|passed/i.test(msg)) return 'pass';
  if (/❌|fail|failed/i.test(msg)) return 'fail';
  if (/🔧|fix|auto.?fix/i.test(msg)) return 'fix';
  if (/attempt|run|🧪/i.test(msg)) return 'run';
  return 'run';
}

// ── Render functions ───────────────────────────────────

/**
 * Hydrate the pipeline graph and step progress from stored phase data.
 * Works with both API shape ({phase_name, status}) and Firebase shape ({name, status}).
 */
function _hydrateFromPhases(phases, buildStatus) {
  if (!phases) return;

  // Normalise — API returns an array, Firebase returns an object keyed by phase_number
  const phaseList = Array.isArray(phases)
    ? phases
    : Object.entries(phases).map(([k, v]) => ({ ...v, phase_number: parseInt(k) }));

  if (phaseList.length === 0) return;

  // Map API/Firebase phase_name → pipeline node key
  const nameToKey = {
    repository: 'repo', repo: 'repo',
    council: 'council',
    design: 'design',
    generate: 'generate',
    assemble: 'assemble',
    test: 'test',
    deploy: 'deploy',
    notify: 'notify',
  };

  let completedCount = 0;
  let activeIdx = 0;

  phaseList.forEach(p => {
    const phaseName = p.phase_name || p.name || '';
    const nodeKey = nameToKey[phaseName.toLowerCase()];
    if (!nodeKey || !pipeline.nodes[nodeKey]) return;

    const node = pipeline.nodes[nodeKey];
    const st = (p.status || '').toLowerCase();

    if (st === 'complete' || st === 'done') {
      node.status = 'done';
      completedCount++;
    } else if (st === 'running') {
      node.status = 'active';
      activeIdx = p.phase_number || completedCount + 1;
    } else if (st === 'failed') {
      node.status = 'failed';
    }

    if (p.started_at) node.time = new Date(p.started_at);
    if (p.error_message) node.detail = p.error_message;
  });

  // For fully complete builds, also mark request as done
  if (completedCount > 0) {
    pipeline.nodes.request.status = 'done';
  }

  // Update step progress bar
  const current = activeIdx || completedCount;
  renderStepProgress(current);

  // If the build itself is complete/failed/stalled, apply terminal state
  if (buildStatus === 'complete' || buildStatus === 'success') {
    for (const n of Object.values(pipeline.nodes)) {
      if (n.status === 'active') n.status = 'done';
    }
  } else if (buildStatus === 'failed' || buildStatus === 'stalled') {
    for (const n of Object.values(pipeline.nodes)) {
      if (n.status === 'active') n.status = 'failed';
    }
  }

  // Re-render the pipeline graph
  if (typeof renderPipeline === 'function') renderPipeline();
}

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
  if ($logPanel) $logPanel.innerHTML = html || '<div class="text-center text-gray-500 text-xs font-mono py-8">No logs found</div>';
  if ($logCount) $logCount.textContent = logLines.length;
}

function renderAI() {
  if (aiEvents.length === 0) {
    $aiPanel.innerHTML = '<div class="text-center text-gray-500 text-xs font-mono py-8">No AI activity found</div>';
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
//  Firebase RTDB — Real-time builds (fallback when API is offline)
// ═══════════════════════════════════════════════════════
function subscribeToBuildsFirebase() {
  if (!window.__db) return;
  window.__db.ref('builds').orderByChild('created_at').limitToLast(50).on('value', (snapshot) => {
    if (apiConnected) return; // API is primary source when available
    const fbBuilds = [];
    snapshot.forEach((child) => {
      const b = child.val();
      fbBuilds.push({
        id: child.key,
        client: b.client_name || b.clientName || 'Unknown',
        status: b.status === 'complete' ? 'success' : b.status,
        niche: b.niche || '',
        email: b.email || '',
        started: b.created_at || b.started_at,
        finished: b.finished_at,
        liveUrl: b.live_url || '',
        protected: !!b.protected,
        repoFull: b.repo_full || '',
      });
    });
    fbBuilds.reverse();
    if (fbBuilds.length > 0) {
      builds = fbBuilds;
      renderBuildList();
      updateStats();
    }
  });
}

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
  const activeLeads = leads.filter(l => l.status !== 'archived');
  const archivedLeads = leads.filter(l => l.status === 'archived');
  const $statLeads = document.getElementById('stat-leads');
  if ($statLeads) $statLeads.textContent = activeLeads.length;
  const $statActive = document.getElementById('stat-leads-active');
  if ($statActive) $statActive.textContent = activeLeads.length;
  const $statArchived = document.getElementById('stat-leads-archived');
  if ($statArchived) $statArchived.textContent = archivedLeads.length;
}

function switchLeadsSubTab(tab) {
  leadsSubTab = tab;
  const $active = document.getElementById('leads-subtab-active');
  const $archived = document.getElementById('leads-subtab-archived');
  const $activePanel = document.getElementById('leads-panel-content');
  const $archivedPanel = document.getElementById('archived-panel-content');

  if (tab === 'archived') {
    $active.className   = 'flex-1 py-2 text-[0.65rem] font-mono font-semibold uppercase tracking-widest text-center border-b-2 border-transparent text-gray-500 hover:text-gray-300 transition';
    $archived.className = 'flex-1 py-2 text-[0.65rem] font-mono font-semibold uppercase tracking-widest text-center border-b-2 border-electric text-electric transition';
    $activePanel.classList.add('hidden');
    $archivedPanel.classList.remove('hidden');
  } else {
    $active.className   = 'flex-1 py-2 text-[0.65rem] font-mono font-semibold uppercase tracking-widest text-center border-b-2 border-electric text-electric transition';
    $archived.className = 'flex-1 py-2 text-[0.65rem] font-mono font-semibold uppercase tracking-widest text-center border-b-2 border-transparent text-gray-500 hover:text-gray-300 transition';
    $activePanel.classList.remove('hidden');
    $archivedPanel.classList.add('hidden');
  }
  renderLeadsPanel();
}

function renderLeadsPanel() {
  const activeLeads = leads.filter(l => l.status !== 'archived');
  const archivedLeads = leads.filter(l => l.status === 'archived');

  // Render active leads
  const $activePanel = document.getElementById('leads-panel-content');
  if ($activePanel) {
    $activePanel.innerHTML = activeLeads.length === 0
      ? `<div class="text-center py-12">
          <div class="text-4xl mb-3 opacity-30">📭</div>
          <p class="text-gray-500 font-mono text-sm">No active leads</p>
          <p class="text-gray-600 text-xs mt-1">Submissions from the intake form will appear here</p>
        </div>`
      : activeLeads.map(lead => renderLeadCard(lead)).join('');
  }

  // Render archived leads
  const $archivedPanel = document.getElementById('archived-panel-content');
  if ($archivedPanel) {
    $archivedPanel.innerHTML = archivedLeads.length === 0
      ? `<div class="text-center py-12">
          <div class="text-4xl mb-3 opacity-30">🗃️</div>
          <p class="text-gray-500 font-mono text-sm">No archived leads</p>
          <p class="text-gray-600 text-xs mt-1">Archived leads will appear here</p>
        </div>`
      : archivedLeads.map(lead => renderLeadCard(lead)).join('');
  }
}

function renderLeadCard(lead) {
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
  const isArchived = lead.status === 'archived';

  return `
    <div onclick="selectLead('${lead.id}')" class="p-4 bg-surface-2 rounded-xl border cursor-pointer transition animate-fade-in
      ${isSelected ? 'border-electric bg-electric/5' : 'border-border hover:border-border-glow'}
      ${isArchived ? 'opacity-70' : ''}">
      <div class="flex items-center justify-between mb-3">
        <h3 class="font-mono text-sm font-bold ${isArchived ? 'text-gray-400' : 'text-white'}">${esc(lead.business_name || 'Unknown')}</h3>
        <div class="flex items-center gap-2" onclick="event.stopPropagation()">
          ${isArchived
            ? `<button onclick="restoreLeadById('${lead.id}')" class="text-[0.65rem] font-mono px-2 py-1 rounded-full bg-neon-green/10 text-neon-green hover:bg-neon-green/20 transition">♻️ Restore</button>`
            : `<select onchange="updateLeadStatus('${lead.id}', this.value)"
                class="text-[0.65rem] font-mono px-2 py-1 rounded-full border-0 cursor-pointer ${statusCls}">
                ${['new','contacted','building','deployed','archived'].map(s =>
                  `<option value="${s}" ${lead.status === s ? 'selected' : ''} class="bg-surface text-gray-300">${s.toUpperCase()}</option>`
                ).join('')}
              </select>`
          }
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
}

function updateLeadStatus(leadId, newStatus) {
  if (!window.__db) return;

  // Optimistic local update — reflects immediately in UI
  const lead = leads.find(l => l.id === leadId);
  if (lead) {
    lead.status = newStatus;
    renderLeadStats();
    renderLeadsPanel();
    if (leadId === selectedLeadId) renderLeadDetail();
  }

  window.__db.ref(`leads/${leadId}/status`).set(newStatus)
    .then(() => {
      console.log(`[Admin] Lead ${leadId} → ${newStatus}`);
    })
    .catch(err => {
      console.error('[Admin] Failed to update lead:', err);
      // Revert on failure — Firebase listener will fix state anyway
    });
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
  if (lead.phone)  metas.push(`<span>📱 ${esc(lead.phone)}</span>`);
  if (lead.location) metas.push(`<span>📍 ${esc(lead.location)}</span>`);
  if (lead.source) metas.push(`<span>🌐 ${esc(lead.source)}</span>`);
  if (lead.rebuild) metas.push(`<span class="text-yellow-400">⚠️ REBUILD</span>`);
  document.getElementById('lead-meta').innerHTML = metas.join('');

  // Content
  document.getElementById('lead-goals').textContent = lead.goals || 'No goals specified';
  document.getElementById('lead-email').textContent = lead.email || '-';
  document.getElementById('lead-niche').textContent = lead.niche || '-';
  document.getElementById('lead-time').textContent = lead.submitted_at ? formatTime(lead.submitted_at) : 'Unknown';
  document.getElementById('lead-source').textContent = lead.source || 'direct';

  // Extended fields
  const $extra = document.getElementById('lead-extra-fields');
  if ($extra) {
    const extras = [];
    if (lead.phone) extras.push(`<div class="flex"><span class="w-32 text-gray-500 shrink-0">Phone</span><span class="text-white">${esc(lead.phone)}</span></div>`);
    if (lead.location) extras.push(`<div class="flex"><span class="w-32 text-gray-500 shrink-0">Location</span><span class="text-white">${esc(lead.location)}</span></div>`);
    if (lead.existingWebsite || lead.existing_website) {
      const url = lead.existingWebsite || lead.existing_website;
      extras.push(`<div class="flex"><span class="w-32 text-gray-500 shrink-0">Existing Site</span><a href="${esc(url)}" target="_blank" class="text-electric hover:underline">${esc(url)}</a></div>`);
    }
    if (lead.brandColors || lead.brand_colors) extras.push(`<div class="flex"><span class="w-32 text-gray-500 shrink-0">Brand Colors</span><span class="text-white">${esc(lead.brandColors || lead.brand_colors)}</span></div>`);
    if (lead.tagline) extras.push(`<div class="flex"><span class="w-32 text-gray-500 shrink-0">Tagline</span><span class="text-white italic">"${esc(lead.tagline)}"</span></div>`);
    if (lead.targetAudience || lead.target_audience) extras.push(`<div class="flex"><span class="w-32 text-gray-500 shrink-0">Audience</span><span class="text-white">${esc(lead.targetAudience || lead.target_audience)}</span></div>`);
    if (lead.competitorUrls || lead.competitor_urls) extras.push(`<div class="flex items-start"><span class="w-32 text-gray-500 shrink-0">Competitors</span><span class="text-white whitespace-pre-line">${esc(lead.competitorUrls || lead.competitor_urls)}</span></div>`);
    if (lead.additionalNotes || lead.additional_notes) extras.push(`<div class="flex items-start"><span class="w-32 text-gray-500 shrink-0">Notes</span><span class="text-white whitespace-pre-line">${esc(lead.additionalNotes || lead.additional_notes)}</span></div>`);
    $extra.innerHTML = extras.length
      ? `<div class="mt-4 pt-4 border-t border-border space-y-2 text-xs font-mono">${extras.join('')}</div>`
      : '';
  }

  // Email link
  if (lead.email) {
    const subject = encodeURIComponent(`AjayaDesign — Your website for ${lead.business_name || 'your business'}`);
    document.getElementById('lead-email-link').href = `mailto:${lead.email}?subject=${subject}`;
  }

  // Toggle Archive / Restore buttons
  const $btnArchive = document.getElementById('btn-archive-lead');
  const $btnRestore = document.getElementById('btn-restore-lead');
  if ($btnArchive && $btnRestore) {
    if (lead.status === 'archived') {
      $btnArchive.classList.add('hidden');
      $btnRestore.classList.remove('hidden');
    } else {
      $btnArchive.classList.remove('hidden');
      $btnRestore.classList.add('hidden');
    }
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

  // POST to FastAPI
  fetch(`${API_BASE}/builds`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      businessName: lead.business_name,
      niche: lead.niche,
      goals: lead.goals || '',
      email: lead.email,
      phone: lead.phone || undefined,
      location: lead.location || undefined,
      firebaseId: selectedLeadId,
      source: lead.source || 'admin-trigger',
    }),
  })
    .then(res => {
      if (!res.ok) return res.json().then(e => { throw new Error(e.detail || `HTTP ${res.status}`); });
      return res.json();
    })
    .then(data => {
      console.log('[Admin] Build triggered:', data);
      // Switch to builds tab and select the new build
      switchTab('builds');
      if (data.short_id) {
        setTimeout(() => selectBuild(data.short_id), 1000);
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
  // Switch to archived sub-tab so user sees where it went
  setTimeout(() => switchLeadsSubTab('archived'), 300);
}

function restoreLead() {
  if (!selectedLeadId) return;
  const lead = leads.find(l => l.id === selectedLeadId);
  if (!lead) return;
  updateLeadStatus(selectedLeadId, 'new');
  // Switch back to active sub-tab
  setTimeout(() => switchLeadsSubTab('active'), 300);
}

function restoreLeadById(leadId) {
  if (!leadId) return;
  updateLeadStatus(leadId, 'new');
  if (leadId === selectedLeadId) {
    setTimeout(() => switchLeadsSubTab('active'), 300);
  }
}

// ── Add Client Modal ───────────────────────────────────
let addClientTab = 'manual';

function openAddClientModal() {
  document.getElementById('add-client-modal').classList.remove('hidden');
  switchAddClientTab('manual');
  clearAddClientForm();
}

function closeAddClientModal() {
  document.getElementById('add-client-modal').classList.add('hidden');
  clearAddClientForm();
}

function switchAddClientTab(tab) {
  addClientTab = tab;
  const $manual = document.getElementById('acm-tab-manual');
  const $ai     = document.getElementById('acm-tab-ai');
  const $aiPanel = document.getElementById('acm-ai-panel');

  if (tab === 'manual') {
    $manual.className = 'flex-1 py-3 text-xs font-mono font-semibold uppercase tracking-widest text-center border-b-2 border-electric text-electric transition';
    $ai.className     = 'flex-1 py-3 text-xs font-mono font-semibold uppercase tracking-widest text-center border-b-2 border-transparent text-gray-500 hover:text-gray-300 transition';
    $aiPanel.classList.add('hidden');
  } else {
    $ai.className     = 'flex-1 py-3 text-xs font-mono font-semibold uppercase tracking-widest text-center border-b-2 border-electric text-electric transition';
    $manual.className = 'flex-1 py-3 text-xs font-mono font-semibold uppercase tracking-widest text-center border-b-2 border-transparent text-gray-500 hover:text-gray-300 transition';
    $aiPanel.classList.remove('hidden');
  }
}

function clearAddClientForm() {
  const ids = ['acm-business-name','acm-niche','acm-email','acm-goals','acm-phone','acm-location',
    'acm-existing-website','acm-brand-colors','acm-tagline','acm-target-audience',
    'acm-competitor-urls','acm-additional-notes','acm-raw-text'];
  ids.forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
  const cb = document.getElementById('acm-rebuild');
  if (cb) cb.checked = false;
  const $status = document.getElementById('acm-parse-status');
  if ($status) { $status.classList.add('hidden'); $status.textContent = ''; }
}

async function parseWithAI() {
  const rawText = (document.getElementById('acm-raw-text')?.value || '').trim();
  if (rawText.length < 10) {
    alert('Please paste at least a few sentences of client details.');
    return;
  }

  const $btn = document.getElementById('acm-parse-btn');
  const $status = document.getElementById('acm-parse-status');
  const origHTML = $btn.innerHTML;
  $btn.innerHTML = '⏳ Parsing...';
  $btn.disabled = true;
  $status.classList.remove('hidden');
  $status.className = 'text-xs font-mono text-gray-400';
  $status.textContent = 'Submitting parse request...';

  // Strategy: Try direct API first (fast, ~2s). If offline, fall back to
  // Firebase bridge (async — Python poller picks it up on next cycle).
  let usedFirebase = false;

  try {
    // ── Attempt 1: Direct API call (works when API server is running) ──
    const res = await fetch(`${API_BASE}/parse-client`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rawText }),
      signal: AbortSignal.timeout(8000),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }

    const data = await res.json();
    _applyParsedFields(data, $status);

  } catch (apiErr) {
    console.warn('[Admin] Direct API parse failed, trying Firebase bridge:', apiErr.message);

    // ── Attempt 2: Firebase bridge (works in prod) ──
    const db = firebase.database();
    if (!db) {
      $status.className = 'text-xs font-mono text-brand-link';
      $status.textContent = `❌ Parse failed: No API or Firebase connection. Fill the form manually.`;
      $btn.innerHTML = origHTML;
      $btn.disabled = false;
      return;
    }

    usedFirebase = true;
    const requestId = Date.now() + '_' + Math.random().toString(36).slice(2, 8);
    const requestRef = db.ref('parse_requests/' + requestId);

    // Write the parse request
    try {
      await requestRef.set({
        rawText,
        status: 'pending',
        requestedAt: Date.now(),
        requestedBy: firebase.auth().currentUser?.email || 'unknown',
      });
      $status.textContent = '📡 Request sent — waiting for automation server...';
    } catch (fbErr) {
      $status.className = 'text-xs font-mono text-brand-link';
      $status.textContent = `❌ Firebase write failed: ${fbErr.message}. Fill the form manually.`;
      $btn.innerHTML = origHTML;
      $btn.disabled = false;
      return;
    }

    // Listen for result (timeout after 90s)
    const result = await new Promise((resolve) => {
      const timeout = setTimeout(() => {
        requestRef.off('value', handler);
        resolve({ error: 'Timeout — automation server may be offline. Try again later or fill manually.' });
      }, 90000);

      function handler(snap) {
        const val = snap.val();
        if (!val) return;
        if (val.status === 'processing') {
          $status.textContent = '⚙️ Processing with AI...';
          return;
        }
        if (val.status === 'complete' || val.status === 'failed') {
          clearTimeout(timeout);
          requestRef.off('value', handler);
          resolve(val);
        }
      }
      requestRef.on('value', handler);
    });

    if (result.status === 'complete' && result.result) {
      _applyParsedFields(result.result, $status);
    } else {
      const errMsg = result.error || 'Parse failed on server';
      $status.className = 'text-xs font-mono text-brand-link';
      $status.textContent = `❌ ${errMsg}. Fill the form manually.`;
    }
  } finally {
    $btn.innerHTML = origHTML;
    $btn.disabled = false;
  }
}

/** Apply parsed fields to the Add Client form. */
function _applyParsedFields(data, $status) {
  const p = data.parsed || {};
  const fieldMap = {
    'acm-business-name':    p.businessName || p.business_name || '',
    'acm-niche':            p.niche || '',
    'acm-email':            p.email || '',
    'acm-goals':            p.goals || '',
    'acm-phone':            p.phone || '',
    'acm-location':         p.location || '',
    'acm-existing-website': p.existingWebsite || p.existing_website || '',
    'acm-brand-colors':     p.brandColors || p.brand_colors || '',
    'acm-tagline':          p.tagline || '',
    'acm-target-audience':  p.targetAudience || p.target_audience || '',
    'acm-competitor-urls':  p.competitorUrls || p.competitor_urls || '',
    'acm-additional-notes': p.additionalNotes || p.additional_notes || '',
  };

  Object.entries(fieldMap).forEach(([id, val]) => {
    const el = document.getElementById(id);
    if (el && val) el.value = val;
  });

  // Highlight required fields that are still empty
  ['acm-business-name', 'acm-niche', 'acm-email', 'acm-goals'].forEach(id => {
    const el = document.getElementById(id);
    if (el && !el.value.trim()) {
      el.classList.add('border-red-500/50');
    } else if (el) {
      el.classList.remove('border-red-500/50');
    }
  });

  const conf = data.confidence || 'medium';
  const confColors = { high: 'text-neon-green', medium: 'text-neon-yellow', low: 'text-neon-orange' };
  $status.className = `text-xs font-mono ${confColors[conf] || 'text-gray-400'}`;
  $status.textContent = `✅ Parsed (${conf} confidence) — review and edit below`;
}

async function saveNewLead(triggerBuild) {
  // Validate required fields
  const biz   = (document.getElementById('acm-business-name')?.value || '').trim();
  const niche = (document.getElementById('acm-niche')?.value || '').trim();
  const email = (document.getElementById('acm-email')?.value || '').trim();
  const goals = (document.getElementById('acm-goals')?.value || '').trim();

  if (!biz || !niche || !email || !goals) {
    alert('Please fill in all required fields: Business Name, Niche, Email, Goals.');
    return;
  }

  const ts = Date.now();
  const leadId = email.replace(/[@.]/g, '-') + '_' + ts;
  const source = addClientTab === 'ai' ? 'admin-ai-parse' : 'admin-manual';

  const leadData = {
    business_name: biz,
    niche: niche,
    goals: goals,
    email: email,
    phone:            (document.getElementById('acm-phone')?.value || '').trim(),
    location:         (document.getElementById('acm-location')?.value || '').trim(),
    existingWebsite:  (document.getElementById('acm-existing-website')?.value || '').trim(),
    brandColors:      (document.getElementById('acm-brand-colors')?.value || '').trim(),
    tagline:          (document.getElementById('acm-tagline')?.value || '').trim(),
    targetAudience:   (document.getElementById('acm-target-audience')?.value || '').trim(),
    competitorUrls:   (document.getElementById('acm-competitor-urls')?.value || '').trim(),
    additionalNotes:  (document.getElementById('acm-additional-notes')?.value || '').trim(),
    rebuild:          !!(document.getElementById('acm-rebuild')?.checked),
    timestamp: ts,
    submitted_at: new Date(ts).toISOString(),
    source: source,
    status: triggerBuild ? 'building' : 'new',
  };

  // 1. Save to Firebase RTDB
  try {
    if (window.__db) {
      await window.__db.ref('leads/' + leadId).set(leadData);
      console.log('[Admin] ✅ Lead saved to Firebase:', leadId);
    }
  } catch (err) {
    console.error('[Admin] Firebase save failed:', err);
    alert('Failed to save lead to Firebase: ' + err.message);
    return;
  }

  // 2. Trigger build if requested
  if (triggerBuild) {
    try {
      const res = await fetch(`${API_BASE}/builds`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          businessName: biz,
          niche: niche,
          goals: goals,
          email: email,
          phone: leadData.phone || undefined,
          location: leadData.location || undefined,
          existingWebsite: leadData.existingWebsite || undefined,
          brandColors: leadData.brandColors || undefined,
          tagline: leadData.tagline || undefined,
          targetAudience: leadData.targetAudience || undefined,
          competitorUrls: leadData.competitorUrls || undefined,
          additionalNotes: leadData.additionalNotes || undefined,
          rebuild: leadData.rebuild,
          firebaseId: leadId,
          source: source,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      const data = await res.json();
      console.log('[Admin] ✅ Build triggered:', data);
      closeAddClientModal();
      switchTab('builds');
      if (data.short_id) {
        setTimeout(() => {
          refreshBuilds();
          selectBuild(data.short_id);
        }, 1000);
      }
      return;
    } catch (err) {
      console.warn('[Admin] Build trigger failed (lead still saved):', err);
    }
  }

  closeAddClientModal();
  switchTab('leads');
  switchLeadsSubTab('active');
}

// ── Sign out ───────────────────────────────────────────
function signOut() {
  if (window.__auth) window.__auth.signOut();
}
