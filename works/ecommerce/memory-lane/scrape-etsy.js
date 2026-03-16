const { chromium } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  // Navigate to Etsy shop
  console.log('Navigating to Etsy shop...');
  await page.goto('https://www.etsy.com/shop/memorylanestudiotx/', { 
    waitUntil: 'networkidle',
    timeout: 60000 
  });
  
  // Wait for content to load
  await page.waitForTimeout(3000);
  
  // Scroll down to load more products  
  for (let i = 0; i < 5; i++) {
    await page.evaluate(() => window.scrollBy(0, 1000));
    await page.waitForTimeout(1000);
  }

  // Extract shop data
  const shopData = await page.evaluate(() => {
    const data = { shopName: '', shopDescription: '', shopBanner: '', shopIcon: '', announcement: '', products: [], reviews: [] };
    
    // Shop name
    const nameEl = document.querySelector('[data-shop-name]') || document.querySelector('h1') || document.querySelector('.shop-name-and-title-container h1');
    data.shopName = nameEl ? nameEl.textContent.trim() : 'Memory Lane Studio TX';
    
    // Shop icon  
    const iconEl = document.querySelector('.shop-icon-external img') || document.querySelector('[data-shop-icon] img') || document.querySelector('.shop-icon img');
    data.shopIcon = iconEl ? iconEl.src : '';
    
    // Banner
    const bannerEl = document.querySelector('.shop-banner img') || document.querySelector('[style*="background-image"]');
    if (bannerEl && bannerEl.tagName === 'IMG') {
      data.shopBanner = bannerEl.src;
    } else if (bannerEl) {
      const style = bannerEl.getAttribute('style');
      const match = style && style.match(/url\(["']?([^"')]+)["']?\)/);
      data.shopBanner = match ? match[1] : '';
    }
    
    // Description/announcement
    const descEl = document.querySelector('.shop-announcement') || document.querySelector('[data-announcement]');
    data.shopDescription = descEl ? descEl.textContent.trim() : '';
    
    // Try to get all text content for analysis
    data.pageText = document.body ? document.body.innerText.substring(0, 5000) : '';
    
    // Products
    const listingCards = document.querySelectorAll('.listing-card, .v2-listing-card, [data-listing-card], .wt-grid__item-xs-6');
    listingCards.forEach(card => {
      const product = {};
      const imgEl = card.querySelector('img');
      const titleEl = card.querySelector('.v2-listing-card__info .v2-listing-card__title, .listing-title, a[title]');
      const priceEl = card.querySelector('.currency-value, .lc-price .wt-text-title-01, span.currency-value');
      const linkEl = card.querySelector('a[href*="/listing/"]');
      
      product.title = titleEl ? titleEl.textContent.trim() : (linkEl ? linkEl.getAttribute('title') : '');
      product.image = imgEl ? (imgEl.src || imgEl.getAttribute('data-src')) : '';
      product.price = priceEl ? priceEl.textContent.trim() : '';
      product.url = linkEl ? linkEl.href : '';
      
      if (product.title || product.image) {
        data.products.push(product);
      }
    });
    
    // Also try alternate selectors for newer Etsy layout
    if (data.products.length === 0) {
      const altCards = document.querySelectorAll('[data-listing-id]');
      altCards.forEach(card => {
        const product = {};
        const imgEl = card.querySelector('img');
        const linkEl = card.querySelector('a');
        product.title = linkEl ? (linkEl.getAttribute('title') || linkEl.textContent.trim()) : '';
        product.image = imgEl ? (imgEl.src || imgEl.getAttribute('data-src')) : '';
        product.url = linkEl ? linkEl.href : '';
        product.id = card.getAttribute('data-listing-id');
        if (product.title || product.image) {
          data.products.push(product);
        }
      });
    }
    
    // Reviews
    const reviewEls = document.querySelectorAll('.review-item, [data-review]');
    reviewEls.forEach(el => {
      const text = el.querySelector('.review-text, .wt-text-body-01');
      const stars = el.querySelectorAll('.star-input svg, .icon-star-filled').length;
      if (text) {
        data.reviews.push({ text: text.textContent.trim(), stars });
      }
    });

    return data;
  });
  
  // Save full page HTML for reference
  const html = await page.content();
  fs.writeFileSync('/tmp/etsy_full.html', html);
  
  // Take screenshot  
  await page.screenshot({ path: '/tmp/etsy_shop_screenshot.png', fullPage: true });
  
  // Save extracted data
  fs.writeFileSync('/tmp/etsy_shop_data.json', JSON.stringify(shopData, null, 2));
  
  console.log('Shop data:', JSON.stringify(shopData, null, 2).substring(0, 3000));
  console.log('\nProducts found:', shopData.products.length);
  console.log('Page text excerpt:', shopData.pageText.substring(0, 1000));
  
  await browser.close();
})();
