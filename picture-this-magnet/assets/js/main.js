/* ============================================
   PictureThisMagnet — Main UI Script
   ============================================ */
(function () {
  'use strict';

  /* ---------- Navbar scroll ---------- */
  const navbar = document.querySelector('.navbar');
  if (navbar) {
    const onScroll = () => {
      navbar.classList.toggle('scrolled', window.scrollY > 50);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  /* ---------- Mobile nav ---------- */
  const navToggle  = document.querySelector('.nav-toggle');
  const navLinks   = document.querySelector('.nav-links');
  const navOverlay = document.querySelector('.nav-overlay');

  function toggleNav() {
    const open = navLinks.classList.toggle('open');
    navToggle.classList.toggle('active', open);
    if (navOverlay) navOverlay.classList.toggle('active', open);
    document.body.style.overflow = open ? 'hidden' : '';
    navToggle.setAttribute('aria-expanded', open);
  }

  if (navToggle && navLinks) {
    navToggle.addEventListener('click', toggleNav);
    if (navOverlay) navOverlay.addEventListener('click', toggleNav);
    navLinks.querySelectorAll('a:not(.cart-toggle)').forEach(a =>
      a.addEventListener('click', () => {
        if (navLinks.classList.contains('open')) toggleNav();
      })
    );
  }

  /* ---------- Active nav link ---------- */
  const currentPath = window.location.pathname.replace(/\/$/, '') || '/';
  document.querySelectorAll('.nav-links a[href]').forEach(a => {
    const href = a.getAttribute('href').replace(/\/$/, '') || '/';
    if (href === currentPath || (href !== '/' && currentPath.startsWith(href))) {
      a.classList.add('active');
    }
  });

  /* ---------- Intersection Observer animations ---------- */
  const animEls = document.querySelectorAll('.fade-in, .fade-in-left, .fade-in-right, .stagger-children');
  if (animEls.length && 'IntersectionObserver' in window) {
    const observer = new IntersectionObserver(
      entries => entries.forEach(e => {
        if (e.isIntersecting) {
          e.target.classList.add('visible');
          observer.unobserve(e.target);
        }
      }),
      { threshold: 0.15, rootMargin: '0px 0px -50px 0px' }
    );
    animEls.forEach(el => observer.observe(el));
  } else {
    animEls.forEach(el => el.classList.add('visible'));
  }

  /* ---------- FAQ Accordion ---------- */
  document.querySelectorAll('.faq-question').forEach(btn => {
    btn.addEventListener('click', () => {
      const item = btn.closest('.faq-item');
      const answer = item.querySelector('.faq-answer');
      const isOpen = item.classList.contains('active');

      // Close all
      document.querySelectorAll('.faq-item.active').forEach(open => {
        open.classList.remove('active');
        const a = open.querySelector('.faq-answer');
        if (a) a.style.maxHeight = '0';
      });

      if (!isOpen && answer) {
        item.classList.add('active');
        answer.style.maxHeight = answer.scrollHeight + 'px';
      }

      btn.setAttribute('aria-expanded', !isOpen);
    });
  });

  /* ---------- Back to Top ---------- */
  const btt = document.querySelector('.back-to-top');
  if (btt) {
    window.addEventListener('scroll', () => {
      btt.classList.toggle('visible', window.scrollY > 600);
    }, { passive: true });
    btt.addEventListener('click', () => {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  /* ---------- Newsletter Popup ---------- */
  const popup        = document.querySelector('.popup-overlay');
  const popupClose   = popup && popup.querySelector('.popup-close');
  const POPUP_KEY    = 'ptm_popup_seen';

  function closePopup() {
    if (!popup) return;
    popup.classList.remove('active');
    document.body.style.overflow = '';
    sessionStorage.setItem(POPUP_KEY, '1');
  }

  if (popup && !sessionStorage.getItem(POPUP_KEY)) {
    setTimeout(() => {
      popup.classList.add('active');
    }, 15000);
  }
  if (popupClose) popupClose.addEventListener('click', closePopup);
  if (popup) popup.addEventListener('click', e => { if (e.target === popup) closePopup(); });

  /* ---------- Marquee pause on hover ---------- */
  document.querySelectorAll('.marquee-inner').forEach(el => {
    el.addEventListener('mouseenter', () => { el.style.animationPlayState = 'paused'; });
    el.addEventListener('mouseleave', () => { el.style.animationPlayState = 'running'; });
  });

  /* ---------- Number counters ---------- */
  function animateCounters() {
    document.querySelectorAll('[data-count]').forEach(el => {
      const target = parseInt(el.dataset.count, 10);
      if (isNaN(target)) return;
      const duration = 2000;
      const start = performance.now();
      function step(now) {
        const progress = Math.min((now - start) / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        el.textContent = Math.floor(eased * target).toLocaleString() + (el.dataset.suffix || '');
        if (progress < 1) requestAnimationFrame(step);
      }
      requestAnimationFrame(step);
    });
  }

  const counterEls = document.querySelectorAll('[data-count]');
  if (counterEls.length && 'IntersectionObserver' in window) {
    const cObserver = new IntersectionObserver(entries => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          animateCounters();
          cObserver.disconnect();
        }
      });
    }, { threshold: 0.3 });
    counterEls.forEach(el => cObserver.observe(el));
  }
})();
