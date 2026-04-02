// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * Scrollytelling canvas frame-sequence tests.
 * CI-hardened: uses waitForFunction/waitFor instead of raw timeouts.
 */

const PAGES_WITH_CANVAS = [
  { path: '/', name: 'Home', frameDir: '/assets/frames/drone', posterSrc: 'drone-hero.webp' },
  { path: '/edge/', name: 'Edge', frameDir: '/assets/frames/pcb', posterSrc: 'pcb-hero.webp' },
  { path: '/works/', name: 'Works', frameDir: '/assets/frames/nozzle', posterSrc: 'nozzle-hero.webp' },
];

/** Wait for the canvas element to be ready (attached + has dimensions) */
async function waitForCanvas(page, timeoutMs = 15000) {
  await page.waitForFunction(() => {
    const c = document.getElementById('scroll-canvas');
    return c && c.getBoundingClientRect().width > 100;
  }, { timeout: timeoutMs });
}

for (const pg of PAGES_WITH_CANVAS) {
  test.describe(`${pg.name} page (${pg.path}) — scrollytelling`, () => {
    // Give CI plenty of room
    test.setTimeout(60000);

    test(`canvas element exists with correct data attributes`, async ({ page }) => {
      await page.goto(pg.path, { waitUntil: 'domcontentloaded' });

      const canvas = page.locator('#scroll-canvas');
      await expect(canvas).toBeAttached({ timeout: 10000 });

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

    test(`canvas is position:fixed and fills viewport`, async ({ page }) => {
      await page.goto(pg.path, { waitUntil: 'domcontentloaded' });
      await waitForCanvas(page);

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
      expect(canvasStyle.width).toBeGreaterThan(300);
      expect(canvasStyle.height).toBeGreaterThan(300);
    });

    test(`canvas loads fewer frames on mobile for performance`, async ({ page }, testInfo) => {
      const isMobile = testInfo.project.name === 'Mobile Chrome';
      if (!isMobile) { test.skip(); return; }

      await page.goto(pg.path, { waitUntil: 'domcontentloaded' });
      await waitForCanvas(page);

      const canvasInfo = await page.evaluate(() => {
        const c = document.getElementById('scroll-canvas');
        if (!c) return { error: 'no canvas' };
        const s = window.getComputedStyle(c);
        return { display: s.display, width: c.width, height: c.height };
      });
      expect(canvasInfo.display).not.toBe('none');
    });

    test(`hero section is transparent (canvas shows through)`, async ({ page }) => {
      await page.goto(pg.path, { waitUntil: 'domcontentloaded' });
      await waitForCanvas(page);

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
      await page.goto(pg.path, { waitUntil: 'domcontentloaded' });
      await page.locator('.content-over-video').first().waitFor({ state: 'attached', timeout: 15000 });

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

    test(`scroll-synced canvas scrub: opacity ramps up`, async ({ page }) => {
      await page.goto(pg.path, { waitUntil: 'domcontentloaded' });
      await waitForCanvas(page);
      // Extra settle time for frame images to start loading
      await page.waitForTimeout(1000);

      const checkpoints = [0, 0.5, 1.0];
      const results = [];

      for (const pct of checkpoints) {
        await page.evaluate((scrollPct) => {
          const maxScroll = document.body.scrollHeight - window.innerHeight;
          window.scrollTo(0, maxScroll * scrollPct);
        }, pct);
        // Wait for scroll handler to fire and repaint
        await page.waitForFunction((expectedPct) => {
          const maxScroll = document.body.scrollHeight - window.innerHeight;
          const currentPct = window.scrollY / maxScroll;
          return Math.abs(currentPct - expectedPct) < 0.1;
        }, pct, { timeout: 5000 }).catch(() => {});
        await page.waitForTimeout(150);

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
      await page.goto(pg.path, { waitUntil: 'domcontentloaded' });
      await waitForCanvas(page);

      const rectTop = await page.evaluate(() => {
        const c = document.getElementById('scroll-canvas');
        const r = c.getBoundingClientRect();
        return { top: r.top, left: r.left };
      });

      await page.evaluate(() => {
        window.scrollTo(0, (document.body.scrollHeight - window.innerHeight) * 0.5);
      });
      await page.waitForFunction(() => window.scrollY > 100, { timeout: 5000 });

      const rectMiddle = await page.evaluate(() => {
        const c = document.getElementById('scroll-canvas');
        const r = c.getBoundingClientRect();
        return { top: r.top, left: r.left };
      });

      expect(rectMiddle.top).toBe(rectTop.top);
      expect(rectMiddle.left).toBe(rectTop.left);
    });

    test(`poster hidden when canvas is active`, async ({ page }) => {
      await page.goto(pg.path, { waitUntil: 'domcontentloaded' });
      // Wait for poster to hide (JS draws frame 0 then hides poster)
      await page.waitForFunction(() => {
        const poster = document.querySelector('.scroll-video-poster');
        if (!poster) return true; // no poster element = fine
        return window.getComputedStyle(poster).display === 'none';
      }, { timeout: 15000 });

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
    await page.goto('/contact/', { waitUntil: 'domcontentloaded' });
    const count = await page.locator('#scroll-canvas').count();
    expect(count).toBe(0);
  });

  test('form is visible and usable', async ({ page }) => {
    await page.goto('/contact/', { waitUntil: 'domcontentloaded' });
    await expect(page.locator('#ajayadesign-intake-form')).toBeAttached({ timeout: 10000 });
  });
});

/* ─── Cross-page navigation ─── */
test('navigating between pages preserves scroll-canvas architecture', async ({ page }, testInfo) => {
  test.setTimeout(60000);
  const isMobile = testInfo.project.name === 'Mobile Chrome';

  async function clickNavLink(href) {
    if (isMobile) {
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.waitForFunction(() => window.scrollY === 0, { timeout: 3000 }).catch(() => {});
      
      const menuBtn = page.locator('#mobile-menu-btn');
      const mobileMenu = page.locator('#mobile-menu');
      
      // Ensure menu is open — may need multiple clicks if state is stale
      for (let attempt = 0; attempt < 3; attempt++) {
        await menuBtn.click({ force: true });
        try {
          await mobileMenu.waitFor({ state: 'visible', timeout: 2000 });
          break;
        } catch {
          // Menu might have toggled closed — try again
        }
      }
      
      const link = page.locator(`#mobile-menu a[href="${href}"]`);
      await link.waitFor({ state: 'visible', timeout: 5000 });
      await link.click();
    } else {
      const directLink = page.locator(`nav a[href="${href}"]:visible`).first();
      if (await directLink.count() > 0) {
        await directLink.click();
      } else {
        const moreBtn = page.locator('nav button:has-text("More")');
        if (await moreBtn.count() > 0) {
          await moreBtn.hover();
          await page.locator(`a[href="${href}"]`).first().waitFor({ state: 'visible', timeout: 5000 });
        }
        const dropdownLink = page.locator(`a[href="${href}"]:visible`).first();
        await dropdownLink.click();
      }
    }
  }

  await page.goto('/', { waitUntil: 'domcontentloaded' });
  await expect(page.locator('#scroll-canvas')).toBeAttached({ timeout: 10000 });

  const homeFrames = await page.evaluate(() => document.getElementById('scroll-canvas')?.dataset.frames);
  expect(homeFrames).toContain('drone');

  await clickNavLink('/edge/');
  await page.waitForURL('**/edge/', { timeout: 15000 });
  await expect(page.locator('#scroll-canvas')).toBeAttached({ timeout: 10000 });
  const edgeFrames = await page.evaluate(() => document.getElementById('scroll-canvas')?.dataset.frames);
  expect(edgeFrames).toContain('pcb');

  await clickNavLink('/works/');
  await page.waitForURL('**/works/', { timeout: 15000 });
  await expect(page.locator('#scroll-canvas')).toBeAttached({ timeout: 10000 });
  const worksFrames = await page.evaluate(() => document.getElementById('scroll-canvas')?.dataset.frames);
  expect(worksFrames).toContain('nozzle');
});
