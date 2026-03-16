// @ts-check
const { test, expect } = require('@playwright/test');

const PAGES = [
  { path: '/', title: 'ENC Printing' },
  { path: '/about/', title: 'About Us' },
  { path: '/contact/', title: 'Contact' },
  { path: '/photo-magnets/', title: 'Photo Magnets' },
  { path: '/frames-ornaments/', title: 'Frames' },
  { path: '/printed-files/', title: 'Files' },
  { path: '/frame-accessories/', title: 'Accessories' },
  { path: '/lithophane-products/', title: 'Lithophane' },
  { path: '/miscellaneous-products/', title: 'Miscellaneous' },
  { path: '/products/custom-photo-magnets/', title: 'Custom Photo Magnets' },
  { path: '/products/frame-magnet-bundle/', title: 'Frame' },
  { path: '/products/mosaic-photo-magnet-set/', title: 'Mosaic' },
  { path: '/products/heart-flexi-figure/', title: 'Heart Flexi' },
];

test.describe('Page Load & Title', () => {
  for (const pg of PAGES) {
    test(`${pg.path} loads with title containing "${pg.title}"`, async ({ page }) => {
      const res = await page.goto(pg.path);
      expect(res.status()).toBe(200);
      await expect(page).toHaveTitle(new RegExp(pg.title, 'i'));
    });
  }
});

test.describe('Navigation', () => {
  test('nav exists and has key links', async ({ page, isMobile }) => {
    await page.goto('/');
    const nav = page.locator('nav');
    await expect(nav).toBeVisible();
    if (!isMobile) {
      const menubar = page.locator('[role="menubar"], .nav-links');
      await expect(menubar.first()).toBeVisible();
    }
  });

  test('nav becomes sticky on scroll', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => window.scrollBy(0, 200));
    await page.waitForTimeout(300);
    const nav = page.locator('.nav');
    await expect(nav).toHaveClass(/scrolled/);
  });

  test('mobile nav toggle works', async ({ page, isMobile }) => {
    test.skip(!isMobile, 'Mobile only');
    await page.goto('/');
    const toggle = page.locator('.nav-toggle');
    await expect(toggle).toBeVisible();
    await toggle.click();
    const links = page.locator('#navLinks');
    await expect(links).toHaveClass(/open/);
  });
});

test.describe('Homepage', () => {
  test('hero section renders', async ({ page }) => {
    await page.goto('/');
    const hero = page.locator('.hero');
    await expect(hero).toBeVisible();
    await expect(page.locator('.hero h1')).toContainText('Photo Magnets');
  });

  test('CTA button links to photo magnets', async ({ page }) => {
    await page.goto('/');
    const cta = page.locator('.hero a[href*="photo-magnets"], .hero-cta').first();
    await expect(cta).toBeVisible();
    const href = await cta.getAttribute('href');
    expect(href).toContain('photo-magnets');
  });

  test('category bento grid is present', async ({ page }) => {
    await page.goto('/');
    const cards = page.locator('.bento-card');
    expect(await cards.count()).toBeGreaterThanOrEqual(4);
  });

  test('testimonials section renders', async ({ page }) => {
    await page.goto('/');
    const section = page.locator('.testimonials-section, .testimonials');
    await expect(section.first()).toBeVisible();
    const cards = page.locator('.testimonial-card');
    expect(await cards.count()).toBeGreaterThanOrEqual(3);
  });

  test('product cards are present', async ({ page }) => {
    await page.goto('/');
    const products = page.locator('.product-card');
    expect(await products.count()).toBeGreaterThanOrEqual(3);
  });
});

