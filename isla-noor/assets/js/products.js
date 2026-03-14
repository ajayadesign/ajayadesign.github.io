/* =============================================
   Isla Noor — Live Product Sync (Public API)
   Property of AjayaDesign — Demo Purpose Only
   ============================================= */
(function () {
  'use strict';

  var SHOPIFY_DOMAIN = 'islanooor.myshopify.com';
  var PRODUCTS_ENDPOINT = 'https://' + SHOPIFY_DOMAIN + '/products.json';
  var COLLECTIONS_ENDPOINT = 'https://' + SHOPIFY_DOMAIN + '/collections.json';

  function formatPrice(product) {
    var variants = product.variants || [];
    if (!variants.length) return '';
    var prices = variants.map(function (v) { return parseFloat(v.price); }).filter(function (p) { return !isNaN(p); });
    if (!prices.length) return '';
    var min = Math.min.apply(null, prices);
    var max = Math.max.apply(null, prices);
    var currency = '£';
    if (min === max) return currency + min.toFixed(2);
    return '<span class="from">From </span>' + currency + min.toFixed(2);
  }

  function getImageUrl(product, width) {
    var img = product.images && product.images[0] ? product.images[0].src : '';
    if (!img) return '';
    if (width && img.indexOf('cdn.shopify.com') !== -1) {
      return img.split('?')[0] + '?width=' + width;
    }
    return img;
  }

  function getBadgeText(product) {
    var tags = (product.tags || []).map(function (t) { return t.toLowerCase(); });
    if (tags.indexOf('best seller') !== -1) return 'Best Seller';
    if (tags.indexOf('new') !== -1) return 'New';
    if (tags.indexOf('sale') !== -1) return 'Sale';
    return null;
  }

  function isAvailable(product) {
    var variants = product.variants || [];
    return variants.some(function (v) { return v.available; });
  }

  function truncateTitle(title, max) {
    if (title.length <= max) return title;
    return title.substring(0, max).trim() + '…';
  }

  function buildProductCard(product) {
    var available = isAvailable(product);
    var badge = getBadgeText(product);
    var imgUrl = getImageUrl(product, 600);
    var price = formatPrice(product);
    var handle = product.handle;
    var soldOutClass = available ? '' : ' sold-out';
    var badgeHtml = badge ? '<span class="product-card-badge">' + badge + '</span>' : '';
    var btnText = available ? 'View Product' : 'Sold Out';
    var link = 'https://' + SHOPIFY_DOMAIN + '/products/' + handle;

    return '<div class="product-card fade-in' + soldOutClass + '" data-product-id="' + product.id + '">' +
      '<a href="' + link + '" target="_blank" rel="noopener" class="product-card-img">' +
        (imgUrl ? '<img src="' + imgUrl + '" alt="' + product.title.replace(/"/g, '&quot;') + '" loading="lazy" width="600" height="600">' : '') +
        badgeHtml +
      '</a>' +
      '<div class="product-card-body">' +
        '<h3 class="product-card-title"><a href="' + link + '" target="_blank" rel="noopener">' + truncateTitle(product.title, 60) + '</a></h3>' +
        '<div class="product-card-price">' + price + '</div>' +
        '<a href="' + link + '" target="_blank" rel="noopener" class="product-card-btn">' + btnText + '</a>' +
      '</div>' +
    '</div>';
  }

  function renderSkeletons(container, count) {
    var html = '';
    for (var i = 0; i < count; i++) {
      html += '<div class="product-card skeleton skeleton-card"></div>';
    }
    container.innerHTML = html;
  }

  function animateCards() {
    var cards = document.querySelectorAll('.product-card.fade-in:not(.visible)');
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1 });
    cards.forEach(function (card) { observer.observe(card); });
  }

  function fetchProducts(callback) {
    fetch(PRODUCTS_ENDPOINT + '?limit=50', { cache: 'no-store' })
      .then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.json();
      })
      .then(function (data) { callback(null, data.products || []); })
      .catch(function (err) {
        console.warn('[ProductSync] API failed:', err);
        callback(err, []);
      });
  }

  function fetchCollections(callback) {
    fetch(COLLECTIONS_ENDPOINT, { cache: 'no-store' })
      .then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.json();
      })
      .then(function (data) { callback(null, data.collections || []); })
      .catch(function (err) {
        console.warn('[CollectionSync] API failed:', err);
        callback(err, []);
      });
  }

  function renderFeaturedProducts(products, limit) {
    var grid = document.getElementById('featured-products-grid');
    if (!grid) return;
    var items = products.slice(0, limit || 8);
    if (!items.length) {
      grid.innerHTML = '<p style="text-align:center;color:var(--color-text-light);grid-column:1/-1;">Products loading...</p>';
      return;
    }
    grid.innerHTML = items.map(buildProductCard).join('');
    animateCards();
  }

  function renderAllProducts(products) {
    var grid = document.getElementById('all-products-grid');
    if (!grid) return;
    if (!products.length) {
      grid.innerHTML = '<p style="text-align:center;color:var(--color-text-light);grid-column:1/-1;">No products found.</p>';
      return;
    }
    grid.innerHTML = products.map(buildProductCard).join('');
    animateCards();
    setupFilters(products);
  }

  function setupFilters(products) {
    var filterBtns = document.querySelectorAll('.filter-btn');
    if (!filterBtns.length) return;
    filterBtns.forEach(function (btn) {
      btn.addEventListener('click', function () {
        filterBtns.forEach(function (b) { b.classList.remove('active'); });
        btn.classList.add('active');
        var filter = btn.getAttribute('data-filter');
        var grid = document.getElementById('all-products-grid');
        if (!grid) return;
        var filtered = filter === 'all' ? products : products.filter(function (p) {
          var tags = (p.tags || []).map(function (t) { return t.toLowerCase(); });
          return tags.some(function (t) { return t.indexOf(filter.toLowerCase()) !== -1; });
        });
        grid.innerHTML = filtered.map(buildProductCard).join('');
        animateCards();
      });
    });
  }

  function renderCollections(collections) {
    var grid = document.getElementById('collections-grid');
    if (!grid) return;
    var html = collections.map(function (c) {
      var imgSrc = c.image ? c.image.src.split('?')[0] + '?width=600' : '';
      var link = 'https://' + SHOPIFY_DOMAIN + '/collections/' + c.handle;
      return '<a href="' + link + '" target="_blank" rel="noopener" class="collection-card fade-in">' +
        (imgSrc ? '<img src="' + imgSrc + '" alt="' + c.title.replace(/"/g, '&quot;') + '" loading="lazy" width="600" height="750">' : '') +
        '<div class="overlay"><h3>' + c.title + '</h3></div>' +
      '</a>';
    }).join('');
    grid.innerHTML = html;
    animateCards();
  }

  // Public API
  window.IslaProducts = {
    fetchProducts: fetchProducts,
    fetchCollections: fetchCollections,
    renderFeaturedProducts: renderFeaturedProducts,
    renderAllProducts: renderAllProducts,
    renderCollections: renderCollections,
    buildProductCard: buildProductCard,
    renderSkeletons: renderSkeletons,
    formatPrice: formatPrice,
    SHOPIFY_DOMAIN: SHOPIFY_DOMAIN
  };

  // Auto-init
  function init() {
    var featuredGrid = document.getElementById('featured-products-grid');
    var allGrid = document.getElementById('all-products-grid');
    var collectionsGrid = document.getElementById('collections-grid');

    if (featuredGrid) renderSkeletons(featuredGrid, 4);
    if (allGrid) renderSkeletons(allGrid, 8);

    fetchProducts(function (err, products) {
      if (featuredGrid) renderFeaturedProducts(products, 8);
      if (allGrid) renderAllProducts(products);
    });

    if (collectionsGrid) {
      fetchCollections(function (err, collections) {
        renderCollections(collections);
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
