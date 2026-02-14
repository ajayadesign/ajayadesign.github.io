# 🏗️ AjayaDesign v2 — Multi-Agent Site Factory

> **Status:** Architecture Proposal  
> **Author:** AjayaDesign Engineering  
> **Date:** February 13, 2026  

---

## 📍 Where We Are (v1)

```
Client Form → n8n → runner (server.js) → bash script → single AI call → 1 page → test → deploy
```

**What v1 does well:**
- ✅ End-to-end automation works
- ✅ Agentic retry loop (3 attempts)
- ✅ Real-time SSE streaming to admin
- ✅ Firebase + Email + Telegram triple-send
- ✅ Auto submodule + portfolio card injection

**What v1 can't do:**
- ❌ Only generates 1 page (`index.html`)
- ❌ Single AI call = no planning, no refinement
- ❌ Sequential — everything runs in series
- ❌ Bash orchestrator — fragile, hard to extend
- ❌ No design system consistency
- ❌ No content strategy — design and copy mixed in one prompt
- ❌ No specialization — one prompt does everything
- ❌ Tests only check the homepage

---

## 🎯 The Vision (v2): Multi-Agent Site Factory

```
┌──────────────────────────────────────────────────────────────────────┐
│                         CLIENT INTAKE                                │
│   Form → Firebase + Email + n8n → Runner                            │
└──────────────────────┬───────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│  PHASE 1 — AI COUNCIL  (Strategist ↔ Critic debate)                 │
│                                                                      │
│   ┌─────────────┐    rounds     ┌─────────────┐                     │
│   │  Strategist  │◄────────────►│   Critic     │                     │
│   │   (gpt-4o)   │  2-3 rounds  │   (gpt-4o)   │                     │
│   └──────┬──────┘               └─────────────┘                     │
│          │                                                           │
│          ▼                                                           │
│   📋 Site Blueprint JSON                                             │
│   {                                                                  │
│     pages: ["home","about","services","portfolio","contact"],        │
│     siteMap: { ... },                                                │
│     brandVoice: "professional, warm, authoritative",                 │
│     colorDirection: "deep navy + gold accents",                      │
│     contentOutlines: { home: {...}, about: {...}, ... }              │
│   }                                                                  │
└──────────────────────┬───────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│  PHASE 2 — DESIGN SYSTEM GENERATION                                  │
│                                                                      │
│   Design Agent → shared/design-system.js                             │
│   (Tailwind config, component HTML snippets, shared nav/footer)      │
│                                                                      │
│   Output: The "Contract" all page agents must follow                 │
└──────────────────────┬───────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│  PHASE 3 — PARALLEL PAGE GENERATION  (Worker Pool)                   │
│                                                                      │
│   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐ │
│   │ Agent 1  │  │ Agent 2  │  │ Agent 3  │  │ Agent 4  │  │ Agent 5  │ │
│   │  HOME    │  │  ABOUT   │  │ SERVICES │  │PORTFOLIO │  │ CONTACT  │ │
│   │ index.   │  │ about.   │  │services. │  │ work.    │  │contact.  │ │
│   │  html    │  │  html    │  │  html    │  │  html    │  │  html    │ │
│   └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘ │
│        │            │            │            │            │       │
│        ▼            ▼            ▼            ▼            ▼       │
│   Each agent receives: blueprint + design system + page brief       │
│   Each agent has its OWN retry loop (3 attempts)                    │
└──────────────────────┬───────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│  PHASE 4 — ASSEMBLY + CROSS-PAGE STITCHING                          │
│                                                                      │
│   • Inject shared navigation with correct active states              │
│   • Inject shared footer across all pages                            │
│   • Validate all internal links (href="/about.html" exists?)         │
│   • Extract shared CSS into styles.css (optional optimization)       │
│   • Generate sitemap.xml + robots.txt                                │
└──────────────────────┬───────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│  PHASE 5 — QUALITY GATE  (Parallel Testing)                         │
│                                                                      │
│   Per-page:           Full-site:                                     │
│   • axe a11y audit    • Cross-page navigation test                   │
│   • No overflow       • 404 link check                               │
│   • Valid links       • Mobile responsiveness all pages              │
│   • Content check     • Lighthouse performance budget                │
│                       • Sitemap validation                           │
│                                                                      │
│   Failed page? → Agentic fix loop (per-page, parallel)              │
└──────────────────────┬───────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│  PHASE 6 — DEPLOY + INTEGRATE + NOTIFY                              │
│   git push → GitHub Pages → submodule → portfolio card → Telegram   │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 🧠 Phase 1 Deep Dive: The AI Council

This is the **biggest unlock**. Instead of one AI call that guesses everything, two specialized AIs **debate** the plan before any code is written.

### Why Debate?

Single-prompt generation is like asking one person to simultaneously be the business consultant, copywriter, designer, and developer. The output is mediocre at everything.

The debate pattern forces **deliberate planning**:

```
Round 1: Strategist proposes a site structure
Round 2: Critic pokes holes ("the services page is too vague, you need separate pages for each service tier")  
Round 3: Strategist revises based on feedback
Round 4: Critic approves with final tweaks
→ Output: Finalized Site Blueprint JSON
```

### The Strategist AI

**Role:** Business analyst + information architect

**System Prompt Direction:**
```
You are a senior web strategist at a design agency. Given a client's business name, 
niche, and goals, you create a detailed site blueprint.

