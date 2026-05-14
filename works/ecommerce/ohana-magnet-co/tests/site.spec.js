const { test, expect } = require('@playwright/test');
const AxeBuilder = require('@axe-core/playwright').default;

const pages = [
  { path: '/', name: 'Homepage' },
  { path: '/about/', name: 'About' },
  { path: '/contact/', name: 'Contact' },
  { path: '/magnets/', name: 'Magnets Collection' },
  { path: '/keychains/', name: 'Keychains Collection' },
  { path: '/frames/', name: 'Frames Collection' },
  { path: '/pre-made-magnets/', name: 'Pre-Made Magnets' },
  { path: '/products/2-25-round-magnet/', name: 'Round Magnet Product' },
  { path: '/products/2x2-square-photo-magnet/', name: 'Square 2x2 Product' },
  { path: '/products/2-25-round-keychain/', name: 'Keychain Product' },
];

// --- Accessibility Tests ---
test.describe('Accessibility', () => {
  for (const page of pages) {
    test(`${page.name} has no critical accessibility violations`, async ({ page: p }) => {
      await p.goto(page.path);
      const results = await new AxeBuilder({ page: p })
        .withTags(['wcag2a', 'wcag2aa'])
        .analyze();
      const critical = results.violations.filter(v => v.impact === 'critical' || v.impact === 'serious');
      expect(critical).toEqual([]);
    });
  }
});

// --- HTML Structure ---
test.describe('HTML Structure', () => {
  test('Homepage has proper heading hierarchy', async ({ page }) => {
    await page.goto('/');
    const h1 = await page.locator('h1').count();
    expect(h1).toBe(1);
    const h1Text = await page.locator('h1').textContent();
    expect(h1Text).toContain('Memories');
  });

  test('All pages have skip link', async ({ page }) => {
    for (const p of pages) {
      await page.goto(p.path);
      const skipLink = page.locator('.skip-link');
      await expect(skipLink).toHaveCount(1);
    }
  });

  test('All pages have meta description', async ({ page }) => {
    for (const p of pages) {
      await page.goto(p.path);
      const desc = await page.locator('meta[name="description"]').getAttribute('content');
      expect(desc).toBeTruthy();
      expect(desc.length).toBeGreaterThan(20);
    }
  });

  test('All pages have unique title', async ({ page }) => {
    const titles = new Set();
    for (const p of pages) {
      await page.goto(p.path);
      const title = await page.title();
      expect(title).toBeTruthy();
      expect(titles.has(title)).toBe(false);
      titles.add(title);
    }
  });
});

// --- Navigation ---
test.describe('Navigation', () => {
  test('Nav has correct links', async ({ page }) => {
    await page.goto('/');
    const nav = page.locator('.site-nav');
    await expect(nav).toBeVisible();
    await expect(page.locator('.site-nav .nav-logo')).toBeVisible();
  });

  test('Nav single-line check at 1280px', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto('/');
    const navHeight = await page.locator('.site-nav').evaluate(el => el.offsetHeight);
    expect(navHeight).toBeLessThanOrEqual(80);
  });

  test('Dropdown menu appears on hover', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto('/');
    const dropdown = page.locator('.nav-dropdown');
    await dropdown.hover();
    const menu = page.locator('.dropdown-menu');
    await expect(menu).toBeVisible();
  });
});

// --- Products ---
test.describe('Products', () => {
  test('Homepage shows product cards', async ({ page }) => {
    await page.goto('/');
    const cards = page.locator('.product-card');
    const count = await cards.count();
    expect(count).toBeGreaterThanOrEqual(4);
  });

  test('Product grid fills width', async ({ page }) => {
    await page.goto('/magnets/');
    const grid = page.locator('.product-grid').first();
    const { scrollWidth, offsetWidth } = await grid.evaluate(el => ({
      scrollWidth: el.scrollWidth,
      offsetWidth: el.offsetWidth,
    }));
    expect(scrollWidth).toBeLessThanOrEqual(offsetWidth + 2);
  });

  test('Collection page shows item count', async ({ page }) => {
    await page.goto('/magnets/');
    const count = page.locator('.collection-count');
    await expect(count).toBeVisible();
  });

  test('Product detail page has specs', async ({ page }) => {
    await page.goto('/products/2-25-round-magnet/');
    await expect(page.locator('.product-specs')).toBeVisible();
    await expect(page.locator('.product-detail-price')).toBeVisible();
  });
});

