const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

(async () => {
  const browser = await chromium.launch();
  const pages = [
    'index.html',
    'shop/index.html', 'collections/index.html', 'about/index.html',
    'faq/index.html', 'contact/index.html', '404.html', 'report.html'
  ];
  const results = [];

  for (const pg of pages) {
    const url = 'file://' + path.resolve(__dirname, pg);
    const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
    
    const errors = [];
    page.on('pageerror', err => errors.push(err.message));
    page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });

    await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);

    // Check mobile viewport
    const checks = await page.evaluate(() => {
      const issues = [];
      
      // Check viewport meta tag
      const viewport = document.querySelector('meta[name="viewport"]');
      if (!viewport) issues.push('Missing viewport meta tag');
      
      // Check title
      if (!document.title || document.title.length < 10) issues.push('Title too short or missing');
      
      // Check meta description
      const desc = document.querySelector('meta[name="description"]');
      if (!desc || !desc.content || desc.content.length < 50) issues.push('Meta description too short or missing');
      
      // Check h1
      const h1s = document.querySelectorAll('h1');
      if (h1s.length === 0) issues.push('No H1 tag found');
      if (h1s.length > 1) issues.push('Multiple H1 tags (' + h1s.length + ')');
      
      // Check images have alt text
      const imgs = document.querySelectorAll('img');
      let missingAlt = 0;
      imgs.forEach(img => { if (!img.alt) missingAlt++; });
      if (missingAlt > 0) issues.push(missingAlt + ' images missing alt text');
      
      // Check for horizontal overflow (mobile-friendliness)
      const bodyWidth = document.body.scrollWidth;
      const viewportWidth = window.innerWidth;
      if (bodyWidth > viewportWidth + 10) {
        issues.push('Horizontal overflow detected: body=' + bodyWidth + 'px, viewport=' + viewportWidth + 'px');
      }
      
      // Check touch targets (links/buttons should be >= 44px)
      let smallTargets = 0;
      document.querySelectorAll('a, button').forEach(el => {
        const rect = el.getBoundingClientRect();
        if (rect.width > 0 && rect.height > 0 && (rect.width < 30 || rect.height < 30)) {
          smallTargets++;
        }
      });
      if (smallTargets > 3) issues.push(smallTargets + ' touch targets may be too small');
      
      // Check skip link
      const skipLink = document.querySelector('.skip-link');
      if (!skipLink) issues.push('Missing skip link');
      
      // Check nav ARIA
      const nav = document.querySelector('nav[role="navigation"], nav[aria-label]');
      if (!nav) issues.push('Nav missing role or aria-label');
      
      // Check for AjayaDesign branding
      const hasFooterBranding = document.body.innerHTML.includes('AjayaDesign');
      if (!hasFooterBranding) issues.push('Missing AjayaDesign branding');
      
      // Check structured data
      const jsonLd = document.querySelectorAll('script[type="application/ld+json"]');
      
      return {
        title: document.title,
        h1Count: h1s.length,
        imgCount: imgs.length,
        missingAlt: missingAlt,
        hasViewport: !!viewport,
        hasDescription: !!(desc && desc.content),
        hasSkipLink: !!skipLink,
        hasAriaNav: !!nav,
        hasBranding: hasFooterBranding,
        jsonLdCount: jsonLd.length,
        bodyWidth: document.body.scrollWidth,
        issues: issues
      };
    });

    results.push({
      page: pg,
      checks: checks,
      jsErrors: errors.filter(e => !e.includes('net::ERR_FILE_NOT_FOUND') && !e.includes('favicon'))
    });

    await page.close();
  }

  // Print report
  console.log('\n' + '='.repeat(60));
  console.log('  ISLA NOOR — MOBILE & QUALITY AUDIT');
  console.log('='.repeat(60));
  
  let totalIssues = 0;
  for (const r of results) {
    const icon = r.checks.issues.length === 0 ? '✅' : '⚠️';
    console.log(`\n${icon} ${r.page}`);
    console.log(`   Title: ${r.checks.title}`);
    console.log(`   H1s: ${r.checks.h1Count} | Images: ${r.checks.imgCount} (${r.checks.missingAlt} missing alt)`);
    console.log(`   Viewport: ${r.checks.hasViewport ? '✓' : '✗'} | Desc: ${r.checks.hasDescription ? '✓' : '✗'} | Skip: ${r.checks.hasSkipLink ? '✓' : '✗'} | ARIA Nav: ${r.checks.hasAriaNav ? '✓' : '✗'}`);
    console.log(`   JSON-LD: ${r.checks.jsonLdCount} | Branding: ${r.checks.hasBranding ? '✓' : '✗'} | Body Width: ${r.checks.bodyWidth}px`);
    if (r.checks.issues.length > 0) {
      r.checks.issues.forEach(i => console.log(`   ⚠ ${i}`));
      totalIssues += r.checks.issues.length;
    }
    if (r.jsErrors.length > 0) {
      r.jsErrors.forEach(e => console.log(`   🐛 JS: ${e}`));
      totalIssues += r.jsErrors.length;
    }
  }
  
  console.log('\n' + '='.repeat(60));
  console.log(`  TOTAL ISSUES: ${totalIssues}`);
  console.log('='.repeat(60));

  await browser.close();
})();
