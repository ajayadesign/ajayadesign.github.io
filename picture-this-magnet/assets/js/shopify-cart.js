/* ============================================
   PictureThisMagnet — Shopify Cart (Cart API)
   ============================================ */
(function () {
  'use strict';

  /* ---------- Config ---------- */
  const SHOPIFY_DOMAIN   = 'picturethismagnet.myshopify.com';
  const STOREFRONT_TOKEN = 'c73d9977cea4de359541b1e865590b18';
  const API_VERSION      = '2025-01';
  const CART_STORAGE_KEY = 'picturethismagnet_cart_id';

  const GQL = `https://${SHOPIFY_DOMAIN}/api/${API_VERSION}/graphql.json`;
  const headers = {
    'Content-Type': 'application/json',
    'X-Shopify-Storefront-Access-Token': STOREFRONT_TOKEN,
  };

  /* ---------- State ---------- */
  let cartId    = localStorage.getItem(CART_STORAGE_KEY) || null;
  let cartLines = [];

  /* ---------- DOM refs ---------- */
  const drawer       = document.getElementById('cart-drawer');
  const overlay      = document.getElementById('cart-overlay');
  const itemsWrap    = document.getElementById('cart-items');
  const emptyState   = document.getElementById('cart-empty');
  const footer       = document.getElementById('cart-footer');
  const subtotalEl   = document.getElementById('cart-subtotal');
  const checkoutBtn  = document.getElementById('cart-checkout-btn');
  const badge        = document.querySelector('.cart-badge');
  const closeBtn     = document.querySelector('.cart-close');

  /* ---------- Custom product modal ---------- */
  const customModalOverlay = document.getElementById('custom-cart-modal-overlay');
  const customModalClose   = document.getElementById('custom-cart-modal-close');
  const customModalCancel  = document.getElementById('custom-cart-modal-cancel');
  const CUSTOM_PRODUCT_HANDLES = ['photo-magnets', 'bulk-1-image'];

  function isCustomProduct(handle) {
    return CUSTOM_PRODUCT_HANDLES.includes(handle);
  }

  function showCustomModal(handle) {
    if (!customModalOverlay) return;
    const link = customModalOverlay.querySelector('.custom-cart-modal-proceed');
    if (link) link.href = `https://${SHOPIFY_DOMAIN}/products/${handle}`;
    customModalOverlay.classList.add('open');
    document.body.style.overflow = 'hidden';
    const closeModal = () => {
      customModalOverlay.classList.remove('open');
      document.body.style.overflow = '';
    };
    if (customModalClose) customModalClose.onclick = closeModal;
    if (customModalCancel)  customModalCancel.onclick  = closeModal;
    customModalOverlay.addEventListener('click', function handler(e) {
      if (e.target === customModalOverlay) {
        closeModal();
        customModalOverlay.removeEventListener('click', handler);
      }
    });
  }

  /* ---------- GraphQL helpers ---------- */
  async function gqlFetch(query, variables) {
    const res = await fetch(GQL, {
      method: 'POST',
      headers,
      body: JSON.stringify({ query, variables }),
    });
    if (!res.ok) throw new Error(`Shopify API ${res.status}`);
    const json = await res.json();
    if (json.errors) throw new Error(json.errors[0].message);
    return json.data;
  }

  /* Cart mutations */
  const CART_CREATE = `
    mutation cartCreate($input: CartInput!) {
      cartCreate(input: $input) {
        cart { id checkoutUrl lines(first:50){ edges { node {
          id quantity
          merchandise { ... on ProductVariant { id title price { amount currencyCode }
            product { title handle featuredImage { url } } } }
        } } } cost { subtotalAmount { amount currencyCode } } }
        userErrors { field message }
      }
    }`;

  const CART_LINES_ADD = `
    mutation cartLinesAdd($cartId: ID!, $lines: [CartLineInput!]!) {
      cartLinesAdd(cartId: $cartId, lines: $lines) {
        cart { id checkoutUrl lines(first:50){ edges { node {
          id quantity
          merchandise { ... on ProductVariant { id title price { amount currencyCode }
            product { title handle featuredImage { url } } } }
        } } } cost { subtotalAmount { amount currencyCode } } }
        userErrors { field message }
      }
    }`;

  const CART_LINES_UPDATE = `
    mutation cartLinesUpdate($cartId: ID!, $lines: [CartLineUpdateInput!]!) {
      cartLinesUpdate(cartId: $cartId, lines: $lines) {
        cart { id checkoutUrl lines(first:50){ edges { node {
          id quantity
          merchandise { ... on ProductVariant { id title price { amount currencyCode }
            product { title handle featuredImage { url } } } }
        } } } cost { subtotalAmount { amount currencyCode } } }
        userErrors { field message }
      }
    }`;

  const CART_LINES_REMOVE = `
    mutation cartLinesRemove($cartId: ID!, $lineIds: [ID!]!) {
      cartLinesRemove(cartId: $cartId, lineIds: $lineIds) {
        cart { id checkoutUrl lines(first:50){ edges { node {
          id quantity
          merchandise { ... on ProductVariant { id title price { amount currencyCode }
            product { title handle featuredImage { url } } } }
        } } } cost { subtotalAmount { amount currencyCode } } }
        userErrors { field message }
      }
    }`;

  const CART_QUERY = `
    query cartQuery($cartId: ID!) {
      cart(id: $cartId) {
        id checkoutUrl lines(first:50){ edges { node {
          id quantity
          merchandise { ... on ProductVariant { id title price { amount currencyCode }
            product { title handle featuredImage { url } } } }
        } } } cost { subtotalAmount { amount currencyCode } }
      }
    }`;

  /* ---------- Cart operations ---------- */
  function parseCart(cart) {
    if (!cart) return;
    cartId = cart.id;
    localStorage.setItem(CART_STORAGE_KEY, cartId);
    cartLines = cart.lines.edges.map(e => e.node);
    renderCart(cart);
  }

  async function loadCart() {
    if (!cartId) { renderCart(null); return; }
    try {
      const data = await gqlFetch(CART_QUERY, { cartId });
      if (data.cart) { parseCart(data.cart); return; }
    } catch (_) { /* cart expired */ }
    localStorage.removeItem(CART_STORAGE_KEY);
    cartId = null;
    renderCart(null);
  }

  async function addToCart(variantGid, quantity) {
    quantity = quantity || 1;
    try {
      let data;
      if (!cartId) {
        data = await gqlFetch(CART_CREATE, { input: { lines: [{ merchandiseId: variantGid, quantity }] } });
        parseCart(data.cartCreate.cart);
      } else {
        data = await gqlFetch(CART_LINES_ADD, { cartId, lines: [{ merchandiseId: variantGid, quantity }] });
        parseCart(data.cartLinesAdd.cart);
      }
      openDrawer();
    } catch (err) {
      console.error('Add to cart failed:', err);
    }
  }

  async function updateLine(lineId, quantity) {
    if (!cartId) return;
    try {
      if (quantity <= 0) {
        const data = await gqlFetch(CART_LINES_REMOVE, { cartId, lineIds: [lineId] });
        parseCart(data.cartLinesRemove.cart);
      } else {
        const data = await gqlFetch(CART_LINES_UPDATE, { cartId, lines: [{ id: lineId, quantity }] });
        parseCart(data.cartLinesUpdate.cart);
      }
    } catch (err) {
      console.error('Update cart failed:', err);
    }
  }

  /* ---------- Render cart drawer ---------- */
  function renderCart(cart) {
    if (!itemsWrap) return;
    const lines = cart ? cart.lines.edges.map(e => e.node) : [];
    const count = lines.reduce((s, l) => s + l.quantity, 0);

    // Badge
    if (badge) {
      if (count > 0) {
        badge.textContent = count;
        badge.style.display = 'flex';
        badge.classList.remove('pop');
        void badge.offsetWidth;
        badge.classList.add('pop');
      } else {
        badge.style.display = 'none';
      }
    }

    if (lines.length === 0) {
      itemsWrap.innerHTML = '';
      if (emptyState) emptyState.style.display = 'block';
      if (footer) footer.style.display = 'none';
      return;
    }

    if (emptyState) emptyState.style.display = 'none';
    if (footer) footer.style.display = 'block';

    const subtotal = cart.cost.subtotalAmount;
    if (subtotalEl) subtotalEl.textContent = formatMoney(subtotal.amount, subtotal.currencyCode);
    if (checkoutBtn) checkoutBtn.href = cart.checkoutUrl;

    itemsWrap.innerHTML = lines.map(line => {
      const m = line.merchandise;
      const img = m.product.featuredImage
        ? `<img class="cart-item-img" src="${escapeAttr(m.product.featuredImage.url)}" alt="${escapeAttr(m.product.title)}" width="60" height="60" loading="lazy">`
        : `<div class="cart-item-img cart-item-img-placeholder" style="width:60px;height:60px"><svg width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="m21 15-5-5L5 21"/></svg></div>`;
      const price = parseFloat(m.price.amount) * line.quantity;
      return `
        <div class="cart-item" data-line-id="${escapeAttr(line.id)}">
          ${img}
          <div class="cart-item-details">
            <p class="cart-item-title">${escapeHtml(m.product.title)}</p>
            ${m.title !== 'Default Title' ? `<p class="cart-item-variant">${escapeHtml(m.title)}</p>` : ''}
            <div class="cart-item-qty">
              <button class="qty-btn qty-minus" aria-label="Decrease quantity" data-line="${escapeAttr(line.id)}" data-qty="${line.quantity - 1}">&minus;</button>
              <span class="qty-value">${line.quantity}</span>
              <button class="qty-btn qty-plus" aria-label="Increase quantity" data-line="${escapeAttr(line.id)}" data-qty="${line.quantity + 1}">+</button>
            </div>
          </div>
          <div class="cart-item-right">
            <span class="cart-item-price">${formatMoney(price, m.price.currencyCode)}</span>
            <button class="cart-item-remove" aria-label="Remove item" data-line="${escapeAttr(line.id)}">
              <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><line x1="4" y1="4" x2="12" y2="12"/><line x1="12" y1="4" x2="4" y2="12"/></svg>
            </button>
          </div>
        </div>`;
    }).join('');

    // Quantity & remove listeners
    itemsWrap.querySelectorAll('.qty-btn').forEach(btn => {
      btn.addEventListener('click', () => updateLine(btn.dataset.line, parseInt(btn.dataset.qty, 10)));
    });
    itemsWrap.querySelectorAll('.cart-item-remove').forEach(btn => {
      btn.addEventListener('click', () => updateLine(btn.dataset.line, 0));
    });
  }

  /* ---------- Drawer open / close ---------- */
  let previousFocus = null;

  function openDrawer() {
    if (!drawer) return;
    previousFocus = document.activeElement;
    drawer.classList.add('open');
    if (overlay) overlay.classList.add('open');
    document.body.style.overflow = 'hidden';
    trapFocus(drawer);
  }

  function closeDrawer() {
    if (!drawer) return;
    drawer.classList.remove('open');
    if (overlay) overlay.classList.remove('open');
    document.body.style.overflow = '';
    if (previousFocus) previousFocus.focus();
  }

  function trapFocus(el) {
    const focusable = el.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
    if (focusable.length) focusable[0].focus();
    el.addEventListener('keydown', function trap(e) {
      if (e.key === 'Escape') { closeDrawer(); el.removeEventListener('keydown', trap); return; }
      if (e.key !== 'Tab') return;
      const first = focusable[0], last = focusable[focusable.length - 1];
      if (e.shiftKey) { if (document.activeElement === first) { e.preventDefault(); last.focus(); } }
      else { if (document.activeElement === last) { e.preventDefault(); first.focus(); } }
    });
  }

  /* ---------- Helpers ---------- */
  function formatMoney(amount, currency) {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: currency || 'USD' }).format(amount);
  }

  function escapeHtml(str) {
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
  }

  function escapeAttr(str) {
    return String(str).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#39;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  /* ---------- Event listeners ---------- */
  if (closeBtn) closeBtn.addEventListener('click', closeDrawer);
  if (overlay)  overlay.addEventListener('click', closeDrawer);

  document.querySelectorAll('.cart-toggle').forEach(btn => {
    btn.addEventListener('click', (e) => { e.preventDefault(); openDrawer(); });
  });

  /* Add-to-cart buttons (click) */
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-variant-id]');
    if (!btn) return;
    e.preventDefault();

    const handle = btn.dataset.productHandle;
    if (handle && isCustomProduct(handle)) {
      showCustomModal(handle);
      return;
    }

    const vid = btn.dataset.variantId;
    if (!vid) return;

    btn.classList.add('adding');
    const origText = btn.textContent;
    btn.textContent = 'Adding…';

    addToCart(vid, 1).finally(() => {
      btn.classList.remove('adding');
      btn.textContent = origText;
    });
  });

  /* ---------- Init ---------- */
  loadCart();

  /* Expose for PDP variant pickers etc. */
  window.ShopifyCart = { addToCart, openDrawer, closeDrawer };
})();
