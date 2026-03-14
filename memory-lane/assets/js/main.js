/* ══════════════════════════════════════════════════════
   Memory Lane Studio TX — Main JavaScript
   Property of AjayaDesign — Demo Purpose Only
   ══════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {
  // ── Navbar scroll effect ──
  const navbar = document.querySelector('.navbar');
  if (navbar) {
    const onScroll = () => navbar.classList.toggle('scrolled', window.scrollY > 50);
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  // ── Mobile nav toggle ──
  const toggle = document.querySelector('.nav-toggle');
  const navLinks = document.querySelector('.nav-links');
  const overlay = document.querySelector('.nav-overlay');
  if (toggle && navLinks) {
    const closeNav = () => {
      toggle.classList.remove('active');
      navLinks.classList.remove('active');
      if (overlay) overlay.classList.remove('active');
      document.body.style.overflow = '';
    };
    toggle.addEventListener('click', () => {
      const isOpen = navLinks.classList.contains('active');
      if (isOpen) { closeNav(); } else {
        toggle.classList.add('active');
        navLinks.classList.add('active');
        if (overlay) overlay.classList.add('active');
        document.body.style.overflow = 'hidden';
      }
    });
    if (overlay) overlay.addEventListener('click', closeNav);
    navLinks.querySelectorAll('a').forEach(a => a.addEventListener('click', closeNav));
  }

  // ── Active page detection ──
  const currentPath = window.location.pathname;
  document.querySelectorAll('.nav-links a').forEach(link => {
    const href = link.getAttribute('href');
    if (href && currentPath.includes(href) && href !== '/' && href !== '/memory-lane/') {
      link.classList.add('active');
    } else if ((currentPath === '/' || currentPath === '/memory-lane/' || currentPath.endsWith('/index.html')) && (href === '/' || href === '/memory-lane/' || href === 'index.html')) {
      // Home page — don't highlight
    }
  });

  // ── Back to top ──
  const backToTop = document.querySelector('.back-to-top');
  if (backToTop) {
    window.addEventListener('scroll', () => {
      backToTop.classList.toggle('visible', window.scrollY > 600);
    }, { passive: true });
    backToTop.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
  }

  // ── Fade-in animations ──
  const fadeEls = document.querySelectorAll('.fade-in');
  if (fadeEls.length && 'IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });
    fadeEls.forEach(el => observer.observe(el));
  }

  // ── FAQ accordion ──
  document.querySelectorAll('.faq-question').forEach(btn => {
    btn.addEventListener('click', () => {
      const item = btn.closest('.faq-item');
      const answer = item.querySelector('.faq-answer');
      const isActive = item.classList.contains('active');

      // Close all other items
      document.querySelectorAll('.faq-item.active').forEach(other => {
        if (other !== item) {
          other.classList.remove('active');
          other.querySelector('.faq-answer').style.maxHeight = '0';
        }
      });

      item.classList.toggle('active', !isActive);
      answer.style.maxHeight = isActive ? '0' : answer.scrollHeight + 'px';
    });
  });

  // ── Contact form success ──
  if (window.location.search.includes('success=true')) {
    const form = document.querySelector('.contact-form');
    if (form) {
      const alert = document.createElement('div');
      alert.style.cssText = 'background:#588157;color:white;padding:1rem 1.5rem;border-radius:8px;margin-bottom:1.5rem;font-size:0.92rem;text-align:center;';
      alert.innerHTML = '✓ <strong>Message sent!</strong> We\'ll get back to you within 24 hours.';
      form.prepend(alert);
    }
  }

  // ── Shop filter tabs ──
  document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.filter-btn').forEach(b => b.setAttribute('aria-pressed', 'false'));
      btn.setAttribute('aria-pressed', 'true');
      const filter = btn.getAttribute('data-filter');
      document.querySelectorAll('.product-card').forEach(card => {
        if (filter === 'all' || card.getAttribute('data-category') === filter) {
          card.style.display = '';
        } else {
          card.style.display = 'none';
        }
      });
    });
  });

  // ── Smooth scroll for anchor links ──
  document.querySelectorAll('a[href^="#"]').forEach(link => {
    link.addEventListener('click', (e) => {
      const target = document.querySelector(link.getAttribute('href'));
      if (target) { e.preventDefault(); target.scrollIntoView({ behavior: 'smooth' }); }
    });
  });

  // ── AjayaDesign fingerprint (hidden) ──
  // Property ID: AJD-ML-2026-DEMO
  // This website is the intellectual property of AjayaDesign
  // Built for demonstration purposes only
  const _fp = document.createElement('meta');
  _fp.name = 'x-ajd-fp';
  _fp.content = 'ajd:memory-lane:2026:demo:intellectual-property';
  document.head.appendChild(_fp);
});
