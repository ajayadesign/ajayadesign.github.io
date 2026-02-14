// ═══════════════════════════════════════════════════════════════
//  Phase 2: AI Council — Strategist ↔ Critic Debate
//  Two AIs debate the site plan before any code is written
// ═══════════════════════════════════════════════════════════════
const { callAI, extractJSON } = require('../lib/ai');
const {
  STRATEGIST_SYSTEM,
  strategistPropose,
  strategistRevise,
  CRITIC_SYSTEM,
  criticReview,
} = require('../lib/prompts');

module.exports = async function aiCouncil(clientRequest, orch) {
  const maxRounds = orch.config.maxCouncilRounds || 2;
  let blueprint = null;
  let critique = null;
  const transcript = [];

  orch.log('🧠 AI Council convened — Strategist vs. Critic');

  for (let round = 1; round <= maxRounds; round++) {
    // ── Strategist proposes (or revises) ────────────────────
    orch.log(`  [Round ${round}/${maxRounds}] 🧠 Strategist ${round === 1 ? 'proposing' : 'revising'}...`);
    orch.emit('council', {
      round,
      speaker: 'strategist',
      action: round === 1 ? 'proposing' : 'revising',
      message: round === 1
        ? `Creating site blueprint for ${clientRequest.businessName}`
        : `Revising based on ${critique.critiques.length} critique(s)`,
    });

    const strategistUserMsg =
      round === 1
        ? strategistPropose(clientRequest)
        : strategistRevise(blueprint, critique);

    const rawProposal = await callAI({
      messages: [
        { role: 'system', content: STRATEGIST_SYSTEM },
        { role: 'user', content: strategistUserMsg },
      ],
      temperature: 0.7,
      maxTokens: 4000,
    });

    blueprint = extractJSON(rawProposal);

    // Validate blueprint structure
    if (!blueprint.pages || !Array.isArray(blueprint.pages) || blueprint.pages.length === 0) {
      throw new Error('Strategist produced invalid blueprint — no pages array');
    }

    // Ensure every page has a slug
    for (const page of blueprint.pages) {
      if (!page.slug) {
        page.slug = page.title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
      }
    }

    const pageList = blueprint.pages.map((p) => p.navLabel || p.title).join(', ');
    orch.log(`  🧠 Strategist proposed ${blueprint.pages.length} pages: ${pageList}`);

    transcript.push({
      round,
      speaker: 'strategist',
      content: blueprint,
      summary: `Proposed ${blueprint.pages.length}-page site: ${pageList}`,
    });

    orch.emit('council', {
      round,
      speaker: 'strategist',
      action: 'proposed',
      message: `${blueprint.pages.length} pages: ${pageList}`,
      pages: blueprint.pages.length,
    });

    // ── Critic reviews ──────────────────────────────────────
    orch.log(`  [Round ${round}/${maxRounds}] 🔍 Critic reviewing...`);
    orch.emit('council', {
      round,
      speaker: 'critic',
      action: 'reviewing',
      message: 'Analyzing blueprint for UX, accessibility, and conversion issues',
    });

    const rawCritique = await callAI({
      messages: [
        { role: 'system', content: CRITIC_SYSTEM },
        { role: 'user', content: criticReview(blueprint) },
      ],
      temperature: 0.4,
      maxTokens: 3000,
    });

    critique = extractJSON(rawCritique);

    const highIssues = (critique.critiques || []).filter((c) => c.severity === 'high').length;
    const medIssues = (critique.critiques || []).filter((c) => c.severity === 'medium').length;

    orch.log(
      `  🔍 Critic: score=${critique.score || '?'}/10, ` +
        `${highIssues} high, ${medIssues} medium issues. ` +
        `Approved: ${critique.approved ? 'YES ✅' : 'NO ❌'}`
    );

    transcript.push({
      round,
      speaker: 'critic',
      content: critique,
      summary: critique.summary || `Score: ${critique.score}/10`,
    });

    orch.emit('council', {
      round,
      speaker: 'critic',
      action: critique.approved ? 'approved' : 'critiqued',
      message: critique.summary || `Score: ${critique.score}/10, ${highIssues} high issues`,
      approved: !!critique.approved,
      score: critique.score,
    });

    // If approved, we're done
    if (critique.approved) {
      orch.log(`  ✅ Council approved blueprint after ${round} round(s)`);
      break;
    }

    // If last round, use what we have
    if (round === maxRounds) {
      orch.log(`  ⚠️ Max council rounds reached — proceeding with current blueprint`);
    }
  }

  // Sanitize color values — strip rationale text, keep only hex
  if (blueprint.colorDirection) {
    for (const [k, v] of Object.entries(blueprint.colorDirection)) {
      const match = String(v).match(/#[0-9A-Fa-f]{3,8}/);
      if (match) blueprint.colorDirection[k] = match[0];
    }
  }

  // Final validation — ensure required fields
  blueprint.siteName = blueprint.siteName || clientRequest.businessName;
  blueprint.tagline = blueprint.tagline || `Professional ${clientRequest.niche} services`;
  blueprint.brandVoice = blueprint.brandVoice || 'professional, clean, modern';
  blueprint.colorDirection = blueprint.colorDirection || {
    primary: '#ED1C24',
    accent: '#00D4FF',
    surface: '#0A0A0F',
    surfaceAlt: '#111118',
    textMain: '#E5E7EB',
    textMuted: '#9CA3AF',
  };
  blueprint.typography = blueprint.typography || {
    headings: 'JetBrains Mono',
    body: 'Inter',
  };

  // Sanitize typography — strip rationale text
  if (blueprint.typography) {
    for (const [k, v] of Object.entries(blueprint.typography)) {
      blueprint.typography[k] = String(v).split('—')[0].split(' - ')[0].trim();
    }
  }

  orch.log(
    `  📋 Final blueprint: ${blueprint.pages.length} pages, ` +
      `voice="${blueprint.brandVoice}", ` +
      `colors: ${blueprint.colorDirection.primary}/${blueprint.colorDirection.accent}`
  );

  return { blueprint, transcript };
};
