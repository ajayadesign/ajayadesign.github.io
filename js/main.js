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

  // ── Smooth Scroll on Nav Click ──
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', (e) => {
      const targetId = anchor.getAttribute('href');
      if (targetId === '#') return;  // logo link
      const target = document.querySelector(targetId);
      if (!target) return;
      e.preventDefault();
      const navHeight = navbar.offsetHeight;
      const targetPos = target.getBoundingClientRect().top + window.scrollY - navHeight - 16;
      window.scrollTo({ top: targetPos, behavior: 'smooth' });
      // Update URL hash without jumping
      history.pushState(null, '', targetId);
    });
  });

  // ── Active Section Highlight ──
  const sections = document.querySelectorAll('section[id]');
  const navLinks = document.querySelectorAll('.nav-link');

  const sectionObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const id = entry.target.getAttribute('id');
        navLinks.forEach(link => {
          link.classList.toggle('active', link.getAttribute('href') === '#' + id);
        });
      }
    });
  }, { rootMargin: '-20% 0px -60% 0px', threshold: 0 });

  sections.forEach(section => sectionObserver.observe(section));

  // ── Firebase Status Indicator ──
  // Uses Firebase .info/connected to show real-time connectivity
  function initStatusIndicator() {
    const db = window.__db;
    if (!db) {
      updateStatusUI(false);
      return;
    }
    db.ref('.info/connected').on('value', (snap) => {
      updateStatusUI(snap.val() === true);
    });
  }

  function updateStatusUI(online) {
    const label = online ? 'System Online' : 'Offline';
    const dotColor = online ? 'bg-green-500' : 'bg-gray-500';
    const pingColor = online ? 'bg-green-400' : 'bg-gray-400';

    // Nav status
    const navDot  = document.getElementById('nav-status-dot');
    const navPing = document.getElementById('nav-status-ping');
    const navText = document.getElementById('nav-status-text');
    if (navDot) {
      navDot.className = `relative inline-flex rounded-full h-2 w-2 ${dotColor}`;
      navPing.className = `animate-ping absolute inline-flex h-full w-full rounded-full ${pingColor} opacity-75`;
      navText.textContent = label;
    }

    // Mobile status
    const mobileSt = document.getElementById('mobile-system-status');
    if (mobileSt) {
      const mDot  = mobileSt.querySelector('span > span:last-child');
      const mPing = mobileSt.querySelector('span > span:first-child');
      if (mDot) mDot.className = `relative inline-flex rounded-full h-2 w-2 ${dotColor}`;
      if (mPing) mPing.className = `animate-ping absolute inline-flex h-full w-full rounded-full ${pingColor} opacity-75`;
      // Update text node (last child text)
      const textNodes = [...mobileSt.childNodes].filter(n => n.nodeType === 3);
      if (textNodes.length) textNodes[textNodes.length - 1].textContent = '\n            ' + label + '\n          ';
    }

    // Footer status
    const footerSt = document.getElementById('footer-system-status');
    if (footerSt) {
      const fDot  = footerSt.querySelector('span.relative > span:last-child');
      const fPing = footerSt.querySelector('span.relative > span:first-child');
      const fText = footerSt.querySelector(':scope > span:last-child');
      if (fDot) fDot.className = `relative inline-flex rounded-full h-2 w-2 ${dotColor}`;
      if (fPing) fPing.className = `animate-ping absolute inline-flex h-full w-full rounded-full ${pingColor} opacity-75`;
      if (fText) fText.textContent = label;
    }
  }

  initStatusIndicator();

  // ── Dynamic "Sites Shipped" counter from Firebase builds node ──
  function initSitesCounter() {
    const el = document.getElementById('stat-sites');
    const db = window.__db;
    if (!el || !db) return;
    db.ref('builds').on('value', (snap) => {
      const builds = snap.val();
      if (!builds) return;
      const completedCount = Object.values(builds).filter(b => b.status === 'complete').length;
      // Minimum of 4 (the manually listed portfolio items)
      const total = Math.max(4, completedCount);
      el.innerHTML = total + '<span class="text-amd-red">+</span>';
    });
  }
  initSitesCounter();

  // ── Intake Form Submission ──
  // Triple-send: Firebase (DB) + FormSubmit (email) + Python API (pipeline).
  // Firebase = persistent storage + offline bridge (poller picks up missed leads).
  // FormSubmit = email backup. Python API = direct pipeline trigger.
  const PYTHON_API = 'http://localhost:8000/api/v1/build';
  const FORMSUBMIT_URL = 'https://formsubmit.co/ajax/9dc23f5c5eb6fba941487190ff80294b';
  const API_TIMEOUT_MS = 5000;
  const intakeForm = document.getElementById('ajayadesign-intake-form');

  intakeForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(intakeForm);
    const data = Object.fromEntries(formData.entries());
    console.log('[AjayaDesign] Intake submission:', data);

    // Rebuild safety gate — must type business name to confirm
    const rebuildBox = document.getElementById('rebuild-checkbox');
    const rebuildConfirm = document.getElementById('rebuild-confirm');
    if (rebuildBox && rebuildBox.checked) {
      const typed = (rebuildConfirm ? rebuildConfirm.value.trim() : '');
      if (typed.toLowerCase() !== (data.business_name || '').trim().toLowerCase()) {
        alert('To confirm a rebuild, type your business name exactly in the confirmation field.');
        btn.innerHTML = originalHTML;
        btn.disabled = false;
        return;
      }
    }

    // Clean lead data — all fields, no FormSubmit config
    const lead = {
      businessName:      data.business_name || '',
      niche:             data.niche || '',
      goals:             data.goals || '',
      email:             data.email || '',
      phone:             data.phone || '',
      location:          data.location || '',
      existingWebsite:   data.existing_website || '',
      brandColors:       data.brand_colors || '',
      tagline:           data.tagline || '',
      targetAudience:    data.target_audience || '',
      competitorUrls:    data.competitor_urls || '',
      additionalNotes:   data.additional_notes || '',
      rebuild:           !!(rebuildBox && rebuildBox.checked),
    };
    const ts = Date.now();
    // ID = sanitized email + timestamp (e.g. "test-at-example-com_1771042375045")
    const leadId = (lead.email || 'unknown').replace(/[@.]/g, '-') + '_' + ts;

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

    // Triple-send: Firebase (DB) + FormSubmit (email) + Python API (pipeline)
    const emailPayload = new FormData(intakeForm);
    emailPayload.append('_subject', 'New AjayaDesign Client Request');
    emailPayload.append('_captcha', 'false');
    emailPayload.append('_template', 'box');

    // 1. Firebase RTDB — persistent lead storage (clean data, custom ID)
    const firebasePromise = (window.__db
      ? window.__db.ref('leads/' + leadId).set({
          ...lead,
          timestamp: ts,
          submitted_at: new Date(ts).toISOString(),
          source: window.location.hostname,
          status: 'new',
        }).then(() => console.log('[AjayaDesign] ✅ Lead saved to Firebase'))
        .catch(err => console.warn('[AjayaDesign] ⚠️ Firebase save failed:', err))
      : Promise.resolve()
    );

    // 2. FormSubmit — email backup
    const emailCtrl = new AbortController();
    const emailTimer = setTimeout(() => emailCtrl.abort(), API_TIMEOUT_MS);
    const emailPromise = fetch(FORMSUBMIT_URL, {
      method: 'POST',
      headers: { 'Accept': 'application/json' },
      body: emailPayload,
      signal: emailCtrl.signal,
    }).then(() => console.log('[AjayaDesign] ✅ Email sent via FormSubmit'))
      .catch(err => console.warn('[AjayaDesign] ⚠️ FormSubmit failed:', err))
      .finally(() => clearTimeout(emailTimer));

    // 3. Python FastAPI — pipeline trigger (only available when API server is running)
    const apiCtrl = new AbortController();
    const apiTimer = setTimeout(() => apiCtrl.abort(), API_TIMEOUT_MS);
    const apiPayload = { ...lead, firebaseId: leadId, source: window.location.hostname };
    const apiPromise = fetch(PYTHON_API, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(apiPayload),
      signal: apiCtrl.signal,
    }).then(r => r.ok
        ? console.log('[AjayaDesign] ✅ Python API build triggered')
        : console.warn('[AjayaDesign] ⚠️ Python API responded', r.status))
      .catch(err => console.warn('[AjayaDesign] ⚠️ Python API unreachable (Firebase bridge will pick it up):', err))
      .finally(() => clearTimeout(apiTimer));

    await Promise.allSettled([firebasePromise, emailPromise, apiPromise]);

    // Visual feedback — success
    btn.innerHTML = `
      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
      Request Received — We'll be in touch!
    `;
    btn.classList.remove('bg-amd-red', 'hover:bg-red-700');
    btn.classList.add('bg-green-600');
  });

});
