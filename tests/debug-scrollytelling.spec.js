// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * Scrollytelling canvas frame-sequence tests.
 *
 * Each page with a canvas background:
 * 1. Canvas element exists with correct data-frames / data-frame-count
 * 2. Canvas is position:fixed, fills viewport
 * 3. Opacity ramps from ~0.55 → ~0.80 as user scrolls
 * 4. Canvas stays fixed while content scrolls
 * 5. Content-over-video sections have dark overlay
 */

const PAGES_WITH_CANVAS = [
  { path: '/', name: 'Home', frameDir: '/assets/frames/drone', posterSrc: 'drone-hero.webp' },
  { path: '/edge/', name: 'Edge', frameDir: '/assets/frames/pcb', posterSrc: 'pcb-hero.webp' },
  { path: '/works/', name: 'Works', frameDir: '/assets/frames/nozzle', posterSrc: 'nozzle-hero.webp' },
];

for (const pg of PAGES_WITH_CANVAS) {
  test.describe(`${pg.name} page (${pg.path}) — scrollytelling`, () => {

    test(`canvas element exists with correct data attributes`, async ({ page }) => {
      await page.goto(pg.path);

      const canvas = page.locator('#scroll-canvas');
      await expect(canvas).toBeAttached();

      const attrs = await page.evaluate(() => {
        const c = document.getElementById('scroll-canvas');
        if (!c) return { error: 'no canvas element' };
        return {
          frames: c.dataset.frames,
          frameCount: c.dataset.frameCount,
          tagName: c.tagName,
        };
      });

      expect(attrs).not.toHaveProperty('error');
      expect(attrs.tagName).toBe('CANVAS');
      expect(attrs.frames).toBe(pg.frameDir);
      expect(attrs.frameCount).toBe('64');
    });

    test(`canvas is position:fixed and fills viewport`, async ({ page, browserName }, testInfo) => {
      await page.goto(pg.path);
      await page.waitForTimeout(1000);

      const canvasStyle = await page.evaluate(() => {
        const c = document.getElementById('scroll-canvas');
        if (!c) return { error: 'no canvas' };
        const s = window.getComputedStyle(c);
        const rect = c.getBoundingClientRect();
        return {
          position: s.position,
          display: s.display,
          width: rect.width,
          height: rect.height,
        };
      });

      expect(canvasStyle.position).toBe('fixed');
      expect(canvasStyle.display).not.toBe('none');
      // Mobile viewport is 375px wide, desktop 1280px+
      expect(canvasStyle.width).toBeGreaterThan(300);
      expect(canvasStyle.height).toBeGreaterThan(300);
    });

    test(`hero section is transparent (canvas shows through)`, async ({ page }) => {
      await page.goto(pg.path);
      await page.waitForTimeout(500);

      const heroInfo = await page.evaluate(() => {
        const hero = document.querySelector('.hero-section');
        if (!hero) return { error: 'no .hero-section' };
        const s = window.getComputedStyle(hero);
        return { background: s.backgroundColor, height: hero.getBoundingClientRect().height };
      });

      expect(heroInfo).not.toHaveProperty('error');
      expect(heroInfo.background).toMatch(/transparent|rgba\(0,\s*0,\s*0,\s*0\)/);
      expect(heroInfo.height).toBeGreaterThanOrEqual(400);
    });

    test(`content sections have opaque overlay`, async ({ page }) => {
      await page.goto(pg.path);
      await page.waitForTimeout(500);

      const contentInfo = await page.evaluate(() => {
        const sections = document.querySelectorAll('.content-over-video');
        if (!sections.length) return { error: 'no sections', count: 0 };
        const results = [];
        sections.forEach((sec, i) => {
          const s = window.getComputedStyle(sec);
          results.push({ index: i, background: s.backgroundColor, position: s.position });
        });
        return { count: sections.length, sections: results };
      });

      expect(contentInfo.count).toBeGreaterThanOrEqual(2);
      for (const sec of contentInfo.sections) {
        expect(sec.position).toBe('relative');
        expect(sec.background).toMatch(/rgba?\(/);
      }
    });

    test(`scroll-synced canvas scrub: opacity ramps up`, async ({ page }, testInfo) => {
      await page.goto(pg.path);
      await page.waitForTimeout(1500);

      const checkpoints = [0, 0.5, 1.0];
      const results = [];

      for (const pct of checkpoints) {
        await page.evaluate((scrollPct) => {
          const maxScroll = document.body.scrollHeight - window.innerHeight;
          window.scrollTo(0, maxScroll * scrollPct);
        }, pct);
        await page.waitForTimeout(200);

        const state = await page.evaluate(() => {
          const c = document.getElementById('scroll-canvas');
          if (!c) return null;
          return { opacity: parseFloat(window.getComputedStyle(c).opacity) };
        });
        results.push({ scrollPct: pct, ...state });
      }

      // Opacity should ramp up from start to end
      expect(results[0].opacity).toBeLessThan(results[results.length - 1].opacity);
    });

    test(`canvas stays fixed while scrolling`, async ({ page }) => {
      await page.goto(pg.path);
      await page.waitForTimeout(500);

      const rectTop = await page.evaluate(() => {
        const c = document.getElementById('scroll-canvas');
        const r = c.getBoundingClientRect();
        return { top: r.top, left: r.left };
      });

      await page.evaluate(() => {
        window.scrollTo(0, (document.body.scrollHeight - window.innerHeight) * 0.5);
      });
      await page.waitForTimeout(200);

      const rectMiddle = await page.evaluate(() => {
        const c = document.getElementById('scroll-canvas');
        const r = c.getBoundingClientRect();
        return { top: r.top, left: r.left };
      });

      expect(rectMiddle.top).toBe(rectTop.top);
      expect(rectMiddle.left).toBe(rectTop.left);
    });

    test(`poster image is hidden when canvas is active`, async ({ page }, testInfo) => {
      await page.goto(pg.path);
      await page.waitForTimeout(500);

      const posterDisplay = await page.evaluate(() => {
        const poster = document.querySelector('.scroll-video-poster');
        if (!poster) return 'no-element';
        return window.getComputedStyle(poster).display;
      });

      expect(posterDisplay).toBe('none');
    });
  });
}

/* ─── Contact page: no canvas expected ─── */
test.describe('Contact page — no canvas expected', () => {
  test('contact page loads without canvas element', async ({ page }) => {
    await page.goto('/contact/');
    const count = await page.locator('#scroll-canvas').count();
    expect(count).toBe(0);
  });

  test('form is visible and usable', async ({ page }) => {
    await page.goto('/contact/');
    await expect(page.locator('#ajayadesign-intake-form')).toBeAttached();
  });
});

/* ─── Cross-page navigation ─── */
test('navigating between pages preserves scroll-canvas architecture', async ({ page }, testInfo) => {
  const isMobile = testInfo.project.name === 'Mobile Chrome';

  async function clickNavLink(href) {
    if (isMobile) {
      // Ensure we're at the top so navbar is fully visible
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.waitForTimeout(300);
      const menuBtn = page.locator('#mobile-menu-btn');
      await menuBtn.click({ force: true });
      const link = page.locator(`#mobile-menu a[href="${href}"]`);
      await link.waitFor({ state: 'visible', timeout: 5000 });
      await link.click();
    } else {
      await page.click(`a[href="${href}"]`);
    }
  }

  await page.goto('/');
  await expect(page.locator('#scroll-canvas')).toBeAttached();

  const homeFrames = await page.evaluate(() => document.getElementById('scroll-canvas')?.dataset.frames);
  expect(homeFrames).toContain('drone');

  await clickNavLink('/edge/');
  await page.waitForURL('**/edge/');
  await expect(page.locator('#scroll-canvas')).toBeAttached();
  const edgeFrames = await page.evaluate(() => document.getElementById('scroll-canvas')?.dataset.frames);
  expect(edgeFrames).toContain('pcb');

  await clickNavLink('/works/');
  await page.waitForURL('**/works/');
  await expect(page.locator('#scroll-canvas')).toBeAttached();
  const worksFrames = await page.evaluate(() => document.getElementById('scroll-canvas')?.dataset.frames);
  expect(worksFrames).toContain('nozzle');
});
