const { chromium } = require('@playwright/test');
const fs = require('fs');

(async () => {
  const browser = await chromium.launch({ 
    headless: false,
    args: [
      '--disable-blink-features=AutomationControlled',
      '--no-sandbox'
    ]
  });
  
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    viewport: { width: 1920, height: 1080 },
    locale: 'en-US',
  });
  
  // Remove webdriver flag
  await context.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => false });
    delete navigator.__proto__.webdriver;
  });
  
  const page = await context.newPage();
  
  console.log('Navigating to Etsy shop...');
  try {
    await page.goto('https://www.etsy.com/shop/memorylanestudiotx/', { 
      waitUntil: 'domcontentloaded',
      timeout: 60000 
    });
  } catch(e) {
    console.log('Navigation timeout, continuing...');
  }
  
  // Wait for page to settle
  await page.waitForTimeout(8000);
  
  // Take screenshot to see what we got
  await page.screenshot({ path: '/tmp/etsy_debug.png', fullPage: false });
  
  const content = await page.content();
  fs.writeFileSync('/tmp/etsy_full2.html', content);
  console.log('Page length:', content.length);
  console.log('Title:', await page.title());
  
  // Check if there's a captcha
  const bodyText = await page.evaluate(() => document.body?.innerText?.substring(0, 2000) || 'empty');
  console.log('Body text:', bodyText);
  
  // Try to extract data from whatever loaded
  const shopData = await page.evaluate(() => {
    const data = { products: [], images: [] };
    
    // Get all images on page
    document.querySelectorAll('img').forEach(img => {
      if (img.src && (img.src.includes('etsystatic') || img.src.includes('etsy'))) {
        data.images.push({ src: img.src, alt: img.alt || '' });
      }
    });
    
    // Get all links
    const links = [];
    document.querySelectorAll('a[href*="listing"]').forEach(a => {
      links.push({ href: a.href, text: a.textContent?.trim()?.substring(0, 100) });
    });
    data.links = links;
    
    return data;
  });
  
  console.log('Images found:', shopData.images.length);
  console.log('Links found:', shopData.links?.length);
  console.log(JSON.stringify(shopData, null, 2).substring(0, 3000));
  
  await browser.close();
})();