You analyze:
- What pages does this business ACTUALLY need? (not every business needs a portfolio page)
- What's the user journey? (visitor → interested → convert)
- What content should each page have?
- What's the brand voice? (formal? casual? technical? warm?)
- What's the color psychology for this industry?

Output a JSON site blueprint.
```

**Output Example:**
```json
{
  "siteName": "Sunrise Bakery",
  "tagline": "Artisan breads & pastries since 1998",
  "pages": [
    {
      "slug": "index",
      "title": "Home",
      "purpose": "Hero + social proof + quick menu preview + CTA to order",
      "sections": ["hero", "featured-products", "testimonials", "instagram-feed", "cta"],
      "contentNotes": "Lead with mouth-watering hero image concept. Emphasize 'artisan' and 'handcrafted'. CTA: 'Order Fresh Today'"
    },
    {
      "slug": "menu",
      "title": "Our Menu", 
      "purpose": "Full product catalog with categories",
      "sections": ["category-nav", "breads", "pastries", "cakes", "seasonal-specials"],
      "contentNotes": "Organize by category. Each item needs name, description, price placeholder area."
    },
    {
      "slug": "about",
      "title": "Our Story",
      "purpose": "Build trust and emotional connection",
      "sections": ["origin-story", "values", "team", "process"],
      "contentNotes": "Family business angle. Show the human side. Include 'since 1998' heritage."
    },
    {
      "slug": "contact",
      "title": "Visit Us",
      "purpose": "Drive foot traffic and orders",
      "sections": ["hours", "location-map", "contact-form", "order-cta"],
      "contentNotes": "Prominent hours display. Map embed placeholder. Order phone number."
    }
  ],
  "brandVoice": "warm, inviting, artisanal, family-oriented",
  "colorDirection": {
    "primary": "warm brown (#8B4513) — earthy, bakery feel",
    "accent": "golden wheat (#DAA520) — warmth, quality",
    "surface": "cream (#FFF8DC) — light, clean, appetizing",
    "text": "dark brown (#3E2723) — readable, warm"
  },
  "typography": {
    "headings": "Playfair Display — elegant, artisanal feel",
    "body": "Lato — clean, friendly readability"
  },
  "keyDifferentiators": [
    "28 years of family tradition",
    "Handcrafted daily, no preservatives",
    "Local ingredients sourced from regional farms"
  ],
  "competitorInsights": "Most bakery sites are cluttered and slow. We differentiate with clean design, fast loading, and mouth-watering typography."
}
```

### The Critic AI

**Role:** UX reviewer + devil's advocate

**System Prompt Direction:**
```
You are a senior UX critic. You review site blueprints and identify:
- Missing pages that this business type needs
- Weak content strategies
- Poor user journey flow
- Accessibility concerns in the color choices
- SEO gaps
- Conversion optimization issues

