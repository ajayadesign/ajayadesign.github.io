/* ═══════════════════════════════════════════════════════
   AjayaDesign Admin — Quote Builder
   Full CRUD, deliverable line items, versioning/revisions,
   email send, public viewer with signing
   ═══════════════════════════════════════════════════════ */

// ── State ──────────────────────────────────────────────
let currentQuote = null;
let quoteDeliverables = [];

// Normalize quote object so quote_id is always set
function _normalizeQuote(q) {
  if (!q) return q;
  // API returns short_id, Firebase uses quote_id — unify
  if (!q.quote_id && q.short_id) q.quote_id = q.short_id;
  if (!q.short_id && q.quote_id) q.short_id = q.quote_id;
  return q;
}

// ── Default deliverables (MMC template) ────────────────
const defaultDeliverables = [
  { description: 'Market Mode — Customer Order Flow',         hours: 16, rate: 75 },
  { description: 'Google Drive API Integration',              hours: 12, rate: 75 },
  { description: 'Firebase Backend & Database',               hours: 10, rate: 75 },
  { description: 'Payment Deep Links (Venmo/PayPal)',         hours:  4, rate: 75 },
  { description: 'Admin Dashboard — Order Management',        hours: 16, rate: 75 },
  { description: 'Event Mode — Photo Capture & Upload',       hours: 14, rate: 75 },
  { description: 'Event Manager & QR Code Generator',         hours:  8, rate: 75 },
  { description: 'Email Notifications',                       hours:  4, rate: 75 },
  { description: 'Testing, QA & Accessibility Audit',         hours:  8, rate: 75 },
  { description: 'Deployment & Launch Support',               hours:  4, rate: 75 },
];

// ── Default quote fields ───────────────────────────────
const defaultQuoteFields = {
  client_name: 'Magnet Moments Co.',
  client_email: '',
  project_name: 'Market & Event Photo Ordering System',
  project_description: 'A custom dual-mode web application for Magnet Moments Co. — enabling on-site photo collection, order management, and payment at markets & events.\n\nMarket Mode: Buyers scan a QR code, enter their info, select a magnet set, upload photos, choose a payment method, and submit.\n\nEvent Mode: Guests scan a QR code, snap or upload photos, and images are automatically collected into a dedicated Google Drive folder.',
  payment_schedule: '50% upfront · 50% at launch',
  valid_days: 30,
  notes: '',
};

