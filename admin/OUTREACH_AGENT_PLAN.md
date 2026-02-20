# 🎯 Outreach Agent — The Autonomous Lead Hunter

## AjayaDesign Admin Dashboard — New Tab: `outreach`

> **"A lean, autonomous agent that never sleeps — systematically discovering local businesses with bad websites, grading them, finding decision-makers, and sending template-driven outreach with real audit data — all visualized in a real-time war-room dashboard, with zero unnecessary AI token burn."**

---

## Table of Contents

1. [Vision & Philosophy](#1-vision--philosophy)
2. [System Architecture](#2-system-architecture)
3. [Data Model & Schema](#3-data-model--schema)
4. [The Crawl Engine — Business Discovery](#4-the-crawl-engine--business-discovery)
5. [The Intel Engine — Website Grading & Analysis](#5-the-intel-engine--website-grading--analysis)
6. [The Recon Engine — Decision-Maker Finder](#6-the-recon-engine--decision-maker-finder)
7. [The Composer Engine — Template-Driven Outreach](#7-the-composer-engine--template-driven-outreach)
8. [The Cadence Engine — Follow-Up Sequencing](#8-the-cadence-engine--follow-up-sequencing)
9. [Geo-Ring Expansion System](#9-geo-ring-expansion-system)
10. [Telegram Notifications & Remote Control](#10-telegram-notifications--remote-control)
11. [Admin Dashboard UI](#11-admin-dashboard-ui)
12. [Backend API Routes](#12-backend-api-routes)
13. [Firebase RTDB Structure](#13-firebase-rtdb-structure)
14. [Clever Tricks & Secret Weapons](#14-clever-tricks--secret-weapons)
15. [Implementation Phases](#15-implementation-phases)
16. [File Inventory](#16-file-inventory)
17. [Legal & Compliance](#17-legal--compliance)

---

## 1. Vision & Philosophy

### The Problem
You're a one-person web design agency. You can build incredible sites, but you can't knock on every door in Texas. Cold outreach works, but manually finding businesses, checking their sites, finding emails, and writing personalized pitches is a 40hr/week job by itself.

### The Solution
An **autonomous agent** that:
1. **Discovers** local businesses in expanding geo-rings (Manor → Pflugerville → Round Rock → Austin → Central TX → ...)
2. **Grades** their website on 12+ metrics (speed, mobile, SEO, design age, SSL, accessibility) — **no AI needed**, pure Lighthouse + programmatic checks
3. **Hunts** for the owner/decision-maker's name, email, and phone
4. **Composes** template-driven emails with **real audit data injected as variables** — no AI token burn, just smart templates
5. **Sequences** multi-touch follow-ups with intelligent timing
6. **Tracks** opens, replies, and conversions — feeding back into the system
7. **Pauses & notifies you via Telegram** after each geo-ring is complete — you decide when to expand
8. **Escalates** hot leads into the existing Leads CRM tab — **builds happen ONLY after you close the deal** (future: local GPU + local model)

### ⚠️ Key Design Principles
- **ZERO auto-builds.** We do NOT kick off AI website builds for every prospect. That burns tokens for businesses that never replied. Builds are manual, after a deal is closed. Future plan: local GPU + local LLM for build generation.
- **Minimal AI usage.** Templates + variable injection instead of Claude rewriting every email. AI is only used for one-time tasks (optional design era detection) not per-prospect.
- **Gmail SMTP for sending.** Same `email_service.py` + Gmail App Password already used for contracts/invoices. No Amazon SES, no new SMTP setup.
- **Audit reports are auth-protected.** Visible only in the admin dashboard (behind Firebase login). Share via screenshare on calls — never give them a public link they can hand to a competitor.
- **Telegram-first alerting.** Every major event (ring complete, reply received, meeting booked) pings you on Telegram so you can manage the system from your phone.
- **ajayadesign.github.io stays the domain** — at least while operating within the Austin metro geo-rings.

### The Philosophy: "Show, Don't Tell" (But Don't Show Too Much)
Every cold email includes **specific audit findings** about *their* site. Not "your site could be better" — but "your homepage loads in 8.2s (should be <2s), you have 0 meta descriptions, your mobile score is 23/100, and your SSL cert expires in 12 days." This is the hook. Nobody ignores a report card about *their own business*.

**Critical:** The full audit report with screenshots, competitor comparison, and detailed scores lives **inside the admin dashboard only** (behind Firebase auth). You NEVER send them a link to view the report. Instead, you offer a **15-minute screenshare call** to walk them through it. This:
1. Forces a meeting (your real goal)
2. Prevents them from taking the report to a cheaper developer
3. Positions you as the expert who *found* the problems
4. Creates urgency — they can't just bookmark it for later

---

## 2. System Architecture

```
┌──────────────────────────────────────────────────────────┐
│                  ADMIN DASHBOARD (Browser)                │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  Outreach Tab                                        │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │ │
│  │  │ Geo Map  │ │ Prospect │ │ Composer │ │ Metrics│ │ │
│  │  │ War Room │ │ Pipeline │ │ Preview  │ │ & Stats│ │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └────────┘ │ │
│  └─────────────────────────────────────────────────────┘ │
└──────────────────────┬───────────────────────────────────┘
                       │ Firebase RTDB (real-time)
                       │ + REST API calls
┌──────────────────────▼───────────────────────────────────┐
│              BACKEND (FastAPI Docker Container)           │
│  ┌─────────────┐ ┌───────────┐ ┌───────────────────────┐│
│  │ Scheduler   │ │ Crawl     │ │ Intel Engine          ││
│  │ (APScheduler│ │ Engine    │ │ (Playwright + APIs)   ││
│  │  cron jobs) │ │ (Google   │ │  • Lighthouse audit   ││
│  │             │ │  Maps API │ │  • Tech stack detect  ││
│  │  Runs 24/7  │ │  + scrape)│ │  • SEO analysis       ││
│  └──────┬──────┘ └─────┬─────┘ │  • Screenshot capture ││
│         │              │       └──────────┬────────────┘│
│  ┌──────▼──────────────▼────────────────▼──────────────┐│
│  │              PostgreSQL Database                      ││
│  │  prospects · audits · emails · sequences · geo_rings  ││
│  └──────────────────────────────────────────────────────┘│
│  ┌───────────────┐ ┌──────────────┐ ┌────────────────┐  │
│  │ Recon Engine  │ │ Template     │ │ Email Sender   │  │
│  │ (Website     │ │ Engine       │ │ (Gmail SMTP    │  │
│  │  scrape,     │ │ (Variable    │ │  via existing   │  │
│  │  WHOIS,      │ │  injection,  │ │  email_service  │  │
│  │  social scan)│ │  no AI)      │ │  .py)           │  │
│  └──────────────┘ └──────────────┘ └────────────────┘  │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Telegram Bot — Sends alerts to your phone:      │   │
│  │  📢 Ring complete · ⭐ Reply received · 📅 Meeting│   │
│  │  ❓ "Expand to Ring N?" → you tap YES/NO         │   │
│  └──────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

### How It Integrates with Existing System
- **Firebase RTDB** path: `outreach/` (mirrors pattern of `builds/`, `leads/`)
- **API routes**: `/api/v1/outreach/*` (new route file in `automation/api/routes/`)
- **Admin tab**: 7th tab in sidebar (`tab-outreach` / `mtab-outreach`)
- **Lead promotion**: One-click "Promote to Lead" pushes prospect into existing `leads/` RTDB for CRM handling
- **Build trigger**: **Manual only.** No auto-builds. After a prospect replies positively → you promote to Lead → you close the deal → THEN you manually kick off a build. (Future: local GPU + local model for build generation, not cloud AI tokens.)
- **Email sending**: Reuses existing `email_service.py` (Gmail SMTP + App Password) — same system that sends contracts and invoices
- **Telegram bot**: All major events fire a Telegram notification. Geo-ring completion requires your approval via Telegram before expanding.
- **Domain**: Uses `ajayadesign.github.io` as the main site — at minimum for all Austin-area geo-rings

---

## 3. Data Model & Schema

### 3.0 Storage Philosophy — PostgreSQL vs Firebase vs Filesystem

> **The #1 rule: Firebase is a real-time view layer, NOT a database.**

Firebase RTDB free tier gives us **1 GB storage** and **10 GB/month download bandwidth**. That sounds like a lot, but a single Lighthouse JSON blob is 200-500 KB, and a screenshot is 100-500 KB. Storing 10K prospects with full audit data in Firebase would blow through both limits in weeks.

**The Smart Split:**

```
┌──────────────────────────────────────────────────────────────────────┐
│                    WHERE EACH BYTE LIVES                             │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  FIREBASE RTDB (~40 KB total!)         ← Real-time UI only          │
│  ─────────────────────────────                                       │
│  • Agent status + heartbeat             (~200 bytes)                 │
│  • Aggregate KPI counters               (~500 bytes)                 │
│  • Ring progress bars (7 rings max)     (~2 KB)                     │
│  • Activity feed (last 50 events)       (~15 KB, auto-pruned)       │
│  • Agent log (last 200 entries)         (~20 KB, auto-pruned)       │
│  • NO prospect records                  ← loaded via REST API       │
│  • NO audit data                        ← loaded via REST API       │
│  • NO email content                     ← loaded via REST API       │
│  • NO screenshots                       ← served via file endpoint  │
│                                                                      │
│  POSTGRESQL (Docker, unlimited)         ← Source of truth            │
│  ──────────────────────────────                                      │
│  • Full prospect records (all fields)                                │
│  • Audit scores + extracted metrics (structured columns)             │
│  • Email content (HTML bodies, tracking, replies)                    │
│  • Sequences, geo-rings, competitor intel                            │
│  • Outreach state machine + history                                  │
│  • File paths to screenshots (NOT the images themselves)             │
│  • Extracted Lighthouse metrics (NOT the full 200-500 KB JSON)       │
│                                                                      │
│  FILESYSTEM (Docker volume: /data/)     ← Heavy binary blobs        │
│  ──────────────────────────────────                                   │
│  • Screenshots: /data/screenshots/{prospect_id}/desktop.webp         │
│  • Screenshots: /data/screenshots/{prospect_id}/mobile.webp          │
│  • Raw Lighthouse JSON: /data/audits/{prospect_id}/lighthouse.json.gz│
│  • Served via: GET /api/v1/outreach/files/{type}/{prospect_id}       │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

**Why NO prospect summaries in Firebase?**

You might think: "put lightweight prospect cards in Firebase for real-time kanban updates." But let's do the math:

| Scale | Firebase Storage | Monthly Download (20 dashboard loads/day) |
|-------|-----------------|------------------------------------------|
| 1K prospects × 150 bytes | 150 KB | 150 KB × 600 = 90 MB |
| 10K prospects × 150 bytes | 1.5 MB | 1.5 MB × 600 = 900 MB ⚠️ |
| 50K prospects × 150 bytes | 7.5 MB | 7.5 MB × 600 = 4.5 GB ❌ |

At 10K prospects you're already at 90% of the 10 GB/month download limit — just from loading the prospect list. And every time a prospect status changes, Firebase pushes the update to every connected client.

**Instead:** Map dots, kanban cards, and prospect lists load from the REST API with pagination + filters. The API returns only the fields needed for each view:

```python
# Map dots endpoint — ~50 bytes per dot, loaded per ring
GET /api/v1/outreach/map-dots?ring_id=abc&fields=id,lat,lng,status,score
→ [{id, lat, lng, status, score}, ...]  # 1000 dots = 50 KB, instant

# Kanban cards — ~200 bytes per card, paginated
GET /api/v1/outreach/prospects?status=contacted&limit=50&offset=0&fields=id,name,score,city,emails_sent
→ [{id, name, score, city, emails_sent}, ...]  # 50 cards = 10 KB

# Full prospect detail — loaded on click
GET /api/v1/outreach/prospects/{id}
→ {full record + audit scores + email history}  # ~5-10 KB
```

**Firebase only fires for things the sidebar needs to update WITHOUT a user action:**
- agent status light changing from 🟢 to 🔴
- KPI counter incrementing ("+1 opened just now")
- new activity appearing in the feed
- ring progress bar ticking up

Everything else is fetched on-demand when the user clicks/navigates.

**Write-Through Pattern:**

```python
async def on_prospect_discovered(prospect):
    """Called in the crawl engine after saving to PostgreSQL."""
    # 1. PostgreSQL already updated (source of truth)
    
    # 2. Firebase: only update aggregate counters + activity feed
    await firebase_increment('outreach/stats/total_prospects', 1)
    await firebase_push_activity({
        'type': 'discovered',
        'name': prospect.business_name,
        'detail': f'{prospect.city}, {prospect.state}',
        'ts': int(time.time()),
    })
    await prune_activity_feed(max_entries=50)
    
    # 3. Telegram: batch — only notify if 10+ discovered in this batch
    # (DON'T push prospect record to Firebase — dashboard will API-fetch)

async def on_email_opened(prospect_id, tracking_id):
    """Called when the tracking pixel fires."""
    # 1. Update PostgreSQL
    await db.update_prospect(prospect_id, emails_opened=F('emails_opened') + 1)
    
    # 2. Firebase: increment counter + activity
    await firebase_increment('outreach/stats/total_opened', 1)
    name = await db.get_prospect_name(prospect_id)
    await firebase_push_activity({
        'type': 'opened',
        'name': name,
        'detail': 'Opened your email',
        'ts': int(time.time()),
    })
    
    # 3. Telegram: notify on opens (they're hot!)
    await telegram_notify(f"👀 {name} opened your email!")
```

**Size Budgets:**

| Data Category | Storage | Estimated Size per 10K Prospects |
|---------------|---------|----------------------------------|
| PostgreSQL: prospect rows | All fields except blobs | ~30 MB |
| PostgreSQL: audit metrics (extracted) | Structured columns | ~20 MB |
| PostgreSQL: email records | HTML + tracking | ~50 MB |
| Filesystem: screenshots (WebP) | 2 × ~40 KB each | ~800 MB |
| Filesystem: Lighthouse JSON (gzipped) | ~30 KB compressed | ~300 MB |
| Firebase: everything | Counters + feed + log | **~40 KB** (constant!) |
| **Total** | | **~1.2 GB** (mostly screenshots) |

> **Key insight:** Firebase stays at ~40 KB whether we have 100 or 100,000 prospects. It's truly O(1) storage.
>
> **Dual-mode consequence:** This same ~40 KB powers the **light mode** dashboard when you're away from home on the production site. The Firebase listeners that run the sidebar in full mode become the *entire* main panel in light mode — zero extra reads. See §11.0 for full architecture.

### 3.1 Data Lifecycle & Archival

| Data | Hot (active) | Warm (3-6 months) | Cold (6-12 months) | Delete |
|------|-------------|-------------------|--------------------|---------| 
| Prospect record | Full row in PostgreSQL | Full row (no change) | Move to `prospects_archive` table | After 18 months if "dead" |
| Audit metrics | In `website_audits` table | No change | Purge raw scores, keep overall only | With prospect |
| Lighthouse JSON | `/data/audits/` gzipped | Keep | Delete file, keep extracted metrics in PG | With prospect |
| Screenshots | `/data/screenshots/` WebP | Keep | Delete for dead/do_not_contact | With prospect |
| Email HTML bodies | In `outreach_emails` table | Keep | Purge body, keep subject + tracking data | With prospect |
| Reply bodies | In `outreach_emails` table | Keep forever (valuable intel) | Keep forever | Never (business intel) |
| Firebase activity | Last 50 entries | Auto-pruned | N/A | Continuous |
| Firebase agent log | Last 200 entries | Auto-pruned | N/A | Continuous |

```python
# Scheduled daily: prune Firebase + archive cold prospects
async def daily_maintenance():
    """Runs at 3 AM via APScheduler."""
    # Firebase pruning — keep nodes small
    await prune_firebase_node('outreach/activity', max_children=50)
    await prune_firebase_node('outreach/log', max_children=200)
    
    # PostgreSQL archival — move stale "dead" prospects
    cutoff = datetime.now() - timedelta(days=365)
    stale = await db.query(
        "SELECT id FROM prospects WHERE status IN ('dead','do_not_contact') AND updated_at < :cutoff",
        cutoff=cutoff
    )
    for p in stale:
        await archive_prospect(p.id)  # Move to prospects_archive, delete screenshots
    
    # Screenshot cleanup — delete for archived prospects
    for prospect_id in archived_ids:
        shutil.rmtree(f'/data/screenshots/{prospect_id}', ignore_errors=True)
        os.remove(f'/data/audits/{prospect_id}/lighthouse.json.gz')
```

### 3.2 `prospects` Table (PostgreSQL)

```sql
CREATE TABLE prospects (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- Discovery
    business_name   TEXT NOT NULL,
    business_type   TEXT,                -- "restaurant", "plumber", "dentist", etc.
    industry_tag    TEXT,                -- NAICS code or custom tag
    address         TEXT,
    city            TEXT NOT NULL,
    state           TEXT DEFAULT 'TX',
    zip             TEXT,
    lat             DECIMAL(10, 7),
    lng             DECIMAL(10, 7),
    phone           TEXT,
    google_maps_url TEXT,
    google_rating   DECIMAL(2,1),
    google_reviews  INTEGER,
    
    -- Website
    website_url     TEXT,
    has_website     BOOLEAN DEFAULT false,
    website_platform TEXT,              -- "wordpress", "wix", "squarespace", "custom", "none"
    ssl_valid       BOOLEAN,
    ssl_expiry      TIMESTAMP,
    domain_age_days INTEGER,
    
    -- Decision Maker
    owner_name      TEXT,
    owner_email     TEXT,
    owner_phone     TEXT,
    owner_linkedin  TEXT,
    owner_title     TEXT,              -- "Owner", "Manager", "Marketing Director"
    email_source    TEXT,              -- "whois", "website_scrape", "hunter.io", "linkedin", "manual"
    email_verified  BOOLEAN DEFAULT false,
    
    -- Audit Scores (0-100)
    score_overall   INTEGER,
    score_speed     INTEGER,
    score_mobile    INTEGER,
    score_seo       INTEGER,
    score_a11y      INTEGER,           -- accessibility
    score_design    INTEGER,           -- heuristic-judged design quality (no AI)
    score_security  INTEGER,
    audit_json      JSONB,             -- extracted audit highlights only (NOT full lighthouse)
    audit_date      TIMESTAMP,
    screenshot_desktop TEXT,            -- file path: /data/screenshots/{id}/desktop.webp
    screenshot_mobile  TEXT,            -- file path: /data/screenshots/{id}/mobile.webp
    
    -- Outreach State Machine
    status          TEXT DEFAULT 'discovered',
    -- discovered → audited → enriched → queued → contacted → 
    -- follow_up_1 → follow_up_2 → follow_up_3 → 
    -- replied → meeting_booked → promoted → dead → do_not_contact
    
    -- Outreach Tracking
    emails_sent     INTEGER DEFAULT 0,
    emails_opened   INTEGER DEFAULT 0,
    emails_clicked  INTEGER DEFAULT 0,
    last_email_at   TIMESTAMP,
    last_opened_at  TIMESTAMP,
    last_clicked_at TIMESTAMP,
    replied_at      TIMESTAMP,
    reply_sentiment TEXT,              -- "positive", "neutral", "negative", "unsubscribe"
    
    -- Geo-ring
    geo_ring_id     UUID REFERENCES geo_rings(id),
    distance_miles  DECIMAL(6,2),      -- distance from Manor, TX
    
    -- Competitor Intel
    competitors     JSONB,             -- [{name, url, score}] nearby same-industry
    competitor_avg  INTEGER,           -- avg website score of competitors
    
    -- Meta
    source          TEXT,              -- "google_maps", "yelp", "bbb", "manual", "referral"
    notes           TEXT,
    tags            TEXT[],
    priority_score  INTEGER,           -- composite: bad website + good reviews + close distance
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

-- Composite index for the priority queue
CREATE INDEX idx_prospects_priority ON prospects(status, priority_score DESC);
CREATE INDEX idx_prospects_geo ON prospects(lat, lng);
CREATE INDEX idx_prospects_city ON prospects(city, state);
```

### 3.3 `website_audits` Table

```sql
CREATE TABLE website_audits (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prospect_id     UUID REFERENCES prospects(id) ON DELETE CASCADE,
    url             TEXT NOT NULL,
    
    -- Lighthouse Scores
    perf_score      INTEGER,           -- Performance 0-100
    a11y_score      INTEGER,           -- Accessibility 0-100
    bp_score        INTEGER,           -- Best Practices 0-100
    seo_score       INTEGER,           -- SEO 0-100
    
    -- Speed Metrics
    fcp_ms          INTEGER,           -- First Contentful Paint
    lcp_ms          INTEGER,           -- Largest Contentful Paint
    cls             DECIMAL(4,3),      -- Cumulative Layout Shift
    tbt_ms          INTEGER,           -- Total Blocking Time
    ttfb_ms         INTEGER,           -- Time to First Byte
    page_size_kb    INTEGER,
    request_count   INTEGER,
    
    -- SEO Details
    has_title       BOOLEAN,
    has_meta_desc   BOOLEAN,
    has_h1          BOOLEAN,
    has_og_tags     BOOLEAN,
    has_schema      BOOLEAN,           -- structured data
    has_sitemap     BOOLEAN,
    has_robots_txt  BOOLEAN,
    mobile_friendly BOOLEAN,
    
    -- Tech Detection
    tech_stack      JSONB,             -- ["WordPress 6.4", "PHP 8.1", "jQuery 3.6"]
    cms_platform    TEXT,
    hosting_provider TEXT,
    cdn_detected    TEXT,
    
    -- Design Analysis (heuristic-based, no AI)
    design_era      TEXT,              -- "modern", "dated-2015", "ancient-2005", "template"
    color_palette   JSONB,             -- extracted dominant colors
    font_stack      JSONB,
    responsive      BOOLEAN,
    has_animations  BOOLEAN,
    design_sins     JSONB,             -- ["copyright 2019", "lorem ipsum", "no viewport meta"]
    
    -- Security
    ssl_valid       BOOLEAN,
    ssl_grade       TEXT,              -- "A+", "A", "B", "C", "F"
    security_headers JSONB,            -- CSP, HSTS, X-Frame-Options, etc.
    
    -- Screenshots (file paths, NOT base64 — stored on disk as WebP)
    desktop_screenshot TEXT,           -- /data/screenshots/{prospect_id}/desktop.webp
    mobile_screenshot  TEXT,           -- /data/screenshots/{prospect_id}/mobile.webp
    
    -- Raw Data (filesystem, NOT in PostgreSQL)
    lighthouse_json_path TEXT,         -- /data/audits/{prospect_id}/lighthouse.json.gz
    raw_html_hash   TEXT,              -- detect if site has changed since last audit
    
    audited_at      TIMESTAMP DEFAULT NOW()
);
```

### 3.4 `outreach_emails` Table

```sql
CREATE TABLE outreach_emails (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prospect_id     UUID REFERENCES prospects(id) ON DELETE CASCADE,
    sequence_step   INTEGER DEFAULT 1, -- 1=initial, 2=follow_up_1, 3=follow_up_2, etc.
    
    -- Email Content
    subject         TEXT NOT NULL,
    body_html       TEXT NOT NULL,
    body_text       TEXT NOT NULL,
    
    -- Personalization Data Used
    personalization JSONB,             -- what data points were injected
    template_id     TEXT,              -- which template variant was used
    
    -- Delivery
    sent_at         TIMESTAMP,
    message_id      TEXT,              -- SMTP message ID
    tracking_id     TEXT UNIQUE,       -- for open/click pixel
    
    -- Engagement
    opened_at       TIMESTAMP,
    open_count      INTEGER DEFAULT 0,
    clicked_at      TIMESTAMP,
    click_count     INTEGER DEFAULT 0,
    clicked_links   JSONB,             -- which links were clicked
    
    -- Reply
    replied_at      TIMESTAMP,
    reply_body      TEXT,
    reply_sentiment TEXT,
    
    -- Status
    status          TEXT DEFAULT 'draft',
    -- draft → scheduled → sent → opened → clicked → replied → bounced → failed
    scheduled_for   TIMESTAMP,
    error_message   TEXT,
    
    created_at      TIMESTAMP DEFAULT NOW()
);
```

### 3.5 `outreach_sequences` Table

```sql
CREATE TABLE outreach_sequences (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,            -- "Restaurant Cold Outreach v2"
    industry_tag    TEXT,                      -- target industry
    
    steps           JSONB NOT NULL,
    -- [
    --   {step: 1, delay_days: 0, type: "email", template: "initial_audit"},
    --   {step: 2, delay_days: 3, type: "email", template: "follow_up_value"},
    --   {step: 3, delay_days: 7, type: "email", template: "social_proof"},
    --   {step: 4, delay_days: 14, type: "email", template: "breakup"},
    -- ]
    
    -- Performance Stats
    total_enrolled  INTEGER DEFAULT 0,
    total_replied   INTEGER DEFAULT 0,
    total_meetings  INTEGER DEFAULT 0,
    reply_rate      DECIMAL(5,2),
    
    active          BOOLEAN DEFAULT true,
    created_at      TIMESTAMP DEFAULT NOW()
);
```

### 3.6 `geo_rings` Table

```sql
CREATE TABLE geo_rings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,            -- "Ring 1: Manor"
    center_lat      DECIMAL(10, 7) DEFAULT 30.3427,  -- Manor, TX
    center_lng      DECIMAL(10, 7) DEFAULT -97.5567,
    radius_miles    DECIMAL(6,2) NOT NULL,
    
    -- Crawl Progress
    status          TEXT DEFAULT 'pending',   -- pending, crawling, complete, paused
    businesses_found INTEGER DEFAULT 0,
    businesses_with_websites INTEGER DEFAULT 0,
    businesses_without_websites INTEGER DEFAULT 0,
    crawl_started   TIMESTAMP,
    crawl_completed TIMESTAMP,
    last_crawl      TIMESTAMP,
    
    -- Categories crawled
    categories_done JSONB DEFAULT '[]',       -- ["restaurant", "plumber", ...]
    categories_total JSONB DEFAULT '[]',
    
    created_at      TIMESTAMP DEFAULT NOW()
);
```

---

## 4. The Crawl Engine — Business Discovery

### 4.1 Strategy: Expanding Geo-Rings

```
Ring 0:  Manor, TX (0-3 miles)          ← START HERE
Ring 1:  Pflugerville (3-8 miles)
Ring 2:  Round Rock / Hutto (8-15 miles)
Ring 3:  North Austin (15-25 miles)
Ring 4:  Greater Austin (25-40 miles)
Ring 5:  Central TX (40-80 miles)
Ring 6:  Extended TX (80-150 miles)
```

The agent crawls Ring 0 first, **exhaustively**. Only after Ring N is at 90%+ completion does it expand to Ring N+1. This ensures local businesses get priority.

### 4.2 Discovery Sources

| Source | Method | Data Quality | Rate Limits |
|--------|--------|-------------|-------------|
| **Google Maps / Places API** | Nearby Search + Place Details | ★★★★★ | 1000 req/day (free tier) |
| **Google Search** | `site:yelp.com "plumber" "Manor TX"` scrape | ★★★★ | Careful rate limiting |
| **Yelp Fusion API** | Business Search endpoint | ★★★★ | 5000 req/day |
| **BBB Directory** | Scrape by location | ★★★ | Gentle crawling |
| **Yellow Pages** | Scrape by category + location | ★★★ | Gentle crawling |
| **State Business Registry** | TX SOS entity search | ★★★ | Public records |
| **Facebook Places** | Graph API search | ★★★ | Limited |
| **Local Chamber of Commerce** | Scrape member directories | ★★★★ | One-time crawl |

### 4.3 Business Category Targets (Priority Order)

These are businesses most likely to need a website overhaul and have budget:

```
TIER 1 (High Budget + Bad Sites):
  restaurants, dental_offices, law_firms, med_spas, 
  real_estate_agents, chiropractors, veterinarians

TIER 2 (Medium Budget + Often Bad Sites):
  plumbers, electricians, hvac, roofing, landscaping,
  auto_repair, hair_salons, fitness_studios

TIER 3 (Variable):
  retailers, photographers, tutoring, pet_services,
  cleaning_services, moving_companies, daycares
```

### 4.4 Crawl Worker Flow

```python
async def crawl_ring(ring_id, category):
    """Crawl one category within one geo-ring."""
    ring = await db.get(ring_id)
    
    # 1. Google Places: nearby search with pagination
    places = await google_places_nearby(
        lat=ring.center_lat, lng=ring.center_lng,
        radius_m=ring.radius_miles * 1609,
        type=category
    )
    
    for place in places:
        # 2. Skip if already in DB (dedup by google_place_id or phone+name)
        if await prospect_exists(place.id):
            continue
        
        # 3. Get detailed info (phone, website, hours, reviews)
        details = await google_place_details(place.id)
        
        # 4. Insert prospect
        prospect = await create_prospect(
            business_name=details.name,
            business_type=category,
            address=details.address,
            city=details.city,
            phone=details.phone,
            website_url=details.website,
            has_website=bool(details.website),
            google_rating=details.rating,
            google_reviews=details.review_count,
            google_maps_url=details.maps_url,
            lat=details.lat, lng=details.lng,
            distance_miles=haversine(MANOR_LAT, MANOR_LNG, details.lat, details.lng),
            source='google_maps',
            geo_ring_id=ring_id,
        )
        
        # 5. Immediately push to Firebase for real-time UI update
        await firebase_push(f'outreach/prospects/{prospect.id}', prospect.to_dict())
        
        # 6. If they have a website, queue for audit
        if prospect.has_website:
            await queue_audit(prospect.id)
```

### 4.5 De-duplication Strategy

```
DEDUP KEYS (in order of priority):
  1. google_place_id (exact match)
  2. phone number (normalized: strip +1, spaces, dashes)
  3. business_name + zip (fuzzy: Levenshtein distance < 3)
  4. website domain (normalized: strip www, trailing slash)
```

---

## 5. The Intel Engine — Website Grading & Analysis

This is the **killer feature**. Every prospect with a website gets a comprehensive audit that becomes the backbone of the personalized outreach.

### 5.1 Audit Pipeline

```
Website URL
    │
    ├─► [1] Playwright: Load page, take screenshots (desktop + mobile)
    │
    ├─► [2] Lighthouse: Run full audit (perf, SEO, a11y, best practices)
    │
    ├─► [3] Tech Detection: Wappalyzer-style stack identification
    │       └── CMS, frameworks, analytics, hosting, CDN
    │
    ├─► [4] SEO Scan: Meta tags, headings, schema, sitemap, robots.txt
    │
    ├─► [5] Security Scan: SSL grade, headers, mixed content
    │
    ├─► [6] Speed Analysis: TTFB, FCP, LCP, CLS, TBT, page weight
    │
    ├─► [7] Heuristic Design Judge (NO AI — rule-based):
    │       └── viewport meta? → mobile-ready check
    │       └── copyright year in footer? → staleness detection
    │       └── CSS framework detection (Bootstrap 3 = dated)
    │       └── jQuery version check (1.x = ancient)
    │       └── responsive breakpoints? → mobile layout
    │       └── Web font usage → modern indicator
    │       └── Flash/Java applet detection → prehistoric
    │
    └─► [8] Composite Score: Weighted formula → 0-100 overall grade
            └── Priority Score = f(audit_score, reviews, distance, industry)
```

> **⚠️ No AI tokens burned per audit.** All 8 steps are programmatic. Lighthouse gives us perf/SEO/a11y/best-practices. Playwright takes screenshots. Heuristic rules detect design era. Zero API calls to Claude/OpenAI.

### 5.2 The Composite Scoring Formula

```python
def calculate_priority_score(prospect, audit):
    """Higher = more likely to convert AND more profitable."""
    
    # Website badness (0-40 points) — worse site = higher priority
    site_badness = 40 - (audit.score_overall * 0.4)
    
    # Business health (0-25 points) — good reviews = has money
    review_score = min(25, (prospect.google_rating or 0) * 4 + 
                        min(10, (prospect.google_reviews or 0) / 10))
    
    # Proximity (0-15 points) — closer = easier to close
    distance = prospect.distance_miles or 100
    proximity_score = max(0, 15 - (distance / 5))
    
    # Industry value (0-10 points) — some industries pay more
    industry_multiplier = INDUSTRY_VALUES.get(prospect.business_type, 5)
    
    # Reachability (0-10 points) — have email = can contact
    reach = 0
    if prospect.owner_email: reach += 5
    if prospect.email_verified: reach += 3
    if prospect.owner_name: reach += 2
    
    return int(site_badness + review_score + proximity_score + 
               industry_multiplier + reach)
```

### 5.3 Heuristic Design Judge (No AI Required)

Instead of burning Claude tokens on every screenshot, we use **deterministic heuristic rules** that run on the scraped HTML/CSS:

```python
def judge_design_era(html, tech_stack, css_info):
    """Rule-based design era detection. No AI needed."""
    score = 50  # Start neutral
    era = 'unknown'
    sins = []
    
    # Ancient signals (subtract points)
    if 'flash' in html.lower() or 'shockwave' in html.lower():
        score -= 30; era = 'pre-2010-prehistoric'; sins.append('Flash detected')
    if 'jQuery' in tech_stack and jquery_version_major(tech_stack) <= 1:
        score -= 15; sins.append('jQuery 1.x (ancient)')
    if 'Bootstrap' in tech_stack and bootstrap_version(tech_stack) <= 3:
        score -= 10; sins.append('Bootstrap 3 or older')
    if 'table' in html.lower() and html.lower().count('<table') > 3:
        score -= 20; sins.append('Table-based layout detected')
    
    # Dated signals
    copyright_year = extract_copyright_year(html)
    if copyright_year and copyright_year < 2020:
        score -= (2024 - copyright_year) * 2
        sins.append(f'Copyright stuck on {copyright_year}')
    if not has_viewport_meta(html):
        score -= 15; sins.append('No viewport meta (not mobile-friendly)')
    if 'lorem ipsum' in html.lower():
        score -= 20; sins.append('Lorem ipsum placeholder text!')
    if 'under construction' in html.lower():
        score -= 25; sins.append('"Under Construction" on page')
    
    # Modern signals (add points)
    if has_viewport_meta(html): score += 10
    if uses_web_fonts(html): score += 5
    if uses_css_grid_or_flex(html): score += 10
    if has_lazy_loading(html): score += 5
    if has_service_worker(tech_stack): score += 5
    
    # Era detection based on score
    if score >= 70: era = '2022-modern'
    elif score >= 50: era = '2018-recent'
    elif score >= 30: era = '2015-dated'
    elif score >= 15: era = '2010-ancient'
    else: era = 'pre-2010-prehistoric'
    
    return {'score': max(0, min(100, score)), 'era': era, 'sins': sins}
```

**Why this is better than AI for our use case:**
- Runs in <10ms per site (vs 3-5s for Claude API call)
- Costs $0 (vs ~$0.01-0.03 per Claude call × thousands of sites)
- Deterministic — same site always gets same score
- The specific "sins" detected feed directly into email templates as {{broken_things}}

### 5.4 "No Website" Handling

Businesses with **no website at all** are actually great prospects:

```python
if not prospect.has_website:
    prospect.score_overall = 0  # Worst possible score
    prospect.website_platform = 'none'
    prospect.priority_score = calculate_priority_nosite(prospect)
    # These get a different email template: "I noticed you don't have a website..."
```

---

## 6. The Recon Engine — Decision-Maker Finder

### 6.1 Email Discovery Waterfall

Try each method in order, stop at first verified hit:

```
Step 1: Website Scrape
  └── Scan /about, /contact, /team pages for email patterns
  └── Check mailto: links
  └── Look for "Contact the Owner" sections

Step 2: WHOIS Lookup
  └── Domain registrant info (often redacted, but worth trying)
  └── Parse registrant name + email

Step 3: Google Search Enrichment
  └── "{business_name} {city} owner email"
  └── "{business_name} owner linkedin"
  └── Parse results for email patterns

Step 4: Pattern Guessing + Verification
  └── If owner_name = "John Smith" and domain = acmeplumbing.com
  └── Try: john@acmeplumbing.com, jsmith@acmeplumbing.com,
           john.smith@acmeplumbing.com, info@acmeplumbing.com
  └── Verify each with SMTP check (RCPT TO without sending)

Step 5: Social Media Scan  
  └── Facebook business page → linked personal profile → email
  └── LinkedIn company page → employees with "Owner" title
  └── Instagram bio → linktr.ee → email in link tree

Step 6: Fallback
  └── Use info@{domain} or contact@{domain}
  └── Use Google Maps listed phone (for SMS outreach if enabled)
```

### 6.2 Email Verification

```python
async def verify_email(email: str) -> dict:
    """Multi-step email verification without sending."""
    result = {
        'email': email,
        'format_valid': False,
        'domain_exists': False, 
        'mx_records': False,
        'smtp_valid': False,
        'disposable': False,
        'catch_all': False,
        'score': 0
    }
    
    # 1. Format check (regex)
    # 2. DNS MX record lookup
    # 3. SMTP handshake (EHLO → MAIL FROM → RCPT TO → check response)
    # 4. Disposable email database check
    # 5. Catch-all detection
    
    # Score: 0-100 confidence that email will deliver
    return result
```

---

## 7. The Composer Engine — Template-Driven Outreach

### 7.1 The Secret Sauce: Data-Driven Personalization Variables (Zero AI)

Every email is unique because it's generated from **real audit data** — not AI rewriting. The template engine simply injects variables:

```python
PERSONALIZATION_VARS = {
    # From Google Maps
    '{{business_name}}':     'Sunrise Bakery',
    '{{owner_first_name}}':  'Maria',
    '{{city}}':              'Manor',
    '{{google_rating}}':     '4.7',
    '{{google_reviews}}':    '134',
    '{{business_type}}':     'bakery',
    
    # From Website Audit (THE HOOK)
    '{{speed_score}}':       '23',
    '{{speed_grade}}':       'F',
    '{{load_time}}':         '8.2 seconds',
    '{{mobile_score}}':      '31',
    '{{seo_score}}':         '18',
    '{{platform}}':          'Wix',
    '{{ssl_status}}':        'expired 12 days ago',
    '{{design_era}}':        '2015',
    '{{page_size}}':         '12MB (should be under 2MB)',
    '{{missing_seo}}':       'meta descriptions, schema markup, sitemap',
    
    # Competitor Intelligence
    '{{competitor_name}}':   'Austin Bakes Co',
    '{{competitor_score}}':  '82',
    '{{competitor_diff}}':   '59 points higher',
    
    # Social Proof
    '{{nearby_client}}':     'Manor Hardware',
    '{{nearby_result}}':     '340% more organic traffic in 3 months',
    
    # Calculated Impact
    '{{estimated_loss}}':    '$2,300/month',  // based on industry avg conversion
    '{{bounce_rate_est}}':   '73%',           // estimated from load time
}
```

### 7.2 Email Templates (Pre-Written, Data-Injected — No AI)

Each template is a **hand-crafted email** with variable slots. The template engine does simple `{{variable}}` replacement. No Claude calls needed.

**Template 1: The Audit Hook (Initial Contact)**
```
Subject: {{business_name}} — Your site scores {{speed_score}}/100 (free audit inside)

Hey {{owner_first_name}},

I ran across {{business_name}} while checking out {{business_type}}s in {{city}} — 
your {{google_rating}}-star rating with {{google_reviews}} reviews is impressive. 
Your customers clearly love what you do.

I'm a web designer here in Manor, and out of professional curiosity I put your 
website through a quick performance audit. Here's what I found:

  🔴 Page Speed: {{load_time}} load time (Google recommends under 2s)
  🔴 Mobile Score: {{mobile_score}}/100 ({{bounce_rate_est}}% of visitors likely leave)
  🔴 SEO: Missing {{missing_seo}}
  {{#if ssl_expired}}🔴 Security: SSL certificate expired{{/if}}

For context, {{competitor_name}} — another {{business_type}} nearby — scores {{competitor_score}}/100.

I'm not sending this to scare you. I genuinely think a business with your reputation 
deserves a website that matches. I've helped {{nearby_client}} get {{nearby_result}}.

Would a 15-minute call to walk through the full audit be useful? No pitch, just data.

— Ajaya Dahal
AjayaDesign · Manor, TX
ajayadesign.github.io
```

**Template 2: The Value Follow-Up (Day 3)**
```
Subject: Re: {{business_name}} — quick thought on mobile traffic

{{owner_first_name}},

Forgot to mention — Google's data shows that {{industry_mobile_pct}}% of 
{{business_type}} searches happen on mobile. With your mobile score at 
{{mobile_score}}/100, you're likely invisible to over half your potential customers.

One quick example: I redesigned a site for a local {{business_type}} and their 
mobile traffic went from 12% to 61% of total visitors in 8 weeks.

Your call — but the full audit report is sitting here if you want it.

— Ajaya
```

**Template 3: Social Proof (Day 7)**
```
Subject: What {{nearby_client}} saw after redesigning

{{owner_first_name}},

Quick update — {{nearby_client}} just shared their latest numbers with me:
  • Organic traffic: +{{traffic_increase}}% 
  • Mobile conversions: +{{mobile_increase}}%
  • Page load: from {{old_speed}}s → {{new_speed}}s

They're about {{distance_between}} miles from you in {{nearby_city}}.

Still happy to share your free audit whenever you're ready.

— Ajaya
```

**Template 4: The Breakup (Day 14)**
```
Subject: Closing your file, {{owner_first_name}}

Hey {{owner_first_name}},

I haven't heard back, so I'll assume the timing isn't right. Totally get it.

I'll keep your audit on file — if you ever want to see it, just reply "send it" 
and I'll forward it over. No strings.

Keep crushing it with those {{google_rating}} stars 🌟

— Ajaya
```

### 7.3 Template Engine (No AI — Pure Variable Injection)

Instead of burning Claude tokens per email, we use a **deterministic template engine**:

```python
async def compose_email(prospect, audit, sequence_step, template):
    """
    Pure template rendering. No AI API calls.
    Each email is unique because the DATA is unique, not the phrasing.
    """
    # Build variable map from real prospect + audit data
    variables = {
        'business_name': prospect.business_name,
        'owner_first_name': (prospect.owner_name or 'there').split()[0],
        'city': prospect.city,
        'business_type': prospect.business_type,
        'google_rating': str(prospect.google_rating or 'N/A'),
        'google_reviews': str(prospect.google_reviews or '0'),
        
        # Audit data (THE HOOK — every email is unique because every site is different)
        'speed_score': str(audit.perf_score or 'N/A'),
        'speed_grade': score_to_grade(audit.perf_score),
        'load_time': f"{(audit.lcp_ms or 0) / 1000:.1f} seconds",
        'mobile_score': str(audit.a11y_score or 'N/A'),  # mobile-friendliness
        'seo_score': str(audit.seo_score or 'N/A'),
        'platform': audit.cms_platform or 'custom-built',
        'ssl_status': 'valid' if audit.ssl_valid else 'expired/missing',
        'design_era': audit.design_era or 'unknown',
        'page_size': f"{(audit.page_size_kb or 0) / 1024:.1f}MB",
        'missing_seo': build_missing_seo_string(audit),
        
        # Competitor intel
        'competitor_name': get_top_competitor_name(prospect),
        'competitor_score': str(get_top_competitor_score(prospect)),
        
        # Conditional blocks
        'ssl_expired': not audit.ssl_valid,
        'has_broken_things': bool(audit.design_sins),
        'worst_broken_thing': (audit.design_sins or [''])[0],
    }
    
    # Simple {{variable}} replacement
    subject = render_template(template.subject, variables)
    body_html = render_template(template.body_html, variables)
    body_text = render_template(template.body_text, variables)
    
    return subject, body_html, body_text


def render_template(template_str, variables):
    """Replace {{var}} placeholders. Handle {{#if var}}...{{/if}} conditionals."""
    import re
    
    # Handle conditionals first
    def replace_conditional(match):
        var_name = match.group(1)
        content = match.group(2)
        return content if variables.get(var_name) else ''
    
    result = re.sub(
        r'\{\{#if (\w+)\}\}(.*?)\{\{/if\}\}',
        replace_conditional, template_str, flags=re.DOTALL
    )
    
    # Replace variables
    for key, value in variables.items():
        result = result.replace(f'{{{{{key}}}}}', str(value))
    
    return result
```

**Why template-only is sufficient:**
- Each email is already unique because the *data* is unique (different scores, different broken things, different competitors)
- Gmail spam filters care about sender reputation, not phrasing variation
- We can A/B test by having multiple template variants per step, not by AI rewriting
- Cost: $0 per email vs ~$0.02 per Claude API call
- Speed: <1ms per email vs 3-5s per Claude call

**Optional future enhancement:** When local GPU + local LLM is set up, we can add AI rewriting as an opt-in feature. For now, templates + variables are the move.

---

## 8. The Cadence Engine — Follow-Up Sequencing

### 8.1 Default Sequence Timeline

```
Day 0:  📧 Initial Audit Email (personalized)
          └── IF opened but not replied → wait
          └── IF not opened after 24h → resend with new subject line

Day 3:  📧 Follow-Up #1: Value add (mobile traffic stat)
          └── Only if initial was opened OR unknown

Day 7:  📧 Follow-Up #2: Social proof (client success story)
          └── Only if no reply yet

Day 14: 📧 Follow-Up #3: Breakup email
          └── Final touch — "closing your file"

Day 30: 📧 Resurrection (only if they opened any email)
          └── "New data on {{business_name}} site performance"
```

### 8.2 Smart Timing

```python
SEND_WINDOWS = {
    'restaurant':    {'days': [1,2,3], 'hours': (9, 11)},   # Tue-Thu morning (before lunch rush)
    'dental_office': {'days': [1,2,3,4], 'hours': (7, 9)},  # Before patients arrive
    'law_firm':      {'days': [0,1,2,3,4], 'hours': (8, 10)},
    'plumber':       {'days': [0,4], 'hours': (18, 20)},     # Mon/Fri evening (after jobs)
    'default':       {'days': [1,2,3], 'hours': (9, 11)},    # Tue-Thu mid-morning
}
```

### 8.3 Exit Conditions

Immediately stop the sequence if:
- Prospect replies (any sentiment) → route to manual handling
- Email bounces → mark dead, try alternate email
- Prospect clicks "unsubscribe" link → mark `do_not_contact`
- Prospect manually marked as `dead` in dashboard
- Prospect promoted to Lead (handoff to CRM)

---

## 9. Geo-Ring Expansion System

### 9.1 The War Room Map Concept

The dashboard features a **live map** centered on Manor, TX with concentric rings:

```
        ┌─────────────────────────────────────┐
        │            🗺️ GEO WAR ROOM          │
        │                                      │
        │      ╭──── Ring 5: Central TX ────╮  │
        │    ╭──── Ring 4: Greater Austin ──╮│  │
        │   ╭──── Ring 3: North Austin ────╮││  │
        │  ╭──── Ring 2: RR / Hutto ──────╮│││  │
        │ ╭──── Ring 1: Pflugerville ────╮ ││││  │
        │╭──── Ring 0: Manor ──────────╮ │ │││││  │
        ││  🟢🟢🔴🟡⚪⚪             │ │ ││││  │
        │╰────────────────────────────╯ │ │││││  │
        │ ╰──────────────────────────╯  ││││  │
        │  ╰────────────────────────╯   │││  │
        │   ╰──────────────────────╯    ││  │
        │    ╰────────────────────╯     │  │
        │      ╰──────────────────╯      │
        │                                      │
        │  🟢 Contacted  🟡 Audited  🔴 Bad Site│
        │  ⚪ Discovered  ⭐ Replied            │
        └─────────────────────────────────────┘
```

Each dot is a business, color-coded by status. Click a dot → see the prospect card.

### 9.2 Ring Progression Rules (Manual Approval Required)

When a ring reaches completion threshold, the agent **pauses and asks you via Telegram** before expanding:

```python
async def check_ring_completion(current_ring):
    """Check if ring is done. If so, PAUSE and notify — don't auto-expand."""
    stats = get_ring_stats(current_ring)
    
    is_complete = (
        stats.businesses_found >= 50 and          # Found enough businesses
        stats.contacted_pct >= 0.8 and             # 80% contacted
        stats.reply_rate is not None and            # Have enough data
        (datetime.now() - current_ring.crawl_started).days >= 7  # At least 1 week
    )
    
    if is_complete:
        # PAUSE the agent
        await set_agent_status('paused_awaiting_approval')
        current_ring.status = 'complete'
        await db.commit()
        
        # Send Telegram notification with inline keyboard
        next_ring = await get_next_ring(current_ring)
        await telegram_notify(
            f"🎯 *Ring Complete: {current_ring.name}*\n"
            f"\n"
            f"📊 Stats:\n"
            f"  • Businesses found: {stats.businesses_found}\n"
            f"  • Contacted: {stats.contacted_count} ({stats.contacted_pct:.0%})\n"
            f"  • Opened: {stats.opened_count} ({stats.open_rate:.1%})\n"
            f"  • Replied: {stats.replied_count} ({stats.reply_rate:.1%})\n"
            f"  • Meetings: {stats.meetings}\n"
            f"\n"
            f"❓ *Expand to {next_ring.name}?*",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Yes, expand", callback_data=f"expand_{next_ring.id}")],
                [InlineKeyboardButton("⏸ Stay paused", callback_data="stay_paused")],
                [InlineKeyboardButton("🛑 Stop agent", callback_data="stop_agent")],
            ])
        )
        
        # Also send via email as backup
        await send_ring_complete_email(current_ring, stats, next_ring)
```

### 9.3 Remote Control via Telegram

You can control the agent entirely from your phone:

```
Telegram Commands:
  /status          → Current agent status + ring progress
  /pause           → Pause the agent immediately
  /resume          → Resume from where it stopped
  /expand          → Approve expansion to next ring
  /stats           → Today's KPIs (discovered, contacted, opened, replied)
  /prospect <name> → Quick lookup of a specific prospect
  /kill            → Emergency stop all activity
```

The Telegram bot runs as part of the FastAPI server (using `python-telegram-bot` library with webhook mode).

---

## 10. Telegram Notifications & Remote Control

The Telegram bot is a **first-class citizen** — not an afterthought. It's how you monitor and control the agent when you're away from the dashboard.

### 10.1 Bot Setup

```python
# automation/api/services/telegram_notifier.py
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from automation.api.config import settings

bot = Bot(token=settings.telegram_bot_token)
CHAT_ID = settings.telegram_chat_id  # Your personal chat ID

async def notify(message: str, reply_markup=None, parse_mode="Markdown"):
    """Send a Telegram notification. Called from anywhere in the system."""
    await bot.send_message(
        chat_id=CHAT_ID,
        text=message,
        parse_mode=parse_mode,
        reply_markup=reply_markup,
    )
```

### 10.2 Event Notification Table

Every major system event triggers a Telegram message:

| Event | Trigger | Message Example |
|-------|---------|-----------------|
| 🔍 New prospects discovered | Batch of 10+ found in a ring | "Found 14 new businesses in Ring 0 (Manor)" |
| 📊 Audit complete | Website audit finishes | "Audited joesplumbing.com — Score: 23/100 🔴" |
| 📧 Email batch sent | Daily send batch completes | "Sent 8 emails today (Ring 0: 5, Ring 1: 3)" |
| 👀 Email opened | Prospect opens email | "👀 Joe's Plumbing opened your email (2nd time)" |
| ⭐ Reply received | Any reply detected | "⭐ REPLY from Texas Eye Care! Classification: interested" |
| 📅 Meeting booked | Prospect agrees to meet | "🎉 MEETING BOOKED: Joe Martinez, Joe's Plumbing — Feb 25 2pm" |
| 🎯 Ring complete | Ring threshold met | "Ring 0 (Manor) complete — 82% contacted. Expand to Ring 1?" (with inline keyboard) |
| ⚠️ Error | Audit timeout, bounce, etc. | "⚠️ Audit failed for brokensite.com: timeout after 30s" |
| 🛑 Agent stopped | Agent crashes or pauses | "🛑 Agent stopped: rate limit hit. Resume?" (with inline keyboard) |
| 💰 Lead created | Prospect promoted to lead | "💰 New lead: Joe's Plumbing (score: 23) → CRM pipeline" |
| 📬 Bounce detected | Email bounced | "📬 Bounce: joe@joesplumbing.com — removed from sequence" |
| 🚫 Unsubscribe | Prospect opts out | "🚫 Unsubscribe: Manor Dental — marked do_not_contact" |

### 10.3 Inline Keyboard Actions

Critical notifications include **inline buttons** so you can act from your phone:

```python
# Reply received — inline actions
async def notify_reply(prospect, classification):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 Schedule Call", callback_data=f"schedule_{prospect.id}")],
        [InlineKeyboardButton("💰 Promote to Lead", callback_data=f"promote_{prospect.id}")],
        [InlineKeyboardButton("👀 View in Dashboard", callback_data=f"view_{prospect.id}")],
        [InlineKeyboardButton("⏭ Skip / Ignore", callback_data=f"skip_{prospect.id}")],
    ])
    await notify(
        f"⭐ *REPLY from {prospect.business_name}!*\n"
        f"📋 Classification: `{classification}`\n"
        f"📧 Subject: {prospect.last_reply_subject}\n"
        f"\n"
        f"💬 Preview: _{prospect.last_reply_preview[:200]}_",
        reply_markup=keyboard
    )
```

### 10.4 Command Interface

Full remote control from Telegram:

```
/status          → Agent status + current ring + today's stats
/pause           → Immediately pause the agent
/resume          → Resume the agent from where it stopped
/expand          → Approve expansion to the next geo ring
/stats           → Full KPI breakdown (discovered/contacted/opened/replied/meetings)
/prospect <name> → Look up a specific prospect by name
/ring <n>        → Status of a specific ring
/queue           → Show today's email queue (pending/sent/failed)
/digest          → Force-send the daily digest now
/kill            → Emergency stop — kills all activity immediately
/help            → Show all available commands
```

### 10.5 Webhook Integration with FastAPI

The Telegram bot runs as a **webhook** inside the existing FastAPI server — no separate process:

```python
# In automation/api/main.py
from telegram.ext import Application
from automation.api.services.telegram_notifier import setup_telegram_handlers

async def lifespan(app: FastAPI):
    # Start Telegram webhook
    tg_app = Application.builder().token(settings.telegram_bot_token).build()
    setup_telegram_handlers(tg_app)
    await tg_app.bot.set_webhook(f"{settings.api_base_url}/api/v1/telegram/webhook")
    yield
    await tg_app.bot.delete_webhook()

# Webhook endpoint
@app.post("/api/v1/telegram/webhook")
async def telegram_webhook(update: dict):
    tg_update = Update.de_json(update, bot)
    await tg_app.process_update(tg_update)
    return {"ok": True}
```

### 10.6 Daily Digest (Scheduled)

Sent every day at a configurable time (default: 8:00 AM CT):

```python
async def send_daily_digest():
    """Scheduled via APScheduler. Summarizes the last 24 hours."""
    stats = await get_24h_stats()
    
    msg = (
        f"📊 *Daily Outreach Digest — {date.today().strftime('%b %d, %Y')}*\n"
        f"\n"
        f"🔍 Discovered: {stats.discovered} new businesses\n"
        f"📧 Sent: {stats.emails_sent} emails\n"
        f"👀 Opened: {stats.opened} ({stats.open_rate:.1%})\n"
        f"⭐ Replies: {stats.replies}\n"
        f"📅 Meetings: {stats.meetings}\n"
        f"\n"
    )
    
    if stats.hot_leads:
        msg += "🔥 *Hot leads:*\n"
        for lead in stats.hot_leads:
            msg += f"  • {lead.business_name} — {lead.classification}\n"
    
    if stats.issues:
        msg += f"\n⚠️ Issues: {', '.join(stats.issues)}\n"
    
    msg += (
        f"\n📍 Ring progress:\n"
        f"  {stats.ring_summary}\n"
        f"\n🔋 Agent: {stats.agent_status} (uptime: {stats.uptime})"
    )
    
    await notify(msg)
```

---

## 11. Admin Dashboard UI

### 11.0 Dual-Mode Architecture: Localhost vs Production

The outreach tab operates in **two distinct modes** depending on where you access it from. This follows the same pattern already established in `admin.js` (API-first with Firebase RTDB fallback).

```
┌──────────────────────────────────────────────────────────────────────┐
│                    HOW MODE DETECTION WORKS                         │
│                                                                      │
│   outreach.js on load:                                               │
│     1. Try fetch(`${API_BASE}/health`, { timeout: 3000 })           │
│     2. If 200 → _mode = 'full'   (API reachable = you're home)     │
│     3. If timeout/error → _mode = 'light' (API down = you're away) │
│     4. Re-check every 30s (auto-upgrade to full if you come home)   │
│                                                                      │
│   const API_BASE = 'http://localhost:3001/api/v1';  // same as now  │
└──────────────────────────────────────────────────────────────────────┘
```

#### 🏠 Full Mode (localhost — at home, API reachable)

**Everything works.** The dashboard hits the local Docker API for all rich data:

| Feature | Data Source | Notes |
|---------|-------------|-------|
| Geo War Room Map | `GET /api/v1/outreach/map-dots` | Leaflet.js, all dots, click-to-expand |
| Prospect Pipeline (Kanban) | `GET /api/v1/outreach/prospects?status=X` | Drag-drop, full cards |
| Prospect Detail Card | `GET /api/v1/outreach/prospects/:id` | Audit scorecard, screenshots, timeline |
| Screenshots | `GET /api/v1/outreach/files/screenshot/:id/:type` | Full desktop + mobile WebP |
| Email Queue | `GET /api/v1/outreach/emails` | Preview, approve, bulk actions |
| Performance Charts | `GET /api/v1/outreach/stats` (detailed) | Open/reply/bounce rates, A/B results |
| Agent Log | Firebase `outreach/log` (real-time) | Streaming append |
| Agent Controls | `POST /api/v1/outreach/agent/start\|pause` | Start, pause, re-audit buttons |
| Sidebar KPIs | Firebase `outreach/stats` (real-time push) | Instant counter updates |
| Activity Feed | Firebase `outreach/activity` (real-time push) | Instant new-event notifications |

**Banner:** `🟢 Local API connected — full dashboard`

#### ☁️ Light Mode (production — away from home, API unreachable)

**Firebase-only view.** Since `localhost:3001` isn't reachable from the public internet, the outreach tab degrades gracefully to show only what's in Firebase RTDB (~40 KB):

| Feature | Data Source | Notes |
|---------|-------------|-------|
| Agent Status Light | Firebase `outreach/agent` | 🟢 running / 🔴 error / 🟡 paused |
| Sidebar KPIs | Firebase `outreach/stats` | Counters + rates (pre-calculated) |
| Ring Progress Bars | Firebase `outreach/rings` | Progress per ring |
| Activity Feed | Firebase `outreach/activity` | Last 50 events |
| Agent Log | Firebase `outreach/log` | Last 200 log lines |
| **🔔 Alerts Badge + Feed** | Firebase `outreach/alerts` | **Unread count badge + actionable notifications** |
| **Pipeline Funnel** | Firebase `outreach/funnel` | **Visual stage-by-stage breakdown** |
| **🔥 Hot Prospects Board** | Firebase `outreach/hot` | **Top 10 most engaged prospects** |
| **90-Day Sparklines** | Firebase `outreach/snapshots` | **Sent/opened/replied trend lines** |
| **Week vs Week Scorecard** | Firebase `outreach/scorecard` | **This week vs last week with deltas** |
| **Best Send Times Heatmap** | Firebase `outreach/heatmap` | **Day×hour grid of email performance** |
| **Template Leaderboard** | Firebase `outreach/tpl_stats` | **Which templates get the best replies** |
| **Industry Breakdown** | Firebase `outreach/industries` | **Top 10 industries by reply rate** |
| **Agent Health Timeline** | Firebase `outreach/health` | **72h CPU/mem/error sparklines** |

**What's hidden/disabled in light mode:**

| Feature | Why | Alternative |
|---------|-----|-------------|
| Geo Map | Needs 1000+ dots from API (~50 KB per ring) | See ring status in sidebar + funnel counts |
| Kanban Board | Needs paginated prospect list from API | **Hot prospects board shows top 10** |
| Prospect Detail | Needs full record from API + filesystem screenshots | Telegram sends you prospect alerts |
| Email Queue | Needs email list from API | Telegram notifies on every send |
| Performance Charts (detailed) | Needs granular metrics from API | **Sparklines + heatmap + scorecard cover 90% of insights** |
| Screenshots | Files on local Docker volume | Telegram sends screenshot with audit alert |
| Agent Start/Pause/Audit | API commands | Telegram `/pause`, `/start`, `/status` commands |

**Banner:** `☁️ Remote mode — live command center. Use Telegram for direct control.`

**Light mode UI layout ("Command Center Anywhere" — see §13.7):**

```
┌─────────────────────────────────────────────────────────────────────┐
│ ☁️ Remote mode — live command center · Telegram for direct control  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─ Agent ────┐  ┌─ Today ────────┐  ┌─ All Time ────────────┐    │
│  │ 🟢 RUNNING │  │ 📧 8 sent      │  │ 📊 847 prospects     │    │
│  │ Auditing   │  │ 👀 3 opened    │  │ 📧 234 contacted     │    │
│  │ joesplumb..│  │ ⭐ 1 replied   │  │ 👀 28.6% open rate   │    │
│  └────────────┘  └────────────────┘  │ ⭐ 5.1% reply rate   │    │
│                                       └──────────────────────┘    │
│                                                                     │
│  ┌─ 🔔 Alerts (3 new) ───────────────────────────────────────┐    │
│  │ ⭐ HIGH  Reply from Joe's Plumbing — interested in quote  │    │
│  │ 🎯 MED   Ring 0 (Manor) 100% complete — expand?           │    │
│  │ ⚠️ LOW   2 bounced emails today                            │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  ┌─ Pipeline Funnel ─────┐  ┌─ 🔥 Hot Prospects ─────────────┐   │
│  │ 847 ████████████ disc │  │ 1. Joe's Plumbing  87  opened  │   │
│  │ 523 ████████░░░ qual  │  │ 2. Manor Dental    82  replied │   │
│  │ 234 █████░░░░░░ sent  │  │ 3. ATX HVAC        79  opened  │   │
│  │  67 ██░░░░░░░░░ open  │  │ 4. Hill Country AC 76  sent    │   │
│  │  12 █░░░░░░░░░░ reply │  │ 5. Texas Eye Care  74  meeting │   │
│  │   3 ░░░░░░░░░░░ meet  │  │   ... +5 more                  │   │
│  └───────────────────────┘  └─────────────────────────────────┘   │
│                                                                     │
│  ┌─ 90-Day Trend (sparklines) ────────────────────────────────┐   │
│  │ Sent    ▁▂▃▃▅▅▆▇▇█  ↑ 12% vs last week                   │   │
│  │ Opened  ▁▁▂▂▃▃▄▅▅▆  ↑ 8%                                 │   │
│  │ Replied ▁▁▁▂▂▂▃▃▃▄  ↑ 50% 🎉                             │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─ Week vs Week ─────────┐  ┌─ Best Templates ──────────────┐   │
│  │ This week:             │  │ initial_audit  33% open  6% rp│   │
│  │  📧 45 sent  (+12%)   │  │ follow_value   41% open  8% rp│   │
│  │  👀 14 opens (+8%)    │  │ follow_social  28% open  4% rp│   │
│  │  ⭐ 3 replies (+50%)  │  │ breakup        52% open 11% rp│   │
│  └────────────────────────┘  └────────────────────────────────┘   │
│                                                                     │
│  ┌─ Best Send Times (heatmap) ────────────────────────────────┐   │
│  │       9am  10am 11am 12pm  1pm  2pm  3pm  4pm  5pm        │   │
│  │ Mon   🟢   🟢   🟡   ⚪   ⚪   🟡   🟡   ⚪   ⚪        │   │
│  │ Tue   🟢   🟢   🟢   🟡   ⚪   ⚪   🟡   ⚪   ⚪        │   │
│  │ Wed   🟡   🟢   🟢   🟢   🟡   ⚪   ⚪   ⚪   ⚪        │   │
│  │ Thu   🟢   🟢   🟡   🟡   ⚪   ⚪   🟡   🟡   ⚪        │   │
│  │ Fri   🟡   🟡   🟡   ⚪   ⚪   ⚪   ⚪   ⚪   ⚪        │   │
│  │ 🟢 = high reply rate  🟡 = moderate  ⚪ = low/no data     │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─ Top Industries ──────────────────────────────────────────┐    │
│  │ plumber      156 found  7.9% reply ████████░░             │    │
│  │ dentist       89 found  5.6% reply █████░░░░░             │    │
│  │ hvac         134 found  4.5% reply ████░░░░░░             │    │
│  │ restaurant   201 found  3.2% reply ███░░░░░░░             │    │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─ Ring Progress ────────────────────────────────────────────┐   │
│  │ Ring 0: Manor        ████████░░ 82%  (156 found, 8 rep)   │   │
│  │ Ring 1: Pflugerville ███░░░░░░░ 34%  (312, 2 rep)         │   │
│  │ Ring 2: Round Rock   ░░░░░░░░░░  0%  (pending)            │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─ Agent Health (72h) ──────────────────────────────────────┐    │
│  │ CPU  ▁▂▂▃▂▂▃▅▃▂▂▁▁▁▂▂▃▃▂▂▁▁▁▁  avg 23%                  │    │
│  │ Mem  ▃▃▃▃▃▃▃▃▃▃▃▃▃▃▃▃▃▃▃▃▃▃▃▃  412 MB (stable)          │    │
│  │ Err  ▁▁▁▁▁▁▁▁▁▁▁█▁▁▁▁▁▁▁▁▁▁▁▁  1 error 48h ago          │    │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─ Recent Activity (live) ───────────────────────────────────┐   │
│  │ 3m ago   🔍 Discovered: Joe's Plumbing (Manor)            │   │
│  │ 15m ago  📧 Sent to: Manor Dental Group                   │   │
│  │ 1h ago   👀 Opened by: ABC Roofing (2nd time)             │   │
│  │ 3h ago   ⭐ Reply from: Texas Eye Care — POSITIVE 😊      │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─ Agent Log (live) ─────────────────────────────────────────┐   │
│  │ [INFO]  14:23:01  audit   Auditing joesplumbing.com...     │   │
│  │ [INFO]  14:22:45  crawl   Found 3 new businesses in Manor │   │
│  │ [WARN]  14:20:12  send    Rate limit approaching (8/10)   │   │
│  └────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

> **This is the same ~87 KB of Firebase data.** No API calls. No Docker. Just Firebase listeners rendering a full command center. The "light" mode is no longer light — it's a war room you can carry in your pocket.

#### Mode Detection Code

```javascript
// outreach.js — dual mode detection
let _mode = 'light';  // default to light (safe)
let _apiAvailable = false;

async function detectMode() {
    try {
        const res = await fetch(`${API_BASE}/health`, {
            signal: AbortSignal.timeout(3000)
        });
        if (res.ok) {
            _apiAvailable = true;
            if (_mode !== 'full') {
                _mode = 'full';
                showBanner('🟢 Local API connected — full dashboard', 'success');
                initFullMode();  // load map, kanban, etc.
            }
        }
    } catch {
        _apiAvailable = false;
        if (_mode !== 'light') {
            _mode = 'light';
            showBanner('☁️ Remote mode — showing live stats only', 'info');
            teardownFullMode();  // hide map, kanban
        }
    }
}

// Check on load, then every 30s (auto-upgrade when you get home)
detectMode();
setInterval(detectMode, 30000);

function initFullMode() {
    // Show all 6 sections
    document.querySelectorAll('.outreach-full-only').forEach(el => el.style.display = '');
    document.querySelector('.outreach-light-panel').style.display = 'none';
    loadGeoMap();
    loadKanban();
    loadEmailQueue();
    loadPerformanceCharts();
}

function teardownFullMode() {
    // Hide API-dependent sections, show light panel
    document.querySelectorAll('.outreach-full-only').forEach(el => el.style.display = 'none');
    document.querySelector('.outreach-light-panel').style.display = '';
    // Firebase listeners already running — they power the light view
}
```

> **Key insight:** Firebase listeners run in BOTH modes. In full mode, they power the sidebar.
> In light mode, they power the entire main panel. Zero extra Firebase reads for light mode.

---

### 11.1 Tab Layout

New 7th tab: **Outreach** (icon: 🎯 or 🕵️)

**Sidebar Panel (`outreach-sidebar`):**

```
┌─────────────────────────────┐
│ 🎯 OUTREACH AGENT          │
│ ─────────────────────────── │
│                             │
│ ┌─────────┐ ┌────────────┐ │
│ │▶ RUNNING │ │ ⏸ PAUSE    │ │  ← Agent control
│ └─────────┘ └────────────┘ │
│                             │
│ ┌ KPI Cards ──────────────┐ │
│ │ 📊 847 Prospects        │ │
│ │ 📧 234 Contacted        │ │
│ │ 👀 67 Opened (28.6%)    │ │
│ │ ⭐ 12 Replied (5.1%)    │ │
│ │ 📅 3 Meetings Booked    │ │
│ └─────────────────────────┘ │
│                             │
│ ┌ Ring Progress ──────────┐ │
│ │ Ring 0: Manor    ████░ 82% │
│ │ Ring 1: Pfluger  ██░░░ 34% │
│ │ Ring 2: RR       ░░░░░  0% │
│ └─────────────────────────┘ │
│                             │
│ ┌ Jump To ─────────────────┐│
│ │ → Prospect Pipeline      ││
│ │ → Geo Map                ││
│ │ → Email Queue            ││
│ │ → Performance            ││
│ │ → Sequences              ││
│ │ → Agent Logs             ││
│ └──────────────────────────┘│
│                             │
│ ┌ Recent Activity ────────┐ │
│ │ 🔍 Discovered: Joe's    │ │
│ │    Plumbing (3m ago)    │ │
│ │ 📧 Sent to: Manor      │ │
│ │    Dental (15m ago)     │ │
│ │ 👀 Opened by: ABC      │ │
│ │    Roofing (1h ago)     │ │
│ │ ⭐ Reply from: Texas    │ │
│ │    Eye Care (3h ago)    │ │
│ └─────────────────────────┘ │
└─────────────────────────────┘
```

**Main Panel (`outreach-panel`):**

Six sub-sections (scrollable) — **all require Full Mode (localhost)**. In Light Mode, the main panel shows the compact Firebase-only layout from §11.0 above.

#### Section 1: Geo War Room Map *(full mode only)*
- Interactive map (Leaflet.js with OpenStreetMap tiles — free, no API key)
- Concentric ring overlays
- Prospect dots color-coded by status
- Click dot → popup with business card
- Ring stats overlay

#### Section 2: Prospect Pipeline (Kanban) *(full mode only)*
```
┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌──────────┐
│Discovered│ │ Audited │ │Enriched │ │Contacted│ │ Replied │ │ Meeting  │
│   (312)  │ │  (245)  │ │  (189)  │ │  (156)  │ │   (12)  │ │ Booked(3)│
│ ┌──────┐ │ │ ┌──────┐│ │ ┌──────┐│ │ ┌──────┐│ │ ┌──────┐│ │ ┌───────┐│
│ │Joe's │ │ │ │Manor ││ │ │ATX   ││ │ │Hill  ││ │ │Texas ││ │ │Austin ││
│ │Plumb.│ │ │ │Dental││ │ │HVAC  ││ │ │Count.││ │ │Eye   ││ │ │Bakes ││
│ │⚪ New │ │ │ │🔴 23 ││ │ │📧 ✓ ││ │ │📧 x2 ││ │ │😊 +  ││ │ │📅 2/21││
│ └──────┘ │ │ └──────┘│ │ └──────┘│ │ └──────┘│ │ └──────┘│ │ └───────┘│
│ ┌──────┐ │ │ ┌──────┐│ │        │ │ ┌──────┐│ │        │ │         │
│ │...   │ │ │ │...   ││ │        │ │ │...   ││ │        │ │         │
│ └──────┘ │ │ └──────┘│ │        │ │ └──────┘│ │        │ │         │
└─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘ └──────────┘
```

#### Section 3: Prospect Detail Card *(full mode only, on click)*
```
┌──────────────────────────────────────────────────────────┐
│ JOE'S PLUMBING                          Score: 23/100 🔴│
│ ──────────────────────────────────────────────────────── │
│ 📍 1234 Main St, Manor TX 78653  (0.8 mi)              │
│ ⭐ 4.6 (87 reviews) · 📞 (512) 555-0123                │
│ 🌐 joesplumbing.com · Built on: Wix                    │
│ 👤 Joe Martinez (Owner) · joe@joesplumbing.com ✓        │
│                                                          │
│ ┌─ AUDIT SCORECARD ────────────────────────────────────┐ │
│ │ Speed:    ██░░░░░░░░ 18/100  (8.2s load)            │ │
│ │ Mobile:   ███░░░░░░░ 31/100  (not responsive)       │ │
│ │ SEO:      ██░░░░░░░░ 15/100  (no meta, no schema)   │ │
│ │ Security: █████░░░░░ 52/100  (SSL ok, no headers)   │ │
│ │ Design:   ██░░░░░░░░ 22/100  (dated ~2015)          │ │
│ │ A11y:     ███░░░░░░░ 34/100  (no alt tags)          │ │
│ └──────────────────────────────────────────────────────┘ │
│                                                          │
│ ┌─ SCREENSHOTS ────────────────────────────────────────┐ │
│ │ [Desktop Screenshot]     [Mobile Screenshot]          │ │
│ └──────────────────────────────────────────────────────┘ │
│                                                          │
│ ┌─ COMPETITORS ────────────────────────────────────────┐ │
│ │ 🏢 Austin Plumbing Co  — 78/100 (⬆ 55 pts higher)  │ │
│ │ 🏢 RR Pipe Masters     — 62/100 (⬆ 39 pts higher)  │ │
│ └──────────────────────────────────────────────────────┘ │
│                                                          │
│ ┌─ OUTREACH TIMELINE ─────────────────────────────────┐ │
│ │ Feb 14 📧 Initial email sent         ✓ Opened 2x   │ │
│ │ Feb 17 📧 Follow-up #1 sent          ○ Not opened   │ │
│ │ Feb 21 📧 Follow-up #2 scheduled     ⏳ Pending     │ │
│ └──────────────────────────────────────────────────────┘ │
│                                                          │
│ ┌─ ACTIONS ───────────────────────────────────────────┐  │
│ │ [👀 Preview Email] [📧 Send Now] [⏭ Skip]          │  │
│ │ [🚀 Promote to Lead] [🗑 Mark Dead] [✏️ Edit]      │  │
│ └─────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

#### Section 4: Email Queue & Preview *(full mode only)*
- List of emails scheduled for today/this week
- Preview rendered email before sending
- Bulk approve/reject
- A/B subject line testing display

#### Section 5: Performance Dashboard *(full mode only)*
```
┌──────────────────────────────────────────┐
│ 📊 OUTREACH PERFORMANCE                 │
│                                          │
│ Open Rate:    28.6%  ████████░░  (goal: 30%)
│ Reply Rate:    5.1%  ██░░░░░░░░  (goal: 5%)
│ Meeting Rate:  1.3%  █░░░░░░░░░  (goal: 2%)
│ Bounce Rate:   2.1%  █░░░░░░░░░  (goal: <3%)
│                                          │
│ ┌─ Replies by Sentiment ──────────────┐  │
│ │ 😊 Positive:  5  (41.7%)           │  │
│ │ 😐 Neutral:   4  (33.3%)           │  │
│ │ 😞 Negative:  2  (16.7%)           │  │
│ │ 🚫 Unsub:     1  (8.3%)            │  │
│ └─────────────────────────────────────┘  │
│                                          │
│ ┌─ Best Performing ──────────────────┐   │
│ │ Template: "Audit Hook"    32% open │   │
│ │ Industry: Dental          8% reply │   │
│ │ Ring:     Manor           12% reply│   │
│ │ Day:      Tuesday         35% open │   │
│ │ Time:     9-10am          38% open │   │
│ └────────────────────────────────────┘   │
└──────────────────────────────────────────┘
```

#### Section 6: Agent Activity Log *(both modes — Firebase-powered)*
- Real-time scrolling log (matches existing build log style)
- Shows what the agent is doing: crawling, auditing, composing, sending
- Color-coded: 🔍 discovery, 📊 audit, 📧 email, ⭐ reply, ❌ error

---

## 12. Backend API Routes

### New file: `automation/api/routes/outreach.py`

```
GET    /api/v1/outreach/stats              → Dashboard KPIs
GET    /api/v1/outreach/prospects           → List (filterable, paginated)
GET    /api/v1/outreach/prospects/:id       → Detail + audit + emails
PATCH  /api/v1/outreach/prospects/:id       → Update status/notes
POST   /api/v1/outreach/prospects/:id/audit → Trigger manual re-audit
POST   /api/v1/outreach/prospects/:id/email → Compose & preview email
POST   /api/v1/outreach/prospects/:id/send  → Send email now
POST   /api/v1/outreach/prospects/:id/promote → Promote to Lead
DELETE /api/v1/outreach/prospects/:id       → Mark as dead/do_not_contact

GET    /api/v1/outreach/emails              → Email queue (scheduled/sent)
GET    /api/v1/outreach/emails/:id          → Email detail + tracking
POST   /api/v1/outreach/emails/:id/approve  → Approve scheduled email
DELETE /api/v1/outreach/emails/:id          → Cancel scheduled email

GET    /api/v1/outreach/rings               → Geo ring status
POST   /api/v1/outreach/rings/:id/crawl     → Trigger crawl for ring
PATCH  /api/v1/outreach/rings/:id           → Pause/resume ring

GET    /api/v1/outreach/sequences           → List sequences
POST   /api/v1/outreach/sequences           → Create sequence
PATCH  /api/v1/outreach/sequences/:id       → Edit sequence

POST   /api/v1/outreach/agent/start         → Start the agent
POST   /api/v1/outreach/agent/pause         → Pause the agent
GET    /api/v1/outreach/agent/status        → Agent status + current task
GET    /api/v1/outreach/agent/log           → Recent log entries (SSE)

GET    /api/v1/outreach/map-dots            → Lightweight lat/lng/status/score (field-filtered)
                                              ?ring_id=X&fields=id,lat,lng,status,score
GET    /api/v1/outreach/files/screenshot/:prospect_id/:type  → Serve WebP (desktop|mobile)
GET    /api/v1/outreach/files/audit/:prospect_id             → Serve Lighthouse JSON (gunzipped)

GET    /api/v1/outreach/track/open/:tracking_id   → Email open pixel (1x1 gif)
GET    /api/v1/outreach/track/click/:tracking_id   → Link click redirect
```

> **Note on map-dots:** Returns only the fields needed for map rendering (~50 bytes/prospect).
> Full prospect detail is loaded on-click via `GET /prospects/:id`. This keeps initial map load
> under 50 KB even with 1000 dots.

---

## 13. Firebase RTDB Structure

> **Design principle: Firebase = real-time sidebar + live indicators ONLY.**  
> Prospect records, audit data, email content, screenshots — ALL in PostgreSQL / filesystem.  
> Firebase stores ~40 KB total regardless of how many prospects we have.

### 13.1 Complete Node Tree

```
outreach/
  │
  ├── agent/                             // ~200 bytes — always loaded
  │     ├── status: "running"            // running | paused | error | idle | awaiting_approval
  │     ├── current_task: "auditing joesplumbing.com"
  │     ├── current_ring: "ring_0"
  │     ├── uptime_seconds: 86400
  │     ├── error_msg: null              // populated when status = "error"
  │     └── last_heartbeat: 1708300000   // unix timestamp, checked for staleness
  │
  ├── stats/                             // ~500 bytes — sidebar KPI cards
  │     ├── total_prospects: 847
  │     ├── total_contacted: 234
  │     ├── total_opened: 67
  │     ├── total_replied: 12
  │     ├── total_meetings: 3
  │     ├── total_bounced: 5
  │     ├── today_sent: 8               // resets at midnight
  │     ├── today_opened: 3
  │     ├── today_replied: 1
  │     ├── open_rate: 28.6             // pre-calculated, not computed client-side
  │     ├── reply_rate: 5.1
  │     └── updated_at: 1708300000
  │
  ├── rings/                             // ~2 KB — sidebar ring progress bars
  │     ├── ring_0/
  │     │     ├── name: "Manor"
  │     │     ├── status: "complete"     // pending | crawling | complete | paused
  │     │     ├── businesses_found: 156
  │     │     ├── contacted_pct: 82      // integer percentage
  │     │     └── replied_count: 8
  │     ├── ring_1/
  │     │     ├── name: "Pflugerville"
  │     │     ├── status: "crawling"
  │     │     ├── businesses_found: 312
  │     │     ├── contacted_pct: 34
  │     │     └── replied_count: 2
  │     └── ...                          // max 7 rings = ~2 KB
  │
  ├── activity/                          // ~15 KB — sidebar "Recent Activity" feed
  │     │                                // Auto-pruned to last 50 entries
  │     ├── {push_id}/                   // Firebase push ID = chronological
  │     │     ├── type: "opened"         // discovered | audited | sent | opened | replied | meeting | error
  │     │     ├── icon: "👀"
  │     │     ├── name: "Joe's Plumbing"
  │     │     ├── detail: "Opened your email (2nd time)"
  │     │     └── ts: 1708300000
  │     └── ...
  │
  └── log/                               // ~20 KB — agent execution log (scrolling)
        │                                // Auto-pruned to last 200 entries
        ├── {push_id}/
        │     ├── level: "info"          // debug | info | warn | error
        │     ├── msg: "Auditing joesplumbing.com..."
        │     ├── cat: "audit"           // crawl | audit | recon | compose | send | track | system
        │     └── ts: 1708300000
        └── ...
```

### 13.2 What is NOT in Firebase (and why)

| Data | Where It Lives | Why Not Firebase |
|------|---------------|------------------|
| Prospect records | PostgreSQL `prospects` table | 10K records × 150 bytes = 1.5 MB; download bandwidth blowout at ~900 MB/month |
| Audit scores | PostgreSQL `website_audits` table | Loaded on-demand when user clicks a prospect |
| Map dots (lat/lng/status) | PostgreSQL → REST API `GET /map-dots?ring_id=X` | 1000 dots = 50 KB via API; no need for real-time push |
| Kanban cards | PostgreSQL → REST API `GET /prospects?status=X` | Paginated, filtered server-side |
| Email HTML content | PostgreSQL `outreach_emails` table | 5-10 KB per email, only loaded on preview |
| Screenshots | Filesystem `/data/screenshots/` | 40-100 KB each as WebP; never stored in any database |
| Lighthouse JSON | Filesystem `/data/audits/` (gzipped) | 200-500 KB raw; extracted metrics in PG columns |
| Reply bodies | PostgreSQL `outreach_emails` table | Valuable business intel, needs full-text search |

### 13.3 Firebase Listeners in `outreach.js`

```javascript
// outreach.js — Firebase real-time listeners (sidebar only)
(function OutreachModule() {
    let _listeners = {};  // track active listeners for cleanup

    function initFirebaseListeners() {
        const db = firebase.database();
        
        // 1. Agent status indicator (top of sidebar)
        _listeners.agent = db.ref('outreach/agent').on('value', snap => {
            const agent = snap.val() || {};
            updateAgentStatusLight(agent.status);     // 🟢/🔴/🟡 dot
            updateCurrentTask(agent.current_task);     // "Auditing..."
        });
        
        // 2. KPI counters (sidebar cards)
        _listeners.stats = db.ref('outreach/stats').on('value', snap => {
            const s = snap.val() || {};
            updateKPICards(s);  // Animate counter changes
        });
        
        // 3. Ring progress bars (sidebar)
        _listeners.rings = db.ref('outreach/rings').on('value', snap => {
            const rings = snap.val() || {};
            updateRingBars(rings);
        });
        
        // 4. Activity feed — new items only (append, don't reload)
        _listeners.activity = db.ref('outreach/activity')
            .orderByChild('ts')
            .limitToLast(20)
            .on('child_added', snap => {
                prependActivityItem(snap.val());
            });
        
        // 5. Agent log — streaming append
        _listeners.log = db.ref('outreach/log')
            .orderByChild('ts')
            .limitToLast(50)
            .on('child_added', snap => {
                appendLogLine(snap.val());
            });
    }
    
    function cleanupFirebaseListeners() {
        const db = firebase.database();
        db.ref('outreach/agent').off('value', _listeners.agent);
        db.ref('outreach/stats').off('value', _listeners.stats);
        db.ref('outreach/rings').off('value', _listeners.rings);
        db.ref('outreach/activity').off('child_added', _listeners.activity);
        db.ref('outreach/log').off('child_added', _listeners.log);
        _listeners = {};
    }
    // ... rest of outreach module
})();
```

### 13.4 Firebase Write Rules

Add to `firebase-database.rules.json`:

```json
"outreach": {
    ".read": "auth != null",
    ".write": "auth != null",
    "agent": { ".indexOn": ["last_heartbeat"] },
    "activity": { ".indexOn": ["ts"] },
    "log": { ".indexOn": ["ts"] },
    "alerts": { ".indexOn": ["ts"] },
    "snapshots": { ".indexOn": [".key"] },
    "scorecard": { ".indexOn": [".key"] },
    "health": { ".indexOn": ["ts"] }
}
```

### 13.5 Firebase Size Budget

| Node | Max Entries | Bytes/Entry | Max Size | Prune Strategy |
|------|-----------|-------------|----------|----------------|
| `agent/` | 1 (singleton) | ~200 | 200 B | Overwrite |
| `stats/` | 1 (singleton) | ~500 | 500 B | Overwrite |
| `rings/` | 7 (max rings) | ~300 | 2.1 KB | Overwrite |
| `activity/` | 50 | ~300 | 15 KB | FIFO 50 (every 5th push + nightly) |
| `log/` | 200 | ~100 | 20 KB | FIFO 200 (every 10th push + nightly) |
| `snapshots/` | 90 (days) | ~200 | 18 KB | Age > 90 days (nightly janitor) |
| `hot/` | 10 (top prospects) | ~500 | 5 KB | Overwrite (daily cycle) |
| `funnel/` | 1 (singleton) | ~300 | 300 B | Overwrite (daily cycle) |
| `heatmap/` | 1 (singleton) | ~3000 | 3 KB | Overwrite (daily cycle) |
| `tpl_stats/` | 5 (templates) | ~300 | 1.5 KB | Overwrite (daily cycle) |
| `industries/` | 10 (top) | ~300 | 3 KB | Overwrite (daily cycle) |
| `alerts/` | 20 | ~400 | 8 KB | FIFO 20 (every 5th push + nightly) |
| `scorecard/` | 12 (weeks) | ~300 | 3.6 KB | Age > 84 days (nightly janitor) |
| `health/` | 72 (hours) | ~100 | 7.2 KB | Age > 72h (nightly janitor) |
| **Total** | | | **~87 KB** | |

At 87 KB, we use **0.009%** of the 1 GB free tier. The full analytics command center (see §13.7) fits in less space than a single JPEG.

Download bandwidth with optimized pruning (see §13.7.7): **~99 MB/month** — **~1% of the 10 GB free limit**. This includes page loads, real-time push syncs, prune reads, nightly janitor sweeps, and daily summary pushes. We have **99× headroom** before hitting the free tier ceiling.

### 13.6 Pruning Logic

```python
import random

async def prune_firebase_node(path: str, max_children: int):
    """Keep only the newest N entries under a Firebase path.
    Called by individual push functions AND the nightly janitor."""
    ref = firebase_db.reference(path)
    snapshot = ref.order_by_child('ts').get()
    if snapshot and len(snapshot) > max_children:
        # Delete oldest entries beyond the limit
        entries = sorted(snapshot.items(), key=lambda x: x[1].get('ts', 0))
        to_delete = entries[:len(entries) - max_children]
        updates = {key: None for key, _ in to_delete}   # None = delete in Firebase
        ref.update(updates)

async def push_activity(event: dict):
    """Push a new activity event. Prune every 5th push (nightly janitor catches the rest)."""
    ref = firebase_db.reference('outreach/activity')
    ref.push(event)
    if random.randint(1, 5) == 1:  # ~20% of pushes trigger prune — saves 80% bandwidth
        await prune_firebase_node('outreach/activity', max_children=50)

async def push_log(entry: dict):
    """Push a log line. Prune every 10th push (nightly janitor catches the rest)."""
    ref = firebase_db.reference('outreach/log')
    ref.push(entry)
    if random.randint(1, 10) == 1:  # ~10% of pushes trigger prune — saves 90% bandwidth
        await prune_firebase_node('outreach/log', max_children=200)
```

> **Why not prune every push?** Each prune downloads ALL entries via REST to check the count.
> For `log/` with 200 entries at ~100 B each, that's 20 KB downloaded per prune read.
> At ~500 log events/day × 20 KB = 300 MB/month just from prune reads!
> Pruning every 10th push: 50 reads/day × 20 KB = 30 MB/month — **10× savings**.
> The nightly janitor (§13.7.5) sweeps up any overflow as a safety net.
```

### 13.7 Firebase Budget Maximizer — "Command Center Anywhere"

> **The math:** We're using ~87 KB of 1 GB storage (0.009%) and ~200–300 MB of 10 GB bandwidth (~3%).
> That leaves us **~999 MB of storage** and **~9.7 GB of bandwidth** sitting idle on the free tier.
> The light mode currently shows a bare-bones status page. Let's turn it into a **full analytics command center** — entirely from Firebase, no API needed.

**Design principle:** The Docker agent computes aggregates from PostgreSQL → pushes pre-computed summaries to Firebase. Light mode renders them instantly. **Zero client-side computation, zero API dependency.**

**Golden rule:** PostgreSQL keeps everything forever (no pruning). Firebase is an ephemeral mirror with auto-pruning. If Firebase data vanishes tomorrow, the agent rebuilds it from PostgreSQL on the next cycle — self-healing, zero-maintenance.

#### 13.7.1 New Firebase Nodes

```
outreach/
  │
  ├── ... (existing: agent, stats, rings, activity, log — see §13.1)
  │
  ├── snapshots/                         // ~18 KB — 90-day daily trend data
  │     ├── {YYYY-MM-DD}/               // One entry per calendar day
  │     │     ├── sent: 8
  │     │     ├── opened: 3
  │     │     ├── replied: 1
  │     │     ├── bounced: 0
  │     │     ├── discovered: 12
  │     │     ├── meetings: 0
  │     │     ├── pipeline_value: 4500   // $ estimate of active pipeline
  │     │     ├── open_rate: 37.5
  │     │     └── reply_rate: 12.5
  │     └── ...                          // Auto-pruned to 90 days
  │
  ├── hot/                               // ~5 KB — top 10 hottest prospects (overwritten each cycle)
  │     ├── 0/
  │     │     ├── name: "Joe's Plumbing"
  │     │     ├── industry: "plumber"
  │     │     ├── score: 87              // composite: audit_score × engagement_level
  │     │     ├── status: "opened"       // discovered | contacted | opened | replied
  │     │     ├── last_action: "Opened 2x in 24h"
  │     │     ├── city: "Manor"
  │     │     └── ts: 1708300000
  │     ├── 1/ ...
  │     └── 9/                           // Always exactly 10 (or fewer if <10 total)
  │
  ├── funnel/                            // ~300 bytes — pipeline stage counts (overwritten)
  │     ├── discovered: 847
  │     ├── qualified: 523               // audit score above threshold
  │     ├── contacted: 234
  │     ├── opened: 67
  │     ├── replied: 12
  │     ├── meeting: 3
  │     ├── converted: 1                 // promoted to CRM lead
  │     └── updated_at: 1708300000
  │
  ├── heatmap/                           // ~3 KB — email performance by day×hour (overwritten)
  │     ├── mon/
  │     │     ├── 9: { sent: 12, opened: 5, replied: 2 }
  │     │     ├── 10: { sent: 8, opened: 3, replied: 1 }
  │     │     └── ...                    // only hours with data
  │     ├── tue/ ...
  │     └── sun/ ...
  │
  ├── tpl_stats/                         // ~1.5 KB — template performance leaderboard (overwritten)
  │     ├── initial_audit/
  │     │     ├── sent: 200
  │     │     ├── opened: 67
  │     │     ├── replied: 12
  │     │     ├── open_rate: 33.5
  │     │     └── reply_rate: 6.0
  │     ├── follow_up_value/ ...
  │     ├── follow_up_social/ ...
  │     └── breakup/ ...
  │
  ├── industries/                        // ~3 KB — top 10 industries by reply rate (overwritten)
  │     ├── 0/
  │     │     ├── name: "plumber"
  │     │     ├── count: 156
  │     │     ├── contacted: 89
  │     │     ├── replied: 7
  │     │     └── reply_rate: 7.9
  │     └── 9/ ...
  │
  ├── alerts/                            // ~8 KB — actionable notifications (FIFO 20)
  │     ├── {push_id}/
  │     │     ├── type: "reply"          // reply | meeting | error | ring_complete | milestone
  │     │     ├── priority: "high"       // high | medium | low
  │     │     ├── icon: "⭐"
  │     │     ├── title: "Reply from Joe's Plumbing"
  │     │     ├── detail: "Interested in a quote — check Telegram"
  │     │     ├── read: false
  │     │     └── ts: 1708300000
  │     └── ...                          // Auto-pruned to 20 entries
  │
  ├── scorecard/                         // ~4 KB — weekly comparison (rolling 12 weeks)
  │     ├── {YYYY-Www}/                  // ISO week key: "2025-W08"
  │     │     ├── sent: 45
  │     │     ├── opened: 14
  │     │     ├── replied: 3
  │     │     ├── meetings: 1
  │     │     ├── discovered: 67
  │     │     ├── delta_sent: "+12%"     // vs previous week (pre-computed string)
  │     │     ├── delta_replied: "+50%"
  │     │     └── week_start: 1708214400
  │     └── ...                          // Auto-pruned to 12 weeks
  │
  └── health/                            // ~7 KB — agent health timeline (72 hours)
        ├── {HH-MMDD}/                   // Keyed by hour — overwrites same slot next day
        │     ├── cpu_pct: 23
        │     ├── mem_mb: 412
        │     ├── queue_depth: 3         // pending tasks in queue
        │     ├── errors_1h: 0
        │     ├── emails_1h: 2
        │     └── ts: 1708300000
        └── ...                          // Auto-pruned to 72 hours
```

#### 13.7.2 Why These Nodes — The "Coffee Shop Test"

When you open the admin dashboard from your phone at a coffee shop, instead of seeing a degraded "sorry, go home" status page, you see:

| Panel | What It Tells You | Powered By |
|-------|-------------------|------------|
| **Alerts** (🔔 badge) | "Reply from X — needs attention" | `alerts/` — real-time |
| **Pipeline Funnel** | How many prospects at each stage | `funnel/` — overwrite |
| **Hot Prospects** | Top 10 most engaged leads right now | `hot/` — overwrite |
| **90-Day Sparklines** | Sent/opened/replied trending up or down | `snapshots/` — once |
| **Week vs Week** | Am I doing better this week than last? | `scorecard/` — once |
| **Best Send Times** | Heatmap of when emails perform best | `heatmap/` — once |
| **Template Leaderboard** | Which email templates are winning | `tpl_stats/` — overwrite |
| **Industry Breakdown** | Which industries respond to outreach | `industries/` — overwrite |
| **Agent Health** | CPU/mem/errors over 72h — is it stable? | `health/` — once |
| **Ring Progress** | Geographic expansion status | `rings/` — real-time |
| **Activity Feed** | Live event stream | `activity/` — real-time |
| **Agent Log** | Execution log tail | `log/` — real-time |

That's a **real analytics dashboard** — not a dumb status page. All from ~87 KB of Firebase.

#### 13.7.3 New Firebase Listeners in `outreach.js`

```javascript
// ─── BUDGET MAXIMIZER LISTENERS (added to initFirebaseListeners) ───

// 6. Alerts — real-time notification badge + feed
_listeners.alerts = db.ref('outreach/alerts')
    .orderByChild('ts')
    .limitToLast(20)
    .on('value', snap => {
        const alerts = snap.val() || {};
        updateAlertsBadge(alerts);         // 🔔 3 unread
        renderAlertsPanel(alerts);
    });

// 7. Pipeline funnel — real-time stage counts
_listeners.funnel = db.ref('outreach/funnel').on('value', snap => {
    renderFunnel(snap.val() || {});        // visual funnel bars
});

// 8. Hot prospects — live leaderboard
_listeners.hot = db.ref('outreach/hot').on('value', snap => {
    renderHotProspects(snap.val() || {});  // top 10 cards
});

// 9. Template leaderboard — updates on each batch send
_listeners.tplStats = db.ref('outreach/tpl_stats').on('value', snap => {
    renderTemplateLeaderboard(snap.val() || {});
});

// 10. Industry breakdown — updates on each cycle
_listeners.industries = db.ref('outreach/industries').on('value', snap => {
    renderIndustryBreakdown(snap.val() || {});
});

// ─── ONE-SHOT LOADS (no persistent listeners — save bandwidth) ───
// These change infrequently (daily/weekly/hourly). Load once per page view.

// 11. 90-day sparklines — loaded once, rebuilt nightly
db.ref('outreach/snapshots')
    .orderByKey()
    .limitToLast(90)
    .once('value', snap => {
        renderSparklines(snap.val() || {}); // ▁▂▃▃▅▅▆▇▇█ trend lines
    });

// 12. Weekly scorecard — loaded once, rebuilt weekly
db.ref('outreach/scorecard')
    .orderByKey()
    .limitToLast(12)
    .once('value', snap => {
        renderWeeklyScorecard(snap.val() || {}); // this week vs last
    });

// 13. Send-time heatmap — loaded once, rebuilt nightly
db.ref('outreach/heatmap')
    .once('value', snap => {
        renderSendTimeHeatmap(snap.val() || {}); // day×hour grid
    });

// 14. Agent health timeline — loaded once, updated hourly
db.ref('outreach/health')
    .orderByChild('ts')
    .limitToLast(72)
    .once('value', snap => {
        renderHealthTimeline(snap.val() || {}); // CPU/mem/err sparklines
    });
```

> **Bandwidth trick:** Nodes that change infrequently (`snapshots`, `scorecard`, `heatmap`, `health`) use `.once('value')` — a single REST read, no persistent WebSocket. Only nodes that benefit from instant updates (`alerts`, `funnel`, `hot`, `tpl_stats`, `industries`) use `.on()` listeners. This cuts persistent connections from 14 to 10 and saves ~40% of listener bandwidth.

#### 13.7.4 Server-Side Push Functions

```python
# ─── DAILY SUMMARY PUSH (runs at end of each day's cycle) ───────────

async def push_firebase_summaries(db: AsyncSession):
    """Compute aggregates from PostgreSQL → push to Firebase. Idempotent.
    Called nightly by APScheduler + on-demand via Telegram /refresh command."""
    
    # 1. Daily snapshot
    today = date.today().isoformat()
    stats = await compute_daily_stats(db)
    firebase_db.reference(f'outreach/snapshots/{today}').set(stats)
    
    # 2. Hot prospects (top 10 by composite score × engagement)
    hot = await get_hot_prospects(db, limit=10)
    firebase_db.reference('outreach/hot').set(
        {str(i): p for i, p in enumerate(hot)}
    )
    
    # 3. Pipeline funnel counts
    funnel = await compute_funnel_counts(db)
    funnel['updated_at'] = int(time.time())
    firebase_db.reference('outreach/funnel').set(funnel)
    
    # 4. Send-time heatmap (all-time aggregated by day×hour)
    heatmap = await compute_email_heatmap(db)
    firebase_db.reference('outreach/heatmap').set(heatmap)
    
    # 5. Template leaderboard
    tpl = await compute_template_stats(db)
    firebase_db.reference('outreach/tpl_stats').set(tpl)
    
    # 6. Industry breakdown (top 10 by reply rate)
    industries = await compute_industry_stats(db, limit=10)
    firebase_db.reference('outreach/industries').set(
        {str(i): ind for i, ind in enumerate(industries)}
    )
    
    # 7. Weekly scorecard (if today is Sunday)
    if date.today().weekday() == 6:
        week_key = date.today().strftime('%G-W%V')
        scorecard = await compute_weekly_scorecard(db)
        firebase_db.reference(f'outreach/scorecard/{week_key}').set(scorecard)


# ─── REAL-TIME ALERT PUSH (fires on important events) ───────────────

async def push_alert(alert_type: str, priority: str, title: str,
                     detail: str, icon: str):
    """Push an actionable alert. Auto-prunes to 20 on every 5th push."""
    ref = firebase_db.reference('outreach/alerts')
    ref.push({
        'type': alert_type,
        'priority': priority,
        'icon': icon,
        'title': title,
        'detail': detail,
        'read': False,
        'ts': int(time.time())
    })
    # Optimized: prune every 5th push (random), not every push
    if random.randint(1, 5) == 1:
        await prune_firebase_node('outreach/alerts', max_children=20)

# Wired into existing event handlers:
# - Reply detected     → push_alert("reply", "high", ...)
# - Meeting booked     → push_alert("meeting", "high", ...)
# - Agent error        → push_alert("error", "high", ...)
# - Ring complete      → push_alert("ring_complete", "medium", ...)
# - 100th email sent   → push_alert("milestone", "low", ...)


# ─── HOURLY HEALTH PUSH (APScheduler, every 60 min) ─────────────────

async def push_health_snapshot():
    """Push agent resource usage to Firebase. Keyed by hour — self-overwriting."""
    import psutil
    key = datetime.now().strftime('%H-%m%d')  # e.g., "14-0221" — overwrites same hour next cycle
    firebase_db.reference(f'outreach/health/{key}').set({
        'cpu_pct': psutil.cpu_percent(),
        'mem_mb': psutil.Process().memory_info().rss // (1024 * 1024),
        'queue_depth': await get_pending_task_count(),
        'errors_1h': await get_error_count_last_hour(),
        'emails_1h': await get_emails_sent_last_hour(),
        'ts': int(time.time())
    })
```

#### 13.7.5 Firebase Janitor — Self-Cleaning System

```python
# ─── NIGHTLY JANITOR (APScheduler, runs at 3:00 AM daily) ───────────

async def firebase_janitor():
    """Single nightly sweep enforcing ALL retention rules across every node.
    Idempotent — safe to run multiple times. Acts as a safety net behind
    the per-push prune logic. If prunes were skipped or failed, this catches them."""
    
    now = int(time.time())
    
    # FIFO prunes (by count)
    await prune_firebase_node('outreach/activity', max_children=50)
    await prune_firebase_node('outreach/log', max_children=200)
    await prune_firebase_node('outreach/alerts', max_children=20)
    
    # Age-based prunes
    await prune_by_age('outreach/snapshots', max_age_days=90)
    await prune_by_age('outreach/scorecard', max_age_days=84)   # 12 weeks
    await prune_by_age('outreach/health', max_age_hours=72)
    
    logger.info("🧹 Firebase janitor: nightly sweep complete")


async def prune_by_age(path: str, max_age_days: int = 0, max_age_hours: int = 0):
    """Delete entries older than max_age from a keyed Firebase node."""
    ref = firebase_db.reference(path)
    snapshot = ref.get()
    if not snapshot:
        return
    
    cutoff = int(time.time()) - (max_age_days * 86400) - (max_age_hours * 3600)
    to_delete = {}
    
    for key, val in snapshot.items():
        ts = val.get('ts', 0) if isinstance(val, dict) else 0
        if ts > 0 and ts < cutoff:
            to_delete[key] = None  # None = delete in Firebase
    
    if to_delete:
        ref.update(to_delete)
        logger.info(f"🧹 Pruned {len(to_delete)} expired entries from {path}")
```

#### 13.7.6 Self-Healing — Rebuild from PostgreSQL

```python
async def rebuild_firebase_from_postgres(db: AsyncSession):
    """Nuclear option: regenerate ALL Firebase summary nodes from PostgreSQL.
    Called on first boot if Firebase is empty, or via Telegram /rebuild command.
    Every write is an idempotent set() — safe to run anytime, no side effects."""
    
    logger.info("🔄 Rebuilding Firebase summaries from PostgreSQL...")
    
    # 1. Rebuild daily snapshots (last 90 days)
    for day_offset in range(90):
        day = date.today() - timedelta(days=day_offset)
        stats = await compute_daily_stats_for_date(db, day)
        if stats['sent'] > 0 or stats['discovered'] > 0:
            firebase_db.reference(f'outreach/snapshots/{day.isoformat()}').set(stats)
    
    # 2. Rebuild weekly scorecards (last 12 weeks)
    for week_offset in range(12):
        week_start = date.today() - timedelta(weeks=week_offset)
        week_key = week_start.strftime('%G-W%V')
        scorecard = await compute_weekly_scorecard_for_week(db, week_start)
        if scorecard['sent'] > 0:
            firebase_db.reference(f'outreach/scorecard/{week_key}').set(scorecard)
    
    # 3. Rebuild all overwrite nodes (hot, funnel, heatmap, tpl_stats, industries)
    await push_firebase_summaries(db)
    
    # 4. Rebuild recent activity + log from PostgreSQL event history
    recent_events = await get_recent_events(db, limit=50)
    for event in recent_events:
        firebase_db.reference('outreach/activity').push(event)
    
    recent_logs = await get_recent_log_entries(db, limit=200)
    for entry in recent_logs:
        firebase_db.reference('outreach/log').push(entry)
    
    logger.info("✅ Firebase rebuild complete — all nodes refreshed from PostgreSQL")


# ─── AUTO-DETECT EMPTY FIREBASE ON BOOT ─────────────────────────────

async def check_and_rebuild_on_boot(db: AsyncSession):
    """Called once at FastAPI startup. If outreach/agent is missing,
    assume Firebase is empty and trigger a full rebuild."""
    agent = firebase_db.reference('outreach/agent').get()
    if not agent:
        logger.warning("Firebase outreach data missing — triggering rebuild...")
        await rebuild_firebase_from_postgres(db)
```

> **Telegram integration:** `/rebuild` command triggers `rebuild_firebase_from_postgres()` on demand.
> Useful after a Firebase project migration or accidental data wipe.

#### 13.7.7 Bandwidth Budget (Updated)

With the optimized prune strategy (every Nth push + nightly janitor):

| Source | Calculation | Monthly |
|--------|-------------|---------|
| **Page loads** (all nodes) | 87 KB × 600 loads | 52 MB |
| **`.once()` reads** (snapshots, scorecard, heatmap, health) | 32 KB × 600 loads | 19 MB |
| **Real-time pushes** to `.on()` listeners | ~2 KB avg × 150 pushes/day × 30 | 9 MB |
| ** Prune reads** (optimized: every 5th–10th push) | ~15 KB × 30 prune reads/day × 30 | 14 MB |
| **Nightly janitor** sweep | 87 KB × 30 nights | 3 MB |
| **Daily summary push** (server writes) | ~50 KB × 30 days | 2 MB |
| **Hourly health push** | 0.1 KB × 720/month | ~0 MB |
| **Total** | | **~99 MB/month** |

That's **~1% of the 10 GB free tier** — with a full analytics command center.

> Compare to the original plan's 38 KB bare-bones setup that would've used ~500 MB/month with un-optimized prunes. The Budget Maximizer adds **9× more features** while using **5× less bandwidth** thanks to optimized pruning + `.once()` reads.

---

## 14. Clever Tricks & Secret Weapons

### 🧠 Trick 1: "The Audit Report" — Auth-Protected Dashboard View
Don't just email a text audit — show it during a **screenshare** via the admin dashboard.

The audit detail card (Section 3 in dashboard UI) renders their audit in beautiful charts, screenshots, and competitor comparison — but it's **behind Firebase Auth**, not a public URL. This protects our methodology and audit data from being shared with competitors.

**Workflow:**
1. Audit runs → data stored in PostgreSQL (never public)
2. You open the prospect detail card in admin dashboard
3. During a call, you share your screen and walk them through their scores
4. They see the analysis live, but can't forward a URL to another agency
5. The exclusivity creates urgency — "I can only show you this live"

> **Why not public URLs?** If we give them a shareable audit link, they take our research and hand it to a cheaper developer. By keeping it screenshare-only, we control the narrative and the deal.

### 🧠 Trick 2: "Before/After Mockup" Generator *(FUTURE — Local GPU + Local Model)*
> **Deferred:** This feature requires AI image generation which burns tokens. Will be implemented later when we have a local GPU + local model (Stable Diffusion / SDXL) running on-premise. For now, any before/after mockups are done manually in Figma when a prospect shows serious interest (after they reply).

### 🧠 Trick 3: Competitor Weaponization
For each prospect, find 2-3 competitors in the same industry + same area. If a competitor has a significantly better website, mention it. Nothing motivates a business owner like "your competitor across the street has a better online presence."

### 🧠 Trick 4: Review Sentiment Mining
Scrape their Google reviews for complaints about "can't find website", "couldn't book online", "site was confusing." Quote these in the email: "I noticed one of your customers mentioned your booking system was confusing..."

### 🧠 Trick 5: Seasonal Timing Hooks
```python
SEASONAL_HOOKS = {
    'tax_season':     {'months': [1,2,3], 'industries': ['accountant', 'tax_prep']},
    'summer':         {'months': [5,6], 'industries': ['hvac', 'pool_service', 'landscaping']},
    'back_to_school': {'months': [7,8], 'industries': ['tutoring', 'daycare']},
    'holiday':        {'months': [10,11], 'industries': ['restaurant', 'retail', 'bakery']},
    'new_year':       {'months': [1], 'industries': ['fitness_studio', 'gym']},
    'wedding':        {'months': [3,4,5], 'industries': ['photographer', 'florist', 'caterer']},
}
# "With wedding season approaching, your website is the first thing brides-to-be will see..."
```

### 🧠 Trick 6: "Broken Things" Detector
Specifically scan for embarrassing issues:
- Broken images, 404 pages, "under construction" notices
- Copyright year stuck on 2019
- "Powered by Wix/WordPress" in footer
- Lorem ipsum text still on page
- Broken contact form
- Social links going to dead pages

Include the most embarrassing one in the email. "I noticed your About page still says 'Coming Soon'..."

### 🧠 Trick 7: Google Business Profile Optimization Upsell
While auditing, check if their Google Business Profile is optimized:
- Missing business hours?
- No photos?
- No posts?
- Wrong category?
Add this as a bonus finding: "I also noticed your Google Business Profile could use some love..."

### 🧠 Trick 8: Reply Classification + Auto-Routing (Keyword-Based — No AI)
When a prospect replies, **keyword matching** classifies the reply (zero AI tokens):
```python
import re

REPLY_PATTERNS = {
    'interested':     r'interested|love to|let.?s (talk|chat|meet|connect)|sounds? good|tell me more|schedule|demo',
    'need_more_info': r'how much|pricing|cost|what do you offer|more (info|details|about)|examples|portfolio',
    'not_right_now':  r'not (right )?now|maybe later|busy|next (month|quarter|year)|circle back|reach out later',
    'not_interested': r'not interested|no thanks?|no thank you|pass|don.?t need|already have|happy with',
    'unsubscribe':    r'unsubscribe|stop (emailing|contacting)|remove me|opt.?out|do not (contact|email)',
    'referral':       r'try (contacting|reaching)|talk to|check with|my (friend|colleague|partner)|refer',
    'angry':          r'spam|reported|stop|harass|legal|lawyer|sue|block',
}

def classify_reply(body: str) -> str:
    """Classify reply using keyword regex — zero AI tokens."""
    body_lower = body.lower()
    for classification, pattern in REPLY_PATTERNS.items():
        if re.search(pattern, body_lower):
            return classification
    return 'unknown'  # Falls to manual review queue

REPLY_ACTIONS = {
    'interested':       # → Auto-create Lead in CRM, notify via Telegram
    'need_more_info':   # → Queue informational follow-up
    'not_right_now':    # → Schedule resurrection email in 3 months
    'not_interested':   # → Park, re-approach in 6 months with new angle
    'unsubscribe':      # → Immediate removal, mark do_not_contact
    'referral':         # → Extract referred business, add to prospects
    'angry':            # → Immediate removal + blacklist
    'unknown':          # → Manual review queue + Telegram alert
}
```

### 🧠 Trick 9: The "Neighborhood Effect" Email
"I'm redesigning the website for [nearby business they'd recognize]. While I'm in the area, I'm offering free audits to other businesses on [their street/area]."

### 🧠 Trick 10: Telegram Digest — Daily Summary While You Sleep
Every day at a configured time (e.g., 8 AM), the bot sends a Telegram summary:
```
📊 Daily Outreach Digest — Feb 21, 2025

🔍 Discovered: 12 new businesses
📧 Sent: 8 emails
👀 Opened: 3 (Joe's Plumbing, Manor Dental, ATX HVAC)
⭐ Replies: 1 (Texas Eye Care — INTERESTED 🎉)
📅 Meetings: 0

📍 Ring 0 (Manor): 82% complete
📍 Ring 1 (Pflugerville): 34% complete

⚠️ Issues: 2 bounced emails, 1 audit timeout

🔋 Agent Status: Running (uptime: 6d 14h)
```
This replaces the need for "passive income from audit pages" — our audit data stays private and our daily visibility comes via Telegram instead.

---

## 15. Implementation Phases

### Phase 1: Foundation + Telegram (Week 1)
**Goal:** Tab exists, database ready, Telegram bot running, basic prospect list

- [ ] Add `outreach` tab to admin HTML (sidebar + main panel)
- [ ] Extend `switchTab()` in admin.js
- [ ] Create `admin/js/outreach.js` (IIFE pattern)
- [ ] Add SQLAlchemy models: `prospect`, `website_audit`, `outreach_email`, `outreach_sequence`, `geo_ring`
- [ ] Run Alembic migration
- [ ] Create `automation/api/routes/outreach.py` with basic CRUD
- [ ] **Telegram bot setup** — webhook inside FastAPI, `/status`, `/pause`, `/resume`, `/kill`, **`/rebuild`** commands
- [ ] **`telegram_notifier.py`** service — `notify()` function callable from anywhere
- [ ] Firebase RTDB structure setup (all §13.1 + §13.7.1 nodes)
- [ ] **`firebase_summarizer.py`** — daily summary push + alert push functions (§13.7.4)
- [ ] **`firebase_janitor.py`** — nightly prune cron + self-healing rebuild (§13.7.5–6)
- [ ] **Auto-rebuild on boot** — `check_and_rebuild_on_boot()` in FastAPI startup
- [ ] Basic prospect list UI (sidebar + detail card)
- [ ] Light mode "Command Center" layout with all §13.7 panels

### Phase 2: Crawl Engine (Week 2)
**Goal:** Agent can discover businesses via Google Maps

- [ ] Google Places API integration (nearby search + details)
- [ ] Geo-ring system implementation
- [ ] De-duplication logic
- [ ] Crawl worker with APScheduler
- [ ] Real-time Firebase push for discovery events
- [ ] Crawl progress UI in sidebar (ring bars)
- [ ] Business category targeting system
- [ ] Agent start/pause controls

### Phase 3: Intel Engine (Week 3)
**Goal:** Websites get audited and scored

- [ ] Playwright-based website crawler + screenshotter
- [ ] Lighthouse audit integration (via `lighthouse` CLI or Chrome DevTools Protocol)
- [ ] Tech stack detection (built-in Wappalyzer rules)
- [ ] SEO scan (meta tags, sitemap, robots.txt, schema)
- [ ] Security scan (SSL, headers)
- [ ] Heuristic Design Judge (rule-based scoring — no AI tokens)
- [ ] Composite scoring + priority formula
- [ ] Audit scorecard UI (bars, grades, screenshots)
- [ ] Competitor detection (same industry + same ring)

### Phase 4: Recon Engine (Week 4)
**Goal:** Find owner names and emails

- [ ] Website scrape for contact info (email, names, phone)
- [ ] WHOIS lookup integration
- [ ] Email pattern guessing + SMTP verification
- [ ] Google search enrichment
- [ ] Social media scan (Facebook, LinkedIn)
- [ ] Email verification scoring
- [ ] Recon status in prospect card UI

### Phase 5: Template Engine (Week 5)
**Goal:** Template-driven email composition with variable injection (zero AI)

- [ ] Email template library (4 sequence steps × industry variants)
- [ ] **Template engine** — `render_template()` with Jinja2-style variable injection
- [ ] Email preview UI (rendered HTML preview in dashboard)
- [ ] Subject line A/B variants (pre-written, not AI-generated)
- [ ] Variable injection from prospect + audit data
- [ ] "Broken things" detector integration
- [ ] Competitor weaponization text
- [ ] Seasonal hook injection

### Phase 6: Cadence & Sending (Week 6)
**Goal:** Emails get sent and tracked

- [ ] **Gmail SMTP sending** (reuse existing `email_service.py` with App Password)
- [ ] Open tracking pixel (1x1 transparent PNG with tracking ID)
- [ ] Click tracking (redirect through tracking endpoint)
- [ ] Sequence scheduler (APScheduler cron)
- [ ] Smart timing per industry
- [ ] Exit conditions (reply, bounce, unsubscribe)
- [ ] Email queue UI (approve/reject upcoming sends)
- [ ] Sending rate limiting (50/day initial, scale up)

### Phase 7: Geo Map & Analytics (Week 7)
**Goal:** War room visualization + performance tracking

- [ ] Leaflet.js map integration
- [ ] Geo-ring overlay visualization
- [ ] Prospect dot plotting with color coding
- [ ] Ring expansion logic + **manual approval via Telegram** (no auto-progression)
- [ ] Performance dashboard (open rate, reply rate, meeting rate)
- [ ] Best-performing template/industry/time analysis
- [ ] **Keyword-based reply classification** (regex patterns — no AI)
- [ ] Auto-routing (promote to CRM lead on positive reply) + Telegram notification

### Phase 8: Advanced Features (Week 8+)
**Goal:** Polish, optimize, and expand tricks

- [ ] Auth-protected audit detail cards (screenshare-ready views in dashboard)
- [ ] Review sentiment mining from Google reviews
- [ ] Google Business Profile analysis
- [ ] "Neighborhood effect" email variant
- [ ] Resurrection sequence (re-engage after 3 months)
- [ ] Telegram daily digest (scheduled summary)
- [ ] Telegram inline keyboard actions (promote, schedule, skip from phone)
- [ ] A/B testing framework for subject lines
- [ ] Referral extraction from replies
- [ ] *(FUTURE: local GPU + local model)* Before/after mockup generator

---

## 16. File Inventory

### New Files to Create

```
admin/
  js/
    outreach.js                    # Main outreach tab JS (IIFE, ~800-1200 lines)

automation/
  api/
    models/
      prospect.py                  # SQLAlchemy: Prospect + WebsiteAudit + OutreachEmail
      geo_ring.py                  # SQLAlchemy: GeoRing
      outreach_sequence.py         # SQLAlchemy: OutreachSequence
    routes/
      outreach.py                  # FastAPI routes for all outreach endpoints
      telegram_webhook.py          # Telegram webhook + command handlers
    services/
      crawl_engine.py              # Google Maps/Places discovery worker
      intel_engine.py              # Website auditing (Lighthouse + Playwright + heuristic judge)
      recon_engine.py              # Email/owner discovery
      template_engine.py           # Template-driven email composition (Jinja2 variable injection, NO AI)
      cadence_engine.py            # Sequence scheduler + sending (via existing Gmail SMTP)
      email_tracker.py             # Open/click tracking endpoints
      geo_ring_manager.py          # Ring expansion logic + manual Telegram approval
      telegram_notifier.py         # Telegram bot: notify(), commands, inline keyboards
      reply_classifier.py          # Keyword-based reply classification (regex, NO AI)
      firebase_summarizer.py       # Daily/weekly aggregate push to Firebase (§13.7.4)
      firebase_janitor.py          # Nightly prune sweep + self-healing rebuild (§13.7.5–6)
    templates/
      email/
        initial_audit.html         # Email template: initial contact
        follow_up_value.html       # Email template: follow-up 1
        follow_up_social.html      # Email template: follow-up 2
        breakup.html               # Email template: breakup
        resurrection.html          # Email template: re-engage
```

### Data Directory Structure (Docker Volume)

```
/data/                                  # Docker volume mount — NOT in git
  screenshots/
    {prospect_id}/
      desktop.webp                     # ~30-60 KB, Playwright fullpage
      mobile.webp                      # ~20-50 KB, Playwright 375px viewport
  audits/
    {prospect_id}/
      lighthouse.json.gz               # ~40-80 KB gzipped (200-500 KB raw)
```

Docker volume mount in `docker-compose.api.yml`:
```yaml
volumes:
  - outreach_data:/data
```

### Files to Modify

```
admin/index.html                   # Add outreach tab button + sidebar panel + main panel HTML
admin/js/admin.js                  # Extend switchTab() with 'outreach' case
automation/api/main.py             # Register outreach router + Telegram webhook + scheduler jobs
automation/api/config.py           # Add TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID settings
automation/requirements.txt        # Add: python-telegram-bot, apscheduler, jinja2, etc.
automation/docker-compose.api.yml  # Add env vars for Telegram + Google Maps API key + /data volume
automation/firebase-database.rules.json # Add outreach/ node rules (see §13.4)
```

### External Dependencies to Add

```python
# automation/requirements.txt additions
python-telegram-bot>=21.0          # Telegram bot (webhook mode inside FastAPI)
apscheduler>=3.10.0               # Job scheduling for crawl/send cycles
Jinja2>=3.1.0                     # Template rendering for email composition
dnspython>=2.6.0                  # DNS/MX lookups for email verification
python-whois>=0.9.0               # WHOIS lookups
beautifulsoup4>=4.12.0            # HTML parsing for recon scraping
lxml>=5.0.0                       # Fast HTML parser
Pillow>=10.0.0                    # Screenshot processing
psutil>=5.9.0                     # Agent health metrics (CPU, mem) for Firebase health node
```

> **Note:** No `anthropic` or `openai` SDK needed — email composition is template-driven, reply classification is regex-based, design scoring is heuristic. Zero AI dependencies.

### Environment Variables Needed

```env
# Google Maps / Places API
GOOGLE_MAPS_API_KEY=...

# Email sending — REUSE EXISTING Gmail SMTP (already in config.py)
# No new email vars needed! Uses settings.smtp_email + settings.smtp_app_password
# Sends from: ajayadesign@gmail.com via smtp.gmail.com:587
SENDER_NAME=Ajaya Dahal

# Telegram Bot (created via @BotFather)
TELEGRAM_BOT_TOKEN=...            # From BotFather → /newbot
TELEGRAM_CHAT_ID=...              # Your personal chat ID (get via /start with @userinfobot)

# Optional: Hunter.io for email enrichment
HUNTER_API_KEY=...

# Tracking base URL (for open/click tracking)
TRACKING_BASE_URL=https://api.ajayadesign.com

# FUTURE (not needed now): AI for mockup generation
# ANTHROPIC_API_KEY=...           # Only if/when we add AI features later
```

---

## 17. Legal & Compliance

### CAN-SPAM Compliance (Required)
- [x] Include physical mailing address in every email
- [x] Include clear "unsubscribe" link in every email
- [x] Honor unsubscribe requests within 10 business days (we do it instantly)
- [x] Don't use deceptive subject lines
- [x] Identify the message as an ad/solicitation
- [x] Use accurate "From" and "Reply-To" headers

### Best Practices
- **Rate limiting:** Start with 30 emails/day, warm up sender reputation over 4 weeks to ~100/day
- **Sending domain:** Use a subdomain (e.g., `outreach.ajayadesign.com`) to protect main domain reputation
- **SPF + DKIM + DMARC:** Must be configured on the sending domain
- **Bounce handling:** Immediately stop sending to bounced addresses
- **Do-Not-Contact list:** Maintain and respect permanently
- **Data retention:** Purge audit data for uninterested prospects after 12 months
- **Opt-out database:** Cross-reference with national DNC registry for phone outreach

### Data Collection Ethics
- Only collect publicly available business information
- Don't scrape personal social media profiles
- Respect robots.txt when auditing websites
- Don't store passwords, financial data, or private communications
- WHOIS data is public record — fair game
- Google Maps data is publicly listed by the business

---

## Summary

This system transforms cold outreach from a manual grind into a **lean, autonomous operation** — without burning AI tokens on every email or giving away our research to competitors.

### Core Principles Recap

1. **Zero AI token burn** — Email composition uses templates + variable injection; reply classification uses keyword regex; design scoring uses heuristic rules. No Claude/GPT calls in the hot path.
2. **Auth-protected audit data** — Audit reports live behind Firebase Auth in the admin dashboard. Shared only via live screenshare — never a public URL that a prospect can forward to a cheaper developer.
3. **Gmail SMTP (existing infra)** — Reuses the same `email_service.py` that sends contracts and invoices. No new email provider, no SES, no third-party SMTP.
4. **Telegram-first remote control** — Every major event (discovery, audit, send, open, reply, meeting, error) triggers a Telegram notification. Inline keyboards let you approve ring expansion, promote leads, and control the agent from your phone.
5. **Manual build trigger only** — No auto-building websites for every prospect. Website builds happen only *after a deal closes* — saving massive token/compute costs. Future: local GPU + local model for mockups.
6. **Geo-ring expansion by permission** — The agent pauses at each ring boundary and asks via Telegram. You decide when to expand, not the algorithm.

### Key Differentiators

1. **Data-driven personalization** — Every email contains specific, verifiable data about their business (audit scores, broken things, competitor gaps)
2. **The free audit hook** — Nobody ignores a report card about their own business
3. **Competitor pressure** — "Your competitor's site scores 78; yours scores 23"
4. **Intelligent timing** — Industry-specific send windows (wedding season, tax season, etc.)
5. **Geo-ring expansion** — Systematic territory coverage, local-first
6. **Full pipeline visibility** — War-room dashboard + Telegram shows everything in real-time
7. **CRM integration** — Hot leads flow directly into the existing build pipeline
8. **Always on, always lean** — The agent works 24/7 while you focus on building sites, and it costs almost nothing to run

### Cost to Run

| Item | Cost |
|------|------|
| Google Maps API | ~$10-20/month (Places + Geocoding) |
| Gmail SMTP | **Free** (reusing existing App Password) |
| AI tokens | **$0** (template-driven, no AI calls) |
| Telegram Bot | **Free** |
| PostgreSQL + FastAPI | Already running (existing Docker stack) |
| **Total incremental cost** | **~$10-20/month** |

The system pays for itself after closing **one client** from outreach. At even a 1% meeting-to-close rate with 100 prospects/month, that's 1 new client per month — on autopilot, for roughly the cost of a lunch.