Be specific and actionable. Don't just say "improve the hero" — say exactly what's wrong and how to fix it.
```

### The Debate Protocol

```javascript
async function aiCouncil(clientRequest) {
  const rounds = 3;
  let blueprint = null;
  const transcript = []; // Full debate log for admin dashboard
  
  for (let round = 1; round <= rounds; round++) {
    // Strategist proposes (or revises)
    const strategistPrompt = round === 1
      ? `Create a site blueprint for: ${JSON.stringify(clientRequest)}`
      : `Revise your blueprint based on this critique:\n${lastCritique}\n\nOriginal: ${JSON.stringify(blueprint)}`;
    
    emit('ai:council', { round, speaker: 'strategist', action: 'thinking' });
    
    const proposal = await callAI('strategist', strategistPrompt);
    blueprint = JSON.parse(proposal);
    transcript.push({ round, speaker: 'strategist', content: proposal });
    
    emit('ai:council', { round, speaker: 'strategist', action: 'proposed', pages: blueprint.pages.length });
    
    // Critic reviews
    const criticPrompt = `Review this site blueprint. Be tough but constructive:\n${JSON.stringify(blueprint)}`;
    
    emit('ai:council', { round, speaker: 'critic', action: 'reviewing' });
    
    const critique = await callAI('critic', criticPrompt);
    transcript.push({ round, speaker: 'critic', content: critique });
    
    emit('ai:council', { round, speaker: 'critic', action: 'critiqued' });
    
    lastCritique = critique;
    
    // Check if critic approves
    if (critique.toLowerCase().includes('approved') || round === rounds) break;
  }
  
  return { blueprint, transcript };
}
```

### What The Admin Sees

The AI Activity panel shows the debate in real-time:

```
🧠 Strategist — Round 1
  Proposing 5-page site: Home, Menu, About, Catering, Contact

🔍 Critic — Round 1  
  "Menu page needs category filtering. Missing: Testimonials. 
   Catering should be a section on Home, not a separate page 
   for a small bakery — reduces bounce. Color scheme needs 
   darker text option for WCAG."

🧠 Strategist — Round 2
  Revised to 4 pages. Added testimonials to Home. 
  Moved catering to Home section. Fixed color contrast.

✅ Critic — Round 2
  "Approved. Strong improvement. One suggestion: add JSON-LD 
   LocalBusiness schema for local SEO."
```

---

## 🎨 Phase 2 Deep Dive: Design System as Contract

The #1 problem with multi-agent page generation is **inconsistency**. Page 1 uses blue buttons, Page 2 uses green. Page 1 has rounded corners, Page 3 has square. 

The solution: **generate a shared design system first**, and every page agent is contractually bound to it.

### What the Design Agent Generates

```javascript
// design-system.js — shared Tailwind config + component snippets
const designSystem = {
  
  // Tailwind config (injected into every page's <script>)
  tailwindConfig: `
    tailwind.config = {
      theme: {
        extend: {
          fontFamily: {
            heading: ['Playfair Display', 'serif'],
            body: ['Lato', 'sans-serif'],
          },
          colors: {
            primary: '#8B4513',
            accent: '#DAA520', 
            surface: '#FFF8DC',
            'surface-alt': '#F5E6C8',
            'text-main': '#3E2723',
            'text-muted': '#6D4C41',
            cta: '#D84315',
            'cta-hover': '#BF360C',
          },
          borderRadius: {
            DEFAULT: '0.75rem',
            'lg': '1rem',
          }
        }
      }
    }
  `,
  
  // Google Fonts link (same on every page)
  fontsLink: '<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Lato:wght@300;400;700&display=swap" rel="stylesheet">',
  
  // Shared <head> content (meta, favicons, etc.)
  sharedHead: `
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- fonts, config, etc. -->
  `,
  
  // Navigation HTML (with {{ACTIVE_PAGE}} placeholder)
  navComponent: `
    <nav class="fixed top-0 w-full bg-surface/95 backdrop-blur shadow-sm z-50">
      <div class="max-w-6xl mx-auto px-6 py-4 flex justify-between items-center">
        <a href="/" class="font-heading text-2xl font-bold text-primary">Sunrise Bakery</a>
        <div class="hidden md:flex items-center gap-8 font-body">
          <a href="/" class="nav-link {{ACTIVE:home}}">Home</a>
          <a href="/menu.html" class="nav-link {{ACTIVE:menu}}">Menu</a>
          <a href="/about.html" class="nav-link {{ACTIVE:about}}">Our Story</a>
          <a href="/contact.html" class="nav-link {{ACTIVE:contact}}">Visit Us</a>
        </div>
        <a href="/contact.html" class="px-5 py-2 bg-cta text-white font-body font-bold rounded-lg hover:bg-cta-hover transition">Order Now</a>
      </div>
    </nav>
  `,
  
  // Footer HTML (same on every page)  
  footerComponent: `
    <footer class="bg-primary text-surface py-12">
      <div class="max-w-6xl mx-auto px-6 grid md:grid-cols-3 gap-8">
        ...
        <p class="text-surface/60 text-sm">Built by <a href="https://ajayadesign.github.io">AjayaDesign</a></p>
      </div>
    </footer>
  `,
  
  // Reusable component snippets (agents can use these)
  components: {
    ctaButton: '<a href="{{href}}" class="inline-block px-8 py-3 bg-cta text-white font-body font-bold rounded-lg hover:bg-cta-hover transition shadow-lg">{{text}}</a>',
    sectionHeading: '<h2 class="font-heading text-4xl font-bold text-primary mb-4">{{text}}</h2>',
    card: '<div class="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition">...</div>',
    testimonial: '<blockquote class="bg-surface-alt rounded-lg p-6 border-l-4 border-accent">...</blockquote>',
  }
};
```

### Why This Matters

Every page agent receives:
1. The full site blueprint (from Phase 1)
2. **This design system** (the contract)
3. Its specific page brief

The page agent's prompt includes:
```
You MUST use the provided Tailwind config exactly as given.
You MUST use the provided nav and footer HTML verbatim.
You MUST use the component patterns for buttons, headings, cards.
Do NOT invent new colors, fonts, or spacing values.
```

This guarantees visual consistency across all pages.

---

## ⚡ Phase 3 Deep Dive: Parallel Page Generation

### Worker Architecture

```
                    Orchestrator (Node.js)
                          │
              ┌───────────┼───────────┐
              │           │           │
              ▼           ▼           ▼
         ┌─────────┐ ┌─────────┐ ┌─────────┐
         │Worker 1  │ │Worker 2  │ │Worker 3  │   ← Promise.allSettled()
         │  HOME    │ │  ABOUT   │ │ CONTACT  │
         │          │ │          │ │          │
         │ AI Call  │ │ AI Call  │ │ AI Call  │   ← All 3 API calls in parallel
         │ Validate │ │ Validate │ │ Validate │
         │ Test     │ │ Test     │ │ Test     │   ← Each has its own retry loop
         │ Fix?     │ │ Fix?     │ │ Fix?     │
         └────┬────┘ └────┬────┘ └────┬────┘
              │           │           │
              └───────────┼───────────┘
                          │
                    Assembly Phase
