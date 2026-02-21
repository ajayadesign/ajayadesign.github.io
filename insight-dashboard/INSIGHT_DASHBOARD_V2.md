# Insight Dashboard V2 — Comprehensive Business Intelligence Plan

> **TLDR:** We have **697 prospects** across **14 DB tables** with **93 columns** on prospects + **41-column website audits** (836 rows) + rich JSONB enrichment (DNS, social, GBP reviews, SOS records, ads/hiring). The current dashboard only shows ~60% of available data and has **3 broken charts** (SSL reads from wrong table, competitive data is empty, formation dates are empty). V2 will: (1) fix the API to join `website_audits` for SSL/SEO/perf data, (2) surface 15+ new insight panels across business health, operations, reputation, and market position, (3) replace broken charts with data-backed alternatives, and (4) add a 5th "Business Health" dashboard page.

---

## 1. Data Inventory — What We Have vs. What We Show

### 1A. Database Schema Overview

| Table | Rows | Key Fields | Currently Exposed to Dashboard? |
|-------|------|-----------|-------------------------------|
| `prospects` | 697 | 93 columns — business info, scores, enrichment JSONB, contacts | Partially (~55 fields via API) |
| `website_audits` | 836 | SSL, SEO, perf, design era, CMS, tech stack, LCP, Lighthouse | Only `design_era` + `design_sins` |
| `outreach_emails` | 516 | subject, body, status, tracking, open/click/reply | Not exposed |
| `outreach_sequences` | n/a | email sequence steps, reply rates | Not exposed |
| `prospect_activities` | ? | activity logs, outcomes | Not exposed |
| `geo_rings` | 7 | Geographic ring data (Manor/Pflugerville) | Not exposed |

### 1B. Critical Data Gaps (Available in DB but NOT in Dashboard)

#### From `website_audits` (836 rows with FULL data):
| Field | Coverage | Status |
|-------|----------|--------|
| `ssl_valid` | 836/836 (True: 569, False: 267) | **BUG: Dashboard reads from `prospects.ssl_valid` (all NULL)** |
| `ssl_grade` | 836/836 (A: 67, B: 142, C: 360, F: 267) | NOT exposed |
| `has_title` | 819/836 true | NOT exposed |
| `has_meta_desc` | 553/836 true | NOT exposed |
| `has_h1` | 633/836 true | NOT exposed |
| `has_og_tags` | 582/836 true | NOT exposed |
| `has_schema` | 560/836 true | NOT exposed |
| `has_sitemap` | 42/836 true | NOT exposed |
| `tech_stack` | Array of technologies per site | NOT exposed |
| `security_headers` | JSONB with HSTS, CSP, etc. | NOT exposed |
| `lcp_ms` | 836 rows (avg 756ms) | NOT exposed |
| `cms_platform` | 836 rows (WP: 270, Custom: 448, Squarespace: 49...) | Uses `prospects.website_platform` instead |

#### From `enrichment` JSONB (all 697 prospects have this field):
| Section | Key Fields | Coverage | Dashboard Status |
|---------|-----------|---------|-----------------|
| `dns` | `has_professional_email` | 139 yes / 39 no | NOT exposed |
| `dns` | `has_dkim` | 52 yes / 126 no | NOT exposed |
| `dns` | `hosting_provider` | ~100 records | NOT exposed |
| `dns` | `dns_provider` | GoDaddy: 42, Cloudflare: 20, AWS: 17 | NOT exposed |
| `social` | Facebook, Instagram, Yelp URLs + exists | FB: 196, IG: 197, Yelp: 41 | Only `has_social` boolean |
| `gbp` | `gbp_reviews` (full text), `gbp_categories` | ~200 prospects | NOT exposed |
| `gbp` | `gbp_primary_type` (dentist, restaurant...) | ~200 prospects | NOT exposed |
| `gbp` | `gbp_hours_complete` | 122 true, 80 false | NOT exposed |
| `gbp` | `gbp_price_level` | 45 have data | NOT exposed |
| `gbp` | `gbp_review_velocity`, `gbp_review_response_rate` | 202 prospects | NOT exposed |
| `records` | `sos_entity_type` | 202 "corp" | Uses `prospects.entity_type` |
| `records` | `sos_formation_date` | **0 records** | Empty — but expected |
| `ads_hiring` | `runs_google_ads`, `runs_meta_ads` | **0 true** across 697 | Ads/hiring all FALSE |

