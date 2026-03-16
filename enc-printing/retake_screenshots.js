const { chromium } = require('playwright-core');
const path = require('path');

const SCREENSHOT_DIR = '/home/aj/website/ajayadesign.github.io/enc-printing/screenshots';
const BASE = 'http://localhost:9222';

async function fixLazyAndCapture(page, url, filename, opts = {}) {
  await page.goto(url, { waitUntil: 'networkidle' });
  
  // Fix lazy-loaded images
  await page.evaluate(() => {
    document.querySelectorAll('img[loading="lazy"]').forEach(img => {
      img.removeAttribute('loading');
      const src = img.src;
      img.src = '';
      img.src = src;
    });
  });
  
  // Scroll through the entire page to trigger IntersectionObservers
  await page.evaluate(async () => {
    const h = document.body.scrollHeight;
    for (let y = 0; y < h; y += 300) {
      window.scrollTo(0, y);
      await new Promise(r => setTimeout(r, 100));
    }
    window.scrollTo(0, 0);
  });
  
  // Wait for all images to load
  await page.evaluate(async () => {
    const imgs = Array.from(document.querySelectorAll('img'));
    await Promise.all(imgs.map(img => {
      if (img.complete && img.naturalHeight > 0) return Promise.resolve();
      return new Promise((resolve) => {
        img.onload = resolve;
        img.onerror = resolve;
        setTimeout(resolve, 3000);
      });
    }));
  });
  
  await page.waitForTimeout(500);
  
  const filepath = path.join(SCREENSHOT_DIR, filename);
  await page.screenshot({ path: filepath, fullPage: true, type: 'png', ...opts });
  console.log(`✓ ${filename}`);
}

(async () => {
  const browser = await chromium.launch();
  
  // Desktop screenshots
  const desktopCtx = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const dp = await desktopCtx.newPage();
  
  await fixLazyAndCapture(dp, `${BASE}/`, 'build-desktop.png');
  await fixLazyAndCapture(dp, `${BASE}/about/`, 'build-about.png');
  await fixLazyAndCapture(dp, `${BASE}/contact/`, 'build-contact.png');
  await fixLazyAndCapture(dp, `${BASE}/photo-magnets/`, 'build-photo-magnets.png');
  await fixLazyAndCapture(dp, `${BASE}/frames-ornaments/`, 'build-frames-ornaments.png');
  await fixLazyAndCapture(dp, `${BASE}/printed-files/`, 'build-printed-files.png');
  await fixLazyAndCapture(dp, `${BASE}/products/custom-photo-magnets/`, 'build-product-detail.png');
  
  await desktopCtx.close();
  
  // Mobile screenshot (375px)
  const mobileCtx = await browser.newContext({ viewport: { width: 375, height: 812 }, isMobile: true });
  const mp = await mobileCtx.newPage();
  
  await fixLazyAndCapture(mp, `${BASE}/`, 'build-mobile.png');
  
  await mobileCtx.close();
  await browser.close();
  console.log('\nAll screenshots captured!');
})();