// ── Open existing quote ────────────────────────────────
async function openQuote(quoteId) {
  let loaded = false;

  // Try API first
  try {
    const res = await fetch(`${API_BASE}/quotes/${quoteId}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    currentQuote = _normalizeQuote(await res.json());
    quoteDeliverables = (currentQuote.deliverables || []).map(d => ({ ...d }));
    loaded = true;
  } catch (err) {
    console.warn('[Quotes] API failed, trying Firebase:', err.message);
  }

  // Fallback: Firebase RTDB
  if (!loaded && window.__db) {
    try {
      const snap = await window.__db.ref(`quotes/${quoteId}`).once('value');
      const val = snap.val();
      if (val) {
        const rawDel = val.deliverables;
        const fbDel = Array.isArray(rawDel) ? rawDel
          : (rawDel && typeof rawDel === 'object') ? Object.values(rawDel) : [];
        currentQuote = { quote_id: quoteId, ...val, deliverables: fbDel };
        quoteDeliverables = fbDel.length > 0
          ? fbDel.map(d => ({ ...d }))
          : defaultDeliverables.map(d => ({ ...d }));
        loaded = true;
        console.info('[Quotes] Loaded from Firebase (%d deliverables)', quoteDeliverables.length);
      }
    } catch (fbErr) {
      console.warn('[Quotes] Firebase fallback failed:', fbErr.message);
    }
  }

  if (!loaded) {
    alert('Failed to load quote — API and Firebase both unavailable.');
    return;
  }

  _populateQuoteForm();
  hideAllMainPanels();
  document.getElementById('quote-detail').classList.remove('hidden');
}

// ── Open a new quote (pre-filled defaults or from portfolio) ──
function openNewQuote(prefill = {}) {
  currentQuote = { _prefill_build_id: prefill.build_id || null };
  quoteDeliverables = defaultDeliverables.map(d => ({ ...d }));

  // Show editable form, hide approved view
  const $approvedView = document.getElementById('qt-approved-view');
  const $editableForm = document.getElementById('qt-editable-form');
  if ($approvedView) $approvedView.classList.add('hidden');
  if ($editableForm) $editableForm.classList.remove('hidden');

  _clearQuoteForm();

  // Apply defaults
  const d = defaultQuoteFields;
  document.getElementById('qt-client-name').value = d.client_name;
  document.getElementById('qt-client-email').value = d.client_email;
  document.getElementById('qt-project-name').value = d.project_name;
  document.getElementById('qt-project-desc').value = d.project_description;
  document.getElementById('qt-payment-schedule').value = d.payment_schedule;
  document.getElementById('qt-valid-days').value = d.valid_days;

  // Override with explicit prefill
  if (prefill.client_name) document.getElementById('qt-client-name').value = prefill.client_name;
  if (prefill.client_email) document.getElementById('qt-client-email').value = prefill.client_email;
  if (prefill.project_name) document.getElementById('qt-project-name').value = prefill.project_name;
  if (prefill.project_description) document.getElementById('qt-project-desc').value = prefill.project_description;

  renderQuoteDeliverables();
  recalcQuote();
  _updateQuoteStatusBadge('draft');
  document.getElementById('qt-meta').textContent = 'New quote — fill in details and save';
  document.getElementById('qt-revision').textContent = 'v1';
  document.getElementById('qt-signature-section').classList.add('hidden');

  hideAllMainPanels();
  document.getElementById('quote-detail').classList.remove('hidden');
}

// ── Populate form from loaded quote ────────────────────
function _populateQuoteForm() {
  const q = currentQuote;
  if (!q) return;

  _updateQuoteDeleteButton();

  // If approved/signed, show read-only view
  if (q.approved_at || q.status === 'approved') {
    _showApprovedQuoteView(q);
    return;
  }

  // Hide approved view, show editable form
  const $approvedView = document.getElementById('qt-approved-view');
  const $editableForm = document.getElementById('qt-editable-form');
  if ($approvedView) $approvedView.classList.add('hidden');
  if ($editableForm) $editableForm.classList.remove('hidden');

  document.getElementById('qt-client-name').value = q.client_name || '';
  document.getElementById('qt-client-email').value = q.client_email || '';
  document.getElementById('qt-project-name').value = q.project_name || '';
  document.getElementById('qt-project-desc').value = q.project_description || '';
  document.getElementById('qt-payment-schedule').value = q.payment_schedule || '50% upfront · 50% at launch';
  document.getElementById('qt-valid-days').value = q.valid_days || 30;
  document.getElementById('qt-notes').value = q.notes || '';

  const saved = q.deliverables || [];
  if (saved.length > 0 || quoteDeliverables.length === 0) {
    quoteDeliverables = saved.map(d => ({ ...d }));
  }
  renderQuoteDeliverables();
  recalcQuote();

  const rev = q.revision || 1;
  _updateQuoteStatusBadge(q.status);
  document.getElementById('qt-meta').textContent =
    `#${q.quote_id} · Created ${q.created_at ? new Date(q.created_at).toLocaleDateString() : 'N/A'}`;
  document.getElementById('qt-revision').textContent = `v${rev}`;

  // Signature section
  if (q.approved_at) {
    document.getElementById('qt-signature-section').classList.remove('hidden');
    if (q.signature_data) document.getElementById('qt-signature-img').src = q.signature_data;
    document.getElementById('qt-signer-name').textContent = q.signer_name || 'Client';
    document.getElementById('qt-signed-at').textContent = `Approved ${new Date(q.approved_at).toLocaleString()}`;
  } else {
    document.getElementById('qt-signature-section').classList.add('hidden');
  }
}

// ── Approved quote view (read-only) ───────────────────
function _showApprovedQuoteView(q) {
  const $approvedView = document.getElementById('qt-approved-view');
  const $editableForm = document.getElementById('qt-editable-form');
  if ($editableForm) $editableForm.classList.add('hidden');

  if (!$approvedView) {
    const container = document.querySelector('#quote-detail > .flex-1.overflow-y-auto');
    if (!container) return;
    const div = document.createElement('div');
    div.id = 'qt-approved-view';
    container.prepend(div);
    _renderApprovedView(div, q);
  } else {
    $approvedView.classList.remove('hidden');
    _renderApprovedView($approvedView, q);
  }

  _updateQuoteStatusBadge('approved');
  document.getElementById('qt-meta').textContent =
    `#${q.quote_id} · APPROVED · Signed ${q.approved_at ? new Date(q.approved_at).toLocaleString() : 'N/A'}`;
}

function _renderApprovedView($el, q) {
  const total = (q.deliverables || []).reduce((sum, d) => sum + (d.hours || 0) * (d.rate || 0), 0);
  const approvedDate = q.approved_at ? new Date(q.approved_at).toLocaleString('en-US', {
    month: 'long', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit', timeZoneName: 'short'
  }) : 'N/A';

  $el.innerHTML = `
    <div class="mb-6 p-5 rounded-2xl bg-gradient-to-r from-neon-green/10 via-neon-green/5 to-transparent border border-neon-green/30 relative overflow-hidden">
      <div class="absolute top-0 right-0 w-32 h-32 bg-neon-green/5 rounded-full -translate-y-1/2 translate-x-1/2"></div>
      <div class="flex items-center gap-4 relative">
        <div class="w-14 h-14 rounded-2xl bg-neon-green/20 flex items-center justify-center text-3xl">✅</div>
        <div>
          <h2 class="font-mono text-lg font-bold text-neon-green">QUOTE APPROVED</h2>
          <p class="text-sm text-gray-400 font-mono">Approved by <span class="text-white font-semibold">${esc(q.signer_name || 'Client')}</span> on ${esc(approvedDate)}</p>
        </div>
      </div>
    </div>
    <div class="grid grid-cols-2 gap-4 mb-6">
      <div class="bg-surface-2 rounded-xl border border-border p-5">
        <div class="text-[0.6rem] font-mono text-electric uppercase tracking-widest mb-3">Client</div>
        <p class="text-sm text-white font-semibold mb-1">${esc(q.client_name)}</p>
        <p class="text-xs text-gray-400">${esc(q.client_email || '')}</p>
      </div>
      <div class="bg-surface-2 rounded-xl border border-border p-5">
        <div class="text-[0.6rem] font-mono text-neon-purple uppercase tracking-widest mb-3">Project</div>
        <p class="text-sm text-white font-semibold mb-1">${esc(q.project_name)}</p>
        <p class="text-xs text-gray-400">${esc(q.project_description || '').slice(0, 120)}${(q.project_description || '').length > 120 ? '…' : ''}</p>
      </div>
    </div>
    <div class="mb-6 bg-surface-2 rounded-xl border border-neon-green/20 p-5">
      <div class="text-[0.6rem] font-mono text-neon-green uppercase tracking-widest mb-3">Investment</div>
      <div class="space-y-2 mb-4">
        ${(q.deliverables || []).map(d => `
          <div class="flex items-center justify-between text-sm">
            <span class="text-gray-300">${esc(d.description || d.name || '')}</span>
            <span class="font-mono text-gray-500">${d.hours}h × $${d.rate} = <span class="text-white">$${(d.hours * d.rate).toLocaleString()}</span></span>
          </div>
        `).join('')}
      </div>
      <div class="border-t border-border pt-3 flex items-center justify-between">
        <span class="font-mono text-sm font-bold text-white">Total</span>
        <span class="font-mono text-xl font-bold text-neon-green">$${total.toLocaleString()}</span>
      </div>
    </div>
    ${q.signature_data ? `
    <div class="mb-6 bg-surface-2 rounded-xl border border-neon-green/30 p-5">
      <div class="text-[0.6rem] font-mono text-neon-green uppercase tracking-widest mb-3">✍️ Signature</div>
      <div class="flex items-center gap-6">
        <div class="bg-white rounded-lg p-2"><img src="${q.signature_data}" class="h-20 max-w-[200px] object-contain" alt="Client Signature" /></div>
        <div>
          <p class="text-sm text-white font-mono font-semibold">${esc(q.signer_name || 'Client')}</p>
          <p class="text-xs text-gray-500 font-mono">${esc(approvedDate)}</p>
          <p class="text-xs text-gray-600 font-mono mt-1">Quote #${esc(q.quote_id)}</p>
        </div>
      </div>
    </div>` : ''}
  `;
}

function _clearQuoteForm() {
  const ids = ['qt-client-name', 'qt-client-email', 'qt-project-name', 'qt-project-desc',
    'qt-payment-schedule', 'qt-valid-days', 'qt-notes'];
  ids.forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
}

function _updateQuoteStatusBadge(status) {
  const $badge = document.getElementById('qt-status-badge');
  const map = {
    draft:    { text: 'DRAFT', cls: 'bg-gray-800 text-gray-400' },
    sent:     { text: 'SENT', cls: 'bg-electric/20 text-electric' },
    viewed:   { text: 'VIEWED', cls: 'bg-neon-yellow/20 text-neon-yellow' },
    approved: { text: 'APPROVED', cls: 'bg-neon-green/20 text-neon-green' },
    declined: { text: 'DECLINED', cls: 'bg-brand-link/20 text-brand-link' },
    expired:  { text: 'EXPIRED', cls: 'bg-gray-800 text-gray-500' },
    revised:  { text: 'REVISED', cls: 'bg-neon-purple/20 text-neon-purple' },
  };
  const s = map[status] || map.draft;
  $badge.textContent = s.text;
  $badge.className = `px-2.5 py-1 rounded-full text-xs font-mono font-semibold ${s.cls}`;
}

// ── Render deliverable line items ──────────────────────
function renderQuoteDeliverables() {
  const $container = document.getElementById('qt-deliverables-container');
  if (!$container) return;

  $container.innerHTML = quoteDeliverables.map((d, i) => `
    <div class="flex gap-3 items-start bg-surface-2 rounded-lg border border-border p-3">
      <div class="flex-1">
        <input value="${esc(d.description || d.name || '')}" onchange="updateQuoteDeliverable(${i}, 'description', this.value)"
          placeholder="Deliverable description" class="w-full bg-transparent text-sm text-white font-mono focus:outline-none border-b border-transparent focus:border-electric pb-1" />
      </div>
      <div class="w-16">
        <input type="number" value="${d.hours || 0}" onchange="updateQuoteDeliverable(${i}, 'hours', this.value)"
          class="w-full bg-transparent text-sm text-white font-mono text-center focus:outline-none border-b border-transparent focus:border-electric pb-1" min="0" />
        <div class="text-[0.6rem] text-gray-600 text-center mt-0.5">Hours</div>
      </div>
      <div class="w-20">
        <input type="number" step="1" value="${d.rate || 75}" onchange="updateQuoteDeliverable(${i}, 'rate', this.value)"
          class="w-full bg-transparent text-sm text-white font-mono text-right focus:outline-none border-b border-transparent focus:border-electric pb-1" min="0" />
        <div class="text-[0.6rem] text-gray-600 text-right mt-0.5">$/hr</div>
      </div>
      <div class="w-24 text-right">
        <div class="text-sm font-mono text-neon-green py-1">$${((d.hours || 0) * (d.rate || 0)).toLocaleString()}</div>
        <div class="text-[0.6rem] text-gray-600 mt-0.5">Cost</div>
      </div>
      <button onclick="removeQuoteDeliverable(${i})" class="text-gray-600 hover:text-brand-link transition mt-1">✕</button>
    </div>
  `).join('');
}

function addQuoteDeliverable() {
  quoteDeliverables.push({ id: crypto.randomUUID().slice(0,8), description: '', hours: 0, rate: 75, amount: 0 });
  renderQuoteDeliverables();
}

function removeQuoteDeliverable(index) {
  quoteDeliverables.splice(index, 1);
  renderQuoteDeliverables();
  recalcQuote();
}

function updateQuoteDeliverable(index, field, value) {
  if (!quoteDeliverables[index]) return;
  if (field === 'hours' || field === 'rate') {
    quoteDeliverables[index][field] = parseFloat(value) || 0;
  } else {
    quoteDeliverables[index][field] = value;
  }
  renderQuoteDeliverables();
  recalcQuote();
}

function resetQuoteDeliverables() {
  if (!confirm('Reset deliverables to default template?')) return;
  quoteDeliverables = defaultDeliverables.map(d => ({ ...d }));
  renderQuoteDeliverables();
  recalcQuote();
}

function recalcQuote() {
  const totalHours = quoteDeliverables.reduce((sum, d) => sum + (d.hours || 0), 0);
  const totalCost = quoteDeliverables.reduce((sum, d) => sum + (d.hours || 0) * (d.rate || 0), 0);

  document.getElementById('qt-total-hours').textContent = `${totalHours}h`;
  document.getElementById('qt-total-cost').textContent = `$${totalCost.toLocaleString()}`;
}

// ── Quick price update (for counter-offers) ────────────
function quickUpdateRate() {
  const newRate = prompt('New hourly rate for ALL deliverables ($):', quoteDeliverables[0]?.rate || 75);
  if (newRate === null) return;
  const rate = parseFloat(newRate);
  if (isNaN(rate) || rate < 0) { alert('Invalid rate.'); return; }
  quoteDeliverables.forEach(d => d.rate = rate);
  renderQuoteDeliverables();
  recalcQuote();
}

function quickUpdateTotal() {
  const currentTotal = quoteDeliverables.reduce((sum, d) => sum + (d.hours || 0) * (d.rate || 0), 0);
  const newTotal = prompt(`New total project cost (current: $${currentTotal.toLocaleString()}):`);
  if (newTotal === null) return;
  const target = parseFloat(newTotal.replace(/[$,]/g, ''));
  if (isNaN(target) || target <= 0) { alert('Invalid amount.'); return; }

  // Scale all rates proportionally to hit the new total
  const totalHours = quoteDeliverables.reduce((sum, d) => sum + (d.hours || 0), 0);
  if (totalHours === 0) { alert('Add deliverables with hours first.'); return; }
  const newRate = Math.round(target / totalHours);
  quoteDeliverables.forEach(d => d.rate = newRate);
  renderQuoteDeliverables();
  recalcQuote();
}

// ── Save quote ─────────────────────────────────────────
async function saveQuote() {
  const data = _gatherQuoteData();
  if (!data.client_name || !data.client_email || !data.project_name) {
    alert('Please fill in Client Name, Email, and Project Name.');
    return;
  }

  let saved = false;

  // Try API first
  try {
    let res;
    if (currentQuote && currentQuote.quote_id) {
      res = await fetch(`${API_BASE}/quotes/${currentQuote.quote_id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
        signal: AbortSignal.timeout(5000),
      });
    } else {
      const createData = { ...data };
      if (currentQuote && currentQuote._prefill_build_id) createData.build_id = currentQuote._prefill_build_id;
      res = await fetch(`${API_BASE}/quotes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(createData),
        signal: AbortSignal.timeout(5000),
      });
    }

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }

    currentQuote = _normalizeQuote(await res.json());
    quoteDeliverables = (currentQuote.deliverables || []).map(d => ({ ...d }));
    saved = true;
  } catch (apiErr) {
    console.warn('[Quotes] API save failed, trying Firebase:', apiErr.message);
  }

  // Fallback: Firebase RTDB
  if (!saved && window.__db) {
    try {
      const isNew = !currentQuote || !currentQuote.quote_id;
      const quoteId = isNew ? _generateQuoteId() : currentQuote.quote_id;
      const now = new Date().toISOString();

      const fbData = {
        ...data,
        quote_id: quoteId,
        status: (currentQuote && currentQuote.status) || 'draft',
        revision: (currentQuote && currentQuote.revision) || 1,
        created_at: (currentQuote && currentQuote.created_at) || now,
        updated_at: now,
      };

      await window.__db.ref(`quotes/${quoteId}`).set(fbData);
      currentQuote = fbData;
      quoteDeliverables = (fbData.deliverables || []).map(d => ({ ...d }));
      saved = true;
      console.info('[Quotes] Saved to Firebase:', quoteId);
    } catch (fbErr) {
      console.error('[Quotes] Firebase save failed:', fbErr);
    }
  }

  if (saved) {
    _populateQuoteForm();
    if (typeof loadAllQuotes === 'function') loadAllQuotes();
    alert('✅ Quote saved!');
  } else {
    alert('Save failed: API and Firebase both unavailable.');
  }
}

