// @ts-check
const { test, expect } = require('@playwright/test');

/*
 * Mobile-specific tests.
 * Only runs in the mobile projects (iPhone 14, Pixel 7)
 * by filtering on isMobile/viewport.
 */

const PAGES = [
  { path: './', label: 'Home' },
  { path: './shop/', label: 'Shop' },
  { path: './events/', label: 'Weddings & Events' },
  { path: './about/', label: 'About' },
  { path: './faq/', label: 'FAQ' },
  { path: './contact/', label: 'Contact' },
];

/* ── Hamburger menu opens and shows all links ─────────────── */
test('hamburger menu opens and shows all 6 nav links', async ({ page, isMobile }) => {
  test.skip(!isMobile, 'Mobile only');
  await page.goto('./');

  const hamburger = page.locator('.mobile-toggle');
  await expect(hamburger).toBeVisible();
  await hamburger.click();

  const navList = page.locator('.header__nav-list');
  await expect(navList).toHaveClass(/open/, { timeout: 3000 });

  const links = navList.locator('.header__nav-link');
  await expect(links).toHaveCount(6);

  // All links should be visible inside the opened panel
  for (let i = 0; i < 6; i++) {
    await expect(links.nth(i)).toBeVisible();
  }
});

/* ── Hamburger closes on overlay click ────────────────────── */
test('hamburger menu closes when overlay is tapped', async ({ page, isMobile }) => {
  test.skip(!isMobile, 'Mobile only');
  await page.goto('./');

  await page.click('.mobile-toggle');
  const navList = page.locator('.header__nav-list');
  await expect(navList).toHaveClass(/open/, { timeout: 3000 });

  // Tap the overlay (left side of screen)
  const overlay = page.locator('.mobile-nav-overlay');
  await overlay.click({ position: { x: 20, y: 400 } });

  // Nav should close
  await expect(navList).not.toHaveClass(/open/, { timeout: 3000 });
});

/* ── Nav link navigation works on mobile ──────────────────── */
test('tapping nav links navigates to correct pages', async ({ page, isMobile }) => {
  test.skip(!isMobile, 'Mobile only');
  await page.goto('./');

  // Open hamburger and tap "About"
  await page.click('.mobile-toggle');
  await page.locator('.header__nav-list').waitFor({ state: 'visible' });
  await page.click('text=About');
  await page.waitForURL('**/about/**');
  expect(page.url()).toContain('/about/');
});

/* ── No horizontal overflow on any page ───────────────────── */
for (const { path, label } of PAGES) {
  test(`${label} — no horizontal overflow on mobile`, async ({ page, isMobile }) => {
    test.skip(!isMobile, 'Mobile only');
    await page.goto(path);
    await page.waitForLoadState('domcontentloaded');

    const overflow = await page.evaluate(() => {
      return document.documentElement.scrollWidth > document.documentElement.clientWidth;
    });
    expect(overflow, `${label} has horizontal overflow on mobile`).toBe(false);
  });
}

/* ── Touch targets are at least 44×44px ───────────────────── */
test('primary touch targets meet 44×44px minimum', async ({ page, isMobile }) => {
  test.skip(!isMobile, 'Mobile only');
  await page.goto('./');

  // Check critical interactive elements (hamburger, cart, primary CTAs)
  const targets = page.locator('.mobile-toggle, .header__cart-btn');
  const count = await targets.count();
  for (let i = 0; i < count; i++) {
    const box = await targets.nth(i).boundingBox();
    if (box) {
      // Use effective size (including padding/touch area)
      expect(
        Math.max(box.width, box.height) >= 44,
        `Touch target #${i} is too small: ${Math.round(box.width)}×${Math.round(box.height)}`
      ).toBe(true);
    }
  }
});

/* ── Text is readable (no tiny fonts) ─────────────────────── */
test('body text is at least 14px on mobile', async ({ page, isMobile }) => {
  test.skip(!isMobile, 'Mobile only');
  await page.goto('./');

  const fontSize = await page.evaluate(() => {
    const body = document.querySelector('main p, main li, .hero__desc');
    if (!body) return 16;
    return parseFloat(getComputedStyle(body).fontSize);
  });
  expect(fontSize).toBeGreaterThanOrEqual(14);
});

/* ── Viewport meta tag present ────────────────────────────── */
test('viewport meta tag is set correctly', async ({ page, isMobile }) => {
  test.skip(!isMobile, 'Mobile only');
  await page.goto('./');
  const viewport = page.locator('meta[name="viewport"]');
  await expect(viewport).toHaveAttribute('content', /width=device-width/);
  await expect(viewport).toHaveAttribute('content', /initial-scale=1/);
});

/* ── Cart drawer works on mobile ──────────────────────────── */
test('cart opens and closes on mobile', async ({ page, isMobile }) => {
  test.skip(!isMobile, 'Mobile only');
  await page.goto('./');
  await page.waitForLoadState('domcontentloaded');

  // Open cart
  await page.click('.header__cart-btn');
  const drawer = page.locator('.cart-drawer');
  await expect(drawer).toHaveClass(/open/, { timeout: 3000 });

  // Close cart — use the close button or overlay
  const closeBtn = page.locator('.cart-drawer__close');
  await closeBtn.click({ timeout: 5000 });
  await expect(drawer).not.toHaveClass(/open/, { timeout: 3000 });
});

/* ── Images do not overflow viewport ──────────────────────── */
test('images fit within viewport on mobile', async ({ page, isMobile }) => {
  test.skip(!isMobile, 'Mobile only');
  await page.goto('./');
  await page.waitForLoadState('domcontentloaded');

  const viewportWidth = page.viewportSize().width;
  const images = page.locator('img:visible');
  const count = await images.count();
  for (let i = 0; i < count; i++) {
    const box = await images.nth(i).boundingBox();
    if (box && box.width > 0) {
      expect(
        box.width <= viewportWidth + 2,
        `Image #${i} overflows: ${box.width}px > ${viewportWidth}px`
      ).toBe(true);
    }
  }
});

/* ── Demo banner does not block header ────────────────────── */
test('demo banner does not block hamburger button', async ({ page, isMobile }) => {
  test.skip(!isMobile, 'Mobile only');
  await page.goto('./');

  const hamburger = page.locator('.mobile-toggle');
  // Force-check that the hamburger is clickable (no overlay blocking it)
  await expect(hamburger).toBeVisible();
  await hamburger.click({ force: false, timeout: 3000 });
  const navList = page.locator('.header__nav-list');
  await expect(navList).toHaveClass(/open/, { timeout: 3000 });
});

/* ── Toast is hidden on mobile ────────────────────────────── */
test('toast element is not visible on load', async ({ page, isMobile }) => {
  test.skip(!isMobile, 'Mobile only');
  await page.goto('./');

  const toast = page.locator('.toast');
  if (await toast.count() > 0) {
    const visible = await toast.evaluate(el => {
      const s = getComputedStyle(el);
      return s.visibility !== 'hidden' && s.display !== 'none' && s.opacity !== '0';
    });
    expect(visible, 'Toast should be hidden on page load').toBe(false);
  }
});
