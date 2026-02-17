/* ═══════════════════════════════════════════════════════
   AjayaDesign Admin — Analytics Dashboard
   Revenue, Pipeline, Engagement, Builds, Storage, Activity
   Reads from Firebase RTDB with API fallback
   ═══════════════════════════════════════════════════════ */

// ── Chart registry (auto-destroy on re-render) ─────────
const _chartInstances = {};
function _createChart(canvasId, config) {
  if (_chartInstances[canvasId]) {
    _chartInstances[canvasId].destroy();
  }
  const ctx = document.getElementById(canvasId);
  if (!ctx) return null;

  // Dark-theme defaults
  const defaults = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { labels: { color: '#9CA3AF', font: { family: 'JetBrains Mono', size: 10 } } },
      tooltip: { titleFont: { family: 'JetBrains Mono' }, bodyFont: { family: 'JetBrains Mono', size: 11 } },
    },
    scales: {},
  };

  // Merge scale colors for line/bar charts
  if (config.type === 'line' || config.type === 'bar') {
    defaults.scales = {
      x: { ticks: { color: '#6B7280', font: { family: 'JetBrains Mono', size: 9 } }, grid: { color: 'rgba(42,42,58,0.5)' } },
      y: { ticks: { color: '#6B7280', font: { family: 'JetBrains Mono', size: 9 } }, grid: { color: 'rgba(42,42,58,0.5)' } },
    };
  }

  config.options = _deepMerge(defaults, config.options || {});
  _chartInstances[canvasId] = new Chart(ctx, config);
  return _chartInstances[canvasId];
}

function _deepMerge(target, source) {
  const out = { ...target };
  for (const key of Object.keys(source)) {
    if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
      out[key] = _deepMerge(out[key] || {}, source[key]);
    } else {
      out[key] = source[key];
    }
  }
  return out;
}

// ── Palette ────────────────────────────────────────────
const COLORS = {
  electric: '#00D4FF',
  green: '#00FF88',
  yellow: '#FFD600',
  purple: '#A855F7',
  orange: '#FF8A00',
  red: '#FF6B6B',
  pink: '#EC4899',
  teal: '#14B8A6',
};
const PALETTE = Object.values(COLORS);

