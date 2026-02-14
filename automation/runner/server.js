// ═══════════════════════════════════════════════════════════════
//  AjayaDesign Runner — HTTP-to-Shell bridge with live streaming
//  POST /build → spawns build_and_deploy.sh
//  GET  /builds → build history (persistent JSON)
//  GET  /builds/:id → build detail + log
//  GET  /builds/:id/stream → SSE live log stream
//  GET  /health, GET /status/:id → backward-compat
// ═══════════════════════════════════════════════════════════════
const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');
const { randomUUID } = require('crypto');

const PORT = 3456;
const SCRIPT = '/workspace/ajayadesign.github.io/automation/build_and_deploy.sh';
const HISTORY_DIR = '/workspace/.buildhistory';
const HISTORY_FILE = path.join(HISTORY_DIR, 'builds.json');

// ── Persistent storage ─────────────────────────────────────────
function ensureDir(dir) {
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

function loadHistory() {
  ensureDir(HISTORY_DIR);
  try { return JSON.parse(fs.readFileSync(HISTORY_FILE, 'utf-8')); }
  catch { return []; }
}

function saveHistory(list) {
  ensureDir(HISTORY_DIR);
  fs.writeFileSync(HISTORY_FILE, JSON.stringify(list, null, 2));
}

function persistBuild(build) {
  const history = loadHistory();
  const { log, ...meta } = build;                      // logs stored separately
  const idx = history.findIndex(b => b.id === meta.id);
  if (idx >= 0) history[idx] = meta; else history.unshift(meta);
  if (history.length > 200) history.length = 200;       // cap at 200
  saveHistory(history);
  // Save log file
  const logFile = path.join(HISTORY_DIR, `${build.id}.log`);
  fs.writeFileSync(logFile, (log || []).join('\n'));
}

function loadBuildLog(id) {
  try { return fs.readFileSync(path.join(HISTORY_DIR, `${id}.log`), 'utf-8').split('\n').filter(Boolean); }
  catch { return []; }
}

// ── In-memory state ────────────────────────────────────────────
const activeBuilds = new Map();   // buildId → { ...state, log:[] }
const sseClients   = new Map();   // buildId → Set<res>

// ── Structured log parser ──────────────────────────────────────
function parseLogLine(line) {
  const ev = { raw: line, type: 'log', timestamp: new Date().toISOString() };

  const stepM = line.match(/\[STEP:(\d+):(\d+):(\w+)\]\s*(.*)/);
  if (stepM) {
    ev.type = 'step'; ev.current = +stepM[1]; ev.total = +stepM[2];
    ev.stepName = stepM[3]; ev.message = stepM[4]; return ev;
  }
  const aiM = line.match(/\[AI:(\w+)(?::(\d+))?\]\s*(.*)/);
  if (aiM) {
    ev.type = 'ai'; ev.action = aiM[1].toLowerCase();
    if (aiM[2]) ev.attempt = +aiM[2]; ev.message = aiM[3]; return ev;
  }
  const testM = line.match(/\[TEST:(\w+)(?::(\d+))?\]\s*(.*)/);
  if (testM) {
    ev.type = 'test'; ev.action = testM[1].toLowerCase();
    if (testM[2]) ev.attempt = +testM[2]; ev.message = testM[3]; return ev;
  }
  if (/\[DEPLOY\]/.test(line)) {
    ev.type = 'deploy'; ev.message = line.replace(/.*\[DEPLOY\]\s*/, ''); return ev;
  }
  return ev;
}

// ── SSE helpers ────────────────────────────────────────────────
function addSSEClient(buildId, res) {
  if (!sseClients.has(buildId)) sseClients.set(buildId, new Set());
  sseClients.get(buildId).add(res);
  res.on('close', () => {
    const s = sseClients.get(buildId);
    if (s) { s.delete(res); if (s.size === 0) sseClients.delete(buildId); }
  });
}

function broadcastSSE(buildId, eventName, data) {
  const clients = sseClients.get(buildId);
  if (!clients || clients.size === 0) return;
  const msg = `event: ${eventName}\ndata: ${JSON.stringify(data)}\n\n`;
  for (const res of clients) { try { res.write(msg); } catch {} }
}

// ── CORS ───────────────────────────────────────────────────────
function setCORS(res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
}

// ── Telegram notification ──────────────────────────────────────
function sendTelegramNotification({ clientName, niche, goals, email, buildId }) {
  const token = process.env.TELEGRAM_BOT_TOKEN;
  const chatId = process.env.TELEGRAM_CHAT_ID;
  if (!token || !chatId) {
    console.log(`[${buildId}] ⚠️ Telegram env vars missing — skipping`);
    return;
  }
  const text = [
    '📬 *New Client Request*', '',
    `🏢 *Business:* ${escMD(clientName)}`,
    `🏷 *Niche:* ${escMD(niche)}`,
    `🎯 *Goals:* ${escMD(goals)}`,
    `📧 *Email:* ${escMD(email || 'not provided')}`,
    '', `🔨 Build \`${buildId}\` has been queued\\.`,
  ].join('\n');

  const payload = JSON.stringify({ chat_id: chatId, text, parse_mode: 'MarkdownV2' });
  const opts = {
    hostname: 'api.telegram.org',
    path: `/bot${token}/sendMessage`,
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(payload) },
  };
  const req = https.request(opts, (r) => {
    let body = '';
    r.on('data', d => body += d);
    r.on('end', () => {
      if (r.statusCode !== 200) console.error(`[${buildId}] Telegram error: ${body}`);
      else console.log(`[${buildId}] 📬 Telegram notified`);
    });
  });
  req.on('error', e => console.error(`[${buildId}] Telegram failed: ${e.message}`));
  req.write(payload); req.end();
}

