/* ═══════════════════════════════════════════════
   Everest Phones — Main JavaScript
   Built by AjayaDesign (https://ajayadesign.github.io)
   Build ID: EP-2026-0307-AD | Demo Only
   ═══════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {

  // ── Mobile Menu Toggle ──
  const menuBtn = document.getElementById('mobile-menu-btn');
  const mobileMenu = document.getElementById('mobile-menu');
  const iconOpen = document.getElementById('mob-icon-open');
  const iconClose = document.getElementById('mob-icon-close');

  if (menuBtn && mobileMenu) {
    menuBtn.addEventListener('click', () => {
      mobileMenu.classList.toggle('hidden');
      iconOpen.classList.toggle('hidden');
      iconClose.classList.toggle('hidden');
    });
    mobileMenu.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => {
        mobileMenu.classList.add('hidden');
        iconOpen.classList.remove('hidden');
        iconClose.classList.add('hidden');
      });
    });
  }

  // ── Scroll Reveal ──
  const revealEls = document.querySelectorAll('.reveal');
  if (revealEls.length) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });
    revealEls.forEach(el => observer.observe(el));
  }

  // ── Navbar shrink on scroll ──
  const navbar = document.getElementById('navbar');
  if (navbar) {
    window.addEventListener('scroll', () => {
      navbar.classList.toggle('shadow-md', window.scrollY > 50);
    }, { passive: true });
  }

  // ── FAQ Accordion ──
  const faqBtns = document.querySelectorAll('.faq-toggle');
  faqBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const answer = btn.nextElementSibling;
      const chevron = btn.querySelector('.faq-chevron');
      const isOpen = answer.classList.contains('open');

      // Close all others
      document.querySelectorAll('.faq-answer.open').forEach(a => {
        a.classList.remove('open');
        a.previousElementSibling.querySelector('.faq-chevron').classList.remove('open');
      });

      if (!isOpen) {
        answer.classList.add('open');
        chevron.classList.add('open');
      }
    });
  });

  // ── Report Carousel ──
  const track = document.querySelector('.carousel-track');
  const prevBtn = document.getElementById('carousel-prev');
  const nextBtn = document.getElementById('carousel-next');
  const dots = document.querySelectorAll('.carousel-dot');

  if (track && prevBtn && nextBtn) {
    let currentSlide = 0;
    const slides = track.querySelectorAll('.carousel-slide');
    const totalSlides = slides.length;

    function goToSlide(n) {
      currentSlide = ((n % totalSlides) + totalSlides) % totalSlides;
      track.style.transform = `translateX(-${currentSlide * 100}%)`;
      dots.forEach((d, i) => {
        d.classList.toggle('bg-ev-teal', i === currentSlide);
        d.classList.toggle('bg-gray-300', i !== currentSlide);
      });
    }

    prevBtn.addEventListener('click', () => goToSlide(currentSlide - 1));
    nextBtn.addEventListener('click', () => goToSlide(currentSlide + 1));
    dots.forEach((dot, i) => dot.addEventListener('click', () => goToSlide(i)));

    // Auto-advance every 5 seconds
    setInterval(() => goToSlide(currentSlide + 1), 5000);
  }

  // ── Contact Form ──
  const contactForm = document.getElementById('contact-form');
  if (contactForm) {
    contactForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const btn = contactForm.querySelector('button[type="submit"]');
      const originalHTML = btn.innerHTML;
      btn.innerHTML = '<svg class="w-5 h-5 animate-spin mx-auto" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>';
      btn.disabled = true;

      setTimeout(() => {
        btn.innerHTML = '✓ Message Sent!';
        btn.classList.remove('bg-ev-teal');
        btn.classList.add('bg-green-600');
      }, 1500);
    });
  }

});