// ── Helpers ────────────────────────────────────────────
function _fb(path) { return window.__db ? window.__db.ref(path).once('value').then(s => s.val()) : Promise.resolve(null); }
function _esc(s) { return typeof esc === 'function' ? esc(s) : String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]); }
function _fmt$(n) { return '$' + parseFloat(n || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }
function _pct(n, d) { return d > 0 ? Math.round((n / d) * 100) : 0; }
function _daysBetween(a, b) {
  if (!a || !b) return null;
  const ms = new Date(b) - new Date(a);
  return ms > 0 ? Math.round(ms / 86400000) : null;
}

function scrollAnalytics(id) {
  const el = document.getElementById(id);
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ── Main data fetch ────────────────────────────────────
let _analyticsData = {};
let _analyticsLoading = false;

async function _fetchAllData() {
  const [buildsRaw, leadsRaw, contractsRaw, invoicesRaw, portfolioRaw, activityRaw] = await Promise.allSettled([
    _fb('builds'),
    _fb('leads'),
    _fb('contracts'),
    _fb('invoices'),
    _fb('portfolio'),
    _fb('activity_logs'),
  ]);

  const toArr = (result) => {
    if (result.status !== 'fulfilled' || !result.value) return [];
    const val = result.value;
    return Object.entries(val).map(([k, v]) => ({ _key: k, ...v }));
  };

  _analyticsData = {
    builds: toArr(buildsRaw),
    leads: toArr(leadsRaw),
    contracts: toArr(contractsRaw),
    invoices: toArr(invoicesRaw),
    portfolio: toArr(portfolioRaw),
    activity: toArr(activityRaw),
  };

  return _analyticsData;
}

// ── Main refresh entry point ───────────────────────────
async function refreshAnalytics() {
  if (_analyticsLoading) return;
  _analyticsLoading = true;

  const $updated = document.getElementById('analytics-updated');
  if ($updated) $updated.textContent = 'Loading data from Firebase…';

  try {
    await _fetchAllData();

    // Run all renderers in parallel
    await Promise.allSettled([
      _renderRevenue(),
      _renderPipeline(),
      _renderEngagement(),
      _renderBuilds(),
      _renderStorage(),
      _renderActivity(),
      _renderKPIs(),
    ]);

    if ($updated) $updated.textContent = `Last updated: ${new Date().toLocaleTimeString()}`;
  } catch (err) {
    console.error('[Analytics] Refresh failed:', err);
    if ($updated) $updated.textContent = 'Failed to load analytics';
  } finally {
    _analyticsLoading = false;
  }
}

// ── Period filter helper ───────────────────────────────
function _getPeriodDays() {
  const el = document.getElementById('analytics-period');
  return parseInt(el?.value || '30', 10);
}

function _withinPeriod(dateStr) {
  if (!dateStr) return true; // include undated items
  const days = _getPeriodDays();
  if (days >= 365) return true; // all time
  const d = new Date(dateStr);
  const cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - days);
  return d >= cutoff;
}

// ── KPI sidebar cards ──────────────────────────────────
async function _renderKPIs() {
  const { contracts, invoices, portfolio } = _analyticsData;

  const totalRevenue = invoices.reduce((s, inv) => s + parseFloat(inv.total_amount || 0), 0);
  const uniqueClients = new Set([
    ...contracts.map(c => c.client_name),
    ...invoices.map(i => i.client_name),
    ...portfolio.map(p => p.client_name),
  ].filter(Boolean));

  _setText('kpi-revenue', _fmt$(totalRevenue));
  _setText('kpi-clients', uniqueClients.size);
  _setText('kpi-contracts', contracts.length);
  _setText('kpi-invoices', invoices.length);
}

function _setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

// ═══════════════════════════════════════════════════════
//  Section Renderers
// ═══════════════════════════════════════════════════════

// ── Revenue & Payments ─────────────────────────────────
async function _renderRevenue() {
  const { invoices } = _analyticsData;
  const filtered = invoices.filter(i => _withinPeriod(i.due_date || i.paid_at));

  const totalRevenue = filtered.reduce((s, i) => s + parseFloat(i.total_amount || 0), 0);
  const collected = filtered.reduce((s, i) => s + parseFloat(i.amount_paid || 0), 0);
  const outstanding = totalRevenue - collected;
  const rate = _pct(collected, totalRevenue);

  _setText('an-total-revenue', _fmt$(totalRevenue));
  _setText('an-collected', _fmt$(collected));
  _setText('an-outstanding', _fmt$(outstanding));
  _setText('an-collection-rate', rate + '%');

  // Revenue over time chart (group by month)
  const monthMap = {};
  filtered.forEach(inv => {
    const d = inv.due_date || inv.paid_at || inv.created_at;
    if (!d) return;
    const month = d.substring(0, 7); // YYYY-MM
    monthMap[month] = (monthMap[month] || 0) + parseFloat(inv.total_amount || 0);
  });
  const months = Object.keys(monthMap).sort();

  _createChart('chart-revenue', {
    type: 'line',
    data: {
      labels: months.map(m => {
        const [y, mo] = m.split('-');
        return new Date(y, mo - 1).toLocaleDateString('en-US', { month: 'short', year: '2-digit' });
      }),
      datasets: [{
        label: 'Revenue',
        data: months.map(m => monthMap[m]),
        borderColor: COLORS.green,
        backgroundColor: 'rgba(0,255,136,0.1)',
        fill: true,
        tension: 0.4,
        pointRadius: 4,
        pointBackgroundColor: COLORS.green,
      }],
    },
    options: {
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: (ctx) => _fmt$(ctx.raw) } },
      },
      scales: {
        y: { ticks: { callback: (v) => '$' + v.toLocaleString() } },
      },
    },
  });

  // Payment status doughnut
  const statusCounts = { paid: 0, partial: 0, unpaid: 0, overdue: 0 };
  filtered.forEach(inv => {
    const s = inv.payment_status || 'unpaid';
    statusCounts[s] = (statusCounts[s] || 0) + 1;
  });

  _createChart('chart-payment-status', {
    type: 'doughnut',
    data: {
      labels: ['Paid', 'Partial', 'Unpaid', 'Overdue'],
      datasets: [{
        data: [statusCounts.paid, statusCounts.partial, statusCounts.unpaid, statusCounts.overdue],
        backgroundColor: [COLORS.green, COLORS.orange, COLORS.yellow, COLORS.red],
        borderWidth: 0,
      }],
    },
    options: {
      cutout: '65%',
      plugins: {
        legend: { position: 'bottom' },
      },
    },
  });
}

