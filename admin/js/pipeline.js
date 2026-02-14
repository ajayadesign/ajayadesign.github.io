/* ═══════════════════════════════════════════════════════════════
   AjayaDesign Admin — Pipeline Graph Visualization
   Real-time flowchart of the v2 multi-agent build pipeline
   ═══════════════════════════════════════════════════════════════ */

// ── Pipeline State ─────────────────────────────────────────────
const pipeline = {
  // Each node tracks: status (pending|active|done|failed), detail text, time
  nodes: {
    request:  { status: 'pending', label: '📋 Client Request', detail: '', time: null },
    repo:     { status: 'pending', label: '🏗️ Create Repository', detail: '', time: null },
    council:  { status: 'pending', label: '🏛️ AI Council', detail: '', time: null },
    design:   { status: 'pending', label: '🎨 Design System', detail: '', time: null },
    generate: { status: 'pending', label: '🤖 Page Generation', detail: '', time: null },
    assemble: { status: 'pending', label: '📎 Assembly', detail: '', time: null },
    test:     { status: 'pending', label: '🧪 Quality Gate', detail: '', time: null },
    deploy:   { status: 'pending', label: '🚀 Deploy', detail: '', time: null },
    notify:   { status: 'pending', label: '📬 Notification', detail: '', time: null },
  },

  // Council debate rounds
  councilRounds: [],

  // Page agents: { slug, title, status, detail }
  agents: [],

  // Test state
  tests: { status: 'pending', attempts: [], currentAttempt: 0 },

  // Metadata
  clientName: '',
  niche: '',
  liveUrl: '',
  repoUrl: '',
};

// ── Reset ──────────────────────────────────────────────────────
function resetPipeline() {
  for (const key of Object.keys(pipeline.nodes)) {
    pipeline.nodes[key].status = 'pending';
    pipeline.nodes[key].detail = '';
    pipeline.nodes[key].time = null;
  }
  pipeline.councilRounds = [];
  pipeline.agents = [];
  pipeline.tests = { status: 'pending', attempts: [], currentAttempt: 0 };
  pipeline.clientName = '';
  pipeline.niche = '';
  pipeline.liveUrl = '';
  pipeline.repoUrl = '';
}

// ── Feed SSE Events into Pipeline ──────────────────────────────

function pipelineHandleStep(data) {
  const name = data.name || data.stepName || '';
  const status = data.status || '';

  if (name && pipeline.nodes[name]) {
    if (status === 'start') {
      pipeline.nodes[name].status = 'active';
      pipeline.nodes[name].time = new Date();
    } else if (status === 'done') {
      pipeline.nodes[name].status = 'done';
    }
  }
  renderPipeline();
}

function pipelineHandleAI(data) {
  const msg = data.message || '';
  const action = data.action || '';

  // Council events (from strategist/critic)
  if (msg.includes('strategist') || msg.includes('critic') || msg.includes('Strategist') || msg.includes('Critic')) {
    const isStrategist = /strategist/i.test(msg);
    const isCritic = /critic/i.test(msg);
    const speaker = isStrategist ? 'strategist' : isCritic ? 'critic' : 'unknown';

    // Extract round number
    const roundMatch = msg.match(/Round (\d+)/i);
    const round = roundMatch ? parseInt(roundMatch[1]) : pipeline.councilRounds.length + 1;

    // Extract the useful part of the message
    let text = msg;
    const colonIdx = msg.indexOf('):');
    if (colonIdx > -1) text = msg.substring(colonIdx + 2).trim();

    pipeline.councilRounds.push({
      speaker,
      round,
      text: text.substring(0, 200),
      action,
      time: new Date(),
    });
  }

  // Agent page-building events
  if (msg.includes(':') && !msg.includes('strategist') && !msg.includes('critic') &&
      !msg.includes('Strategist') && !msg.includes('Critic')) {
    const parts = msg.split(':');
    const pageName = parts[0].trim();
    const detail = parts.slice(1).join(':').trim();

    if (pageName && pageName !== '_design') {
      const existing = pipeline.agents.find(a => a.slug === pageName);
      if (existing) {
        existing.detail = detail;
        if (action === 'done') existing.status = 'done';
        else if (action === 'generating') existing.status = 'active';
        else if (action === 'failed' || action === 'fallback') existing.status = 'failed';
      } else {
        pipeline.agents.push({
          slug: pageName,
          title: pageName,
          status: action === 'done' ? 'done' : action === 'generating' ? 'active' : 'pending',
          detail,
        });
      }
    }

    // Design system event
    if (pageName === '_design') {
      if (action === 'generating') pipeline.nodes.design.detail = 'Generating...';
      else if (action === 'done') pipeline.nodes.design.detail = detail;
    }
  }

  renderPipeline();
}

