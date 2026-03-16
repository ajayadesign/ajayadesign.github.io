/* Magnetic Soul — Core JS */
(function () {
  'use strict';

  /* --- Sticky Nav Scroll Effect --- */
  const nav = document.querySelector('.nav');
  if (nav) {
    let ticking = false;
    window.addEventListener('scroll', function () {
      if (!ticking) {
        requestAnimationFrame(function () {
          nav.classList.toggle('scrolled', window.scrollY > 40);
          ticking = false;
        });
        ticking = true;
      }
    });
  }

  /* --- Mobile Nav Toggle --- */
  const toggle = document.querySelector('.nav-toggle');
  const links = document.querySelector('.nav-links');
  if (toggle && links) {
    toggle.setAttribute('aria-expanded', 'false');
    toggle.addEventListener('click', function () {
      const open = links.classList.toggle('open');
      toggle.setAttribute('aria-expanded', String(open));
    });
  }

  /* --- Tab System --- */
  document.querySelectorAll('.tab-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      const tabGroup = btn.closest('.section') || document;
      tabGroup.querySelectorAll('.tab-btn').forEach(function (b) {
        b.classList.remove('active');
        b.setAttribute('aria-selected', 'false');
      });
      btn.classList.add('active');
      btn.setAttribute('aria-selected', 'true');
      const target = btn.getAttribute('data-tab');
      tabGroup.querySelectorAll('[data-tab-content]').forEach(function (panel) {
        panel.style.display = panel.getAttribute('data-tab-content') === target ? '' : 'none';
      });
    });
  });

  /* --- FAQ Accordion --- */
  document.querySelectorAll('.faq-question').forEach(function (q) {
    q.addEventListener('click', function () {
      q.closest('.faq-item').classList.toggle('open');
    });
  });

  /* --- Scroll Reveal --- */
  var reveals = document.querySelectorAll('.reveal');
  if (reveals.length && 'IntersectionObserver' in window) {
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1 });
    reveals.forEach(function (el) { observer.observe(el); });
  }

  /* --- Contact Form Validation --- */
  var form = document.getElementById('contact-form');
  if (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var valid = true;
      form.querySelectorAll('[required]').forEach(function (input) {
        var errorEl = input.parentElement.querySelector('.form-error');
        if (!input.value.trim()) {
          valid = false;
          if (errorEl) { errorEl.style.display = 'block'; }
          input.style.borderColor = '#e53e3e';
        } else {
          if (errorEl) { errorEl.style.display = 'none'; }
          input.style.borderColor = '';
        }
      });
      var emailInput = form.querySelector('input[type="email"]');
      if (emailInput && emailInput.value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailInput.value)) {
        valid = false;
        var errorEl = emailInput.parentElement.querySelector('.form-error');
        if (errorEl) {
          errorEl.textContent = 'Please enter a valid email address.';
          errorEl.style.display = 'block';
        }
        emailInput.style.borderColor = '#e53e3e';
      }
      if (valid) {
        form.style.opacity = '0';
        form.style.transition = 'opacity 400ms ease-out';
        setTimeout(function () {
          form.style.display = 'none';
          var success = document.querySelector('.form-success');
          if (success) { success.classList.add('visible'); }
        }, 400);
      }
    });
  }

  /* --- Keyboard Shortcuts --- */
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      document.querySelectorAll('.faq-item.open').forEach(function (item) {
        item.classList.remove('open');
      });
      var navLinks = document.querySelector('.nav-links');
      if (navLinks && navLinks.classList.contains('open')) {
        navLinks.classList.remove('open');
        var tog = document.querySelector('.nav-toggle');
        if (tog) { tog.setAttribute('aria-expanded', 'false'); }
      }
    }
  });
})();
