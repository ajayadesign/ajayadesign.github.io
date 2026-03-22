# AJAYADESIGN 2.0: THE ENGINEERING-GRADE REFACTOR PLAN

## // Project Overview
Transform **ajayadesign.github.io** from a single-page landing site into a high-performance, multi-page "Scrollytelling" engine. 

**The Narrative Arc:**
1. **Home (The Vision):** Macro Drone Lens — focusing on visibility and SEO elevation.
2. **The Edge (The Logic):** Glowing PCB Traces — engineering the "Silicon Trace" of high-performance code.
3. **Works (The Build):** 3D Printer Nozzle — "printing" growth, SERP charts, and 29+ successful site deployments.

---

## 01. Visual Asset Generation (AI Vision Prompts)
Use these prompts in Midjourney v6.1 or DALL-E 3 to generate the keyframes for your scroll-animations.

### Shot A: Home Page (The Drone Lens)
* **Start Frame Prompt:** `Extreme macro photography of a DJI Mavic 3 camera lens, cinematic lighting, matte black carbon fiber textures, dark moody atmosphere. The lens glass is deep and clear with subtle iridescent purple coatings. 8k resolution, photorealistic.`
* **End Frame Prompt:** `Extreme macro of a drone camera lens, zoomed in closer. Reflected in the glass is a glowing neon green "100" Lighthouse Score and a sharp Google Search "G" logo. High-contrast, tech-noir aesthetic.`

### Shot B: The Edge (The PCB Traces)
* **Start Frame Prompt:** `Macro top-down view of a high-end black PCB motherboard, gold traces are dark and unlit. Minimalist engineering layout, sharp shadows, industrial design.`
* **End Frame Prompt:** `Same PCB view, but the gold traces are surging with electric green neon light, pulses of data flowing through the circuits toward a central glowing AMD-style CPU socket. High-energy data flow.`

### Shot C: Works Page (The 3D Printer Nozzle)
* **Start Frame Prompt:** `Cinematic side-view of a 3D printer nozzle (Anycubic Kobra style) hovering over a dark glass print bed. A single drop of neon green translucent filament is touching the bed. Dark background, precise engineering focus.`
* **End Frame Prompt:** `The 3D printer nozzle is finishing a print of a 3D bar chart with three bars of increasing height. The filament is glowing green. The final bar has a small "1st Place" icon on top. Symbolic of SEO growth.`

---

## 02. Video Generation & AI Tools Workflow
Once you have the frames, use these tools to create the motion between them.

### Recommended AI Video Generators (2026 Edition)
1. **Kling.ai (International):** Use the "End Frame" feature to ensure the drone lens perfectly lands on the Lighthouse reflection.
2. **Luma Dream Machine:** Best for the "PCB Flow" animation where lighting transitions are complex.
3. **Runway Gen-3 Alpha:** Best for hyper-realistic textures in the 3D printer nozzle movement.
4. **Pika.art:** Use for "Cinemagraph" loops if you want a subtle idle state.

### The Optimization Pipeline (Ezgif/Squoosh)
* **Step 1:** Generate video in 4K at 60 FPS.
* **Step 2:** Upload to **Ezgif** -> "Video to JPG/WebP Sequence".
* **Step 3:** Reduce to **12 FPS**. For scroll-animations, the browser interpolates frames; 60 FPS is too heavy.
* **Step 4:** Run all frames through **Squoosh.app** for bulk WebP conversion (Goal: < 40kb per frame).

---

## 03. AI Copilot Execution Protocol (The Transition)
Copy and paste these prompts into **Cursor** or **GitHub Copilot** to automate the refactor.

### Phase 1: Static Multi-Page Architecture
Split the current `index.html` into dedicated static pages. No SPA routing needed — GitHub Pages serves real HTML files natively.

**File Structure:**
```
/index.html              ← Drone Lens hero (lightweight gateway)
/edge/index.html         ← PCB Traces deep-dive
/works/index.html        ← 3D Nozzle + portfolio grid
/contact/index.html      ← Intake form
```

**Shared Components:**
- Duplicate `<nav>` and `<footer>` in each page (simplest, zero JS overhead), OR use a tiny `fetch()` injector to load `/partials/nav.html` and `/partials/footer.html` at DOMContentLoaded.

**Fast Page Transitions:**
1. Add `<link rel="prefetch" href="/edge/">` and `<link rel="prefetch" href="/works/">` in the home page `<head>` — browser pre-fetches in the background, making clicks feel instant.
2. Use the **View Transitions API** (CSS `@view-transition`) for cross-page morphing animations. Supported in Chrome/Edge, graceful fallback to instant navigation elsewhere.
3. Ensure all Tailwind CSS links and asset paths use root-relative URLs (`/css/styles.css`, `/js/main.js`).

### Phase 2: Per-Page Scroll-Sync Engine
Each page loads **only its own** animation assets — no cross-page payload pollution.

### Phase 2.5: Mobile-First & Reduced-Motion Mode
Add a dedicated mobile/low-motion fallback on every page so the desktop scrollytelling experience does not punish phones.

1. Add `prefers-reduced-motion` and `max-width: 768px` rules in `css/styles.css`:
   - force hero video `display: none`, show `img.hero-poster` instead.
   - reduce `.scroll-hero` height to `210vh` (or `250vh`) on mobile.
   - shrink the 3-cta stats grid to `grid-cols-1` under `sm:`.
   - enlarge touch targets on `#mobile-menu-btn`, navigation links, and `.cta-btn` to min `44px` hit area.

