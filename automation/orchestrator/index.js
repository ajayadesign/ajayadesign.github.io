// ═══════════════════════════════════════════════════════════════
//  AjayaDesign v2 — Build Orchestrator
//  Multi-agent site factory with AI Council + Design System
//
//  Usage (CLI):
//    node index.js "Business Name" "Niche" "Goals" "email"
//
//  Usage (programmatic):
//    const BuildOrchestrator = require('./orchestrator');
//    const orch = new BuildOrchestrator(config);
//    orch.on('log', data => console.log(data.raw));
//    await orch.run({ businessName, niche, goals, email });
// ═══════════════════════════════════════════════════════════════
const { EventEmitter } = require('events');
const { ensureGitIdentity } = require('./lib/shell');

// Phase imports
const createRepo = require('./phases/01-repo');
const aiCouncil = require('./phases/02-council');
const generateDesignSystem = require('./phases/03-design');
const generatePages = require('./phases/04-generate');
const assemble = require('./phases/05-assemble');
const qualityGate = require('./phases/06-test');
const deploy = require('./phases/07-deploy');
const notify = require('./phases/08-notify');

class BuildOrchestrator extends EventEmitter {
  constructor(config = {}) {
    super();
    this.config = {
      githubOrg: config.githubOrg || 'ajayadesign',
      baseDir: config.baseDir || '/workspace/builds',
      mainSiteDir:
        config.mainSiteDir || '/workspace/ajayadesign.github.io',
      maxCouncilRounds: config.maxCouncilRounds || 2,
      maxFixAttempts: config.maxFixAttempts || 3,
      ...config,
    };
    this.state = {
      phase: 'init',
      blueprint: null,
      designSystem: null,
      pages: [],
      repo: null,
      testResults: null,
    };
  }

  /** Emit a structured log line (also emits to 'log'). */
  log(msg) {
    const entry = { raw: `[${ts()}] ${msg}`, timestamp: new Date().toISOString() };
    this.emit('log', entry);
  }

  /** Run the full 8-phase build pipeline. */
  async run(clientRequest) {
    const { businessName, niche, goals, email } = clientRequest;
    this.log(`🚀 AjayaDesign v2 — Starting build for: ${businessName}`);
    this.log(`   Niche: ${niche} | Goals: ${goals}`);

    ensureGitIdentity();

    try {
      // ── Phase 1: Create GitHub Repo ──────────────────────
      this.emit('phase', { step: 1, total: 8, name: 'repo', status: 'start' });
      this.state.repo = await createRepo(
        { businessName, niche, goals, email },
        this
      );
      this.emit('phase', { step: 1, total: 8, name: 'repo', status: 'done' });

      // ── Phase 2: AI Council (Strategist ↔ Critic) ────────
      this.emit('phase', { step: 2, total: 8, name: 'council', status: 'start' });
      const { blueprint, transcript } = await aiCouncil(clientRequest, this);
      this.state.blueprint = blueprint;
      this.state.transcript = transcript;
      this.emit('phase', { step: 2, total: 8, name: 'council', status: 'done' });

      // ── Phase 3: Design System Generation ────────────────
      this.emit('phase', { step: 3, total: 8, name: 'design', status: 'start' });
      this.state.designSystem = await generateDesignSystem(blueprint, this);
      this.emit('phase', { step: 3, total: 8, name: 'design', status: 'done' });

      // ── Phase 4: Page Generation (sequential for now) ────
      this.emit('phase', { step: 4, total: 8, name: 'generate', status: 'start' });
      this.state.pages = await generatePages(
        blueprint,
        this.state.designSystem,
        this.state.repo.dir,
        this
      );
      this.emit('phase', { step: 4, total: 8, name: 'generate', status: 'done' });

      // ── Phase 5: Assembly + Cross-Linking ────────────────
      this.emit('phase', { step: 5, total: 8, name: 'assemble', status: 'start' });
      await assemble(
        blueprint,
        this.state.designSystem,
        this.state.repo.dir,
        this
      );
      this.emit('phase', { step: 5, total: 8, name: 'assemble', status: 'done' });

      // ── Phase 6: Quality Gate (Test + Fix) ───────────────
      this.emit('phase', { step: 6, total: 8, name: 'test', status: 'start' });
      this.state.testResults = await qualityGate(
        blueprint,
        this.state.designSystem,
        this.state.repo.dir,
        this
      );
      this.emit('phase', { step: 6, total: 8, name: 'test', status: 'done' });

      // ── Phase 7: Deploy ──────────────────────────────────
      this.emit('phase', { step: 7, total: 8, name: 'deploy', status: 'start' });
      await deploy(this.state.repo, this);
      this.emit('phase', { step: 7, total: 8, name: 'deploy', status: 'done' });

      // ── Phase 8: Notify ──────────────────────────────────
      this.emit('phase', { step: 8, total: 8, name: 'notify', status: 'start' });
      await notify(clientRequest, this.state.repo, this);
      this.emit('phase', { step: 8, total: 8, name: 'notify', status: 'done' });

      // ── Complete ─────────────────────────────────────────
      this.log('═══════════════════════════════════════════════════════');
      this.log(`✅  BUILD COMPLETE: ${businessName}`);
      this.log(`   Live: ${this.state.repo.liveUrl}`);
      this.log(`   Repo: https://github.com/${this.state.repo.repoFull}`);
      this.log(`   Pages: ${this.state.pages.length}`);
      this.log('═══════════════════════════════════════════════════════');

      this.emit('done', {
        status: 'success',
        liveUrl: this.state.repo.liveUrl,
        repoUrl: `https://github.com/${this.state.repo.repoFull}`,
        pages: this.state.pages.length,
      });

      return this.state;
    } catch (err) {
      this.log(`❌ BUILD FAILED: ${err.message}`);
      this.emit('error', { message: err.message, stack: err.stack });
      this.emit('done', { status: 'failed', error: err.message });
      throw err;
    }
  }
}

function ts() {
  return new Date().toISOString().slice(11, 19);
}

// ── CLI support ────────────────────────────────────────────────
if (require.main === module) {
  const [, , businessName, niche, goals, email] = process.argv;
  if (!businessName || !niche || !goals) {
    console.error('Usage: node index.js "Business" "Niche" "Goals" [email]');
    process.exit(1);
  }

  const orch = new BuildOrchestrator();

  // Print all events to console
  orch.on('log', (d) => console.log(d.raw));
  orch.on('phase', (d) =>
    console.log(`[STEP:${d.step}:${d.total}:${d.name}] ${d.status}`)
  );
  orch.on('council', (d) =>
    console.log(`[COUNCIL:${d.speaker}:${d.round}] ${d.action}`)
  );
  orch.on('agent', (d) =>
    console.log(`[AGENT:${d.page}] ${d.action} ${d.detail || ''}`)
  );
  orch.on('error', (d) => console.error(`[ERROR] ${d.message}`));

  orch
    .run({ businessName, niche, goals, email: email || '' })
    .then(() => process.exit(0))
    .catch(() => process.exit(1));
}

module.exports = BuildOrchestrator;
