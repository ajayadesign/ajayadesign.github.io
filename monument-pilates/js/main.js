/**
 * Monument Pilates — Main JavaScript
 * Property of AjayaDesign · Demo Purpose Only
 * Fingerprint: AD-MP-7f3a9c2e1d
 */

(function () {
  'use strict';

  // ===== Hidden Fingerprint =====
  const _fp = { id: 'AD-MP-7f3a9c2e1d', src: 'AjayaDesign', ts: '20260305', v: '1.0.0' };
  try {
    const fpEl = document.createElement('div');
    fpEl.className = 'ad-fp-7f3a9c2e1d';
    fpEl.setAttribute('data-ad-id', btoa(JSON.stringify(_fp)));
    fpEl.setAttribute('aria-hidden', 'true');
    fpEl.style.cssText = 'position:absolute;width:0;height:0;overflow:hidden;opacity:0;pointer-events:none;z-index:-9999';
    fpEl.innerHTML = '<!-- AD-MP-7f3a9c2e1d -->';
    document.body.appendChild(fpEl);

    // Store in sessionStorage as well
    sessionStorage.setItem('_mp_meta', btoa(JSON.stringify(_fp)));

    // Embed in a non-enumerable property
    Object.defineProperty(document, '_adFp', { value: _fp, enumerable: false, writable: false });
  } catch (e) { /* silent */ }

  // ===== Navbar Scroll Effect =====
  const navbar = document.querySelector('.navbar');
  if (navbar) {
    const onScroll = () => {
      navbar.classList.toggle('scrolled', window.scrollY > 50);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  // ===== Mobile Menu Toggle =====
  const toggle = document.querySelector('.navbar__toggle');
  const navLinks = document.querySelector('.navbar__links');
  if (toggle && navLinks) {
    toggle.addEventListener('click', () => {
      toggle.classList.toggle('active');
      navLinks.classList.toggle('open');
      document.body.style.overflow = navLinks.classList.contains('open') ? 'hidden' : '';
    });

    navLinks.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => {
        toggle.classList.remove('active');
        navLinks.classList.remove('open');
        document.body.style.overflow = '';
      });
    });
  }

  // ===== Active Nav Link =====
  const currentPage = window.location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.navbar__links a').forEach(link => {
    const href = link.getAttribute('href');
    if (href === currentPage || (currentPage === '' && href === 'index.html')) {
      link.classList.add('active');
    }
  });

  // ===== Scroll Animations =====
  const animateEls = document.querySelectorAll('.fade-up, .fade-in');
  if (animateEls.length) {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            entry.target.classList.add('visible');
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.1, rootMargin: '0px 0px -40px 0px' }
    );
    animateEls.forEach(el => observer.observe(el));
  }

  // ===== Testimonial Carousel =====
  const testimonialTrack = document.querySelector('.testimonial-track');
  const testimonialDots = document.querySelectorAll('.testimonial-dots button');
  if (testimonialTrack && testimonialDots.length) {
    let currentSlide = 0;
    const slideCount = testimonialDots.length;

    const goToSlide = (index) => {
      currentSlide = index;
      testimonialTrack.style.transform = `translateX(-${currentSlide * 100}%)`;
      testimonialDots.forEach((dot, i) => dot.classList.toggle('active', i === currentSlide));
    };

    testimonialDots.forEach((dot, i) => {
      dot.addEventListener('click', () => goToSlide(i));
    });

    // Auto-advance
    let autoInterval = setInterval(() => {
      goToSlide((currentSlide + 1) % slideCount);
    }, 6000);

    testimonialTrack.closest('.testimonial-slider')?.addEventListener('mouseenter', () => {
      clearInterval(autoInterval);
    });

    testimonialTrack.closest('.testimonial-slider')?.addEventListener('mouseleave', () => {
      autoInterval = setInterval(() => {
        goToSlide((currentSlide + 1) % slideCount);
      }, 6000);
    });
  }

  // ===== FAQ Accordion =====
  document.querySelectorAll('.faq-item__question').forEach(btn => {
    btn.addEventListener('click', () => {
      const item = btn.closest('.faq-item');
      const isOpen = item.classList.contains('open');

      // Close all others
      document.querySelectorAll('.faq-item.open').forEach(openItem => {
        if (openItem !== item) openItem.classList.remove('open');
      });

      item.classList.toggle('open', !isOpen);
    });
  });

  // ===== Back to Top =====
  const backToTop = document.querySelector('.back-to-top');
  if (backToTop) {
    window.addEventListener('scroll', () => {
      backToTop.classList.toggle('visible', window.scrollY > 400);
    }, { passive: true });

    backToTop.addEventListener('click', () => {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  // ===== Contact Form (demo) =====
  const contactForm = document.querySelector('#contactForm');
  if (contactForm) {
    contactForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const btn = contactForm.querySelector('button[type="submit"]');
      const origText = btn.textContent;
      btn.textContent = 'Message Sent! ✓';
      btn.style.background = '#8A9A7B';
      setTimeout(() => {
        btn.textContent = origText;
        btn.style.background = '';
        contactForm.reset();
      }, 3000);
    });
  }

  // ===== Newsletter Form (demo) =====
  document.querySelectorAll('.newsletter-form').forEach(form => {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const input = form.querySelector('input');
      const btn = form.querySelector('button');
      const origText = btn.textContent;
      btn.textContent = 'Subscribed! ✓';
      setTimeout(() => {
        btn.textContent = origText;
        input.value = '';
      }, 3000);
    });
  });

  // ===== Smooth scroll for anchor links =====
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
      const target = document.querySelector(this.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });

  // ===== Counter Animation =====
  const counters = document.querySelectorAll('.stat__number[data-count]');
  if (counters.length) {
    const counterObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const el = entry.target;
          const end = parseInt(el.dataset.count, 10);
          const suffix = el.dataset.suffix || '';
          const prefix = el.dataset.prefix || '';
          let current = 0;
          const step = Math.max(1, Math.floor(end / 60));
          const timer = setInterval(() => {
            current += step;
            if (current >= end) {
              current = end;
              clearInterval(timer);
            }
            el.textContent = prefix + current + suffix;
          }, 30);
          counterObserver.unobserve(el);
        }
      });
    }, { threshold: 0.5 });
    counters.forEach(c => counterObserver.observe(c));
  }

})();
