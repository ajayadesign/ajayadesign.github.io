# Website Sales Agent — Implementation Plan

> **Goal**: Collect 150+ data points per local business. Use ALL of them to calculate a **Website Purchase Likelihood Score** that predicts who will buy a website from us ASAP. Hyper-target outreach emails based on evidence.
>
> **Scope**: The agent collects data for all future services, but the **scoring and outreach** focus on website building/redesign as the primary revenue driver.
>
> **Sister project**: A separate analytics webapp will use this same data to identify cross-sell opportunities (SEO, social, reputation, etc.) — see `ENRICHMENT_PLAN.md`.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          PIPELINE WORKER (24/7)                         │
│                                                                         │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐            │
│  │ DISCOVER  │──▶│  AUDIT   │──▶│ DEEP     │──▶│  RECON   │            │
│  │ (Maps API)│   │(Lighthouse│   │ ENRICH   │   │(Owner    │            │
│  │           │   │ +PageScan)│   │(GBP/DNS/ │   │ finder)  │            │
│  └──────────┘   └──────────┘   │ Social/   │   └────┬─────┘            │
│                                 │ Records)  │        │                  │
│                                 └──────────┘        ▼                  │
│                                              ┌──────────┐              │
│                                              │  SCORE   │              │
│                                              │(Website  │              │
│                                              │ Purchase │              │
│                                              │ Likelihood│             │
│                                              └────┬─────┘              │
│                                                   │                    │
│                                                   ▼                    │
│                                              ┌──────────┐              │
│                                              │ ENQUEUE  │              │
│                                              │(Pick best │             │
│                                              │ template, │             │
│                                              │ personalize│            │
│                                              │ email)    │             │
│                                              └──────────┘              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                    ┌──────────────────────────────┐
                    │   ANALYTICS WEBAPP (future)   │
                    │  Cross-sell recommendations   │
                    │  Service gap heatmaps         │
                    │  Revenue forecasting          │
                    └──────────────────────────────┘
```

### What Changes vs Current

| Component | Current | After |
|-----------|---------|-------|
| **Discovery** | Google Maps → basic fields | Same + pull GBP detail (hours, photos, categories, popular times, reviews text) |
| **Audit** | Lighthouse + tech stack + design | Same + **Page Signal Scanner** (20 new detections from existing HTML) |
| **Enrich (NEW)** | _(doesn't exist)_ | New phase: DNS intel, social media scan, public records, ad intel, hiring signals |
| **Recon** | Owner finder (scrape/WHOIS/Hunter) | Same (runs after enrich, needs domain from audit) |
| **Score** | Simple `priority_score` | **Website Purchase Likelihood Score** — weighted formula using all 150+ signals |
| **Enqueue** | Generic template | **Template picker** — chooses email angle based on strongest signal cluster |
| **Storage** | `prospects` + `website_audits` | + `prospect_enrichment` JSONB on prospects + new score columns |

---

## Part 1: Database Changes

### New Columns on `prospects` Table

```sql
-- Website Purchase Likelihood Score (the main output)
ALTER TABLE prospects ADD COLUMN wp_score          INTEGER;  -- 0-100 composite
ALTER TABLE prospects ADD COLUMN wp_score_json     JSONB;    -- breakdown per dimension

-- Sub-scores (each 0-100)
ALTER TABLE prospects ADD COLUMN score_digital     INTEGER;  -- website quality + mobile + SSL + ADA
ALTER TABLE prospects ADD COLUMN score_visibility  INTEGER;  -- SEO + GBP + social + directories
ALTER TABLE prospects ADD COLUMN score_reputation  INTEGER;  -- reviews, response rate, sentiment
ALTER TABLE prospects ADD COLUMN score_operations  INTEGER;  -- booking, ordering, POS, CRM, analytics
ALTER TABLE prospects ADD COLUMN score_growth      INTEGER;  -- review velocity, hiring, revenue signals
ALTER TABLE prospects ADD COLUMN score_compliance  INTEGER;  -- licenses, ADA, privacy, insurance

-- Deep enrichment blob (all 80+ new signals)
ALTER TABLE prospects ADD COLUMN enrichment        JSONB DEFAULT '{}';
ALTER TABLE prospects ADD COLUMN enriched_at       TIMESTAMPTZ;

-- Key fields promoted to columns for fast querying/sorting
ALTER TABLE prospects ADD COLUMN has_booking       BOOLEAN;
ALTER TABLE prospects ADD COLUMN has_contact_form  BOOLEAN;
ALTER TABLE prospects ADD COLUMN has_analytics     BOOLEAN;
ALTER TABLE prospects ADD COLUMN has_social        BOOLEAN;  -- any social presence
ALTER TABLE prospects ADD COLUMN social_score      INTEGER;  -- 0-100
ALTER TABLE prospects ADD COLUMN review_response_rate NUMERIC(5,2);  -- 0.00 - 100.00
ALTER TABLE prospects ADD COLUMN review_velocity   NUMERIC(6,2);  -- reviews per month
ALTER TABLE prospects ADD COLUMN gbp_photos_count  INTEGER;
ALTER TABLE prospects ADD COLUMN gbp_posts_count   INTEGER;
ALTER TABLE prospects ADD COLUMN mx_provider       VARCHAR;  -- google, microsoft, none, other
ALTER TABLE prospects ADD COLUMN has_spf           BOOLEAN;
ALTER TABLE prospects ADD COLUMN has_dmarc         BOOLEAN;
ALTER TABLE prospects ADD COLUMN entity_type       VARCHAR;  -- llc, corp, sole_prop, dba
ALTER TABLE prospects ADD COLUMN formation_date    DATE;
ALTER TABLE prospects ADD COLUMN ppp_loan_amount   INTEGER;
ALTER TABLE prospects ADD COLUMN is_hiring         BOOLEAN;
ALTER TABLE prospects ADD COLUMN hiring_roles      JSONB;    -- ["marketing", "receptionist"]
ALTER TABLE prospects ADD COLUMN runs_ads          BOOLEAN;  -- any ads detected
ALTER TABLE prospects ADD COLUMN ad_platforms      JSONB;    -- ["meta", "google"]
ALTER TABLE prospects ADD COLUMN competitor_count  INTEGER;  -- same-type within 1 mile
```

### Indexes for Scoring Queries

```sql
CREATE INDEX ix_prospects_wp_score ON prospects (wp_score DESC);
CREATE INDEX ix_prospects_enriched_at ON prospects (enriched_at);
```

---

## Part 2: Enhanced Audit Phase — Page Signal Scanner

> **Where**: Extend `intel_engine.py` — `audit_prospect()` already fetches HTML and headers.
> Add a new function `scan_page_signals(html, headers, url)` that returns a dict.

### Signals to Detect (from HTML we already have)

```python
PAGE_SIGNAL_DETECTORS = {
    # ── Contact & Conversion ──
    "has_contact_form":     [r'<form[^>]*>', r'type=["\']email["\']', r'wpcf7', r'contact-form'],
    "has_cta_above_fold":   [r'book\s*now', r'get\s*a?\s*quote', r'schedule', r'free\s*consultation',
                             r'call\s*us', r'request\s*appointment'],
    "has_click_to_call":    [r'href=["\']tel:', r'tap\s*to\s*call'],
    "has_maps_embed":       [r'maps\.googleapis\.com', r'google\.com/maps/embed'],
    "has_testimonials":     [r'testimonial', r'review', r'what\s*our\s*customers\s*say'],
    "has_video":            [r'youtube\.com/embed', r'vimeo\.com', r'<video[\s>]', r'wistia\.com'],
    "has_menu_or_pricelist":[r'/menu', r'menu\.pdf', r'our\s*menu', r'price\s*list', r'pricing'],
    "has_portfolio":        [r'portfolio', r'our\s*work', r'gallery', r'projects', r'before.*after'],

    # ── Booking / Ordering / POS ──
    "has_booking":          [r'calendly\.com', r'acuityscheduling', r'vagaro\.com', r'mindbody',
                             r'fresha\.com', r'booksy\.com', r'opentable\.com', r'resy\.com',
                             r'jane\.app', r'square\.site/book', r'setmore\.com', r'zocdoc\.com'],
    "has_online_ordering":  [r'order\.online', r'chownow\.com', r'toast\.restaurants',
                             r'doordash\.com/store', r'grubhub', r'ubereats',
                             r'order\s*now', r'online\s*ordering'],
    "has_pos":              [r'squareup\.com', r'square\.com', r'toasttab\.com', r'clover\.com',
                             r'lightspeedhq', r'shopify\.com/pos'],

    # ── Analytics / Marketing ──
    "has_ga4":              [r'gtag.*G-', r'googletagmanager\.com', r'google-analytics\.com/g/'],
    "has_gtm":              [r'googletagmanager\.com/gtm\.js', r'GTM-'],
    "has_fb_pixel":         [r'connect\.facebook\.net.*fbevents', r'fbq\(', r'facebook\.com/tr'],
    "has_hotjar":           [r'hotjar\.com', r'static\.hotjar\.com'],
    "has_email_capture":    [r'mailchimp\.com', r'list-manage\.com', r'constantcontact\.com',
                             r'klaviyo\.com', r'convertkit\.com', r'sendinblue', r'newsletter',
                             r'subscribe', r'signup.*email'],
    "has_crm":              [r'hubspot\.com', r'salesforce\.com', r'zoho\.com', r'pipedrive'],

    # ── Chat / Support ──
    "has_live_chat":        [r'tidio\.co', r'drift\.com', r'intercom\.io', r'livechat\.com',
                             r'zendesk\.com', r'tawk\.to', r'crisp\.chat', r'olark\.com'],

    # ── Compliance ──
    "has_privacy_policy":   [r'/privacy', r'privacy.policy', r'privacy-policy'],
    "has_terms":            [r'/terms', r'terms.of.service', r'terms-of-service',
                             r'terms.and.conditions'],
    "has_cookie_consent":   [r'cookie.consent', r'cookie.banner', r'cookiebot', r'onetrust',
                             r'consent.manager', r'gdpr'],
    "has_ada_widget":       [r'accessibe\.com', r'userway\.org', r'equalweb\.com',
                             r'accessibility.widget'],

    # ── Payments ──
    "has_stripe":           [r'stripe\.com', r'js\.stripe\.com'],
    "has_square_pay":       [r'squareup\.com.*checkout', r'square.*payment'],
    "has_paypal":           [r'paypal\.com', r'paypalobjects\.com'],

    # ── Content ──
    "has_blog":             [r'/blog', r'/news', r'/articles', r'wp-content/uploads'],
    "has_careers_page":     [r'/careers', r'/jobs', r'/hiring', r'we.*hiring',
                             r'join.*team', r'open.*position'],
    "has_ads_txt":          None,  # separate HEAD request to /ads.txt
}
```

### Blog Freshness Detection

```python
# After detecting has_blog=True, crawl /blog and find latest post date
# Look for <time>, date patterns in text, structured data datePublished
```

### Return Object

```python
{
    "page_signals": {
        "has_contact_form": True,
        "has_cta_above_fold": False,
        "has_click_to_call": True,
        "has_booking": False,       # ← BIG signal for appointment businesses
        "has_online_ordering": False,
        "has_ga4": False,           # ← flying blind
        "has_fb_pixel": False,
        "has_email_capture": False,
        "has_live_chat": False,
        "has_privacy_policy": False, # ← compliance risk
        "has_ada_widget": False,     # ← lawsuit risk
        "has_blog": True,
        "blog_last_post": "2023-04-15",  # ← dead blog
        "has_video": False,
        "has_testimonials": False,
        "has_portfolio": False,
        "has_menu_or_pricelist": True,
        "has_careers_page": False,
        "has_stripe": False,
        "has_paypal": False,
        "has_pos": False,
        "has_crm": False,
        # ... all 30+ boolean signals
    }
}
```

---

## Part 3: Deep Enrichment Phase (NEW)

> **Where**: New file `api/services/deep_enrichment.py`
> **When**: After audit, before recon. New pipeline state: `audited → enriching → enriched`
> **Rate**: 1 prospect per cycle per agent, with delays between external calls

### 3A. GBP Deep Enrichment

```python
async def enrich_gbp(place_id: str) -> dict:
    """
    Pull extra fields from Google Places API (New) — Place Details.
    We already call this API during discovery; we just need to request more fields.
    
    Extra fields (no additional cost on existing call):
    - currentOpeningHours, regularOpeningHours → hours_complete (bool)
    - photos → gbp_photos_count (int)
    - reviews → review texts, response analysis
    - editorialSummary → gbp_summary
    - priceLevel → price_level
    - types → gbp_categories (list)
    - userRatingCount → already have
    - websiteUri → already have
    """
    # Uses existing GOOGLE_MAPS_API_KEY
    # Returns:
    return {
        "gbp_hours_complete": True,   # all 7 days filled?
        "gbp_photos_count": 3,        # <5 = red flag
        "gbp_categories": ["restaurant", "bar"],
        "gbp_price_level": "PRICE_LEVEL_MODERATE",
        "gbp_summary": "Popular Italian restaurant...",
        "gbp_reviews": [              # up to 5 most relevant
            {"text": "...", "rating": 5, "owner_replied": False, "time": "2025-12-01"},
            {"text": "...", "rating": 2, "owner_replied": False, "time": "2025-11-15"},
        ],
        "gbp_review_response_rate": 0.0,  # % of reviews with owner reply
        "gbp_review_velocity": 4.3,       # reviews per month (last 6 months)
        "gbp_popular_times": {             # if available
            "busiest_day": "Saturday",
            "busiest_hour": 19,
            "dead_hours": ["Monday 14:00-17:00", "Tuesday 14:00-17:00"],
        },
    }
```

### 3B. DNS & Email Intelligence

```python
async def enrich_dns(domain: str) -> dict:
    """
    Pure DNS lookups — no API key needed. Uses dnspython (already installed).
    """
    # MX records → detect email provider
    # TXT records → detect SPF, DKIM, DMARC
    # NS records → detect DNS provider
    # A/CNAME → detect hosting provider
    return {
        "mx_provider": "google",         # google | microsoft | none | zoho | other
        "has_professional_email": True,   # domain MX exists (vs gmail personal)
        "has_spf": False,
        "has_dkim": False,
        "has_dmarc": False,
        "dns_provider": "cloudflare",
        "hosting_provider": "wpengine",  # resolved from CNAME/A
    }
```

### 3C. Social Media Scanner

```python
async def enrich_social(business_name: str, website_url: str, city: str) -> dict:
    """
    Check major social platforms for presence.
    Method: HEAD requests + known URL patterns + page scraping.
    """
    # Facebook: check facebook.com/[businessname], parse for follower count, last post
    # Instagram: check instagram.com/[businessname]
    # Yelp: search yelp.com/biz/[businessname-city]
    # YouTube: search youtube.com/@[businessname]
    # TikTok: check tiktok.com/@[businessname]
    # LinkedIn: search linkedin.com/company/[businessname]
    # Also: extract social links from their own website HTML (we already have it)
    return {
        "social_facebook": {"exists": True, "url": "...", "followers": 342, "last_post": "2025-06-01"},
        "social_instagram": {"exists": False},
        "social_tiktok": {"exists": False},
        "social_youtube": {"exists": False},
        "social_linkedin": {"exists": False},
        "social_yelp": {"exists": True, "rating": 3.5, "reviews": 23, "response_rate": 0.0},
        "social_nextdoor": {"exists": False},
        "social_score": 25,  # 0-100 based on presence + activity
    }
```

### 3D. Public Records Lookup

```python
async def enrich_public_records(business_name: str, state: str, city: str, 
                                 business_type: str) -> dict:
    """
    Check free government databases.
    """
    # Texas SOS: search by business name → entity type, formation date, status
    # PPP loan data: search SBA public dataset by business name + city
    # Health inspections: Austin Public Health open data (restaurants only)
    # TDLR: license lookup (if contractor/cosmetologist/etc.)
    return {
        "sos_entity_type": "llc",              # llc | corp | sole_prop | dba | not_found
        "sos_formation_date": "2019-03-15",
        "sos_status": "active",                # active | forfeited | dissolved
        "sos_officers": ["John Smith"],
        "ppp_loan_amount": 87000,              # null if not found
        "ppp_jobs_reported": 8,
        "health_inspection_score": 92,         # null if not restaurant
        "license_status": "active",            # null if not licensed profession
        "license_expiry": "2026-06-30",
    }
```

### 3E. Advertising & Hiring Intelligence

```python
async def enrich_ads_and_hiring(business_name: str, website_url: str, city: str) -> dict:
    """
    Check Meta Ad Library + job boards.
    """
    # Meta Ad Library: search by page name → active ads?
    # Google Ads Transparency: search by advertiser → active?
    # Indeed/Google Jobs: search "[business_name] [city]" → open positions?
    return {
        "runs_meta_ads": False,
        "runs_google_ads": True,
        "ad_platforms": ["google"],
        "is_hiring": True,
        "hiring_roles": ["receptionist", "marketing coordinator"],
        "hiring_count": 2,
    }
```

### 3F. Orchestrator

```python
async def deep_enrich_prospect(prospect_id: str) -> dict:
    """
    Run all enrichment steps. Called by pipeline worker after audit phase.
    Stores everything in prospects.enrichment JSONB + key columns.
    """
    # 1. GBP deep enrichment (uses place_id)
    # 2. DNS intelligence (uses domain from website_url)
    # 3. Social media scan (uses business_name + website_url + city)
    # 4. Public records (uses business_name + state + business_type)
    # 5. Ads & hiring (uses business_name + website_url + city)
    # 6. Merge all into enrichment blob
    # 7. Update prospect columns (promoted fields for fast querying)
    # 8. Calculate sub-scores
    # 9. Update status: enriching → enriched
    pass
```

---

## Part 4: Website Purchase Likelihood Score

> **The core algorithm.** This is what makes us different — we don't just email everyone.
> We rank-order 697 businesses by how likely they are to buy a website RIGHT NOW.

### Score Formula: `wp_score` (0–100)

```python
def calculate_wp_score(prospect: Prospect, enrichment: dict, audit: WebsiteAudit) -> int:
    """
    Website Purchase Likelihood Score.
    Higher = more likely to buy a website from us ASAP.
    
    Three components:
    1. NEED (0-40): How badly do they need a new website?
    2. ABILITY (0-30): Can they afford it?
    3. TIMING (0-30): Are they ready right now?
    """
```

### Component 1: NEED (0–40 points)

> How bad is their current web presence?

| Signal | Points | Logic |
|--------|--------|-------|
| No website at all | +40 | Maximum need — they literally have nothing |
| Website score 0–19 | +35 | Terrible, basically unusable |
| Website score 20–29 | +30 | Very poor |
| Website score 30–39 | +25 | Below average |
| Website score 40–59 | +15 | Mediocre |
| Website score 60+ | +5 | Decent — low urgency |
| Not mobile-friendly | +5 | (bonus on top of base score) |
| No SSL | +3 | |
| Flash detected | +5 | Ancient tech — embarrassing |
| "Under construction" text | +5 | They KNOW they need help |
| Lorem ipsum detected | +5 | Incomplete site |
| Design era pre-2015 | +5 | Visually dated |
| Copyright year > 2 years stale | +3 | Neglected |
| Using free subdomain (wix.com, etc.) | +3 | Amateur |
| No contact form | +2 | Can't convert visitors |
| No CTA above fold | +2 | |

**Cap at 40.**

### Component 2: ABILITY (0–30 points)

> Can they afford to pay for a website?

| Signal | Points | Logic |
|--------|--------|-------|
| PPP loan > $150K | +10 | High revenue confirmed |
| PPP loan $50K–150K | +6 | Mid-tier revenue |
| PPP loan < $50K | +3 | Small but real |
| Google reviews > 200 | +8 | Lots of customers = real revenue |
| Google reviews 50–200 | +5 | Established business |
| Google reviews 10–50 | +3 | Newer but active |
| Google rating ≥ 4.5 | +3 | Successful business |
| Currently hiring | +5 | Growing = investing |
| Running ads (any platform) | +5 | Already spending on marketing |
| Entity type LLC/Corp | +3 | Formal business structure |
| Entity type sole prop | +1 | Less formal but still real |
| Professional email (Google Workspace/M365) | +2 | Tech-savvy enough to invest |
| On premium platform (Squarespace, Shopify) | +2 | Already paying for web presence |
| Formation date < 2 years | +3 | New businesses invest in setup |
| Multiple job postings | +3 | Serious growth |

**Cap at 30.**

### Component 3: TIMING (0–30 points)

> Are external triggers making them ready RIGHT NOW?

| Signal | Points | Logic |
|--------|--------|-------|
| Recent building permit | +10 | Renovation/expansion = rebrand moment |
| "Under construction" on site | +8 | They're actively trying to fix it |
| New GBP listing (< 6 months) | +5 | Just opened — building everything |
| Formation date < 6 months | +8 | Brand new business — setting up |
| Formation date 6–12 months | +5 | Still in setup mode |
| License expiring soon (< 90 days) | +3 | We can lead with a compliance alert = trust |
| Seasonal hook active for their industry | +3 | "Valentine's Day is next month..." |
| Review complaint: "can't find online" | +5 | Customers telling them they need a website |
| Review complaint: "website" mentioned negatively | +5 | Direct evidence |
| Competitor has much better score (diff > 30) | +5 | Competitive pressure |
| Competitor running ads, they aren't | +3 | Losing ground |
| Declining review velocity | +3 | Business is fading — website could help |
| No social media at all | +3 | They're invisible and may know it |
| Running ads + bad website | +8 | Burning money — urgency argument |
| Health inspection score trending down (restaurants) | +3 | Need to rebuild trust online |
| Hiring marketing/web person | +8 | Literally looking for what we sell |

**Cap at 30.**

### Final Score

```python
wp_score = min(need, 40) + min(ability, 30) + min(timing, 30)
# Range: 0–100
# Email priority: 80+ = immediate email, 60-79 = this week, 40-59 = queue, <40 = low priority
```

### Score Tiers for Email Targeting

| Tier | Score | Action | Email Template Strategy |
|------|-------|--------|------------------------|
| **HOT** | 80–100 | Email within 24 hours | Lead with their #1 pain (specific broken thing), show competitor, include before/after mockup |
| **WARM** | 60–79 | Email within 1 week | Lead with industry-specific hook, include audit summary |
| **COOL** | 40–59 | Queue for batch outreach | Generic industry pitch with seasonal hook |
| **COLD** | 0–39 | Don't email (collect more data or wait for trigger) | — |

---

## Part 5: Pipeline Worker Changes

### New Pipeline States

```
discovered → auditing → audited → enriching → enriched → recon → scored → queued → sent → ...
```

### Updated `_run_cycle()`

```python
async def _run_cycle(self):
    """One worker cycle — all phases in sequence."""
    # Phase 0: Recovery (existing)
    await self._recover_stuck_prospects()
    
    # Phase 1: Crawler (existing, only if enabled)
    if self._crawl_enabled:
        await self._crawl_ring()
    
    # Phase 2: Audit (existing + page signal scanner)
    await self._process_audits()  # now includes scan_page_signals()
    
    # Phase 3: Deep Enrichment (NEW)
    await self._process_deep_enrichments()   # GBP, DNS, social, records, ads
    
    # Phase 4: Recon (existing — owner/email finder)
    await self._process_recons()
    
    # Phase 5: Score (NEW — calculate wp_score)
    await self._process_scoring()
    
    # Phase 6: Enqueue (existing but now uses wp_score for template selection)
    await self._process_enqueue()
```

### Deep Enrichment Phase

```python
async def _process_deep_enrichments(self) -> int:
    """Pick audited prospects and run deep enrichment."""
    query = select(Prospect).where(
        Prospect.status == "audited",
        Prospect.enriched_at.is_(None),
    ).order_by(Prospect.priority_score.desc()).limit(ENRICH_BATCH_SIZE)
    
    # For each prospect:
    # 1. Set status = "enriching"
    # 2. Run deep_enrich_prospect()
    # 3. Set status = "enriched", enriched_at = now()
    # Rate limit: 3-second delay between prospects
```

### Scoring Phase

```python
async def _process_scoring(self) -> int:
    """Calculate wp_score for enriched prospects that haven't been scored yet."""
    query = select(Prospect).where(
        Prospect.status == "enriched",
        Prospect.wp_score.is_(None),
    ).order_by(Prospect.created_at.asc()).limit(SCORE_BATCH_SIZE)
    
    # For each prospect:
    # 1. Load enrichment data + audit data
    # 2. Calculate wp_score using the formula above
    # 3. Store wp_score, wp_score_json (breakdown), sub-scores
    # 4. Set status = "scored"
```

### Updated Enqueue Phase

```python
async def _process_enqueue(self) -> int:
    """Generate personalized emails for scored prospects."""
    query = select(Prospect).where(
        Prospect.status.in_(["scored", "enriched"]),  # enriched as fallback
        Prospect.owner_email.isnot(None),
        Prospect.wp_score >= 40,  # only email prospects with meaningful score
    ).order_by(Prospect.wp_score.desc()).limit(ENQUEUE_BATCH_SIZE)
    
    # For each prospect:
    # 1. Pick template based on highest-signal cluster:
    #    - "no_website" template if has_website = False
    #    - "burning_money" template if runs_ads + bad website
    #    - "hiring_web" template if hiring_roles includes web/marketing
    #    - "competitor_beating_you" template if competitor score >> theirs
    #    - "customer_complaints" template if review complaints about website
    #    - "new_business" template if formation_date < 12 months
    #    - "seasonal" template if seasonal hook active
    #    - "generic_audit" template as default
    # 2. Personalize with specific data points
    # 3. Generate email via template engine
    # 4. Set status = "queued"
```

---

## Part 6: New Email Templates

### Template: `no_website`
> For 192 businesses with no website at all

```
Subject: {business_name} — your customers are looking for you online

{owner_name}, I searched for "{business_name}" and found your Google listing
({google_reviews} reviews, {google_rating}★) — but no website.

{google_reviews} customers found you. How many gave up because they couldn't
find a menu/hours/booking page?

I built a mock-up of what {business_name}'s website could look like:
{mockup_url}

Quick call this week? I have a few slots open.
```

### Template: `burning_money`
> For businesses running ads but sending traffic to a broken site

```
Subject: {business_name} — you're paying for traffic that bounces

{owner_name}, I noticed {business_name} is running {ad_platform} ads — smart move.

But your site scores {score_overall}/100 on Google's own speed test.
{specific_issue_1}. {specific_issue_2}.

You're paying to send people to a site that {broken_thing}.
Fix the landing page and your ad ROI improves immediately.

Here's a 60-second audit: {audit_url}
```

### Template: `hiring_web`
> For businesses with job postings for marketing/web roles

```
Subject: {business_name} — before you hire, consider this

{owner_name}, I saw {business_name} is looking for a {hiring_role}.

A full-time {hiring_role} costs $40-60K/year + benefits.
I can build you a professional website + handle your SEO for a fraction of that.

Your current site scores {score_overall}/100. Here's what needs fixing:
{broken_things_list}

15 minutes to chat?
```

### Template: `customer_complaints`
> For businesses whose Google reviews mention website/online issues

```
Subject: Your customers are telling you something, {owner_name}

{review_complaint_quote}
— one of your recent Google reviews.

{business_name} has {google_reviews} reviews and {google_rating}★. 
Your customers love you. But {complaint_count} of them mentioned 
{complaint_theme} in their reviews.

I can fix that. Here's what I found: {audit_url}
```

### Template: `competitor_beating_you`
> For businesses whose competitors have significantly better websites

```
Subject: {competitor_name} is outranking {business_name}

{owner_name}, I analyzed {business_name} and a nearby competitor ({competitor_name}).

Your site scores {score_overall}/100.
{competitor_name} scores {competitor_score}/100.

When someone Googles "{business_type} in {city}", {competitor_name} wins.
Here's what they're doing that you're not: {competitor_advantages}

I can close that gap this month. 15-minute call?
```

### Template: `new_business`
> For businesses formed in the last 12 months

```
Subject: Congrats on launching {business_name}!

{owner_name}, I noticed {business_name} was registered {months_ago} months ago 
in {city}. Congrats on the new venture!

Most new businesses lose their first 50 customers because they can't be found
online. I checked — {no_website_or_bad_website_detail}.

I help new {city} businesses launch with a professional website + Google presence 
in under 2 weeks. Want to see some examples?
```

---

## Part 7: Implementation Order

### Sprint 1 (Week 1–2): Database + Page Signal Scanner
- [ ] Alembic migration: add all new columns to `prospects`
- [ ] Build `scan_page_signals()` in `intel_engine.py`
- [ ] Integrate into existing `audit_prospect()` (stores in `enrichment` JSONB)
- [ ] Backfill: re-scan existing 412 audited prospects with new scanner
- [ ] Tests: verify signal detection for each regex pattern

### Sprint 2 (Week 3–4): GBP + DNS Enrichment
- [ ] Build `enrich_gbp()` in new `deep_enrichment.py`
- [ ] Build `enrich_dns()` using dnspython
- [ ] Add `_process_deep_enrichments()` to pipeline worker
- [ ] Add `enriching` status to pipeline state machine
- [ ] Tests: mock API responses, verify data storage

### Sprint 3 (Week 5–6): Social Media + Public Records
- [ ] Build `enrich_social()` — Facebook, Instagram, Yelp, YouTube, TikTok detection
- [ ] Build `enrich_public_records()` — Texas SOS, PPP data, health inspections
- [ ] Rate limiting: respectful delays between external requests
- [ ] Tests: verify detection accuracy

### Sprint 4 (Week 7–8): Ads, Hiring, Scoring
- [ ] Build `enrich_ads_and_hiring()` — Meta Ad Library, Google Transparency, Indeed
- [ ] Build `calculate_wp_score()` — implement full scoring formula
- [ ] Add `_process_scoring()` to pipeline worker
- [ ] Add `scored` status to pipeline state machine
- [ ] Tests: score calculation with various prospect profiles

### Sprint 5 (Week 9–10): Template Engine + Email Personalization
- [ ] Create 6 new email templates (no_website, burning_money, hiring_web, customer_complaints, competitor_beating_you, new_business)
- [ ] Build template selection logic based on wp_score breakdown
- [ ] Update `_process_enqueue()` to use new templates
- [ ] A/B test framework: generate variant subjects for each template
- [ ] Tests: end-to-end email generation for each template

### Sprint 6 (Week 11–12): Backfill + Launch
- [ ] Run deep enrichment on all 697 existing prospects
- [ ] Score all prospects, verify distribution makes sense
- [ ] Review top-50 wp_score prospects manually — do the scores feel right?
- [ ] Tune weights based on review
- [ ] Enable email sending for HOT tier (score ≥ 80)
- [ ] Monitor open/click/reply rates by template

### Future: Analytics Webapp
- [ ] Separate project — React/Next.js dashboard
- [ ] Connects to same PostgreSQL database
- [ ] Visualizes all 150+ data points with filters
- [ ] Cross-sell recommendation engine
- [ ] Service gap heatmaps by geography + industry
- [ ] Revenue forecasting based on pipeline data
- [ ] Not part of this sprint plan — see `ENRICHMENT_PLAN.md`

---

## Success Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Data completeness | 80%+ of prospects have enrichment | `SELECT count(*) FILTER (WHERE enrichment != '{}') / count(*)` |
| Score distribution | Normal-ish curve, 20% in HOT tier | Histogram of wp_score |
| Email open rate | >40% (vs industry avg 20%) | Tracking pixel |
| Email reply rate | >5% (vs cold email avg 1-2%) | Reply detection |
| Template performance | Identify top template by reply rate | A/B tracking per template |
| First customer from pipeline | 1 paying client within 30 days of launch | CRM / manual tracking |
| Pipeline → Revenue | 5% conversion within 90 days | 35 clients × $4K avg = $140K | 

---

## File Map

| File | Status | Purpose |
|------|--------|---------|
| `api/services/intel_engine.py` | Modify | Add `scan_page_signals()`, integrate into `audit_prospect()` |
| `api/services/deep_enrichment.py` | **New** | GBP, DNS, social, records, ads enrichment orchestrator |
| `api/services/scoring_engine.py` | **New** | `calculate_wp_score()` + sub-score calculations |
| `api/services/pipeline_worker.py` | Modify | Add enrichment + scoring phases to `_run_cycle()` |
| `api/services/template_engine.py` | Modify | Add 6 new templates + template selection logic |
| `api/models/prospect.py` | Modify | Add new columns to SQLAlchemy model |
| `api/routes/outreach.py` | Modify | Expose wp_score in API, add score filters |
| `alembic/versions/xxx_deep_enrichment.py` | **New** | Database migration for new columns |
| `WEBSITE_SALES_AGENT.md` | **New** | This file |
| `ENRICHMENT_PLAN.md` | Reference | Full data collection vision (all services) |
