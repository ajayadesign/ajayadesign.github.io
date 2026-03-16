/* =============================================
   Ankita Dahal — Portfolio Scripts
   Engineered by AjayaDesign — 2026
   ============================================= */

(function () {
  'use strict';

  // ==================== NAVBAR ====================
  const navbar = document.getElementById('navbar');
  const navToggle = document.getElementById('navToggle');
  const navLinks = document.getElementById('navLinks');

  window.addEventListener('scroll', function () {
    navbar.classList.toggle('scrolled', window.scrollY > 60);
  });

  navToggle.addEventListener('click', function () {
    navLinks.classList.toggle('open');
  });

  // Close mobile menu on link click
  navLinks.querySelectorAll('a').forEach(function (link) {
    link.addEventListener('click', function () {
      navLinks.classList.remove('open');
    });
  });

  // ==================== TYPING EFFECT ====================
  var phrases = [
    'Aspiring Registered Nurse',
    'Nursing Student at ACC',
    'Passionate About Patient Care',
    'Healthcare Advocate',
    'Future RN — Austin, TX'
  ];
  var typedEl = document.getElementById('typedText');
  var phraseIdx = 0;
  var charIdx = 0;
  var isDeleting = false;
  var typeSpeed = 80;

  function typeLoop() {
    var current = phrases[phraseIdx];
    if (isDeleting) {
      typedEl.textContent = current.substring(0, charIdx - 1);
      charIdx--;
      typeSpeed = 40;
    } else {
      typedEl.textContent = current.substring(0, charIdx + 1);
      charIdx++;
      typeSpeed = 80;
    }

    if (!isDeleting && charIdx === current.length) {
      typeSpeed = 2000;
      isDeleting = true;
    } else if (isDeleting && charIdx === 0) {
      isDeleting = false;
      phraseIdx = (phraseIdx + 1) % phrases.length;
      typeSpeed = 400;
    }

    setTimeout(typeLoop, typeSpeed);
  }

  if (typedEl) typeLoop();

  // ==================== SCROLL REVEAL ====================
  var revealEls = document.querySelectorAll('.reveal');
  var observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.15, rootMargin: '0px 0px -40px 0px' });

  revealEls.forEach(function (el) {
    observer.observe(el);
  });

  // ==================== ACTIVE NAV LINK ====================
  var sections = document.querySelectorAll('section[id]');

  function updateActiveNav() {
    var scrollY = window.scrollY + 200;

    // Clear all active states
    document.querySelectorAll('.nav-links a').forEach(function (a) {
      a.classList.remove('active');
    });

    // Find the last section whose top is at or above the scroll position
    var current = null;
    sections.forEach(function (section) {
      if (section.offsetTop <= scrollY) {
        current = section;
      }
    });

    if (current) {
      var link = document.querySelector('.nav-links a[href="#' + current.getAttribute('id') + '"]');
      if (link) link.classList.add('active');
    }
  }

  window.addEventListener('scroll', updateActiveNav);
  window.addEventListener('hashchange', function () {
    setTimeout(updateActiveNav, 50);
  });
  // Run once on load
  setTimeout(updateActiveNav, 100);

})();
