/* ═══════════════════════════════════════════════════════
   AjayaDesign — Chatbot Widget + Exit-Intent Popup
   Pure client-side, Firebase RTDB for lead capture
   ═══════════════════════════════════════════════════════ */
(function () {
  'use strict';

  // ─── helpers ───
  const $ = (s, p) => (p || document).querySelector(s);
  const ce = (tag, cls, html) => { const e = document.createElement(tag); if (cls) e.className = cls; if (html) e.innerHTML = html; return e; };
  const db = () => window.__db;

  // ─── FAQ data ───
  const QUICK_BTNS = [
    '💰 Website cost?',
    '⏱️ How long?',
    '🔄 Redesigns?',
    '🖼️ Examples',
    '🔍 Free audit',
    '⭐ What\'s different?'
  ];

  const PORTFOLIO = [
    { name: 'Apex Auto', url: '/apex-auto/', img: '/assets/images/apex-auto-thumb.webp' },
    { name: 'Monument Pilates', url: '/monument-pilates/', img: '/assets/images/monument-pilates-thumb.webp' },
    { name: 'Snoball Dude', url: '/snoball-dude/', img: '/assets/images/snoball-dude-thumb.webp' }
  ];

  function getResponse(text) {
    const t = text.toLowerCase();
    if (t.includes('cost') || t.includes('price') || t.includes('💰'))
      return { html: 'Our websites start at <strong>$1,500</strong> for a custom-built site. No monthly fees, no templates. Want a free audit of your current site? <a href="/grader/">Try our free grader →</a>' };
    if (t.includes('long') || t.includes('time') || t.includes('⏱'))
      return { html: 'Most projects are delivered in <strong>2-4 weeks</strong>. Rush delivery available for an additional fee.' };
    if (t.includes('redesign') || t.includes('🔄'))
      return { html: 'Absolutely! We\'ve redesigned <strong>29+ sites</strong> with an average performance boost from 32 to 95. <a href="/works/">Check our case studies →</a>' };
    if (t.includes('example') || t.includes('portfolio') || t.includes('🖼'))
      return { html: 'Here are a few recent builds:', portfolio: true };
    if (t.includes('audit') || t.includes('🔍'))
      return { html: 'Get your free website audit right here! Fill in below:', form: 'audit' };
    if (t.includes('different') || t.includes('⭐') || t.includes('why you'))
      return { html: 'We build custom sites, not templates. Every site gets: <strong>performance optimization, mobile-first design, SEO setup, and analytics</strong>. Plus our <a href="/grader/">free website grader</a> lets you see your current score instantly.' };
    return { html: 'Thanks for your question! Leave your email and we\'ll get back to you within 24 hours.', form: 'lead' };
  }

  // ─── save lead to Firebase ───
  function saveLead(path, data) {
    try {
      if (db()) db().ref(path).push({
        ...data,
        timestamp: Date.now(),
        page: location.pathname
      });
    } catch (e) { console.warn('Chatbot lead save failed', e); }
  }

  // ═══════════════ CHATBOT WIDGET ═══════════════
  function initChatbot() {
    // FAB
    const fab = ce('button', 'chatbot-fab', '<svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H5.2L4 17.2V4h16v12z"/><path d="M7 9h2v2H7zm4 0h2v2h-2zm4 0h2v2h-2z"/></svg>');
    fab.setAttribute('aria-label', 'Open chat');
    document.body.appendChild(fab);

    // Panel
    const panel = ce('div', 'chatbot-panel');
    panel.innerHTML = `
      <div class="chatbot-header">
        <div class="dot"></div>
        <span>AjayaDesign Chat</span>
        <button class="chatbot-close" aria-label="Close chat">&times;</button>
      </div>
      <div class="chatbot-messages"></div>
      <div class="cb-quick"></div>
      <div class="chatbot-input">
        <input type="text" placeholder="Type a message…" />
        <button>Send</button>
      </div>`;
    document.body.appendChild(panel);

    const msgs = $('.chatbot-messages', panel);
    const quickWrap = $('.cb-quick', panel);
    const input = $('input', $('.chatbot-input', panel));
    const sendBtn = $('button', $('.chatbot-input', panel));
    let isOpen = false;

    function toggle() {
      isOpen = !isOpen;
      panel.classList.toggle('open', isOpen);
      fab.classList.toggle('open', isOpen);
      if (isOpen && msgs.children.length === 0) greet();
    }

    fab.onclick = toggle;
    $('.chatbot-close', panel).onclick = toggle;

    function addMsg(html, who, extra) {
      const m = ce('div', `cb-msg ${who}`);
      m.innerHTML = html;
      if (extra) m.appendChild(extra);
      msgs.appendChild(m);
      msgs.scrollTop = msgs.scrollHeight;
      return m;
    }

    function showTyping() {
      const t = ce('div', 'cb-typing', '<span></span><span></span><span></span>');
      msgs.appendChild(t);
      msgs.scrollTop = msgs.scrollHeight;
      return t;
    }

    function showQuickBtns() {
      quickWrap.innerHTML = '';
      QUICK_BTNS.forEach(label => {
        const b = ce('button', '', label);
        b.onclick = () => handleInput(label);
        quickWrap.appendChild(b);
      });
    }

    function buildPortfolio() {
      const wrap = ce('div', 'cb-portfolio');
      PORTFOLIO.forEach(p => {
        const a = ce('a');
        a.href = p.url;
        a.target = '_blank';
        a.innerHTML = `<img src="${p.img}" alt="${p.name}" onerror="this.style.display='none'"><span>${p.name}</span>`;
        wrap.appendChild(a);
      });
      return wrap;
    }

    function buildForm(type) {
      const wrap = ce('div', 'cb-form');
      if (type === 'audit') {
        wrap.innerHTML = '<input type="text" placeholder="Your name" data-f="name"><input type="email" placeholder="Email" data-f="email"><input type="url" placeholder="Your website URL" data-f="website"><button>Get Free Audit</button>';
      } else {
        wrap.innerHTML = '<input type="email" placeholder="Your email" data-f="email"><button>Submit</button>';
      }
      $('button', wrap).onclick = () => {
        const data = {};
        wrap.querySelectorAll('input').forEach(i => { data[i.dataset.f] = i.value; });
        if (!data.email || !data.email.includes('@')) { alert('Please enter a valid email.'); return; }
        saveLead('/chat-leads', { type, ...data });
        wrap.innerHTML = '<span style="color:#00D4FF">✓ Sent! We\'ll be in touch soon.</span>';
        if (type === 'audit') localStorage.setItem('ad_audit_submitted', '1');
      };
      return wrap;
    }

    function handleInput(text) {
      addMsg(text, 'user');
      quickWrap.innerHTML = '';
      const typing = showTyping();
      const resp = getResponse(text);

      // check if user typed an email directly
      if (/@/.test(text) && text.includes('.')) {
        saveLead('/chat-leads', { type: 'inline', email: text, question: text });
      }

      setTimeout(() => {
        typing.remove();
        const extra = resp.portfolio ? buildPortfolio() : resp.form ? buildForm(resp.form) : null;
        addMsg(resp.html, 'bot', extra);
        showQuickBtns();
      }, 600 + Math.random() * 600);
    }

    function greet() {
      const typing = showTyping();
      setTimeout(() => {
        typing.remove();
        addMsg('Hey! 👋 I\'m AjayaDesign\'s assistant. How can I help you today?', 'bot');
        showQuickBtns();
      }, 800);
    }

    sendBtn.onclick = () => { if (input.value.trim()) { handleInput(input.value.trim()); input.value = ''; } };
    input.onkeydown = (e) => { if (e.key === 'Enter') sendBtn.click(); };
  }

  // ═══════════════ EXIT INTENT POPUP ═══════════════
  function initExitIntent() {
    if (sessionStorage.getItem('ad_exit_shown')) return;

    const overlay = ce('div', 'exit-overlay');
    overlay.innerHTML = `
      <div class="exit-modal">
        <button class="exit-close" aria-label="Close popup">&times;</button>
        <h2>Wait! Your website might be losing you customers.</h2>
        <p>Find out in 30 seconds with our free instant audit.</p>
        <a href="/grader/" class="exit-cta">Get Free Instant Audit →</a>
        <div class="exit-divider">— or —</div>
        <div class="exit-form">
          <input type="email" placeholder="Your email" data-f="email" />
          <input type="url" placeholder="Your website URL" data-f="url" />
          <button>Email Me a Report</button>
        </div>
      </div>`;
    document.body.appendChild(overlay);

    function show() {
      if (sessionStorage.getItem('ad_exit_shown')) return;
      if (localStorage.getItem('ad_audit_submitted')) return;
      sessionStorage.setItem('ad_exit_shown', '1');
      overlay.classList.add('show');
    }

    function dismiss() { overlay.classList.remove('show'); }

    // desktop: mouse leave
    document.addEventListener('mouseout', (e) => {
      if (!e.relatedTarget && e.clientY < 5) show();
    });
    // mobile: 30s timer
    if ('ontouchstart' in window) setTimeout(show, 30000);

    overlay.onclick = (e) => { if (e.target === overlay) dismiss(); };
    $('.exit-close', overlay).onclick = dismiss;

    $('button', $('.exit-form', overlay)).onclick = () => {
      const form = $('.exit-form', overlay);
      const email = $('input[data-f="email"]', form).value;
      const url = $('input[data-f="url"]', form).value;
      if (!email || !email.includes('@')) { alert('Please enter a valid email.'); return; }
      saveLead('/exit-intent-leads', { email, url });
      form.innerHTML = '<span class="exit-success">✓ We\'ll email your report shortly!</span>';
      setTimeout(dismiss, 2500);
    };
  }

  // ─── init on DOM ready ───
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => { initChatbot(); initExitIntent(); });
  } else {
    initChatbot(); initExitIntent();
  }
})();