function pipelineHandleTest(data) {
  const action = (data.action || '').toLowerCase();
  const attempt = data.attempt || pipeline.tests.currentAttempt || 1;
  const msg = data.message || '';

  pipeline.tests.currentAttempt = attempt;

  if (action === 'start' || action === 'run') {
    pipeline.tests.status = 'running';
    // Add or update attempt
    const existing = pipeline.tests.attempts.find(a => a.num === attempt);
    if (existing) {
      existing.status = 'running';
      existing.detail = msg;
    } else {
      pipeline.tests.attempts.push({ num: attempt, status: 'running', detail: msg });
    }
  } else if (action === 'pass') {
    pipeline.tests.status = 'pass';
    const existing = pipeline.tests.attempts.find(a => a.num === attempt);
    if (existing) { existing.status = 'pass'; existing.detail = msg; }
    else pipeline.tests.attempts.push({ num: attempt, status: 'pass', detail: msg });
  } else if (action === 'fail') {
    pipeline.tests.status = 'fail';
    const existing = pipeline.tests.attempts.find(a => a.num === attempt);
    if (existing) { existing.status = 'fail'; existing.detail = msg; }
    else pipeline.tests.attempts.push({ num: attempt, status: 'fail', detail: msg });
  } else if (action === 'fix') {
    const existing = pipeline.tests.attempts.find(a => a.num === attempt);
    if (existing) { existing.status = 'fixing'; existing.detail = msg; }
  }

  renderPipeline();
}

