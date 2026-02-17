/* ═══════════════════════════════════════════════════════
   AjayaDesign Admin — Portfolio Tab Logic
   Shows finished sites, inline editing, seed existing sites
   ═══════════════════════════════════════════════════════ */

// ── State ──────────────────────────────────────────────
let portfolioSites = [];
let selectedPortfolioId = null;
let portfolioSubTab = 'sites';

// ── 4 existing sites to seed ───────────────────────────
const SEED_SITES = [
  {
    client_name: "Ajaya Dahal",
    niche: "Personal Portfolio",
    goals: "Showcase engineering portfolio, education, skills, and achievements",
    email: "",
    live_url: "https://ajayadesign.github.io/ajayadahal/",
    directory_name: "ajayadahal",
    tagline: "Hardware Engineering Portfolio",
    status: "complete",
  },
  {
    client_name: "Chhaya Photography",
    niche: "Wedding Photography",
    goals: "Display photography portfolio, galleries, and booking information",
    email: "",
    live_url: "https://ajayadesign.github.io/chhayaphotography/",
    directory_name: "chhayaphotography",
    tagline: "Capturing Life's Beautiful Moments",
    status: "complete",
  },
  {
    client_name: "Magnet Moments Co",
    niche: "Photo Magnets / E-commerce",
    goals: "Sell custom photo magnets, events, wholesale, and retail",
    email: "",
    live_url: "https://ajayadesign.github.io/magnetmomentsco/",
    directory_name: "magnetmomentsco",
    tagline: "Turn Your Favorite Photos Into Magnets",
    status: "complete",
  },
  {
    client_name: "Sanz The Nanny",
    niche: "Nanny / Childcare Services",
    goals: "Professional nanny service website with booking and testimonials",
    email: "",
    live_url: "https://ajayadesign.github.io/sanz-the-nanny/",
    directory_name: "sanz-the-nanny",
    tagline: "Caring for Your Little Ones",
    status: "complete",
  },
];

