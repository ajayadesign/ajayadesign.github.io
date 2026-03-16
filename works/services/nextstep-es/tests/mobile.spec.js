// @ts-check
import { test, expect } from '@playwright/test';

const viewports = [
  { name: 'iPhone SE', width: 375, height: 812 },
  { name: 'iPhone Mini', width: 320, height: 568 },
];

const pages = [
  { name: 'Home', path: 'index.html' },
  { name: 'Services', path: 'services.html' },
  { name: 'Gallery', path: 'gallery.html' },
  { name: 'About', path: 'about.html' },
  { name: 'FAQ', path: 'faq.html' },
  { name: 'Contact', path: 'contact.html' },
  { name: 'Report', path: 'report.html' },
];

for (const vp of viewports) {
  test.describe(`Mobile — ${vp.name} (${vp.width}×${vp.height})`, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    for (const pg of pages) {
      test(`${pg.name} has no horizontal overflow`, async ({ page }) => {
        await page.goto(pg.path);
        const overflow = await page.evaluate(() => {
          return document.documentElement.scrollWidth > document.documentElement.clientWidth;
        });
        expect(overflow, `${pg.name} has horizontal scroll at ${vp.width}px`).toBe(false);
      });
    }

    test('hamburger menu opens and closes', async ({ page }) => {
      await page.goto('index.html');
      const toggle = page.locator('.nav-toggle');
      await expect(toggle).toBeVisible();

      // Open nav
      await toggle.click();
      const navLinks = page.locator('#nav-links');
      await expect(navLinks).toHaveClass(/open/);

      // Close nav
      await toggle.click();
      await expect(navLinks).not.toHaveClass(/open/);
    });

    test('nav links are reachable via hamburger', async ({ page }) => {
      await page.goto('index.html');
      await page.locator('.nav-toggle').click();
      const navLinks = page.locator('#nav-links a');
      const count = await navLinks.count();
      expect(count).toBeGreaterThanOrEqual(6);
      for (let i = 0; i < count; i++) {
        await expect(navLinks.nth(i)).toBeVisible();
      }
    });

    test('touch targets are at least 44×44px', async ({ page }) => {
      await page.goto('index.html');
      const selectors = ['.nav-toggle', '.hero .btn', '.back-to-top'];
      const tooSmall = [];
      for (const sel of selectors) {
        const els = page.locator(sel);
        const n = await els.count();
        for (let i = 0; i < n; i++) {
          const el = els.nth(i);
          if (!(await el.isVisible())) continue;
          const box = await el.boundingBox();
          if (!box) continue;
          if (box.width < 44 || box.height < 44) {
            const desc = await el.evaluate((e) => `${e.tagName.toLowerCase()}.${[...e.classList].join('.')}`);
            tooSmall.push(`${desc} → ${Math.round(box.width)}×${Math.round(box.height)}`);
          }
        }
      }
      expect(tooSmall, `Touch targets < 44×44:\n${tooSmall.join('\n')}`).toHaveLength(0);
    });
  });
}
