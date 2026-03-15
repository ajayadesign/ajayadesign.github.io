---
name: web-engine-pro
description: "High-fidelity web transformation, localization, creative evolution, and forensic QA engine. USE WHEN: rebuilding a website from a source URL or design reference, cloning and localizing a live site, optimizing assets, running visual regression tests, auditing SEO & accessibility, or generating premium client-facing reports. Covers asset extraction, image optimization, Playwright visual diffing, advanced SEO, accessibility audits, AjayaDesign branding, and creative UI/UX enhancement."
argument-hint: "Provide a source URL or project name to transform, and the Client/Project Name for the report"
---

# Web Engine Pro -- High-Fidelity Web Transformation, Evolution & QA

Transform a source URL or design reference into a localized, optimized, and tested web application. Act as a **Digital Conservator** for branding and content, but as a **Lead Design Engineer** for execution—preserve intent while upgrading the technical and visual stack. Conclude with a forensic audit and premium client-facing report.

## When to Use

Invoke this skill **start-to-finish** when creating a new client project from a source URL or design reference. All phases run in sequence.

- Rebuilding or cloning a client website from a live URL.
- Standing up a brand-new project folder with localized and *improved* assets.
- Generating a premium "Visual Truth" comparison report (`report.html`) for the client.

## Important Conventions

- **Self-contained projects:** Each project directory (e.g., `memory-magnets/`) is treated as its own deployable unit. All tests, configs (`playwright.config.js`, `package.json`), and assets live *inside* the project directory—not in the parent repo. The project will ultimately be hosted as its own GitHub Page.
- **Port 9222:** Local dev server runs via `npx serve . -l 9222` from the project root.
- **Directory-based URLs (SEO):** All pages use directory-based URL structure for clean, extensionless URLs. Use `magnet-making/index.html` not `magnet-making.html`. Product pages go in `products/<slug>/index.html`. Internal links use trailing-slash format (`magnet-making/`, `products/2x2-magnet-kit/`). This ensures URLs like `/magnet-making/` work cleanly on any static host.
- **Parallelization via Subagents:** Maximize throughput by spawning subagents for independent work streams. When multiple phases or tasks have no dependencies on each other, run them in parallel using `runSubagent`. Examples:
  - Phase 1 asset extraction + Phase 2 optimization scripting (prep) can overlap.
  - Category page creation and product page creation can be split across subagents (one per category or batch of products).
  - SEO audit (Phase 6), UI/UX check (Phase 4), and identity injection (Phase 5) are independent — run all three in parallel.
  - Screenshot retakes, test suite updates, and report.html updates are independent — parallelize.
  - **Rule:** If task A does not depend on the output of task B, they SHOULD be parallelized. Prefer spawning 2-4 subagents over sequential execution. Each subagent prompt must be self-contained with full context.

## Procedure

### Phase 1 -- Intelligence & Asset Localization

1. **Extract** all CSS, JS, images (webp/png/jpg), and fonts recursively from the source URL.
2. **Distill Content:** Scrape core value propositions, text, and brand colors to use as the foundation for the build.
3. **Normalize paths** -- rewrite all `url()` in CSS and `src`/`href` in HTML to local `./css/`, `./js/`, `./images/` paths.
4. **Generate SRI hashes** for all local scripts (`integrity` attribute) to prevent tampering.
5. **Organize** into the standard self-contained project layout:
```
<project-name>/
├── index.html
├── about.html / contact.html / services.html ...
├── report.html
├── package.json
├── playwright.config.js
├── css/
├── js/
├── images/
├── screenshots/
└── tests/
```

### Phase 2 -- Asset Optimization & Enhancement (Python)

Generate and run a `process_assets.py` script. Skip only if assets are already optimized.

1. **Lossless compression** -- use Pillow to optimize images; convert to WebP/AVIF. Target: < 200 KB per image, < 500 KB for hero images.
2. **Smart cropping** -- detect focal points in hero images to preserve context on mobile.
3. **SVG reconstruction** -- attempt SVG conversion via potrace for small, simple PNG icons.
4. **Sprite sheets** -- combine small icons into a single SVG sprite.
5. **Steganographic Watermarking:** Inject "AjayaDesign Build [UUID]" into the metadata of all processed images for ownership tracking.

### Phase 3 -- Visual Fidelity & Creative Evolution (Playwright)

1. **Screenshot Original:** Capture the source URL (full-page, desktop + mobile).
2. **Creative Mandate:** While maintaining brand colors and content, the agent is authorized to improve layout, spacing, and modern UI components if the original is outdated.
3. **Local Build Capture:** Serve on port **9222** (`npx serve . -l 9222`) from the project directory and screenshot.
4. **Visual Analysis:** Run pixel-diff comparison.
   - *Note:* If the design was intentionally evolved, the "Threshold gate" (5%) applies to **Content Parity**, not necessarily exact pixel placement. Fix any unintended breakage before proceeding.

