/* ═══════════════════════════════════════════════════════
   AjayaDesign Admin — Invoice Management
   Full CRUD, line items, totals, email, PDF, mark paid,
   payment plans with automated reminders
   ═══════════════════════════════════════════════════════ */

// ── State ──────────────────────────────────────────────
let currentInvoice = null;
let invoiceItems = [];
let paymentPlan = [];  // [{id, due_date, amount, status, paid_at, reminder_sent_at}]

// ── PayPal config ──────────────────────────────────────
const PAYPAL_ME = 'ajayadesign';             // paypal.me/ajayadesign
const PAYPAL_FEE_PERCENT = 0.0349;           // 3.49%
const PAYPAL_FEE_FIXED   = 0.49;             // $0.49

/**
 * Calculate the gross amount so that after PayPal takes its fee,
 * the seller receives exactly `netAmount`.
 * Formula: gross = (net + fixed) / (1 - percent)
 */
function calcPayPalGross(netAmount) {
  const gross = (netAmount + PAYPAL_FEE_FIXED) / (1 - PAYPAL_FEE_PERCENT);
  return Math.ceil(gross * 100) / 100; // round up to nearest cent
}

/** Build a PayPal.me link with the fee-adjusted amount */
function getPayPalLink(amount) {
  const gross = calcPayPalGross(amount);
  return `https://paypal.me/${PAYPAL_ME}/${gross.toFixed(2)}USD`;
}

/** Open PayPal payment link for the current invoice */
function payWithPayPal() {
  if (!currentInvoice) { alert('Save the invoice first.'); return; }
  const total = parseFloat(currentInvoice.total_amount) || 0;
  if (total <= 0) { alert('Invoice total must be greater than $0.'); return; }
  const gross = calcPayPalGross(total);
  const fee = (gross - total).toFixed(2);
  if (!confirm(
    `PayPal Payment Link\n\n` +
    `Invoice total: $${total.toFixed(2)}\n` +
    `Processing fee: $${fee} (paid by client)\n` +
    `Client pays: $${gross.toFixed(2)}\n\n` +
    `Open PayPal link?`
  )) return;
  window.open(getPayPalLink(total), '_blank');
}

/** Copy PayPal link to clipboard (to share with client) */
function copyPayPalLink() {
  if (!currentInvoice) { alert('Save the invoice first.'); return; }
  const total = parseFloat(currentInvoice.total_amount) || 0;
  if (total <= 0) { alert('Invoice total must be greater than $0.'); return; }
  const link = getPayPalLink(total);
  navigator.clipboard.writeText(link).then(() => {
    alert('PayPal link copied!\n' + link);
  });
}

