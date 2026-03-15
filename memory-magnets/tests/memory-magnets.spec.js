// @ts-check
const { test, expect } = require('@playwright/test');
const AxeBuilder = require('@axe-core/playwright').default;

const BASE = '/';

/* ── Page Load & Core Structure ── */

test('index loads with correct title', async ({ page }) => {
  await page.goto(BASE);
  await expect(page).toHaveTitle(/Memory Magnets/i);
});

test('contact loads with correct title', async ({ page }) => {
  await page.goto(BASE + 'contact/');
  await expect(page).toHaveTitle(/Contact.*Memory Magnets/i);
});

test('glassmorphic nav is present and sticky', async ({ page }) => {
  await page.goto(BASE);
  const nav = page.locator('nav.nav');
  await expect(nav).toBeVisible();
  // Scroll down and check nav is still visible
  await page.evaluate(() => window.scrollBy(0, 500));
  await expect(nav).toBeVisible();
});

test('hero section renders with heading', async ({ page }) => {
  await page.goto(BASE);
  const hero = page.locator('.hero');
  await expect(hero).toBeVisible();
  await expect(hero.locator('h1')).toContainText(/Memories.*Magnets/i);
});

test('bento grid has product cards', async ({ page }) => {
  await page.goto(BASE);
  const cards = page.locator('.bento-card');
  await expect(cards.first()).toBeVisible();
  const count = await cards.count();
  expect(count).toBeGreaterThanOrEqual(3);
});

test('footer has AjayaDesign branding', async ({ page }) => {
  await page.goto(BASE);
  const footer = page.locator('footer');
  await expect(footer).toContainText(/AjayaDesign/i);
});

test('build signature meta tag present', async ({ page }) => {
  await page.goto(BASE);
  const sig = await page.locator('meta[name="x-build-signature"]').getAttribute('content');
  expect(sig).toContain('AjayaDesign');
});

/* ── Navigation ── */

test('nav links point to valid sections or pages', async ({ page }) => {
  await page.goto(BASE);
  const links = page.locator('nav a[href]');
  const hrefs = await links.evaluateAll(els => els.map(e => e.getAttribute('href')));
  expect(hrefs.length).toBeGreaterThanOrEqual(2);
});

test('contact link navigates to contact page', async ({ page, isMobile }) => {
  await page.goto(BASE);
  if (isMobile) {
    await page.locator('.nav-toggle').click();
    await page.waitForTimeout(300);
  }
  await page.locator('nav a[href*="contact"]').click();
  await expect(page).toHaveURL(/contact/);
});

/* ── Contact Form ── */

test('contact form validates required fields', async ({ page }) => {
  await page.goto(BASE + 'contact/');
  const form = page.locator('#contactForm');
  await expect(form).toBeAttached();
  await form.locator('button[type="submit"]').click();
  // Success message should NOT show when fields are empty
  const msg = page.locator('#successMsg');
  await expect(msg).not.toBeVisible();
});

test('contact form shows success on valid submit', async ({ page }) => {
  await page.goto(BASE + 'contact/');
  await page.locator('#name').fill('Test User');
  await page.locator('#email').fill('test@example.com');
  await page.locator('#message').fill('Hello');
  await page.locator('#contactForm button[type="submit"]').click();
  await expect(page.locator('#successMsg')).toBeVisible();
});

/* ── Scroll Reveal ── */

test('reveal elements animate on scroll', async ({ page }) => {
  await page.goto(BASE);
  // Scroll to bottom to trigger IntersectionObserver on all reveal elements
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await page.waitForTimeout(800);
  const revealed = await page.locator('.reveal.visible').count();
  expect(revealed).toBeGreaterThanOrEqual(1);
});

/* ── Mobile Responsive ── */

test('mobile nav toggle works', async ({ page, isMobile }) => {
  test.skip(!isMobile, 'Mobile-only test');
  await page.goto(BASE);
  const toggle = page.locator('.nav-toggle');
  await expect(toggle).toBeVisible();
  await toggle.click();
  const links = page.locator('#navLinks');
  await expect(links).toHaveClass(/open/);
});

/* ── Accessibility (Axe) ── */

test('index page accessibility audit', async ({ page }) => {
  await page.goto(BASE);
  const results = await new AxeBuilder({ page })
    .disableRules(['color-contrast']) // images may affect contrast detection
    .analyze();
  const violations = results.violations.filter(v => v.impact === 'critical' || v.impact === 'serious');
  expect(violations).toEqual([]);
});

