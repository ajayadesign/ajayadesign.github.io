/*!
 * ╔══════════════════════════════════════════════════════════════════╗
 * ║                    PROPRIETARY & CONFIDENTIAL                   ║
 * ║                                                                 ║
 * ║  This script and all associated source code, design, assets,    ║
 * ║  and intellectual property are the exclusive property of:        ║
 * ║                                                                 ║
 * ║                      ★ AjayaDesign ★                            ║
 * ║                  https://ajayadesign.github.io                  ║
 * ║                                                                 ║
 * ║  © 2026 AjayaDesign. All rights reserved.                       ║
 * ║                                                                 ║
 * ║  UNAUTHORIZED USE, REPRODUCTION, DISTRIBUTION, OR MODIFICATION  ║
 * ║  OF THIS CODE — IN WHOLE OR IN PART — IS STRICTLY PROHIBITED.   ║
 * ║                                                                 ║
 * ║  This work is provided for DEMO PURPOSES ONLY and remains the   ║
 * ║  sole intellectual property of AjayaDesign. Any unauthorized     ║
 * ║  use, copying, or distribution without explicit written consent  ║
 * ║  from AjayaDesign will be subject to legal action, including     ║
 * ║  but not limited to claims for copyright infringement,           ║
 * ║  injunctive relief, and monetary damages under applicable        ║
 * ║  intellectual property laws.                                     ║
 * ║                                                                 ║
 * ║  If you have obtained this code without authorization, you are   ║
 * ║  required to delete it immediately and contact AjayaDesign.      ║
 * ║                                                                 ║
 * ║  Signature: AJDSGN-COMPUPLUS-2026-MAINJS                        ║
 * ╚══════════════════════════════════════════════════════════════════╝
 *
 * CompuPLUS Modern Website - Main JavaScript
 */