function pipelineHandleLog(line) {
  if (!line) return;

  // Extract client info from early log lines
  if (line.includes('Starting build for:')) {
    const m = line.match(/Starting build for:\s*(.+)/);
    if (m) pipeline.clientName = m[1].trim();
    pipeline.nodes.request.status = 'done';
    pipeline.nodes.request.detail = pipeline.clientName;
  }
  if (line.includes('Niche:')) {
    const m = line.match(/Niche:\s*([^|]+)/);
    if (m) pipeline.niche = m[1].trim();
  }
  // Detect page count from council
  if (line.includes('proposed') && line.includes('pages:')) {
    const m = line.match(/proposed (\d+) pages:\s*(.+)/);
    if (m) {
      pipeline.nodes.council.detail = `${m[1]} pages planned`;
      // Pre-populate agents
      const pageNames = m[2].split(',').map(s => s.trim());
      if (pipeline.agents.length === 0) {
        pipeline.agents = pageNames.map(name => ({
          slug: name.toLowerCase().replace(/\s+/g, '-'),
          title: name,
          status: 'pending',
          detail: '',
        }));
      }
    }
  }
  // Detect council approval
  if (line.includes('Council approved')) {
    pipeline.nodes.council.detail = 'Approved ✅';
  }
  if (line.includes('Max council rounds')) {
    pipeline.nodes.council.detail = 'Proceeded with best plan';
  }
  // Detect design system
  if (line.includes('Design system ready')) {
    pipeline.nodes.design.detail = 'Ready ✅';
  }
  // Detect page generation
  if (line.includes('.html generated')) {
    const m = line.match(/(\w+)\.html generated \((\d+)/);
    if (m) {
      const agent = pipeline.agents.find(a => a.slug === m[1]);
      if (agent) { agent.status = 'done'; agent.detail = `${m[2]} bytes`; }
    }
  }
  // Detect test results
  if (line.includes('All tests passed')) {
    pipeline.tests.status = 'pass';
  }
  // Detect deploy
  if (line.includes('BUILD COMPLETE')) {
    pipeline.nodes.deploy.status = 'done';
  }
  // Live URL
  if (line.includes('Live:')) {
    const m = line.match(/Live:\s*(\S+)/);
    if (m) pipeline.liveUrl = m[1];
  }

  renderPipeline();
}

function pipelineHandleDone(data) {
  if (data.status === 'success') {
    // Mark remaining as done
    for (const n of Object.values(pipeline.nodes)) {
      if (n.status === 'active') n.status = 'done';
    }
    pipeline.liveUrl = data.liveUrl || pipeline.liveUrl;
  } else {
    // Mark active as failed
    for (const n of Object.values(pipeline.nodes)) {
      if (n.status === 'active') n.status = 'failed';
    }
  }
  renderPipeline();
}

// ── Render the Full Pipeline Graph ─────────────────────────────

function renderPipeline() {
  const $graph = document.getElementById('pipeline-graph');
  if (!$graph) return;

  const html = [];

  // ── 1. Client Request Node ─────────────────────────
  html.push(renderNode('request', pipeline.nodes.request, {
    extra: pipeline.clientName
      ? `<div class="mt-2 text-xs text-gray-400"><span class="text-electric">${escP(pipeline.clientName)}</span>${pipeline.niche ? ` · ${escP(pipeline.niche)}` : ''}</div>`
      : '',
  }));
  html.push(renderConnector('request', 'repo'));

  // ── 2. Create Repo ────────────────────────────────
  html.push(renderNode('repo', pipeline.nodes.repo));
  html.push(renderConnector('repo', 'council'));

  // ── 3. AI Council ─────────────────────────────────
  html.push(renderNode('council', pipeline.nodes.council, {
    extra: renderCouncilDebate(),
  }));
  html.push(renderConnector('council', 'design'));

  // ── 4. Design System ──────────────────────────────
  html.push(renderNode('design', pipeline.nodes.design));
  html.push(renderConnector('design', 'generate'));

  // ── 5. Page Generation — FORK into agent grid ─────
  html.push(renderNode('generate', pipeline.nodes.generate, {
    extra: renderAgentGrid(),
  }));
  html.push(renderConnector('generate', 'assemble'));

  // ── 6. Assembly ───────────────────────────────────
  html.push(renderNode('assemble', pipeline.nodes.assemble));
  html.push(renderConnector('assemble', 'test'));

  // ── 7. Quality Gate ───────────────────────────────
  html.push(renderNode('test', pipeline.nodes.test, {
    extra: renderTestAttempts(),
  }));
  html.push(renderConnector('test', 'deploy'));

  // ── 8. Deploy ─────────────────────────────────────
  html.push(renderNode('deploy', pipeline.nodes.deploy, {
    extra: pipeline.liveUrl
      ? `<div class="mt-2"><a href="${pipeline.liveUrl}" target="_blank" class="text-xs text-electric hover:underline font-mono">${escP(pipeline.liveUrl)}</a></div>`
      : '',
  }));
  html.push(renderConnector('deploy', 'notify'));

  // ── 9. Notification ───────────────────────────────
  html.push(renderNode('notify', pipeline.nodes.notify));

  $graph.innerHTML = html.join('');

  // Auto-scroll to active node
  const activeNode = $graph.querySelector('.pipe-node.active');
  if (activeNode && document.getElementById('auto-scroll')?.checked) {
    activeNode.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
}

// ── Render Helpers ─────────────────────────────────────────────

function renderNode(key, node, opts = {}) {
  const statusCls = node.status;
  const statusBadge = {
    pending: '',
    active:  '<span class="inline-block w-2 h-2 rounded-full bg-electric live-dot mr-2"></span>',
    done:    '<span class="text-neon-green mr-2">✓</span>',
    failed:  '<span class="text-brand-link mr-2">✗</span>',
  }[node.status] || '';

  const timeStr = node.time ? `<span class="text-[0.6rem] text-gray-600 ml-auto font-mono">${node.time.toLocaleTimeString()}</span>` : '';

  return `
    <div class="pipe-node ${statusCls}" data-node="${key}">
      <div class="flex items-center">
        ${statusBadge}
        <span class="font-mono text-sm font-semibold ${node.status === 'pending' ? 'text-gray-600' : 'text-white'}">${node.label}</span>
        ${timeStr}
      </div>
      ${node.detail ? `<div class="mt-1 text-xs text-gray-400 font-mono">${escP(node.detail)}</div>` : ''}
      ${opts.extra || ''}
    </div>`;
}

function renderConnector(fromKey, toKey) {
  const fromStatus = pipeline.nodes[fromKey]?.status;
  const lit = fromStatus === 'done' ? 'lit' : fromStatus === 'failed' ? 'lit-fail' : '';
  return `<div class="pipe-connector ${lit}" style="height:24px;"></div>`;
}

function renderCouncilDebate() {
  if (pipeline.councilRounds.length === 0) return '';

  const rounds = pipeline.councilRounds.map(r => {
    const cls = r.speaker === 'strategist' ? 'strategist' : 'critic';
    const icon = r.speaker === 'strategist' ? '🧠' : '🔍';
    const label = r.speaker === 'strategist' ? 'Strategist' : 'Critic';
    return `
      <div class="council-bubble ${cls}">
        <div class="flex items-center gap-1.5 mb-0.5">
          <span>${icon}</span>
          <span class="font-mono text-[0.65rem] font-semibold ${r.speaker === 'strategist' ? 'text-electric' : 'text-neon-purple'}">${label}</span>
          <span class="text-[0.6rem] text-gray-600">R${r.round}</span>
        </div>
        <p class="text-xs text-gray-400 leading-relaxed">${escP(r.text)}</p>
      </div>`;
  }).join('');

  return `<div class="mt-3 space-y-2 ml-4 border-l border-border pl-3">${rounds}</div>`;
}

function renderAgentGrid() {
  if (pipeline.agents.length === 0) return '';

  // Fork visualization
  const agentCount = pipeline.agents.length;
  const cards = pipeline.agents.map(a => {
    const icon = a.status === 'done' ? '✅' : a.status === 'active' ? '⚙️' : a.status === 'failed' ? '⚠️' : '📄';
    const statusCls = a.status;
    return `
      <div class="agent-card ${statusCls}">
        <div class="flex items-center gap-1.5">
          <span class="text-sm">${icon}</span>
          <span class="font-mono text-[0.7rem] font-semibold ${a.status === 'pending' ? 'text-gray-600' : 'text-gray-200'}">${escP(a.title)}</span>
        </div>
        ${a.detail ? `<div class="text-[0.65rem] text-gray-500 mt-0.5">${escP(a.detail)}</div>` : ''}
      </div>`;
  }).join('');

  // Show as a branching grid
  return `
    <div class="mt-3">
      <div class="flex items-start justify-center gap-1 mb-1">
        ${pipeline.agents.map(() => '<div class="pipe-branch-drop ' + (pipeline.nodes.generate.status !== 'pending' ? 'lit' : '') + '"></div>').join('')}
      </div>
      <div class="grid gap-2" style="grid-template-columns: repeat(${Math.min(agentCount, 4)}, 1fr);">
        ${cards}
      </div>
      <div class="flex items-start justify-center gap-1 mt-1">
        ${pipeline.agents.map(() => '<div class="pipe-branch-drop ' + (pipeline.agents.every(a => a.status === 'done') ? 'lit' : '') + '"></div>').join('')}
      </div>
    </div>`;
}

function renderTestAttempts() {
  const { attempts } = pipeline.tests;
  if (attempts.length === 0) return '';

  const rows = attempts.map(a => {
    let icon, color, cls;
    switch (a.status) {
      case 'pass':    icon = '✅'; color = 'text-neon-green'; cls = ''; break;
      case 'fail':    icon = '❌'; color = 'text-brand-link'; cls = 'retry-shake'; break;
      case 'fixing':  icon = '🔧'; color = 'text-neon-orange'; cls = ''; break;
      case 'running': icon = '🔄'; color = 'text-electric'; cls = ''; break;
      default:        icon = '⏳'; color = 'text-gray-500'; cls = '';
    }
    return `
      <div class="flex items-center gap-2 py-1 ${cls}">
        <span>${icon}</span>
        <span class="font-mono text-[0.7rem] ${color} font-semibold">Attempt #${a.num}</span>
        <span class="text-[0.65rem] text-gray-500 truncate">${escP(a.detail)}</span>
      </div>`;
  }).join('');

  return `<div class="mt-2 ml-4 border-l border-border pl-3 space-y-0.5">${rows}</div>`;
}

function escP(s) {
  return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// ── Demo / Test Function ───────────────────────────────────────
// Run `demoPipeline()` from console to see the full graph animate

async function demoPipeline() {
  resetPipeline();
  renderPipeline();

  const sleep = ms => new Promise(r => setTimeout(r, ms));

  // 1. Request
  pipeline.clientName = 'Sunrise Bakery';
  pipeline.niche = 'Bakery';
  pipeline.nodes.request.status = 'done';
  pipeline.nodes.request.detail = 'Sunrise Bakery';
  pipeline.nodes.request.time = new Date();
  renderPipeline();
  await sleep(600);

  // 2. Repo
  pipeline.nodes.repo.status = 'active';
  pipeline.nodes.repo.time = new Date();
  renderPipeline();
  await sleep(800);
  pipeline.nodes.repo.status = 'done';
  pipeline.nodes.repo.detail = 'ajayadesign/sunrise-bakery';
  renderPipeline();
  await sleep(400);

  // 3. Council
  pipeline.nodes.council.status = 'active';
  pipeline.nodes.council.time = new Date();
  renderPipeline();
  await sleep(500);

  pipeline.councilRounds.push({ speaker: 'strategist', round: 1, text: 'Proposing 5 pages: Home, Menu, About, Order, Contact. Warm bakery tones with golden accents.', action: 'proposing' });
  renderPipeline();
  await sleep(1000);

  pipeline.councilRounds.push({ speaker: 'critic', round: 1, text: 'Score 7/10. Menu page needs filtering. No testimonials section. Hero CTA is too generic.', action: 'critiqued' });
  renderPipeline();
  await sleep(800);

  pipeline.councilRounds.push({ speaker: 'strategist', round: 2, text: 'Revised: Added testimonials to Home, menu categories with filter tabs, specific CTAs per page.', action: 'revising' });
  renderPipeline();
  await sleep(800);

  pipeline.councilRounds.push({ speaker: 'critic', round: 2, text: 'Score 9/10. Approved ✅ — Strong conversion funnel, good UX flow.', action: 'approved' });
  pipeline.nodes.council.status = 'done';
  pipeline.nodes.council.detail = 'Approved after 2 rounds';
  renderPipeline();
  await sleep(400);

  // 4. Design System
  pipeline.nodes.design.status = 'active';
  pipeline.nodes.design.time = new Date();
  pipeline.nodes.design.detail = 'Generating Tailwind config + nav/footer...';
  renderPipeline();
  await sleep(1200);
  pipeline.nodes.design.status = 'done';
  pipeline.nodes.design.detail = 'Playfair Display + Inter · #D2691E / #FFD700';
  renderPipeline();
  await sleep(400);

  // 5. Page Generation — agents fork
  pipeline.nodes.generate.status = 'active';
  pipeline.nodes.generate.time = new Date();
  pipeline.agents = [
    { slug: 'index', title: 'Home', status: 'pending', detail: '' },
    { slug: 'menu', title: 'Menu', status: 'pending', detail: '' },
    { slug: 'about', title: 'About', status: 'pending', detail: '' },
    { slug: 'order', title: 'Order', status: 'pending', detail: '' },
    { slug: 'contact', title: 'Contact', status: 'pending', detail: '' },
  ];
  renderPipeline();

  for (const agent of pipeline.agents) {
    agent.status = 'active';
    agent.detail = 'Building...';
    renderPipeline();
    await sleep(700);
    agent.status = 'done';
    agent.detail = `${(6000 + Math.random() * 4000).toFixed(0)} bytes`;
    renderPipeline();
    await sleep(300);
  }

  pipeline.nodes.generate.status = 'done';
  pipeline.nodes.generate.detail = '5 pages generated';
  renderPipeline();
  await sleep(400);

  // 6. Assembly
  pipeline.nodes.assemble.status = 'active';
  pipeline.nodes.assemble.time = new Date();
  renderPipeline();
  await sleep(800);
  pipeline.nodes.assemble.status = 'done';
  pipeline.nodes.assemble.detail = 'Nav stitched · sitemap · 404 · robots.txt';
  renderPipeline();
  await sleep(400);

  // 7. Test — fail then pass
  pipeline.nodes.test.status = 'active';
  pipeline.nodes.test.time = new Date();
  pipeline.tests.status = 'running';
  pipeline.tests.attempts.push({ num: 1, status: 'running', detail: 'Running 12 tests...' });
  renderPipeline();
  await sleep(1200);

  pipeline.tests.attempts[0].status = 'fail';
  pipeline.tests.attempts[0].detail = '10/12 passed · 2 failures (menu overflow, contact form)';
  pipeline.tests.status = 'fail';
  renderPipeline();
  await sleep(600);

  pipeline.tests.attempts.push({ num: 2, status: 'fixing', detail: 'AI Fixer patching menu.html + contact.html...' });
  renderPipeline();
  await sleep(1000);

  pipeline.tests.attempts[1].status = 'running';
  pipeline.tests.attempts[1].detail = 'Re-running 12 tests...';
  renderPipeline();
  await sleep(1000);

  pipeline.tests.attempts[1].status = 'pass';
  pipeline.tests.attempts[1].detail = '12/12 passed ✅';
  pipeline.tests.status = 'pass';
  pipeline.nodes.test.status = 'done';
  pipeline.nodes.test.detail = 'All tests passed (attempt 2)';
  renderPipeline();
  await sleep(400);

  // 8. Deploy
  pipeline.nodes.deploy.status = 'active';
  pipeline.nodes.deploy.time = new Date();
  renderPipeline();
  await sleep(1000);
  pipeline.liveUrl = 'https://ajayadesign.github.io/sunrise-bakery';
  pipeline.nodes.deploy.status = 'done';
  pipeline.nodes.deploy.detail = 'GitHub Pages live';
  renderPipeline();
  await sleep(400);

  // 9. Notify
  pipeline.nodes.notify.status = 'active';
  pipeline.nodes.notify.time = new Date();
  renderPipeline();
  await sleep(600);
  pipeline.nodes.notify.status = 'done';
  pipeline.nodes.notify.detail = 'Telegram sent ✅';
  renderPipeline();
}
