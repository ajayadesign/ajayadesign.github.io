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

  if (menuBtn && mobileMenu) {
    menuBtn.addEventListener('click', () => {
      const open = mobileMenu.classList.contains('hidden');
      mobileMenu.classList.toggle('hidden');
      if (iconOpen) iconOpen.classList.toggle('hidden');
      if (iconClose) iconClose.classList.toggle('hidden');
      document.body.style.overflow = open ? 'hidden' : 'auto';
    });

    // Close mobile menu on link click
    mobileMenu.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => {
        mobileMenu.classList.add('hidden');
        if (iconOpen) iconOpen.classList.remove('hidden');
        if (iconClose) iconClose.classList.add('hidden');
        document.body.style.overflow = 'auto';
      });
    });
  }

  // ── PrecisionScrollEngine — Apple-style canvas frame sequence ──
  // Desktop: full 64 frames, 2x DPR, continuous lerp
  // Mobile: lighter — 1x DPR, every-other-frame, idle rAF stop
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const isMobileCanvas = window.matchMedia('(max-width: 768px)').matches;
  const scrollCanvas = document.getElementById('scroll-canvas');
  const heroPosters = document.querySelectorAll('.scroll-video-poster');

  if (prefersReducedMotion) {
    // Reduced-motion only: show static poster, skip canvas entirely
    document.body.classList.add('reduced-motion');
    if (scrollCanvas) scrollCanvas.style.display = 'none';
    heroPosters.forEach(poster => {
      poster.classList.remove('hidden');
      poster.style.display = 'block';
      poster.style.opacity = '0.7';
    });
  } else if (scrollCanvas) {
    const ctx = scrollCanvas.getContext('2d');
    const frameDir = scrollCanvas.dataset.frames;
    const totalFrames = parseInt(scrollCanvas.dataset.frameCount, 10) || 64;
    // Mobile: 1x DPR (halves GPU pixels), skip every other frame
    const dpr = isMobileCanvas ? 1 : Math.min(window.devicePixelRatio || 1, 2);
    const frameStep = isMobileCanvas ? 2 : 1; // load every Nth frame
    const frameCount = Math.ceil(totalFrames / frameStep);
    const frames = [];
    let loadedCount = 0;
    let currentFrame = -1;
    let displayFrame = 0;  // lerp target (float)
    let animFrame = 0;     // actual rendered frame (float, lerped)
    let rafId = null;
    let isScrolling = false;
    let scrollTimer = null;
    const lerpFactor = isMobileCanvas ? 0.18 : 0.12; // faster settle on mobile

    // Show poster as fallback until frame 1 loads
    // (poster is hidden only after first canvas draw)

    // Progressive preload: load frame 1 first, then rest
    function preloadFrame(frameIndex, arrayIndex) {
      const img = new Image();
      img.src = `${frameDir}/frame_${String(frameIndex).padStart(4, '0')}.webp`;
      img.onload = () => {
        loadedCount++;
        if (arrayIndex === 0 && ctx) {
          setupCanvasDPR(img);
          drawFrame(0);
          // Frame 1 painted — crossfade poster out smoothly
          heroPosters.forEach(p => {
            p.style.transition = 'opacity 0.4s ease';
            p.style.opacity = '0';
            setTimeout(() => { p.style.display = 'none'; }, 400);
          });
        }
      };
      frames[arrayIndex] = img;
    }

    // DPR-aware canvas sizing
    function setupCanvasDPR(img) {
      const vw = window.innerWidth;
      const vh = window.innerHeight;
      scrollCanvas.style.width = vw + 'px';
      scrollCanvas.style.height = vh + 'px';
      scrollCanvas.width = vw * dpr;
      scrollCanvas.height = vh * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    // Preload frame 1 immediately, queue rest
    preloadFrame(1, 0);
    let arrIdx = 1;
    for (let i = 1 + frameStep; i <= totalFrames; i += frameStep) {
      preloadFrame(i, arrIdx++);
    }

    function drawFrame(index) {
      if (index === currentFrame) return;
      const img = frames[index];
      if (!img || !img.complete || img.naturalWidth === 0) return;
      currentFrame = index;

      const vw = window.innerWidth;
      const vh = window.innerHeight;
      const imgRatio = img.naturalWidth / img.naturalHeight;
      const vpRatio = vw / vh;
      let dw, dh, dx, dy;

      if (isMobileCanvas && imgRatio > vpRatio) {
        // Mobile portrait + landscape image: contain-fit (show full frame)
        dw = vw; dh = vw / imgRatio;
        dx = 0; dy = (vh - dh) / 2;
      } else if (imgRatio > vpRatio) {
        // Desktop cover-fit
        dh = vh; dw = vh * imgRatio;
        dx = (vw - dw) / 2; dy = 0;
      } else {
        dw = vw; dh = vw / imgRatio;
        dx = 0; dy = (vh - dh) / 2;
      }
      ctx.clearRect(0, 0, vw, vh);
      ctx.drawImage(img, dx, dy, dw, dh);
    }

    // Lerp animation loop — smooth sub-frame interpolation
    // On mobile: stops after settling to save battery
    function lerpLoop() {
      animFrame += (displayFrame - animFrame) * lerpFactor;
      const snapped = Math.round(animFrame);
      const clamped = Math.min(frameCount - 1, Math.max(0, snapped));
      drawFrame(clamped);

      // Ramp canvas opacity: 0.90 at top → 1.0 at bottom (frames are dark, need high opacity)
      const ratio = frameCount > 1 ? animFrame / (frameCount - 1) : 0;
      scrollCanvas.style.opacity = 0.90 + 0.10 * ratio;

      // On mobile, stop loop when settled to save battery
      if (isMobileCanvas && !isScrolling && Math.abs(displayFrame - animFrame) < 0.5) {
        rafId = null;
        return;
      }
      rafId = requestAnimationFrame(lerpLoop);
    }

    function startLoop() {
      if (!rafId) rafId = requestAnimationFrame(lerpLoop);
    }

    function onScroll() {
      const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
      const maxScroll = document.body.scrollHeight - window.innerHeight;
      const ratio = maxScroll > 0 ? Math.min(1, Math.max(0, scrollTop / maxScroll)) : 0;
      displayFrame = ratio * (frameCount - 1);

      // Track scroll activity for mobile idle detection
      isScrolling = true;
      clearTimeout(scrollTimer);
      scrollTimer = setTimeout(() => { isScrolling = false; }, 150);
      startLoop();
    }

    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', () => {
      if (frames[0] && frames[0].complete) setupCanvasDPR(frames[0]);
      currentFrame = -1; // force redraw
      startLoop();
    });
    onScroll();
    startLoop();
  }

  // ── Scroll-Driven Hero Overlays (fade + translate tied to scroll) ──
  const heroOverlays = document.querySelectorAll('[data-scroll-fade]');
  const isMobile = isMobileCanvas;
  if (heroOverlays.length && !prefersReducedMotion) {
    if (isMobile) {
      // Mobile: show all hero text immediately — not enough scroll runway for fade effect
      heroOverlays.forEach(el => {
        el.style.opacity = '1';
        el.style.transform = 'translateY(0)';
      });
    } else {
      function updateOverlays() {
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        const vh = window.innerHeight;
        heroOverlays.forEach(el => {
          const start = parseFloat(el.dataset.scrollStart || '0') * vh;
          const end = parseFloat(el.dataset.scrollEnd || '1') * vh;
          const progress = Math.min(1, Math.max(0, (scrollTop - start) / (end - start)));
          // Start visible, fade out as user scrolls past
          const opacity = 1 - progress;
          const translateY = progress * 30; // drift up 30px as fading out
          el.style.opacity = opacity;
          el.style.transform = `translateY(-${translateY}px)`;
        });
        requestAnimationFrame(updateOverlays);
      }
      requestAnimationFrame(updateOverlays);
    }
  }

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

  // ── Navbar Blur Transition ──
  const navbar = document.getElementById('navbar');
  if (navbar) {
    // Start transparent, transition to frosted glass on scroll
    navbar.style.transition = 'background-color 0.4s ease, backdrop-filter 0.4s ease, padding 0.3s ease';
    function updateNavbar() {
      const scrolled = window.scrollY > 50;
      if (scrolled) {
        navbar.classList.add('py-0', 'nav-scrolled');
        navbar.classList.remove('nav-top');
      } else {
        navbar.classList.remove('py-0', 'nav-scrolled');
        navbar.classList.add('nav-top');
      }
    }
    window.addEventListener('scroll', updateNavbar, { passive: true });
    updateNavbar();
  }

  // ── Background Ambient Audio ──
  const audioToggle = document.getElementById('audio-toggle');
  const audioIcon = document.getElementById('audio-icon');
  if (audioToggle) {
    let audio = null;
    let isPlaying = false;
    const targetVolume = 0.15;
    const fadeDuration = 600; // ms

    function createAudio() {
      if (audio) return audio;
      audio = new Audio(document.body.dataset.audio || '/assets/audio/ambient-drone.mp3');
      audio.loop = true;
      audio.volume = 0;
      audio.preload = 'none';
      return audio;
    }

    function fadeIn() {
      const a = createAudio();
      a.play().then(() => {
        const steps = 20;
        const stepTime = fadeDuration / steps;
        let step = 0;
        const interval = setInterval(() => {
          step++;
          a.volume = Math.min(targetVolume, (step / steps) * targetVolume);
          if (step >= steps) clearInterval(interval);
        }, stepTime);
        isPlaying = true;
        audioToggle.classList.add('audio-playing');
        if (audioIcon) audioIcon.setAttribute('data-state', 'playing');
      }).catch(() => {});
    }

    function fadeOut() {
      if (!audio) return;
      const startVol = audio.volume;
      const steps = 20;
      const stepTime = fadeDuration / steps;
      let step = 0;
      const interval = setInterval(() => {
        step++;
        audio.volume = Math.max(0, startVol * (1 - step / steps));
        if (step >= steps) {
          clearInterval(interval);
          audio.pause();
          isPlaying = false;
          audioToggle.classList.remove('audio-playing');
          if (audioIcon) audioIcon.setAttribute('data-state', 'paused');
        }
      }, stepTime);
    }

    audioToggle.addEventListener('click', () => {
      if (isPlaying) fadeOut();
      else fadeIn();
    });

    // Stop on page unload
    window.addEventListener('beforeunload', () => { if (audio) { audio.pause(); audio.src = ''; } });
  }

  // ── Smooth Scroll on Nav Click (same-page #hash links only) ──
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', (e) => {
      const targetId = anchor.getAttribute('href');
      if (targetId === '#') return;
      const target = document.querySelector(targetId);
      if (!target) return;
      e.preventDefault();
      const navHeight = navbar ? navbar.offsetHeight : 0;
      const targetPos = target.getBoundingClientRect().top + window.scrollY - navHeight - 16;
      window.scrollTo({ top: targetPos, behavior: 'smooth' });
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

  if (intakeForm) intakeForm.addEventListener('submit', async (e) => {
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

  // ── Lazy-Load Portfolio Iframes ──
  // Only load iframes when their card is visible; unload when far off-screen.
  // Caps concurrent iframes to avoid memory/CPU spikes that crash the tab.
  // (Only runs on pages with project cards — i.e. /works/)
  const MAX_CONCURRENT_IFRAMES = 6;
  const loadedIframes = new Set();

  function loadIframe(iframe) {
    if (!iframe.dataset.src || iframe.src) return;
    iframe.src = iframe.dataset.src;
    loadedIframes.add(iframe);
  }

  function unloadIframe(iframe) {
    if (!iframe.src) return;
    iframe.removeAttribute('src');
    loadedIframes.delete(iframe);
  }

  const iframeObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      const iframe = entry.target.querySelector('iframe[data-src]');
      if (!iframe) return;

      if (entry.isIntersecting) {
        // Enforce concurrency cap — evict oldest loaded iframe if at limit
        if (loadedIframes.size >= MAX_CONCURRENT_IFRAMES) {
          const oldest = loadedIframes.values().next().value;
          unloadIframe(oldest);
        }
        loadIframe(iframe);
      } else {
        unloadIframe(iframe);
      }
    });
  }, { rootMargin: '200px 0px' });

  document.querySelectorAll('.project-card').forEach(card => iframeObserver.observe(card));

  // ── Portfolio Filtering (works page only) ──
  const filterBtns = document.querySelectorAll('.filter-btn');
  const projectCards = document.querySelectorAll('.project-card');
  const filterPath = document.getElementById('filter-path');
  const filterCount = document.getElementById('filter-count');

  if (filterBtns.length && projectCards.length) {
    filterBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        const filter = btn.dataset.filter;

        // Update active state
        filterBtns.forEach(b => {
          b.classList.remove('active');
          b.classList.add('border-border-dim', 'text-gray-400');
        });
        btn.classList.add('active');
        btn.classList.remove('border-border-dim', 'text-gray-400');

        // Update terminal path
        if (filterPath) {
          filterPath.textContent = filter === 'all' ? '*' : filter + '/';
        }

        // Filter cards
        let count = 0;
        projectCards.forEach(card => {
          const tags = (card.dataset.tags || '').split(',');
          const match = filter === 'all' || tags.includes(filter);
          if (match) {
            card.classList.remove('filter-hidden');
            count++;
          } else {
            card.classList.add('filter-hidden');
          }
        });

        // Update count
        if (filterCount) filterCount.textContent = count;
      });
    });
  }

});