// ── Generate short quote ID ───────────────────────────
function _generateQuoteId() {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
  let id = 'QT-';
  for (let i = 0; i < 6; i++) id += chars[Math.floor(Math.random() * chars.length)];
  return id;
}

// ── Delete quote (draft/expired only) ──────────────────
async function deleteQuote() {
  if (!currentQuote || !currentQuote.quote_id) {
    alert('No saved quote to delete.');
    return;
  }
  const status = (currentQuote.status || 'draft').toLowerCase();
  if (status === 'approved') {
    alert('❌ Cannot delete an approved quote. It is a permanent record.');
    return;
  }
  if (!confirm(`⚠️ Delete quote #${currentQuote.quote_id} for ${currentQuote.client_name}?\n\nThis cannot be undone.`)) return;

  let deleted = false;

  // Try API first
  try {
    const res = await fetch(`${API_BASE}/quotes/${currentQuote.quote_id}`, { method: 'DELETE', signal: AbortSignal.timeout(5000) });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    deleted = true;
  } catch (apiErr) {
    console.warn('[Quotes] API delete failed, trying Firebase:', apiErr.message);
  }

  // Fallback: Firebase
  if (!deleted && window.__db) {
    try {
      await window.__db.ref(`quotes/${currentQuote.quote_id}`).remove();
      deleted = true;
      console.info('[Quotes] Deleted from Firebase:', currentQuote.quote_id);
    } catch (fbErr) {
      console.error('[Quotes] Firebase delete failed:', fbErr);
    }
  }

  if (deleted) {
    alert('🗑️ Quote deleted.');
    currentQuote = null;
    quoteDeliverables = [];
    document.getElementById('quote-detail').classList.add('hidden');
    if (typeof loadAllQuotes === 'function') loadAllQuotes();
  } else {
    alert('Delete failed: API and Firebase both unavailable.');
  }
}