> **CRITICAL — Lazy-Load Screenshot Fix:**
> All Playwright screenshots (full-page captures for report, mobile proof, visual comparisons) MUST handle `loading="lazy"` images. Before capturing:
> 1. Remove `loading="lazy"` from all `<img>` elements via `page.evaluate()`.
> 2. Force re-fetch by resetting each `img.src` (clear then restore).
> 3. Scroll incrementally through the full page height to trigger IntersectionObserver callbacks.
> 4. Wait for ALL images to report `img.complete && img.naturalHeight > 0`.
> 5. Scroll back to top, wait 300-500ms, then capture.
> Failure to do this results in blank/missing images in screenshots — especially in the report's Mobile-First Validation section.

### Phase 3.5 -- Individual Pages & Product Pages (SEO)

Every navigation item and every product/item should have its own dedicated HTML page. This is critical for SEO — each page becomes a unique indexable entry point with its own `<title>`, `<meta description>`, Schema.org structured data, and keyword targeting.

1. **Category/Section Pages:** Create a dedicated page for each primary navigation item, using directory-based URL structure (e.g., `magnet-making/index.html`, `custom-magnets/index.html`, `start-a-business/index.html`). Each page gets:
   - Unique `<title>` and `<meta name="description">`.
   - Dedicated hero/header section with category-specific content.
   - Full product listings for that category (expanded from the homepage summary).
   - JSON-LD Schema.org markup (`ItemList`, `OfferCatalog`, or relevant type).
   - Breadcrumb navigation for hierarchy.
2. **Product Detail Pages:** Create a dedicated page for each individual product/item using directory-based URLs (e.g., `products/2x2-magnet-kit/index.html`). Each page gets:
   - Unique `<title>` with product name and brand.
   - Unique `<meta name="description">` focused on that product.
   - JSON-LD `Product` Schema with `name`, `description`, `image`, `offers` (price, availability, currency).
   - Full product description, features, and larger images.
   - Breadcrumb trail: Home > Category > Product.
   - Internal links back to category and related products.
3. **Navigation Updates:** Update `<nav>` links on ALL pages (index, contact, category pages, product pages) to point to the real directory-based pages using trailing slashes (e.g., `magnet-making/`, `products/2x2-magnet-kit/`). Keep anchor links on the homepage as secondary shortcuts.
4. **Sitemap & Internal Linking:** Update `sitemap.xml` to include all new pages. Ensure strong internal linking between category pages, product pages, and the homepage.
5. **Consistent Layout:** All new pages must share the same nav, footer, CSS, and design system as the homepage. Reuse the glassmorphic nav, footer branding, and identity markers.

### Phase 4 -- UI/UX Quality Check (Shneiderman's 8 Rules)

Verify the build against these standards:

| # | Rule | Check |
|---|------|-------|
| 1 | Consistency | Uniform button styles, typography, spacing |
| 2 | Shortcuts | `Ctrl/Cmd+K` search, `Esc` to close modals |
| 3 | Feedback | Hover/active states on all interactive elements |
| 4 | Closure | Form submissions show clear success/confirmation |
| 5 | Error Prevention | Client-side input validation before submission |
| 6 | Reversal | Cancel/Undo options for destructive actions |
| 7 | Control | No auto-playing video or unexpected pop-ups |
| 8 | Memory Load | Clear breadcrumbs, grouped information |

### Phase 5 -- Identity & Security

1. **Footer branding**: inject `"Developed for Demo - Owned by AjayaDesign."` in global footer.
2. **Build signature meta tag**: `<meta name="x-build-signature" content="AjayaDesign-[TIMESTAMP]-[UUID]">`
3. **CSS fingerprint**: invisible class on the `main` container.
4. **Steganography Check:** Verify the "AjayaDesign Build" watermark in the EXIF data of optimized images.
5. **Access control**: generate `.htaccess` or `firebase.json` protection rules if requested.

### Phase 6 -- Advanced SEO & Discoverability Audit

Audit the site for modern search engine superiority.

1. **Semantic Architecture:** Ensure proper use of `<header>`, `<nav>`, `<main>`, `<article>`, and logical `H1` -> `H6` nesting (no skipped heading levels).
2. **Metadata & Open Graph:** Verify unique `<title>`, `<meta name="description">`, and rich social sharing tags (`og:title`, `og:image`, `og:description`, `twitter:card`) on every page.
3. **Schema.org Markup:** Ensure injected JSON-LD structured data exists (e.g., `LocalBusiness`, `WebSite`, `Store`, or `Organization` schemas) to help Google understand the business entity.
4. **Core Web Vitals Readiness:** Confirm that critical CSS is prioritized and images have explicit `width` and `height` attributes to prevent Cumulative Layout Shift (CLS).
5. **Canonical & Robots:** Verify `<link rel="canonical">` on each page. Ensure `robots.txt` and `sitemap.xml` exist and are correct.

### Phase 7 -- Automated Testing (Per-Project)

All testing infrastructure lives **inside** the project directory. Create a `playwright.config.js` and `package.json` at the project root, and a `tests/` folder for specs.

**Pre-Test Link & Path Audit (MANDATORY before running tests):**

Before executing any test suite, run a comprehensive audit of every HTML file to catch broken relative paths. This is the #1 source of bugs when using directory-based URLs.