```

### Concurrency Control

We can't fire 10 AI calls simultaneously — API rate limits. Use a **semaphore**:

```javascript
class AgentPool {
  constructor(concurrency = 3) {
    this.concurrency = concurrency;
    this.running = 0;
    this.queue = [];
  }
  
  async run(task) {
    if (this.running >= this.concurrency) {
      await new Promise(resolve => this.queue.push(resolve));
    }
    this.running++;
    try {
      return await task();
    } finally {
      this.running--;
      if (this.queue.length > 0) this.queue.shift()();
    }
  }
  
  async runAll(tasks) {
    return Promise.allSettled(tasks.map(t => this.run(t)));
  }
}

// Usage:
const pool = new AgentPool(3); // max 3 parallel AI calls

const pageResults = await pool.runAll(
  blueprint.pages.map(page => () => generatePage(page, designSystem, blueprint))
);
```

### Per-Page Agent

Each page agent is **self-contained** with its own retry loop:

```javascript
async function generatePage(pageSpec, designSystem, blueprint) {
  const MAX_ATTEMPTS = 3;
  
  for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
    emit('agent:start', { page: pageSpec.slug, attempt });
    
    // 1. Generate
    const html = await callAI('page-builder', buildPagePrompt(pageSpec, designSystem));
    
    // 2. Inject shared components (nav, footer, head)
    const assembled = injectSharedComponents(html, designSystem, pageSpec.slug);
    
    // 3. Write file
    fs.writeFileSync(`${projectDir}/${pageSpec.slug}.html`, assembled);
    
    // 4. Test this specific page
    const testResult = await testPage(pageSpec.slug);
    
    if (testResult.passed) {
      emit('agent:done', { page: pageSpec.slug, attempt, status: 'pass' });
      return { page: pageSpec.slug, status: 'success', attempts: attempt };
    }
    
    // 5. Auto-fix
    if (attempt < MAX_ATTEMPTS) {
      emit('agent:fix', { page: pageSpec.slug, attempt, errors: testResult.errors });
      const fixed = await callAI('fixer', buildFixPrompt(assembled, testResult.errors));
      fs.writeFileSync(`${projectDir}/${pageSpec.slug}.html`, fixed);
    }
  }
  
  return { page: pageSpec.slug, status: 'failed', attempts: MAX_ATTEMPTS };
}
```

### What The Admin Sees

Real-time parallel progress:

```
┌─── Page Agents ──────────────────────────────────────┐
│                                                       │
│  index.html    ████████████████████░░  🧪 Testing     │
│  about.html    ████████████░░░░░░░░░  🤖 Generating   │
│  services.html ██████████████████████  ✅ Pass (1st)   │
│  portfolio.html████░░░░░░░░░░░░░░░░░  📡 AI Call      │
│  contact.html  ████████████████████░░  🔧 Fix #2       │
│                                                       │
└───────────────────────────────────────────────────────┘
```

---

## 🔧 Phase 4: Assembly

After all pages are generated, the Assembly phase stitches everything together:

### Tasks

1. **Navigation Active States**: Replace `{{ACTIVE:home}}` placeholders with proper CSS classes
2. **Cross-Link Validation**: Every `href="/about.html"` → verify `about.html` exists
3. **Sitemap Generation**: Auto-generate `sitemap.xml` from the page list
4. **robots.txt**: Standard allow-all with sitemap reference
5. **404 Page**: Auto-generate a styled 404 page matching the design system
6. **Favicon**: Generate from brand colors (SVG with initials)
7. **Shared CSS Extraction** (optional): Pull repeated Tailwind from inline to `shared.css`
8. **JSON-LD Schema**: LocalBusiness, Organization, or relevant schema per page type
9. **Open Graph Tags**: Per-page OG title, description, image placeholders

```javascript
async function assemble(pages, designSystem, blueprint, projectDir) {
  emit('phase', { name: 'assembly', status: 'start' });
  
  // 1. Fix nav active states
  for (const page of pages) {
    let html = fs.readFileSync(`${projectDir}/${page.slug}.html`, 'utf-8');
    for (const p of pages) {
      const activeClass = p.slug === page.slug ? 'text-primary font-bold' : 'text-text-muted hover:text-primary';
      html = html.replace(`{{ACTIVE:${p.slug}}}`, activeClass);
    }
    fs.writeFileSync(`${projectDir}/${page.slug}.html`, html);
  }
  
  // 2. Generate sitemap.xml
  const sitemap = generateSitemap(pages, blueprint.siteUrl);
  fs.writeFileSync(`${projectDir}/sitemap.xml`, sitemap);
  
  // 3. Generate robots.txt
  fs.writeFileSync(`${projectDir}/robots.txt`, `User-agent: *\nAllow: /\nSitemap: ${blueprint.siteUrl}/sitemap.xml`);
  
  // 4. Generate 404.html
  const notFoundHtml = await callAI('utility', build404Prompt(designSystem, blueprint));
  fs.writeFileSync(`${projectDir}/404.html`, notFoundHtml);
  
  // 5. Cross-link validation
  const brokenLinks = validateCrossLinks(pages, projectDir);
  if (brokenLinks.length > 0) {
    emit('assembly:warning', { brokenLinks });
    // Auto-fix broken links
  }
  
  emit('phase', { name: 'assembly', status: 'done' });
}
```

---

## 🧪 Phase 5: Full-Site Quality Gate

### Per-Page Tests (Parallel)

```javascript
// Each page gets the same test battery
const perPageTests = [
  'page-loads-and-has-content',
  'no-horizontal-overflow',
  'axe-zero-critical-violations',
  'all-links-have-valid-href',
  'images-have-alt-text',
  'heading-hierarchy-valid',     // h1 → h2 → h3, no skips
  'interactive-elements-focusable',
];
```

### Full-Site Integration Tests

```javascript
const integrationTests = [
  'navigation-works-across-all-pages',  // Click every nav link, verify page loads
  'no-404-internal-links',              // Crawl all internal links
  'consistent-nav-on-every-page',       // Nav HTML matches across pages
  'consistent-footer-on-every-page',    // Footer HTML matches
  'sitemap-matches-actual-pages',       // sitemap.xml lists all pages
  'mobile-responsive-all-pages',        // Viewport test on every page
  'total-page-weight-under-budget',     // Combined JS + CSS + HTML < 500KB
];
```

### Parallel Fix Loop

If `about.html` fails but `contact.html` passes, only `about.html` enters the fix loop. The others are done:

```javascript
const results = await Promise.allSettled(
  failedPages.map(page => agenticFixLoop(page, designSystem))
);
```

---

## 📊 Admin Dashboard v2: What Changes

### New SSE Events

```
Existing:          New for v2:
─────────          ───────────
step               council:round      (debate round start)
ai                 council:proposal   (strategist speaks)  
test               council:critique   (critic speaks)
log                council:approved   (plan finalized)
done               design:start       (design system generation)
                   design:done
                   agent:spawn        (page agent started)
                   agent:generating   (AI call for page)
                   agent:testing      (page test running)
                   agent:fix          (page entering fix loop)
                   agent:done         (page complete)
                   assembly:start
                   assembly:warning   (broken links, etc.)
                   assembly:done
                   integration:start  (full-site tests)
                   integration:done
