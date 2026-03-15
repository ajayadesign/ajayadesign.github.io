---
name: web-engine-pro
description: "High-fidelity web transformation, localization, and validation engine. USE WHEN: rebuilding a website from a source URL or design reference, cloning and localizing a live site, creating a new client project folder, optimizing assets, running visual regression tests, generating comparison reports. Covers asset extraction, image optimization, Playwright visual diffing, accessibility audits, AjayaDesign branding, and CI/CD gating."
argument-hint: "Provide a source URL or project name to transform"
---

# Web Engine Pro -- High-Fidelity Web Transformation

Transform a source URL or design reference into a localized, optimized, and tested web application. Act as a Digital Conservator -- preserve design intent while upgrading the technical stack.

## When to Use

Invoke this skill **start-to-finish** when creating a new client project from a source URL or design reference. All seven phases run in sequence.

- Rebuilding or cloning a client website from a live URL
- Standing up a brand-new project folder with localized assets
- Generating a full comparison report (`report.html`) for the client

## Procedure

### Phase 1 -- Asset Acquisition & Localization

1. **Extract** all CSS, JS, images (webp/png/jpg), and fonts recursively from the source URL.
2. **Normalize paths** -- rewrite all `url()` in CSS and `src`/`href` in HTML to local `./css/`, `./js/`, `./images/` paths.
3. **Generate SRI hashes** for all local scripts (`integrity` attribute) to prevent tampering.
4. **Organize** into the standard project layout:
   ```
   <project-name>/
   ├── index.html
   ├── about.html / contact.html / services.html ...
   ├── report.html
   ├── css/
   ├── js/
   ├── images/
   └── screenshots/
   ```

### Phase 2 -- Asset Optimization (Python)

Generate and run a `process_assets.py` script. Skip only if **all** images are already WebP/AVIF and under 200 KB each.

1. **Lossless compression** -- use Pillow to optimize images; convert to WebP/AVIF. Target: no image over 200 KB unless it's a full-page hero.
2. **Smart cropping** -- detect focal points in hero images to preserve context on mobile.
3. **SVG reconstruction** -- if a PNG is under 10 KB and has fewer than 4 colors, attempt SVG conversion via potrace.
4. **Sprite sheets** -- if there are 4+ small icon images (<5 KB each), combine into a single SVG sprite.

### Phase 3 -- Visual Fidelity & Regression (Playwright)

1. Screenshot the **original URL** (full-page, desktop + mobile).
2. Serve the **local build** on port **9222** (`npx serve . -l 9222`) and screenshot it.
3. Run pixel-diff comparison (pixelmatch or similar).
4. **Threshold gate**: if pixel difference exceeds **5%**, fix CSS/layout before proceeding.

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
4. **Access control** (if requested): generate `.htaccess` or `firebase.json` password protection rules.

### Phase 6 -- Automated Testing & CI/CD

1. Run **Playwright** test suite:
   - Axe-core accessibility audit (target: score >= 90)
   - HTML5 validation
   - Mobile compatibility (responsive viewports)
2. Ensure the existing **GitHub Actions** workflow gates deployment on:
   - Visual regression pass (<=5% diff)
   - Accessibility score >= 90
   - All assets have fingerprints

### Phase 7 -- Project Report

Generate `report.html` with:

- Side-by-side screenshot comparison (Original vs. New)
- Performance badges (Lighthouse scores)
- Asset optimization summary (space saved, formats converted)
- Accessibility audit results
- AjayaDesign branding confirmation