function escMD(s) { return String(s).replace(/([_*\[\]()~`>#+\-=|{}.!\\])/g, '\\$1'); }

// ── Route helpers ──────────────────────────────────────────────
function json(res, code, data) {
  setCORS(res);
  res.writeHead(code, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify(data));
}

function extractPath(url) {
  return url.split('?')[0]; // strip query string
}

// ═══════════════════════════════════════════════════════════════
//  HTTP Server
// ═══════════════════════════════════════════════════════════════
const server = http.createServer((req, res) => {
  setCORS(res);
  const p = extractPath(req.url);

  // ── Preflight ──
  if (req.method === 'OPTIONS') { res.writeHead(204); return res.end(); }

  // ── GET /health ──
  if (req.method === 'GET' && p === '/health') {
    return json(res, 200, { status: 'ok', active: activeBuilds.size, uptime: process.uptime() | 0 });
  }

  // ── GET /builds ── full history ──
  if (req.method === 'GET' && p === '/builds') {
    const history = loadHistory();
    // Merge active builds at the top (they might not be persisted yet)
    for (const [, b] of activeBuilds) {
      if (!history.find(h => h.id === b.id)) {
        const { log, ...meta } = b;
        history.unshift(meta);
      }
    }
    return json(res, 200, history);
  }

  // ── GET /builds/:id/stream ── SSE ──
  const streamMatch = p.match(/^\/builds\/([a-f0-9-]+)\/stream$/);
  if (req.method === 'GET' && streamMatch) {
    const id = streamMatch[1];
    setCORS(res);
    res.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'Access-Control-Allow-Origin': '*',
    });
    res.write(':ok\n\n'); // keep-alive

    // Send catch-up: replay all existing log lines
    const active = activeBuilds.get(id);
    const logLines = active ? active.log : loadBuildLog(id);
    for (const line of logLines) {
      const parsed = parseLogLine(line);
      res.write(`event: ${parsed.type}\ndata: ${JSON.stringify(parsed)}\n\n`);
    }
    res.write(`event: catch-up-done\ndata: {}\n\n`);

    // If build is already done, send done event and close
    if (!active) {
      const history = loadHistory();
      const build = history.find(b => b.id === id);
      if (build && build.status !== 'running') {
        res.write(`event: done\ndata: ${JSON.stringify({ status: build.status })}\n\n`);
      }
      // Keep connection open briefly then close for completed builds
      setTimeout(() => { try { res.end(); } catch {} }, 1000);
      return;
    }

    // Register for live updates
    addSSEClient(id, res);
    return;
  }

  // ── GET /builds/:id ── single build detail ──
  const buildMatch = p.match(/^\/builds\/([a-f0-9-]+)$/);
  if (req.method === 'GET' && buildMatch) {
    const id = buildMatch[1];
    const active = activeBuilds.get(id);
    if (active) return json(res, 200, active);
    // Check history
    const history = loadHistory();
    const build = history.find(b => b.id === id);
    if (build) {
      build.log = loadBuildLog(id);
      return json(res, 200, build);
    }
    return json(res, 404, { error: 'Build not found' });
  }

  // ── GET /status/:id ── backward compat ──
  if (req.method === 'GET' && p.startsWith('/status/')) {
    const id = p.split('/status/')[1];
    const active = activeBuilds.get(id);
    if (active) return json(res, 200, active);
    const history = loadHistory();
    const build = history.find(b => b.id === id);
    if (build) { build.log = loadBuildLog(id); return json(res, 200, build); }
    return json(res, 404, { error: 'Build not found' });
  }

  // ── POST /build ── trigger a new build ──
  if (req.method === 'POST' && p === '/build') {
    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', () => {
      let data;
      try { data = JSON.parse(body); } catch {
        return json(res, 400, { error: 'Invalid JSON' });
      }

      const clientName = data.business_name || data.businessName || data.clientName;
      const niche  = data.niche || data.businessType || data.business_type || 'General';
      const goals  = data.goals || data.details || data.description || 'Professional website';
      const email  = data.email || '';

      if (!clientName) return json(res, 400, { error: 'business_name is required' });

      const buildId = randomUUID().slice(0, 8);
      const repoName = clientName.toLowerCase().replace(/[^a-z0-9-]/g, '-').replace(/-+/g, '-').replace(/^-|-$/g, '');
      const buildState = {
        id: buildId,
        client: clientName,
        niche,
        goals,
        email,
        repoName,
        liveUrl: `https://ajayadesign.github.io/${repoName}`,
        status: 'running',
        started: new Date().toISOString(),
        log: [],
      };
      activeBuilds.set(buildId, buildState);
      persistBuild(buildState);

      console.log(`[${buildId}] 🚀 Starting build for: ${clientName}`);
      sendTelegramNotification({ clientName, niche, goals, email, buildId });

      // ── Spawn the build script ──
      const child = spawn('bash', [SCRIPT, clientName, niche, goals, email], {
        cwd: '/workspace',
        env: { ...process.env, HOME: '/root', PATH: process.env.PATH },
        stdio: ['ignore', 'pipe', 'pipe'],
      });

      // Process stdout line-by-line
      let stdoutBuf = '';
      child.stdout.on('data', (chunk) => {
        stdoutBuf += chunk.toString();
        const lines = stdoutBuf.split('\n');
        stdoutBuf = lines.pop(); // keep incomplete line in buffer
        for (const raw of lines) {
          const line = raw.trim();
          if (!line) continue;
          console.log(`[${buildId}] ${line}`);
          buildState.log.push(line);
          // Parse and broadcast
          const parsed = parseLogLine(line);
          broadcastSSE(buildId, parsed.type, parsed);
        }
      });

      child.stderr.on('data', (chunk) => {
        const lines = chunk.toString().trim().split('\n');
        for (const raw of lines) {
          const line = `STDERR: ${raw.trim()}`;
          if (!raw.trim()) continue;
          console.error(`[${buildId}] ⚠️ ${raw.trim()}`);
          buildState.log.push(line);
          broadcastSSE(buildId, 'log', { raw: line, type: 'log', timestamp: new Date().toISOString() });
        }
      });

      child.on('close', (code) => {
        // Flush remaining stdout
        if (stdoutBuf.trim()) {
          const line = stdoutBuf.trim();
          buildState.log.push(line);
          const parsed = parseLogLine(line);
          broadcastSSE(buildId, parsed.type, parsed);
        }

        buildState.status = code === 0 ? 'success' : 'failed';
        buildState.exitCode = code;
        buildState.finished = new Date().toISOString();
        console.log(`[${buildId}] ${code === 0 ? '✅' : '❌'} Build finished (exit ${code})`);

        // Persist final state
        persistBuild(buildState);

        // Notify all SSE clients
        broadcastSSE(buildId, 'done', { status: buildState.status, exitCode: code });

        // Move from active to history
        activeBuilds.delete(buildId);
      });

      return json(res, 202, {
        message: `Build started for ${clientName}`,
        buildId,
        statusUrl: `/status/${buildId}`,
        streamUrl: `/builds/${buildId}/stream`,
        dashboardUrl: `/builds/${buildId}`,
      });
    });
    return;
  }

  // ── 404 ──
  json(res, 404, {
    error: 'Not found',
    endpoints: {
      'POST /build': 'Trigger a build',
      'GET /builds': 'Build history',
      'GET /builds/:id': 'Build detail',
      'GET /builds/:id/stream': 'SSE live stream',
      'GET /health': 'Health check',
    },
  });
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`🔧 AjayaDesign Runner v2 — listening on port ${PORT}`);
  console.log(`   POST /build             — trigger a build`);
  console.log(`   GET  /builds            — build history`);
  console.log(`   GET  /builds/:id        — build detail`);
  console.log(`   GET  /builds/:id/stream — SSE live stream`);
  console.log(`   GET  /health            — health check`);
  console.log(`   History: ${HISTORY_FILE}`);
});