function _updateQuoteDeleteButton() {
  const $btn = document.getElementById('qt-btn-delete');
  if (!$btn) return;
  const status = (currentQuote?.status || 'draft').toLowerCase();
  if (status === 'approved') {
    $btn.classList.add('hidden');
  } else {
    $btn.classList.remove('hidden');
  }
}

function _gatherQuoteData() {
  const totalHours = quoteDeliverables.reduce((sum, d) => sum + (d.hours || 0), 0);
  const totalCost = quoteDeliverables.reduce((sum, d) => sum + (d.hours || 0) * (d.rate || 0), 0);

  // Normalize deliverables for API schema: ensure id, description, amount
  const normalizedDeliverables = quoteDeliverables.map(d => ({
    id: d.id || crypto.randomUUID().slice(0, 8),
    description: d.description || d.name || '',
    hours: d.hours || 0,
    rate: d.rate || 0,
    amount: (d.hours || 0) * (d.rate || 0),
  }));

  return {
    client_name: document.getElementById('qt-client-name').value.trim(),
    client_email: document.getElementById('qt-client-email').value.trim(),
    project_name: document.getElementById('qt-project-name').value.trim(),
    project_description: document.getElementById('qt-project-desc').value.trim(),
    payment_schedule: document.getElementById('qt-payment-schedule').value.trim(),
    valid_days: parseInt(document.getElementById('qt-valid-days').value) || 30,
    custom_notes: document.getElementById('qt-notes').value.trim(),
    deliverables: normalizedDeliverables,
    total_amount: totalCost,
  };
}

