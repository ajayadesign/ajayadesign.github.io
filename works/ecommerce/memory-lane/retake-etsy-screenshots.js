const { chromium } = require('@playwright/test');
const path = require('path');

const screenshotDir = path.join(__dirname, 'assets', 'screenshots');

(async () => {
  const browser = await chromium.launch({ 
    headless: false,
    args: ['--disable-blink-features=AutomationControlled', '--no-sandbox']
  });
  
  // Desktop
  const ctx = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
  });
  await ctx.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => false });
    delete navigator.__proto__.webdriver;
  });
  
  console.log('Taking Etsy desktop screenshot...');
  const page = await ctx.newPage();
  await page.goto('https://www.etsy.com/shop/memorylanestudiotx/', { 
    waitUntil: 'domcontentloaded', timeout: 45000 
  });
  await page.waitForTimeout(8000);
  
  // Scroll to load content
  for (let i = 0; i < 3; i++) {
    await page.evaluate(() => window.scrollBy(0, 600));
    await page.waitForTimeout(800);
  }
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(1000);
  
  await page.screenshot({ path: path.join(screenshotDir, 'old-etsy-desktop-full.png'), fullPage: true });
  await page.screenshot({ path: path.join(screenshotDir, 'old-etsy-desktop-top.png') });
  console.log('  ✓ Desktop done');
  await page.close();
  await ctx.close();
  
  // Mobile
  console.log('Taking Etsy mobile screenshot...');
  const mCtx = await browser.newContext({
    viewport: { width: 375, height: 812 }, isMobile: true,
    userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1'
  });
  await mCtx.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => false });
  });
  const mp = await mCtx.newPage();
  await mp.goto('https://www.etsy.com/shop/memorylanestudiotx/', { 
    waitUntil: 'domcontentloaded', timeout: 45000 
  });
  await mp.waitForTimeout(8000);
  await mp.screenshot({ path: path.join(screenshotDir, 'old-etsy-mobile-full.png'), fullPage: true });
  await mp.screenshot({ path: path.join(screenshotDir, 'old-etsy-mobile-top.png') });
  console.log('  ✓ Mobile done');
  
  await browser.close();
  console.log('✅ Etsy screenshots updated');
})();