// ── Open an existing invoice ───────────────────────────
async function openInvoice(invoiceNumber) {
  try {
    const res = await fetch(`${API_BASE}/invoices/${invoiceNumber}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    currentInvoice = await res.json();
    invoiceItems = (currentInvoice.items || []).map(item => ({ ...item }));
  } catch (err) {
    console.error('[Invoices] Failed to load:', err);
    alert('Failed to load invoice: ' + err.message);
    return;
  }
  _populateInvoiceForm();
  hideAllMainPanels();
  document.getElementById('invoice-detail').classList.remove('hidden');
}

// ── Open a new invoice (pre-filled from portfolio) ─────
function openNewInvoice(prefill = {}) {
  currentInvoice = { _prefill_build_id: prefill.build_id || null, _prefill_contract_id: prefill.contract_id || null };
  invoiceItems = [{ description: 'Website Design & Development', quantity: 1, unit_price: 0, amount: 0 }];

  _clearInvoiceForm();

  if (prefill.client_name) document.getElementById('inv-client-name').value = prefill.client_name;
  if (prefill.client_email) document.getElementById('inv-client-email').value = prefill.client_email;

  renderInvoiceItems();
  recalcInvoice();
  _updateInvoiceStatusBadge('draft');
  document.getElementById('inv-number').textContent = '💰 New Invoice';

  hideAllMainPanels();
  document.getElementById('invoice-detail').classList.remove('hidden');
}

// ── Populate form from loaded invoice ──────────────────
function _populateInvoiceForm() {
  const inv = currentInvoice;
  if (!inv) return;

  document.getElementById('inv-client-name').value = inv.client_name || '';
  document.getElementById('inv-client-email').value = inv.client_email || '';
  document.getElementById('inv-payment-method').value = inv.payment_method || '';
  document.getElementById('inv-due-date').value = inv.due_date || '';
  document.getElementById('inv-tax-rate').value = inv.tax_rate ? (parseFloat(inv.tax_rate) * 100).toFixed(2) : '0';
  document.getElementById('inv-notes').value = inv.notes || '';

  invoiceItems = (inv.items || []).map(item => ({ ...item }));
  renderInvoiceItems();
  recalcInvoice();

  // Payment plan
  paymentPlan = (inv.payment_plan || []).map(inst => ({ ...inst }));
  const ppEnabled = inv.payment_plan_enabled === 'true';
  document.getElementById('inv-payment-plan-enabled').checked = ppEnabled;
  _togglePaymentPlanUI(ppEnabled);
  renderPaymentPlan();

  _updateInvoiceStatusBadge(inv.payment_status || inv.status || 'unpaid');
  document.getElementById('inv-number').textContent = `💰 ${inv.invoice_number}`;
}

function _clearInvoiceForm() {
  const ids = ['inv-client-name', 'inv-client-email', 'inv-payment-method', 'inv-due-date', 'inv-notes'];
  ids.forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
  document.getElementById('inv-tax-rate').value = '0';
  paymentPlan = [];
  document.getElementById('inv-payment-plan-enabled').checked = false;
  _togglePaymentPlanUI(false);
}

function _updateInvoiceStatusBadge(status) {
  const $badge = document.getElementById('inv-status-badge');
  const map = {
    draft:   { text: 'DRAFT', cls: 'bg-gray-800 text-gray-400' },
    sent:    { text: 'SENT', cls: 'bg-electric/20 text-electric' },
    unpaid:  { text: 'UNPAID', cls: 'bg-neon-yellow/20 text-neon-yellow' },
    partial: { text: 'PARTIAL', cls: 'bg-neon-orange/20 text-neon-orange' },
    paid:    { text: 'PAID', cls: 'bg-neon-green/20 text-neon-green' },
    overdue: { text: 'OVERDUE', cls: 'bg-brand-link/20 text-brand-link' },
    cancelled: { text: 'CANCELLED', cls: 'bg-brand-link/20 text-brand-link' },
  };
  const s = map[status] || map.draft;
  $badge.textContent = s.text;
  $badge.className = `px-2.5 py-1 rounded-full text-xs font-mono font-semibold ${s.cls}`;
}

// ── Render line items ──────────────────────────────────
function renderInvoiceItems() {
  const $container = document.getElementById('inv-items-container');
  if (!$container) return;

  $container.innerHTML = invoiceItems.map((item, i) => `
    <div class="flex gap-3 items-start bg-surface-2 rounded-lg border border-border p-3">
      <div class="flex-1">
        <input value="${esc(item.description || '')}" onchange="updateInvoiceItem(${i}, 'description', this.value)"
          placeholder="Description" class="w-full bg-transparent text-sm text-white font-mono focus:outline-none border-b border-transparent focus:border-electric pb-1" />
      </div>
      <div class="w-16">
        <input type="number" value="${item.quantity || 1}" onchange="updateInvoiceItem(${i}, 'quantity', this.value)"
          class="w-full bg-transparent text-sm text-white font-mono text-center focus:outline-none border-b border-transparent focus:border-electric pb-1" />
        <div class="text-[0.6rem] text-gray-600 text-center mt-0.5">Qty</div>
      </div>
      <div class="w-24">
        <input type="number" step="0.01" value="${item.unit_price || 0}" onchange="updateInvoiceItem(${i}, 'unit_price', this.value)"
          class="w-full bg-transparent text-sm text-white font-mono text-right focus:outline-none border-b border-transparent focus:border-electric pb-1" />
        <div class="text-[0.6rem] text-gray-600 text-right mt-0.5">Price</div>
      </div>
      <div class="w-24 text-right">
        <div class="text-sm font-mono text-neon-green py-1">$${(parseFloat(item.amount) || 0).toFixed(2)}</div>
        <div class="text-[0.6rem] text-gray-600 mt-0.5">Amount</div>
      </div>
      <button onclick="removeInvoiceItem(${i})" class="text-gray-600 hover:text-brand-link transition mt-1">✕</button>
    </div>
  `).join('');
}

function addInvoiceItem() {
  invoiceItems.push({ description: '', quantity: 1, unit_price: 0, amount: 0 });
  renderInvoiceItems();
}

function removeInvoiceItem(index) {
  invoiceItems.splice(index, 1);
  renderInvoiceItems();
  recalcInvoice();
}

function updateInvoiceItem(index, field, value) {
  if (!invoiceItems[index]) return;

  if (field === 'quantity' || field === 'unit_price') {
    invoiceItems[index][field] = parseFloat(value) || 0;
    invoiceItems[index].amount = (invoiceItems[index].quantity || 1) * (invoiceItems[index].unit_price || 0);
  } else {
    invoiceItems[index][field] = value;
  }
  renderInvoiceItems();
  recalcInvoice();
}

function recalcInvoice() {
  const subtotal = invoiceItems.reduce((sum, item) => sum + (parseFloat(item.amount) || 0), 0);
  const taxRatePercent = parseFloat(document.getElementById('inv-tax-rate').value) || 0;
  const taxRate = taxRatePercent / 100;
  const taxAmount = subtotal * taxRate;
  const total = subtotal + taxAmount;

  document.getElementById('inv-subtotal').textContent = `$${subtotal.toFixed(2)}`;
  document.getElementById('inv-tax-amount').textContent = `$${taxAmount.toFixed(2)}`;
  document.getElementById('inv-total').textContent = `$${total.toFixed(2)}`;
}

// ── Save invoice ───────────────────────────────────────
async function saveInvoice() {
  const data = _gatherInvoiceData();
  if (!data.client_name || !data.client_email) {
    alert('Please fill in Client Name and Email.');
    return;
  }

  try {
    let res;
    if (currentInvoice && currentInvoice.invoice_number) {
      // Update existing
      res = await fetch(`${API_BASE}/invoices/${currentInvoice.invoice_number}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
    } else {
      // Create new
      const createData = { ...data };
      if (currentInvoice && currentInvoice._prefill_build_id) createData.build_id = currentInvoice._prefill_build_id;
      if (currentInvoice && currentInvoice._prefill_contract_id) createData.contract_id = currentInvoice._prefill_contract_id;
      res = await fetch(`${API_BASE}/invoices`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(createData),
      });
    }

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }

    currentInvoice = await res.json();
    invoiceItems = (currentInvoice.items || []).map(item => ({ ...item }));
    _populateInvoiceForm();
    alert('✅ Invoice saved!');
  } catch (err) {
    console.error('[Invoices] Save failed:', err);
    alert('Save failed: ' + err.message);
  }
}