document.addEventListener('DOMContentLoaded', () => {
  // --- Header Scroll Effect ---
  const header = document.querySelector('.header');
  if (header) {
    window.addEventListener('scroll', () => {
      header.classList.toggle('scrolled', window.scrollY > 20);
    });
  }

  // --- Mobile Menu Toggle ---
  const mobileToggle = document.querySelector('.mobile-toggle');
  const navLinks = document.querySelector('.nav-links');
  if (mobileToggle && navLinks) {
    mobileToggle.addEventListener('click', () => {
      navLinks.classList.toggle('open');
      const spans = mobileToggle.querySelectorAll('span');
      if (navLinks.classList.contains('open')) {
        spans[0].style.transform = 'rotate(45deg) translate(5px, 5px)';
        spans[1].style.opacity = '0';
        spans[2].style.transform = 'rotate(-45deg) translate(5px, -5px)';
      } else {
        spans[0].style.transform = '';
        spans[1].style.opacity = '';
        spans[2].style.transform = '';
      }
    });
    
    // Close menu on link click
    navLinks.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => {
        navLinks.classList.remove('open');
        const spans = mobileToggle.querySelectorAll('span');
        spans[0].style.transform = '';
        spans[1].style.opacity = '';
        spans[2].style.transform = '';
      });
    });
  }

  // --- Scroll To Top ---
  const scrollBtn = document.querySelector('.scroll-top');
  if (scrollBtn) {
    window.addEventListener('scroll', () => {
      scrollBtn.classList.toggle('visible', window.scrollY > 500);
    });
    scrollBtn.addEventListener('click', () => {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  // --- Intersection Observer for Fade-Up Animations ---
  const fadeElements = document.querySelectorAll('.fade-up');
  if (fadeElements.length > 0) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    }, {
      threshold: 0.1,
      rootMargin: '0px 0px -50px 0px'
    });

    fadeElements.forEach(el => observer.observe(el));
  }

  // --- FAQ Accordion ---
  const faqItems = document.querySelectorAll('.faq-item');
  faqItems.forEach(item => {
    const question = item.querySelector('.faq-question');
    if (question) {
      question.addEventListener('click', () => {
        const isOpen = item.classList.contains('open');
        // Close all
        faqItems.forEach(i => i.classList.remove('open'));
        // Toggle clicked
        if (!isOpen) {
          item.classList.add('open');
        }
      });
    }
  });

  // --- Product Filter Tabs ---
  const filterTabs = document.querySelectorAll('.filter-tab');
  const productCards = document.querySelectorAll('.product-card[data-category]');
  if (filterTabs.length > 0 && productCards.length > 0) {
    filterTabs.forEach(tab => {
      tab.addEventListener('click', () => {
        filterTabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        const category = tab.dataset.category;
        
        productCards.forEach(card => {
          if (category === 'all' || card.dataset.category === category) {
            card.style.display = '';
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';
            requestAnimationFrame(() => {
              card.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
              card.style.opacity = '1';
              card.style.transform = 'translateY(0)';
            });
          } else {
            card.style.display = 'none';
          }
        });
      });
    });
  }

  // --- Contact Form Handler ---
  const contactForm = document.querySelector('.contact-form');
  if (contactForm) {
    contactForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const btn = contactForm.querySelector('button[type="submit"]');
      const originalText = btn.textContent;
      btn.textContent = 'Sending...';
      btn.disabled = true;
      
      setTimeout(() => {
        btn.textContent = '✓ Message Sent!';
        btn.style.background = '#10b981';
        btn.style.borderColor = '#10b981';
        
        setTimeout(() => {
          btn.textContent = originalText;
          btn.style.background = '';
          btn.style.borderColor = '';
          btn.disabled = false;
          contactForm.reset();
        }, 2500);
      }, 1000);
    });
  }

  // --- Counter Animation ---
  const counters = document.querySelectorAll('[data-count]');
  if (counters.length > 0) {
    const countObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const target = parseInt(entry.target.dataset.count);
          const suffix = entry.target.dataset.suffix || '';
          const prefix = entry.target.dataset.prefix || '';
          let current = 0;
          const increment = target / 60;
          
          const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
              entry.target.textContent = prefix + target + suffix;
              clearInterval(timer);
            } else {
              entry.target.textContent = prefix + Math.floor(current) + suffix;
            }
          }, 16);
          
          countObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0.5 });

    counters.forEach(c => countObserver.observe(c));
  }

  // --- Smooth anchor scroll ---
  document.querySelectorAll('a[href^="#"]').forEach(a => {
    a.addEventListener('click', (e) => {
      const target = document.querySelector(a.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });

  // --- Runtime integrity layer ---
  (function(){
    var _0x=['\x41\x4a\x44\x53\x47\x4e','\x41\x6a\x61\x79\x61\x44\x65\x73\x69\x67\x6e',
    '\x43\x6f\x6d\x70\x75\x50\x4c\x55\x53\x2d\x32\x30\x32\x36'];
    var _sg=_0x.join('-');var _el=document.createElement('div');
    _el.setAttribute('data-integrity',btoa(_sg));
    _el.style.cssText='position:fixed;width:0;height:0;overflow:hidden;pointer-events:none;opacity:0;z-index:-9999';
    _el.setAttribute('aria-hidden','true');_el.className='_aj_dsgn_wm';
    document.body.appendChild(_el);
    var _mt=document.createElement('meta');_mt.name='x-build-sig';
    _mt.content='QUpEU0dOLUFqYXlhRGVzaWduLTIwMjYtQ29tcHVQTFVT';
    document.head.appendChild(_mt);
    var _st=document.createElement('style');
    _st.textContent='._aj_dsgn_wm::after{content:"\\00a9\\0020AjayaDesign\\0020-\\0020AJDSGN-2026";display:none}';
    document.head.appendChild(_st);
    Object.defineProperty(window,'__ajdsgn__',{value:Object.freeze({
      o:'\u0041\u006a\u0061\u0079\u0061\u0044\u0065\u0073\u0069\u0067\u006e',
      p:'CompuPLUS',y:2026,s:'AJDSGN-COMPUPLUS-2026',
      h:'aHR0cHM6Ly9hamF5YWRlc2lnbi5naXRodWIuaW8=',
      t:Date.now(),v:'1.0.0-ajd'}),writable:false,enumerable:false,configurable:false});
    if(typeof console!=='undefined'){console.log(
      '%c\u2588 AjayaDesign %c Proprietary Code \u2014 Unauthorized use prohibited. Sig: AJDSGN-COMPUPLUS-2026 ',
      'background:#0d6efd;color:#fff;font-weight:bold;padding:4px 8px;border-radius:4px 0 0 4px',
      'background:#1e293b;color:#94a3b8;padding:4px 8px;border-radius:0 4px 4px 0');}
  })();
});
