const { chromium } = require('@playwright/test');
const fs = require('fs');
const https = require('https');
const http = require('http');
const path = require('path');

const imgDir = path.join(__dirname, 'assets', 'images');
fs.mkdirSync(imgDir, { recursive: true });

function downloadImage(url, filepath) {
  return new Promise((resolve, reject) => {
    const proto = url.startsWith('https') ? https : http;
    proto.get(url, { headers: { 'User-Agent': 'Mozilla/5.0' } }, (res) => {
      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
        return downloadImage(res.headers.location, filepath).then(resolve).catch(reject);
      }
      const ws = fs.createWriteStream(filepath);
      res.pipe(ws);
      ws.on('finish', () => { ws.close(); resolve(filepath); });
      ws.on('error', reject);
    }).on('error', reject);
  });
}

(async () => {
  // All images from Etsy shop
  const images = [
    { url: 'https://i.etsystatic.com/63720559/r/isbl/cf3aad/82016740/isbl_1680x420.82016740_aeaf162x.jpg', name: 'shop-banner.jpg' },
    { url: 'https://i.etsystatic.com/63720559/r/isla/443333/83319003/isla_180x180.83319003_huvarxsp.jpg', name: 'shop-icon.jpg' },
    { url: 'https://i.etsystatic.com/63720559/r/il/38ee83/7601742996/il_340x270.7601742996_nwe0.jpg', name: 'product-valentines-magnets.jpg' },
    { url: 'https://i.etsystatic.com/63720559/r/il/4bbb7f/7582481830/il_340x270.7582481830_qxow.jpg', name: 'product-set-of-6.jpg' },
    { url: 'https://i.etsystatic.com/63720559/r/il/5b66a0/7582250160/il_340x270.7582250160_9z5e.jpg', name: 'product-set-of-3.jpg' },
  ];

  // Try to get higher resolution versions
  const highResImages = images.map(img => {
    // Etsy supports different sizes: il_75x75, il_170x135, il_340x270, il_570xN, il_794xN, il_1588xN
    let highRes = img.url.replace('il_340x270', 'il_794xN');
    if (img.url.includes('isbl_1680x420')) highRes = img.url; // Banner is already large
    return { ...img, url: highRes };
  });

  console.log('Downloading images...');
  for (const img of highResImages) {
    try {
      const filepath = path.join(imgDir, img.name);
      await downloadImage(img.url, filepath);
      const stats = fs.statSync(filepath);
      console.log(`  ✓ ${img.name} (${(stats.size/1024).toFixed(0)}KB)`);
    } catch (e) {
      // Fallback to original URL
      console.log(`  High-res failed for ${img.name}, trying original...`);
      try {
        const orig = images.find(i => i.name === img.name);
        await downloadImage(orig.url, path.join(imgDir, img.name));
        console.log(`  ✓ ${img.name} (fallback)`);
      } catch(e2) {
        console.log(`  ✗ ${img.name} failed: ${e2.message}`);
      }
    }
  }

  // Also try to get individual listing pages for more/better images 
  const browser = await chromium.launch({ 
    headless: false,
    args: ['--disable-blink-features=AutomationControlled', '--no-sandbox']
  });
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    viewport: { width: 1920, height: 1080 },
  });
  await context.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => false });
  });

  const listings = [
    { id: '4441094144', slug: 'personalized-photo-magnets-valentines' },
    { id: '4438043566', slug: 'set-of-6-custom-photo-magnets' },
    { id: '4438003854', slug: 'set-of-3-custom-photo-magnets' },
  ];

  for (const listing of listings) {
    try {
      const page = await context.newPage();
      await page.goto(`https://www.etsy.com/listing/${listing.id}/${listing.slug}`, {
        waitUntil: 'domcontentloaded',
        timeout: 30000
      });
      await page.waitForTimeout(5000);
      
      // Extract all product images
      const productImages = await page.evaluate(() => {
        const imgs = [];
        // Try carousel images
        document.querySelectorAll('img').forEach(img => {
          if (img.src && img.src.includes('etsystatic') && img.src.includes('/il/') && img.naturalWidth > 100) {
            imgs.push({ src: img.src, alt: img.alt || '' });
          }
        });
        // Try picture elements
        document.querySelectorAll('picture source').forEach(src => {
          if (src.srcset && src.srcset.includes('etsystatic')) {
            imgs.push({ src: src.srcset.split(',')[0].trim().split(' ')[0], alt: '' });
          }
        });
        
        // Get description
        const descEl = document.querySelector('[data-id="description-text"]') || 
                       document.querySelector('.wt-text-body-01[data-appears-component-name]');
        const desc = descEl ? descEl.innerText : '';
        
        return { imgs, desc };
      });
      
      console.log(`\nListing ${listing.id}: ${productImages.imgs.length} images`);
      console.log(`Description: ${productImages.desc.substring(0, 300)}`);
      
      // Download the best quality images
      let idx = 0;
      for (const img of productImages.imgs.slice(0, 3)) {
        const imgUrl = img.src.replace(/il_\d+x\w+/, 'il_794xN');
        const fname = `product-${listing.id}-${idx}.jpg`;
        try {
          await downloadImage(imgUrl, path.join(imgDir, fname));
          console.log(`  ✓ ${fname}`);
        } catch(e) {
          try {
            await downloadImage(img.src, path.join(imgDir, fname));
            console.log(`  ✓ ${fname} (original res)`);
          } catch(e2) {
            console.log(`  ✗ ${fname}: ${e2.message}`);
          }
        }
        idx++;
      }
      
      await page.close();
    } catch (e) {
      console.log(`Failed to scrape listing ${listing.id}: ${e.message}`);
    }
  }

  await browser.close();
  console.log('\nDone! All assets saved to assets/images/');
})();