#### Contact Intelligence (on `prospects` table):
| Field | Coverage | Dashboard Status |
|-------|---------|-----------------|
| `owner_email` | 496/697 (71%) | Only shows has_email boolean |
| `email_source` | pattern_guess: 217, scrape: 143, fallback: 96 | NOT exposed |
| `owner_name` | 131/697 | NOT exposed |
| `owner_phone` | 0/697 | Empty |
| `owner_linkedin` | 10/697 | NOT exposed |
| `tags` | recon_fail: 54, audit_fail: 11 | NOT exposed |

### 1C. Broken Charts (Must Fix)

| Chart | Page | Problem | Root Cause | Fix |
|-------|------|---------|-----------|-----|
| **SSL/Security Status** | intelligence.html | Shows "505 Unknown" | `prospects.ssl_valid` = NULL for all 697. Real data is in `website_audits` (836 rows) | Join `website_audits` in API |
| **Outperforming vs Competitors** | market.html | All "No Competitor Data" | `competitor_avg` = NULL for all 697. Data was never populated. | Replace with industry-benchmark comparison |
| **Formation Year Timeline** | market.html | "No formation date data" | `formation_date` = NULL for all; `enrichment→records→sos_formation_date` also empty | Replace with business maturity indicators |

---

## 2. V2 Architecture — API Changes

### 2A. Expand `/insights/analytics` Endpoint

Add these fields to the `latest_audit` subquery join:

```python
# NEW fields from website_audits
WebsiteAudit.ssl_valid,      # boolean — THE source of truth
WebsiteAudit.ssl_grade,      # A/B/C/F
WebsiteAudit.has_title,
WebsiteAudit.has_meta_desc,
WebsiteAudit.has_h1,
WebsiteAudit.has_og_tags,
WebsiteAudit.has_schema,
WebsiteAudit.has_sitemap,
WebsiteAudit.tech_stack,     # array
WebsiteAudit.cms_platform,   # string
WebsiteAudit.lcp_ms,         # performance
WebsiteAudit.page_size_kb,
WebsiteAudit.security_headers,  # JSONB
WebsiteAudit.responsive,
WebsiteAudit.cdn_detected,
```

Map in the response dict:
```python
"ssl_valid": r.wa_ssl_valid if r.wa_ssl_valid is not None else r.ssl_valid,
"ssl_grade": r.ssl_grade,
"has_title": r.has_title,
"has_meta_desc": r.has_meta_desc,
...etc
```

### 2B. Add Enrichment JSONB Extraction

Extract key enrichment fields in a new helper or inline:
```python
# From enrichment JSONB — extract per-prospect
"has_professional_email": enrichment.get('dns', {}).get('has_professional_email'),
"has_dkim": enrichment.get('dns', {}).get('has_dkim'),
"hosting_provider": enrichment.get('dns', {}).get('hosting_provider'),
"social_facebook": enrichment.get('social', {}).get('social_facebook', {}).get('exists'),
"social_instagram": enrichment.get('social', {}).get('social_instagram', {}).get('exists'),
"social_yelp": enrichment.get('social', {}).get('social_yelp', {}).get('exists'),
"gbp_primary_type": enrichment.get('gbp', {}).get('gbp_primary_type'),
"gbp_hours_complete": enrichment.get('gbp', {}).get('gbp_hours_complete'),
"gbp_price_level": enrichment.get('gbp', {}).get('gbp_price_level'),
"email_source": prospect.email_source,
"owner_name": bool(prospect.owner_name),
```

---

## 3. V2 Dashboard Enhancements — Page by Page

### 3A. index.html (Overview) — ENHANCE

**New KPIs to add:**
- `Avg Google Rating` (4.28★) — market reputation snapshot
- `No Website %` — already shown but also add $ value
- `Email Reachable` — 496/697 = 71%

**New Charts:**
1. **Outreach Pipeline Waterfall** — Emails pending: 474, cancelled: 42, unique prospects emailed: 490
2. **Contact Reachability** — donut: has_email (496) vs no_email (201)

### 3B. intelligence.html (Intelligence) — MAJOR OVERHAUL

**Fix SSL Chart:**
- Use `ssl_valid` + `ssl_grade` from website_audits (A: 67, B: 142, C: 360, F: 267)
- Show SSL Grade distribution instead of just valid/invalid/unknown
- This is the #1 bug fix

