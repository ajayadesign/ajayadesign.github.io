/**
 * Screenshot script for report.html
 * Takes screenshots of old (themagnetguy.com) and new (local) sites
 */
const { chromium } = require('playwright');
const path = require('path');
const http = require('http');
const fs = require('fs');

const SCREENSHOT_DIR = path.join(__dirname, 'assets', 'images', 'report');
const OLD_URL = 'https://themagnetguy.com/';
const NEW_DIR = __dirname;

// Simple static file server
function startServer(dir, port) {
  return new Promise((resolve) => {
    const mimeTypes = {
      '.html': 'text/html', '.css': 'text/css', '.js': 'application/javascript',
      '.png': 'image/png', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml',
      '.json': 'application/json', '.xml': 'application/xml',
    };
    const server = http.createServer((req, res) => {
      let urlPath = req.url.split('?')[0];
      if (urlPath.endsWith('/')) urlPath += 'index.html';
      const filePath = path.join(dir, urlPath);
      const ext = path.extname(filePath);
      fs.readFile(filePath, (err, data) => {
        if (err) {
          res.writeHead(404);
          res.end('Not Found');
          return;
        }
        res.writeHead(200, { 'Content-Type': mimeTypes[ext] || 'application/octet-stream' });
        res.end(data);
      });
    });
    server.listen(port, () => resolve(server));
  });
}

async function main() {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });

  // Start local server
  const server = await startServer(NEW_DIR, 8765);
  console.log('Local server started on port 8765');

  const browser = await chromium.launch({ args: ['--no-sandbox'] });

  // Desktop viewport
  const desktopCtx = await browser.newContext({ viewport: { width: 1440, height: 900 } });

  // Mobile viewport
  const mobileCtx = await browser.newContext({ viewport: { width: 375, height: 812 }, isMobile: true });

  // --- OLD SITE (Desktop) ---
  console.log('Capturing old site (desktop)...');
  const oldDesktop = await desktopCtx.newPage();
  try {
    await oldDesktop.goto(OLD_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await oldDesktop.waitForTimeout(2000);
    await oldDesktop.screenshot({ path: path.join(SCREENSHOT_DIR, 'old-desktop-full.png'), fullPage: true });
    await oldDesktop.screenshot({ path: path.join(SCREENSHOT_DIR, 'old-desktop-top.png') });
    console.log('  Old desktop screenshots done');
  } catch (e) {
    console.error('  Old desktop failed:', e.message);
  }
  await oldDesktop.close();

  // --- OLD SITE (Mobile) ---
  console.log('Capturing old site (mobile)...');
  const oldMobile = await mobileCtx.newPage();
  try {
    await oldMobile.goto(OLD_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await oldMobile.waitForTimeout(2000);
    await oldMobile.screenshot({ path: path.join(SCREENSHOT_DIR, 'old-mobile-full.png'), fullPage: true });
    await oldMobile.screenshot({ path: path.join(SCREENSHOT_DIR, 'old-mobile-top.png') });
    console.log('  Old mobile screenshots done');
  } catch (e) {
    console.error('  Old mobile failed:', e.message);
  }
  await oldMobile.close();

  // --- NEW SITE (Desktop) ---
  console.log('Capturing new site (desktop)...');
  const newDesktop = await desktopCtx.newPage();
  try {
    await newDesktop.goto('http://localhost:8765/', { waitUntil: 'networkidle', timeout: 15000 });
    await newDesktop.waitForTimeout(1500);
    await newDesktop.screenshot({ path: path.join(SCREENSHOT_DIR, 'new-desktop-full.png'), fullPage: true });
    await newDesktop.screenshot({ path: path.join(SCREENSHOT_DIR, 'new-desktop-top.png') });
    console.log('  New desktop screenshots done');
  } catch (e) {
    console.error('  New desktop failed:', e.message);
  }
  await newDesktop.close();

  // --- NEW SITE (Mobile) ---
  console.log('Capturing new site (mobile)...');
  const newMobile = await mobileCtx.newPage();
  try {
    await newMobile.goto('http://localhost:8765/', { waitUntil: 'networkidle', timeout: 15000 });
    await newMobile.waitForTimeout(1500);
    await newMobile.screenshot({ path: path.join(SCREENSHOT_DIR, 'new-mobile-full.png'), fullPage: true });
    await newMobile.screenshot({ path: path.join(SCREENSHOT_DIR, 'new-mobile-top.png') });
    console.log('  New mobile screenshots done');
  } catch (e) {
    console.error('  New mobile failed:', e.message);
  }
  await newMobile.close();

  // --- NEW SITE PAGES ---
  const pages = ['shop/', 'events/', 'about/', 'faq/', 'contact/'];
  for (const pg of pages) {
    console.log(`Capturing new ${pg} (desktop)...`);
    const p = await desktopCtx.newPage();
    try {
      await p.goto(`http://localhost:8765/${pg}`, { waitUntil: 'networkidle', timeout: 15000 });
      await p.waitForTimeout(1000);
      await p.screenshot({ path: path.join(SCREENSHOT_DIR, `new-${pg.replace('/', '')}-desktop.png`) });
    } catch (e) {
      console.error(`  ${pg} failed:`, e.message);
    }
    await p.close();
  }

  await browser.close();
  server.close();
  console.log('All screenshots complete!');
}

main().catch(e => { console.error(e); process.exit(1); });
