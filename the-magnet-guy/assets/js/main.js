/**
 * The Magnet Guy — Main JavaScript
 * A property of AjayaDesign — Demo Purpose Only
 * ─────────────────────────────────────────────────
 */

(function () {
  'use strict';

  /* ─── Config ──────────────────────────────────────────── */
  const SHOPIFY_DOMAIN = 'themagnetguy.com';
  const PRODUCTS_JSON  = `https://${SHOPIFY_DOMAIN}/products.json`;

  /* ─── DOM Refs ────────────────────────────────────────── */
  const header      = document.querySelector('.header');
  const mobileBtn   = document.querySelector('.mobile-toggle');
  const navList     = document.querySelector('.header__nav-list');
  const cartDrawer  = document.querySelector('.cart-drawer');
  const cartOverlay = document.querySelector('.cart-drawer__overlay');
  const cartBtn     = document.querySelector('.header__cart-btn');
  const cartClose   = document.querySelector('.cart-drawer__close');
  const cartCount   = document.querySelector('.header__cart-count');
  const cartItems   = document.querySelector('.cart-drawer__items');
  const cartTotal   = document.querySelector('.cart-total-amount');
  const toast       = document.querySelector('.toast');

  /* ─── State ───────────────────────────────────────────── */
  let cart = JSON.parse(localStorage.getItem('tmg_cart') || '[]');

  /* ─── Header Scroll ───────────────────────────────────── */
  if (header) {
    let lastY = 0;
    window.addEventListener('scroll', () => {
      const y = window.scrollY;
      if (y > 50) header.classList.add('scrolled');
      else header.classList.remove('scrolled');
      lastY = y;
    }, { passive: true });
  }

  /* ─── Mobile Navigation ───────────────────────────────── */
  if (mobileBtn && navList) {
    // Create overlay dynamically
    let overlay = document.querySelector('.mobile-nav-overlay');
    if (!overlay) {
      overlay = document.createElement('div');
      overlay.className = 'mobile-nav-overlay';
      document.body.appendChild(overlay);
    }

    function openMobileNav() {
      mobileBtn.classList.add('open');
      navList.classList.add('open');
      overlay.classList.add('open');
      document.body.style.overflow = 'hidden';
      mobileBtn.setAttribute('aria-expanded', 'true');
    }

    function closeMobileNav() {
      mobileBtn.classList.remove('open');
      navList.classList.remove('open');
      overlay.classList.remove('open');
      document.body.style.overflow = '';
      mobileBtn.setAttribute('aria-expanded', 'false');
    }

    mobileBtn.addEventListener('click', () => {
      if (navList.classList.contains('open')) closeMobileNav();
      else openMobileNav();
    });

    // Close when clicking a link
    navList.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', closeMobileNav);
    });

    // Close when clicking the backdrop
    overlay.addEventListener('click', closeMobileNav);
  }

  /* ─── Cart Drawer ─────────────────────────────────────── */
  function openCart() {
    if (cartDrawer) cartDrawer.classList.add('open');
    if (cartOverlay) cartOverlay.classList.add('open');
    document.body.style.overflow = 'hidden';
  }

  function closeCart() {
    if (cartDrawer) cartDrawer.classList.remove('open');
    if (cartOverlay) cartOverlay.classList.remove('open');
    document.body.style.overflow = '';
  }

  if (cartBtn) cartBtn.addEventListener('click', openCart);
  if (cartClose) cartClose.addEventListener('click', closeCart);
  if (cartOverlay) cartOverlay.addEventListener('click', closeCart);

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeCart();
  });

  function saveCart() {
    localStorage.setItem('tmg_cart', JSON.stringify(cart));
  }

  function updateCartUI() {
    const count = cart.reduce((s, i) => s + i.qty, 0);
    if (cartCount) {
      cartCount.textContent = count;
      cartCount.style.display = count > 0 ? 'flex' : 'none';
    }

    if (!cartItems) return;

    if (cart.length === 0) {
      cartItems.innerHTML = `
        <div class="cart-empty">
          <div class="cart-empty__icon">🛒</div>
          <p>Your cart is empty</p>
          <a href="/the-magnet-guy/shop/" class="btn btn-primary btn-sm" style="margin-top:1rem">Browse Products</a>
        </div>`;
      if (cartTotal) cartTotal.textContent = '$0.00';
      return;
    }

    cartItems.innerHTML = cart.map((item, i) => `
      <div class="cart-item">
        <div class="cart-item__image">
          <div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;font-size:1.5rem">📸</div>
        </div>
        <div class="cart-item__info">
          <div class="cart-item__title">${escapeHtml(item.title)}</div>
          <div class="cart-item__variant">${escapeHtml(item.variant || '')}</div>
          <div class="cart-item__price">$${(item.price * item.qty).toFixed(2)}</div>
          <div class="cart-item__qty">
            <button onclick="window.TMG.updateQty(${i}, -1)" aria-label="Decrease quantity">−</button>
            <span>${item.qty}</span>
            <button onclick="window.TMG.updateQty(${i}, 1)" aria-label="Increase quantity">+</button>
            <button onclick="window.TMG.removeItem(${i})" style="margin-left:auto;color:#e74c3c;font-size:0.8rem" aria-label="Remove item">Remove</button>
          </div>
        </div>
      </div>`).join('');

    const total = cart.reduce((s, i) => s + (i.price * i.qty), 0);
    if (cartTotal) cartTotal.textContent = '$' + total.toFixed(2);
  }

  function addToCart(title, price, variant) {
    const existing = cart.find(i => i.title === title && i.variant === variant);
    if (existing) {
      existing.qty++;
    } else {
      cart.push({ title, price: parseFloat(price), variant, qty: 1 });
    }
    saveCart();
    updateCartUI();
    openCart();
    showToast(`${title} added to cart!`);
  }

  function updateQty(index, delta) {
    if (!cart[index]) return;
    cart[index].qty += delta;
    if (cart[index].qty <= 0) cart.splice(index, 1);
    saveCart();
    updateCartUI();
  }

  function removeItem(index) {
    cart.splice(index, 1);
    saveCart();
    updateCartUI();
  }

  /* ─── Toast ───────────────────────────────────────────── */
  function showToast(message) {
    if (!toast) return;
    toast.textContent = message;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 3000);
  }

  /* ─── Escape HTML ─────────────────────────────────────── */
  function escapeHtml(str) {
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  /* ─── Fetch Products from Shopify ─────────────────────── */
  async function fetchProducts() {
    const grid = document.getElementById('product-grid');
    if (!grid) return;

    grid.innerHTML = '<div class="spinner"></div>';

    try {
      const res = await fetch(PRODUCTS_JSON);
      if (!res.ok) throw new Error('Network error');
      const data = await res.json();
      const products = data.products || [];
      renderProducts(products, grid);
    } catch (err) {
      console.error('Product fetch failed:', err);
      grid.innerHTML = renderFallbackProducts();
    }
  }

  function renderProducts(products, grid) {
    if (products.length === 0) {
      grid.innerHTML = '<p style="text-align:center;color:var(--color-text-muted)">No products available right now.</p>';
      return;
    }

    grid.innerHTML = products.map(p => {
      const minPrice = p.variants && p.variants.length > 0
        ? Math.min(...p.variants.map(v => parseFloat(v.price)))
        : 0;
      const maxPrice = p.variants && p.variants.length > 0
        ? Math.max(...p.variants.map(v => parseFloat(v.price)))
        : 0;
      const priceDisplay = minPrice === maxPrice
        ? `$${minPrice.toFixed(2)}`
        : `<span class="from">From </span>$${minPrice.toFixed(2)}`;
      const firstVariant = p.variants && p.variants[0] ? p.variants[0] : null;
      const imgPlaceholder = p.product_type === 'Photo Magnets' ? '📸' : '🎁';

      return `
        <div class="product-card fade-in">
          <div class="product-card__image">
            <div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;font-size:4rem;background:linear-gradient(135deg,#FDF8F0,#E8E0D0)">${imgPlaceholder}</div>
            ${p.variants && p.variants.length > 1 ? `<span class="product-card__badge">${p.variants.length} Options</span>` : ''}
          </div>
          <div class="product-card__body">
            <h3 class="product-card__title">${escapeHtml(p.title)}</h3>
            <div class="product-card__price">${priceDisplay}</div>
            ${renderVariantChips(p.variants)}
            <div class="product-card__actions">
              <button class="btn btn-primary btn-sm" style="flex:1"
                onclick="window.TMG.addToCart('${escapeHtml(p.title).replace(/'/g, "\\'")}', ${firstVariant ? firstVariant.price : minPrice}, '${firstVariant ? escapeHtml(firstVariant.title).replace(/'/g, "\\'") : 'Default'}')"
              >Add to Cart</button>
              <a href="https://${SHOPIFY_DOMAIN}/products/${encodeURIComponent(p.handle)}" target="_blank" rel="noopener" class="btn btn-outline btn-sm">View</a>
            </div>
          </div>
        </div>`;
    }).join('');

    observeFadeIn();
  }

  function renderVariantChips(variants) {
    if (!variants || variants.length <= 1) return '';
    return `<div class="product-card__variants">${variants.slice(0, 5).map(v =>
      `<span class="variant-chip">${escapeHtml(v.title)}</span>`
    ).join('')}${variants.length > 5 ? `<span class="variant-chip">+${variants.length - 5}</span>` : ''}</div>`;
  }

  function renderFallbackProducts() {
    const fallback = [
      { title: '2x2 Photo Magnet', price: '4.99', variants: ['Single', '6 Pack', '12 Pack', '36 Pack', '48 Pack', '100 Pack'], icon: '📸', type: 'Photo Magnets' },
      { title: 'Gift Card – The Magnet Guy', price: '20.00', variants: ['$20', '$30', '$50', '$100', '$200'], icon: '🎁', type: 'Gift Card' }
    ];
    return fallback.map(p => `
      <div class="product-card fade-in visible">
        <div class="product-card__image">
          <div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;font-size:4rem;background:linear-gradient(135deg,#FDF8F0,#E8E0D0)">${p.icon}</div>
          <span class="product-card__badge">${p.variants.length} Options</span>
        </div>
        <div class="product-card__body">
          <h3 class="product-card__title">${p.title}</h3>
          <div class="product-card__price"><span class="from">From </span>$${p.price}</div>
          <div class="product-card__variants">${p.variants.map(v => `<span class="variant-chip">${v}</span>`).join('')}</div>
          <div class="product-card__actions">
            <a href="https://${SHOPIFY_DOMAIN}/products/2x2-photo-magnet" target="_blank" rel="noopener" class="btn btn-primary btn-sm" style="flex:1">Shop on Shopify</a>
          </div>
        </div>
      </div>`).join('');
  }

  /* ─── FAQ Accordion ───────────────────────────────────── */
  function initFAQ() {
    document.querySelectorAll('.faq-question').forEach(btn => {
      btn.addEventListener('click', () => {
        const item = btn.closest('.faq-item');
        const wasOpen = item.classList.contains('open');
        // Close all
        document.querySelectorAll('.faq-item').forEach(i => i.classList.remove('open'));
        if (!wasOpen) item.classList.add('open');
      });
    });
  }

  /* ─── Scroll Animations ───────────────────────────────── */
  function observeFadeIn() {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1 });

    document.querySelectorAll('.fade-in:not(.visible)').forEach(el => observer.observe(el));
  }

  /* ─── Active Nav Link ─────────────────────────────────── */
  function setActiveNav() {
    const path = window.location.pathname;
    document.querySelectorAll('.header__nav-link').forEach(link => {
      const href = link.getAttribute('href');
      if (href === path || (href !== '/the-magnet-guy/' && path.startsWith(href))) {
        link.classList.add('active');
      }
    });
  }

  /* ─── Newsletter Form ─────────────────────────────────── */
  function initNewsletter() {
    document.querySelectorAll('.newsletter-form').forEach(form => {
      form.addEventListener('submit', (e) => {
        e.preventDefault();
        const email = form.querySelector('input[type="email"]');
        if (email && email.value) {
          showToast('Thanks for subscribing! 🎉');
          email.value = '';
        }
      });
    });
  }

  /* ─── Contact Form ────────────────────────────────────── */
  function initContactForm() {
    const form = document.getElementById('contact-form');
    if (!form) return;
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      showToast('Message sent! We\'ll get back to you soon. 📬');
      form.reset();
    });
  }

  /* ─── Expose Global API ───────────────────────────────── */
  window.TMG = {
    addToCart,
    updateQty,
    removeItem,
    openCart,
    closeCart
  };

  /* ─── Init ────────────────────────────────────────────── */
  document.addEventListener('DOMContentLoaded', () => {
    updateCartUI();
    fetchProducts();
    initFAQ();
    observeFadeIn();
    setActiveNav();
    initNewsletter();
    initContactForm();
  });

})();
