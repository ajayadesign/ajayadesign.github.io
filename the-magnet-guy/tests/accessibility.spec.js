// @ts-check
const { test, expect } = require('@playwright/test');
const AxeBuilder = require('@axe-core/playwright').default;

const PAGES = [
  { path: './', label: 'Home' },
  { path: './shop/', label: 'Shop' },
  { path: './events/', label: 'Weddings & Events' },
  { path: './about/', label: 'About' },
  { path: './faq/', label: 'FAQ' },
  { path: './contact/', label: 'Contact' },
];

for (const { path, label } of PAGES) {
  test(`${label} — no critical accessibility violations`, async ({ page }) => {
    await page.goto(path);
    // Wait for content to render
    await page.waitForLoadState('domcontentloaded');

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .disableRules(['color-contrast']) // skip contrast — depends on loaded fonts/images
      .analyze();

    const critical = results.violations.filter(
      v => v.impact === 'critical' || v.impact === 'serious'
    );

    if (critical.length > 0) {
      const summary = critical.map(v =>
        `[${v.impact}] ${v.id}: ${v.help} (${v.nodes.length} instances)\n` +
        v.nodes.slice(0, 3).map(n => `  → ${n.html.slice(0, 120)}`).join('\n')
      ).join('\n\n');
      expect(critical, `Accessibility violations on ${label}:\n${summary}`).toHaveLength(0);
    }
  });
}

/* ── Landmark roles ───────────────────────────────────────── */
for (const { path, label } of PAGES) {
  test(`${label} — has proper ARIA landmarks`, async ({ page }) => {
    await page.goto(path);
    // banner (header), navigation, main, contentinfo (footer)
    await expect(page.locator('[role="banner"], header')).toBeAttached();
    await expect(page.locator('nav[aria-label]')).toBeAttached();
    await expect(page.locator('main')).toBeAttached();
    await expect(page.locator('footer, [role="contentinfo"]')).toBeAttached();
  });
}

/* ── Focus management: skip links or keyboard-accessible nav ─ */
test('keyboard Tab reaches nav links', async ({ page }) => {
  await page.goto('./');
  // Tab through to the first nav link
  for (let i = 0; i < 10; i++) {
    await page.keyboard.press('Tab');
    const tag = await page.evaluate(() => document.activeElement?.tagName);
    const href = await page.evaluate(() => document.activeElement?.getAttribute('href'));
    if (tag === 'A' && href?.includes('/the-magnet-guy')) {
      return; // success — reached a nav link via keyboard
    }
  }
  expect(false, 'Could not reach a navigation link within 10 Tab presses').toBe(true);
});

/* ── Buttons have accessible names ────────────────────────── */
test('all buttons have accessible text', async ({ page }) => {
  await page.goto('./');
  const buttons = page.locator('button');
  const count = await buttons.count();
  for (let i = 0; i < count; i++) {
    const btn = buttons.nth(i);
    const label = await btn.getAttribute('aria-label');
    const text = (await btn.textContent()).trim();
    const title = await btn.getAttribute('title');
    expect(
      label || text || title,
      `Button #${i} has no accessible name: ${await btn.evaluate(el => el.outerHTML.slice(0, 100))}`
    ).toBeTruthy();
  }
});

/* ── form inputs have labels ──────────────────────────────── */
test('Contact form inputs have labels', async ({ page }) => {
  await page.goto('./contact/');
  const inputs = page.locator('input:not([type="hidden"]):not([type="submit"]), textarea, select');
  const count = await inputs.count();
  for (let i = 0; i < count; i++) {
    const input = inputs.nth(i);
    const id = await input.getAttribute('id');
    const ariaLabel = await input.getAttribute('aria-label');
    const placeholder = await input.getAttribute('placeholder');
    if (id) {
      const label = page.locator(`label[for="${id}"]`);
      const hasLabel = await label.count() > 0;
      expect(hasLabel || !!ariaLabel || !!placeholder, `Input "${id}" has no label`).toBe(true);
    } else {
      expect(!!ariaLabel || !!placeholder, `Input #${i} has no label or aria-label`).toBe(true);
    }
  }
});
