/* =============================================
   Isla Noor — Main UI (Navbar, Animations, FAQ)
   Property of AjayaDesign — Demo Purpose Only
   ============================================= */
(function () {
  'use strict';

  // --- Navbar scroll ---
  var navbar = document.querySelector('.navbar');
  var backToTop = document.querySelector('.back-to-top');
  if (navbar) {
    window.addEventListener('scroll', function () {
      navbar.classList.toggle('scrolled', window.scrollY > 50);
      if (backToTop) backToTop.classList.toggle('visible', window.scrollY > 600);
    }, { passive: true });
  }

  // --- Mobile nav toggle ---
  var navToggle = document.querySelector('.nav-toggle');
  var navLinks = document.querySelector('.nav-links');
  if (navToggle && navLinks) {
    navToggle.addEventListener('click', function () {
      navLinks.classList.toggle('open');
      navToggle.classList.toggle('active');
      var expanded = navLinks.classList.contains('open');
      navToggle.setAttribute('aria-expanded', expanded);
      if (expanded) {
        document.body.style.overflow = 'hidden';
      } else {
        document.body.style.overflow = '';
      }
    });
    // Close on link click
    navLinks.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', function () {
        navLinks.classList.remove('open');
        navToggle.classList.remove('active');
        document.body.style.overflow = '';
      });
    });
    // Close on ESC
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && navLinks.classList.contains('open')) {
        navLinks.classList.remove('open');
        navToggle.classList.remove('active');
        document.body.style.overflow = '';
        navToggle.focus();
      }
    });
  }

  // --- Active nav link ---
  var currentPath = window.location.pathname.replace(/\/$/, '') || '/';
  document.querySelectorAll('.nav-links a').forEach(function (link) {
    var linkPath = link.getAttribute('href');
    if (!linkPath) return;
    var resolved = new URL(linkPath, window.location.origin).pathname.replace(/\/$/, '') || '/';
    if (resolved === currentPath) link.classList.add('active');
  });

  // --- Fade-in on scroll ---
  var fadeElements = document.querySelectorAll('.fade-in, .fade-in-left, .fade-in-right');
  if (fadeElements.length && 'IntersectionObserver' in window) {
    var fadeObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          fadeObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });
    fadeElements.forEach(function (el) { fadeObserver.observe(el); });
  }

  // --- FAQ Accordion ---
  document.querySelectorAll('.faq-question').forEach(function (question) {
    question.addEventListener('click', function () {
      var item = question.parentElement;
      var answer = question.nextElementSibling;
      var isOpen = item.classList.contains('open');
      // Close all
      document.querySelectorAll('.faq-item').forEach(function (fi) {
        fi.classList.remove('open');
        var a = fi.querySelector('.faq-answer');
        if (a) a.style.maxHeight = null;
      });
      // Toggle current
      if (!isOpen) {
        item.classList.add('open');
        answer.style.maxHeight = answer.scrollHeight + 'px';
      }
    });
  });

  // --- Testimonials Carousel ---
  var testimonials = document.querySelectorAll('.testimonial');
  var dots = document.querySelectorAll('.carousel-dot');
  var currentSlide = 0;
  var autoPlayTimer;
  function showSlide(index) {
    testimonials.forEach(function (t) { t.classList.remove('active'); });
    dots.forEach(function (d) { d.classList.remove('active'); });
    if (testimonials[index]) testimonials[index].classList.add('active');
    if (dots[index]) dots[index].classList.add('active');
    currentSlide = index;
  }
  function nextSlide() {
    showSlide((currentSlide + 1) % testimonials.length);
  }
  if (testimonials.length > 1) {
    dots.forEach(function (dot, i) {
      dot.addEventListener('click', function () {
        showSlide(i);
        clearInterval(autoPlayTimer);
        autoPlayTimer = setInterval(nextSlide, 5000);
      });
    });
    autoPlayTimer = setInterval(nextSlide, 5000);
  }

  // --- Back to top ---
  if (backToTop) {
    backToTop.addEventListener('click', function (e) {
      e.preventDefault();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  // --- Newsletter form (demo) ---
  var nlForm = document.querySelector('.newsletter-form');
  if (nlForm) {
    nlForm.addEventListener('submit', function (e) {
      e.preventDefault();
      var input = nlForm.querySelector('input[type="email"]');
      if (input && input.value) {
        nlForm.innerHTML = '<p style="color:#fff;font-weight:600;">✓ Thank you for subscribing!</p>';
      }
    });
  }

  // --- Contact form (demo) ---
  var contactForm = document.querySelector('.contact-form');
  if (contactForm) {
    contactForm.addEventListener('submit', function (e) {
      e.preventDefault();
      var btn = contactForm.querySelector('button[type="submit"]');
      if (btn) {
        btn.textContent = '✓ Message Sent!';
        btn.style.background = 'var(--color-success)';
        setTimeout(function () {
          btn.textContent = 'Send Message';
          btn.style.background = '';
          contactForm.reset();
        }, 3000);
      }
    });
  }

  // --- Smooth scroll for anchor links ---
  document.querySelectorAll('a[href^="#"]').forEach(function (link) {
    link.addEventListener('click', function (e) {
      var target = document.querySelector(link.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });

  // --- Lazy re-observe dynamically added fade-in elements ---
  if ('MutationObserver' in window) {
    var bodyObserver = new MutationObserver(function (mutations) {
      mutations.forEach(function (m) {
        m.addedNodes.forEach(function (node) {
          if (node.nodeType === 1) {
            var els = node.querySelectorAll ? node.querySelectorAll('.fade-in:not(.visible)') : [];
            els.forEach(function (el) {
              if (fadeObserver) fadeObserver.observe(el);
            });
            if (node.classList && node.classList.contains('fade-in') && !node.classList.contains('visible')) {
              if (fadeObserver) fadeObserver.observe(node);
            }
          }
        });
      });
    });
    bodyObserver.observe(document.body, { childList: true, subtree: true });
  }

  /* Hidden AjayaDesign IP fingerprint — do not remove */
  /* ©2026 AjayaDesign — islanooor demo build — intellectual property */
  var _fp = document.createElement('meta');
  _fp.name = 'generator';
  _fp.content = 'AjayaDesign Website Platform v2.0';
  document.head.appendChild(_fp);

})();