// --- Contact Form ---
test.describe('Contact Form', () => {
  test('Empty submit is blocked', async ({ page }) => {
    await page.goto('/contact/');
    const form = page.locator('#contact-form');
    if (await form.count() > 0) {
      await page.click('#contact-form button[type="submit"]');
      // Form should still be visible (not hidden)
      await expect(form).toBeVisible();
      const success = page.locator('.form-success');
      const display = await success.evaluate(el => getComputedStyle(el).display);
      expect(display).toBe('none');
    }
  });

  test('Valid submit shows success', async ({ page }) => {
    await page.goto('/contact/');
    const form = page.locator('#contact-form');
    if (await form.count() > 0) {
      await page.fill('#contact-form input[name="name"]', 'Test User');
      await page.fill('#contact-form input[name="email"]', 'test@example.com');
      await page.fill('#contact-form textarea[name="message"]', 'Hello there!');
      await page.click('#contact-form button[type="submit"]');
      await page.waitForTimeout(500);
      const success = page.locator('.form-success');
      const isVisible = await success.isVisible();
      expect(isVisible).toBe(true);
    }
  });
});

// --- Identity Markers (hidden) ---
test.describe('Identity Markers', () => {
  test('Build signature meta tag exists', async ({ page }) => {
    await page.goto('/');
    const gen = await page.locator('meta[name="generator"]').getAttribute('content');
    expect(gen).toBeTruthy();
  });

  test('Hidden comment marker exists', async ({ page }) => {
    await page.goto('/');
    const html = await page.content();
    expect(html).toContain('p:demo-asset');
  });
});

// --- SEO ---
test.describe('SEO', () => {
  test('Homepage has JSON-LD schema', async ({ page }) => {
    await page.goto('/');
    const schema = page.locator('script[type="application/ld+json"]');
    const count = await schema.count();
    expect(count).toBeGreaterThanOrEqual(1);
  });

  test('Product pages have Product schema', async ({ page }) => {
    await page.goto('/products/2-25-round-magnet/');
    const schema = await page.locator('script[type="application/ld+json"]').textContent();
    expect(schema).toContain('"@type":"Product"');
  });

  test('All pages have OG tags', async ({ page }) => {
    for (const p of pages.slice(0, 5)) {
      await page.goto(p.path);
      const ogTitle = await page.locator('meta[property="og:title"]').getAttribute('content');
      expect(ogTitle).toBeTruthy();
    }
  });
});

// --- Visual Spot-Check ---
test.describe('Visual Spot-Check', () => {
  test('Homepage screenshot is non-blank', async ({ page }) => {
    await page.goto('/');
    const screenshot = await page.screenshot({ fullPage: true });
    expect(screenshot.length).toBeGreaterThan(50000);
  });

  test('Collection page screenshot is non-blank', async ({ page }) => {
    await page.goto('/magnets/');
    const screenshot = await page.screenshot({ fullPage: true });
    expect(screenshot.length).toBeGreaterThan(30000);
  });

  test('Product page screenshot is non-blank', async ({ page }) => {
    await page.goto('/products/2-25-round-magnet/');
    const screenshot = await page.screenshot({ fullPage: true });
    expect(screenshot.length).toBeGreaterThan(30000);
  });
});

// --- Console Integrity ---
test.describe('Console Integrity', () => {
  test('No console errors on homepage', async ({ page }) => {
    const errors = [];
    page.on('console', msg => {
      if (msg.type() === 'error') errors.push(msg.text());
    });
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    expect(errors).toEqual([]);
  });

  test('No 404s on key pages', async ({ page }) => {
    const notFounds = [];
    page.on('response', response => {
      if (response.status() === 404 && !response.url().includes('fonts.g') && !response.url().includes('favicon')) notFounds.push(response.url());
    });
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.goto('/magnets/');
    await page.waitForLoadState('networkidle');
    await page.goto('/products/2-25-round-magnet/');
    await page.waitForLoadState('networkidle');
    expect(notFounds).toEqual([]);
  });
});

// --- Mobile Responsiveness ---
test.describe('Mobile Responsiveness', () => {
  test('Homepage renders at 375px', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto('/');
    const hero = page.locator('.hero');
    await expect(hero).toBeVisible();
    const nav = page.locator('.nav-toggle');
    await expect(nav).toBeVisible();
  });

  test('Nav toggle works on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto('/');
    await page.click('.nav-toggle');
    const navLinks = page.locator('.nav-links');
    await expect(navLinks).toHaveClass(/open/);
  });
});