function _gatherInvoiceData() {
  const subtotal = invoiceItems.reduce((sum, item) => sum + (parseFloat(item.amount) || 0), 0);
  const taxRatePercent = parseFloat(document.getElementById('inv-tax-rate').value) || 0;
  const taxRate = taxRatePercent / 100;
  const taxAmount = subtotal * taxRate;
  const total = subtotal + taxAmount;
  const ppEnabled = document.getElementById('inv-payment-plan-enabled').checked;

  return {
    client_name: document.getElementById('inv-client-name').value.trim(),
    client_email: document.getElementById('inv-client-email').value.trim(),
    payment_method: document.getElementById('inv-payment-method').value,
    due_date: document.getElementById('inv-due-date').value || null,
    items: invoiceItems,
    subtotal: subtotal,
    tax_rate: taxRate,
    tax_amount: taxAmount,
    total_amount: total,
    notes: document.getElementById('inv-notes').value.trim(),
    payment_plan: ppEnabled ? paymentPlan : [],
    payment_plan_enabled: ppEnabled ? 'true' : 'false',
  };
}

// ── Send invoice via email ─────────────────────────────
async function sendInvoice() {
  if (!currentInvoice || !currentInvoice.invoice_number) {
    alert('Please save the invoice first.');
    return;
  }
  if (!confirm(`Send invoice to ${currentInvoice.client_email}?`)) return;

  try {
    const res = await fetch(`${API_BASE}/invoices/${currentInvoice.invoice_number}/send`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    if (data.success) {
      alert('✅ Invoice sent to ' + currentInvoice.client_email);
      _updateInvoiceStatusBadge('sent');
    } else {
      alert('⚠️ ' + (data.message || 'Send failed'));
    }
  } catch (err) {
    console.error('[Invoices] Send failed:', err);
    alert('Send failed: ' + err.message);
  }
}

// ── Mark invoice as paid ───────────────────────────────
async function markInvoicePaid() {
  if (!currentInvoice || !currentInvoice.invoice_number) {
    alert('Please save the invoice first.');
    return;
  }
  if (!confirm('Mark this invoice as fully paid?')) return;

  try {
    const res = await fetch(`${API_BASE}/invoices/${currentInvoice.invoice_number}/mark-paid`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    currentInvoice = await res.json();
    _populateInvoiceForm();
    alert('✅ Invoice marked as paid!');
  } catch (err) {
    console.error('[Invoices] Mark paid failed:', err);
    alert('Mark paid failed: ' + err.message);
  }
}

// ── PDF Generation ─────────────────────────────────────
function downloadInvoicePDF() {
  const data = currentInvoice && currentInvoice.invoice_number ? currentInvoice : _gatherInvoiceData();
  if (!data.client_name) {
    alert('Please fill in at least Client Name.');
    return;
  }

  if (typeof window.jspdf === 'undefined') {
    alert('PDF library still loading, please try again.');
    return;
  }

  const { jsPDF } = window.jspdf;
  const doc = new jsPDF();
  const pageWidth = doc.internal.pageSize.getWidth();
  const margin = 20;
  const contentWidth = pageWidth - margin * 2;
  let y = 20;

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
  doc.setFontSize(20);
  doc.setTextColor(40, 40, 40);
  doc.text('INVOICE', pageWidth - margin, y, { align: 'right' });
  y += 6;

  // Thin red accent line
  doc.setDrawColor(237, 28, 36);
  doc.setLineWidth(0.5);
  doc.line(margin, y, pageWidth - margin, y);
  y += 10;

  // Invoice number and date
  const invNum = data.invoice_number || 'DRAFT';
  doc.setFontSize(10);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(100);
  doc.text(`${invNum}  ·  ${new Date().toLocaleDateString()}`, pageWidth / 2, y, { align: 'center' });
  y += 15;

  // From / To
  doc.setTextColor(0);
  doc.setFontSize(9);
  doc.setFont('helvetica', 'bold');
  doc.text('FROM', margin, y);
  doc.text('TO', pageWidth / 2 + 10, y);
  y += 6;

  doc.setFont('helvetica', 'normal');
  doc.text('AjayaDesign', margin, y);
  doc.text(data.client_name, pageWidth / 2 + 10, y);
  y += 5;
  doc.text('13721 Andrew Abernathy Pass', margin, y);
  doc.text(data.client_email || '', pageWidth / 2 + 10, y);
  y += 5;
  doc.text('Manor, TX 78653', margin, y);
  y += 5;
  doc.text('ajayadesign@gmail.com', margin, y);
  y += 12;

  // Line items table
  doc.setFillColor(240, 240, 245);
  doc.rect(margin, y, contentWidth, 8, 'F');
  doc.setFontSize(8);
  doc.setFont('helvetica', 'bold');
  doc.text('Description', margin + 2, y + 5.5);
  doc.text('Qty', margin + 100, y + 5.5, { align: 'center' });
  doc.text('Unit Price', margin + 125, y + 5.5, { align: 'right' });
  doc.text('Amount', margin + contentWidth - 2, y + 5.5, { align: 'right' });
  y += 12;

  doc.setFont('helvetica', 'normal');
  const items = data.items || invoiceItems || [];
  items.forEach(item => {
    doc.text(item.description || '', margin + 2, y);
    doc.text(String(item.quantity || 1), margin + 100, y, { align: 'center' });
    doc.text(`$${(parseFloat(item.unit_price) || 0).toFixed(2)}`, margin + 125, y, { align: 'right' });
    doc.text(`$${(parseFloat(item.amount) || 0).toFixed(2)}`, margin + contentWidth - 2, y, { align: 'right' });
    y += 7;
  });

  y += 5;
  doc.line(margin + 90, y, margin + contentWidth, y);
  y += 8;

  // Totals
  const subtotal = parseFloat(data.subtotal) || items.reduce((s, i) => s + (parseFloat(i.amount) || 0), 0);
  const taxRate = parseFloat(data.tax_rate) || 0;
  const taxAmount = parseFloat(data.tax_amount) || subtotal * taxRate;
  const total = parseFloat(data.total_amount) || subtotal + taxAmount;

  doc.text('Subtotal:', margin + 110, y, { align: 'right' });
  doc.text(`$${subtotal.toFixed(2)}`, margin + contentWidth - 2, y, { align: 'right' });
  y += 6;

  if (taxRate > 0) {
    doc.text(`Tax (${(taxRate * 100).toFixed(2)}%):`, margin + 110, y, { align: 'right' });
    doc.text(`$${taxAmount.toFixed(2)}`, margin + contentWidth - 2, y, { align: 'right' });
    y += 6;
  }

  doc.setFontSize(12);
  doc.setFont('helvetica', 'bold');
  doc.text('Total:', margin + 110, y, { align: 'right' });
  doc.text(`$${total.toFixed(2)}`, margin + contentWidth - 2, y, { align: 'right' });
  y += 12;

  // Payment info
  doc.setFontSize(9);
  doc.setFont('helvetica', 'normal');
  if (data.payment_method) {
    doc.text(`Payment Method: ${data.payment_method.charAt(0).toUpperCase() + data.payment_method.slice(1)}`, margin, y);
    y += 5;
  }
  if (data.due_date) {
    doc.text(`Due Date: ${data.due_date}`, margin, y);
    y += 5;
  }

  // PayPal payment link (if method is paypal or always show as option)
  if (total > 0 && (!data.payment_method || data.payment_method === 'paypal')) {
    y += 4;
    const gross = calcPayPalGross(total);
    const fee = (gross - total).toFixed(2);
    doc.setFillColor(0, 112, 186); // PayPal blue
    doc.roundedRect(margin, y - 4, contentWidth, 24, 2, 2, 'F');
    doc.setFontSize(11);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(255, 255, 255);
    doc.text('Pay with PayPal', margin + contentWidth / 2, y + 4, { align: 'center' });
    doc.setFontSize(8);
    doc.setFont('helvetica', 'normal');
    doc.text(`paypal.me/${PAYPAL_ME}/${gross.toFixed(2)}USD`, margin + contentWidth / 2, y + 10, { align: 'center' });
    doc.text(`(Includes $${fee} processing fee)`, margin + contentWidth / 2, y + 15, { align: 'center' });
    doc.setTextColor(0);
    // Make the PayPal rect clickable as a link
    doc.link(margin, y - 4, contentWidth, 24, { url: getPayPalLink(total) });
    y += 26;
  }

  // Notes
  if (data.notes) {
    y += 5;
    doc.setFont('helvetica', 'bold');
    doc.text('Notes:', margin, y);
    y += 5;
    doc.setFont('helvetica', 'normal');
    const noteLines = doc.splitTextToSize(data.notes, contentWidth);
    doc.text(noteLines, margin, y);
  }

  // Footer
  doc.setFontSize(7);
  doc.setTextColor(150);
  doc.text(
    `AjayaDesign Invoice · ${invNum} · Thank you for your business!`,
    pageWidth / 2, doc.internal.pageSize.getHeight() - 10,
    { align: 'center' }
  );

  const filename = `AjayaDesign-${invNum}-${(data.client_name || 'client').replace(/\s+/g, '-')}.pdf`;
  doc.save(filename);
}

// ── Log a past invoice event (manual history entry) ────
async function logPastInvoiceEvent() {
  if (!currentInvoice || !currentInvoice.invoice_number) {
    alert('Please save the invoice first, then log past events.');
    return;
  }

  const action = prompt('What happened? (e.g., "sent", "payment_received", "partial_payment", "refunded")');
  if (!action || !action.trim()) return;

  const description = prompt('Description (e.g., "Client paid $500 deposit via Zelle"):') || '';
  const dateStr = prompt('When did this happen? (YYYY-MM-DD, leave blank for today):') || '';

  const metadata = { manual_entry: true };
  if (dateStr) metadata.event_date = dateStr;

  if (action.toLowerCase().includes('payment') || action.toLowerCase().includes('paid')) {
    const amount = prompt('Payment amount ($):');
    if (amount) metadata.payment_amount = parseFloat(amount);
  }

  try {
    const res = await fetch(`${API_BASE}/activity`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        entity_type: 'invoice',
        entity_id: currentInvoice.invoice_number,
        action: action.trim().toLowerCase().replace(/\s+/g, '_'),
        description: description.trim() || `Manual log: ${action}`,
        icon: action.toLowerCase().includes('payment') || action.toLowerCase().includes('paid') ? '💵' : '📋',
        actor: 'admin',
        metadata,
      }),
    });
    if (res.ok) {
      alert('✅ Event logged to history!');
    } else {
      if (window.__db) {
        const logId = 'manual-' + Date.now();
        await window.__db.ref(`activity_logs/${logId}`).set({
          id: logId,
          entity_type: 'invoice',
          entity_id: currentInvoice.invoice_number,
          action: action.trim().toLowerCase().replace(/\s+/g, '_'),
          description: description.trim() || `Manual log: ${action}`,
          icon: '📋',
          actor: 'admin',
          metadata,
          created_at: dateStr ? new Date(dateStr).toISOString() : new Date().toISOString(),
        });
        alert('✅ Event logged to Firebase!');
      } else {
        alert('⚠️ Failed to log event.');
      }
    }
  } catch (err) {
    console.error('[Invoices] Log event failed:', err);
    alert('Failed to log event: ' + err.message);
  }
}

