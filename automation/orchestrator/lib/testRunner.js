// ═══════════════════════════════════════════════════════════════
//  AjayaDesign v2 — Test Runner
//  Generates Playwright tests, runs them, parses results
// ═══════════════════════════════════════════════════════════════
const fs = require('fs');
const path = require('path');
const { exec, tryExec } = require('./shell');

/**
 * Set up test infrastructure in a project directory.
 * Installs deps, creates playwright config and test files.
 */
function setupTests(projectDir, pages) {
  // package.json
  const pkgPath = path.join(projectDir, 'package.json');
  if (!fs.existsSync(pkgPath)) {
    fs.writeFileSync(
      pkgPath,
      JSON.stringify({ name: 'client-site', private: true }, null, 2)
    );
  }

  // Install serve (for local dev server during tests)
  tryExec('npm install --save-dev serve --loglevel=silent', { cwd: projectDir });

  // Link globally installed playwright + axe (pre-installed in Docker)
  const linkResult = tryExec(
    'npm link @playwright/test @axe-core/playwright 2>/dev/null',
    { cwd: projectDir }
  );
  if (!linkResult.ok) {
    tryExec(
      'npm install --save-dev @playwright/test @axe-core/playwright --loglevel=silent',
      { cwd: projectDir }
    );
    tryExec('npx playwright install --with-deps chromium 2>/dev/null', {
      cwd: projectDir,
    });
  }

  // Playwright config
  fs.writeFileSync(
    path.join(projectDir, 'playwright.config.js'),
    `const { defineConfig, devices } = require('@playwright/test');
module.exports = defineConfig({
  testDir: './tests',
  fullyParallel: true,
  retries: 0,
  reporter: [['list'], ['json', { outputFile: 'test-results.json' }]],
  use: { baseURL: 'http://localhost:9333' },
  webServer: {
    command: 'npx serve . -l 9333 -s',
    port: 9333,
    reuseExistingServer: false,
  },
  projects: [
    { name: 'Desktop', use: { ...devices['Desktop Chrome'] } },
    { name: 'Mobile', use: { ...devices['Pixel 5'] } },
  ],
});
`
  );

  // Create test directory
  const testDir = path.join(projectDir, 'tests');
  if (!fs.existsSync(testDir)) fs.mkdirSync(testDir, { recursive: true });

  // Generate per-page test files
  for (const page of pages) {
    const filename = page.slug === 'index' ? 'index.html' : `${page.slug}.html`;
    const route = page.slug === 'index' ? '/' : `/${page.slug}.html`;

    fs.writeFileSync(
      path.join(testDir, `${page.slug}.spec.js`),
      generatePageTest(page.slug, page.title, route)
    );
  }

  // Integration test (cross-page)
  fs.writeFileSync(
    path.join(testDir, 'integration.spec.js'),
    generateIntegrationTest(pages)
  );
}

/**
 * Run all tests and return structured results.
 */
function runTests(projectDir) {
  const result = tryExec('npx playwright test 2>&1', {
    cwd: projectDir,
    timeout: 120_000,
  });

  // Try to parse JSON results
  const jsonPath = path.join(projectDir, 'test-results.json');
  let jsonResults = null;
  try {
    jsonResults = JSON.parse(fs.readFileSync(jsonPath, 'utf-8'));
  } catch {}

  const output = result.output || '';
  const passed = result.ok && !output.includes('failed');

  // Extract failure details
  const failures = [];
  if (!passed) {
    // Parse from output — skip passing lines (✓) and summary lines
    const lines = output.split('\n');
    for (const line of lines) {
      const trimmed = line.trim();
      // Skip passing tests and blank lines
      if (!trimmed || trimmed.startsWith('✓') || trimmed.startsWith('·')) continue;
      if (
        trimmed.match(
          /color-contrast|\[serious\]|\[critical\]|href="#"|Error:|Expected.*Received|scrollWidth/i
        )
      ) {
        failures.push(trimmed);
      }
    }
  }

  return {
    passed,
    output,
    failures,
    jsonResults,
    failedPages: extractFailedPages(output),
  };
}

/**
 * Run tests for a specific page only.
 */
function runPageTest(projectDir, pageSlug) {
  const result = tryExec(
    `npx playwright test tests/${pageSlug}.spec.js 2>&1`,
    { cwd: projectDir, timeout: 90_000 }
  );

  const output = result.output || '';
  const passed = result.ok && !output.includes('failed');

  const failures = [];
  if (!passed) {
    const lines = output.split('\n');
    for (const line of lines) {
      if (
        line.match(
          /color-contrast|href.*#|Error:|serious\]|critical\]|Expected|Received|overflow|axe/i
        )
      ) {
        failures.push(line.trim());
      }
    }
  }

  return { passed, output, failures };
}

