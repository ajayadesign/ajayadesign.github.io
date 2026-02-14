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

  // ── Validate contrast ratios & auto-fix ───────────────────
  const ctaColors = extractColorsFromConfig(ds.tailwindConfig, ['cta', 'primary', 'accent']);
  for (const [name, hex] of Object.entries(ctaColors)) {
    if (hex && !passesContrast(hex, '#ffffff', 4.5)) {
      const darkened = darkenUntilContrast(hex, '#ffffff', 4.5);
      orch.log(`    ⚠️ ${name} (${hex}) fails WCAG AA vs white → fixed to ${darkened}`);
      ds.tailwindConfig = ds.tailwindConfig.replace(
        new RegExp(`(['"]?)${escRegex(hex)}\\1`, 'gi'),
        `'${darkened}'`
      );
    }
  }

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

// ── WCAG Contrast Utilities ───────────────────────────────────

function hexToRgb(hex) {
  hex = hex.replace('#', '');
  if (hex.length === 3) hex = hex[0]+hex[0]+hex[1]+hex[1]+hex[2]+hex[2];
  const n = parseInt(hex, 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function luminance([r, g, b]) {
  const [rs, gs, bs] = [r, g, b].map(c => {
    c = c / 255;
    return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
}

function contrastRatio(hex1, hex2) {
  const l1 = luminance(hexToRgb(hex1));
  const l2 = luminance(hexToRgb(hex2));
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

function passesContrast(fg, bg, ratio) {
  return contrastRatio(fg, bg) >= ratio;
}

function darkenUntilContrast(hex, against, targetRatio) {
  let [r, g, b] = hexToRgb(hex);
  for (let i = 0; i < 100; i++) {
    const candidate = '#' + [r, g, b].map(c => c.toString(16).padStart(2, '0')).join('');
    if (contrastRatio(candidate, against) >= targetRatio) return candidate;
    r = Math.max(0, r - 5);
    g = Math.max(0, g - 5);
    b = Math.max(0, b - 5);
  }
  return '#1a1a1a'; // fallback very dark
}

function extractColorsFromConfig(configStr, colorNames) {
  const colors = {};
  for (const name of colorNames) {
    // Match patterns like cta: '#FF6347' or 'cta': '#FF6347'
    const match = configStr.match(new RegExp(`['"]?${name}['"]?\\s*:\\s*['"]?(#[0-9A-Fa-f]{3,8})['"]?`));
    if (match) colors[name] = match[1];
  }
  return colors;
}

function escRegex(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

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
