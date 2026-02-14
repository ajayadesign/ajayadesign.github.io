// ═══════════════════════════════════════════════════════════════
//  AjayaDesign Runner — HTTP-to-Shell bridge for n8n
//  Receives POST from n8n webhook → spawns build_and_deploy.sh
//  No dependencies — pure Node.js http module
// ═══════════════════════════════════════════════════════════════
const http = require('http');
const { spawn } = require('child_process');
const { randomUUID } = require('crypto');

const PORT = 3456;
const SCRIPT = '/workspace/automation/build_and_deploy.sh';

// Track running builds
const builds = new Map();

const server = http.createServer((req, res) => {
  // Health check
  if (req.method === 'GET' && req.url === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    return res.end(JSON.stringify({ status: 'ok', active_builds: builds.size }));
  }

  // Build status
  if (req.method === 'GET' && req.url.startsWith('/status/')) {
    const id = req.url.split('/status/')[1];
    const build = builds.get(id);
    if (!build) {
      res.writeHead(404, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify({ error: 'Build not found' }));
    }
    res.writeHead(200, { 'Content-Type': 'application/json' });
    return res.end(JSON.stringify(build));
  }

  // Trigger build
  if (req.method === 'POST' && req.url === '/build') {
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', () => {
      let data;
      try {
        data = JSON.parse(body);
      } catch {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        return res.end(JSON.stringify({ error: 'Invalid JSON' }));
      }

      const clientName = data.businessName || data.clientName || data.business_name;
      const niche = data.niche || 'General';
      const goals = data.goals || '';
      const email = data.email || '';

      if (!clientName) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        return res.end(JSON.stringify({ error: 'businessName is required' }));
      }

      const buildId = randomUUID().slice(0, 8);
      const buildState = {
        id: buildId,
        client: clientName,
        status: 'running',
        started: new Date().toISOString(),
        log: [],
      };
      builds.set(buildId, buildState);

      console.log(`[${buildId}] 🚀 Starting build for: ${clientName}`);

      const child = spawn('bash', [SCRIPT, clientName, niche, goals, email], {
        cwd: '/workspace',
        env: {
          ...process.env,
          HOME: '/root',
          PATH: process.env.PATH,
        },
        stdio: ['ignore', 'pipe', 'pipe'],
      });

      child.stdout.on('data', (chunk) => {
        const line = chunk.toString().trim();
        console.log(`[${buildId}] ${line}`);
        buildState.log.push(line);
      });

      child.stderr.on('data', (chunk) => {
        const line = chunk.toString().trim();
        console.error(`[${buildId}] ⚠️ ${line}`);
        buildState.log.push(`STDERR: ${line}`);
      });

      child.on('close', (code) => {
        buildState.status = code === 0 ? 'success' : 'failed';
        buildState.exitCode = code;
        buildState.finished = new Date().toISOString();
        console.log(`[${buildId}] ${code === 0 ? '✅' : '❌'} Build finished (exit ${code})`);

        // Clean up old builds after 1 hour
        setTimeout(() => builds.delete(buildId), 3600000);
      });

      // Respond immediately with build ID (async build)
      res.writeHead(202, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({
        message: `Build started for ${clientName}`,
        buildId,
        statusUrl: `/status/${buildId}`,
      }));
    });
    return;
  }

  // 404
  res.writeHead(404, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ error: 'Not found. POST /build to trigger a build.' }));
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`🔧 AjayaDesign Runner listening on port ${PORT}`);
  console.log(`   POST /build     — trigger a build`);
  console.log(`   GET  /status/id — check build status`);
  console.log(`   GET  /health    — health check`);
});