// ═══════════════════════════════════════════════════════
//  Payment Plan Management
// ═══════════════════════════════════════════════════════

/** Toggle the payment plan UI visibility */
function togglePaymentPlan() {
  const enabled = document.getElementById('inv-payment-plan-enabled').checked;
  _togglePaymentPlanUI(enabled);
}

function _togglePaymentPlanUI(show) {
  const els = ['pp-controls', 'pp-installments', 'pp-summary'];
  els.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.classList.toggle('hidden', !show);
  });
  if (show) renderPaymentPlan();
}

/** Auto-generate installments from the invoice total */
function generatePaymentPlan() {
  const total = _getCurrentTotal();
  if (total <= 0) {
    alert('Please add line items first (total must be > $0).');
    return;
  }

  const numInstallments = parseInt(document.getElementById('pp-num-installments').value) || 4;
  const amountPaid = currentInvoice ? parseFloat(currentInvoice.amount_paid || 0) : 0;
  const remaining = total - amountPaid;

  if (remaining <= 0) {
    alert('Invoice is already fully paid.');
    return;
  }

  const perInstallment = Math.floor(remaining / numInstallments * 100) / 100;
  const lastInstallment = remaining - perInstallment * (numInstallments - 1);

  // Start from today, monthly intervals
  const startDate = new Date();
  paymentPlan = [];

  for (let i = 0; i < numInstallments; i++) {
    const dueDate = new Date(startDate);
    dueDate.setMonth(dueDate.getMonth() + i);
    // Set to 1st of the month for clean dates (if generating fresh)
    if (i > 0) dueDate.setDate(1);

    const amount = i === numInstallments - 1 ? lastInstallment : perInstallment;

    paymentPlan.push({
      id: 'inst-' + Date.now() + '-' + i,
      due_date: dueDate.toISOString().split('T')[0],
      amount: parseFloat(amount.toFixed(2)),
      status: 'pending',
      paid_at: null,
      reminder_sent_at: null,
    });
  }

  renderPaymentPlan();
}

