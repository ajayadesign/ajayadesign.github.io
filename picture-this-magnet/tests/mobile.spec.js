// @ts-check
import { test, expect } from '@playwright/test';

const viewports = [
  { name: 'iPhone SE', width: 375, height: 812 },
  { name: 'iPhone Mini', width: 320, height: 568 },
];

const pages = [
  { name: 'Home', path: '/' },
  { name: 'Shop', path: '/shop/' },
  { name: 'About', path: '/about/' },
  { name: 'Contact', path: '/contact/' },
  { name: 'Events', path: '/events/' },
  { name: 'FAQ', path: '/faq/' },
  { name: 'Wholesale', path: '/wholesale/' },
];

/** Dismiss popup overlay if it appears */
async function dismissPopup(p) {
  const close = p.locator('.popup-close');
  if (await close.isVisible({ timeout: 500 }).catch(() => false)) {
    await close.click();
    await p.locator('.popup-overlay.active').waitFor({ state: 'hidden', timeout: 1000 }).catch(() => {});
  }
}

for (const vp of viewports) {
  test.describe(`Mobile — ${vp.name} (${vp.width}×${vp.height})`, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    for (const page of pages) {
      test(`${page.name} has no horizontal overflow`, async ({ page: p }) => {
        await p.goto(page.path);
        const overflow = await p.evaluate(() => {
          // Check if horizontal scroll is actually possible (visible to user)
          const docEl = document.documentElement;
          return docEl.scrollWidth > docEl.clientWidth;
        });
        expect(overflow, `${page.name} has horizontal scroll`).toBe(false);
      });
    }

    test('hamburger menu opens and closes', async ({ page: p }) => {
      await p.goto('/');
      await dismissPopup(p);
      const toggle = p.locator('#nav-toggle');
      await expect(toggle).toBeVisible();

      // Open nav
      await toggle.click();
      const navLinks = p.locator('#nav-links');
      await expect(navLinks).toHaveClass(/open/);

      // Close nav
      await toggle.click();
      await expect(navLinks).not.toHaveClass(/open/);
    });

    test('nav links are reachable via hamburger', async ({ page: p }) => {
      await p.goto('/');
      await dismissPopup(p);
      await p.locator('#nav-toggle').click();
      const navLinks = p.locator('#nav-links a');
      const count = await navLinks.count();
      expect(count).toBeGreaterThan(0);
      for (let i = 0; i < count; i++) {
        await expect(navLinks.nth(i)).toBeVisible();
      }
    });

    test('touch targets are at least 44×44px', async ({ page: p }) => {
      await p.goto('/');
      await dismissPopup(p);
      // Only check primary interactive controls visible on mobile (not hidden nav drawer links)
      const selectors = [
        '#nav-toggle',
        '.cart-toggle',
        '.hero .btn',
        '.btn-primary:not(.nav-cta)',
      ];
      const tooSmall = [];
      for (const sel of selectors) {
        const els = p.locator(sel);
        const count = await els.count();
        for (let i = 0; i < count; i++) {
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
      expect(tooSmall, `Touch targets smaller than 44×44:\n${tooSmall.join('\n')}`).toHaveLength(0);
    });
  });
}