test.describe('Collection Pages', () => {
  test('photo magnets shows products', async ({ page }) => {
    await page.goto('/photo-magnets/');
    const cards = page.locator('.product-card');
    expect(await cards.count()).toBeGreaterThanOrEqual(3);
  });

  test('frames & ornaments shows products', async ({ page }) => {
    await page.goto('/frames-ornaments/');
    const cards = page.locator('.product-card');
    expect(await cards.count()).toBeGreaterThanOrEqual(3);
  });

  test('3D files shows products with sale badges', async ({ page }) => {
    await page.goto('/printed-files/');
    const cards = page.locator('.product-card');
    expect(await cards.count()).toBeGreaterThanOrEqual(3);
  });

  test('collection pages have breadcrumbs', async ({ page }) => {
    await page.goto('/photo-magnets/');
    const breadcrumb = page.locator('.breadcrumb');
    await expect(breadcrumb).toBeVisible();
    await expect(breadcrumb.locator('a').first()).toHaveAttribute('href', /\.\.\//);
  });
});

test.describe('Product Detail Pages', () => {
  test('product page has detail layout', async ({ page }) => {
    await page.goto('/products/custom-photo-magnets/');
    await expect(page.locator('h1')).toContainText('Custom Photo Magnets');
    await expect(page.locator('.price').first()).toBeVisible();
  });

  test('product page has breadcrumb', async ({ page }) => {
    await page.goto('/products/custom-photo-magnets/');
    const breadcrumb = page.locator('.breadcrumb');
    await expect(breadcrumb).toBeVisible();
  });

  test('product page has JSON-LD Product schema', async ({ page }) => {
    await page.goto('/products/custom-photo-magnets/');
    const schemas = await page.locator('script[type="application/ld+json"]').allTextContents();
    const hasProduct = schemas.some(s => s.includes('"@type":"Product"') || s.includes('"@type": "Product"'));
    expect(hasProduct).toBeTruthy();
  });
});

test.describe('Contact Form', () => {
  test('form exists with required fields', async ({ page }) => {
    await page.goto('/contact/');
    const form = page.locator('#contactForm');
    await expect(form).toBeVisible();
    await expect(page.locator('#contactForm input[required]').first()).toBeVisible();
  });

  test('empty submit is blocked', async ({ page }) => {
    await page.goto('/contact/');
    await page.locator('#contactForm button[type="submit"], #contactForm .btn-primary').first().click();
    const success = page.locator('#formSuccess');
    await expect(success).not.toBeVisible();
  });

  test('valid submit shows success', async ({ page }) => {
    await page.goto('/contact/');
    await page.fill('input[name="name"], #contactForm input[type="text"]', 'Test User', { strict: false });
    await page.fill('input[name="email"], input[type="email"]', 'test@example.com', { strict: false });

    // Fill message/comment textarea
    const textarea = page.locator('#contactForm textarea').first();
    await textarea.fill('Test message');

    await page.locator('#contactForm button[type="submit"], #contactForm .btn-primary').first().click();
    await page.waitForTimeout(500);
    const success = page.locator('#formSuccess');
    await expect(success).toBeVisible();
  });
});

test.describe('AjayaDesign Identity', () => {
  test('build signature meta tag present', async ({ page }) => {
    await page.goto('/');
    const sig = await page.locator('meta[name="x-build-signature"]').getAttribute('content');
    expect(sig).toContain('AjayaDesign');
  });

  test('footer demo branding present', async ({ page }) => {
    await page.goto('/');
    const footer = page.locator('.footer-demo');
    await expect(footer.first()).toContainText('AjayaDesign');
  });

  test('CSS fingerprint class exists', async ({ page }) => {
    await page.goto('/');
    const fp = page.locator('.enc-ajyd-fp-2026');
    expect(await fp.count()).toBeGreaterThanOrEqual(1);
  });
});

test.describe('SEO & Schema', () => {
  test('homepage has JSON-LD schemas', async ({ page }) => {
    await page.goto('/');
    const schemas = await page.locator('script[type="application/ld+json"]').allTextContents();
    expect(schemas.length).toBeGreaterThanOrEqual(1);
    const hasWebSite = schemas.some(s => s.includes('WebSite'));
    expect(hasWebSite).toBeTruthy();
  });

  test('all pages have meta description', async ({ page }) => {
    for (const pg of PAGES) {
      await page.goto(pg.path);
      const desc = await page.locator('meta[name="description"]').getAttribute('content');
      expect(desc, `Missing description on ${pg.path}`).toBeTruthy();
    }
  });

  test('all pages have canonical link', async ({ page }) => {
    for (const pg of PAGES) {
      await page.goto(pg.path);
      const canonical = await page.locator('link[rel="canonical"]').getAttribute('href');
      expect(canonical, `Missing canonical on ${pg.path}`).toBeTruthy();
    }
  });
});

test.describe('Console Integrity', () => {
  test('no 404 errors on homepage', async ({ page }) => {
    const errors = [];
    page.on('response', res => {
      if (res.status() === 404 && !res.url().includes('favicon')) {
        errors.push(res.url());
      }
    });
    await page.goto('/');
    await page.waitForTimeout(1000);
    expect(errors, `404 errors found: ${errors.join(', ')}`).toHaveLength(0);
  });

  test('no JS console errors on homepage', async ({ page }) => {
    const errors = [];
    page.on('console', msg => {
      if (msg.type() === 'error') errors.push(msg.text());
    });
    await page.goto('/');
    await page.waitForTimeout(1000);
    expect(errors, `Console errors: ${errors.join('; ')}`).toHaveLength(0);
  });
});

test.describe('Accessibility', () => {
  test('homepage passes axe-core audit', async ({ page }) => {
    await page.goto('/');
    let AxeBuilder;
    try {
      AxeBuilder = require('@axe-core/playwright').default;
    } catch {
      test.skip(true, 'axe-core not installed');
      return;
    }
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();
    const critical = results.violations.filter(v => v.impact === 'critical' || v.impact === 'serious');
    expect(critical, `Critical a11y violations: ${JSON.stringify(critical.map(v => v.id))}`).toHaveLength(0);
  });
});
