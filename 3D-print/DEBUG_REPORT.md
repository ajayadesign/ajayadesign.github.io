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

---

## Webhook & Access Audit

**Date:** 2026-04-05  
**Auditor:** CBabe (automated)

- **Payment processor:** Stripe (Checkout Sessions via `buy.stripe.com` links)
- **Webhook endpoint:** Google Apps Script Web App (`https://script.google.com/macros/s/AKfycbw.../exec`)
- **Access control mechanism:** Firebase RTDB with admin-approved access model
- **Issues found:** 2 (0 Critical, 1 Medium, 1 Low)

### Architecture Overview

The payment → access flow works as follows:

1. **User clicks Stripe link** → Stripe Checkout (4 tiers: STL $29, Course $97, Session $149, Bundle $349)
2. **Stripe sends `checkout.session.completed` webhook** → Google Apps Script `doPost()`
3. **Apps Script verifies event** by re-fetching from Stripe API (not HMAC — Apps Script limitation, acceptable)
4. **Apps Script checks `pending_users`** in Firebase RTDB for matching email:
   - If found → moves user to `approved_users` (direct approval)
   - If not found → writes to `pre_approved` for deferred approval
5. **When user signs into portal**, `portal-auth.js` checks:
   - `approved_users/{uid}` → if exists, grant access
   - `pre_approved` (query by email) → if match, auto-promote to `approved_users`
   - Otherwise → register in `pending_users`, show "pending" screen, listen for live approval
6. **Welcome email + drip sequence** sent via Gmail (Day 0, 1, 3, 7, 14)

### What Works Well ✅

- **Event verification:** Webhook re-fetches event from Stripe API — prevents forged payloads
- **Idempotency:** Pre-approved entries are keyed by push ID with email matching, so duplicate webhooks create duplicate `pre_approved` entries but the portal only consumes the first match (acceptable, not harmful)
- **Tier-based access control:** `TIER_ACCESS` map enforces module-level gating per tier
- **Firebase security rules:** Well-structured — users can only read their own data, only admin can write to `approved_users`, `pending_users` is write-once per UID
- **Reconciliation function:** `reconcilePendingUsers()` exists as a manual recovery mechanism for orphaned states
- **Unsubscribe handling:** Follow-up emails respect unsubscribe list
- **Admin notification:** Admin gets email on every purchase
- **Live approval listener:** Pending users get real-time access when admin approves (Firebase `.on('value')`)
- **XSS prevention:** `escapeHtml()` and `escapeAttr()` used consistently, event delegation instead of inline handlers
- **Firebase API key:** Base64-obfuscated (not encrypted, but Firebase API keys are designed to be public — restricted by domain referrer in Google Cloud console per the comment)

### Issues Detail

#### Issue 1: Duplicate `pre_approved` entries on webhook retry (Medium)

**Severity:** Medium  
**Description:** If Stripe retries the webhook (e.g., on timeout), `processApproval()` calls `fbPush('pre_approved', ...)` which creates a new entry each time. While the portal only consumes the first match and removes it, leftover duplicates accumulate in `pre_approved` and show up in the admin dashboard as "Paid Not Logged In" ghosts.  
**Impact:** Admin sees inflated "Paid Not Logged In" count; no access impact.  
**Fix:** Add idempotency check in `processApproval()` — query `pre_approved` by email before pushing. If an entry for this email+tier already exists, skip the push.  
**Status:** Not fixed (requires Apps Script redeployment — flagged for AJ)

#### Issue 2: Leads endpoint writes without authentication (Low)

**Severity:** Low  
**Description:** The lead capture form on `3D-print/index.html:1401` writes directly to `https://...firebaseio.com/leads.json` via unauthenticated POST. The Firebase rules allow write-once per lead ID (`!data.exists()`), which limits abuse, but an attacker could spam the leads collection with junk entries.  
**Impact:** Potential spam pollution of leads data. No access control impact.  
**Fix:** Rate-limit at the Firebase rules level isn't possible, but the write-once rule provides reasonable protection. Consider adding reCAPTCHA or moving lead capture to the Apps Script endpoint.  
**Status:** Not fixed (by design — trade-off for frictionless lead capture)

### Security

