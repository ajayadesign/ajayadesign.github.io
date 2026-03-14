const { chromium } = require('@playwright/test');
const http = require('http');
const fs = require('fs');
const path = require('path');

const SITE_DIR = __dirname;
const PORT = 8765;

// Simple static file server
function startServer() {
  return new Promise((resolve) => {
    const mimeTypes = {
      '.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript',
      '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png',
      '.svg': 'image/svg+xml', '.json': 'application/json', '.xml': 'text/xml',
      '.ico': 'image/x-icon', '.webmanifest': 'application/manifest+json'
    };
    const server = http.createServer((req, res) => {
      let urlPath = req.url.split('?')[0];
      // Rewrite /memory-lane/ paths to local
      urlPath = urlPath.replace(/^\/memory-lane/, '');
      if (urlPath.endsWith('/')) urlPath += 'index.html';
      if (!path.extname(urlPath)) urlPath += '/index.html';
      const filePath = path.join(SITE_DIR, urlPath);
      const ext = path.extname(filePath).toLowerCase();
      fs.readFile(filePath, (err, data) => {
        if (err) {
          res.writeHead(404, { 'Content-Type': 'text/html' });
          res.end('<h1>404 Not Found</h1>');
          return;
        }
        res.writeHead(200, { 'Content-Type': mimeTypes[ext] || 'application/octet-stream' });
        res.end(data);
      });
    });
    server.listen(PORT, () => {
      console.log(`Server running at http://localhost:${PORT}`);
      resolve(server);
    });
  });
}

async function takeScreenshots() {
  const server = await startServer();
  const browser = await chromium.launch({ headless: true });

  // Screenshot the new site pages
  const newPages = [
    { name: 'new-home', url: `http://localhost:${PORT}/memory-lane/` },
    { name: 'new-shop', url: `http://localhost:${PORT}/memory-lane/shop/` },
    { name: 'new-about', url: `http://localhost:${PORT}/memory-lane/about/` },
    { name: 'new-contact', url: `http://localhost:${PORT}/memory-lane/contact/` },
    { name: 'new-faq', url: `http://localhost:${PORT}/memory-lane/faq/` },
  ];

  const screenshotDir = path.join(SITE_DIR, 'assets', 'screenshots');
  fs.mkdirSync(screenshotDir, { recursive: true });

  // Desktop screenshots
  console.log('\n📸 Taking desktop screenshots...');
  const desktopCtx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  for (const pg of newPages) {
    const page = await desktopCtx.newPage();
    await page.goto(pg.url, { waitUntil: 'networkidle', timeout: 15000 }).catch(() => {});
    await page.waitForTimeout(1000);
    // Full page
    await page.screenshot({ path: path.join(screenshotDir, `${pg.name}-desktop-full.png`), fullPage: true });
    // Top fold
    await page.screenshot({ path: path.join(screenshotDir, `${pg.name}-desktop-top.png`) });
    console.log(`  ✓ ${pg.name} desktop`);
    await page.close();
  }
  await desktopCtx.close();

  // Mobile screenshots
  console.log('\n📱 Taking mobile screenshots...');
  const mobileCtx = await browser.newContext({ 
    viewport: { width: 375, height: 812 },
    isMobile: true,
    userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1'
  });
  for (const pg of newPages) {
    const page = await mobileCtx.newPage();
    await page.goto(pg.url, { waitUntil: 'networkidle', timeout: 15000 }).catch(() => {});
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(screenshotDir, `${pg.name}-mobile-full.png`), fullPage: true });
    await page.screenshot({ path: path.join(screenshotDir, `${pg.name}-mobile-top.png`) });
    console.log(`  ✓ ${pg.name} mobile`);
    await page.close();
  }
  await mobileCtx.close();

  // Screenshot the OLD Etsy shop
  console.log('\n🏚️ Taking Etsy (old site) screenshot...');
  const etsyCtx = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
  });
  await etsyCtx.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => false });
  });
  try {
    const etsyPage = await etsyCtx.newPage();
    await etsyPage.goto('https://www.etsy.com/shop/memorylanestudiotx/', { 
      waitUntil: 'domcontentloaded', timeout: 30000 
    });
    await etsyPage.waitForTimeout(6000);
    await etsyPage.screenshot({ path: path.join(screenshotDir, 'old-etsy-desktop-full.png'), fullPage: true });
    await etsyPage.screenshot({ path: path.join(screenshotDir, 'old-etsy-desktop-top.png') });
    console.log('  ✓ Etsy desktop');
    await etsyPage.close();

    // Mobile Etsy
    const etsyMobileCtx = await browser.newContext({
      viewport: { width: 375, height: 812 }, isMobile: true,
      userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15'
    });
    const etsyMobile = await etsyMobileCtx.newPage();
    await etsyMobile.goto('https://www.etsy.com/shop/memorylanestudiotx/', { 
      waitUntil: 'domcontentloaded', timeout: 30000 
    });
    await etsyMobile.waitForTimeout(6000);
    await etsyMobile.screenshot({ path: path.join(screenshotDir, 'old-etsy-mobile-full.png'), fullPage: true });
    await etsyMobile.screenshot({ path: path.join(screenshotDir, 'old-etsy-mobile-top.png') });
    console.log('  ✓ Etsy mobile');
    await etsyMobile.close();
    await etsyMobileCtx.close();
  } catch (e) {
    console.log('  ⚠ Etsy screenshot failed:', e.message);
  }
  await etsyCtx.close();

  await browser.close();
  server.close();
  console.log('\n✅ All screenshots saved to assets/screenshots/');
}

takeScreenshots().catch(console.error);
