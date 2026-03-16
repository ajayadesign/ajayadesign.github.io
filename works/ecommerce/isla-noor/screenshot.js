const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const browser = await chromium.launch();
  const dir = path.join(__dirname, 'assets', 'images');

  // --- Old site screenshots ---
  console.log('Capturing old site...');
  const oldPage = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await oldPage.goto('https://islanooor.myshopify.com/', { waitUntil: 'networkidle', timeout: 30000 });
  await oldPage.waitForTimeout(2000);
  await oldPage.screenshot({ path: path.join(dir, 'old-site-desktop.png'), fullPage: true });
  console.log('  old desktop done');

  await oldPage.setViewportSize({ width: 390, height: 844 });
  await oldPage.waitForTimeout(1000);
  await oldPage.screenshot({ path: path.join(dir, 'old-site-mobile.png'), fullPage: true });
  console.log('  old mobile done');
  await oldPage.close();

  // --- New site screenshots ---
  console.log('Capturing new site...');
  const newDesktop = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const newSiteUrl = 'file://' + path.resolve(__dirname, 'index.html');
  await newDesktop.goto(newSiteUrl, { waitUntil: 'networkidle', timeout: 30000 });
  await newDesktop.waitForTimeout(3000);
  // Trigger scroll animations
  await newDesktop.evaluate(() => {
    document.querySelectorAll('.fade-in, .fade-in-left, .fade-in-right').forEach(el => el.classList.add('visible'));
  });
  await newDesktop.waitForTimeout(500);
  await newDesktop.screenshot({ path: path.join(dir, 'new-site-desktop.png'), fullPage: true });
  console.log('  new desktop done');

  await newDesktop.setViewportSize({ width: 390, height: 844 });
  await newDesktop.waitForTimeout(1000);
  await newDesktop.screenshot({ path: path.join(dir, 'new-site-mobile.png'), fullPage: true });
  console.log('  new mobile done');

  // Capture other new pages
  const pages = [
    { dir: 'shop', name: 'shop' },
    { dir: 'collections', name: 'collections' },
    { dir: 'about', name: 'about' },
    { dir: 'faq', name: 'faq' },
    { dir: 'contact', name: 'contact' },
  ];
  for (const pg of pages) {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    await page.goto('file://' + path.resolve(__dirname, pg.dir, 'index.html'), { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);
    await page.evaluate(() => {
      document.querySelectorAll('.fade-in, .fade-in-left, .fade-in-right').forEach(el => el.classList.add('visible'));
    });
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(dir, `new-${pg.name}-desktop.png`), fullPage: true });
    console.log(`  new ${pg.name} done`);
    await page.close();
  }

  await browser.close();
  console.log('All screenshots captured!');
})();