2. Add JS guard in `js/main.js`:
   - `const isMobile = window.matchMedia('(max-width: 768px)').matches;`
   - `const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;`
   - if either is true, deactivate scrollytelling animation engine and ensure `video` is paused/hidden.
   - set `document.body.classList.add('reduced-motion')` when reduced motion.

3. On desktop, keep current behavior; on mobile, use hero poster + minimal animated underline on copy.

4. Ensure `mobile-menu` toggling locks body scroll when open:
   - `document.body.style.overflow = 'hidden'` when open, `auto` when closed.

**Quick targets:**
- Home, Edge, Works: static first-frame poster + single legacy card fallback (no video) on mobile.
- Contact: native form + field sizes already good.
- ASAP: load 90+ Lighthouse for mobile on each page.

**Bridge to Phase 3:**
- mobile behavior should be tested by Playwright via 375x667 viewport (iPhone SE path), including “no more than 3s TTI”, “no animation jitter”, and “menu tappable in 44px hotspots”.

**Note:** this phase is mandatory before desktop feature completion; it should not be optional.
- **Option A — Short looping video:** A 3-5s `<video>` (WebM/MP4, ~500-800KB) synced to scroll via CSS `scroll-timeline` or the `ScrollTimeline` JS API. Lightest payload, best browser support trajectory.
- **Option B — Canvas frame sequence:** `PrecisionScrollEngine` class draws pre-loaded WebP frames to a `<canvas>` mapped to scroll position. Heavier payload (60-120 frames × ~40KB = 2.4-4.8MB per page), but smoother on desktop.

**Shared Engine Requirements (either approach):**
1. Map `window.scrollY` (0 to 100% of the scrollytelling section) to playback progress.
2. Use `requestAnimationFrame` for rendering — zero layout shift.
3. **Mobile fallback:** Disable animation engine entirely. Replace with a single high-quality static WebP hero image for battery efficiency and fast LCP.
4. Preload the first frame / poster image for instant visibility; lazy-load the rest.
5. Each page's animation assets live in their own directory: `/assets/frames/drone/`, `/assets/frames/pcb/`, `/assets/frames/nozzle/`.

### Phase 3: Metadata & SEO Migration
> **Prompt:** "Analyze my current single-page SEO metadata. 
> 1. Generate unique `title` and `meta description` tags for the new `/edge` and `/works` pages. 
> 2. For `/works`, create a JSON-LD schema that lists my 29+ portfolio projects as 'CreativeWorks' with their respective URLs and performance scores. 
> 3. Update the `sitemap.xml` to reflect the new multi-page structure."

---

## 04. Information Migration Plan

### `index.html` — The Trailer (Drone Lens)
A **lightweight gateway page** — 4-5 viewport heights max. Loads fast, hits Lighthouse 100, hooks the visitor, and funnels them deeper.
* **Content:** Hero Headline, "Your Next Customer" text, Terminal "Checking..." animation, social proof metrics (25+ sites, <24hr, $0 down).
* **Scroll Animation:** The **Drone Lens Zoom** — only animation on this page. Camera lens zooms until the "100" Lighthouse score reflection fills the viewport.
* **CTAs at bottom:** "See The Engineering" → `/edge/` | "See The Builds" → `/works/`
* **Prefetch:** `<link rel="prefetch" href="/edge/">` and `<link rel="prefetch" href="/works/">` in `<head>` so the next page loads instantly on click.

### `/edge/index.html` — Episode 1: The Logic (PCB Traces)
Dedicated deep-dive page — **6-8 viewport heights** of scroll runway for the full PCB animation experience.
* **Content:** "The Edge" (Speed/Systems/Automation), "The Gadget Den Legacy" origin story, and the **Drone Builder Checklist**.
* **Scroll Animation:** The **PCB Data Flow** owns the entire page. Traces light up progressively as user scrolls. At 100% lit, the "Drone Builder Checklist" terminal window slides in from the right.
* **Logic:** This proves the "Hardware-level precision" claim with room to breathe — no competing animations.
* **CTA at bottom:** "See The Builds" → `/works/`

### `/works/index.html` — Episode 2: The Build (3D Nozzle)
Dedicated portfolio showcase — needs ALL the scroll room for 27+ project cards.
* **Content:** The full project portfolio with live iframe previews.
* **Scroll Animation:** The **3D Printer Nozzle** is `position: sticky` at the top. As user scrolls, the nozzle moves horizontally, "printing" the top border of each project card as it appears.
* **Terminal Filter:** `ls -category` filter bar for: `local-biz/`, `ecommerce/`, `services/`, `fitness/`, `creative/`, `retail/`
* **CTA at bottom:** "Start Your Build" → `/contact/`

---

## 05. The "Zero-Defect" Quality Audit
Before final deployment to GitHub Pages:
1.  **Lighthouse Check (per page):** Each page (`/`, `/edge/`, `/works/`, `/contact/`) must hit **95+ Performance**. Home page target: **100**.
2.  **Navigation Test:** Navigate `Home → Edge → Works → Contact` using CTAs, then use the browser's "Back" button through the full chain. Each transition should feel instant (prefetch).
3.  **Direct URL Test:** Paste `ajayadesign.github.io/edge/` directly into the browser — it must load correctly without redirects (static files, no SPA hack).
4.  **Terminal Accuracy:** Ensure the "Drone Builder Checklist" references are consistent across all pages.
5.  **Playwright Test Migration:** Update `tests/accessibility.spec.js` to cover the multi-page structure — test nav links, anchor IDs, form fields, and axe accessibility audits on all 4 pages.
6.  **Mobile Audit:** Verify animation fallback (static WebP) loads on mobile. No canvas/video on touch devices.