1. **Classify each file by depth:** Root files (`index.html`) use bare paths (`css/`, `images/`). Level-1 files (`magnet-making/index.html`, `contact/index.html`) need `../` prefix. Level-2 files (`products/2x2-magnet-kit/index.html`) need `../../` prefix.
2. **Audit asset references:** `href="css/"`, `src="images/"`, `src="js/"` must have the correct `../` depth.
3. **Audit internal page links:** Nav, footer, breadcrumb, and inline links to other pages (`magnet-making/`, `contact/`, `products/X/`) must have the correct `../` depth for the current file's location.
4. **Audit JSON-LD schema URLs:** `"url":` and `"item":` values in `<script type="application/ld+json">` blocks must also use correct relative depth.
5. **Audit home links:** Logo and breadcrumb "Home" links must point to the project root at the correct depth (`./` for root, `../` for level-1, `../../` for level-2).
6. **Live HTTP check:** Start the dev server and `curl` every page URL + key assets to confirm 200 status codes, zero 404s.

> **Rule of thumb:** A file at depth N needs N `../` segments to reach a root-level asset. `magnet-making/index.html` (depth 1) → `../css/styles.css`. `products/kit/index.html` (depth 2) → `../../css/styles.css`.

1. **Playwright Suite (inside `<project>/tests/`):**
   - Axe-core accessibility audit (Target: score >= 98, zero critical/serious violations).
   - HTML structure & content validation.
   - Mobile compatibility (Responsive viewports: 375px, 768px, 1440px).
   - Contact form validation (empty submit blocked, valid submit shows success).
   - Navigation & scroll interactions.
   - Identity marker verification (build signature, footer branding).
2. **Console Integrity:** Run a headless browser check. Fail if there are any 404s, broken links, or JavaScript console errors.

### Phase 8 -- Premium Client Report (`report.html`)

Generate a high-fidelity, standalone, responsive `report.html` inside the project directory. This is the final client-facing deliverable.

**Structure of `report.html`:**

1. **Welcome Section (Hero Section):**
   - **Header:** "Project Audit & Design Evolution Report"
   - **Find the owner's name:** Before writing the report, scrape the source website (homepage, about page, contact page, social media links like TikTok/Instagram/Linktree) to find the business owner's first name. Address the report directly to them (e.g., "Hi Sariah" not "Hi Memory Magnets team"). This personal touch matters — it shows we did our research and built this *for them*, not generically. If the name cannot be found, fall back to the business name.
   - **Personalized Message:** Synthesize a custom 2-3 paragraph welcome note that references specifics about *their* business — their products, their audience, their growth story. Avoid generic templates.
     *Template constraint:* "Hi [Owner First Name], at AjayaDesign, we don't just build websites; we engineer digital assets. This report details the specific performance, SEO, and design upgrades we implemented to ensure your brand outpaces the competition..."

2. **The "Why This is the Greatest" Breakdown (Value Translation):**
   Explicitly translate technical work into business value for the client:
   - **Speed = Revenue:** "By converting your images to next-gen formats (WebP/AVIF) and reducing payload by X%, your site loads near-instantly, drastically reducing bounce rates."
   - **SEO & Discoverability:** "We implemented advanced JSON-LD Schema markup and Semantic HTML. This means Google doesn't just 'read' your site; it understands your business entity, giving you a distinct advantage in local and global search rankings."
   - **Accessibility = Reach:** "A perfect score on our Axe-Core audit means your site is legally compliant and usable by 100% of your audience, including those with disabilities."

3. **The Visual Truth (Interactive Sliders):**
   - Implement vanilla JS/CSS draggable side-by-side comparison sliders.
   - Show the "Before" (Original Source) vs. "After" (AjayaDesign Build).
   - Include a thumbnail carousel to navigate between different page comparisons (Home, About, Contact, etc.).

4. **The Evolution Narrative:**
   - Below the sliders, output a structured list of the UX upgrades made.
   - Examples: "Moved CTA above the fold," "Implemented Bento Grid for scannability," "Upgraded typography for modern readability."

5. **Technical Triumphs (Metrics Dashboard):**
   - **Speed/Optimization:** Display visual badges for space saved (e.g., "Image payload reduced by 78%").
   - **Lighthouse/Axe-core Scores:** Display scores in circular progress indicators (aiming for 95+ in Performance, Accessibility, Best Practices, and SEO).
   - **Mobile-First Validation:** Show the 375px viewport screenshot proving mobile readiness. **The screenshot MUST be captured with the lazy-load fix** (see Phase 3 critical note) — all images must be fully rendered, no blank placeholders.

6. **Project Sign-off (Quality Assurance & Delivery):**
   - Display a professional sign-off block confirming the project has passed all quality checks.
   - List client-facing quality milestones: automated tests passed, accessibility compliance, image optimization results, SEO verification, mobile-first validation.
   - **IMPORTANT:** Do NOT reveal hidden identity markers to the client. Do NOT mention CSS fingerprint classes, data-fingerprint attributes, steganographic EXIF watermarks, or build-signature meta tags in the report. These are internal AjayaDesign tracking mechanisms and must remain invisible to the client. Only mention visible branding (footer text) if relevant.