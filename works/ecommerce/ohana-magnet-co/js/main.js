/* Ohana Magnet Co — Main JavaScript */
(function() {
  'use strict';

  /* --- Mobile Nav Toggle --- */
  const navToggle = document.querySelector('.nav-toggle');
  const navLinks = document.querySelector('.nav-links');

  if (navToggle && navLinks) {
    navToggle.addEventListener('click', function() {
      navToggle.classList.toggle('active');
      navLinks.classList.toggle('open');
      document.body.style.overflow = navLinks.classList.contains('open') ? 'hidden' : '';
    });

    // Close mobile nav on link click
    navLinks.querySelectorAll('a:not(.nav-dropdown > a)').forEach(function(link) {
      link.addEventListener('click', function() {
        navToggle.classList.remove('active');
        navLinks.classList.remove('open');
        document.body.style.overflow = '';
      });
    });
  }

  /* --- Mobile Dropdown Toggle --- */
  document.querySelectorAll('.nav-dropdown > a').forEach(function(trigger) {
    trigger.addEventListener('click', function(e) {
      if (window.innerWidth <= 768) {
        e.preventDefault();
        trigger.parentElement.classList.toggle('open');
      }
    });
  });

  /* --- Nav scroll effect --- */
  var nav = document.querySelector('.site-nav');
  if (nav) {
    window.addEventListener('scroll', function() {
      nav.classList.toggle('scrolled', window.scrollY > 20);
    }, { passive: true });
  }

  /* --- Contact Form Validation --- */
  var contactForm = document.getElementById('contact-form');
  if (contactForm) {
    contactForm.addEventListener('submit', function(e) {
      e.preventDefault();
      var valid = true;
      var fields = contactForm.querySelectorAll('[required]');

      fields.forEach(function(field) {
        var errorEl = field.parentElement.querySelector('.form-error');
        if (!field.value.trim()) {
          valid = false;
          field.style.borderColor = 'var(--color-error)';
          if (errorEl) errorEl.style.display = 'block';
        } else if (field.type === 'email' && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(field.value)) {
          valid = false;
          field.style.borderColor = 'var(--color-error)';
          if (errorEl) {
            errorEl.textContent = 'Please enter a valid email address';
            errorEl.style.display = 'block';
          }
        } else {
          field.style.borderColor = '';
          if (errorEl) errorEl.style.display = 'none';
        }
      });

      if (valid) {
        contactForm.style.display = 'none';
        var success = document.querySelector('.form-success');
        if (success) success.style.display = 'block';
      }
    });

    // Clear error on input
    contactForm.querySelectorAll('[required]').forEach(function(field) {
      field.addEventListener('input', function() {
        field.style.borderColor = '';
        var errorEl = field.parentElement.querySelector('.form-error');
        if (errorEl) errorEl.style.display = 'none';
      });
    });
  }

  /* --- Newsletter Form --- */
  document.querySelectorAll('.newsletter-form').forEach(function(form) {
    form.addEventListener('submit', function(e) {
      e.preventDefault();
      var input = form.querySelector('input[type="email"]');
      if (input && input.value.trim() && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(input.value)) {
        input.value = '';
        var btn = form.querySelector('button');
        if (btn) {
          var orig = btn.textContent;
          btn.textContent = 'Subscribed ✓';
          btn.disabled = true;
          setTimeout(function() {
            btn.textContent = orig;
            btn.disabled = false;
          }, 3000);
        }
      }
    });
  });

  /* --- Scroll animations --- */
  if ('IntersectionObserver' in window) {
    var observer = new IntersectionObserver(function(entries) {
      entries.forEach(function(entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('animate-in');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1 });

    document.querySelectorAll('.product-card, .feature-card, .testimonial-card, .step-card').forEach(function(el) {
      observer.observe(el);
    });
  }

  /* --- Escape to close mobile nav --- */
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && navLinks && navLinks.classList.contains('open')) {
      navToggle.classList.remove('active');
      navLinks.classList.remove('open');
      document.body.style.overflow = '';
    }
  });

})();
