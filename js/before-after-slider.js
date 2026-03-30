/**
 * Before/After Image Comparison Slider
 * AjayaDesign © 2026 — Reusable component
 * Usage: <div class="ba-slider" data-before="old.png" data-after="new.png" data-before-label="BEFORE" data-after-label="AFTER"></div>
 * Then call: BeforeAfterSlider.init()
 */
(function () {
  'use strict';

  const CSS = `
    .ba-slider{position:relative;overflow:hidden;border-radius:12px;cursor:col-resize;user-select:none;-webkit-user-select:none;touch-action:none;background:#111;border:1px solid rgba(255,255,255,.08)}
    .ba-slider img{display:block;width:100%;height:auto;pointer-events:none;-webkit-user-drag:none}
    .ba-slider .ba-after{position:absolute;top:0;left:0;width:100%;height:100%;overflow:hidden}
    .ba-slider .ba-after img{position:absolute;top:0;left:0;width:100%;height:100%;object-fit:cover}
    .ba-slider .ba-before-wrap{position:relative;width:100%;height:100%}
    .ba-slider .ba-before-wrap img{width:100%;height:auto;display:block}
    .ba-slider .ba-handle{position:absolute;top:0;width:4px;height:100%;background:#e11d48;z-index:10;transform:translateX(-50%)}
    .ba-slider .ba-handle::before{content:'';position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:44px;height:44px;background:#e11d48;border-radius:50%;border:3px solid #fff;box-shadow:0 2px 12px rgba(0,0,0,.5)}
    .ba-slider .ba-handle::after{content:'⟨ ⟩';position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);color:#fff;font-size:16px;font-weight:700;letter-spacing:6px;z-index:1;white-space:nowrap}
    .ba-slider .ba-label{position:absolute;top:16px;padding:6px 14px;font-size:12px;font-weight:700;letter-spacing:2px;text-transform:uppercase;border-radius:6px;z-index:5;pointer-events:none;font-family:ui-monospace,monospace}
    .ba-slider .ba-label-before{left:16px;background:rgba(239,68,68,.85);color:#fff}
    .ba-slider .ba-label-after{right:16px;background:rgba(16,185,129,.85);color:#fff}
    .ba-slider .ba-overlay{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,.3);z-index:20;transition:opacity .3s;pointer-events:none}
    .ba-slider .ba-overlay span{color:#fff;font-size:14px;font-weight:600;font-family:ui-monospace,monospace;letter-spacing:1px;background:rgba(0,0,0,.6);padding:8px 20px;border-radius:8px}
    .ba-slider.ba-active .ba-overlay{opacity:0}
  `;

  function injectCSS() {
    if (document.getElementById('ba-slider-css')) return;
    const s = document.createElement('style');
    s.id = 'ba-slider-css';
    s.textContent = CSS;
    document.head.appendChild(s);
  }

  function create(el) {
    const beforeSrc = el.dataset.before;
    const afterSrc = el.dataset.after;
    if (!beforeSrc || !afterSrc) return;

    const beforeLabel = el.dataset.beforeLabel || 'BEFORE';
    const afterLabel = el.dataset.afterLabel || 'AFTER';

    el.innerHTML = `
      <div class="ba-before-wrap"><img src="${beforeSrc}" alt="${beforeLabel}" loading="lazy"></div>
      <div class="ba-after"><img src="${afterSrc}" alt="${afterLabel}" loading="lazy"></div>
      <div class="ba-handle"></div>
      <div class="ba-label ba-label-before">${beforeLabel}</div>
      <div class="ba-label ba-label-after">${afterLabel}</div>
      <div class="ba-overlay"><span>↔ Drag to compare</span></div>
    `;

    const afterDiv = el.querySelector('.ba-after');
    const handle = el.querySelector('.ba-handle');
    let pct = 50;
    let bounds;

    function setPosition(p) {
      pct = Math.max(0, Math.min(100, p));
      afterDiv.style.clipPath = `inset(0 0 0 ${pct}%)`;
      handle.style.left = pct + '%';
    }

    function refresh() {
      bounds = el.getBoundingClientRect();
    }

    function move(clientX) {
      if (!bounds) refresh();
      const x = clientX - bounds.left;
      setPosition((x / bounds.width) * 100);
    }

    // Mouse
    el.addEventListener('mousedown', function (e) {
      e.preventDefault();
      el.classList.add('ba-active');
      refresh();
      move(e.clientX);
      function onMove(ev) { move(ev.clientX); }
      function onUp() {
        document.removeEventListener('mousemove', onMove);
        document.removeEventListener('mouseup', onUp);
      }
      document.addEventListener('mousemove', onMove);
      document.addEventListener('mouseup', onUp);
    });

    // Touch
    el.addEventListener('touchstart', function (e) {
      el.classList.add('ba-active');
      refresh();
      move(e.touches[0].clientX);
    }, { passive: true });
    el.addEventListener('touchmove', function (e) {
      e.preventDefault();
      move(e.touches[0].clientX);
    }, { passive: false });

    // Initial
    setPosition(50);

    // Resize observer
    if (window.ResizeObserver) {
      new ResizeObserver(refresh).observe(el);
    }
  }

  window.BeforeAfterSlider = {
    init: function (selector) {
      injectCSS();
      const els = document.querySelectorAll(selector || '.ba-slider');
      els.forEach(create);
    }
  };
})();
