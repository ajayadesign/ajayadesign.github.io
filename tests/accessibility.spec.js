// @ts-check
const { test, expect } = require('@playwright/test');
const AxeBuilder = require('@axe-core/playwright').default;

/* ───────────────────────────────────────────────
   MAIN SITE — All viewports
   ─────────────────────────────────────────────── */
test('page loads with correct title', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle(/AjayaDesign/i);
});

test('hero section is visible', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('h1')).toBeVisible();
  await expect(page.locator('h1')).toContainText('One Click Away');
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

  // All 6 required fields must exist
  await expect(form.locator('#business-name')).toBeAttached();
  await expect(form.locator('#niche')).toBeAttached();
  await expect(form.locator('#goals')).toBeAttached();
  await expect(form.locator('#email')).toBeAttached();
  await expect(form.locator('#phone')).toBeAttached();
  await expect(form.locator('#location')).toBeAttached();

  // Fill all required fields and submit
  await form.locator('#business-name').scrollIntoViewIfNeeded();
  await form.locator('#business-name').fill('Test Biz');
  await form.locator('#niche').fill('Tech');
  await form.locator('#goals').fill('Build a site');
  await form.locator('#email').fill('test@example.com');
  await form.locator('#phone').fill('(512) 555-1234');
  await form.locator('#location').fill('Manor, TX');
  await form.locator('button[type="submit"]').click();

  const btn = form.locator('button[type="submit"]');
  await expect(btn).toContainText('Processing', { timeout: 3000 });
  await expect(btn).toContainText('Request Received', { timeout: 10000 });
});

test('optional fields toggle reveals additional inputs', async ({ page }) => {
  await page.goto('/');
  const form = page.locator('#ajayadesign-intake-form');

  // Optional section is hidden by default
  const optionalSection = form.locator('#optional-fields');
  await expect(optionalSection).toBeHidden();

  // Click toggle to show optional fields
  const toggle = form.locator('#toggle-optional');
  await toggle.scrollIntoViewIfNeeded();
  await toggle.click();
  await expect(optionalSection).toBeVisible();

  // Verify enhanced optional fields exist
  await expect(form.locator('#existing-website')).toBeAttached();
  await expect(form.locator('#brand-colors')).toBeAttached();
  await expect(form.locator('#tagline')).toBeAttached();
  await expect(form.locator('#target-audience')).toBeAttached();
  await expect(form.locator('#competitor-urls')).toBeAttached();
  await expect(form.locator('#additional-notes')).toBeAttached();
  await expect(form.locator('#rebuild-checkbox')).toBeAttached();
});

test('rebuild checkbox shows confirmation panel', async ({ page }) => {
  await page.goto('/');
  const form = page.locator('#ajayadesign-intake-form');

  // Expand optional fields
  await form.locator('#toggle-optional').scrollIntoViewIfNeeded();
  await form.locator('#toggle-optional').click();

  const confirmPanel = form.locator('#rebuild-confirm-panel');
  await expect(confirmPanel).toBeHidden();

  // Check the rebuild checkbox
  await form.locator('#rebuild-checkbox').scrollIntoViewIfNeeded();
  await form.locator('#rebuild-checkbox').check();
  await expect(confirmPanel).toBeVisible();

  // Confirmation input should be present
  await expect(form.locator('#rebuild-confirm')).toBeAttached();
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
   ADMIN PAGE
   ─────────────────────────────────────────────── */
test('admin page loads with login screen', async ({ page }) => {
  await page.goto('/admin/');
  await expect(page).toHaveTitle(/Admin/i);
  // Login screen should be visible since we're not authenticated
  const loginScreen = page.locator('#login-screen');
  await expect(loginScreen).toBeVisible();
  await expect(page.locator('#google-login-btn')).toBeVisible();
});

test('admin page has Add Client modal markup', async ({ page }) => {
  await page.goto('/admin/');
  // The add-client-modal exists in DOM but is hidden
  const modal = page.locator('#add-client-modal');
  await expect(modal).toBeAttached();
  await expect(modal).toBeHidden();

  // Modal contains required form fields
  await expect(page.locator('#acm-business-name')).toBeAttached();
  await expect(page.locator('#acm-niche')).toBeAttached();
  await expect(page.locator('#acm-email')).toBeAttached();
  await expect(page.locator('#acm-goals')).toBeAttached();
  // AI parse tab exists
  await expect(page.locator('#acm-tab-ai')).toBeAttached();
  await expect(page.locator('#acm-raw-text')).toBeAttached();
});

test('admin dashboard structure behind login', async ({ page }) => {
  await page.goto('/admin/');
  // Dashboard structural elements exist even behind the login overlay
  await expect(page.locator('#sidebar')).toBeAttached();
  await expect(page.locator('#tab-builds')).toBeAttached();
  await expect(page.locator('#tab-leads')).toBeAttached();
  await expect(page.locator('#build-list')).toBeAttached();
  await expect(page.locator('#empty-state')).toBeAttached();
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