// ── Send quote via email ───────────────────────────────
async function sendQuote() {
  if (!currentQuote || !currentQuote.quote_id) {
    alert('Please save the quote first.');
    return;
  }
  if (!confirm(`Send quote to ${currentQuote.client_email}?`)) return;

  let sent = false;

  // Try API first (sends email via Gmail SMTP)
  try {
    const res = await fetch(`${API_BASE}/quotes/${currentQuote.quote_id}/send`, {
      method: 'POST',
      signal: AbortSignal.timeout(5000),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (data.success) sent = true;
  } catch (apiErr) {
    console.warn('[Quotes] API send failed, publishing to Firebase:', apiErr.message);
  }

  // Fallback: publish to Firebase quote_viewer so the public URL works
  // (email won't be sent, but the quote link is shareable)
  if (!sent && window.__db) {
    try {
      const token = _generateQuoteToken();
      const now = new Date().toISOString();
      const viewerData = {
        quote_id: currentQuote.quote_id,
        client_name: currentQuote.client_name,
        client_email: currentQuote.client_email,
        project_name: currentQuote.project_name,
        project_description: currentQuote.project_description || '',
        payment_schedule: currentQuote.payment_schedule || '',
        valid_days: currentQuote.valid_days || 30,
        notes: currentQuote.notes || '',
        deliverables: currentQuote.deliverables || quoteDeliverables,
        total_hours: currentQuote.total_hours || 0,
        total_amount: currentQuote.total_amount || 0,
        revision: currentQuote.revision || 1,
        status: 'sent',
        sent_at: now,
        expires_at: new Date(Date.now() + (currentQuote.valid_days || 30) * 86400000).toISOString(),
      };

      await window.__db.ref(`quote_viewer/${token}`).set(viewerData);
      // Update the quote status in Firebase
      await window.__db.ref(`quotes/${currentQuote.quote_id}/status`).set('sent');
      await window.__db.ref(`quotes/${currentQuote.quote_id}/sent_at`).set(now);
      await window.__db.ref(`quotes/${currentQuote.quote_id}/view_token`).set(token);

      currentQuote.status = 'sent';
      currentQuote.view_token = token;

      const quoteUrl = `${location.origin}/admin/quote.html?token=${token}`;
      _updateQuoteStatusBadge('sent');
      if (typeof loadAllQuotes === 'function') loadAllQuotes();

      // Show the link so admin can copy/share it
      const copyLink = confirm(`✅ Quote published!\n\nQuote link (also copied to clipboard):\n${quoteUrl}\n\nNote: Email send requires the API. You can share this link manually.\n\nCopy link to clipboard?`);
      if (copyLink) {
        try { await navigator.clipboard.writeText(quoteUrl); } catch (_) {}
      }
      return;
    } catch (fbErr) {
      console.error('[Quotes] Firebase publish failed:', fbErr);
      alert('Send failed: API unavailable and Firebase publish failed.');
      return;
    }
  }

  if (sent) {
    alert('✅ Quote sent to ' + currentQuote.client_email);
    _updateQuoteStatusBadge('sent');
    currentQuote.status = 'sent';
    if (typeof loadAllQuotes === 'function') loadAllQuotes();
  }
}

function _generateQuoteToken() {
  const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
  let tok = '';
  for (let i = 0; i < 24; i++) tok += chars[Math.floor(Math.random() * chars.length)];
  return tok;
}

// ── Revise & resend (bump version, set status back to draft) ──
async function reviseQuote() {
  if (!currentQuote || !currentQuote.quote_id) {
    alert('Please save the quote first.');
    return;
  }
  const data = _gatherQuoteData();
  data.revision = (currentQuote.revision || 1) + 1;
  data.status = 'revised';

  if (!confirm(`Create revision v${data.revision} and resend to ${currentQuote.client_email}?`)) return;

  let revised = false;

  // Try API first
  try {
    const patchRes = await fetch(`${API_BASE}/quotes/${currentQuote.quote_id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
      signal: AbortSignal.timeout(5000),
    });
    if (!patchRes.ok) throw new Error(`HTTP ${patchRes.status}`);
    currentQuote = _normalizeQuote(await patchRes.json());

    const sendRes = await fetch(`${API_BASE}/quotes/${currentQuote.quote_id}/send`, {
      method: 'POST',
      signal: AbortSignal.timeout(5000),
    });
    if (!sendRes.ok) throw new Error(`Send HTTP ${sendRes.status}`);
    const sendData = await sendRes.json();
    if (sendData.success) revised = true;
  } catch (apiErr) {
    console.warn('[Quotes] API revise failed, using Firebase:', apiErr.message);
  }

  // Fallback: Firebase save + publish
  if (!revised && window.__db) {
    try {
      const now = new Date().toISOString();
      const fbData = {
        ...currentQuote,
        ...data,
        updated_at: now,
      };
      await window.__db.ref(`quotes/${currentQuote.quote_id}`).set(fbData);
      currentQuote = fbData;

      // Re-publish to viewer with new token
      const token = _generateQuoteToken();
      const viewerData = {
        ...fbData,
        status: 'sent',
        sent_at: now,
        expires_at: new Date(Date.now() + (fbData.valid_days || 30) * 86400000).toISOString(),
      };
      await window.__db.ref(`quote_viewer/${token}`).set(viewerData);
      await window.__db.ref(`quotes/${currentQuote.quote_id}/view_token`).set(token);
      currentQuote.view_token = token;
      revised = true;
    } catch (fbErr) {
      console.error('[Quotes] Firebase revise failed:', fbErr);
    }
  }

  if (revised) {
    quoteDeliverables = (currentQuote.deliverables || []).map(d => ({ ...d }));
    _populateQuoteForm();
    if (typeof loadAllQuotes === 'function') loadAllQuotes();
    alert(`✅ Revision v${data.revision} saved and published!`);
  } else {
    alert('Revise failed: API and Firebase both unavailable.');
  }
}

// ── Create contract from approved quote ────────────────
function createContractFromQuote() {
  if (!currentQuote) return;
  const total = (currentQuote.deliverables || []).reduce((sum, d) => sum + (d.hours || 0) * (d.rate || 0), 0);
  openNewContract({
    client_name: currentQuote.client_name,
    client_email: currentQuote.client_email,
    project_name: currentQuote.project_name,
    project_description: currentQuote.project_description || '',
  });
  // Pre-fill the total
  setTimeout(() => {
    const $total = document.getElementById('ct-total-amount');
    if ($total) $total.value = total;
  }, 100);
}

// ── Create quote from portfolio site ───────────────────
function createQuoteForSite() {
  const site = portfolioSites.find(s => s.short_id === selectedPortfolioId);
  if (!site) return;
  openNewQuote({
    build_id: site.id,
    client_name: site.client_name,
    client_email: site.email || '',
    project_name: `Website for ${site.client_name}`,
    project_description: site.goals || '',
  });
}