```

### Updated Step Progress Bar

v1 had 6 steps. v2 has 8:

```
1. Repo    → Create GitHub repo
2. Plan    → AI Council debate (NEW)
3. Design  → Generate design system (NEW)
4. Build   → Parallel page generation (EXPANDED)
5. Stitch  → Assembly + cross-linking (NEW)
6. QA      → Per-page + integration tests
7. Deploy  → Push + Pages + submodule
8. Notify  → Telegram + email
```

### New: Agent Grid View

Instead of just a log panel, add a **visual grid** showing all page agents:

```
┌──────────────────────────────────────────────────┐
│  📄 index.html     ████████████████████  ✅ Pass  │
│  📄 about.html     ██████████████░░░░░░  🧪 Test  │
│  📄 services.html  ████████████████████  ✅ Pass  │
│  📄 portfolio.html ██████░░░░░░░░░░░░░░  🤖 Gen   │
│  📄 contact.html   ████████████████░░░░  🔧 Fix 2 │
└──────────────────────────────────────────────────┘
```

### New: Council Transcript Panel

Shows the Strategist ↔ Critic debate like a chat:

```
🧠 Strategist (Round 1)
"I propose a 5-page site: Home, Menu, About, 
 Catering, Contact..."

🔍 Critic (Round 1)
"Catering should be a section on Home, not its 
 own page. For a small bakery, fewer pages with 
 stronger content beats many thin pages..."

