/* ══════════════════════════════════════════════════════
   Memory Lane Studio TX — Etsy Product Integration
   Since Etsy has no public storefront API like Shopify,
   we use scraped product data + direct Etsy links.
   Property of AjayaDesign — Demo Purpose Only
   ══════════════════════════════════════════════════════ */

const ETSY_SHOP = 'memorylanestudiotx';
const ETSY_SHOP_URL = 'https://www.etsy.com/shop/' + ETSY_SHOP;

// Static product catalog (scraped from Etsy; update periodically)
const PRODUCTS = [
  {
    id: '4441094144',
    title: "Personalized Photo Magnets | Valentine's Day Keepsake Gift, Set of 3",
    price: 15.00,
    category: 'custom',
    tags: ['valentines', 'custom', 'featured', 'bestseller'],
    image: 'assets/images/product-valentines-magnets.jpg',
    images: [
      'assets/images/product-4441094144-0.jpg',
      'assets/images/product-4441094144-1.jpg',
      'assets/images/product-4441094144-2.jpg'
    ],
    url: 'https://www.etsy.com/listing/4441094144/personalized-photo-magnets-valentines',
    description: "Celebrate Valentine's Day with a gift that's truly personal. These custom Valentine's Day photo magnets are created using your favorite memories and designed as meaningful keepsakes you'll treasure long after the holiday. Perfect for couples, kids & babies, parents & grandparents.",
    available: true
  },
  {
    id: '4438043566',
    title: 'Set of 6 Custom Photo Magnets | Personalized Memory Keepsakes | Gift for Family',
    price: 25.00,
    category: 'custom',
    tags: ['custom', 'family', 'new'],
    image: 'assets/images/product-set-of-6.jpg',
    images: [
      'assets/images/product-4438043566-0.jpg',
      'assets/images/product-4438043566-1.jpg',
      'assets/images/product-4438043566-2.jpg'
    ],
    url: 'https://www.etsy.com/listing/4438043566/set-of-6-custom-photo-magnets',
    description: "Create a beautiful collection of your most cherished moments with our set of 6 custom photo magnets. Thoughtfully made to preserve memories that deserve to be seen and remembered every day. Includes high-quality photo printing and sturdy magnet backing.",
    available: true
  },
  {
    id: '4438003854',
    title: 'Set of 3 Custom Photo Magnets | Personalized Memory Keepsakes | Gift for Family',
    price: 15.00,
    category: 'custom',
    tags: ['custom', 'family'],
    image: 'assets/images/product-set-of-3.jpg',
    images: [
      'assets/images/product-4438003854-0.jpg',
      'assets/images/product-4438003854-1.jpg',
      'assets/images/product-4438003854-2.jpg'
    ],
    url: 'https://www.etsy.com/listing/4438003854/set-of-3-custom-photo-magnets',
    description: "Create a beautiful collection of your most cherished moments with our set of 3 custom photo magnets. Thoughtfully made to preserve memories that deserve to be seen and remembered every day. Includes high-quality photo printing and sturdy magnet backing.",
    available: true
  }
];

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function formatPrice(price) {
  return '$' + price.toFixed(2);
}

function getBadgeText(product) {
  if (product.tags.includes('bestseller')) return 'Best Seller';
  if (product.tags.includes('new')) return 'New';
  if (product.tags.includes('sale')) return 'Sale';
  return '';
}

function renderProductCard(product) {
  const badge = getBadgeText(product);
  const card = document.createElement('div');
  card.className = 'product-card fade-in';
  card.setAttribute('data-product-id', product.id);
  card.setAttribute('data-category', product.category);

  card.innerHTML = `
    <a href="${escapeHtml(product.url)}" target="_blank" rel="noopener noreferrer" class="product-card-image">
      <img src="${escapeHtml(product.image)}" alt="${escapeHtml(product.title)}" loading="lazy" width="400" height="300">
      ${badge ? `<span class="product-badge">${escapeHtml(badge)}</span>` : ''}
    </a>
    <div class="product-card-body">
      <h3 class="product-card-title">${escapeHtml(product.title)}</h3>
      <div class="product-card-price">${formatPrice(product.price)}</div>
      <a href="${escapeHtml(product.url)}" target="_blank" rel="noopener noreferrer" class="btn btn-primary">
        View on Etsy
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
      </a>
    </div>
  `;

  // Trigger fade-in
  requestAnimationFrame(() => card.classList.add('visible'));
  return card;
}

// Initialize product grid on shop page
function initProductGrid() {
  const grid = document.querySelector('.products-grid');
  if (!grid) return;

  // Check if statically rendered products exist
  const existingCards = grid.querySelectorAll('.product-card');
  if (existingCards.length > 0) return; // Already rendered server-side

  PRODUCTS.forEach(product => {
    if (product.available) {
      grid.appendChild(renderProductCard(product));
    }
  });
}

// Initialize featured products on homepage
function initFeaturedProducts() {
  const grid = document.querySelector('.featured-products-grid');
  if (!grid) return;

  const existingCards = grid.querySelectorAll('.product-card');
  if (existingCards.length > 0) return;

  const featured = PRODUCTS.filter(p => p.available).slice(0, 3);
  featured.forEach(product => {
    grid.appendChild(renderProductCard(product));
  });
}

document.addEventListener('DOMContentLoaded', () => {
  initProductGrid();
  initFeaturedProducts();
});

// Export for use in other scripts
if (typeof window !== 'undefined') {
  window.MemoryLaneProducts = { PRODUCTS, ETSY_SHOP_URL, renderProductCard };
}
