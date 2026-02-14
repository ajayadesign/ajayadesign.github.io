// ═══════════════════════════════════════════════════════════════
//  Phase 5: Assembly + Cross-Page Stitching
//  Nav active states, sitemap, robots.txt, 404, link validation
// ═══════════════════════════════════════════════════════════════
const fs = require('fs');
const path = require('path');

module.exports = async function assemble(blueprint, designSystem, projectDir, orch) {
  orch.log('📎 Assembling site — stitching nav, sitemap, cross-links');

  const pages = blueprint.pages;

  // ── 1. Fix navigation active states ───────────────────────
  orch.log('  1/5 Fixing nav active states...');
  for (const page of pages) {
    const filename = page.slug === 'index' ? 'index.html' : `${page.slug}.html`;
    const filePath = path.join(projectDir, filename);

    if (!fs.existsSync(filePath)) continue;

    let html = fs.readFileSync(filePath, 'utf-8');

    // Replace {{ACTIVE:slug}} placeholders
    for (const p of pages) {
      const placeholder = `{{ACTIVE:${p.slug}}}`;
      const replacement =
        p.slug === page.slug
          ? designSystem.activeNavClass
          : designSystem.inactiveNavClass;
      html = html.replace(new RegExp(escRegex(placeholder), 'g'), replacement);
    }

    // Handle {{ACTIVE:}} (empty slug) — treat as index page
    const emptyActiveReplacement =
      page.slug === 'index'
        ? designSystem.activeNavClass
        : designSystem.inactiveNavClass;
    html = html.replace(/\{\{ACTIVE:\}\}/g, emptyActiveReplacement);

    // Catch any remaining {{ACTIVE:*}} placeholders
    html = html.replace(/\{\{ACTIVE:\w*\}\}/g, designSystem.inactiveNavClass);

    fs.writeFileSync(filePath, html, 'utf-8');
  }
  orch.log('    ✅ Nav active states set');

  // ── 2. Generate sitemap.xml ───────────────────────────────
  orch.log('  2/5 Generating sitemap.xml...');
  const siteUrl = `https://ajayadesign.github.io/${path.basename(projectDir)}`;
  const today = new Date().toISOString().split('T')[0];

  const sitemapEntries = pages
    .map((p) => {
      const loc =
        p.slug === 'index' ? siteUrl + '/' : `${siteUrl}/${p.slug}.html`;
      const priority = p.slug === 'index' ? '1.0' : '0.8';
      return `  <url>
    <loc>${loc}</loc>
    <lastmod>${today}</lastmod>
    <priority>${priority}</priority>
  </url>`;
    })
    .join('\n');

  fs.writeFileSync(
    path.join(projectDir, 'sitemap.xml'),
    `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${sitemapEntries}
</urlset>`,
    'utf-8'
  );
  orch.log('    ✅ sitemap.xml generated');

  // ── 3. Generate robots.txt ────────────────────────────────
  orch.log('  3/5 Generating robots.txt...');
  fs.writeFileSync(
    path.join(projectDir, 'robots.txt'),
    `User-agent: *
Allow: /
Sitemap: ${siteUrl}/sitemap.xml
`,
    'utf-8'
  );
  orch.log('    ✅ robots.txt generated');

  // ── 4. Generate 404.html ──────────────────────────────────
  orch.log('  4/5 Generating 404.html...');
  const notFoundPage = build404(designSystem, blueprint);
  fs.writeFileSync(path.join(projectDir, '404.html'), notFoundPage, 'utf-8');
  orch.log('    ✅ 404.html generated');

  // ── 5. Validate cross-page links ─────────────────────────
  orch.log('  5/5 Validating cross-page links...');
  const existingFiles = fs
    .readdirSync(projectDir)
    .filter((f) => f.endsWith('.html'));

  let brokenLinks = 0;
  for (const file of existingFiles) {
    const html = fs.readFileSync(path.join(projectDir, file), 'utf-8');

    // Find all href="/something.html" links
    const linkMatches = html.matchAll(/href="\/([^"]+\.html)"/g);
    for (const match of linkMatches) {
      const target = match[1];
      if (!existingFiles.includes(target)) {
        orch.log(`    ⚠️ Broken link in ${file}: /${target} → file not found`);
        brokenLinks++;
      }
    }

    // Check for href="#" violations
    if (html.includes('href="#"')) {
      orch.log(`    ⚠️ href="#" found in ${file} — should use real targets`);
      brokenLinks++;
    }
  }

  if (brokenLinks === 0) {
    orch.log('    ✅ All cross-page links valid');
  } else {
    orch.log(`    ⚠️ ${brokenLinks} link issue(s) found`);
  }

  // ── Generate .gitignore ───────────────────────────────────
  fs.writeFileSync(
    path.join(projectDir, '.gitignore'),
    `node_modules/
test-results/
test-results.json
playwright-report/
`,
    'utf-8'
  );

  orch.log('  ✅ Assembly complete');
};

// ── Build a styled 404 page ────────────────────────────────────

function build404(ds, blueprint) {
  const nav = (ds.navHtml || '').replace(/\{\{ACTIVE:\w*\}\}/g, ds.inactiveNavClass || '');
  const footer = ds.footerHtml || '';
  const body = ds.bodyClass || 'antialiased';
  const mobile = ds.mobileMenuJs || '';

  return `<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
${ds.sharedHead || '<meta charset="UTF-8">'}
  <title>Page Not Found — ${escHtml(ds.siteName || blueprint.siteName)}</title>
</head>
<body class="${body}">

${nav}

<main class="min-h-[70vh] flex items-center justify-center px-6">
  <div class="text-center max-w-xl">
    <div class="text-8xl mb-6 opacity-30">404</div>
    <h1 class="font-heading text-3xl font-bold text-textMain mb-4">Page Not Found</h1>
    <p class="text-textMuted mb-8">The page you're looking for doesn't exist or has been moved.</p>
    <a href="/" class="inline-block px-8 py-3 bg-primary text-white font-body font-bold rounded-lg hover:opacity-90 transition">
      ← Back to Home
    </a>
  </div>
</main>

${footer}

${mobile}
</body>
</html>`;
}

function escHtml(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function escRegex(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