🧠 Strategist (Round 2)  
"Revised to 4 pages. Merged catering into Home 
 hero as a featured CTA..."

✅ Critic (Round 2)
"Approved. Clean structure. One addition: add 
 Instagram feed section to Home for social proof."
```

---

## 🏗️ Technical Implementation Plan

### Migrate: Bash → Node.js Orchestrator

The bash script served us well for v1, but parallel agents, JSON state management, and SSE streaming are painful in bash. 

**New file structure:**

```
automation/
├── orchestrator/
│   ├── index.js              ← Main entry point (replaces build_and_deploy.sh)
│   ├── phases/
│   │   ├── 01-repo.js        ← Create GitHub repo
│   │   ├── 02-council.js     ← AI Council (Strategist ↔ Critic)
│   │   ├── 03-design.js      ← Design System generation
│   │   ├── 04-generate.js    ← Parallel page agent pool
│   │   ├── 05-assemble.js    ← Cross-page stitching
│   │   ├── 06-test.js        ← Per-page + integration tests
│   │   ├── 07-deploy.js      ← Git push + Pages + submodule
│   │   └── 08-notify.js      ← Telegram + email notifications
│   ├── agents/
│   │   ├── strategist.js     ← Council: site planning
│   │   ├── critic.js         ← Council: plan review
│   │   ├── designer.js       ← Design system generation
│   │   ├── pageBuilder.js    ← Individual page generation
│   │   └── fixer.js          ← Agentic fix specialist
│   ├── lib/
│   │   ├── ai.js             ← GitHub Models API wrapper (shared)
│   │   ├── pool.js           ← Agent pool with concurrency control
│   │   ├── emitter.js        ← Event emitter for SSE/logging
│   │   ├── prompts.js        ← All prompt templates
│   │   └── testRunner.js     ← Playwright test execution
│   └── package.json
├── runner/
│   └── server.js             ← HTTP bridge (updated for v2 events)
├── docker-compose.yml
└── .env
```

### The Orchestrator

```javascript
// orchestrator/index.js
const { EventEmitter } = require('events');

class BuildOrchestrator extends EventEmitter {
  constructor(config) {
    super();
    this.config = config;
    this.state = {
      phase: 'init',
      blueprint: null,
      designSystem: null,
      pages: [],
      testResults: {},
    };
  }
  
