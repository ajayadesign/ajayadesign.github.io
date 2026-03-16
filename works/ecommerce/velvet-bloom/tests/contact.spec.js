const { test, expect } = require('@playwright/test');
const AxeBuilder = require('@axe-core/playwright').default;

test.describe('Contact Us page (contact)', () => {
  test('loads and has content', async ({ page }) => {
    await page.goto('/contact.html');
    await expect(page.locator('body')).not.toBeEmpty();
    const h1 = page.locator('h1').first();
    if (await h1.count()) await expect(h1).toBeVisible();
  });

  test('no horizontal overflow', async ({ page }) => {
    await page.goto('/contact.html');
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth
    );
    expect(overflow).toBe(false);
  });

  test('axe accessibility — zero critical/serious violations', async ({ page }) => {
    await page.goto('/contact.html');
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(500);
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice'])
      .analyze();
    const critical = results.violations.filter(
      (v) => v.impact === 'critical' || v.impact === 'serious'
    );
    if (critical.length > 0) {
      console.log('\n🔴 Critical/Serious violations on /contact.html:');
      critical.forEach((v) => {
        console.log('  [' + v.impact + '] ' + v.id + ': ' + v.description);
        v.nodes.forEach((n) => console.log('    → ' + n.html.substring(0, 120)));
      });
    }
    expect(critical).toHaveLength(0);
  });

  test('all links have valid href', async ({ page }) => {
    await page.goto('/contact.html');
    const links = page.locator('a[href]');
    const count = await links.count();
    for (let i = 0; i < count; i++) {
      const href = await links.nth(i).getAttribute('href');
      expect(href).toBeTruthy();
      expect(href).not.toBe('#');
    }
  });

  test('SEO: exactly one h1 tag', async ({ page }) => {
    await page.goto('/contact.html');
    const h1Count = await page.locator('h1').count();
    expect(h1Count, 'Page must have exactly 1 <h1> tag, found ' + h1Count).toBe(1);
  });

  test('SEO: heading hierarchy (no skipped levels)', async ({ page }) => {
    await page.goto('/contact.html');
    const headings = await page.evaluate(() => {
      const els = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
      return Array.from(els).map(el => parseInt(el.tagName[1]));
    });
    for (let i = 1; i < headings.length; i++) {
      const gap = headings[i] - headings[i - 1];
      expect(gap, 'Heading level skipped: h' + headings[i-1] + ' → h' + headings[i]).toBeLessThanOrEqual(1);
    }
  });

  test('SEO: all images have descriptive alt text', async ({ page }) => {
    await page.goto('/contact.html');
    const images = page.locator('img');
    const count = await images.count();
    for (let i = 0; i < count; i++) {
      const alt = await images.nth(i).getAttribute('alt');
      expect(alt, 'Image missing alt text').toBeTruthy();
      expect(alt.length, 'Alt text too short: "' + alt + '"').toBeGreaterThan(4);
    }
  });

  test('SEO: page has a title tag', async ({ page }) => {
    await page.goto('/contact.html');
    const title = await page.title();
    expect(title, 'Page must have a <title> tag').toBeTruthy();
    expect(title.length, 'Title too short: "' + title + '"').toBeGreaterThan(10);
    expect(title.length, 'Title too long (' + title.length + ' chars)').toBeLessThan(65);
  });
});