/** Add a single empty installment */
function addInstallment() {
  const lastDate = paymentPlan.length > 0
    ? new Date(paymentPlan[paymentPlan.length - 1].due_date)
    : new Date();
  lastDate.setMonth(lastDate.getMonth() + 1);

  paymentPlan.push({
    id: 'inst-' + Date.now(),
    due_date: lastDate.toISOString().split('T')[0],
    amount: 0,
    status: 'pending',
    paid_at: null,
    reminder_sent_at: null,
  });

  renderPaymentPlan();
}

/** Remove an installment */
function removeInstallment(index) {
  paymentPlan.splice(index, 1);
  renderPaymentPlan();
}

/** Update installment field */
function updateInstallment(index, field, value) {
  if (!paymentPlan[index]) return;
  if (field === 'amount') {
    paymentPlan[index][field] = parseFloat(value) || 0;
  } else {
    paymentPlan[index][field] = value;
  }
  renderPaymentPlan();
}

/** Render the payment plan installments list */
function renderPaymentPlan() {
  const $container = document.getElementById('pp-installments');
  if (!$container) return;

  // Update summary counts
  const paid = paymentPlan.filter(i => i.status === 'paid').length;
  const overdue = paymentPlan.filter(i => i.status === 'overdue').length;
  const pending = paymentPlan.filter(i => i.status === 'pending').length;

  const $paidCount = document.getElementById('pp-paid-count');
  const $pendingCount = document.getElementById('pp-pending-count');
  const $overdueCount = document.getElementById('pp-overdue-count');
  if ($paidCount) $paidCount.textContent = paid;
  if ($pendingCount) $pendingCount.textContent = pending;
  if ($overdueCount) $overdueCount.textContent = overdue;

  // Check for overdue (client-side, in case poller hasn't run yet)
  const today = new Date().toISOString().split('T')[0];
  paymentPlan.forEach(inst => {
    if (inst.status === 'pending' && inst.due_date < today) {
      inst.status = 'overdue';
    }
  });

  if (paymentPlan.length === 0) {
    $container.innerHTML = `
      <div class="text-center text-gray-600 text-xs font-mono py-6">
        No installments yet. Click "Auto-Generate" or "+ Add" to create a plan.
      </div>
    `;
    return;
  }

  const planTotal = paymentPlan.reduce((s, i) => s + (parseFloat(i.amount) || 0), 0);
  const invoiceTotal = _getCurrentTotal();
  const diff = invoiceTotal - planTotal;

  $container.innerHTML = paymentPlan.map((inst, i) => {
    const statusStyles = {
      pending: { bg: 'bg-neon-yellow/10', border: 'border-neon-yellow/30', text: 'text-neon-yellow', label: 'PENDING', icon: '⏳' },
      paid:    { bg: 'bg-neon-green/10', border: 'border-neon-green/30', text: 'text-neon-green', label: 'PAID', icon: '✅' },
      overdue: { bg: 'bg-red-500/10', border: 'border-red-500/30', text: 'text-red-400', label: 'OVERDUE', icon: '🚨' },
      skipped: { bg: 'bg-gray-800', border: 'border-gray-700', text: 'text-gray-500', label: 'SKIPPED', icon: '⏭️' },
    };
    const s = statusStyles[inst.status] || statusStyles.pending;
    const isPaid = inst.status === 'paid';
    const reminderInfo = inst.reminder_sent_at
      ? `<span class="text-[0.6rem] text-gray-600" title="Last reminder: ${inst.reminder_sent_at}">🔔 Reminded</span>`
      : '';

    return `
      <div class="flex gap-3 items-center ${s.bg} rounded-lg border ${s.border} p-3 ${isPaid ? 'opacity-70' : ''}">
        <div class="text-lg">${s.icon}</div>
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2 mb-1">
            <span class="text-[0.6rem] font-mono font-bold ${s.text} uppercase">${s.label}</span>
            <span class="text-[0.6rem] font-mono text-gray-600">#${i + 1}</span>
            ${reminderInfo}
          </div>
          <div class="flex items-center gap-3">
            <input type="date" value="${inst.due_date || ''}" ${isPaid ? 'disabled' : ''}
              onchange="updateInstallment(${i}, 'due_date', this.value)"
              class="bg-transparent text-sm text-white font-mono focus:outline-none border-b border-transparent focus:border-electric ${isPaid ? 'opacity-50' : ''}" />
            <span class="text-gray-600 text-xs">$</span>
            <input type="number" step="0.01" value="${parseFloat(inst.amount || 0).toFixed(2)}" ${isPaid ? 'disabled' : ''}
              onchange="updateInstallment(${i}, 'amount', this.value)"
              class="w-24 bg-transparent text-sm text-white font-mono text-right focus:outline-none border-b border-transparent focus:border-electric ${isPaid ? 'opacity-50' : ''}" />
          </div>
          ${isPaid && inst.paid_at ? `<div class="text-[0.55rem] text-gray-600 mt-1">Paid: ${new Date(inst.paid_at).toLocaleDateString()}</div>` : ''}
        </div>
        <div class="flex flex-col gap-1">
          ${!isPaid ? `
            <button onclick="recordInstallmentPayment(${i})" class="text-[0.6rem] font-mono px-2 py-1 rounded bg-neon-green/10 text-neon-green hover:bg-neon-green/20 transition" title="Record payment">💵 Paid</button>
          ` : ''}
          ${!isPaid ? `
            <button onclick="removeInstallment(${i})" class="text-[0.6rem] font-mono px-2 py-1 rounded bg-red-500/10 text-red-400 hover:bg-red-500/20 transition" title="Remove">✕</button>
          ` : ''}
        </div>
      </div>
    `;
  }).join('');

  // Plan total vs invoice total warning
  if (Math.abs(diff) > 0.01) {
    const color = diff > 0 ? 'text-neon-yellow' : 'text-red-400';
    $container.innerHTML += `
      <div class="text-center text-xs font-mono ${color} mt-2">
        Plan total: $${planTotal.toFixed(2)} · Invoice total: $${invoiceTotal.toFixed(2)} · Difference: $${Math.abs(diff).toFixed(2)}
      </div>
    `;
  }
}