// ── Client Pipeline ────────────────────────────────────
async function _renderPipeline() {
  const { leads, contracts, invoices, portfolio } = _analyticsData;

  // Funnel stages
  const totalLeads = leads.length;
  const contacted = leads.filter(l => l.status === 'contacted' || l.status === 'building' || l.status === 'deployed').length;
  const building = leads.filter(l => l.status === 'building' || l.status === 'deployed').length;
  const deployed = leads.filter(l => l.status === 'deployed').length + portfolio.length;
  const contracted = contracts.length;
  const paid = invoices.filter(i => i.payment_status === 'paid').length;

  const funnel = [
    { label: 'Leads', count: totalLeads, color: COLORS.electric, icon: '📬' },
    { label: 'Contacted', count: contacted, color: COLORS.purple, icon: '📞' },
    { label: 'Building', count: building, color: COLORS.yellow, icon: '🔨' },
    { label: 'Deployed', count: deployed, color: COLORS.orange, icon: '🚀' },
    { label: 'Contracted', count: contracted, color: COLORS.teal, icon: '📝' },
    { label: 'Paid', count: paid, color: COLORS.green, icon: '✅' },
  ];

  const maxCount = Math.max(...funnel.map(f => f.count), 1);
  const $funnel = document.getElementById('pipeline-funnel');
  if ($funnel) {
    $funnel.innerHTML = funnel.map(f => {
      const pct = Math.max(15, (f.count / maxCount) * 100);
      return `
        <div class="flex items-center gap-3">
          <span class="text-lg w-6 text-center">${f.icon}</span>
          <div class="flex-1">
            <div class="flex items-center justify-between mb-1">
              <span class="font-mono text-xs text-gray-400">${f.label}</span>
              <span class="font-mono text-xs font-bold text-white">${f.count}</span>
            </div>
            <div class="w-full bg-surface rounded-full h-5 overflow-hidden border border-border">
              <div class="h-full rounded-full transition-all duration-700" style="width:${pct}%; background:${f.color}; opacity:0.6"></div>
            </div>
          </div>
        </div>`;
    }).join('');
  }

  // Lead niches doughnut
  const nicheCounts = {};
  [...leads, ...portfolio].forEach(l => {
    const n = l.niche || 'Other';
    nicheCounts[n] = (nicheCounts[n] || 0) + 1;
  });
  const nicheLabels = Object.keys(nicheCounts);
  _createChart('chart-niches', {
    type: 'doughnut',
    data: {
      labels: nicheLabels,
      datasets: [{
        data: nicheLabels.map(n => nicheCounts[n]),
        backgroundColor: PALETTE.slice(0, nicheLabels.length),
        borderWidth: 0,
      }],
    },
    options: {
      cutout: '60%',
      plugins: { legend: { position: 'bottom' } },
    },
  });

  // Lead status breakdown
  const statusCounts = {};
  leads.forEach(l => {
    const s = l.status || 'new';
    statusCounts[s] = (statusCounts[s] || 0) + 1;
  });
  const statusLabels = Object.keys(statusCounts);
  _createChart('chart-lead-sources', {
    type: 'doughnut',
    data: {
      labels: statusLabels.map(s => s.charAt(0).toUpperCase() + s.slice(1)),
      datasets: [{
        data: statusLabels.map(s => statusCounts[s]),
        backgroundColor: [COLORS.electric, COLORS.purple, COLORS.yellow, COLORS.green, COLORS.red].slice(0, statusLabels.length),
        borderWidth: 0,
      }],
    },
    options: {
      cutout: '60%',
      plugins: { legend: { position: 'bottom' } },
    },
  });
}

