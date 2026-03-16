// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * All pages to test — path relative to baseURL, plus a label.
 */
const PAGES = [
  { path: './', label: 'Home' },
  { path: './shop/', label: 'Shop' },
  { path: './events/', label: 'Weddings & Events' },
  { path: './about/', label: 'About' },
  { path: './faq/', label: 'FAQ' },
  { path: './contact/', label: 'Contact' },
];

/* ── Smoke: every page loads with 200 ─────────────────────── */
for (const { path, label } of PAGES) {
  test(`${label} page loads successfully`, async ({ page }) => {
    const resp = await page.goto(path);
    expect(resp.status()).toBe(200);
  });
}

/* ── Core structure present on every page ─────────────────── */
for (const { path, label } of PAGES) {
  test(`${label} has header, nav, main, footer`, async ({ page }) => {
    await page.goto(path);
    await expect(page.locator('header.header')).toBeVisible();
    await expect(page.locator('nav[aria-label="Primary"]')).toBeAttached();
    await expect(page.locator('main#main')).toBeAttached();
    await expect(page.locator('footer.footer')).toBeVisible();
  });
}

/* ── Navigation links present ─────────────────────────────── */
test('header contains all 6 navigation links', async ({ page }) => {
  await page.goto('./');
  const links = page.locator('.header__nav-list .header__nav-link');
  await expect(links).toHaveCount(6);
  const texts = await links.allTextContents();
  expect(texts).toEqual(
    expect.arrayContaining(['Home', 'Shop', 'Weddings & Events', 'About', 'FAQ', 'Contact'])
  );
});

/* ── Home page hero section ───────────────────────────────── */
test('Home hero has headline and CTAs', async ({ page }) => {
  await page.goto('./');
  await expect(page.locator('.hero__title')).toBeVisible();
  const ctas = page.locator('.hero__ctas a, .hero__ctas button');
  expect(await ctas.count()).toBeGreaterThanOrEqual(1);
});

/* ── Meta tags (SEO basics) ───────────────────────────────── */
for (const { path, label } of PAGES) {
  test(`${label} has title and meta description`, async ({ page }) => {
    await page.goto(path);
    const title = await page.title();
    expect(title.length).toBeGreaterThan(10);
    const desc = page.locator('meta[name="description"]');
    await expect(desc).toHaveAttribute('content', /.{20,}/);
  });
}

/* ── Cart drawer exists and is hidden ─────────────────────── */
test('cart drawer exists but is not visible on load', async ({ page }) => {
  await page.goto('./');
  const drawer = page.locator('.cart-drawer');
  await expect(drawer).toBeAttached();
  // Drawer should be off-screen (translateX(100%))
  const transform = await drawer.evaluate(el => getComputedStyle(el).transform);
  expect(transform).not.toBe('none');
});

/* ── Cart button opens drawer ─────────────────────────────── */
test('clicking cart button opens the cart drawer', async ({ page }) => {
  await page.goto('./');
  await page.click('.header__cart-btn');
  const drawer = page.locator('.cart-drawer');
  await expect(drawer).toHaveClass(/open/);
});

/* ── 404 page ─────────────────────────────────────────────── */
test('404 page renders for unknown routes', async ({ page }) => {
  const resp = await page.goto('./nonexistent-page-xyz/');
  expect(resp.status()).toBe(404);
});

/* ── No console errors on home page ───────────────────────── */
test('no JavaScript console errors on home page', async ({ page }) => {
  const errors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') errors.push(msg.text());
  });
  await page.goto('./');
  await page.waitForTimeout(2000);
  // Filter out known external resource errors (Shopify CDN, fonts)
  const realErrors = errors.filter(
    e => !e.includes('net::') && !e.includes('Failed to load resource')
  );
  expect(realErrors).toHaveLength(0);
});

/* ── Images have alt text ─────────────────────────────────── */
test('all images have alt attributes', async ({ page }) => {
  await page.goto('./');
  const images = page.locator('img');
  const count = await images.count();
  for (let i = 0; i < count; i++) {
    const alt = await images.nth(i).getAttribute('alt');
    expect(alt, `Image #${i} is missing alt text`).not.toBeNull();
  }
});

/* ── Links are not broken (same-origin only) ──────────────── */
test('internal links return 200', async ({ page, baseURL }) => {
  await page.goto('./');
  const hrefs = await page.locator('a[href^="/works/ecommerce/the-magnet-guy"]').evaluateAll(
    els => els.map(a => a.getAttribute('href'))
  );
  const unique = [...new Set(hrefs)];
  const broken = [];
  for (const href of unique) {
    const url = new URL(href, baseURL).href;
    const resp = await page.request.get(url);
    if (resp.status() !== 200) broken.push(href);
  }
  expect(broken, `Broken links: ${broken.join(', ')}`).toHaveLength(0);
});

/* ── Shop page has product grid ───────────────────────────── */
test('Shop page has product grid container', async ({ page }) => {
  await page.goto('./shop/');
  await expect(page.locator('#product-grid')).toBeAttached();
});

/* ── FAQ page has questions ───────────────────────────────── */
test('FAQ page has at least 3 FAQ items', async ({ page }) => {
  await page.goto('./faq/');
  const items = page.locator('.faq-item, .faq__item, details, [class*="accordion"]');
  expect(await items.count()).toBeGreaterThanOrEqual(3);
});
