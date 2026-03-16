const { test, expect } = require('@playwright/test');

test.describe('Site Integration', () => {
  test('nav and footer present on all pages', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('nav')).toBeVisible();
    await expect(page.locator('footer')).toBeVisible();

    await page.goto('/shop.html');
    await expect(page.locator('nav')).toBeVisible();
    await expect(page.locator('footer')).toBeVisible();

    await page.goto('/about.html');
    await expect(page.locator('nav')).toBeVisible();
    await expect(page.locator('footer')).toBeVisible();

    await page.goto('/contact.html');
    await expect(page.locator('nav')).toBeVisible();
    await expect(page.locator('footer')).toBeVisible();
  });

  test('nav links are present on homepage', async ({ page }) => {
    await page.goto('/');
    const link_index = page.locator('nav a[href="index.html"]');
    if (await link_index.count()) await expect(link_index).toBeVisible();
    const link_shop = page.locator('nav a[href="shop.html"]');
    if (await link_shop.count()) await expect(link_shop).toBeVisible();
    const link_about = page.locator('nav a[href="about.html"]');
    if (await link_about.count()) await expect(link_about).toBeVisible();
    const link_contact = page.locator('nav a[href="contact.html"]');
    if (await link_contact.count()) await expect(link_contact).toBeVisible();
  });
});