// ── Customer Engagement ────────────────────────────────
async function _renderEngagement() {
  const { contracts, invoices } = _analyticsData;
  const filtered = contracts.filter(c => _withinPeriod(c.signed_at || c.sent_at));
  const filteredInv = invoices.filter(i => _withinPeriod(i.due_date || i.paid_at));

  // Avg deal size
  const amounts = filteredInv.map(i => parseFloat(i.total_amount || 0)).filter(a => a > 0);
  const avgDeal = amounts.length > 0 ? amounts.reduce((a, b) => a + b, 0) / amounts.length : 0;
  _setText('an-avg-deal', _fmt$(avgDeal));

  // Sign rate
  const signed = filtered.filter(c => c.status === 'signed' || c.signed_at).length;
  const total = filtered.length || contracts.length;
  _setText('an-sign-rate', _pct(signed, total) + '%');

  // Avg time to sign (sent_at → signed_at)
  const signTimes = filtered
    .filter(c => c.sent_at && c.signed_at)
    .map(c => _daysBetween(c.sent_at, c.signed_at))
    .filter(d => d !== null && d >= 0);
  const avgSignDays = signTimes.length > 0 ? Math.round(signTimes.reduce((a, b) => a + b, 0) / signTimes.length) : null;
  _setText('an-avg-time-sign', avgSignDays !== null ? avgSignDays + 'd' : '—');

  // Repeat client rate
  const clientContracts = {};
  contracts.forEach(c => {
    if (c.client_name) clientContracts[c.client_name] = (clientContracts[c.client_name] || 0) + 1;
  });
  const totalClients = Object.keys(clientContracts).length;
  const repeats = Object.values(clientContracts).filter(n => n > 1).length;
  _setText('an-repeat-rate', _pct(repeats, totalClients) + '%');

  // Contract status flow
  const flowCounts = {};
  contracts.forEach(c => {
    const s = c.status || 'draft';
    flowCounts[s] = (flowCounts[s] || 0) + 1;
  });
  const flowLabels = Object.keys(flowCounts);
  const flowColors = {
    draft: COLORS.electric, sent: COLORS.purple, viewed: COLORS.orange,
    signed: COLORS.green, completed: COLORS.teal, cancelled: COLORS.red,
  };
  _createChart('chart-contract-flow', {
    type: 'doughnut',
    data: {
      labels: flowLabels.map(s => s.charAt(0).toUpperCase() + s.slice(1)),
      datasets: [{
        data: flowLabels.map(s => flowCounts[s]),
        backgroundColor: flowLabels.map(s => flowColors[s] || '#6B7280'),
        borderWidth: 0,
      }],
    },
    options: {
      cutout: '60%',
      plugins: { legend: { position: 'bottom' } },
    },
  });

  // Monthly activity chart
  const { activity } = _analyticsData;
  const monthActivity = {};
  activity.forEach(a => {
    const d = a.created_at || a.timestamp;
    if (!d) return;
    const month = d.substring(0, 7);
    monthActivity[month] = (monthActivity[month] || 0) + 1;
  });
  const actMonths = Object.keys(monthActivity).sort();
  _createChart('chart-monthly-activity', {
    type: 'bar',
    data: {
      labels: actMonths.map(m => {
        const [y, mo] = m.split('-');
        return new Date(y, mo - 1).toLocaleDateString('en-US', { month: 'short', year: '2-digit' });
      }),
      datasets: [{
        label: 'Events',
        data: actMonths.map(m => monthActivity[m]),
        backgroundColor: COLORS.electric + '80',
        borderColor: COLORS.electric,
        borderWidth: 1,
        borderRadius: 4,
      }],
    },
    options: {
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } },
    },
  });

  // Top clients table
  const clientRevenue = {};
  invoices.forEach(inv => {
    const name = inv.client_name || 'Unknown';
    if (!clientRevenue[name]) clientRevenue[name] = { revenue: 0, paid: 0, contracts: 0, invoices: 0 };
    clientRevenue[name].revenue += parseFloat(inv.total_amount || 0);
    clientRevenue[name].paid += parseFloat(inv.amount_paid || 0);
    clientRevenue[name].invoices++;
  });
  contracts.forEach(c => {
    const name = c.client_name || 'Unknown';
    if (!clientRevenue[name]) clientRevenue[name] = { revenue: 0, paid: 0, contracts: 0, invoices: 0 };
    clientRevenue[name].contracts++;
  });

  const sorted = Object.entries(clientRevenue).sort((a, b) => b[1].revenue - a[1].revenue);
  const $table = document.getElementById('top-clients-table');
  if ($table) {
    if (sorted.length === 0) {
      $table.innerHTML = '<p class="text-xs text-gray-600 font-mono">No client data yet</p>';
    } else {
      $table.innerHTML = `
        <table class="w-full text-xs font-mono">
          <thead><tr class="text-gray-500 border-b border-border">
            <th class="text-left py-2 pr-3">Client</th>
            <th class="text-right py-2 px-2">Revenue</th>
            <th class="text-right py-2 px-2">Paid</th>
            <th class="text-right py-2 px-2">Contracts</th>
            <th class="text-right py-2 pl-2">Invoices</th>
          </tr></thead>
          <tbody>${sorted.map(([name, d]) => `
            <tr class="border-b border-border/30 hover:bg-surface/50">
              <td class="py-2 pr-3 text-white">${_esc(name)}</td>
              <td class="text-right py-2 px-2 text-neon-green">${_fmt$(d.revenue)}</td>
              <td class="text-right py-2 px-2 text-electric">${_fmt$(d.paid)}</td>
              <td class="text-right py-2 px-2 text-gray-400">${d.contracts}</td>
              <td class="text-right py-2 pl-2 text-gray-400">${d.invoices}</td>
            </tr>
          `).join('')}</tbody>
        </table>`;
    }
  }
}

