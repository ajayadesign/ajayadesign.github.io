# 3D Print Academy — Link Integrity Audit Report

**Date:** 2026-04-05  
**Branch:** `clawbot-overnight-patch-2026-04-05`  
**Auditor:** CBabe (automated)

---

## Summary

| Metric | Count |
|--------|-------|
| HTML pages crawled | 33 |
| Total link references extracted | 395 |
| Internal links (OK) | 214 |
| External links checked | 168 (16 unique non-CDN) |
| Broken links found | 0 |
| STL files on disk | 22 |
| PDF files on disk | 0 |

### Overall Status: ✅ HEALTHY

No broken links, no missing assets, no domain migration issues detected.

---

## Detailed Findings

### 1. Hardcoded Domain Check
- **`ajayadesign.github.io` references:** ✅ None found
- **`http://` (insecure) references:** ✅ None found
- Domain migration from GitHub Pages to `ajayadesign.com` appears complete.

### 2. Internal Links
All 214 internal links resolve correctly. Pages link to each other using relative paths consistently.

**Note:** 3 pages use `href="/"` to link to site root — this is intentional and correct:
- `3D-print/index.html:271` (logo/home link)
- `3D-print/index.html:1350` (footer "Home" link)
- `3D-print/portal/admin.html:40`, `3D-print/portal/index.html:45`

### 3. External Links — All Alive (HTTP 200)
| URL | Status |
|-----|--------|
| `https://ajayadesign.com/3D-print/` | 200 ✅ |
| `https://buy.stripe.com/6oUbJ06jF2s87U72lG7Re08` | 200 ✅ |
| `https://buy.stripe.com/8x2aEW6jF6Iofmz7G07Re09` | 200 ✅ |
| `https://buy.stripe.com/9B6aEWazV3wccanf8s7Re0a` | 200 ✅ |
| `https://buy.stripe.com/8x2dR8eQb9UAfmzgcw7Re0b` | 200 ✅ |
| `https://drive.google.com/drive/folders/...` | 200 ✅ |
| `https://www.youtube.com/@AJDESIGN-y8m` | 200 ✅ |

CDN/infrastructure links (Google Fonts, Tailwind CDN, Firebase JS, Google Tag Manager, Clarity, Calendly) — all standard and reliable.

### 4. Asset Pathing Audit
- **STL files:** 22 files exist in `3D-print/stl-files/` — none are directly linked from HTML (referenced by display name only in portal module pages)
- **Images:** Gallery uses Unsplash URLs (external, reliable). No local image `src` attributes found.
- **YouTube embeds:** No `<iframe>` YouTube embeds found. YouTube channel links go to `@AJDESIGN-y8m` (verified alive).
- **No broken image references detected.**

### 5. Template Placeholders (Not Bugs)
These are correctly template-interpolated at runtime:
- `{{UNSUBSCRIBE_URL}}` in 5 email templates under `automation/templates/` — email system replaces at send time
- `${item.src}` in `gallery/index.html` — JavaScript template literal, renders correctly in browser

---

## Issues by Severity

### Critical
None.

### Warning
None.

### Cosmetic
| File | Line | Note |
|------|------|------|
| `gallery/index.html` | — | Uses Unsplash stock photos rather than actual product photos. Consider replacing with real 3D-printed frame images for authenticity. |
| `portal/downloads.html` | 85 | Google Drive folder link — verify sharing permissions are set to "Anyone with the link" for student access. |
| `free/index.html` | 231-232 | Uses Firebase JS SDK v9.23.0 while portal pages use v11.4.0. Consider aligning versions. |

---

## Fixes Applied
No fixes were needed — the 3D Print Academy link structure is clean and well-maintained.

---

## Recommendations
1. **Firebase SDK version alignment:** `free/index.html` uses v9.23.0 while all portal pages use v11.4.0. Upgrading the free page would ensure consistent behavior.
2. **Gallery images:** Replace Unsplash stock photos with actual product photography for better conversion.
3. **STL download links:** Portal module pages display STL filenames but don't provide direct download links. Consider adding download buttons pointing to `stl-files/` directory.
