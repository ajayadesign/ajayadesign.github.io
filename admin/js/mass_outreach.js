/**
 * Mass Outreach — SMTP Pool, Excel Import, Verification
 * Wires to /api/v1/outreach/mass/* endpoints
 */
(function () {
  'use strict';

  const _API = (typeof API_BASE !== 'undefined') ? API_BASE : `http://${location.hostname}:3001/api/v1`;
  const MASS = `${_API}/outreach/mass`;

  // ── Sub-tab switcher ──────────────────────────────────
  window.switchOutreachMode = function (mode) {
    const agentSection = document.getElementById('agent-outreach-section');
    const massSection = document.getElementById('mass-outreach-section');
    const btnAgent = document.getElementById('outreach-mode-agent');
    const btnMass = document.getElementById('outreach-mode-mass');
    if (!agentSection || !massSection) return;

    const activeClasses = 'bg-electric/10 text-electric border border-electric/30';
    const inactiveClasses = 'text-gray-500 hover:text-gray-300';

    if (mode === 'mass') {
      agentSection.style.display = 'none';
      massSection.classList.remove('hidden');
      btnMass.className = btnMass.className.replace(inactiveClasses, '') + ' ' + activeClasses;
      btnAgent.className = btnAgent.className.replace(activeClasses, '') + ' ' + inactiveClasses;
      massRefreshPool();
      massRefreshProviders();
    } else {
      agentSection.style.display = '';
      massSection.classList.add('hidden');
      btnAgent.className = btnAgent.className.replace(inactiveClasses, '') + ' ' + activeClasses;
      btnMass.className = btnMass.className.replace(activeClasses, '') + ' ' + inactiveClasses;
    }
  };

  // ── API helpers ────────────────────────────────────────
  async function api(path, opts = {}) {
    const url = `${MASS}${path}`;
    const res = await fetch(url, {
      headers: { 'Content-Type': 'application/json', ...opts.headers },
      ...opts,
    });
    if (!res.ok) {
      const body = await res.text();
      throw new Error(`${res.status}: ${body}`);
    }
    return res.json();
  }

  // ── Pool Status ────────────────────────────────────────
  async function massRefreshPool() {
    try {
      const d = await api('/providers/pool-status');
      document.getElementById('mass-pool-total').textContent = d.total_limit || 0;
      document.getElementById('mass-pool-sent').textContent = d.total_sent || 0;
      document.getElementById('mass-pool-remaining').textContent = d.total_remaining || 0;
      document.getElementById('mass-pool-providers').textContent = d.provider_count || 0;
      const pct = d.total_limit > 0
        ? Math.round((d.total_sent / d.total_limit) * 100) : 0;
      document.getElementById('mass-pool-bar-fill').style.width = pct + '%';
    } catch (e) {
      console.warn('Pool status error:', e);
    }
  }
  window.massRefreshPool = massRefreshPool;

  // ── Provider CRUD ──────────────────────────────────────
  async function massRefreshProviders() {
    try {
      const providers = await api('/providers');
      const container = document.getElementById('mass-provider-list');
      if (!providers.length) {
        container.innerHTML = '<div class="text-xs text-gray-600 font-mono text-center py-4">No providers configured. Add your first SMTP provider above.</div>';
        return;
      }
      container.innerHTML = providers.map(p => {
        const pct = p.daily_limit > 0 ? Math.round((p.daily_sent / p.daily_limit) * 100) : 0;
        const color = p.enabled ? 'emerald' : 'gray';
        return `
        <div class="flex items-center gap-3 bg-surface-2 rounded-lg border border-border p-3">
          <div class="w-2 h-2 rounded-full bg-${color}-400 flex-shrink-0"></div>
          <div class="flex-1 min-w-0">
            <div class="text-xs font-mono font-semibold text-gray-300">${esc(p.name)}</div>
            <div class="text-[0.6rem] text-gray-500 font-mono">${esc(p.host)}:${p.port} — ${esc(p.username || '')}</div>
          </div>
          <div class="text-right flex-shrink-0 w-24">
            <div class="text-xs font-mono text-gray-400">${p.daily_sent}/${p.daily_limit}</div>
            <div class="mt-1 h-1 rounded-full bg-surface-1 overflow-hidden">
              <div class="h-full rounded-full bg-${color}-500/60" style="width:${pct}%"></div>
            </div>
          </div>
          <div class="flex gap-1 flex-shrink-0">
            <button onclick="massEditProvider(${p.id})" class="px-2 py-1 text-[0.6rem] text-gray-400 hover:text-electric font-mono transition" title="Edit">✏️</button>
            <button onclick="massToggleProvider(${p.id}, ${!p.enabled})" class="px-2 py-1 text-[0.6rem] text-gray-400 hover:text-yellow-400 font-mono transition" title="${p.enabled ? 'Disable' : 'Enable'}">${p.enabled ? '⏸️' : '▶️'}</button>
            <button onclick="massDeleteProvider(${p.id})" class="px-2 py-1 text-[0.6rem] text-gray-400 hover:text-red-400 font-mono transition" title="Delete">🗑️</button>
          </div>
        </div>`;
      }).join('');
    } catch (e) {
      console.warn('Provider list error:', e);
    }
  }
  window.massRefreshProviders = massRefreshProviders;

  let _providers = {}; // cached for edits
  window.massShowAddProvider = function () {
    document.getElementById('mass-provider-form').classList.remove('hidden');
    document.getElementById('mass-provider-form-title').textContent = 'Add SMTP Provider';
    document.getElementById('mp-edit-id').value = '';
    ['mp-name', 'mp-host', 'mp-username', 'mp-password', 'mp-from'].forEach(id => document.getElementById(id).value = '');
    document.getElementById('mp-port').value = '587';
    document.getElementById('mp-limit').value = '100';
    document.getElementById('mp-priority').value = '0';
    hideMsg();
  };

  window.massEditProvider = async function (id) {
    try {
      const providers = await api('/providers');
      const p = providers.find(x => x.id === id);
      if (!p) return;
      document.getElementById('mass-provider-form').classList.remove('hidden');
      document.getElementById('mass-provider-form-title').textContent = 'Edit Provider: ' + p.name;
      document.getElementById('mp-edit-id').value = id;
      document.getElementById('mp-name').value = p.name || '';
      document.getElementById('mp-host').value = p.host || '';
      document.getElementById('mp-port').value = p.port || 587;
      document.getElementById('mp-username').value = p.username || '';
      document.getElementById('mp-password').value = '';
      document.getElementById('mp-limit').value = p.daily_limit || 100;
      document.getElementById('mp-from').value = p.from_email || '';
      document.getElementById('mp-priority').value = p.priority || 0;
      hideMsg();
    } catch (e) {
      showMsg('Error loading provider: ' + e.message, 'red');
    }
  };

  window.massSaveProvider = async function () {
    const editId = document.getElementById('mp-edit-id').value;
    const payload = {
      name: document.getElementById('mp-name').value.trim(),
      host: document.getElementById('mp-host').value.trim(),
      port: parseInt(document.getElementById('mp-port').value) || 587,
      username: document.getElementById('mp-username').value.trim(),
      daily_limit: parseInt(document.getElementById('mp-limit').value) || 100,
      from_email: document.getElementById('mp-from').value.trim() || null,
      priority: parseInt(document.getElementById('mp-priority').value) || 0,
    };
    const pw = document.getElementById('mp-password').value;
    if (pw) payload.password = pw;

    if (!payload.name || !payload.host || !payload.username) {
      showMsg('Name, Host, and Username are required.', 'red');
      return;
    }
    if (!editId && !pw) {
      showMsg('Password is required for new providers.', 'red');
      return;
    }

    try {
      if (editId) {
        await api(`/providers/${editId}`, { method: 'PATCH', body: JSON.stringify(payload) });
        showMsg('Provider updated!', 'emerald');
      } else {
        await api('/providers', { method: 'POST', body: JSON.stringify(payload) });
        showMsg('Provider added!', 'emerald');
      }
      massRefreshProviders();
      massRefreshPool();
    } catch (e) {
      showMsg('Save error: ' + e.message, 'red');
    }
  };

  window.massCancelProvider = function () {
    document.getElementById('mass-provider-form').classList.add('hidden');
    hideMsg();
  };

  window.massTestProvider = async function () {
    const editId = document.getElementById('mp-edit-id').value;
    if (!editId) {
      showMsg('Save the provider first, then test.', 'yellow');
      return;
    }
    showMsg('Testing connection…', 'sky');
    try {
      const r = await api(`/providers/${editId}/test`, { method: 'POST' });
      if (r.success) {
        showMsg('✅ Connection successful!', 'emerald');
      } else {
        showMsg('❌ ' + (r.error || 'Connection failed'), 'red');
      }
    } catch (e) {
      showMsg('Test error: ' + e.message, 'red');
    }
  };

  window.massToggleProvider = async function (id, enable) {
    try {
      await api(`/providers/${id}`, { method: 'PATCH', body: JSON.stringify({ enabled: enable }) });
      massRefreshProviders();
      massRefreshPool();
    } catch (e) {
      console.warn('Toggle error:', e);
    }
  };

  window.massDeleteProvider = async function (id) {
    if (!confirm('Delete this SMTP provider?')) return;
    try {
      await api(`/providers/${id}`, { method: 'DELETE' });
      massRefreshProviders();
      massRefreshPool();
    } catch (e) {
      showMsg('Delete error: ' + e.message, 'red');
    }
  };

  function showMsg(text, color) {
    const el = document.getElementById('mass-provider-msg');
    el.className = `mt-2 text-xs font-mono px-3 py-2 rounded-lg bg-${color}-600/10 text-${color}-400 border border-${color}-600/30`;
    el.textContent = text;
    el.classList.remove('hidden');
  }
  function hideMsg() {
    document.getElementById('mass-provider-msg').classList.add('hidden');
  }

  // ── File Import ───────────────────────────────────────
  let _importFile = null;

  window.massHandleDrop = function (e) {
    e.preventDefault();
    e.currentTarget.classList.remove('border-electric/50');
    const file = e.dataTransfer.files[0];
    if (file) processImportFile(file);
  };

  window.massHandleFile = function (input) {
    if (input.files[0]) processImportFile(input.files[0]);
  };

  async function processImportFile(file) {
    _importFile = file;
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await fetch(`${MASS}/import/preview`, {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();

      document.getElementById('mass-preview-count').textContent = data.with_email || 0;
      document.getElementById('mass-preview-dedup').textContent = data.duplicates_in_file || 0;
      document.getElementById('mass-preview-noemail').textContent = data.skipped_no_email || 0;

      const tbody = document.getElementById('mass-preview-body');
      const rows = (data.preview || []).slice(0, 50);
      tbody.innerHTML = rows.map(r => `
        <tr class="hover:bg-surface-2/50">
          <td class="px-3 py-1.5">${esc(r.owner_name || r.business_name || '')}</td>
          <td class="px-3 py-1.5">${esc(r.owner_email || '')}</td>
          <td class="px-3 py-1.5">${esc(r.business_type || '')}</td>
          <td class="px-3 py-1.5">${esc(r.city || '')}</td>
          <td class="px-3 py-1.5">${esc(r.phone || '')}</td>
        </tr>
      `).join('');

      document.getElementById('mass-import-preview').classList.remove('hidden');
      document.getElementById('mass-import-result').classList.add('hidden');
    } catch (e) {
      alert('Preview error: ' + e.message);
    }
  }

  window.massExecuteImport = async function () {
    if (!_importFile) return;
    const btn = document.getElementById('mass-import-btn');
    btn.disabled = true;
    btn.textContent = '⏳ Importing…';
    const result = document.getElementById('mass-import-result');

    try {
      const formData = new FormData();
      formData.append('file', _importFile);
      const res = await fetch(`${MASS}/import/execute`, {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();

      result.className = 'mt-3 px-4 py-3 rounded-lg text-xs font-mono bg-emerald-600/10 text-emerald-400 border border-emerald-600/30';
      result.innerHTML = `✅ Imported <strong>${data.created || 0}</strong> prospects (${data.skipped_existing || 0} already existed, ${data.duplicates_in_file || 0} dupes merged)`;
      result.classList.remove('hidden');
    } catch (e) {
      result.className = 'mt-3 px-4 py-3 rounded-lg text-xs font-mono bg-red-600/10 text-red-400 border border-red-600/30';
      result.textContent = '❌ Import failed: ' + e.message;
      result.classList.remove('hidden');
    } finally {
      btn.disabled = false;
      btn.textContent = '🚀 Import All';
    }
  };

  // ── Email Verification ────────────────────────────────
  window.massVerifyBatch = async function () {
    const el = document.getElementById('mass-verify-result');
    el.textContent = '⏳ Verifying batch of 50…';
    try {
      const data = await api('/verify/batch?limit=50', { method: 'POST' });
      el.innerHTML = `Verified <strong>${data.total || 0}</strong>: ${data.verified || 0} valid, ${data.invalid || 0} invalid, ${data.errors || 0} errors`;
      el.className = 'text-xs font-mono text-emerald-400';
    } catch (e) {
      el.textContent = '❌ Verification error: ' + e.message;
      el.className = 'text-xs font-mono text-red-400';
    }
  };

  // ── Helpers ───────────────────────────────────────────
  function esc(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  // ── Activate / Enqueue ────────────────────────────────
  window.massActivatePreview = async function () {
    const el = document.getElementById('mass-activate-result');
    const limit = parseInt(document.getElementById('activate-limit').value) || 200;
    const onlyVerified = document.getElementById('activate-verified-only').checked;
    el.textContent = '⏳ Checking eligible prospects…';
    try {
      const qs = `?limit=${limit}&only_verified=${onlyVerified}`;
      const data = await api('/activate/preview' + qs);
      if (data.total_eligible === 0) {
        el.textContent = 'No eligible imported prospects found. Import more or verify emails first.';
        el.className = 'text-xs font-mono text-yellow-400';
        return;
      }
      const types = Object.entries(data.by_type || {})
        .map(([t, c]) => `${esc(t)}: ${c}`)
        .join(', ');
      el.innerHTML = `<strong>${data.total_eligible}</strong> eligible — will activate <strong>${data.will_activate}</strong><br><span class="text-gray-500">${types}</span>`;
      el.className = 'text-xs font-mono text-emerald-400';
    } catch (e) {
      el.textContent = '❌ Preview error: ' + e.message;
      el.className = 'text-xs font-mono text-red-400';
    }
  };

  window.massActivateBatch = async function () {
    const el = document.getElementById('mass-activate-result');
    const limit = parseInt(document.getElementById('activate-limit').value) || 200;
    const onlyVerified = document.getElementById('activate-verified-only').checked;
    el.textContent = '⏳ Activating… this may take a moment';
    try {
      const data = await api('/activate', {
        method: 'POST',
        body: JSON.stringify({
          limit: limit,
          only_verified: onlyVerified,
        }),
      });
      el.innerHTML = `✅ <strong>${data.activated}</strong> activated, ${data.skipped} skipped, ${data.errors} errors (${data.total} total processed)`;
      el.className = 'text-xs font-mono text-emerald-400';
      // Refresh pool & dashboard counts
      massRefreshPool();
    } catch (e) {
      el.textContent = '❌ Activate error: ' + e.message;
      el.className = 'text-xs font-mono text-red-400';
    }
  };
})();