// ── Build Performance ──────────────────────────────────
async function _renderBuilds() {
  const { builds, portfolio } = _analyticsData;
  const filtered = builds.filter(b => _withinPeriod(b.created_at || b.started_at));

  _setText('an-total-builds', filtered.length);

  const success = filtered.filter(b => b.status === 'success' || b.status === 'complete').length;
  _setText('an-build-success', _pct(success, filtered.length) + '%');

  // Avg build time
  const durations = filtered
    .filter(b => b.created_at && b.finished_at)
    .map(b => {
      const ms = new Date(b.finished_at) - new Date(b.created_at);
      return ms / 1000; // seconds
    })
    .filter(s => s > 0 && s < 7200); // filter outliers
  const avgSec = durations.length > 0 ? Math.round(durations.reduce((a, b) => a + b, 0) / durations.length) : 0;
  _setText('an-avg-build-time', avgSec > 0 ? (avgSec < 60 ? avgSec + 's' : Math.round(avgSec / 60) + 'm') : '—');

  _setText('an-sites-live', portfolio.length);

  // Build outcomes doughnut
  const outcomeCounts = {};
  filtered.forEach(b => {
    const s = b.status || 'unknown';
    outcomeCounts[s] = (outcomeCounts[s] || 0) + 1;
  });
  const outcomeLabels = Object.keys(outcomeCounts);
  const outcomeColors = {
    success: COLORS.green, complete: COLORS.green,
    failed: COLORS.red, error: COLORS.red,
    running: COLORS.yellow, pending: COLORS.electric,
    queued: COLORS.purple,
  };
  _createChart('chart-build-outcomes', {
    type: 'doughnut',
    data: {
      labels: outcomeLabels.map(s => s.charAt(0).toUpperCase() + s.slice(1)),
      datasets: [{
        data: outcomeLabels.map(s => outcomeCounts[s]),
        backgroundColor: outcomeLabels.map(s => outcomeColors[s] || '#6B7280'),
        borderWidth: 0,
      }],
    },
    options: {
      cutout: '60%',
      plugins: { legend: { position: 'bottom' } },
    },
  });

  // Builds over time (weekly buckets)
  const weekMap = {};
  filtered.forEach(b => {
    const d = b.created_at || b.started_at;
    if (!d) return;
    const date = new Date(d);
    // Week start (Monday)
    const day = date.getDay();
    const diff = date.getDate() - day + (day === 0 ? -6 : 1);
    const monday = new Date(date.setDate(diff));
    const key = monday.toISOString().substring(0, 10);
    weekMap[key] = (weekMap[key] || 0) + 1;
  });
  const weeks = Object.keys(weekMap).sort();
  _createChart('chart-builds-timeline', {
    type: 'bar',
    data: {
      labels: weeks.map(w => new Date(w).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })),
      datasets: [{
        label: 'Builds',
        data: weeks.map(w => weekMap[w]),
        backgroundColor: COLORS.electric + '80',
        borderColor: COLORS.electric,
        borderWidth: 1,
        borderRadius: 4,
      }],
    },
    options: {
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } },
    },
  });
}