// ── Load portfolio from API ────────────────────────────
async function loadPortfolio() {
  try {
    const res = await fetch(`${API_BASE}/portfolio`, { signal: AbortSignal.timeout(5000) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    portfolioSites = data.sites || [];
  } catch (err) {
    console.warn('[Portfolio] Failed to load:', err.message);
    portfolioSites = [];
  }
  renderPortfolioSites();
}

// ── Seed existing sites ────────────────────────────────
async function seedPortfolioSites() {
  if (!confirm('Seed the 4 existing portfolio sites into the database?')) return;

  try {
    const res = await fetch(`${API_BASE}/portfolio/seed`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sites: SEED_SITES }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    alert(`✅ Seeded: ${data.total_created} created, ${data.total_skipped} already existed`);
    loadPortfolio();
  } catch (err) {
    console.error('[Portfolio] Seed failed:', err);
    alert('Failed to seed: ' + err.message);
  }
}

// ── Render portfolio sites list ────────────────────────
function renderPortfolioSites() {
  const $list = document.getElementById('portfolio-sites-list');
  if (!$list) return;

  if (portfolioSites.length === 0) {
    $list.innerHTML = `
      <div class="text-center py-12">
        <div class="text-4xl mb-3 opacity-30">📁</div>
        <p class="text-gray-500 font-mono text-sm">No portfolio sites</p>
        <p class="text-gray-600 text-xs mt-1">Click "🌱 Seed" to import existing sites</p>
      </div>`;
    return;
  }

  $list.innerHTML = portfolioSites.map(site => {
    const isSelected = site.short_id === selectedPortfolioId;
    return `
      <div onclick="selectPortfolioSite('${site.short_id}')"
        class="p-4 bg-surface-2 rounded-xl border cursor-pointer transition animate-fade-in
          ${isSelected ? 'border-electric bg-electric/5' : 'border-border hover:border-border-glow'}">
        <div class="flex items-center justify-between mb-2">
          <h3 class="font-mono text-sm font-bold text-white">${esc(site.client_name)}</h3>
          <span class="px-2 py-0.5 rounded-full text-[0.6rem] font-mono bg-neon-green/20 text-neon-green">LIVE</span>
        </div>
        <div class="grid grid-cols-2 gap-2 text-xs mb-2">
          <div><span class="text-gray-600">Niche:</span> <span class="text-gray-400">${esc(site.niche || '-')}</span></div>
          <div class="overflow-hidden"><span class="text-gray-600">Email:</span> <span class="text-gray-400 truncate inline-block max-w-[90px] align-bottom" title="${esc(site.email || '')}">${esc(site.email || '-')}</span></div>
        </div>
        ${site.live_url ? `<a href="${site.live_url}" target="_blank" class="text-[0.65rem] text-electric font-mono hover:underline" onclick="event.stopPropagation()">🔗 ${site.live_url}</a>` : ''}
      </div>`;
  }).join('');
}

// ── Select a portfolio site ────────────────────────────
function selectPortfolioSite(shortId) {
  selectedPortfolioId = shortId;
  renderPortfolioSites();

  const site = portfolioSites.find(s => s.short_id === shortId);
  if (!site) return;

  // Hide other panels, show portfolio detail
  hideAllMainPanels();
  document.getElementById('portfolio-detail').classList.remove('hidden');

  // Populate fields
  document.getElementById('pf-client-name').textContent = site.client_name || 'Unknown';
  document.getElementById('pf-edit-name').value = site.client_name || '';
  document.getElementById('pf-edit-email').value = site.email || '';
  document.getElementById('pf-edit-phone').value = site.phone || '';
  document.getElementById('pf-edit-niche').value = site.niche || '';
  document.getElementById('pf-edit-location').value = site.location || '';
  document.getElementById('pf-edit-url').value = site.live_url || '';
  document.getElementById('pf-edit-colors').value = site.brand_colors || '';
  document.getElementById('pf-edit-tagline').value = site.tagline || '';
  document.getElementById('pf-edit-goals').value = site.goals || '';

  // Meta line
  const metas = [];
  if (site.niche) metas.push(`<span>🏷 ${esc(site.niche)}</span>`);
  if (site.email) metas.push(`<span>📧 ${esc(site.email)}</span>`);
  if (site.live_url) metas.push(`<a href="${site.live_url}" target="_blank" class="text-electric hover:underline">🔗 ${site.live_url}</a>`);
  document.getElementById('pf-meta').innerHTML = metas.join('');

  // Load related contracts and invoices
  loadSiteContracts(shortId);
  loadSiteInvoices(shortId);
}

// ── Save portfolio edit ────────────────────────────────
async function savePortfolioEdit() {
  if (!selectedPortfolioId) return;

  const patch = {
    client_name: document.getElementById('pf-edit-name').value.trim(),
    email: document.getElementById('pf-edit-email').value.trim(),
    phone: document.getElementById('pf-edit-phone').value.trim(),
    niche: document.getElementById('pf-edit-niche').value.trim(),
    location: document.getElementById('pf-edit-location').value.trim(),
    live_url: document.getElementById('pf-edit-url').value.trim(),
    brand_colors: document.getElementById('pf-edit-colors').value.trim(),
    tagline: document.getElementById('pf-edit-tagline').value.trim(),
    goals: document.getElementById('pf-edit-goals').value.trim(),
  };

  try {
    const res = await fetch(`${API_BASE}/builds/${selectedPortfolioId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patch),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    // Update local state
    const idx = portfolioSites.findIndex(s => s.short_id === selectedPortfolioId);
    if (idx !== -1) Object.assign(portfolioSites[idx], patch);

    document.getElementById('pf-client-name').textContent = patch.client_name;
    renderPortfolioSites();
    alert('✅ Saved!');
  } catch (err) {
    console.error('[Portfolio] Save failed:', err);
    alert('Save failed: ' + err.message);
  }
}

// ── Load contracts/invoices for a site ─────────────────
async function loadSiteContracts(shortId) {
  const $list = document.getElementById('pf-contracts-list');
  try {
    const res = await fetch(`${API_BASE}/contracts`, { signal: AbortSignal.timeout(5000) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const site = portfolioSites.find(s => s.short_id === shortId);
    const siteContracts = (data.contracts || []).filter(c =>
      c.client_name === site?.client_name || c.build_id === site?.id
    );

    if (siteContracts.length === 0) {
      $list.innerHTML = '<p class="text-xs text-gray-600 font-mono">No contracts yet</p>';
      return;
    }

    $list.innerHTML = siteContracts.map(c => `
      <div onclick="openContract('${c.short_id}')"
        class="p-3 bg-surface rounded-lg border border-border hover:border-border-glow cursor-pointer transition flex items-center justify-between">
        <div>
          <span class="font-mono text-xs text-white font-semibold">${esc(c.project_name)}</span>
          <span class="text-[0.6rem] text-gray-500 ml-2">#${c.short_id}</span>
        </div>
        <div class="flex items-center gap-2">
          <span class="text-xs font-mono text-neon-green">$${parseFloat(c.total_amount || 0).toFixed(2)}</span>
          <span class="px-2 py-0.5 rounded-full text-[0.6rem] font-mono ${contractStatusClass(c.status)}">${(c.status || 'draft').toUpperCase()}</span>
        </div>
      </div>
    `).join('');
  } catch (err) {
    $list.innerHTML = '<p class="text-xs text-gray-600 font-mono">Failed to load contracts</p>';
  }
}

async function loadSiteInvoices(shortId) {
  const $list = document.getElementById('pf-invoices-list');
  try {
    const res = await fetch(`${API_BASE}/invoices`, { signal: AbortSignal.timeout(5000) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const site = portfolioSites.find(s => s.short_id === shortId);
    const siteInvoices = (data.invoices || []).filter(inv =>
      inv.client_name === site?.client_name || inv.build_id === site?.id
    );

    if (siteInvoices.length === 0) {
      $list.innerHTML = '<p class="text-xs text-gray-600 font-mono">No invoices yet</p>';
      return;
    }

    $list.innerHTML = siteInvoices.map(inv => `
      <div onclick="openInvoice('${inv.invoice_number}')"
        class="p-3 bg-surface rounded-lg border border-border hover:border-border-glow cursor-pointer transition flex items-center justify-between">
        <div>
          <span class="font-mono text-xs text-white font-semibold">${inv.invoice_number}</span>
          <span class="text-[0.6rem] text-gray-500 ml-2">${esc(inv.client_name)}</span>
        </div>
        <div class="flex items-center gap-2">
          <span class="text-xs font-mono text-neon-green">$${parseFloat(inv.total_amount || 0).toFixed(2)}</span>
          <span class="px-2 py-0.5 rounded-full text-[0.6rem] font-mono ${invoiceStatusClass(inv.payment_status)}">${(inv.payment_status || 'unpaid').toUpperCase()}</span>
        </div>
      </div>
    `).join('');
  } catch (err) {
    $list.innerHTML = '<p class="text-xs text-gray-600 font-mono">Failed to load invoices</p>';
  }
}

// ── Sub-tab switching ──────────────────────────────────
function switchPortfolioSubTab(tab) {
  portfolioSubTab = tab;
  const tabs = ['sites', 'contracts', 'invoices'];
  tabs.forEach(t => {
    const $tab = document.getElementById('portfolio-subtab-' + t);
    const $panel = document.getElementById('portfolio-' + t + '-list');
    if (!$tab || !$panel) return;
    if (t === tab) {
      $tab.className = 'flex-1 py-2 text-[0.65rem] font-mono font-semibold uppercase tracking-widest text-center border-b-2 border-electric text-electric transition';
      $panel.classList.remove('hidden');
    } else {
      $tab.className = 'flex-1 py-2 text-[0.65rem] font-mono font-semibold uppercase tracking-widest text-center border-b-2 border-transparent text-gray-500 hover:text-gray-300 transition';
      $panel.classList.add('hidden');
    }
  });

  if (tab === 'contracts') loadAllContracts();
  if (tab === 'invoices') loadAllInvoices();
}

// ── Load all contracts / invoices for sidebar ──────────
async function loadAllContracts() {
  const $list = document.getElementById('portfolio-contracts-list');
  try {
    const res = await fetch(`${API_BASE}/contracts`, { signal: AbortSignal.timeout(5000) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const contracts = data.contracts || [];

    if (contracts.length === 0) {
      $list.innerHTML = `<div class="text-center py-12"><div class="text-4xl mb-3 opacity-30">📝</div><p class="text-gray-500 font-mono text-sm">No contracts yet</p></div>`;
      return;
    }

    $list.innerHTML = contracts.map(c => `
      <div onclick="openContract('${c.short_id}')"
        class="p-4 bg-surface-2 rounded-xl border border-border hover:border-border-glow cursor-pointer transition">
        <div class="flex items-center justify-between mb-2">
          <h3 class="font-mono text-sm font-bold text-white">${esc(c.client_name)}</h3>
          <span class="px-2 py-0.5 rounded-full text-[0.6rem] font-mono ${contractStatusClass(c.status)}">${(c.status || 'draft').toUpperCase()}</span>
        </div>
        <div class="text-xs text-gray-400 mb-1">${esc(c.project_name)}</div>
        <div class="flex items-center justify-between text-[0.65rem]">
          <span class="text-gray-600">#${c.short_id}</span>
          <span class="text-neon-green font-mono">$${parseFloat(c.total_amount || 0).toFixed(2)}</span>
        </div>
      </div>
    `).join('');
  } catch (err) {
    $list.innerHTML = '<p class="text-xs text-gray-600 font-mono p-4">Failed to load contracts</p>';
  }
}

async function loadAllInvoices() {
  const $list = document.getElementById('portfolio-invoices-list');
  try {
    const res = await fetch(`${API_BASE}/invoices`, { signal: AbortSignal.timeout(5000) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const invoices = data.invoices || [];

    if (invoices.length === 0) {
      $list.innerHTML = `<div class="text-center py-12"><div class="text-4xl mb-3 opacity-30">💰</div><p class="text-gray-500 font-mono text-sm">No invoices yet</p></div>`;
      return;
    }

    $list.innerHTML = invoices.map(inv => `
      <div onclick="openInvoice('${inv.invoice_number}')"
        class="p-4 bg-surface-2 rounded-xl border border-border hover:border-border-glow cursor-pointer transition">
        <div class="flex items-center justify-between mb-2">
          <h3 class="font-mono text-sm font-bold text-white">${inv.invoice_number}</h3>
          <span class="px-2 py-0.5 rounded-full text-[0.6rem] font-mono ${invoiceStatusClass(inv.payment_status)}">${(inv.payment_status || 'unpaid').toUpperCase()}</span>
        </div>
        <div class="text-xs text-gray-400 mb-1">${esc(inv.client_name)}</div>
        <div class="flex items-center justify-between text-[0.65rem]">
          <span class="text-gray-600">${inv.due_date || 'No due date'}</span>
          <span class="text-neon-green font-mono">$${parseFloat(inv.total_amount || 0).toFixed(2)}</span>
        </div>
      </div>
    `).join('');
  } catch (err) {
    $list.innerHTML = '<p class="text-xs text-gray-600 font-mono p-4">Failed to load invoices</p>';
  }
}

// ── Create contract/invoice from portfolio site ────────
function createContractForSite() {
  const site = portfolioSites.find(s => s.short_id === selectedPortfolioId);
  if (!site) return;
  openNewContract({
    build_id: site.id,
    client_name: site.client_name,
    client_email: site.email || '',
    project_name: `Website for ${site.client_name}`,
    project_description: site.goals || '',
  });
}

function createInvoiceForSite() {
  const site = portfolioSites.find(s => s.short_id === selectedPortfolioId);
  if (!site) return;
  openNewInvoice({
    build_id: site.id,
    client_name: site.client_name,
    client_email: site.email || '',
  });
}

// ── Helpers ────────────────────────────────────────────
function contractStatusClass(status) {
  const map = {
    draft:    'bg-gray-800 text-gray-400',
    sent:     'bg-electric/20 text-electric',
    viewed:   'bg-neon-yellow/20 text-neon-yellow',
    signed:   'bg-neon-green/20 text-neon-green',
    completed:'bg-neon-green/20 text-neon-green',
    cancelled:'bg-brand-link/20 text-brand-link',
  };
  return map[status] || map.draft;
}

function invoiceStatusClass(status) {
  const map = {
    unpaid:  'bg-neon-yellow/20 text-neon-yellow',
    partial: 'bg-neon-orange/20 text-neon-orange',
    paid:    'bg-neon-green/20 text-neon-green',
    overdue: 'bg-brand-link/20 text-brand-link',
  };
  return map[status] || map.unpaid;
}

function hideAllMainPanels() {
  const panels = ['empty-state', 'build-detail', 'lead-detail', 'portfolio-detail', 'contract-detail', 'invoice-detail'];
  panels.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.classList.add('hidden');
  });
}