  async run(clientRequest) {
    try {
      // Phase 1: Create repo
      this.emit('phase', { step: 1, total: 8, name: 'repo', status: 'start' });
      const repo = await createRepo(clientRequest, this);
      
      // Phase 2: AI Council
      this.emit('phase', { step: 2, total: 8, name: 'council', status: 'start' });
      const { blueprint, transcript } = await aiCouncil(clientRequest, this);
      this.state.blueprint = blueprint;
      
      // Phase 3: Design System
      this.emit('phase', { step: 3, total: 8, name: 'design', status: 'start' });
      const designSystem = await generateDesignSystem(blueprint, this);
      this.state.designSystem = designSystem;
      
      // Phase 4: Parallel Page Generation
      this.emit('phase', { step: 4, total: 8, name: 'generate', status: 'start' });
      const pages = await generateAllPages(blueprint, designSystem, repo.dir, this);
      
      // Phase 5: Assembly
      this.emit('phase', { step: 5, total: 8, name: 'assemble', status: 'start' });
      await assemble(pages, designSystem, blueprint, repo.dir, this);
      
      // Phase 6: Quality Gate
      this.emit('phase', { step: 6, total: 8, name: 'test', status: 'start' });
      const testResults = await qualityGate(pages, repo.dir, this);
      
      // Phase 7: Deploy
      this.emit('phase', { step: 7, total: 8, name: 'deploy', status: 'start' });
      await deploy(repo, this);
      
      // Phase 8: Notify
      this.emit('phase', { step: 8, total: 8, name: 'notify', status: 'start' });
      await notify(clientRequest, repo, this);
      
      this.emit('done', { status: 'success' });
    } catch (err) {
      this.emit('error', { message: err.message });
      this.emit('done', { status: 'failed' });
      throw err;
    }
  }
}
```

### Runner Server v2 Integration

The runner server stays as the HTTP bridge, but now spawns the Node.js orchestrator instead of bash:

```javascript
// Instead of:
spawn('bash', [SCRIPT, clientName, niche, goals, email])

// Now:
const orchestrator = new BuildOrchestrator(config);

// Forward all events to SSE
orchestrator.on('phase',     data => broadcastSSE(buildId, 'phase', data));
orchestrator.on('council',   data => broadcastSSE(buildId, 'council', data));
orchestrator.on('agent',     data => broadcastSSE(buildId, 'agent', data));
orchestrator.on('test',      data => broadcastSSE(buildId, 'test', data));
orchestrator.on('log',       data => broadcastSSE(buildId, 'log', data));
orchestrator.on('done',      data => broadcastSSE(buildId, 'done', data));

orchestrator.run(clientRequest);
```

---

## 🚀 Outside-The-Box Ideas

### 1. 🔍 Reference Site Analyzer

Before the AI Council starts, optionally scrape 2-3 competitor/reference sites for the same niche:

```javascript
// "What are other bakery websites doing?"
const competitors = await analyzeCompetitors(niche, 3);
// Returns: color schemes, section patterns, CTAs used, content length averages
// Feed this into the Strategist's context
```

**Implementation:** Playwright scrapes the top Google results for `"${niche} website"`, extracts structural patterns with an AI call, and feeds insights to the Strategist.

### 2. 🎨 A/B Hero Variants

Generate **2 different hero sections** for the homepage. Store both in Firebase. Let the client pick in a selection UI, or even auto-deploy the "winner" after basic analytics.

### 3. 📝 Content-First Pipeline

Separate **copywriting** from **design**:

```
Copywriter Agent → writes all text content for all pages (JSON)
Designer Agent  → receives the copy + design system → generates HTML

Why? AI writes MUCH better copy when it's not simultaneously worrying about HTML.
```

### 4. 🖼️ AI Image Prompts

For each section, generate **Stable Diffusion / DALL-E prompt suggestions** that match the brand. Store them in the blueprint. Client or admin can generate actual images later.

```json
{
  "hero": {
    "imagePrompt": "Warm, inviting bakery interior, golden hour lighting, fresh artisan bread on wooden counter, shallow depth of field, professional food photography",
    "placeholder": "gradient-warm-brown"
  }
}
```

### 5. 📊 Lighthouse CI Budget

After deploy, run Lighthouse CI and gate on performance:

```javascript
const lighthouse = await runLighthouse(liveUrl);
if (lighthouse.performance < 90) {
  emit('warning', 'Performance below 90 — consider optimization pass');
  // Optional: trigger optimization agent
}
```

### 6. 🔄 Incremental Rebuilds

v2+ idea: Client requests a change → AI only regenerates the affected page(s), not the whole site. The design system + nav/footer stay locked.

### 7. 🤖 Client Preview Bot

After build, send the client a **Telegram/WhatsApp message** with screenshots of each page + a preview link. They can reply "approved" or "change the hero color to blue" → triggers a targeted rebuild.

### 8. 📦 Component Library Growth

Over time, the design system components get **better** as we learn what works. Save successful component patterns to a shared library:

```
builds/sunrise-bakery  → testimonial component was great, save it
builds/apex-fitness    → pricing table component, save it  
builds/bloom-flowers   → gallery grid component, save it