**New Charts:**
1. **SEO Compliance Checklist** — Horizontal bar showing has_title (819), has_meta_desc (553), has_h1 (633), has_og_tags (582), has_schema (560), has_sitemap (42)
2. **Social Platform Breakdown** — Facebook (196), Instagram (197), Yelp (41) — replaces the current "social score distribution" which is less actionable
3. **Professional Email Adoption** — 139 have professional email vs 39 free email
4. **DNS/DKIM Security** — 52 have DKIM vs 126 don't
5. **Tech Stack Word Cloud / Bar** — WordPress (270), jQuery, Bootstrap, Google Analytics, nginx, cloudflare
6. **GBP Profile Completeness** — Hours complete (122 vs 80), Photos (avg 9.6), Price level set (45)

**Enhanced Digital Gap Analysis:**
Add: No Sitemap (794/836), No Schema (276/836), No Meta Desc (283/836), No Professional Email (39), No DKIM (126)

### 3C. opportunities.html — ENHANCE

**New Panels:**
1. **Quick Win Segments** — Businesses with high reviews (50+) + no website = easiest sells
2. **Email Reachability Filter** — Show only opportunities with verified emails for immediate outreach
3. **Revenue Estimator** — Based on tier: Hot × $5K, Warm × $3K, Cool × $1.5K

### 3D. market.html — REBUILD BROKEN SECTIONS

**Fix Competitive Chart → Replace with:**
"Industry Performance Benchmark" — Compare each business_type's avg WP score to the overall market average. This creates a real "outperforming vs underperforming" view without needing `competitor_avg`.

**Fix Formation Timeline → Replace with:**
"Business Maturity Indicators" — Show: entity_type distribution (202 corp), GBP hours completeness, review velocity ranges, professional email adoption. These indicate maturity better than formation dates.

**New Charts:**
1. **GBP Category Analysis** — dentist: 13, mexican_restaurant: 10, fast_food: 10, car_repair: 9...
2. **Review Velocity** — avg 120/month, max 2375/month, 197 prospects with data
3. **Price Level Distribution** — Inexpensive: 31, Moderate: 14
4. **Geographic Ring Analysis** — Ring 0 (Manor 3mi): 247, Ring 1 (Pflugerville 8mi): 450

### 3E. NEW PAGE: business-health.html — FULL BUSINESS PROFILE

A new 5th page focused on the **complete picture per business**, not just website opportunity:

1. **Business Health Score Card** — Composite of: Web presence + Google reputation + Social activity + Email professionalism + Business registration
2. **Individual Prospect Deep-Dive** — Searchable table with expandable rows showing ALL data for a single business
3. **Segment Comparison** — Compare industries, cities, or tiers side-by-side
4. **Outreach Readiness** — How many are email-reachable, what template to use, personalization data available

---

## 4. Implementation Priority

### Sprint 1: Critical Fixes (API + SSL + Competitive)
1. ✅ Update API endpoint to join more website_audit fields
2. ✅ Fix SSL chart with ssl_grade data
3. ✅ Replace competitive chart with industry benchmark
4. ✅ Replace formation timeline with maturity indicators

### Sprint 2: New Intelligence Panels
5. Add SEO compliance checklist chart
6. Add social platform breakdown (FB/IG/Yelp)
7. Add GBP profile completeness panel
8. Add professional email / DKIM stats
9. Enhanced digital gap analysis

### Sprint 3: Market Enhancements
10. GBP category analysis
11. Review velocity chart
12. Geographic ring visualization
13. Revenue estimator

### Sprint 4: Business Health Page
14. Create business-health.html
15. Searchable prospect deep-dive
16. Segment comparison tool

---

## 5. Data Quality Notes

- **SSL data is GOOD** — 836 website_audits all have ssl_valid + ssl_grade. The bug is only in the API join.
- **Sub-scores are EMPTY** — score_digital, score_visibility, score_reputation, score_operations, score_growth, score_compliance are all NULL (0 prospects). These are placeholder columns never populated.
- **Page features are EMPTY** — has_booking, has_contact_form, has_analytics, has_email_capture, has_live_chat, has_privacy_policy, has_ada_widget are all NULL/0 for all prospects.
- **Ads/Hiring JSONB is empty** — runs_google_ads, runs_meta_ads = 0 true. hiring = 0 true in enrichment JSONB. The prospects table copies may differ.
- **Lighthouse scores are 0** — perf_score, a11y_score, bp_score, seo_score in website_audits are all 0 despite LCP being present. Lighthouse runner may have failed silently.
- **Review response rate is 0** across all 202 with data. Either businesses genuinely don't respond or the scraper couldn't detect responses.
- **Outreach is pre-launch** — 474 emails pending_approval, 42 cancelled. Zero sent, zero opens, zero replies. Data exists for future funnel charts.
