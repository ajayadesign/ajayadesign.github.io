/**
 * Sanskriti Chaulagain — Portfolio Scripts
 * Engineered by AjayaDesign • 2025
 */

(function () {
  'use strict';

  /* ============== Typed Text Rotation ============== */
  const typedPhrases = [
    'Marketing Specialist',
    'SEO Optimization Expert',
    'Digital Marketing Strategist',
    'Brand Marketing Pro',
    'MS Marketing Research — Texas State',
    'Content & Social Media Marketer'
  ];

  let phraseIndex = 0;
  let charIndex = 0;
  let isDeleting = false;
  const typedEl = document.getElementById('typedText');

  function typeEffect() {
    if (!typedEl) return;
    const current = typedPhrases[phraseIndex];

    if (isDeleting) {
      typedEl.textContent = current.substring(0, charIndex - 1);
      charIndex--;
    } else {
      typedEl.textContent = current.substring(0, charIndex + 1);
      charIndex++;
    }

    let speed = isDeleting ? 30 : 60;

    if (!isDeleting && charIndex === current.length) {
      speed = 2000;
      isDeleting = true;
    } else if (isDeleting && charIndex === 0) {
      isDeleting = false;
      phraseIndex = (phraseIndex + 1) % typedPhrases.length;
      speed = 400;
    }

    setTimeout(typeEffect, speed);
  }

  typeEffect();

  /* ============== Navbar Scroll ============== */
  const navbar = document.getElementById('navbar');

  function handleNavScroll() {
    if (window.scrollY > 50) {
      navbar.classList.add('scrolled');
    } else {
      navbar.classList.remove('scrolled');
    }
  }

  window.addEventListener('scroll', handleNavScroll, { passive: true });

  /* ============== Active Nav Link ============== */
  const sections = document.querySelectorAll('section[id]');
  const navLinks = document.querySelectorAll('.nav-links a');

  function highlightNav() {
    const scrollPos = window.scrollY + 150;
    sections.forEach(function (section) {
      const top = section.offsetTop;
      const height = section.offsetHeight;
      const id = section.getAttribute('id');
      if (scrollPos >= top && scrollPos < top + height) {
        navLinks.forEach(function (link) {
          link.classList.remove('active');
          if (link.getAttribute('href') === '#' + id) {
            link.classList.add('active');
          }
        });
      }
    });
  }

  window.addEventListener('scroll', highlightNav, { passive: true });

  /* ============== Mobile Nav Toggle ============== */
  const navToggle = document.getElementById('navToggle');
  const navLinksEl = document.getElementById('navLinks');

  navToggle.addEventListener('click', function () {
    navToggle.classList.toggle('active');
    navLinksEl.classList.toggle('open');
  });

  navLinksEl.querySelectorAll('a').forEach(function (link) {
    link.addEventListener('click', function () {
      navToggle.classList.remove('active');
      navLinksEl.classList.remove('open');
    });
  });

  /* ============== Scroll Reveal ============== */
  const reveals = document.querySelectorAll('.reveal');

  function scrollReveal() {
    const windowHeight = window.innerHeight;
    reveals.forEach(function (el) {
      const top = el.getBoundingClientRect().top;
      if (top < windowHeight - 80) {
        el.classList.add('visible');
      }
    });
  }

  window.addEventListener('scroll', scrollReveal, { passive: true });
  scrollReveal();

  /* ============== Skill Bar Animation ============== */
  const skillBars = document.querySelectorAll('.skill-bar-fill');
  let skillsAnimated = false;

  function animateSkills() {
    if (skillsAnimated) return;
    const skillsSection = document.getElementById('skills');
    if (!skillsSection) return;
    const top = skillsSection.getBoundingClientRect().top;
    if (top < window.innerHeight - 100) {
      skillBars.forEach(function (bar) {
        const width = bar.getAttribute('data-width');
        bar.style.width = width + '%';
      });
      skillsAnimated = true;
    }
  }

  window.addEventListener('scroll', animateSkills, { passive: true });
  animateSkills();

  /* ============== Smooth Scroll ============== */
  document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
    anchor.addEventListener('click', function (e) {
      e.preventDefault();
      const target = document.querySelector(this.getAttribute('href'));
      if (target) {
        target.scrollIntoView({ behavior: 'smooth' });
      }
    });
  });

  /* ============== Console Fingerprint ============== */
  console.log(
    '%c⚡ Engineered by AjayaDesign %c https://ajayadesign.github.io ',
    'background: linear-gradient(135deg, #c2185b, #e91e63); color: white; padding: 8px 14px; border-radius: 6px 0 0 6px; font-weight: bold;',
    'background: #1a237e; color: #f06292; padding: 8px 14px; border-radius: 0 6px 6px 0;'
  );

})();