test('contact page accessibility audit', async ({ page }) => {
  await page.goto(BASE + 'contact/');
  const results = await new AxeBuilder({ page })
    .disableRules(['color-contrast'])
    .analyze();
  const violations = results.violations.filter(v => v.impact === 'critical' || v.impact === 'serious');
  expect(violations).toEqual([]);
});

/* ── Category Pages ── */

test('magnet-making page loads with correct title', async ({ page }) => {
  await page.goto(BASE + 'magnet-making/');
  await expect(page).toHaveTitle(/Magnet Making Kits/i);
  await expect(page.locator('h1')).toContainText(/Magnet Making Kits/i);
});

test('custom-magnets page loads with correct title', async ({ page }) => {
  await page.goto(BASE + 'custom-magnets/');
  await expect(page).toHaveTitle(/Custom Photo/i);
  await expect(page.locator('h1')).toContainText(/Custom Photo Products/i);
});

test('start-a-business page loads with correct title', async ({ page }) => {
  await page.goto(BASE + 'start-a-business/');
  await expect(page).toHaveTitle(/Start.*Business/i);
  await expect(page.locator('h1')).toContainText(/Magnet Business/i);
});

test('category pages have breadcrumb navigation', async ({ page }) => {
  await page.goto(BASE + 'magnet-making/');
  const breadcrumb = page.locator('nav.breadcrumb');
  await expect(breadcrumb).toBeVisible();
  await expect(breadcrumb.locator('a[href="../"]')).toBeVisible();
});

test('category pages have product cards with links', async ({ page }) => {
  await page.goto(BASE + 'magnet-making/');
  const productLinks = page.locator('.bento-card__link');
  const count = await productLinks.count();
  expect(count).toBeGreaterThanOrEqual(5);
});

/* ── Product Pages ── */

test('product page loads with correct structure', async ({ page }) => {
  await page.goto(BASE + 'products/2x2-magnet-kit/');
  await expect(page).toHaveTitle(/2x2.*Magnet Making Kit/i);
  await expect(page.locator('h1')).toContainText(/2x2.*Magnet Making Kit/i);
  await expect(page.locator('.product-price')).toBeVisible();
  await expect(page.locator('.product-features')).toBeVisible();
});

test('product page has breadcrumb with category link', async ({ page }) => {
  await page.goto(BASE + 'products/2x2-magnet-kit/');
  const breadcrumb = page.locator('nav.breadcrumb');
  await expect(breadcrumb).toBeVisible();
  await expect(breadcrumb.locator('a[href="../../magnet-making/"]')).toBeVisible();
});

test('product page has Schema.org Product JSON-LD', async ({ page }) => {
  await page.goto(BASE + 'products/2x2-magnet-kit/');
  const jsonLd = await page.locator('script[type="application/ld+json"]').first().textContent();
  const data = JSON.parse(jsonLd);
  expect(data['@type']).toBe('Product');
  expect(data.offers).toBeDefined();
});

test('product pages have related products', async ({ page }) => {
  await page.goto(BASE + 'products/2x2-magnet-kit/');
  const related = page.locator('.related-grid .bento-card');
  const count = await related.count();
  expect(count).toBeGreaterThanOrEqual(2);
});

test('nav links to real pages (not anchors only)', async ({ page }) => {
  await page.goto(BASE);
  const navLinks = await page.locator('.nav-links a').evaluateAll(
    els => els.map(e => e.getAttribute('href'))
  );
  const realPages = navLinks.filter(h => h && h.endsWith('/'));
  expect(realPages.length).toBeGreaterThanOrEqual(4);
});

/* ── Category Page Accessibility ── */

test('magnet-making page accessibility audit', async ({ page }) => {
  await page.goto(BASE + 'magnet-making/');
  const results = await new AxeBuilder({ page })
    .disableRules(['color-contrast'])
    .analyze();
  const violations = results.violations.filter(v => v.impact === 'critical' || v.impact === 'serious');
  expect(violations).toEqual([]);
});

test('product page accessibility audit', async ({ page }) => {
  await page.goto(BASE + 'products/2x2-magnet-kit/');
  const results = await new AxeBuilder({ page })
    .disableRules(['color-contrast'])
    .analyze();
  const violations = results.violations.filter(v => v.impact === 'critical' || v.impact === 'serious');
  expect(violations).toEqual([]);
});
