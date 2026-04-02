// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * Navigation consistency tests.
 * Every page must have the same desktop + mobile nav links.
 */

const PAGES = [
  '/',
  '/works/',
  '/edge/',
  '/contact/',
  '/ai-automation/',
  '/blog/',
  '/free-audit/',
  '/grader/',
];

const EXPECTED_DESKTOP_LINKS = [
  '/ai-automation/',
  '/works/',
  '/blog/',
  '/contact/',
  '/edge/',
  '/grader/',
  '/3D-print/',
  '/tools/roi-calculator.html',
  '/free-audit/',
];

const EXPECTED_MOBILE_LINKS = [
  '/ai-automation/',
  '/works/',
  '/blog/',
  '/contact/',
  '/edge/',
  '/grader/',
  '/3D-print/',
  '/tools/roi-calculator.html',
  '/free-audit/',
];

for (const pagePath of PAGES) {
  test(`${pagePath} has consistent desktop nav links`, async ({ page }) => {
    await page.goto(pagePath, { waitUntil: 'domcontentloaded' });

    // Get all desktop nav links (inside the hidden md:flex ul)
    const desktopLinks = await page.evaluate(() => {
      const nav = document.querySelector('nav#navbar');
      if (!nav) return [];
      const desktopUl = nav.querySelector('ul.hidden.md\\:flex, ul[class*="hidden md:flex"]');
      if (!desktopUl) return [];
      return Array.from(desktopUl.querySelectorAll('a[href]'))
        .map(a => new URL(a.href).pathname)
        .filter(h => h !== '/'); // skip logo
    });

    const uniqueLinks = [...new Set(desktopLinks)].sort();
    const expected = [...EXPECTED_DESKTOP_LINKS].sort();

    for (const link of expected) {
      expect(uniqueLinks, `Page ${pagePath} missing desktop nav link: ${link}`).toContain(link);
    }
  });

  test(`${pagePath} has mobile menu with toggle`, async ({ page }, testInfo) => {
    const isMobile = testInfo.project.name === 'Mobile Chrome';
    if (!isMobile) { test.skip(); return; }

    await page.goto(pagePath, { waitUntil: 'domcontentloaded' });

    // Mobile menu button exists
    const menuBtn = page.locator('#mobile-menu-btn');
    await expect(menuBtn).toBeVisible();

    // Click to open
    await menuBtn.click();
    const mobileMenu = page.locator('#mobile-menu');
    await expect(mobileMenu).toBeVisible();

    // Check mobile links
    const mobileLinks = await page.evaluate(() => {
      const menu = document.getElementById('mobile-menu');
      if (!menu) return [];
      return Array.from(menu.querySelectorAll('a[href]'))
        .map(a => new URL(a.href).pathname)
        .filter(h => h !== '/');
    });

    const uniqueMobile = [...new Set(mobileLinks)].sort();
    const expectedMobile = [...EXPECTED_MOBILE_LINKS].sort();

    for (const link of expectedMobile) {
      expect(uniqueMobile, `Page ${pagePath} missing mobile nav link: ${link}`).toContain(link);
    }
  });

  test(`${pagePath} has "Start Free" CTA button`, async ({ page }) => {
    await page.goto(pagePath, { waitUntil: 'domcontentloaded' });

    const ctaBtn = page.locator('nav#navbar a:has-text("Start Free")');
    const count = await ctaBtn.count();
    expect(count, `Page ${pagePath} missing "Start Free" CTA in nav`).toBeGreaterThanOrEqual(1);
  });

  test(`${pagePath} has "More" dropdown in desktop nav`, async ({ page }, testInfo) => {
    const isMobile = testInfo.project.name === 'Mobile Chrome';
    if (isMobile) { test.skip(); return; }

    await page.goto(pagePath, { waitUntil: 'domcontentloaded' });

    const moreBtn = page.locator('nav#navbar button:has-text("More")');
    await expect(moreBtn).toBeVisible();
  });
}
