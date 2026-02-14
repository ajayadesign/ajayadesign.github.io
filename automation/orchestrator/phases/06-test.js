// ═══════════════════════════════════════════════════════════════
//  Phase 6: Quality Gate — Test + Agentic Fix Loop
//  Per-page tests with auto-fix, then full-site integration
// ═══════════════════════════════════════════════════════════════
const fs = require('fs');
const path = require('path');
const { callAI, extractHTML } = require('../lib/ai');
const { FIXER_SYSTEM, fixerFix } = require('../lib/prompts');
const { setupTests, runTests, runPageTest } = require('../lib/testRunner');

module.exports = async function qualityGate(blueprint, designSystem, projectDir, orch) {
  const maxFix = orch.config.maxFixAttempts || 3;
  const pages = blueprint.pages;

  orch.log('🧪 Quality Gate — setting up tests');

  // ── Set up test infrastructure ────────────────────────────
  setupTests(projectDir, pages);
  orch.log(`  Test files created for ${pages.length} pages + integration`);

  // ── Run all tests ─────────────────────────────────────────
  let attempt = 1;
  let testResult;

  while (attempt <= maxFix) {
    orch.log(`  [Attempt ${attempt}/${maxFix}] ▶ Running full test suite...`);
    orch.emit('test', {
      action: 'run',
      attempt,
      message: `Test run #${attempt}`,
    });

    testResult = runTests(projectDir);

    if (testResult.passed) {
      orch.log(`  ✅ All tests passed on attempt ${attempt}!`);
      orch.emit('test', {
        action: 'pass',
        attempt,
        message: `All tests passed on attempt ${attempt}`,
      });
      return { passed: true, attempts: attempt };
    }

    // Tests failed
    const failedCount = testResult.failures.length;
    orch.log(`  ❌ Tests failed (${failedCount} issue(s)) on attempt ${attempt}`);
    orch.emit('test', {
      action: 'fail',
      attempt,
      message: `${failedCount} failure(s) on attempt ${attempt}`,
    });

    // If exhausted retries, report failure
    if (attempt >= maxFix) {
      orch.log(`  ❌ TESTS FAILED after ${maxFix} attempts — proceeding anyway`);
      orch.log(`    Failures:\n    ${testResult.failures.slice(0, 10).join('\n    ')}`);
      return { passed: false, attempts: attempt, failures: testResult.failures };
    }

    // ── Agentic fix: try to fix pages individually ──────────
    orch.log(`  🔧 Attempting AI auto-fix (attempt ${attempt + 1})...`);

    // Identify which pages failed (if possible)
    const failedPages = testResult.failedPages || [];

    if (failedPages.length > 0) {
      // Fix specific failed pages
      for (const slug of failedPages) {
        await fixPage(slug, projectDir, testResult.failures, designSystem, blueprint, orch);
      }
    } else {
      // Can't identify specific pages — fix all pages
      for (const page of pages) {
        await fixPage(page.slug, projectDir, testResult.failures, designSystem, blueprint, orch);
      }
    }

    attempt++;
  }

  return { passed: false, attempts: attempt };
};

// ── Fix a single page ──────────────────────────────────────────

async function fixPage(slug, projectDir, failures, designSystem, blueprint, orch) {
  const filename = slug === 'index' ? 'index.html' : `${slug}.html`;
  const filePath = path.join(projectDir, filename);

  if (!fs.existsSync(filePath)) return;

  orch.log(`    🔧 Fixing ${filename}...`);
  orch.emit('agent', {
    page: slug,
    action: 'fixing',
    detail: `Auto-fixing ${filename}`,
  });

  try {
    const fullHtml = fs.readFileSync(filePath, 'utf-8');

    // Extract <main> content
    const mainMatch = fullHtml.match(/<main[\s>][\s\S]*<\/main>/i);
    if (!mainMatch) {
      orch.log(`    ⚠️ Could not extract <main> from ${filename}, skipping fix`);
      return;
    }

    const mainContent = mainMatch[0];
    const errorSummary = failures.slice(0, 15).join('\n');

    // Ask AI to fix (use extra retries for rate limiting during fix cycles)
    const fixedMain = await callAI({
      messages: [
        { role: 'system', content: FIXER_SYSTEM },
        { role: 'user', content: fixerFix(mainContent, errorSummary) },
      ],
      temperature: 0.3,
      maxTokens: 8000,
      retries: 4,
    });

    // Validate response
    const cleanFixed = extractHTML(fixedMain);
    if (!cleanFixed.includes('<main') && !cleanFixed.includes('<section')) {
      orch.log(`    ⚠️ AI fix for ${filename} invalid, keeping original`);
      return;
    }

    // Reconstruct full page with fixed <main>
    let fixedContent = cleanFixed;
    if (!fixedContent.startsWith('<main')) {
      fixedContent = `<main>\n${fixedContent}\n</main>`;
    }

    // Find the page spec for this slug
    const pageSpec = blueprint.pages.find((p) => p.slug === slug) || {
      title: slug,
      slug,
      purpose: '',
    };

    // Rebuild the full page with design system wrapper
    const rebuilt = rebuildPage(fixedContent, designSystem, blueprint, pageSpec, fullHtml);
    fs.writeFileSync(filePath, rebuilt, 'utf-8');

    orch.log(`    ✅ ${filename} fixed (${Buffer.byteLength(rebuilt)} bytes)`);
    orch.emit('agent', { page: slug, action: 'fixed', detail: 'AI fix applied' });
  } catch (err) {
    orch.log(`    ⚠️ Fix failed for ${filename}: ${err.message}`);
  }
}

// ── Rebuild a page preserving head/nav/footer ──────────────────

function rebuildPage(newMain, ds, blueprint, pageSpec, originalHtml) {
  // Try to preserve the original <head> content (may have page-specific meta)
  const headMatch = originalHtml.match(/<head>([\s\S]*?)<\/head>/i);
  const headContent = headMatch ? headMatch[1] : ds.sharedHead;

  // Preserve nav from original (it has the correct active states)
  const navMatch = originalHtml.match(/<nav[\s>][\s\S]*?<\/nav>/i);
  const navHtml = navMatch ? navMatch[0] : ds.navHtml;

  // Preserve footer from original
  const footerMatch = originalHtml.match(/<footer[\s>][\s\S]*?<\/footer>/i);
  const footerHtml = footerMatch ? footerMatch[0] : ds.footerHtml;

  return `<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
${headContent}
</head>
<body class="${ds.bodyClass}">

${navHtml}

${newMain}

${footerHtml}

${ds.mobileMenuJs || ''}
</body>
</html>`;
}
