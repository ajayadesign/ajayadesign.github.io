/* ═══════════════════════════════════════════════════════
   AjayaDesign Admin — Contract Builder + PDF Generation
   Full CRUD, clause toggling, email send, PDF download
   ═══════════════════════════════════════════════════════ */

// ── State ──────────────────────────────────────────────
let currentContract = null;  // Currently loaded contract
let contractClauses = [];    // Current clause list
let defaultClauses = [];     // Default clause library

// ── Load default clause library ────────────────────────
async function loadDefaultClauses() {
  try {
    const res = await fetch('templates/contract-clauses.json');
    const data = await res.json();
    defaultClauses = data.clauses || [];
  } catch (err) {
    console.warn('[Contracts] Failed to load default clauses:', err);
    defaultClauses = [];
  }
}

// Load on startup
loadDefaultClauses();

// ── Open a contract (existing) ─────────────────────────
async function openContract(shortId) {
  try {
    const res = await fetch(`${API_BASE}/contracts/${shortId}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    currentContract = await res.json();
    contractClauses = (currentContract.clauses || []).map(c => ({ ...c }));
  } catch (err) {
    console.error('[Contracts] Failed to load contract:', err);
    alert('Failed to load contract: ' + err.message);
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

  // Clear form
  _clearContractForm();

  // Pre-fill
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

  contractClauses = (c.clauses || []).map(cl => ({ ...cl }));
  renderClauses();

  _updateContractStatusBadge(c.status);
  document.getElementById('ct-meta').textContent = `#${c.short_id} · Created ${c.created_at ? new Date(c.created_at).toLocaleDateString() : 'N/A'}`;

  // Signature section
  if (c.signed_at) {
    document.getElementById('ct-signature-section').classList.remove('hidden');
    if (c.signature_data) document.getElementById('ct-signature-img').src = c.signature_data;
    document.getElementById('ct-signer-name').textContent = c.signer_name || 'Client';
    document.getElementById('ct-signed-at').textContent = `Signed ${new Date(c.signed_at).toLocaleString()}`;
  } else {
    document.getElementById('ct-signature-section').classList.add('hidden');
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
function renderClauses() {
  const $container = document.getElementById('ct-clauses-container');
  if (!$container) return;

  $container.innerHTML = contractClauses.map((clause, i) => {
    const categoryColors = {
      core: 'border-electric/20',
      technical: 'border-neon-purple/20',
      legal: 'border-neon-yellow/20',
      support: 'border-neon-green/20',
    };
    const borderColor = categoryColors[clause.category] || 'border-border';

    return `
      <div class="bg-surface-2 rounded-xl border ${borderColor} p-4 ${!clause.enabled ? 'opacity-50' : ''}">
        <div class="flex items-center justify-between mb-2">
          <div class="flex items-center gap-3">
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

// ── Save contract ──────────────────────────────────────
async function saveContract() {
  const data = _gatherContractData();
  if (!data.client_name || !data.client_email || !data.project_name) {
    alert('Please fill in Client Name, Email, and Project Name.');
    return;
  }

  try {
    let res;
    if (currentContract && currentContract.short_id) {
      // Update existing
      res = await fetch(`${API_BASE}/contracts/${currentContract.short_id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
    } else {
      // Create new
      const createData = { ...data };
      if (currentContract && currentContract._prefill_build_id) {
        createData.build_id = currentContract._prefill_build_id;
      }
      res = await fetch(`${API_BASE}/contracts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(createData),
      });
    }

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }

    currentContract = await res.json();
    contractClauses = (currentContract.clauses || []).map(c => ({ ...c }));
    _populateContractForm();
    alert('✅ Contract saved!');
  } catch (err) {
    console.error('[Contracts] Save failed:', err);
    alert('Save failed: ' + err.message);
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

  try {
    const res = await fetch(`${API_BASE}/contracts/${currentContract.short_id}/send`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    if (data.success) {
      alert('✅ Contract sent to ' + currentContract.client_email);
      _updateContractStatusBadge('sent');
      currentContract.status = 'sent';
    } else {
      alert('⚠️ ' + (data.message || 'Send failed'));
    }
  } catch (err) {
    console.error('[Contracts] Send failed:', err);
    alert('Send failed: ' + err.message);
  }
}

// ── PDF Generation (client-side with jsPDF) ────────────
function downloadContractPDF() {
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

  // ── Header
  doc.setFontSize(20);
  doc.setFont('helvetica', 'bold');
  doc.text('SERVICE AGREEMENT', pageWidth / 2, y, { align: 'center' });
  y += 10;

  doc.setFontSize(10);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(100);
  doc.text('AjayaDesign Web Development Services', pageWidth / 2, y, { align: 'center' });
  y += 15;

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

  doc.text(`Client: ${data.client_name}`, margin, y);
  y += 5;
  if (data.client_address) { doc.text(`Address: ${data.client_address}`, margin, y); y += 5; }
  if (data.client_email) { doc.text(`Email: ${data.client_email}`, margin, y); y += 5; }
  if (data.client_phone) { doc.text(`Phone: ${data.client_phone}`, margin, y); y += 5; }
  y += 8;

  // ── Project Details
  doc.setFontSize(11);
  doc.setFont('helvetica', 'bold');
  doc.text('PROJECT DETAILS', margin, y);
  y += 7;

  doc.setFontSize(9);
  doc.setFont('helvetica', 'normal');
  doc.text(`Project: ${data.project_name}`, margin, y);
  y += 5;
  if (data.project_description) {
    const descLines = doc.splitTextToSize(data.project_description, contentWidth);
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
  if (data.payment_method) { doc.text(`Payment Method: ${data.payment_method.charAt(0).toUpperCase() + data.payment_method.slice(1)}`, margin, y); y += 5; }
  if (data.start_date) { doc.text(`Start Date: ${data.start_date}`, margin, y); y += 5; }
  if (data.estimated_completion_date) { doc.text(`Est. Completion: ${data.estimated_completion_date}`, margin, y); y += 5; }
  if (data.payment_terms) {
    const ptLines = doc.splitTextToSize(`Payment Terms: ${data.payment_terms}`, contentWidth);
    doc.text(ptLines, margin, y);
    y += ptLines.length * 4.5 + 3;
  }
  y += 5;

  // ── Clauses
  const enabledClauses = (data.clauses || contractClauses || []).filter(c => c.enabled !== false);
  if (enabledClauses.length > 0) {
    enabledClauses.forEach((clause, i) => {
      // Check if we need a new page
      if (y > 260) {
        doc.addPage();
        y = 20;
      }

      doc.setFontSize(10);
      doc.setFont('helvetica', 'bold');
      doc.text(`${i + 1}. ${clause.title}`, margin, y);
      y += 6;

      doc.setFontSize(8.5);
      doc.setFont('helvetica', 'normal');
      const bodyLines = doc.splitTextToSize(clause.body, contentWidth);
      doc.text(bodyLines, margin, y);
      y += bodyLines.length * 4 + 6;
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
    const noteLines = doc.splitTextToSize(data.custom_notes, contentWidth);
    doc.text(noteLines, margin, y);
    y += noteLines.length * 4.5 + 8;
  }

  // ── Signature Section
  if (y > 230) { doc.addPage(); y = 20; }
  doc.setFontSize(11);
  doc.setFont('helvetica', 'bold');
  doc.text('SIGNATURES', margin, y);
  y += 10;

  doc.setFontSize(9);
  doc.setFont('helvetica', 'normal');

  // Provider signature
  doc.text('Provider: AjayaDesign', margin, y);
  y += 12;
  doc.line(margin, y, margin + 80, y);
  y += 5;
  doc.text('Signature', margin, y);
  doc.text('Date: _______________', margin + 90, y);
  y += 15;

  // Client signature
  doc.text(`Client: ${data.client_name}`, margin, y);
  y += 12;

  if (data.signature_data) {
    try {
      doc.addImage(data.signature_data, 'PNG', margin, y - 10, 60, 20);
      y += 12;
    } catch (e) {
      doc.line(margin, y, margin + 80, y);
      y += 5;
    }
  } else {
    doc.line(margin, y, margin + 80, y);
    y += 5;
  }
  doc.text('Signature', margin, y);
  doc.text('Date: _______________', margin + 90, y);

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

  // Download
  const filename = `AjayaDesign-Contract-${contractId}-${(data.client_name || 'client').replace(/\s+/g, '-')}.pdf`;
  doc.save(filename);
}
