// @ts-check
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const pages = [
  { name: 'Home', path: '/' },
  { name: 'Shop', path: '/shop/' },
  { name: 'About', path: '/about/' },
  { name: 'Contact', path: '/contact/' },
  { name: 'Events', path: '/events/' },
  { name: 'FAQ', path: '/faq/' },
  { name: 'Wholesale', path: '/wholesale/' },
  { name: 'Privacy', path: '/policies/privacy/' },
  { name: 'Shipping', path: '/policies/shipping/' },
  { name: 'Terms', path: '/policies/terms/' },
  { name: 'Refund', path: '/policies/refund/' },
];

for (const page of pages) {
  test(`${page.name} page should pass axe accessibility checks`, async ({ page: p }) => {
    await p.goto(page.path);
    // Force all scroll-triggered animations to their visible end-state
    await p.addStyleTag({ content: `
      .fade-in, .fade-in-left, .fade-in-right,
      .stagger-children > * {
        opacity: 1 !important;
        transform: none !important;
        transition: none !important;
      }
    `});
    const results = await new AxeBuilder({ page: p })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();

    const violations = results.violations.map(
      (v) => `[${v.impact}] ${v.id}: ${v.help} (${v.nodes.length} instance${v.nodes.length > 1 ? 's' : ''})`
    );

    expect(violations, `Axe violations on ${page.name}:\n${violations.join('\n')}`).toHaveLength(0);
  });
}