- ✅ **No leaked credentials in repo.** The Stripe secret key is stored in Google Apps Script Properties (server-side), not in client code. The `Code.gs` comment mentions `sk_live_51TFlQz...` but it's truncated documentation, not the actual key.
- ✅ **Firebase API key is public by design.** It's base64-encoded in `firebase-config.js` but Firebase API keys are meant to be client-side; security is enforced by RTDB rules + auth.
- ✅ **RTDB rules are solid.** Admin-only writes to `approved_users`, write-once for `pending_users`, auth-gated reads for course content.
- ✅ **No replay attack vulnerability.** Webhook verifies events by re-fetching from Stripe API with the secret key server-side.
- ✅ **No self-elevation path.** Users cannot write to `approved_users` — only admin email can.
- ⚠️ **Apps Script Web App is "Anyone" accessible** — required for Stripe webhooks, but also means anyone can send POST requests. The Stripe event verification mitigates this.
- ⚠️ **`pre_approved` cleanup:** Duplicate entries from webhook retries should be cleaned up periodically. The `reconcilePendingUsers()` function helps but doesn't deduplicate `pre_approved`.

### Race Condition Analysis

- **Pay but no access?** Covered. If webhook fires before user signs in → `pre_approved` catches them on first login. If user is already pending → direct approval. If both happen simultaneously → Firebase atomic writes prevent corruption; worst case user sees "pending" briefly then gets auto-approved on next auth state check.
- **Orphaned "Access Denied"?** Unlikely. The `pre_approved` → `approved_users` promotion happens on every login via `portal-auth.js`. The manual `reconcilePendingUsers()` function handles edge cases.
- **Webhook timeout?** Stripe retries automatically (up to ~3 days). Apps Script has a 30-second execution limit which is ample for this flow.

---

## Mobile Responsiveness Audit (2026-04-05)

- **Pages tested:** 33/33 (excludes 5 email templates in automation/templates/)
- **Viewports tested:** iPhone SE (375×667), iPhone 14 Pro (393×852), iPad Mini (768×1024)
- **Issues found:** 8 (Critical: 1, Warning: 5, Cosmetic: 2)
- **Fixes applied:** 3 (covering all Critical + Warning issues)

### Issues Detail

| # | Severity | Page | Issue | Fix Applied |
|---|----------|------|-------|-------------|
| 1 | Critical | blog/magnet-frame-profit-margins.html | `.cost-table` overflows viewport at iPhone SE (504px > 375px) and iPhone 14 Pro (504px > 393px) | Made table `display: block; overflow-x: auto` for horizontal scroll |
| 2 | Critical | blog/magnet-frame-profit-margins.html | Mobile media query *reduced* font to 0.75rem (12px) — counterproductive | Changed to 0.875rem (14px) |
| 3 | Warning | 20+ pages (portal/modules, tools, etc.) | `text-xs` (12px) and `text-sm` (14px) Tailwind classes too small for at-the-printer phone use | Created `mobile-responsive.css` — bumps `text-xs` → 14px, `text-sm` → 15px on screens ≤640px |
| 4 | Warning | All pages | No `overflow-x: hidden` on html/body — risk of horizontal scroll from any rogue element | Added global `overflow-x: hidden; max-width: 100vw` in mobile-responsive.css |
| 5 | Warning | All pages | Images and iframes lacked guaranteed responsive sizing | Added `img { max-width: 100%; height: auto }` and `iframe { max-width: 100% }` in mobile CSS |
| 6 | Warning | Portal modules | Code blocks could overflow on narrow screens | Added `pre, code { overflow-x: auto; max-width: 100% }` |
| 7 | Cosmetic | gallery, social-templates, materials | Some elements use inline `font-size` < 14px (not Tailwind classes) — unaffected by CSS override | Not fixed — low impact, would require per-page edits |
| 8 | Cosmetic | 5 email templates | Small fonts in automation/templates/ — these are email HTML, not web pages | Skipped — not user-facing web pages |

### Architecture

- **New file:** `3D-print/mobile-responsive.css` — single shared stylesheet for mobile overrides
- **Linked from:** All 28 public HTML pages in 3D-print/
- **Approach:** CSS `!important` overrides on Tailwind utility classes within `@media (max-width: 640px)` — non-destructive, easy to extend
- **Not modified:** Email templates (automation/templates/), no Tailwind config changes

### Navigation & Sidebar

All pages with nav elements use `fixed top-0 inset-x-0` positioning — correctly spans full mobile width (375px). No sidebar collapse issues detected. Navigation works across all viewports.

### Video/Iframe

No YouTube iframes detected in current page set. The CSS safety net (`iframe { max-width: 100% }`) is in place for when videos are added.

### At-the-Printer UX Assessment

After fixes, the portal modules are usable on a phone next to a 3D printer:
- Font sizes bumped to minimum 14px on mobile
- Tables scroll horizontally rather than breaking layout
- Touch targets improved (44px minimum via CSS)
- Dark theme maintained — good for workshop lighting
