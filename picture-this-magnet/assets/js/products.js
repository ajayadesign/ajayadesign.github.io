/* ============================================
   PictureThisMagnet — Live Product Sync
   Fetches from /products.json REST endpoint
   ============================================ */
(function () {
  'use strict';

  const SHOPIFY_DOMAIN = 'picturethismagnet.myshopify.com';
  const PRODUCTS_URL   = `https://${SHOPIFY_DOMAIN}/products.json`;

  /* ---------- Fetch products ---------- */
  async function fetchProducts() {
    try {
      const res = await fetch(PRODUCTS_URL);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      return data.products || [];
    } catch (err) {
      console.warn('Live fetch failed, trying static data:', err);
      try {
        const res = await fetch('/_data/products.json');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        return data.products || [];
      } catch (err2) {
        console.warn('Static fallback also failed:', err2);
        return null;
      }
    }
  }

  /* ---------- Format helpers ---------- */
  function formatMoney(cents) {
    const dollars = typeof cents === 'string' ? parseFloat(cents) : cents;
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(dollars);
  }

  function escapeHtml(str) {
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
  }

  /* ---------- Create product card HTML ---------- */
  function buildCard(product) {
    const firstVariant = product.variants[0];
    const price = firstVariant ? firstVariant.price : '0';
    const img = product.images && product.images[0]
      ? product.images[0].src
      : '';
    const handle = product.handle;
    const available = product.variants.some(v => v.available !== false);
    const hasMultipleVariants = product.variants.length > 1;
    const gid = firstVariant ? `gid://shopify/ProductVariant/${firstVariant.id}` : '';
    const isCustom = ['photo-magnets', 'bulk-1-image'].includes(handle);

    let badge = '';
    if (!available) badge = '<span class="product-card-badge sold-out-badge">Sold Out</span>';
    else if (product.tags && product.tags.includes('new')) badge = '<span class="product-card-badge">New</span>';

    const priceLabel = hasMultipleVariants
      ? `<span class="from">From </span>${formatMoney(price)}`
      : formatMoney(price);

    const cardClass = available ? 'product-card' : 'product-card sold-out';

    const btnText = !available ? 'Sold Out'
      : isCustom ? 'Customize &amp; Order'
      : 'Add to Cart';

    const btnAttr = available && !isCustom
      ? `data-variant-id="${escapeHtml(gid)}" data-product-handle="${escapeHtml(handle)}"`
      : available && isCustom
        ? `data-variant-id="${escapeHtml(gid)}" data-product-handle="${escapeHtml(handle)}"`
        : 'disabled';

    return `
      <div class="${cardClass}" data-product-handle="${escapeHtml(handle)}" data-product-id="${product.id}">
        <a href="https://${SHOPIFY_DOMAIN}/products/${escapeHtml(handle)}" class="product-card-link" aria-label="${escapeHtml(product.title)}">
          <div class="product-card-image">
            ${badge}
            ${img ? `<img src="${escapeHtml(img)}" alt="${escapeHtml(product.title)}" width="400" height="400" loading="lazy">` : ''}
          </div>
          <div class="product-card-body">
            <h3 class="product-card-title">${escapeHtml(product.title)}</h3>
            <p class="product-card-price">${priceLabel}</p>
          </div>
        </a>
        <div class="product-card-actions">
          <button class="product-card-btn" ${btnAttr}>${btnText}</button>
        </div>
      </div>`;
  }

  /* ---------- Update existing cards from live data ---------- */
  function updateExistingCards(products) {
    products.forEach(product => {
      const card = document.querySelector(`[data-product-handle="${product.handle}"]`);
      if (!card) return;

      const firstVariant = product.variants[0];
      const available = product.variants.some(v => v.available !== false);
      const hasMultipleVariants = product.variants.length > 1;
      const price = firstVariant ? firstVariant.price : '0';

      // Update price
      const priceEl = card.querySelector('.product-card-price');
      if (priceEl) {
        priceEl.innerHTML = hasMultipleVariants
          ? `<span class="from">From </span>${formatMoney(price)}`
          : formatMoney(price);
      }

      // Update availability
      const btn = card.querySelector('.product-card-btn');
      if (btn) {
        if (!available) {
          card.classList.add('sold-out');
          btn.disabled = true;
          btn.textContent = 'Sold Out';
          btn.removeAttribute('data-variant-id');
        } else if (firstVariant) {
          card.classList.remove('sold-out');
          btn.disabled = false;
          const gid = `gid://shopify/ProductVariant/${firstVariant.id}`;
          btn.setAttribute('data-variant-id', gid);
          btn.setAttribute('data-product-handle', product.handle);
        }
      }

      // Update image
      if (product.images && product.images[0]) {
        const img = card.querySelector('.product-card-image img');
        if (img) img.src = product.images[0].src;
      }

      // Update badge
      const existingBadge = card.querySelector('.product-card-badge');
      if (!available && !existingBadge) {
        const imageDiv = card.querySelector('.product-card-image');
        if (imageDiv) imageDiv.insertAdjacentHTML('afterbegin', '<span class="product-card-badge sold-out-badge">Sold Out</span>');
      }
    });
  }

  /* ---------- Render new products to grid ---------- */
  function renderProducts(products, gridSelector) {
    const grid = document.querySelector(gridSelector);
    if (!grid) return;

    const existingHandles = new Set();
    grid.querySelectorAll('[data-product-handle]').forEach(el => {
      existingHandles.add(el.dataset.productHandle);
    });

    products.forEach(product => {
      if (!existingHandles.has(product.handle)) {
        grid.insertAdjacentHTML('beforeend', buildCard(product));
      }
    });
  }

  /* ---------- Init ---------- */
  async function syncProducts() {
    const products = await fetchProducts();
    if (!products) return;

    // Update existing static cards with live data
    updateExistingCards(products);

    // Render any new products to the shop grid
    const shopGrid = document.querySelector('.products-grid[data-live-sync]');
    if (shopGrid) renderProducts(products, '.products-grid[data-live-sync]');

    // Also update the featured grid on homepage
    const featuredGrid = document.querySelector('.products-grid--featured');
    if (featuredGrid) updateExistingCards(products);
  }

  // Run sync after DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', syncProducts);
  } else {
    syncProducts();
  }

  // Expose for external use
  window.ProductSync = { fetchProducts, buildCard, formatMoney };
})();