→ Future agents can pull from this component library for inspiration
```

### 9. 🌍 Multi-Language Support

The Copywriter Agent generates content in multiple languages. Blueprint includes `languages: ['en', 'es']`. Page agents generate `index.html` + `es/index.html`.

### 10. 📈 Post-Deploy Analytics Agent

A background agent checks the site 24h after deploy:
- Is it indexed by Google?
- Any console errors in production?
- Is the SSL cert working?
- Page load time from different regions?

Reports findings to the admin dashboard.

---

## 🗺️ Implementation Roadmap

### Sprint 1: Foundation (Current → v2 Core)
- [ ] Create `orchestrator/` folder structure
- [ ] Implement `lib/ai.js` — shared API wrapper with retry + rate limiting
- [ ] Implement `lib/emitter.js` — structured event system  
- [ ] Implement `lib/pool.js` — concurrent agent pool
- [ ] Port Phase 1 (repo creation) from bash to JS
- [ ] Port Phase 7 (deploy) from bash to JS
- [ ] Port Phase 8 (notify) from bash to JS

### Sprint 2: AI Council
- [ ] Implement Strategist agent with site blueprint output
- [ ] Implement Critic agent with review output
- [ ] Implement debate loop (2-3 rounds)
- [ ] Add `council` SSE events to runner
- [ ] Add Council Transcript panel to admin dashboard

### Sprint 3: Design System + Parallel Generation
- [ ] Implement Design System agent
- [ ] Implement page builder agent with design system injection
- [ ] Implement parallel agent pool for pages
- [ ] Implement per-page test + fix loop
- [ ] Add `agent:*` SSE events to runner
- [ ] Add Agent Grid view to admin dashboard

### Sprint 4: Assembly + Quality Gate
- [ ] Implement assembly phase (nav stitching, sitemap, 404, cross-links)
- [ ] Implement full-site integration test suite
- [ ] Implement parallel fix loops for failed pages
- [ ] Performance budget check (optional Lighthouse)

### Sprint 5: Polish + Outside-the-Box
- [ ] Content-first pipeline (separate copywriting agent)
- [ ] Reference site analyzer
- [ ] AI image prompt generation
- [ ] Client preview bot (Telegram screenshots)
- [ ] Incremental rebuild support

---

## 💰 Cost Analysis

### API Calls Per Build (v1 vs v2)

| Phase | v1 Calls | v2 Calls | Notes |
|-------|----------|----------|-------|
| Planning | 0 | 4-6 | 2-3 debate rounds × 2 AIs |
| Design System | 0 | 1 | One-time generation |
| Page Generation | 1 | 3-7 | One per page (parallel) |
| Fix Attempts | 0-2 | 0-10 | Per-page, up to 3 each |
| Assembly | 0 | 1 | 404 page generation |
| **Total** | **1-3** | **9-25** | ~10x more calls |

### Mitigation Strategies

1. **Caching**: Save design system patterns across builds for similar niches
2. **Prompt optimization**: Keep prompts tight to reduce tokens
3. **Smart skipping**: If critic approves in Round 1, skip Round 2-3
4. **Temperature tuning**: Low temp (0.3) for fixes, higher (0.7) for creative phases
5. **Model tiering**: Use `gpt-4o-mini` for simple tasks (404 page, sitemap), `gpt-4o` for creative work
6. **GitHub Models is free**: With the free tier we get ~150 requests/day — enough for ~6-8 full builds

---

## 🏁 Summary

The jump from v1 → v2 is a paradigm shift:

| Aspect | v1 | v2 |
|--------|----|----|
| Pages | 1 | 3-7+ |
| AI Calls | 1-3 | 9-25 |
| Planning | None | AI Council debate |
| Consistency | N/A (1 page) | Design System contract |
| Parallelism | None | Agent pool (3 concurrent) |
| Testing | 1 page | Per-page + integration |
| Orchestrator | Bash script | Node.js with EventEmitter |
| Admin View | Linear log | Agent grid + council transcript |
| Fix Scope | Whole site | Per-page targeted |
| Time | ~2 min | ~4-6 min (parallel helps) |

The architecture is **modular** — each phase is a separate file, each agent is independent. We can evolve any piece without rewriting the whole system.

**The AI Council alone would be a massive upgrade** — even if we kept single-page generation, having AIs debate the plan first would dramatically improve output quality.

---

> *"The best code is the code that writes itself — and then reviews itself."*  
> — AjayaDesign Engineering
