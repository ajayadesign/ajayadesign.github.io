/* ═══════════════════════════════════════════════
   AjayaDesign — Main JavaScript
   ═══════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {

  // ── Footer Year ──
  document.getElementById('footer-year').textContent = new Date().getFullYear();

  // ── Mobile Menu Toggle ──
  const menuBtn   = document.getElementById('mobile-menu-btn');
  const mobileMenu = document.getElementById('mobile-menu');
  const iconOpen   = document.getElementById('menu-icon-open');
  const iconClose  = document.getElementById('menu-icon-close');

  menuBtn.addEventListener('click', () => {
    mobileMenu.classList.toggle('hidden');
    iconOpen.classList.toggle('hidden');
    iconClose.classList.toggle('hidden');
  });

  // Close mobile menu on link click
  mobileMenu.querySelectorAll('a').forEach(link => {
    link.addEventListener('click', () => {
      mobileMenu.classList.add('hidden');
      iconOpen.classList.remove('hidden');
      iconClose.classList.add('hidden');
    });
  });

  // ── Scroll Reveal (IntersectionObserver) ──
  const revealObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        revealObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.15 });

  document.querySelectorAll('.reveal').forEach(el => revealObserver.observe(el));

  // ── Navbar Shrink on Scroll ──
  const navbar = document.getElementById('navbar');
  window.addEventListener('scroll', () => {
    if (window.scrollY > 50) {
      navbar.classList.add('py-0');
    } else {
      navbar.classList.remove('py-0');
    }
  });

  // ── Intake Form Submission ──
  // Hook ID: #ajayadesign-intake-form
  // Replace the TODO fetch() with your Oracle VM + OpenClaw automation endpoint.
  const intakeForm = document.getElementById('ajayadesign-intake-form');

  intakeForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const formData = new FormData(intakeForm);
    const data = Object.fromEntries(formData.entries());
    console.log('[AjayaDesign] Intake submission:', data);

    // Visual feedback — spinner
    const btn = intakeForm.querySelector('button[type="submit"]');
    const originalHTML = btn.innerHTML;
    btn.innerHTML = `
      <svg class="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
      Processing...
    `;
    btn.disabled = true;

    // Visual feedback — success after delay
    setTimeout(() => {
      btn.innerHTML = `
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
        Build Initiated — We'll be in touch.
      `;
      btn.classList.remove('bg-amd-red', 'hover:bg-red-700');
      btn.classList.add('bg-green-600');
    }, 1500);

    // TODO: POST data to your automation endpoint
    // fetch('https://your-oracle-vm.example.com/api/intake', {
    //   method: 'POST',
    //   headers: { 'Content-Type': 'application/json' },
    //   body: JSON.stringify(data),
    // });
  });

});
