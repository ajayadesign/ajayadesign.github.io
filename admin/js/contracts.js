/* ═══════════════════════════════════════════════════════
   AjayaDesign Admin — Contract Builder + PDF Generation
   Full CRUD, clause toggling, email send, PDF download
   ═══════════════════════════════════════════════════════ */

// ── State ──────────────────────────────────────────────
let currentContract = null;  // Currently loaded contract
let contractClauses = [];    // Current clause list
let defaultClauses = [];     // Default clause library
let contractDefaults = {};   // Default form values from JSON

// ── Load default clause library + form defaults ────────
async function loadDefaultClauses() {
  try {
    const res = await fetch('templates/contract-clauses.json');
    const data = await res.json();
    defaultClauses = data.clauses || [];
    contractDefaults = data.defaults || {};
  } catch (err) {
    console.warn('[Contracts] Failed to load default clauses:', err);
    defaultClauses = [];
    contractDefaults = {};
  }
}

// Load on startup
loadDefaultClauses();

// ── Open a contract (existing) ─────────────────────────
async function openContract(shortId) {
  let loaded = false;

  // Try API first
  try {
    const res = await fetch(`${API_BASE}/contracts/${shortId}`, {
      signal: AbortSignal.timeout(5000),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    currentContract = await res.json();
    contractClauses = (currentContract.clauses || []).map(c => ({ ...c }));
    loaded = true;
  } catch (err) {
    console.warn('[Contracts] API failed, trying Firebase:', err.message);
  }

  // Fallback: Firebase RTDB
  if (!loaded && window.__db) {
    try {
      const snap = await window.__db.ref(`contracts/${shortId}`).once('value');
      const val = snap.val();
      if (val) {
        // Firebase RTDB stores arrays as indexed objects {0:{...},1:{...}}
        const rawClauses = val.clauses;
        const fbClauses = Array.isArray(rawClauses) ? rawClauses
          : (rawClauses && typeof rawClauses === 'object') ? Object.values(rawClauses)
          : [];
        currentContract = { short_id: shortId, ...val, clauses: fbClauses };
        contractClauses = fbClauses.length > 0
          ? fbClauses.map(c => ({ ...c }))
          : defaultClauses.map(c => ({ ...c }));  // Use defaults when Firebase has none
        loaded = true;
        console.info('[Contracts] Loaded from Firebase (%d clauses%s)', contractClauses.length,
          fbClauses.length === 0 ? ' — used defaults' : '');
      }
    } catch (fbErr) {
      console.warn('[Contracts] Firebase fallback failed:', fbErr.message);
    }
  }

  if (!loaded) {
    alert('Failed to load contract — API and Firebase both unavailable.');
    return;
  }

  _populateContractForm();
  hideAllMainPanels();
  document.getElementById('contract-detail').classList.remove('hidden');
}

// ── Open a new contract (pre-filled from portfolio) ────
function openNewContract(prefill = {}) {
  currentContract = null;
  contractClauses = defaultClauses.map(c => ({ ...c }));

  // Ensure we show the editable form, not the signed view
  const $signedView = document.getElementById('ct-signed-view');
  const $editableForm = document.getElementById('ct-editable-form');
  if ($signedView) $signedView.classList.add('hidden');
  if ($editableForm) $editableForm.classList.remove('hidden');

  // Clear form
  _clearContractForm();

  // Apply defaults from JSON first, then override with prefill
  const d = contractDefaults;
  if (d.client_name) document.getElementById('ct-client-name').value = d.client_name;
  if (d.client_email) document.getElementById('ct-client-email').value = d.client_email;
  if (d.project_name) document.getElementById('ct-project-name').value = d.project_name;
  if (d.project_description) document.getElementById('ct-project-desc').value = d.project_description;
  if (d.total_amount) document.getElementById('ct-total-amount').value = d.total_amount;
  if (d.deposit_amount) document.getElementById('ct-deposit-amount').value = d.deposit_amount;
  if (d.payment_method) document.getElementById('ct-payment-method').value = d.payment_method;
  if (d.payment_terms) document.getElementById('ct-payment-terms').value = d.payment_terms;

  // Override with explicit prefill values
  if (prefill.client_name) document.getElementById('ct-client-name').value = prefill.client_name;
  if (prefill.client_email) document.getElementById('ct-client-email').value = prefill.client_email;
  if (prefill.project_name) document.getElementById('ct-project-name').value = prefill.project_name;
  if (prefill.project_description) document.getElementById('ct-project-desc').value = prefill.project_description;

  // Store build_id for linking
  currentContract = { _prefill_build_id: prefill.build_id || null };

  renderClauses();
  _updateContractStatusBadge('draft');
  document.getElementById('ct-meta').textContent = 'New contract — fill in details and save';
  document.getElementById('ct-signature-section').classList.add('hidden');

  hideAllMainPanels();
  document.getElementById('contract-detail').classList.remove('hidden');
}

// ── Populate form from loaded contract ─────────────────
function _populateContractForm() {
  const c = currentContract;
  if (!c) return;

  _updateDeleteButton();

  // If signed, show the beautiful executed contract view instead
  if (c.signed_at || c.status === 'signed') {
    _showSignedContractView(c);
    return;
  }

  // Hide the signed view, show the editable form
  const $signedView = document.getElementById('ct-signed-view');
  const $editableForm = document.getElementById('ct-editable-form');
  if ($signedView) $signedView.classList.add('hidden');
  if ($editableForm) $editableForm.classList.remove('hidden');

  document.getElementById('ct-client-name').value = c.client_name || '';
  document.getElementById('ct-client-email').value = c.client_email || '';
  document.getElementById('ct-client-phone').value = c.client_phone || '';
  document.getElementById('ct-client-address').value = c.client_address || '';
  document.getElementById('ct-project-name').value = c.project_name || '';
  document.getElementById('ct-project-desc').value = c.project_description || '';
  document.getElementById('ct-total-amount').value = c.total_amount || '';
  document.getElementById('ct-deposit-amount').value = c.deposit_amount || '';
  document.getElementById('ct-payment-method').value = c.payment_method || '';
  document.getElementById('ct-start-date').value = c.start_date || '';
  document.getElementById('ct-completion-date').value = c.estimated_completion_date || '';
  document.getElementById('ct-payment-terms').value = c.payment_terms || '';
  document.getElementById('ct-custom-notes').value = c.custom_notes || '';

  // Only overwrite contractClauses from saved data if it has clauses;
  // otherwise keep what openContract() already set (e.g. defaults from Firebase fallback)
  const savedClauses = c.clauses || [];
  if (savedClauses.length > 0 || contractClauses.length === 0) {
    contractClauses = savedClauses.map(cl => ({ ...cl }));
  }
  renderClauses();

  _updateContractStatusBadge(c.status);
  document.getElementById('ct-meta').textContent = `#${c.short_id} · Created ${c.created_at ? new Date(c.created_at).toLocaleDateString() : 'N/A'}`;

  // Signature section (legacy — only for editable view)
  if (c.signed_at) {
    document.getElementById('ct-signature-section').classList.remove('hidden');
    if (c.signature_data) document.getElementById('ct-signature-img').src = c.signature_data;
    document.getElementById('ct-signer-name').textContent = c.signer_name || 'Client';
    document.getElementById('ct-signed-at').textContent = `Signed ${new Date(c.signed_at).toLocaleString()}`;
  } else {
    document.getElementById('ct-signature-section').classList.add('hidden');
  }
}

// ── Beautiful Signed Contract View ─────────────────────
function _showSignedContractView(c) {
  const $signedView = document.getElementById('ct-signed-view');
  const $editableForm = document.getElementById('ct-editable-form');
  if ($editableForm) $editableForm.classList.add('hidden');

  // Create the signed view container if it doesn't exist yet
  if (!$signedView) {
    const container = document.querySelector('#contract-detail > .flex-1.overflow-y-auto');
    if (!container) return;
    const div = document.createElement('div');
    div.id = 'ct-signed-view';
    container.prepend(div);
    _renderSignedView(div, c);
  } else {
    $signedView.classList.remove('hidden');
    _renderSignedView($signedView, c);
  }

  _updateContractStatusBadge('signed');
  document.getElementById('ct-meta').textContent = `#${c.short_id} · EXECUTED CONTRACT · Signed ${c.signed_at ? new Date(c.signed_at).toLocaleString() : 'N/A'}`;
}

function _renderSignedView($el, c) {
  const amount = parseFloat(c.total_amount || 0);
  const deposit = parseFloat(c.deposit_amount || 0);
  const enabledClauses = (c.clauses || []).filter(cl => cl.enabled !== false);
  const signedDate = c.signed_at ? new Date(c.signed_at).toLocaleString('en-US', { month: 'long', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit', timeZoneName: 'short' }) : 'N/A';

  $el.innerHTML = `
    <!-- ═══ Signed Banner ═══ -->
    <div class="mb-6 p-5 rounded-2xl bg-gradient-to-r from-neon-green/10 via-neon-green/5 to-transparent border border-neon-green/30 relative overflow-hidden">
      <div class="absolute top-0 right-0 w-32 h-32 bg-neon-green/5 rounded-full -translate-y-1/2 translate-x-1/2"></div>
      <div class="flex items-center gap-4 relative">
        <div class="w-14 h-14 rounded-2xl bg-neon-green/20 flex items-center justify-center text-3xl">✅</div>
        <div>
          <h2 class="font-mono text-lg font-bold text-neon-green">CONTRACT EXECUTED</h2>
          <p class="text-sm text-gray-400 font-mono">Signed by <span class="text-white font-semibold">${esc(c.signer_name || 'Client')}</span> on ${esc(signedDate)}</p>
        </div>
      </div>
    </div>

    <!-- ═══ Parties ═══ -->
    <div class="grid grid-cols-2 gap-4 mb-6">
      <div class="bg-surface-2 rounded-xl border border-border p-5">
        <div class="text-[0.6rem] font-mono text-electric uppercase tracking-widest mb-3">Provider</div>
        <p class="text-sm text-white font-semibold mb-1">${esc(c.provider_name || 'AjayaDesign')}</p>
        <p class="text-xs text-gray-400">${esc(c.provider_email || 'ajayadesign@gmail.com')}</p>
        ${c.provider_address ? `<p class="text-xs text-gray-500 mt-1">${esc(c.provider_address)}</p>` : ''}
      </div>
      <div class="bg-surface-2 rounded-xl border border-border p-5">
        <div class="text-[0.6rem] font-mono text-neon-purple uppercase tracking-widest mb-3">Client</div>
        <p class="text-sm text-white font-semibold mb-1">${esc(c.client_name)}</p>
        <p class="text-xs text-gray-400">${esc(c.client_email || '')}</p>
        ${c.client_phone ? `<p class="text-xs text-gray-500 mt-1">📱 ${esc(c.client_phone)}</p>` : ''}
        ${c.client_address ? `<p class="text-xs text-gray-500 mt-1">📍 ${esc(c.client_address)}</p>` : ''}
      </div>
    </div>

    <!-- ═══ Project Details ═══ -->
    <div class="mb-6 bg-surface-2 rounded-xl border border-border p-5">
      <div class="text-[0.6rem] font-mono text-electric uppercase tracking-widest mb-3">Project Details</div>
      <h3 class="text-base text-white font-semibold font-mono mb-2">${esc(c.project_name)}</h3>
      ${c.project_description ? `<p class="text-sm text-gray-400 leading-relaxed">${esc(c.project_description)}</p>` : ''}
      <div class="grid grid-cols-2 gap-4 mt-4">
        ${c.start_date ? `<div><span class="text-[0.6rem] text-gray-600 block">Start Date</span><span class="text-sm text-white font-mono">${esc(c.start_date)}</span></div>` : ''}
        ${c.estimated_completion_date ? `<div><span class="text-[0.6rem] text-gray-600 block">Est. Completion</span><span class="text-sm text-white font-mono">${esc(c.estimated_completion_date)}</span></div>` : ''}
      </div>
    </div>

    <!-- ═══ Financial Terms ═══ -->
    <div class="mb-6 bg-surface-2 rounded-xl border border-neon-green/20 p-5">
      <div class="text-[0.6rem] font-mono text-neon-green uppercase tracking-widest mb-3">Financial Terms</div>
      <div class="grid grid-cols-2 gap-4">
        <div>
          <span class="text-[0.6rem] text-gray-600 block">Total Amount</span>
          <span class="text-xl text-neon-green font-mono font-bold">$${amount.toLocaleString('en-US', { minimumFractionDigits: 2 })}</span>
        </div>
        ${deposit > 0 ? `<div>
          <span class="text-[0.6rem] text-gray-600 block">Deposit</span>
          <span class="text-lg text-white font-mono">$${deposit.toLocaleString('en-US', { minimumFractionDigits: 2 })}</span>
        </div>` : ''}
        ${c.payment_method ? `<div>
          <span class="text-[0.6rem] text-gray-600 block">Payment Method</span>
          <span class="text-sm text-white font-mono capitalize">${esc(c.payment_method)}</span>
        </div>` : ''}
      </div>
      ${c.payment_terms ? `<div class="mt-4 pt-3 border-t border-border">
        <span class="text-[0.6rem] text-gray-600 block mb-1">Payment Terms</span>
        <p class="text-sm text-gray-400">${esc(c.payment_terms)}</p>
      </div>` : ''}
    </div>

    <!-- ═══ All Clauses ═══ -->
    <div class="mb-6">
      <div class="text-[0.6rem] font-mono text-electric uppercase tracking-widest mb-3">📋 Contract Clauses (${enabledClauses.length})</div>
      <div class="space-y-3">
        ${enabledClauses.map((clause, i) => {
          const catColors = {
            core: 'border-l-electric',
            technical: 'border-l-neon-purple',
            legal: 'border-l-neon-yellow',
            support: 'border-l-neon-green',
            custom: 'border-l-neon-orange',
          };
          const borderColor = catColors[clause.category] || 'border-l-gray-600';
          return `
            <div class="bg-surface-2 rounded-xl border border-border ${borderColor} border-l-4 p-4">
              <div class="flex items-center gap-2 mb-2">
                <span class="text-sm font-mono font-semibold text-white">${i + 1}. ${esc(clause.title)}</span>
                <span class="text-[0.55rem] font-mono text-gray-600 uppercase px-1.5 py-0.5 bg-surface rounded">${esc(clause.category || '')}</span>
              </div>
              <p class="text-xs text-gray-400 leading-relaxed whitespace-pre-line">${esc(clause.body)}</p>
            </div>`;
        }).join('')}
      </div>
    </div>

    ${c.custom_notes ? `
    <!-- ═══ Custom Notes ═══ -->
    <div class="mb-6 bg-surface-2 rounded-xl border border-border p-5">
      <div class="text-[0.6rem] font-mono text-neon-yellow uppercase tracking-widest mb-3">Additional Notes</div>
      <p class="text-sm text-gray-400 leading-relaxed whitespace-pre-line">${esc(c.custom_notes)}</p>
    </div>` : ''}

    <!-- ═══ Signature ═══ -->
    <div class="mb-6 bg-surface-2 rounded-xl border border-neon-green/30 p-5">
      <div class="text-[0.6rem] font-mono text-neon-green uppercase tracking-widest mb-3">✍️ Signature</div>
      <div class="flex items-center gap-6">
        ${c.signature_data ? `<div class="bg-white rounded-lg p-2"><img src="${c.signature_data}" class="h-20 max-w-[200px] object-contain" alt="Client Signature" /></div>` : '<div class="text-xs text-gray-600 font-mono">Signature data not available</div>'}
        <div>
          <p class="text-sm text-white font-mono font-semibold">${esc(c.signer_name || 'Client')}</p>
          <p class="text-xs text-gray-500 font-mono">${esc(signedDate)}</p>
          <p class="text-xs text-gray-600 font-mono mt-1">Contract #${esc(c.short_id)}</p>
        </div>
      </div>
    </div>

    <!-- ═══ Activity History for this contract ═══ -->
    <div class="mb-6">
      <div class="text-[0.6rem] font-mono text-gray-400 uppercase tracking-widest mb-3">📜 Contract History</div>
      <div id="ct-entity-history" class="space-y-1">
        <p class="text-xs text-gray-600 font-mono">Loading history...</p>
      </div>
    </div>
  `;

  // Load entity-specific history timeline
  if (typeof loadEntityHistory === 'function') {
    loadEntityHistory('contract', c.short_id, document.getElementById('ct-entity-history'));
  }
}

function _clearContractForm() {
  const ids = ['ct-client-name','ct-client-email','ct-client-phone','ct-client-address',
    'ct-project-name','ct-project-desc','ct-total-amount','ct-deposit-amount',
    'ct-payment-method','ct-start-date','ct-completion-date','ct-payment-terms','ct-custom-notes'];
  ids.forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
}

function _updateContractStatusBadge(status) {
  const $badge = document.getElementById('ct-status-badge');
  const map = {
    draft:    { text: 'DRAFT', cls: 'bg-gray-800 text-gray-400' },
    sent:     { text: 'SENT', cls: 'bg-electric/20 text-electric' },
    viewed:   { text: 'VIEWED', cls: 'bg-neon-yellow/20 text-neon-yellow' },
    signed:   { text: 'SIGNED', cls: 'bg-neon-green/20 text-neon-green' },
    completed:{ text: 'COMPLETE', cls: 'bg-neon-green/20 text-neon-green' },
    cancelled:{ text: 'CANCELLED', cls: 'bg-brand-link/20 text-brand-link' },
  };
  const s = map[status] || map.draft;
  $badge.textContent = s.text;
  $badge.className = `px-2.5 py-1 rounded-full text-xs font-mono font-semibold ${s.cls}`;
}

// ── Render clause toggles ──────────────────────────────
let _draggedClauseIdx = null;

function renderClauses() {
  const $container = document.getElementById('ct-clauses-container');
  if (!$container) return;

  $container.innerHTML = contractClauses.map((clause, i) => {
    const categoryColors = {
      core: 'border-electric/20',
      technical: 'border-neon-purple/20',
      legal: 'border-neon-yellow/20',
      support: 'border-neon-green/20',
      custom: 'border-neon-orange/20',
    };
    const borderColor = categoryColors[clause.category] || 'border-border';

    return `
      <div class="clause-item bg-surface-2 rounded-xl border ${borderColor} p-4 ${!clause.enabled ? 'opacity-50' : ''} transition-all duration-200"
           draggable="true" data-clause-idx="${i}"
           ondragstart="_onClauseDragStart(event, ${i})"
           ondragover="_onClauseDragOver(event)"
           ondragenter="_onClauseDragEnter(event)"
           ondragleave="_onClauseDragLeave(event)"
           ondrop="_onClauseDrop(event, ${i})"
           ondragend="_onClauseDragEnd(event)">
        <div class="flex items-center justify-between mb-2">
          <div class="flex items-center gap-2">
            <span class="drag-handle cursor-grab active:cursor-grabbing text-gray-600 hover:text-gray-400 select-none text-sm px-0.5" title="Drag to reorder">⠿</span>
            <div class="flex flex-col -my-1">
              <button onclick="moveClause(${i}, -1)" class="text-gray-600 hover:text-electric transition text-[0.6rem] leading-none ${i === 0 ? 'invisible' : ''}" title="Move up">▲</button>
              <button onclick="moveClause(${i}, 1)" class="text-gray-600 hover:text-electric transition text-[0.6rem] leading-none ${i === contractClauses.length - 1 ? 'invisible' : ''}" title="Move down">▼</button>
            </div>
            <label class="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" ${clause.enabled ? 'checked' : ''} onchange="toggleClause(${i})"
                class="sr-only peer">
              <div class="w-9 h-5 bg-surface-3 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-gray-400 after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-electric/40 peer-checked:after:bg-electric"></div>
            </label>
            <span class="font-mono text-sm font-semibold text-white">${esc(clause.title)}</span>
            <span class="text-[0.6rem] font-mono text-gray-600 uppercase">${clause.category || ''}</span>
          </div>
          <button onclick="removeClause(${i})" class="text-gray-600 hover:text-brand-link transition text-xs">✕</button>
        </div>
        <textarea onchange="updateClauseBody(${i}, this.value)" rows="3"
          class="w-full bg-transparent text-xs text-gray-400 font-mono focus:text-gray-300 focus:outline-none resize-none leading-relaxed">${esc(clause.body)}</textarea>
      </div>`;
  }).join('');
}

// ── Drag-and-drop handlers ─────────────────────────────
function _onClauseDragStart(e, idx) {
  _draggedClauseIdx = idx;
  e.dataTransfer.effectAllowed = 'move';
  e.currentTarget.style.opacity = '0.4';
}
function _onClauseDragOver(e) {
  e.preventDefault();
  e.dataTransfer.dropEffect = 'move';
}
function _onClauseDragEnter(e) {
  e.preventDefault();
  const card = e.currentTarget;
  if (card.classList.contains('clause-item')) {
    card.classList.add('ring-1', 'ring-electric/40');
  }
}
function _onClauseDragLeave(e) {
  const card = e.currentTarget;
  card.classList.remove('ring-1', 'ring-electric/40');
}
function _onClauseDrop(e, targetIdx) {
  e.preventDefault();
  e.currentTarget.classList.remove('ring-1', 'ring-electric/40');
  if (_draggedClauseIdx === null || _draggedClauseIdx === targetIdx) return;

  const [moved] = contractClauses.splice(_draggedClauseIdx, 1);
  contractClauses.splice(targetIdx, 0, moved);
  _draggedClauseIdx = null;
  renderClauses();
}
function _onClauseDragEnd(e) {
  e.currentTarget.style.opacity = '';
  _draggedClauseIdx = null;
  // Clean up any lingering highlights
  document.querySelectorAll('.clause-item').forEach(el => {
    el.classList.remove('ring-1', 'ring-electric/40');
  });
}

// ── Arrow-key move ─────────────────────────────────────
function moveClause(index, direction) {
  const target = index + direction;
  if (target < 0 || target >= contractClauses.length) return;
  const [moved] = contractClauses.splice(index, 1);
  contractClauses.splice(target, 0, moved);
  renderClauses();
}

function toggleClause(index) {
  if (contractClauses[index]) {
    contractClauses[index].enabled = !contractClauses[index].enabled;
    renderClauses();
  }
}

function removeClause(index) {
  contractClauses.splice(index, 1);
  renderClauses();
}

function updateClauseBody(index, newBody) {
  if (contractClauses[index]) {
    contractClauses[index].body = newBody;
  }
}

function resetClausesToDefault() {
  contractClauses = defaultClauses.map(c => ({ ...c }));
  renderClauses();
}

// ── Add a custom clause ────────────────────────────────
function addCustomClause() {
  const title = prompt('Clause heading:');
  if (!title || !title.trim()) return;

  const body = prompt('Clause body text (you can edit it after adding):') || '';

  contractClauses.push({
    id: 'custom-' + Date.now(),
    title: title.trim(),
    body: body.trim(),
    category: 'custom',
    enabled: true,
  });
  renderClauses();

  // Scroll to the newly added clause
  const $container = document.getElementById('ct-clauses-container');
  if ($container) $container.scrollTop = $container.scrollHeight;
}

// ── Log a past contract event (manual history entry) ───
async function logPastContractEvent() {
  if (!currentContract || !currentContract.short_id) {
    alert('Please save the contract first, then log past events.');
    return;
  }

  const action = prompt('What happened? (e.g., "sent", "signed", "payment_received", "voided")');
  if (!action || !action.trim()) return;

  const description = prompt('Description (e.g., "First contract sent to client via email"):') || '';
  const dateStr = prompt('When did this happen? (YYYY-MM-DD, leave blank for today):') || '';

  const metadata = { manual_entry: true };
  if (dateStr) metadata.event_date = dateStr;

  // If this is a payment, ask for amount
  if (action.toLowerCase().includes('payment')) {
    const amount = prompt('Payment amount ($):');
    if (amount) metadata.payment_amount = parseFloat(amount);
  }

  try {
    const res = await fetch(`${API_BASE}/activity`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        entity_type: 'contract',
        entity_id: currentContract.short_id,
        action: action.trim().toLowerCase().replace(/\s+/g, '_'),
        description: description.trim() || `Manual log: ${action}`,
        icon: _actionIcon(action),
        actor: 'admin',
        metadata,
      }),
    });
    if (res.ok) {
      alert('✅ Event logged to history!');
    } else {
      // Fallback: log directly to Firebase
      if (window.__db) {
        const logId = 'manual-' + Date.now();
        await window.__db.ref(`activity_logs/${logId}`).set({
          id: logId,
          entity_type: 'contract',
          entity_id: currentContract.short_id,
          action: action.trim().toLowerCase().replace(/\s+/g, '_'),
          description: description.trim() || `Manual log: ${action}`,
          icon: _actionIcon(action),
          actor: 'admin',
          metadata,
          created_at: dateStr ? new Date(dateStr).toISOString() : new Date().toISOString(),
        });
        alert('✅ Event logged to Firebase!');
      } else {
        alert('⚠️ Failed to log event (API returned ' + res.status + ')');
      }
    }
  } catch (err) {
    console.error('[Contracts] Log event failed:', err);
    alert('Failed to log event: ' + err.message);
  }
}

function _actionIcon(action) {
  const a = (action || '').toLowerCase();
  if (a.includes('sent')) return '📧';
  if (a.includes('sign')) return '✍️';
  if (a.includes('payment') || a.includes('paid')) return '💵';
  if (a.includes('void') || a.includes('cancel')) return '🚫';
  if (a.includes('create')) return '📝';
  if (a.includes('update') || a.includes('amend')) return '✏️';
  return '📋';
}

// ── Save contract ──────────────────────────────────────
async function saveContract() {
  const data = _gatherContractData();
  if (!data.client_name || !data.client_email || !data.project_name) {
    alert('Please fill in Client Name, Email, and Project Name.');
    return;
  }

  let saved = false;

  // Try API first
  try {
    let res;
    if (currentContract && currentContract.short_id) {
      res = await fetch(`${API_BASE}/contracts/${currentContract.short_id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
        signal: AbortSignal.timeout(5000),
      });
    } else {
      const createData = { ...data };
      if (currentContract && currentContract._prefill_build_id) {
        createData.build_id = currentContract._prefill_build_id;
      }
      res = await fetch(`${API_BASE}/contracts`, {
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

    currentContract = await res.json();
    contractClauses = (currentContract.clauses || []).map(c => ({ ...c }));
    saved = true;
  } catch (apiErr) {
    console.warn('[Contracts] API save failed, trying Firebase:', apiErr.message);
  }

  // Fallback: Firebase RTDB
  if (!saved && window.__db) {
    try {
      const isNew = !currentContract || !currentContract.short_id;
      const shortId = isNew ? _generateContractId() : currentContract.short_id;
      const now = new Date().toISOString();

      const fbData = {
        ...data,
        short_id: shortId,
        status: (currentContract && currentContract.status) || 'draft',
        created_at: (currentContract && currentContract.created_at) || now,
        updated_at: now,
      };

      await window.__db.ref(`contracts/${shortId}`).set(fbData);
      currentContract = fbData;
      contractClauses = (fbData.clauses || []).map(c => ({ ...c }));
      saved = true;
      console.info('[Contracts] Saved to Firebase:', shortId);
    } catch (fbErr) {
      console.error('[Contracts] Firebase save failed:', fbErr);
    }
  }

  if (saved) {
    _populateContractForm();
    if (typeof loadAllContracts === 'function') loadAllContracts();
    alert('✅ Contract saved!');
  } else {
    alert('Save failed: API and Firebase both unavailable.');
  }
}

// ── Generate short contract ID ─────────────────────────
function _generateContractId() {
  const hex = '0123456789abcdef';
  let id = '';
  for (let i = 0; i < 8; i++) id += hex[Math.floor(Math.random() * 16)];
  return id;
}

// ── Delete contract (draft only) ───────────────────────
async function deleteContract() {
  if (!currentContract || !currentContract.short_id) {
    alert('No saved contract to delete.');
    return;
  }
  const status = (currentContract.status || 'draft').toLowerCase();
  if (status === 'signed' || status === 'executed' || status === 'completed') {
    alert('❌ Cannot delete a signed/executed contract. It is a permanent record.');
    return;
  }
  if (!confirm(`⚠️ Delete contract #${currentContract.short_id} for ${currentContract.client_name}?\n\nThis cannot be undone.`)) return;

  let deleted = false;

  // Try API first
  try {
    const res = await fetch(`${API_BASE}/contracts/${currentContract.short_id}`, {
      method: 'DELETE',
      signal: AbortSignal.timeout(5000),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    deleted = true;
  } catch (apiErr) {
    console.warn('[Contracts] API delete failed, trying Firebase:', apiErr.message);
  }

  // Fallback: Firebase
  if (!deleted && window.__db) {
    try {
      await window.__db.ref(`contracts/${currentContract.short_id}`).remove();
      deleted = true;
      console.info('[Contracts] Deleted from Firebase:', currentContract.short_id);
    } catch (fbErr) {
      console.error('[Contracts] Firebase delete failed:', fbErr);
    }
  }

  if (deleted) {
    alert('🗑️ Contract deleted.');
    currentContract = null;
    contractClauses = [];
    document.getElementById('contract-detail').classList.add('hidden');
    if (typeof loadAllContracts === 'function') loadAllContracts();
  } else {
    alert('Delete failed: API and Firebase both unavailable.');
  }
}

function _updateDeleteButton() {
  const $btn = document.getElementById('ct-btn-delete');
  if (!$btn) return;
  const status = (currentContract?.status || 'draft').toLowerCase();
  if (status === 'signed' || status === 'executed' || status === 'completed') {
    $btn.classList.add('hidden');
  } else {
    $btn.classList.remove('hidden');
  }
}

function _gatherContractData() {
  return {
    client_name: document.getElementById('ct-client-name').value.trim(),
    client_email: document.getElementById('ct-client-email').value.trim(),
    client_phone: document.getElementById('ct-client-phone').value.trim(),
    client_address: document.getElementById('ct-client-address').value.trim(),
    project_name: document.getElementById('ct-project-name').value.trim(),
    project_description: document.getElementById('ct-project-desc').value.trim(),
    total_amount: parseFloat(document.getElementById('ct-total-amount').value) || 0,
    deposit_amount: parseFloat(document.getElementById('ct-deposit-amount').value) || 0,
    payment_method: document.getElementById('ct-payment-method').value,
    start_date: document.getElementById('ct-start-date').value || null,
    estimated_completion_date: document.getElementById('ct-completion-date').value || null,
    payment_terms: document.getElementById('ct-payment-terms').value.trim(),
    clauses: contractClauses,
    custom_notes: document.getElementById('ct-custom-notes').value.trim(),
  };
}

// ── Send contract via email ────────────────────────────
async function sendContract() {
  if (!currentContract || !currentContract.short_id) {
    alert('Please save the contract first.');
    return;
  }
  if (!confirm(`Send contract to ${currentContract.client_email}?`)) return;

  let sent = false;

  // Try API first (sends email via Gmail SMTP)
  try {
    const res = await fetch(`${API_BASE}/contracts/${currentContract.short_id}/send`, {
      method: 'POST',
      signal: AbortSignal.timeout(5000),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (data.success) sent = true;
  } catch (apiErr) {
    console.warn('[Contracts] API send failed, publishing to Firebase:', apiErr.message);
  }

  // Fallback: publish to Firebase signing/ so the public URL works
  if (!sent && window.__db) {
    try {
      const token = _generateSignToken();
      const now = new Date().toISOString();
      const signingData = {
        short_id: currentContract.short_id,
        client_name: currentContract.client_name,
        client_email: currentContract.client_email,
        project_name: currentContract.project_name,
        project_description: currentContract.project_description || '',
        total_amount: currentContract.total_amount || 0,
        deposit_amount: currentContract.deposit_amount || 0,
        payment_method: currentContract.payment_method || '',
        payment_terms: currentContract.payment_terms || '',
        clauses: currentContract.clauses || contractClauses,
        custom_notes: currentContract.custom_notes || '',
        status: 'sent',
        sent_at: now,
        provider_name: 'AjayaDesign',
        provider_email: 'ajayadesign@gmail.com',
      };

      await window.__db.ref(`signing/${token}`).set(signingData);
      await window.__db.ref(`contracts/${currentContract.short_id}/status`).set('sent');
      await window.__db.ref(`contracts/${currentContract.short_id}/sent_at`).set(now);
      await window.__db.ref(`contracts/${currentContract.short_id}/sign_token`).set(token);

      currentContract.status = 'sent';
      currentContract.sign_token = token;

      const signUrl = `${location.origin}/admin/sign.html?token=${token}`;
      _updateContractStatusBadge('sent');
      if (typeof loadAllContracts === 'function') loadAllContracts();

      const copyLink = confirm(`✅ Contract published!\n\nSigning link:\n${signUrl}\n\nNote: Email send requires the API. You can share this link manually.\n\nCopy link to clipboard?`);
      if (copyLink) {
        try { await navigator.clipboard.writeText(signUrl); } catch (_) {}
      }
      return;
    } catch (fbErr) {
      console.error('[Contracts] Firebase publish failed:', fbErr);
      alert('Send failed: API unavailable and Firebase publish failed.');
      return;
    }
  }

  if (sent) {
    alert('✅ Contract sent to ' + currentContract.client_email);
    _updateContractStatusBadge('sent');
    currentContract.status = 'sent';
    if (typeof loadAllContracts === 'function') loadAllContracts();
  }
}

function _generateSignToken() {
  const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
  let tok = '';
  for (let i = 0; i < 24; i++) tok += chars[Math.floor(Math.random() * chars.length)];
  return tok;
}

// ── PDF Generation (client-side with jsPDF) ────────────
async function downloadContractPDF() {
  const data = currentContract && currentContract.short_id ? currentContract : _gatherContractData();
  if (!data.client_name || !data.project_name) {
    alert('Please fill in at least Client Name and Project Name.');
    return;
  }

  // Wait for jsPDF to load
  if (typeof window.jspdf === 'undefined') {
    alert('PDF library still loading, please try again in a moment.');
    return;
  }

  const { jsPDF } = window.jspdf;
  const doc = new jsPDF();
  const pageWidth = doc.internal.pageSize.getWidth();
  const margin = 20;
  const contentWidth = pageWidth - margin * 2;
  let y = 20;

  // Sanitize text for jsPDF (built-in fonts only support basic Latin)
  function pdfSafe(str) {
    return String(str || '')
      .replace(/\u2192|\u2794|\u27A1/g, '->')   // → arrows
      .replace(/\u2190/g, '<-')                   // ←
      .replace(/\u2194/g, '<->')                  // ↔
      .replace(/\u2013/g, '-')                    // – en dash
      .replace(/\u2014/g, '--')                   // — em dash
      .replace(/\u2018|\u2019/g, "'")             // '' smart quotes
      .replace(/\u201C|\u201D/g, '"')             // "" smart quotes
      .replace(/\u2026/g, '...')                  // … ellipsis
      .replace(/\u00D7/g, 'x')                   // × multiplication
      .replace(/\u2265/g, '>=')                   // ≥
      .replace(/\u2264/g, '<=')                   // ≤
      .replace(/\u2022/g, '*')                    // • bullet (alt)
      .replace(/\u00B7/g, '*')                    // · middle dot
      .replace(/[\u{1F000}-\u{1FFFF}]/gu, '')    // strip all emojis
      .replace(/[^\x00-\x7F\xA0-\xFF]/g, '');    // strip remaining non-Latin-1
  }

  // ── Logo: red dot + "Ajaya" (dark) + "Design" (red)
  const logoX = margin;
  doc.setFillColor(237, 28, 36); // #ED1C24
  doc.circle(logoX + 3, y - 2, 3, 'F');
  doc.setFontSize(16);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(40, 40, 40);
  doc.text('Ajaya', logoX + 9, y);
  const ajayaW = doc.getTextWidth('Ajaya');
  doc.setTextColor(237, 28, 36);
  doc.text('Design', logoX + 9 + ajayaW, y);

  // Right-aligned doc title
  doc.setFontSize(18);
  doc.setTextColor(40, 40, 40);
  doc.text('SERVICE AGREEMENT', pageWidth - margin, y, { align: 'right' });
  y += 6;

  // Thin red accent line
  doc.setDrawColor(237, 28, 36);
  doc.setLineWidth(0.5);
  doc.line(margin, y, pageWidth - margin, y);
  y += 8;

  doc.setFontSize(8);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(120);
  doc.text('Web Development Services  -  ajayadesign@gmail.com', margin, y);
  y += 10;

  // ── Contract ID and Date
  doc.setTextColor(0);
  doc.setFontSize(9);
  const contractId = data.short_id || 'DRAFT';
  const contractDate = data.created_at ? new Date(data.created_at).toLocaleDateString() : new Date().toLocaleDateString();
  doc.text(`Contract #${contractId}  ·  Date: ${contractDate}`, margin, y);
  y += 10;

  // ── Parties
  doc.setFontSize(11);
  doc.setFont('helvetica', 'bold');
  doc.text('PARTIES', margin, y);
  y += 7;

  doc.setFontSize(9);
  doc.setFont('helvetica', 'normal');
  doc.text('Provider: AjayaDesign', margin, y);
  y += 5;
  doc.text('Address: 13721 Andrew Abernathy Pass, Manor, TX 78653', margin, y);
  y += 5;
  doc.text('Email: ajayadesign@gmail.com', margin, y);
  y += 8;

  doc.text(pdfSafe(`Client: ${data.client_name}`), margin, y);
  y += 5;
  if (data.client_address) { doc.text(pdfSafe(`Address: ${data.client_address}`), margin, y); y += 5; }
  if (data.client_email) { doc.text(pdfSafe(`Email: ${data.client_email}`), margin, y); y += 5; }
  if (data.client_phone) { doc.text(pdfSafe(`Phone: ${data.client_phone}`), margin, y); y += 5; }
  y += 8;

  // ── Project Details
  doc.setFontSize(11);
  doc.setFont('helvetica', 'bold');
  doc.text('PROJECT DETAILS', margin, y);
  y += 7;

  doc.setFontSize(9);
  doc.setFont('helvetica', 'normal');
  doc.text(pdfSafe(`Project: ${data.project_name}`), margin, y);
  y += 5;
  if (data.project_description) {
    const descLines = doc.splitTextToSize(pdfSafe(data.project_description), contentWidth);
    doc.text(descLines, margin, y);
    y += descLines.length * 4.5 + 3;
  }

  // ── Financial
  doc.setFontSize(11);
  doc.setFont('helvetica', 'bold');
  doc.text('FINANCIAL TERMS', margin, y);
  y += 7;

  doc.setFontSize(9);
  doc.setFont('helvetica', 'normal');
  const amount = parseFloat(data.total_amount) || 0;
  const deposit = parseFloat(data.deposit_amount) || 0;
  doc.text(`Total Amount: $${amount.toFixed(2)}`, margin, y); y += 5;
  if (deposit > 0) { doc.text(`Deposit: $${deposit.toFixed(2)}`, margin, y); y += 5; }
  if (data.payment_method) { doc.text(pdfSafe(`Payment Method: ${data.payment_method.charAt(0).toUpperCase() + data.payment_method.slice(1)}`), margin, y); y += 5; }
  if (data.start_date) { doc.text(`Start Date: ${data.start_date}`, margin, y); y += 5; }
  if (data.estimated_completion_date) { doc.text(`Est. Completion: ${data.estimated_completion_date}`, margin, y); y += 5; }
  if (data.payment_terms) {
    const ptLines = doc.splitTextToSize(pdfSafe(`Payment Terms: ${data.payment_terms}`), contentWidth);
    doc.text(ptLines, margin, y);
    y += ptLines.length * 4.5 + 3;
  }
  y += 5;

  // ── Clauses (use GUI order from contractClauses if available, else saved data)
  const clauseSource = contractClauses.length > 0 ? contractClauses : (data.clauses || []);
  const enabledClauses = clauseSource.filter(c => c.enabled !== false);

  if (enabledClauses.length > 0) {
    enabledClauses.forEach((clause, i) => {
      // Check if we need a new page
      if (y > 255) { doc.addPage(); y = 20; }

      // Clause heading
      doc.setFontSize(11);
      doc.setFont('helvetica', 'bold');
      doc.setTextColor(40, 40, 40);
      doc.text(pdfSafe(`${i + 1}. ${clause.title}`), margin, y);
      y += 7;

      // Clause body — split by \n\n for paragraphs, then wrap each
      doc.setFontSize(9);
      doc.setFont('helvetica', 'normal');
      doc.setTextColor(60, 60, 60);

      const paragraphs = pdfSafe(clause.body || '').split(/\n\n+/);
      paragraphs.forEach(para => {
        para = para.trim();
        if (!para) return;

        // Detect bullet / numbered lines within a paragraph
        const subLines = para.split('\n');
        subLines.forEach(line => {
          line = line.trim();
          if (!line) return;

          // Check if line is a bullet (•, -, *) or numbered (1., 2.)
          const isBullet = /^[•\-\*]\s/.test(line);
          const isNumbered = /^\d+\.\s/.test(line);
          const indent = (isBullet || isNumbered) ? 6 : 0;
          const lineMargin = margin + indent;
          const lineWidth = contentWidth - indent;

          const wrapped = doc.splitTextToSize(line, lineWidth);
          wrapped.forEach((wl, wIdx) => {
            if (y > 275) { doc.addPage(); y = 20; }
            // First line at full indent; continuation lines get extra indent
            const xPos = wIdx === 0 ? lineMargin : lineMargin + (indent ? 2 : 0);
            doc.text(wl, xPos, y);
            y += 4.5;
          });
        });
        y += 2; // paragraph gap
      });
      y += 4; // gap after clause
    });
  }

  // ── Custom Notes
  if (data.custom_notes) {
    if (y > 250) { doc.addPage(); y = 20; }
    doc.setFontSize(11);
    doc.setFont('helvetica', 'bold');
    doc.text('ADDITIONAL NOTES', margin, y);
    y += 7;
    doc.setFontSize(9);
    doc.setFont('helvetica', 'normal');
    const noteLines = doc.splitTextToSize(pdfSafe(data.custom_notes), contentWidth);
    doc.text(noteLines, margin, y);
    y += noteLines.length * 4.5 + 8;
  }

  // ── Client Signature Section
  if (y > 220) { doc.addPage(); y = 20; }

  const isSigned = !!(data.signature_data && data.status === 'signed');

  doc.setFontSize(11);
  doc.setFont('helvetica', 'bold');
  doc.text(isSigned ? 'EXECUTED BY CLIENT' : 'CLIENT SIGNATURE', margin, y);
  y += 10;

  doc.setFontSize(9);
  doc.setFont('helvetica', 'normal');
  doc.text(pdfSafe(`Client: ${data.client_name}`), margin, y);
  y += 8;

  if (isSigned) {
    // Draw a light grey background box for signature
    doc.setFillColor(248, 248, 248);
    doc.roundedRect(margin, y - 2, 80, 28, 2, 2, 'F');
    try {
      doc.addImage(data.signature_data, 'PNG', margin + 2, y, 76, 24);
    } catch (e) {
      doc.setFontSize(8);
      doc.setTextColor(150);
      doc.text('[signature on file]', margin + 4, y + 14);
      doc.setTextColor(0);
    }
    y += 30;

    // Signer name and date below signature
    doc.setFontSize(8);
    doc.setTextColor(80);
    const signerName = data.signer_name || data.client_name;
    doc.text(pdfSafe(`Signed by: ${signerName}`), margin, y);
    y += 4;
    if (data.signed_at) {
      const signedDate = new Date(data.signed_at);
      doc.text(`Date: ${signedDate.toLocaleDateString()} at ${signedDate.toLocaleTimeString()}`, margin, y);
      y += 4;
    }
    if (data.signer_ip) {
      doc.text(`IP: ${data.signer_ip}`, margin, y);
      y += 4;
    }
    doc.setTextColor(0);
  } else {
    // Unsigned — blank line for future signature
    y += 5;
    doc.line(margin, y, margin + 80, y);
    y += 5;
    doc.text('Signature', margin, y);
    doc.text('Date: _______________', margin + 90, y);
  }

  // Footer on each page
  const pageCount = doc.internal.getNumberOfPages();
  for (let i = 1; i <= pageCount; i++) {
    doc.setPage(i);
    doc.setFontSize(7);
    doc.setTextColor(150);
    doc.text(
      `AjayaDesign Service Agreement · #${contractId} · Page ${i} of ${pageCount}`,
      pageWidth / 2, doc.internal.pageSize.getHeight() - 10,
      { align: 'center' }
    );
  }

  // Download — Chrome ignores the `download` attribute on blob: URLs and
  // uses the blob UUID as the filename. The File System Access API
  // (showSaveFilePicker) is the only reliable way to guarantee the
  // filename in Chrome. Falls back to doc.save() for Firefox / Safari / mobile.
  const filename = `AjayaDesign-Contract-${contractId}-${(data.client_name || 'client').replace(/\s+/g, '-')}.pdf`;

  if (window.showSaveFilePicker) {
    try {
      const handle = await window.showSaveFilePicker({
        suggestedName: filename,
        types: [{ description: 'PDF Document', accept: { 'application/pdf': ['.pdf'] } }],
      });
      const writable = await handle.createWritable();
      await writable.write(doc.output('arraybuffer'));
      await writable.close();
      return;
    } catch (e) {
      if (e.name === 'AbortError') return;   // user cancelled picker
      console.warn('[PDF] File picker failed, using fallback:', e);
    }
  }

  // Fallback for Firefox, Safari, mobile — doc.save works fine there
  doc.save(filename);
}