// ── Test generators ────────────────────────────────────────────

function generatePageTest(slug, title, route) {
  return `const { test, expect } = require('@playwright/test');
const AxeBuilder = require('@axe-core/playwright').default;

test.describe('${title} page (${slug})', () => {
  test('loads and has content', async ({ page }) => {
    await page.goto('${route}');
    await expect(page.locator('body')).not.toBeEmpty();
    const h1 = page.locator('h1').first();
    if (await h1.count()) await expect(h1).toBeVisible();
  });

  test('no horizontal overflow', async ({ page }) => {
    await page.goto('${route}');
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth
    );
    expect(overflow).toBe(false);
  });

  test('axe accessibility — zero critical/serious violations', async ({ page }) => {
    await page.goto('${route}');
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(500);

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice'])
      .analyze();

    const critical = results.violations.filter(
      (v) => v.impact === 'critical' || v.impact === 'serious'
    );

    if (critical.length > 0) {
      console.log('\\n🔴 Critical/Serious violations on ${route}:');
      critical.forEach((v) => {
        console.log('  [' + v.impact + '] ' + v.id + ': ' + v.description);
        v.nodes.forEach((n) => console.log('    → ' + n.html.substring(0, 120)));
      });
    }

    expect(critical).toHaveLength(0);
  });

  test('all links have valid href', async ({ page }) => {
    await page.goto('${route}');
    const links = page.locator('a[href]');
    const count = await links.count();
    for (let i = 0; i < count; i++) {
      const href = await links.nth(i).getAttribute('href');
      expect(href).toBeTruthy();
      expect(href).not.toBe('#');
    }
  });
});
`;
}

function generateIntegrationTest(pages) {
  const pageChecks = pages
    .map((p) => {
      const route = p.slug === 'index' ? '/' : `/${p.slug}.html`;
      return `    await page.goto('${route}');
    await expect(page.locator('nav')).toBeVisible();
    await expect(page.locator('footer')).toBeVisible();`;
    })
    .join('\n\n');

  const navLinkChecks = pages
    .map((p) => {
      const href = p.slug === 'index' ? '/' : `/${p.slug}.html`;
      const safe = p.slug.replace(/[^a-zA-Z0-9_]/g, '_');
      return `    const link_${safe} = page.locator('nav a[href="${href}"]');
    if (await link_${safe}.count()) await expect(link_${safe}).toBeVisible();`;
    })
    .join('\n');

  return `const { test, expect } = require('@playwright/test');

test.describe('Site Integration', () => {
  test('nav and footer present on all pages', async ({ page }) => {
${pageChecks}
  });

  test('nav links are present on homepage', async ({ page }) => {
    await page.goto('/');
${navLinkChecks}
  });

  test('no broken internal links', async ({ page }) => {
    await page.goto('/');
    const links = page.locator('a[href]');
    const count = await links.count();
    const internalLinks = [];
    for (let i = 0; i < count; i++) {
      const href = await links.nth(i).getAttribute('href');
      if (href && href.startsWith('/') && !href.startsWith('//')) {
        internalLinks.push(href);
      }
    }
    for (const link of [...new Set(internalLinks)]) {
      const res = await page.goto(link);
      expect(res.status(), 'Broken link: ' + link).toBeLessThan(400);
    }
  });
});
`;
}

function extractFailedPages(output) {
  const failed = new Set();
  const lines = output.split('\n');
  for (const line of lines) {
    // Match lines like: ✘ 3 [Desktop] › tests/index.spec.js:20:3 › ... (failed)
    // or lines with ✗, ✘, ×, or containing 'failed' next to a spec file
    const specMatch = line.match(/(\w+)\.spec\.js/);
    if (specMatch && (line.includes('✘') || line.includes('✗') || line.includes('×') || line.match(/\d+\).*failed/))) {
      failed.add(specMatch[1]);
    }
  }
  // Also check for pages mentioned in axe violation output
  const axePageMatch = output.matchAll(/tests\/(\w+)\.spec\.js.*?axe accessibility.*?failed/gis);
  for (const m of axePageMatch) {
    failed.add(m[1]);
  }
  return [...failed];
}

module.exports = { setupTests, runTests, runPageTest };
