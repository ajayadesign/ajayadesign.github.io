// ═══════════════════════════════════════════════════════════════
//  Phase 4: Page Generation
//  Generates each page's <main> content, wraps with design system
// ═══════════════════════════════════════════════════════════════
const fs = require('fs');
const path = require('path');
const { callAI, extractHTML } = require('../lib/ai');
const { PAGE_BUILDER_SYSTEM, pageBuilderCreate } = require('../lib/prompts');

module.exports = async function generatePages(blueprint, designSystem, projectDir, orch) {
  const pages = blueprint.pages;
  const results = [];

  orch.log(`🤖 Generating ${pages.length} pages (sequential)`);

  for (let i = 0; i < pages.length; i++) {
    const page = pages[i];
    const filename = page.slug === 'index' ? 'index.html' : `${page.slug}.html`;

    orch.log(`  [${i + 1}/${pages.length}] Generating ${filename} — "${page.title}"`);

    orch.emit('agent', {
      page: page.slug,
      action: 'generating',
      detail: `Building ${page.title} page`,
      index: i + 1,
      total: pages.length,
    });

    try {
      // Call AI for page body (<main>)
      const rawMain = await callAI({
        messages: [
          { role: 'system', content: PAGE_BUILDER_SYSTEM },
          { role: 'user', content: pageBuilderCreate(page, designSystem, blueprint) },
        ],
        temperature: 0.7,
        maxTokens: 8000,
      });

      // Extract <main> content (AI might return extra wrapper)
      let mainContent = extractMainContent(rawMain);

      // Assemble full page
      const fullPage = wrapWithDesignSystem(
        mainContent,
        designSystem,
        blueprint,
        page
      );

      // Write to file
      const filePath = path.join(projectDir, filename);
      fs.writeFileSync(filePath, fullPage, 'utf-8');

      const size = Buffer.byteLength(fullPage);
      orch.log(`  ✅ ${filename} generated (${size} bytes)`);

      orch.emit('agent', {
        page: page.slug,
        action: 'done',
        detail: `${size} bytes`,
        index: i + 1,
        total: pages.length,
      });

      results.push({ slug: page.slug, filename, status: 'generated', size });
    } catch (err) {
      orch.log(`  ❌ ${filename} FAILED: ${err.message}`);

      orch.emit('agent', {
        page: page.slug,
        action: 'error',
        detail: err.message,
        index: i + 1,
        total: pages.length,
      });

      // Generate fallback page
      const fallback = generateFallbackPage(designSystem, blueprint, page);
      fs.writeFileSync(path.join(projectDir, filename), fallback, 'utf-8');

      orch.log(`  ⚠️ ${filename} — using fallback page`);
      results.push({ slug: page.slug, filename, status: 'fallback' });
    }
  }

  return results;
};

// ── Extract <main>...</main> from AI output ────────────────────

function extractMainContent(raw) {
  // If AI output contains <main>, extract it
  const mainMatch = raw.match(/<main[\s>][\s\S]*<\/main>/i);
  if (mainMatch) return mainMatch[0];

  // If it's a partial (just sections without <main> wrapper)
  if (raw.includes('<section') || raw.includes('<div')) {
    return `<main>\n${raw}\n</main>`;
  }

  // Fallback — wrap whatever we got
  return `<main class="pt-20">\n${raw}\n</main>`;
}

// ── Wrap page content with design system shell ─────────────────

function wrapWithDesignSystem(mainContent, ds, blueprint, pageSpec) {
  const title = `${pageSpec.title} — ${ds.siteName || blueprint.siteName}`;
  const description =
    pageSpec.purpose || blueprint.tagline || `${ds.siteName} - ${pageSpec.title}`;
  const year = new Date().getFullYear();

  return `<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
${ds.sharedHead}
  <title>${escHtml(title)}</title>
  <meta name="description" content="${escHtml(description)}">
  <meta property="og:title" content="${escHtml(title)}">
  <meta property="og:description" content="${escHtml(description)}">
  <meta property="og:type" content="website">
</head>
<body class="${ds.bodyClass}">

${ds.navHtml}

${mainContent}

${ds.footerHtml}

${ds.mobileMenuJs || ''}
</body>
</html>`;
}

// ── Fallback page (always works, no AI needed) ─────────────────

function generateFallbackPage(ds, blueprint, pageSpec) {
  const mainContent = `<main class="pt-24">
  <section class="min-h-[60vh] flex items-center justify-center px-6">
    <div class="text-center max-w-3xl">
      <h1 class="font-heading text-4xl md:text-6xl font-bold text-textMain mb-6">${escHtml(pageSpec.title)}</h1>
      <p class="text-xl text-textMuted mb-8">${escHtml(pageSpec.purpose || blueprint.tagline || '')}</p>
      <a href="/contact.html" class="inline-block px-8 py-3 bg-cta text-white font-body font-bold rounded-lg hover:opacity-90 transition">
        Get in Touch
      </a>
    </div>
  </section>
</main>`;

  return wrapWithDesignSystem(mainContent, ds, blueprint, pageSpec);
}

function escHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
