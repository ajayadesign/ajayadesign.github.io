// @ts-check
const { test, expect } = require('@playwright/test');
const AxeBuilder = require('@axe-core/playwright').default;

const BASE = '/';

/* ══════════════════════════════════════════════
   Page Load & Core Structure
   ══════════════════════════════════════════════ */

test('homepage loads with correct title', async ({ page }) => {
  await page.goto(BASE);
  await expect(page).toHaveTitle(/Magnetic Soul/i);
});

test('about page loads with correct title', async ({ page }) => {
  await page.goto(BASE + 'about/');
  await expect(page).toHaveTitle(/About.*Magnetic Soul/i);
});

test('contact page loads with correct title', async ({ page }) => {
  await page.goto(BASE + 'contact/');
  await expect(page).toHaveTitle(/Contact.*Magnetic Soul/i);
});

test('FAQ page loads with correct title', async ({ page }) => {
  await page.goto(BASE + 'faq/');
  await expect(page).toHaveTitle(/FAQ.*Magnetic Soul/i);
});

test('shipping page loads with correct title', async ({ page }) => {
  await page.goto(BASE + 'shipping/');
  await expect(page).toHaveTitle(/Shipping.*Magnetic Soul/i);
});

test('glassmorphic nav is present and sticky', async ({ page }) => {
  await page.goto(BASE);
  const nav = page.locator('nav.nav');
  await expect(nav).toBeVisible();
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

/* ══════════════════════════════════════════════
   Navigation
   ══════════════════════════════════════════════ */

test('nav links point to valid pages', async ({ page }) => {
  await page.goto(BASE);
  const links = page.locator('nav a[href]');
  const hrefs = await links.evaluateAll(els => els.map(e => e.getAttribute('href')));
  expect(hrefs.length).toBeGreaterThanOrEqual(5);
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

test('nav links to real pages (not anchors only)', async ({ page }) => {
  await page.goto(BASE);
  const navLinks = await page.locator('.nav-links a').evaluateAll(
    els => els.map(e => e.getAttribute('href'))
  );
  const realPages = navLinks.filter(h => h && h.endsWith('/'));
  expect(realPages.length).toBeGreaterThanOrEqual(4);
});

/* ══════════════════════════════════════════════
   Contact Form
   ══════════════════════════════════════════════ */

test('contact form validates required fields', async ({ page }) => {
  await page.goto(BASE + 'contact/');
  const form = page.locator('#contact-form');
  await expect(form).toBeAttached();
  await form.locator('button[type="submit"]').click();
  // Form should still be visible (not hidden) when fields are empty
  await expect(form).toBeVisible();
  const success = page.locator('.form-success');
  await expect(success).not.toHaveClass(/visible/);
});

test('contact form shows success on valid submit', async ({ page }) => {
  await page.goto(BASE + 'contact/');
  await page.locator('#contact-name').fill('Test User');
  await page.locator('#contact-email').fill('test@example.com');
  await page.locator('#contact-subject').selectOption({ index: 1 });
  await page.locator('#contact-message').fill('Hello from Playwright test');
  await page.locator('#contact-form button[type="submit"]').click();
  await page.waitForTimeout(500);
  await expect(page.locator('.form-success')).toHaveClass(/visible/);
});

test('contact form rejects invalid email', async ({ page }) => {
  await page.goto(BASE + 'contact/');
  await page.locator('#contact-name').fill('Test User');
  await page.locator('#contact-email').fill('not-an-email');
  await page.locator('#contact-subject').selectOption({ index: 1 });
  await page.locator('#contact-message').fill('Testing bad email');
  await page.locator('#contact-form button[type="submit"]').click();
  // Form should still be visible — invalid email
  await expect(page.locator('#contact-form')).toBeVisible();
});

/* ══════════════════════════════════════════════
   Scroll Reveal
   ══════════════════════════════════════════════ */

test('reveal elements animate on scroll', async ({ page }) => {
  await page.goto(BASE);
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await page.waitForTimeout(800);
  const revealed = await page.locator('.reveal.visible').count();
  expect(revealed).toBeGreaterThanOrEqual(1);
});

/* ══════════════════════════════════════════════
   Mobile Responsive
   ══════════════════════════════════════════════ */

test('mobile nav toggle works', async ({ page, isMobile }) => {
  test.skip(!isMobile, 'Mobile-only test');
  await page.goto(BASE);
  const toggle = page.locator('.nav-toggle');
  await expect(toggle).toBeVisible();
  await toggle.click();
  const links = page.locator('.nav-links');
  await expect(links).toHaveClass(/open/);
});

/* ══════════════════════════════════════════════
   Collection Pages
   ══════════════════════════════════════════════ */

test('button magnets collection page loads', async ({ page }) => {
  await page.goto(BASE + 'collections/button-magnets/');
  await expect(page).toHaveTitle(/Button Magnets/i);
  await expect(page.locator('h1')).toContainText(/Button Magnets/i);
});

test('flexible magnets collection page loads', async ({ page }) => {
  await page.goto(BASE + 'collections/flexible-magnets/');
  await expect(page).toHaveTitle(/Flexible Magnets/i);
  await expect(page.locator('h1')).toContainText(/Flexible Magnets/i);
});

test('crochet toys collection page loads', async ({ page }) => {
  await page.goto(BASE + 'collections/crochet-toys/');
  await expect(page).toHaveTitle(/Crochet Toys/i);
  await expect(page.locator('h1')).toContainText(/Crochet/i);
});

test('pearl glass magnets collection page loads', async ({ page }) => {
  await page.goto(BASE + 'collections/pearl-glass-magnets/');
  await expect(page).toHaveTitle(/Pearl Glass/i);
  await expect(page.locator('h1')).toContainText(/Pearl.*Glass/i);
});

test('magnetic sheets collection page loads', async ({ page }) => {
  await page.goto(BASE + 'collections/magnetic-sheets/');
  await expect(page).toHaveTitle(/Magnetic Sheets/i);
  await expect(page.locator('h1')).toContainText(/Magnetic Sheet/i);
});

test('collection pages have breadcrumb navigation', async ({ page }) => {
  await page.goto(BASE + 'collections/button-magnets/');
  const breadcrumb = page.locator('.breadcrumbs');
  await expect(breadcrumb).toBeVisible();
  await expect(breadcrumb.locator('a')).toHaveCount(1); // Home link
});

test('collection pages have product cards', async ({ page }) => {
  await page.goto(BASE + 'collections/flexible-magnets/');
  const cards = page.locator('.product-card');
  const count = await cards.count();
  expect(count).toBeGreaterThanOrEqual(1);
});

/* ══════════════════════════════════════════════
   Product Pages
   ══════════════════════════════════════════════ */

test('product page loads with correct structure', async ({ page }) => {
  await page.goto(BASE + 'products/custom-photo-button-magnet/');
  await expect(page).toHaveTitle(/Custom Photo Button Magnet/i);
  await expect(page.locator('h1')).toContainText(/Custom Photo Button Magnet/i);
  await expect(page.locator('.product-detail__price')).toBeVisible();
});

test('product page has breadcrumb with category link', async ({ page }) => {
  await page.goto(BASE + 'products/custom-photo-button-magnet/');
  const breadcrumb = page.locator('.breadcrumbs');
  await expect(breadcrumb).toBeVisible();
  const links = breadcrumb.locator('a');
  const count = await links.count();
  expect(count).toBeGreaterThanOrEqual(2); // Home + Collection
});

test('product page has Schema.org Product JSON-LD', async ({ page }) => {
  await page.goto(BASE + 'products/custom-photo-button-magnet/');
  const jsonLd = await page.locator('script[type="application/ld+json"]').first().textContent();
  const data = JSON.parse(jsonLd);
  expect(data['@type']).toBe('Product');
  expect(data.offers).toBeDefined();
});

test('product page has features list', async ({ page }) => {
  await page.goto(BASE + 'products/custom-photo-button-magnet/');
  const features = page.locator('.product-detail__features li');
  const count = await features.count();
  expect(count).toBeGreaterThanOrEqual(3);
});

/* ══════════════════════════════════════════════
   FAQ Accordion
   ══════════════════════════════════════════════ */

test('FAQ accordion opens on click', async ({ page }) => {
  await page.goto(BASE + 'faq/');
  const firstItem = page.locator('.faq-item').first();
  await firstItem.locator('.faq-question').click();
  await expect(firstItem).toHaveClass(/open/);
});

test('Esc key closes open FAQ items', async ({ page }) => {
  await page.goto(BASE + 'faq/');
  const firstItem = page.locator('.faq-item').first();
  await firstItem.locator('.faq-question').click();
  await expect(firstItem).toHaveClass(/open/);
  await page.keyboard.press('Escape');
  await expect(firstItem).not.toHaveClass(/open/);
});

/* ══════════════════════════════════════════════
   Accessibility (Axe)
   ══════════════════════════════════════════════ */

test('homepage accessibility audit', async ({ page }) => {
  await page.goto(BASE);
  const results = await new AxeBuilder({ page })
    .disableRules(['color-contrast'])
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

test('collection page accessibility audit', async ({ page }) => {
  await page.goto(BASE + 'collections/button-magnets/');
  const results = await new AxeBuilder({ page })
    .disableRules(['color-contrast'])
    .analyze();
  const violations = results.violations.filter(v => v.impact === 'critical' || v.impact === 'serious');
  expect(violations).toEqual([]);
});

test('product page accessibility audit', async ({ page }) => {
  await page.goto(BASE + 'products/custom-photo-button-magnet/');
  const results = await new AxeBuilder({ page })
    .disableRules(['color-contrast'])
    .analyze();
  const violations = results.violations.filter(v => v.impact === 'critical' || v.impact === 'serious');
  expect(violations).toEqual([]);
});

/* ══════════════════════════════════════════════
   Layout Regression Tests
   ══════════════════════════════════════════════ */

test('nav fits single line at 1280px', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto(BASE);
  const navHeight = await page.locator('nav.nav').evaluate(el => el.offsetHeight);
  expect(navHeight).toBeLessThanOrEqual(80);
});

test('product grid fills container width', async ({ page }) => {
  await page.goto(BASE + 'collections/flexible-magnets/');
  const gridInfo = await page.locator('.product-grid').evaluate(el => ({
    scrollWidth: el.scrollWidth,
    offsetWidth: el.offsetWidth,
  }));
  // scrollWidth should not exceed offsetWidth significantly (no horizontal overflow)
  expect(gridInfo.scrollWidth).toBeLessThanOrEqual(gridInfo.offsetWidth + 2);
});

test('product grid has display grid', async ({ page }) => {
  await page.goto(BASE + 'collections/flexible-magnets/');
  const display = await page.locator('.product-grid').evaluate(el =>
    getComputedStyle(el).display
  );
  expect(display).toBe('grid');
});

test('dropdown menus become visible on hover', async ({ page, isMobile }) => {
  test.skip(isMobile, 'Desktop-only test');
  await page.goto(BASE);
  const dropdownTrigger = page.locator('.has-dropdown').first();
  await dropdownTrigger.hover();
  const dropdown = dropdownTrigger.locator('.nav-dropdown');
  await expect(dropdown).toBeVisible();
});

/* ══════════════════════════════════════════════
   Visual Spot-Check Tests
   ══════════════════════════════════════════════ */

test('homepage screenshot is non-blank', async ({ page }) => {
  await page.goto(BASE);
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await page.waitForTimeout(500);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(300);
  const screenshot = await page.screenshot({ fullPage: true, type: 'jpeg', quality: 80 });
  expect(screenshot.length).toBeGreaterThan(50000);
});

test('collection page screenshot is non-blank', async ({ page }) => {
  await page.goto(BASE + 'collections/button-magnets/');
  const screenshot = await page.screenshot({ fullPage: true, type: 'jpeg', quality: 80 });
  expect(screenshot.length).toBeGreaterThan(30000);
});

test('product page screenshot is non-blank', async ({ page }) => {
  await page.goto(BASE + 'products/custom-photo-button-magnet/');
  const screenshot = await page.screenshot({ fullPage: true, type: 'jpeg', quality: 80 });
  expect(screenshot.length).toBeGreaterThan(30000);
});

test('nav height consistent across pages', async ({ page }) => {
  const pages = [BASE, BASE + 'about/', BASE + 'contact/', BASE + 'collections/button-magnets/'];
  const heights = [];
  for (const url of pages) {
    await page.goto(url);
    const h = await page.locator('nav.nav').evaluate(el => el.offsetHeight);
    heights.push(h);
  }
  const maxDiff = Math.max(...heights) - Math.min(...heights);
  expect(maxDiff).toBeLessThanOrEqual(5);
});

/* ══════════════════════════════════════════════
   Identity Markers
   ══════════════════════════════════════════════ */

test('CSS fingerprint class present on main', async ({ page }) => {
  await page.goto(BASE);
  const main = page.locator('main.main-ajd-fp');
  await expect(main).toBeAttached();
  const fp = await main.getAttribute('data-fingerprint');
  expect(fp).toBeTruthy();
});

test('footer branding on all key pages', async ({ page }) => {
  const pages = [BASE, BASE + 'about/', BASE + 'contact/', BASE + 'faq/', BASE + 'collections/button-magnets/'];
  for (const url of pages) {
    await page.goto(url);
    await expect(page.locator('.footer-demo')).toContainText(/AjayaDesign/i);
  }
});

/* ══════════════════════════════════════════════
   Console Integrity
   ══════════════════════════════════════════════ */

test('no JavaScript console errors on homepage', async ({ page }) => {
  const errors = [];
  page.on('console', msg => {
    if (msg.type() === 'error' && !msg.text().includes('favicon')) {
      errors.push(msg.text());
    }
  });
  await page.goto(BASE);
  await page.waitForTimeout(1000);
  expect(errors).toEqual([]);
});

test('no 404 responses on homepage', async ({ page }) => {
  const notFound = [];
  page.on('response', response => {
    if (response.status() === 404 && !response.url().includes('favicon')) {
      notFound.push(response.url());
    }
  });
  await page.goto(BASE);
  await page.waitForTimeout(1000);
  expect(notFound).toEqual([]);
});