/** Get current invoice total from the form */
function _getCurrentTotal() {
  const subtotal = invoiceItems.reduce((sum, item) => sum + (parseFloat(item.amount) || 0), 0);
  const taxRatePercent = parseFloat(document.getElementById('inv-tax-rate').value) || 0;
  return subtotal + subtotal * (taxRatePercent / 100);
}

/** Record payment for a specific installment via the API */
async function recordInstallmentPayment(index) {
  const inst = paymentPlan[index];
  if (!inst) return;

  if (!currentInvoice || !currentInvoice.invoice_number) {
    alert('Please save the invoice first.');
    return;
  }

  const amount = parseFloat(inst.amount) || 0;
  if (!confirm(`Record payment of $${amount.toFixed(2)} for installment #${index + 1}?`)) return;

  try {
    const res = await fetch(`${API_BASE}/invoices/${currentInvoice.invoice_number}/record-payment`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        installment_id: inst.id,
        amount: amount,
        payment_method: document.getElementById('inv-payment-method').value || null,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }

    currentInvoice = await res.json();
    paymentPlan = (currentInvoice.payment_plan || []).map(i => ({ ...i }));
    _populateInvoiceForm();
    alert(`✅ Payment of $${amount.toFixed(2)} recorded!`);
  } catch (err) {
    console.error('[PaymentPlan] Record payment failed:', err);
    alert('Record payment failed: ' + err.message);
  }
}

/** Send a payment reminder for the next unpaid installment */
async function sendPaymentReminder() {
  if (!currentInvoice || !currentInvoice.invoice_number) {
    alert('Please save the invoice first.');
    return;
  }

  const nextPending = paymentPlan.find(i => i.status === 'pending' || i.status === 'overdue');
  if (!nextPending) {
    alert('No pending installments to remind about.');
    return;
  }

  const amt = parseFloat(nextPending.amount || 0).toFixed(2);
  if (!confirm(`Send payment reminder to ${currentInvoice.client_email}?\n\nAmount: $${amt}\nDue: ${nextPending.due_date}`)) return;

  try {
    const res = await fetch(`${API_BASE}/invoices/${currentInvoice.invoice_number}/send-reminder`, {
      method: 'POST',
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }

    const data = await res.json();
    if (data.success) {
      alert(`✅ Payment reminder sent to ${currentInvoice.client_email}!`);
      // Refresh to show updated reminder_sent_at
      await openInvoice(currentInvoice.invoice_number);
    } else {
      alert('⚠️ ' + (data.message || 'Failed to send reminder'));
    }
  } catch (err) {
    console.error('[PaymentPlan] Send reminder failed:', err);
    alert('Send reminder failed: ' + err.message);
  }
}