// ── Firebase Storage Monitor ───────────────────────────
async function _renderStorage() {
  // Estimate storage from actual data sizes
  const nodes = ['builds', 'leads', 'contracts', 'invoices', 'portfolio', 'activity_logs', 'signing'];
  const nodeSizes = {};
  let totalBytes = 0;

  for (const node of nodes) {
    try {
      const snap = await (window.__db ? window.__db.ref(node).once('value') : Promise.resolve({ val: () => null }));
      const val = snap.val ? snap.val() : null;
      const json = val ? JSON.stringify(val) : '';
      const bytes = new Blob([json]).size;
      nodeSizes[node] = bytes;
      totalBytes += bytes;
    } catch (_) {
      nodeSizes[node] = 0;
    }
  }

  const FREE_TIER = 1024 * 1024 * 1024; // 1 GB
  const usedPct = Math.min(100, (totalBytes / FREE_TIER) * 100);

  const $bar = document.getElementById('storage-bar');
  const $text = document.getElementById('storage-usage-text');
  if ($bar) $bar.style.width = Math.max(1, usedPct) + '%';
  if ($text) {
    const mb = (totalBytes / (1024 * 1024)).toFixed(2);
    $text.textContent = `${mb} MB / 1 GB (${usedPct.toFixed(2)}%)`;
  }

  // Change bar color based on usage
  if ($bar) {
    if (usedPct > 80) $bar.className = $bar.className.replace(/from-\w+\s+to-\w+/, 'from-red-500 to-red-400');
    else if (usedPct > 50) $bar.className = $bar.className.replace(/from-\w+\s+to-\w+/, 'from-yellow-500 to-orange-400');
  }

  // Storage doughnut
  const nodeLabels = nodes.filter(n => nodeSizes[n] > 0);
  const nodeColors = {
    builds: COLORS.electric, leads: COLORS.purple, contracts: COLORS.teal,
    invoices: COLORS.yellow, portfolio: COLORS.green, activity_logs: COLORS.orange, signing: COLORS.pink,
  };
  _createChart('chart-storage', {
    type: 'doughnut',
    data: {
      labels: nodeLabels.map(n => n.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase())),
      datasets: [{
        data: nodeLabels.map(n => nodeSizes[n]),
        backgroundColor: nodeLabels.map(n => nodeColors[n] || '#6B7280'),
        borderWidth: 0,
      }],
    },
    options: {
      cutout: '60%',
      plugins: {
        legend: { position: 'bottom' },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const bytes = ctx.raw;
              if (bytes > 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
              if (bytes > 1024) return `${(bytes / 1024).toFixed(1)} KB`;
              return `${bytes} B`;
            },
          },
        },
      },
    },
  });

  // Breakdown list
  const $breakdown = document.getElementById('storage-breakdown');
  if ($breakdown) {
    const sortedNodes = nodes.sort((a, b) => nodeSizes[b] - nodeSizes[a]);
    $breakdown.innerHTML = sortedNodes.map(node => {
      const bytes = nodeSizes[node];
      let sizeStr;
      if (bytes > 1024 * 1024) sizeStr = (bytes / (1024 * 1024)).toFixed(2) + ' MB';
      else if (bytes > 1024) sizeStr = (bytes / 1024).toFixed(1) + ' KB';
      else sizeStr = bytes + ' B';

      const pctOfTotal = totalBytes > 0 ? ((bytes / totalBytes) * 100).toFixed(1) : 0;
      const count = _analyticsData[node]?.length || '?';
      const color = nodeColors[node] || '#6B7280';

      return `
        <div class="flex items-center justify-between py-1.5 border-b border-border/30">
          <div class="flex items-center gap-2">
            <div class="w-2.5 h-2.5 rounded-full" style="background:${color}"></div>
            <span class="font-mono text-xs text-gray-300">${node.replace('_', ' ')}</span>
            <span class="text-[0.6rem] text-gray-600">(${count} items)</span>
          </div>
          <div class="flex items-center gap-3">
            <span class="font-mono text-xs text-gray-400">${pctOfTotal}%</span>
            <span class="font-mono text-xs text-white font-semibold">${sizeStr}</span>
          </div>
        </div>`;
    }).join('');
  }
}

