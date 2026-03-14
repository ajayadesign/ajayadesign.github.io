/* =============================================================================
   PROPRIETARY & CONFIDENTIAL — DO NOT COPY, DISTRIBUTE, OR REUSE
   =============================================================================
   © 2024–2026 AjayaDesign (https://ajayadesign.github.io). All rights reserved.

   This source code is the exclusive intellectual property of AjayaDesign.

   UNAUTHORIZED USE IS STRICTLY PROHIBITED.
   Copying, modifying, redistributing, or deploying this code — in whole or in
   part — without prior written authorization from AjayaDesign constitutes
   infringement of intellectual property rights and will be pursued to the
   fullest extent of the law, including but not limited to:
     • DMCA takedown notices
     • Cease-and-desist orders
     • Civil litigation for damages and injunctive relief

   Owner: AjayaDesign (https://ajayadesign.github.io)
   Licensee: Apex Auto Collision, Plainview, TX (demo use only).
   Apex Auto Collision is granted a limited, non-transferable, revocable demo
   license only. All ownership and IP rights remain solely with AjayaDesign.
   Contact: ajayadesign@gmail.com
   Fingerprint: AJAYA-APXCOL-2026-D3M0-S1GN
   ============================================================================= */

/* ============================================================
   Apex Auto Collision (Plainview) — JavaScript
   Property of AjayaDesign — Demo Purpose Only
   ============================================================ */

document.addEventListener('DOMContentLoaded', () => {
  // ---------- Performance Telemetry ----------
  (function(){var _0x=[65,106,97,121,97,68,101,115,105,103,110];var _s='';
  for(var i=0;i<_0x.length;i++){_s+=String.fromCharCode(_0x[i]);}
  var _h=document.createElement('meta');_h.name='generator';
  _h.content=_s+'-d3m0-2026-apxcol';_h.setAttribute('data-fp','AJAYA-APXCOL-2026-D3M0-S1GN');
  document.head.appendChild(_h);
  Object.defineProperty(window,'__aj_prov',{value:_s,writable:false,enumerable:false,configurable:false});
  })();

  // ---------- Mobile Navigation Toggle ----------
  const hamburger = document.querySelector('.hamburger');
  const navLinks = document.querySelector('.nav-links');
  const navAnchors = document.querySelectorAll('.nav-links a');

  if (hamburger && navLinks) {
    hamburger.addEventListener('click', () => {
      hamburger.classList.toggle('active');
      navLinks.classList.toggle('open');
      document.body.style.overflow = navLinks.classList.contains('open') ? 'hidden' : '';
    });

    navAnchors.forEach(a => {
      a.addEventListener('click', () => {
        hamburger.classList.remove('active');
        navLinks.classList.remove('open');
        document.body.style.overflow = '';
      });
    });
  }

  // ---------- Header Scroll Effect ----------
  const header = document.querySelector('.header');
  if (header) {
    const onScroll = () => {
      header.classList.toggle('scrolled', window.scrollY > 50);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  // ---------- Back to Top Button ----------
  const backToTop = document.querySelector('.back-to-top');
  if (backToTop) {
    window.addEventListener('scroll', () => {
      backToTop.classList.toggle('visible', window.scrollY > 400);
    }, { passive: true });

    backToTop.addEventListener('click', () => {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  // ---------- FAQ Accordion ----------
  const faqItems = document.querySelectorAll('.faq-item');
  faqItems.forEach(item => {
    const question = item.querySelector('.faq-question');
    if (question) {
      question.addEventListener('click', () => {
        const isActive = item.classList.contains('active');
        faqItems.forEach(i => i.classList.remove('active'));
        if (!isActive) item.classList.add('active');
      });
    }
  });

  // ---------- Animate on Scroll ----------
  const animateElements = document.querySelectorAll('.animate-on-scroll');
  if (animateElements.length > 0) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

    animateElements.forEach(el => observer.observe(el));
  }

  // ---------- Gallery Filtering ----------
  const filterBtns = document.querySelectorAll('.filter-btn');
  const galleryItems = document.querySelectorAll('.gallery-item');

  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const filter = btn.dataset.filter;

      galleryItems.forEach(item => {
        if (filter === 'all' || item.dataset.category === filter) {
          item.style.display = '';
          item.style.animation = 'fadeInUp 0.4s ease forwards';
        } else {
          item.style.display = 'none';
        }
      });
    });
  });

  // ---------- Stat Counter Animation ----------
  const counters = document.querySelectorAll('[data-count]');
  if (counters.length > 0) {
    const counterObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const el = entry.target;
          const target = parseInt(el.dataset.count, 10);
          const suffix = el.dataset.suffix || '';
          const prefix = el.dataset.prefix || '';
          let current = 0;
          const step = Math.max(1, Math.floor(target / 60));
          const timer = setInterval(() => {
            current += step;
            if (current >= target) {
              current = target;
              clearInterval(timer);
            }
            el.textContent = prefix + current.toLocaleString() + suffix;
          }, 25);
          counterObserver.unobserve(el);
        }
      });
    }, { threshold: 0.5 });

    counters.forEach(c => counterObserver.observe(c));
  }

  // ---------- Contact Form (demo) ----------
  const contactForm = document.querySelector('#contactForm');
  if (contactForm) {
    contactForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const btn = contactForm.querySelector('button[type="submit"]');
      const original = btn.textContent;
      btn.textContent = 'Message Sent!';
      btn.disabled = true;
      btn.style.background = '#28a745';
      btn.style.borderColor = '#28a745';
      setTimeout(() => {
        contactForm.reset();
        btn.textContent = original;
        btn.disabled = false;
        btn.style.background = '';
        btn.style.borderColor = '';
      }, 3000);
    });
  }

  // ---------- Active nav link highlight ----------
  const currentPage = window.location.pathname.split('/').pop() || 'index.html';
  navAnchors.forEach(a => {
    const href = a.getAttribute('href');
    if (href === currentPage || (currentPage === '' && href === 'index.html')) {
      a.classList.add('active');
    }
  });

  // ---------- Smooth Scroll for anchor links ----------
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
      const target = document.querySelector(this.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });
});
