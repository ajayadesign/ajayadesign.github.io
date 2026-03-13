// @ts-check
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const pages = [
  { name: 'Home', path: 'index.html' },
  { name: 'Services', path: 'services.html' },
  { name: 'Gallery', path: 'gallery.html' },
  { name: 'About', path: 'about.html' },
  { name: 'FAQ', path: 'faq.html' },
  { name: 'Contact', path: 'contact.html' },
  { name: 'Report', path: 'report.html' },
];

for (const pg of pages) {
  test(`${pg.name} page should pass axe accessibility checks`, async ({ page }) => {
    await page.goto(pg.path);
    // Force scroll-triggered animations to visible state
    await page.addStyleTag({ content: `
      .fade-in, .fade-in-left, .fade-in-right,
      .stagger-children > * {
        opacity: 1 !important;
        transform: none !important;
        transition: none !important;
      }
    `});
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();

    const violations = results.violations.map(
      (v) => `[${v.impact}] ${v.id}: ${v.help} (${v.nodes.length} instance${v.nodes.length > 1 ? 's' : ''})`
    );

    expect(violations, `Axe violations on ${pg.name}:\n${violations.join('\n')}`).toHaveLength(0);
  });
}
