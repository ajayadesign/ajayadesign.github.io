/* ═══════════════════════════════════════════════════════
   AjayaDesign Admin — Activity History / Audit Trail
   Beautiful timeline view of all contract & invoice events
   ═══════════════════════════════════════════════════════ */

// ── State ──────────────────────────────────────────────
let activityLogs = [];
let activityFilter = 'all'; // 'all', 'contract', 'invoice'

// ── Action → color / label mapping ─────────────────────
const ACTION_STYLES = {
  created:  { color: 'bg-electric/20 text-electric',        ring: 'ring-electric/40' },
  updated:  { color: 'bg-neon-yellow/20 text-neon-yellow',  ring: 'ring-neon-yellow/40' },
  sent:     { color: 'bg-neon-purple/20 text-neon-purple',  ring: 'ring-neon-purple/40' },
  signed:   { color: 'bg-neon-green/20 text-neon-green',    ring: 'ring-neon-green/40' },
  paid:     { color: 'bg-neon-green/20 text-neon-green',    ring: 'ring-neon-green/40' },
  deleted:  { color: 'bg-brand-link/20 text-brand-link',    ring: 'ring-brand-link/40' },
  viewed:   { color: 'bg-neon-orange/20 text-neon-orange',  ring: 'ring-neon-orange/40' },
};

