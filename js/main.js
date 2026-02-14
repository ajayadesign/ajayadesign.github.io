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
  // Dual-send: FormSubmit.co (email — always works) + n8n (automation pipeline).
  // n8n only fires when browsing from the same machine running Docker.
  // From production (GitHub Pages), n8n silently fails and email still delivers.
  const N8N_WEBHOOK = 'http://localhost:5678/webhook/ajayadesign-intake';
  const FORMSUBMIT_URL = 'https://formsubmit.co/ajax/9dc23f5c5eb6fba941487190ff80294b';
  const N8N_TIMEOUT_MS = 3000; // fail fast from production
  const intakeForm = document.getElementById('ajayadesign-intake-form');

  intakeForm.addEventListener('submit', async (e) => {
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

    // Send to all three: Firebase (DB) + FormSubmit (email) + n8n (automation)
    const emailPayload = new FormData(intakeForm);
    emailPayload.append('_subject', 'New AjayaDesign Client Request');
    emailPayload.append('_captcha', 'false');
    emailPayload.append('_template', 'box');

    // 1. Firebase RTDB — persistent lead storage
    const firebasePromise = (window.__db
      ? window.__db.ref('leads').push({
          ...data,
          timestamp: Date.now(),
          submitted_at: new Date().toISOString(),
          source: window.location.hostname,
          status: 'new',
        }).then(() => console.log('[AjayaDesign] ✅ Lead saved to Firebase'))
        .catch(err => console.warn('[AjayaDesign] ⚠️ Firebase save failed:', err))
      : Promise.resolve()
    );

    // 2. FormSubmit — email backup
    const emailPromise = fetch(FORMSUBMIT_URL, {
      method: 'POST',
      headers: { 'Accept': 'application/json' },
      body: emailPayload,
    }).then(() => console.log('[AjayaDesign] ✅ Email sent via FormSubmit'))
      .catch(err => console.warn('[AjayaDesign] ⚠️ FormSubmit failed:', err));

    const n8nCtrl = new AbortController();
    const n8nTimer = setTimeout(() => n8nCtrl.abort(), N8N_TIMEOUT_MS);
    const n8nPromise = fetch(N8N_WEBHOOK, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
      signal: n8nCtrl.signal,
    }).then(() => console.log('[AjayaDesign] ✅ n8n webhook triggered'))
      .catch(err => console.warn('[AjayaDesign] ⚠️ n8n unreachable (email still sent):', err))
      .finally(() => clearTimeout(n8nTimer));

    await Promise.allSettled([firebasePromise, emailPromise, n8nPromise]);

    // Visual feedback — success
    btn.innerHTML = `
      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
      Request Received — We'll be in touch!
    `;
    btn.classList.remove('bg-amd-red', 'hover:bg-red-700');
    btn.classList.add('bg-green-600');
  });

});
