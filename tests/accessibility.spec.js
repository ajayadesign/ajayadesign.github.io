// @ts-check
const { test, expect } = require('@playwright/test');
const AxeBuilder = require('@axe-core/playwright').default;

/* ───────────────────────────────────────────────
   SHARED  –  All viewports
   ─────────────────────────────────────────────── */
test('page loads with correct title', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle(/AjayaDesign/i);
});

test('hero section is visible', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('h1')).toBeVisible();
  await expect(page.locator('h1')).toContainText('Engineering Precision');
});

test('all nav links point to valid anchors', async ({ page }) => {
  await page.goto('/');
  const anchors = page.locator('nav a[href^="#"]');
  const hrefs = await anchors.evaluateAll(els => els.map(e => e.getAttribute('href')));
  for (const href of hrefs) {
    const id = href.replace('#', '');
    if (!id) continue;
    await expect(page.locator(`#${id}`)).toBeAttached();
  }
});

test('intake form has all required fields and submits', async ({ page }) => {
  await page.goto('/');
  const form = page.locator('#ajayadesign-intake-form');
  await expect(form).toBeAttached();
  await expect(form.locator('#business-name')).toBeAttached();
  await expect(form.locator('#niche')).toBeAttached();
  await expect(form.locator('#goals')).toBeAttached();
  await expect(form.locator('#email')).toBeAttached();

  // Fill and submit
  await form.locator('#business-name').scrollIntoViewIfNeeded();
  await form.locator('#business-name').fill('Test Biz');
  await form.locator('#niche').fill('Tech');
  await form.locator('#goals').fill('Build a site');
  await form.locator('#email').fill('test@example.com');
  await form.locator('button[type="submit"]').click();

  const btn = form.locator('button[type="submit"]');
  await expect(btn).toContainText('Processing', { timeout: 3000 });
  await expect(btn).toContainText('Build Initiated', { timeout: 5000 });
});

test('portfolio links point to local submodule paths', async ({ page }) => {
  await page.goto('/');
  const links = page.locator('#works a[target="_blank"]');
  const count = await links.count();
  expect(count).toBeGreaterThanOrEqual(4);
  for (let i = 0; i < count; i++) {
    const href = await links.nth(i).getAttribute('href');
    // Each portfolio card links to /<submodule-name>/
    expect(href).toMatch(/^\/[a-z0-9-]+\//);
    await expect(links.nth(i)).toHaveAttribute('rel', /noopener/);
  }
});

test('no horizontal overflow', async ({ page }) => {
  await page.goto('/');
  const overflow = await page.evaluate(() =>
    document.documentElement.scrollWidth > document.documentElement.clientWidth
  );
  expect(overflow).toBe(false);
});

test('axe accessibility audit — zero critical or serious violations', async ({ page }) => {
  await page.goto('/');
  // Scroll to trigger reveals so all content is in the DOM
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await page.waitForTimeout(1000);
  await page.evaluate(() => window.scrollTo(0, 0));

  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice'])
    .analyze();

  const critical = results.violations.filter(
    v => v.impact === 'critical' || v.impact === 'serious'
  );

  if (critical.length > 0) {
    console.log('\n🔴 Critical/Serious axe violations:');
    critical.forEach(v => {
      console.log(`  [${v.impact}] ${v.id}: ${v.description}`);
      v.nodes.forEach(n => console.log(`    → ${n.html.substring(0, 150)}`));
    });
  }

  expect(critical).toHaveLength(0);
});

/* ───────────────────────────────────────────────
   MOBILE-ONLY  –  Skipped on desktop projects
   ─────────────────────────────────────────────── */
test('mobile menu toggles', async ({ page }, testInfo) => {
  if (!testInfo.project.name.toLowerCase().includes('mobile')) {
    test.skip();
  }
  await page.goto('/');
  const menuBtn = page.locator('#mobile-menu-btn');
  const mobileMenu = page.locator('#mobile-menu');

  await expect(mobileMenu).toBeHidden();
  await menuBtn.click();
  await expect(mobileMenu).toBeVisible();

  // Clicking a link closes the menu
  await mobileMenu.locator('a[href="#edge"]').click();
  await expect(mobileMenu).toBeHidden();
});

test('hero CTA meets minimum touch target size', async ({ page }, testInfo) => {
  if (!testInfo.project.name.toLowerCase().includes('mobile')) {
    test.skip();
  }
  await page.goto('/');
  // On mobile the nav CTA is hidden; pick the visible hero CTA
  const cta = page.locator('section a[href="#intake"]').first();
  await expect(cta).toBeVisible();
  const box = await cta.boundingBox();
  // WCAG 2.5.8 Target Size (minimum) — 24x24 CSS pixels (AA)
  expect(box.height).toBeGreaterThanOrEqual(24);
  expect(box.width).toBeGreaterThanOrEqual(24);
});