// ── Activity Heatmap ───────────────────────────────────
async function _renderActivity() {
  const { activity } = _analyticsData;

  // Daily event counts for last 30 days
  const days = {};
  const today = new Date();
  for (let i = 29; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(d.getDate() - i);
    days[d.toISOString().substring(0, 10)] = 0;
  }

  activity.forEach(a => {
    const d = (a.created_at || a.timestamp || '').substring(0, 10);
    if (d in days) days[d]++;
  });

  const dayLabels = Object.keys(days);
  const dayCounts = Object.values(days);

  _createChart('chart-activity-heatmap', {
    type: 'bar',
    data: {
      labels: dayLabels.map(d => {
        const dt = new Date(d);
        return dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      }),
      datasets: [{
        label: 'Events',
        data: dayCounts,
        backgroundColor: dayCounts.map(c =>
          c === 0 ? 'rgba(42,42,58,0.5)' :
          c <= 2 ? COLORS.electric + '40' :
          c <= 5 ? COLORS.electric + '80' : COLORS.electric
        ),
        borderRadius: 2,
        barPercentage: 0.9,
        categoryPercentage: 0.9,
      }],
    },
    options: {
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { maxRotation: 45, font: { size: 8 } } },
        y: { beginAtZero: true, ticks: { stepSize: 1 } },
      },
    },
  });

  // Recent events list
  const $list = document.getElementById('recent-events-list');
  if ($list) {
    const recent = [...activity]
      .sort((a, b) => (b.created_at || b.timestamp || '').localeCompare(a.created_at || a.timestamp || ''))
      .slice(0, 20);

    if (recent.length === 0) {
      $list.innerHTML = '<p class="text-xs text-gray-600 font-mono">No recent events</p>';
    } else {
      const actionIcons = {
        created: '✨', updated: '📝', sent: '📧', signed: '✍️',
        contract_signed: '✍️', paid: '💰', payment_received: '💰',
        deleted: '🗑️', viewed: '👁️',
      };
      const actionColors = {
        created: 'text-electric', updated: 'text-neon-yellow', sent: 'text-neon-purple',
        signed: 'text-neon-green', contract_signed: 'text-neon-green',
        paid: 'text-neon-green', payment_received: 'text-neon-green',
        deleted: 'text-brand-link', viewed: 'text-neon-orange',
      };

      $list.innerHTML = recent.map(ev => {
        const icon = actionIcons[ev.action] || '📌';
        const color = actionColors[ev.action] || 'text-gray-400';
        const time = ev.created_at || ev.timestamp || '';
        const timeStr = time ? new Date(time).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '';
        const entity = ev.entity_type ? ev.entity_type.charAt(0).toUpperCase() + ev.entity_type.slice(1) : '';
        const detail = ev.entity_id || ev.short_id || '';

        return `
          <div class="flex items-center gap-2 py-1.5 px-2 rounded hover:bg-surface/50 transition">
            <span class="text-sm">${icon}</span>
            <span class="font-mono text-xs ${color} font-semibold">${_esc(ev.action || '?')}</span>
            <span class="text-[0.65rem] text-gray-500">${entity} ${detail}</span>
            <span class="ml-auto text-[0.6rem] text-gray-600 font-mono whitespace-nowrap">${timeStr}</span>
          </div>`;
      }).join('');
    }
  }
}
