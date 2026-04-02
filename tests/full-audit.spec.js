// @ts-check
const { test, expect } = require('@playwright/test');
const AxeBuilder = require('@axe-core/playwright').default;

/* ═══════ AjayaDesign-owned pages ONLY ═══════ */
const CORE_PAGES = [
  { path: '/', name: 'Homepage' },
  { path: '/about/', name: 'About' },
  { path: '/contact/', name: 'Contact' },
  { path: '/works/', name: 'Works' },
  { path: '/edge/', name: 'Edge' },
  { path: '/blog/', name: 'Blog' },
  { path: '/faq/', name: 'FAQ' },
  { path: '/case-studies/', name: 'Case Studies' },
  { path: '/404.html', name: '404' },
];

const PRINT_PAGES = [
  { path: '/3D-print/', name: '3D Print Home' },
  { path: '/3D-print/portal/', name: '3D Print Portal' },
  { path: '/3D-print/gallery/', name: '3D Print Gallery' },
  { path: '/3D-print/free/', name: '3D Print Free' },
  { path: '/3D-print/tiktok/', name: '3D Print TikTok' },
  { path: '/3D-print/referral/', name: '3D Print Referral' },
  { path: '/3D-print/tools/profit-calculator.html', name: '3D Print Profit Calc' },
  { path: '/3D-print/tools/etsy-optimizer.html', name: '3D Print Etsy Tool' },
  { path: '/3D-print/tools/calculator.html', name: '3D Print Calculator' },
  { path: '/3D-print/tools/checklist.html', name: '3D Print Checklist' },
  { path: '/3D-print/tools/materials.html', name: '3D Print Materials' },
  { path: '/3D-print/blog/', name: '3D Print Blog' },
  { path: '/3D-print/promo.html', name: '3D Print Promo' },
  { path: '/3D-print/roadmap.html', name: '3D Print Roadmap' },
];

const ALL_PAGES = [...CORE_PAGES, ...PRINT_PAGES];

/* ═══════ Horizontal Overflow — Desktop ═══════ */
test.describe('Horizontal Overflow — Desktop (1280x800)', () => {
  test.use({ viewport: { width: 1280, height: 800 } });
  for (const pg of ALL_PAGES) {
    test(`${pg.name} — no horizontal overflow`, async ({ page }) => {
      await page.goto(pg.path, { waitUntil: 'domcontentloaded' });
      const overflow = await page.evaluate(() =>
        document.documentElement.scrollWidth > document.documentElement.clientWidth
      );
      expect(overflow, `${pg.name} has horizontal overflow on desktop`).toBe(false);
    });
  }
});

/* ═══════ Horizontal Overflow — Mobile ═══════ */
test.describe('Horizontal Overflow — Mobile (375x812)', () => {
  test.use({ viewport: { width: 375, height: 812 } });
  for (const pg of ALL_PAGES) {
    test(`${pg.name} — no horizontal overflow on mobile`, async ({ page }) => {
      await page.goto(pg.path, { waitUntil: 'domcontentloaded' });
      const overflow = await page.evaluate(() =>
        document.documentElement.scrollWidth > document.documentElement.clientWidth
      );
      expect(overflow, `${pg.name} has horizontal overflow on mobile`).toBe(false);
    });
  }
});

/* ═══════ Axe A11y — Critical/Serious ═══════ */
test.describe('Accessibility — axe-core critical/serious', () => {
  for (const pg of ALL_PAGES) {
    test(`${pg.name} — no critical a11y violations`, async ({ page, browserName }) => {
      test.skip(browserName === 'webkit', 'axe-core not reliable on webkit');
      await page.goto(pg.path, { waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(1000);
      const results = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa'])
        .analyze();
      const critical = results.violations.filter(v => v.impact === 'critical' || v.impact === 'serious');
      if (critical.length > 0) {
        const summary = critical.map(v =>
          `[${v.impact}] ${v.id}: ${v.description} (${v.nodes.length} nodes)\n` +
          v.nodes.slice(0, 3).map(n => `  → ${n.html.slice(0, 120)}`).join('\n')
        ).join('\n\n');
        console.log(`\n⚠️ ${pg.name} a11y:\n${summary}\n`);
      }
      expect(critical, `${pg.name} has critical/serious a11y violations`).toHaveLength(0);
    });
  }
});

/* ═══════ 3D-Print Mobile — Specific checks ═══════ */
test.describe('3D Print — Mobile specific', () => {
  test.use({ viewport: { width: 375, height: 812 } });

  test('pricing cards stack to single column on mobile', async ({ page }) => {
    await page.goto('/3D-print/', { waitUntil: 'domcontentloaded' });
    const cards = page.locator('#enroll .grid > div, #enroll .grid > a').first();
    if (await cards.count() > 0) {
      const box = await cards.boundingBox();
      expect(box).toBeTruthy();
      // Card should be nearly full width on mobile (minus padding)
      expect(box.width).toBeGreaterThan(300);
    }
  });

  test('comparison table does not overflow viewport', async ({ page }) => {
    await page.goto('/3D-print/', { waitUntil: 'domcontentloaded' });
    // The table section has overflow-x-auto which is acceptable
    const overflow = await page.evaluate(() =>
      document.documentElement.scrollWidth > document.documentElement.clientWidth
    );
    expect(overflow).toBe(false);
  });

  test('hero floating cards do not overflow on mobile', async ({ page }) => {
    await page.goto('/3D-print/', { waitUntil: 'domcontentloaded' });
    // Check that no elements are positioned outside the viewport
    const overflowElements = await page.evaluate(() => {
      const els = document.querySelectorAll('[class*="absolute"]');
      const vw = document.documentElement.clientWidth;
      let overflow = [];
      els.forEach(el => {
        const rect = el.getBoundingClientRect();
        if (rect.right > vw + 20 || rect.left < -20) {
          overflow.push(`${el.className.slice(0, 50)}... (left:${rect.left.toFixed(0)}, right:${rect.right.toFixed(0)})`);
        }
      });
      return overflow;
    });
    if (overflowElements.length > 0) {
      console.log('Overflow elements:', overflowElements);
    }
    // Allow up to a few decorative elements outside viewport
    expect(overflowElements.length).toBeLessThan(10);
  });

  test('mobile hamburger menu works on 3D-print page', async ({ page }) => {
    await page.goto('/3D-print/', { waitUntil: 'domcontentloaded' });
    const hamburger = page.locator('#mobile-menu-btn');
    await expect(hamburger).toBeVisible();
    await hamburger.click({ force: true });
    const mobileMenu = page.locator('#mobile-menu');
    await expect(mobileMenu).toBeVisible({ timeout: 3000 });
  });

  test('footer links do not overflow on mobile', async ({ page }) => {
    await page.goto('/3D-print/', { waitUntil: 'domcontentloaded' });
    const footer = page.locator('footer');
    const box = await footer.boundingBox();
    expect(box).toBeTruthy();
    // Footer should fit within viewport width
    expect(box.x + box.width).toBeLessThanOrEqual(375 + 5);
  });

  test('chatbot button is accessible on mobile', async ({ page }) => {
    await page.goto('/3D-print/', { waitUntil: 'domcontentloaded' });
    const chatBtn = page.locator('#faq-toggle');
    if (await chatBtn.count() > 0) {
      await expect(chatBtn).toBeVisible();
      const box = await chatBtn.boundingBox();
      // Touch target should be at least 44x44
      expect(box.width).toBeGreaterThanOrEqual(44);
      expect(box.height).toBeGreaterThanOrEqual(44);
    }
  });
});
