// ═══════════════════════════════════════════════════════════════
//  Phase 3: Design System Generation
//  Creates the shared visual contract for all page agents
// ═══════════════════════════════════════════════════════════════
const { callAI, extractJSON } = require('../lib/ai');
const { DESIGNER_SYSTEM, designerCreate } = require('../lib/prompts');

module.exports = async function generateDesignSystem(blueprint, orch) {
  orch.log('🎨 Generating design system (Tailwind config + shared nav/footer)');

  orch.emit('agent', {
    page: '_design',
    action: 'generating',
    detail: 'Creating shared design system contract',
  });

  const raw = await callAI({
    messages: [
      { role: 'system', content: DESIGNER_SYSTEM },
      { role: 'user', content: designerCreate(blueprint) },
    ],
    temperature: 0.5,
    maxTokens: 6000,
  });

  const ds = extractJSON(raw);

  // Validate required keys
  const required = ['tailwindConfig', 'googleFontsUrl', 'navHtml', 'footerHtml'];
  for (const key of required) {
    if (!ds[key]) {
      throw new Error(`Design system missing required key: ${key}`);
    }
  }

  // Set defaults for optional keys
  ds.bodyClass = ds.bodyClass || 'bg-surface text-textMain font-body antialiased';
  ds.activeNavClass = ds.activeNavClass || 'text-primary font-bold';
  ds.inactiveNavClass = ds.inactiveNavClass || 'text-textMuted hover:text-primary transition';
  ds.mobileMenuJs = ds.mobileMenuJs || '';
  ds.siteName = blueprint.siteName;

  // Build the shared <head> content
  ds.sharedHead = buildSharedHead(ds, blueprint);

  orch.log(`  ✅ Design system ready`);
  orch.log(`    Fonts: ${ds.googleFontsUrl.slice(0, 80)}...`);
  orch.log(`    Nav: ${ds.navHtml.length} chars, Footer: ${ds.footerHtml.length} chars`);

  orch.emit('agent', {
    page: '_design',
    action: 'done',
    detail: `Tailwind config + nav (${ds.navHtml.length}c) + footer (${ds.footerHtml.length}c)`,
  });

  return ds;
};

function buildSharedHead(ds, blueprint) {
  // If design system already provides sharedHead, use it
  if (ds.sharedHead && ds.sharedHead.includes('tailwindcss')) {
    return ds.sharedHead;
  }

  return `  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="${ds.googleFontsUrl}" rel="stylesheet">
  <script>
    ${ds.tailwindConfig}
  </script>
  <style>
    html { scroll-behavior: smooth; }
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: #333; border-radius: 3px; }
  </style>`;
}