// ── Load activity log from API ─────────────────────────
async function loadActivityLog() {
  const $list = document.getElementById('history-list');
  if (!$list) return;

  $list.innerHTML = '<div class="text-center text-gray-600 text-xs font-mono py-8">Loading activity...</div>';

  try {
    let url = `${API_BASE}/activity?limit=200`;
    if (activityFilter !== 'all') {
      url += `&entity_type=${activityFilter}`;
    }
    const res = await fetch(url, { signal: AbortSignal.timeout(5000) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    activityLogs = data.activities || [];
  } catch (err) {
    console.warn('[History] Failed to load:', err.message);
    // If API is offline, try Firebase real-time data
    try {
      if (window.__db) {
        const snapshot = await window.__db.ref('activity_logs')
          .orderByChild('created_at')
          .limitToLast(200)
          .once('value');
        const raw = snapshot.val();
        if (raw) {
          activityLogs = Object.values(raw).sort((a, b) =>
            (b.created_at || '').localeCompare(a.created_at || '')
          );
          if (activityFilter !== 'all') {
            activityLogs = activityLogs.filter(a => a.entity_type === activityFilter);
          }
        }
      }
    } catch (fbErr) {
      console.warn('[History] Firebase fallback failed:', fbErr.message);
    }

    if (activityLogs.length === 0) {
      $list.innerHTML = '<div class="text-center text-gray-600 text-xs font-mono py-8">Failed to load activity</div>';
      return;
    }
  }

  renderActivityTimeline();
}

// ── Filter buttons ─────────────────────────────────────
function filterActivityLog(filter) {
  activityFilter = filter;
  const filters = ['all', 'contract', 'invoice'];
  const activeClass = 'flex-1 py-2 text-[0.65rem] font-mono font-semibold uppercase tracking-widest text-center border-b-2 border-electric text-electric transition';
  const inactiveClass = 'flex-1 py-2 text-[0.65rem] font-mono font-semibold uppercase tracking-widest text-center border-b-2 border-transparent text-gray-500 hover:text-gray-300 transition';

  filters.forEach(f => {
    const $btn = document.getElementById(`history-filter-${f}`);
    if ($btn) $btn.className = (f === filter) ? activeClass : inactiveClass;
  });

  loadActivityLog();
}

// ── Render the timeline ────────────────────────────────
function renderActivityTimeline() {
  const $list = document.getElementById('history-list');
  if (!$list) return;

  if (activityLogs.length === 0) {
    $list.innerHTML = `
      <div class="text-center py-12">
        <div class="text-4xl mb-3 opacity-30">📜</div>
        <p class="text-gray-500 font-mono text-sm">No activity yet</p>
        <p class="text-gray-600 text-xs mt-1">Actions on contracts & invoices will appear here</p>
      </div>`;
    return;
  }

  // Group by date
  const groups = {};
  activityLogs.forEach(log => {
    const dateStr = log.created_at
      ? new Date(log.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
      : 'Unknown';
    if (!groups[dateStr]) groups[dateStr] = [];
    groups[dateStr].push(log);
  });

  let html = '';
  for (const [dateLabel, logs] of Object.entries(groups)) {
    html += `<div class="mb-2 mt-3 first:mt-0"><span class="text-[0.6rem] font-mono text-gray-600 uppercase tracking-widest">${_escH(dateLabel)}</span></div>`;

    logs.forEach(log => {
      const style = ACTION_STYLES[log.action] || ACTION_STYLES.updated;
      const time = log.created_at
        ? new Date(log.created_at).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
        : '';
      const entityTag = log.entity_type === 'contract' ? '📝' : log.entity_type === 'invoice' ? '💰' : '📁';
      const actorLabel = log.actor === 'admin' ? '' : `<span class="text-[0.55rem] text-gray-600 ml-1">by ${_escH(log.actor)}</span>`;

      html += `
        <div class="flex gap-3 py-2 px-2 rounded-lg hover:bg-surface-2 transition cursor-pointer group"
          onclick="viewEntityFromLog('${log.entity_type}', '${_escH(log.entity_id)}')">
          <!-- Timeline dot -->
          <div class="flex flex-col items-center pt-0.5">
            <div class="w-7 h-7 rounded-full flex items-center justify-center text-sm ${style.color} ring-1 ${style.ring}">
              ${log.icon || '📋'}
            </div>
            <div class="w-px flex-1 bg-border mt-1 group-last:hidden"></div>
          </div>
          <!-- Content -->
          <div class="flex-1 min-w-0 pb-1">
            <div class="flex items-center gap-2 mb-0.5">
              <span class="text-[0.6rem] font-mono px-1.5 py-0.5 rounded ${style.color}">${(log.action || '').toUpperCase()}</span>
              <span class="text-[0.55rem] text-gray-600">${entityTag} ${_escH(log.entity_id)}</span>
              ${actorLabel}
            </div>
            <p class="text-xs text-gray-400 leading-relaxed truncate">${_escH(log.description)}</p>
            <span class="text-[0.55rem] text-gray-600">${time}</span>
          </div>
        </div>`;
    });
  }

  $list.innerHTML = html;
}

// ── Click a log entry to jump to entity ────────────────
function viewEntityFromLog(entityType, entityId) {
  if (entityType === 'contract') {
    switchTab('portfolio');
    setTimeout(() => {
      switchPortfolioSubTab('contracts');
      setTimeout(() => openContract(entityId), 200);
    }, 200);
  } else if (entityType === 'invoice') {
    switchTab('portfolio');
    setTimeout(() => {
      switchPortfolioSubTab('invoices');
      setTimeout(() => openInvoice(entityId), 200);
    }, 200);
  }
}

// ── Load entity-specific history (for detail panels) ───
async function loadEntityHistory(entityType, entityId, $container) {
  if (!$container) return;

  $container.innerHTML = '<p class="text-xs text-gray-600 font-mono">Loading history...</p>';

  try {
    const res = await fetch(`${API_BASE}/activity/entity/${entityType}/${entityId}`, { signal: AbortSignal.timeout(5000) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const logs = data.history || [];

    if (logs.length === 0) {
      $container.innerHTML = '<p class="text-xs text-gray-600 font-mono">No activity recorded yet</p>';
      return;
    }

    $container.innerHTML = logs.map(log => {
      const style = ACTION_STYLES[log.action] || ACTION_STYLES.updated;
      const time = log.created_at
        ? new Date(log.created_at).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
        : '';

      return `
        <div class="flex gap-2 py-1.5">
          <div class="w-5 h-5 rounded-full flex items-center justify-center text-[0.6rem] ${style.color} shrink-0 mt-0.5">
            ${log.icon || '📋'}
          </div>
          <div class="min-w-0">
            <span class="text-[0.6rem] font-mono px-1 py-0.5 rounded ${style.color}">${(log.action || '').toUpperCase()}</span>
            <span class="text-[0.55rem] text-gray-600 ml-1">${time}</span>
            <p class="text-[0.65rem] text-gray-400 truncate mt-0.5">${_escH(log.description)}</p>
          </div>
        </div>`;
    }).join('');
  } catch (err) {
    $container.innerHTML = '<p class="text-xs text-gray-600 font-mono">Failed to load history</p>';
  }
}

// ── Helper ─────────────────────────────────────────────
function _escH(s) {
  return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
