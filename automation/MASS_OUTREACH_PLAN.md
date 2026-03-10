# Mass Outreach Plan — 1,000 Emails/Day for $0

## The Problem

We have **9,991 registered contractors** (7,468 with emails) from Dallas TX.
Gmail SMTP free tier caps at **~200 emails/day**.
We need **~1,000/day** without paying for any email service.

---

## The Solution: Multi-SMTP Provider Pool

Aggregate free tiers from **7 providers** into a single rotating pool.
The cadence engine already handles scheduling — we just need a provider abstraction
that tracks daily quotas and rotates automatically.

| # | Provider | Free Tier | Daily Limit | SMTP Host | Port |
|---|----------|-----------|-------------|-----------|------|
| 1 | **Gmail** (App Password) | Unlimited* | **200/day** | smtp.gmail.com | 587 |
| 2 | **Brevo** (Sendinblue) | 300/day forever | **300/day** | smtp-relay.brevo.com | 587 |
| 3 | **Mailjet** | 6,000/month | **200/day** | in-v3.mailjet.com | 587 |
| 4 | **SendGrid** | 100/day forever | **100/day** | smtp.sendgrid.net | 587 |
| 5 | **Elastic Email** | 100/day | **100/day** | smtp.elasticemail.com | 2525 |
| 6 | **Resend** | 3,000/month | **100/day** | smtp.resend.com | 465 |
| 7 | **SMTP2GO** | 1,000/month | **~33/day** | mail.smtp2go.com | 2525 |
| | **TOTAL** | | **~1,033/day** | | |

> *Gmail "200" is conservative — Google enforces 500 for consumer, 2000 for Workspace.
> We stay at 200 to avoid triggering spam flags.

### Signup Effort (One-Time ~30 Minutes)

1. **Gmail** — Already configured (`SMTP_EMAIL` + `SMTP_APP_PASSWORD`)
2. **Brevo** — Sign up at brevo.com → Settings → SMTP & API → get SMTP key
3. **Mailjet** — Sign up at mailjet.com → Account Settings → SMTP Settings → get API key/secret
4. **SendGrid** — Sign up at sendgrid.com → Settings → API Keys → create with Mail Send permission
5. **Elastic Email** — Sign up at elasticemail.com → Settings → SMTP → get credentials
6. **Resend** — Sign up at resend.com → API Keys → use as SMTP password
7. **SMTP2GO** — Sign up at smtp2go.com → Settings → Users → get SMTP credentials

All use **your same From address** (your Gmail) — the providers just act as relays.
SPF record on your domain should include all providers' SPF includes.

---

## Architecture

```
┌─────────────────────────────────────────────┐
│              Admin Dashboard                 │
│  ┌─────────┐ ┌──────────┐ ┌──────────────┐ │
│  │ Import   │ │ Provider │ │   Sending    │ │
│  │ Wizard   │ │ Manager  │ │  Dashboard   │ │
│  └────┬─────┘ └────┬─────┘ └──────┬───────┘ │
└───────┼─────────────┼──────────────┼─────────┘
        │             │              │
        ▼             ▼              ▼
┌─────────────────────────────────────────────┐
│              API  (FastAPI)                  │
│                                              │
│  POST /outreach/import        ← Excel data   │
│  GET/POST /outreach/providers ← SMTP creds   │
│  GET /outreach/send-queue     ← daily view   │
│  POST /outreach/send-now      ← manual flush │
│  GET /outreach/dashboard      ← stats        │
│                                              │
│  ┌──────────────────────────────────────┐    │
│  │        SMTP Provider Pool            │    │
│  │                                      │    │
│  │  pick_provider() →                   │    │
│  │    1. Check daily_sent < daily_limit │    │
│  │    2. Round-robin among available    │    │
│  │    3. Fallback to next provider      │    │
│  │    4. If all exhausted → queue rest  │    │
│  │                                      │    │
│  │  Providers stored in PostgreSQL:     │    │
│  │    smtp_providers table              │    │
│  │    (name, host, port, user, pass,    │    │
│  │     daily_limit, daily_sent,         │    │
│  │     last_reset, enabled, priority)   │    │
│  └──────────────────────────────────────┘    │
│                                              │
│  ┌──────────────────────────────────────┐    │
│  │       Cadence Engine (existing)      │    │
│  │  Schedules emails across the day:    │    │
│  │  • 8am-6pm CT window (business hrs)  │    │
│  │  • 3-5 min random gap between sends  │    │
│  │  • Tue-Thu heavy, Mon/Fri lighter    │    │
│  │  • Never weekends                    │    │
│  └──────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
```

---

## Database Changes

### New Table: `smtp_providers`

```sql
CREATE TABLE smtp_providers (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL UNIQUE,        -- 'gmail', 'brevo', 'mailjet', etc.
    host        TEXT NOT NULL,
    port        INTEGER NOT NULL DEFAULT 587,
    username    TEXT NOT NULL,
    password    TEXT NOT NULL,               -- encrypted at rest
    use_tls     BOOLEAN DEFAULT TRUE,
    from_email  TEXT,                        -- override From, or NULL = default
    daily_limit INTEGER NOT NULL DEFAULT 100,
    daily_sent  INTEGER NOT NULL DEFAULT 0,
    last_reset  DATE NOT NULL DEFAULT CURRENT_DATE,
    enabled     BOOLEAN DEFAULT TRUE,
    priority    INTEGER DEFAULT 0,           -- higher = preferred
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

### Modify Existing: `outreach_emails`

Add column:
```sql
ALTER TABLE outreach_emails ADD COLUMN smtp_provider_id UUID REFERENCES smtp_providers(id);
```

This tracks which provider delivered each email — essential for debugging
bounces and per-provider reputation monitoring.

---

## Excel Import Pipeline

### Step 1 — Parse & Normalize

```
Excel Row → {
    registration_type: "Electrical (EL)",
    business_name: "SMITH ELECTRIC LLC",       -- from Contractor column
    owner_name: "John Smith",                  -- parsed from Contractor
    address: "123 Main St",
    city: "Dallas", state: "TX", zip: "75243",
    phone: "(972) 479-0292",
    email: "john@smithelectric.com"
}
```

- Split `Contractor` field: last-name-first format → "SMITH, JOHN" → owner_name = "John Smith"
- Split `City-State` field: "DALLAS ,TX 75243" → city, state, zip
- Normalize phone: strip to digits, format as (XXX) XXX-XXXX
- Lowercase email, trim whitespace
- Skip rows with empty email

### Step 2 — Deduplicate

- Group by email (case-insensitive)
- If same person has multiple registrations, merge registration_types as tags
- ~7,468 emails → likely ~5,000-6,000 unique after dedup

### Step 3 — Insert as Prospects

- Status: `imported` (new state before `discovered`)
- Source: `dallas_contractor_registry`
- Tags: registration types as JSON array
- `has_website`: NULL (unknown until we crawl)
- `wp_score`: NULL (calculate after audit)

### Step 4 — Verify Emails (Pre-Send)

Before sending, verify each email is deliverable:
- **MX record check** — does the domain have mail servers?
- **SMTP RCPT TO check** — does the mailbox exist? (non-destructive probe)
- Mark as `email_verified: true/false`
- Skip sending to unverified addresses (saves quota)

This is free and built into Python's `smtplib` + `dns.resolver`.

---

## Email Templates — Contractor-Specific

### Template Strategy

Different pitch per contractor type. The message: **"You're a licensed contractor,
but when someone Googles you, what do they find?"**

#### Template Variables (from prospect data)

| Variable | Source | Example |
|----------|--------|---------|
| `{{owner_first}}` | Parsed from Contractor | "John" |
| `{{business_name}}` | Contractor field | "Smith Electric" |
| `{{registration_type}}` | Registration Type | "Electrical" |
| `{{city}}` | City-State field | "Dallas" |
| `{{industry_noun}}` | Mapped from type | "electrician" |
| `{{service_example}}` | Mapped from type | "panel upgrades" |

#### Sequence: 3-Touch Drip

**Email 1 — The Hook** (Day 0)
```
Subject: {{owner_first}}, your {{registration_type}} license is public — your website should be too

Hi {{owner_first}},

I noticed {{business_name}} is a registered {{industry_noun}} in {{city}}.
That means you passed inspections, you're legit — but when someone
Googles "{{industry_noun}} near me," does your name come up?

I build websites for contractors like you. Fast, mobile-friendly,
shows up on Google. Here's one I just finished for a plumber in DFW:
[link to portfolio example]

Would a quick 5-minute look at what I'd build for you be worth it?

— Ajaya
AjayaDesign.com
```

**Email 2 — The Proof** (Day 3, if no open/reply)
```
Subject: Re: Quick question about {{business_name}}

Hey {{owner_first}},

Just following up. Here's what happened for a roofer I worked with:
- Before: No website, zero Google presence
- After: Page 1 for "{{city}} roofing," 12 new leads/month

I could show you a free mockup for {{business_name}} — no cost,
no commitment. Just reply "sure" and I'll send it over.

— Ajaya
```

**Email 3 — The Last Chance** (Day 7, if no open/reply)
```
Subject: Closing the loop — {{business_name}}

Hi {{owner_first}},

Last note from me. If now's not the right time, no worries.

But if you ever want a website that actually brings in
{{service_example}} jobs from Google, I'm here.

Just reply to this email anytime.

— Ajaya
AjayaDesign.com

P.S. Here's your free website audit — I ran it anyway: [audit link]
```

---

## Sending Strategy

### Daily Schedule (1,000 emails/day)

```
Provider rotation across the day (8am-6pm CT):

 8:00 -  9:30  │ Gmail (100)      ← warm start
 9:30 - 11:00  │ Brevo (150)
11:00 - 12:30  │ Mailjet (100) + SendGrid (50)
12:30 -  1:30  │ Lunch pause — no sends
 1:30 -  3:00  │ Brevo (150)
 3:00 -  4:30  │ Gmail (100) + Elastic (100)
 4:30 -  6:00  │ Resend (100) + SMTP2GO (33) + remaining
```

### Warm-Up Ramp (Critical)

Don't start at 1,000/day. Ramp up over 2 weeks:

| Week | Day | Volume | Providers Active |
|------|-----|--------|-----------------|
| 1 | Mon | 50 | Gmail only |
| 1 | Tue | 75 | Gmail only |
| 1 | Wed | 100 | Gmail only |
| 1 | Thu | 150 | Gmail + Brevo |
| 1 | Fri | 200 | Gmail + Brevo |
| 2 | Mon | 300 | Gmail + Brevo + Mailjet |
| 2 | Tue | 500 | +SendGrid, Elastic |
| 2 | Wed | 700 | +Resend |
| 2 | Thu | 900 | +SMTP2GO |
| 2 | Fri | 1,000 | All providers |

This protects sender reputation on every provider.

### Prioritization Order

Send to highest-value prospects first:

1. **Electrical, Plumbing, Mechanical, HVAC** — highest-ticket services, most need websites
2. **Roofing, Building, Foundation** — competitive markets, website = huge advantage
3. **Swimming Pool, Fence, Landscape** — visual businesses, portfolio sites sell
4. **Tree Service, Lawn Sprinkler, Paving** — smaller ops, still need presence
5. **Backflow, Fire Alarm, Medical Gas** — niche/B2B, lower priority

---

## Admin GUI — New "Mass Outreach" Section

### Location: `admin/index.html` → new tab in sidebar

### Components

#### 1. Import Panel
- Drag & drop Excel file
- Preview parsed data (table with first 10 rows)
- Column mapping confirmation
- "Import X prospects" button
- Progress bar during import
- Dedup report ("merged 234 duplicates")

#### 2. SMTP Provider Manager
- Card per provider: name, host, daily limit, today's sent, status indicator
- Add/edit provider modal (host, port, username, password, daily limit)
- Enable/disable toggle per provider
- Test connection button (sends test email to yourself)
- Daily reset countdown timer
- Visual quota bar (sent / limit) per provider

#### 3. Sending Dashboard
- **Today's Stats:** Sent / Queued / Failed / Opened / Replied
- **Provider Breakdown:** Pie chart of sends per provider
- **Queue Preview:** Next 20 emails to be sent (prospect, subject, scheduled time, provider)
- **Send Controls:**
  - Start / Pause sending
  - Speed slider (emails per hour)
  - "Send Now" button for manual batch
- **Timeline:** Hourly send volume bar chart for today

#### 4. Prospect Pipeline (filtered view)
- Table: Name | Email | Type | Status | Score | Actions
- Filters: registration type, status, email verified, has website
- Bulk actions: Send to queue, Skip, Mark dead
- Click row → expand: full prospect details, email history, audit link

#### 5. Template Editor
- Select template → edit subject + body with live preview
- Variable autocomplete ({{owner_first}}, {{business_name}}, etc.)
- Preview with random prospect data
- A/B test support: create variant, set split percentage

#### 6. Health & Reputation Monitor
- Bounce rate per provider (flag if >5%)
- Open rate per provider
- Spam complaints (if detectable)
- Email verification queue status
- Alerts: "Gmail hit daily limit at 2:15pm", "Brevo bounce rate spiking"

---

## Implementation Tasks

### Phase 1 — Provider Pool (Backend) ◻️

- [ ] Add `smtp_providers` table + SQLAlchemy model
- [ ] Create `SmtpPool` service class:
  - `pick_provider()` — selects lowest-usage enabled provider under limit
  - `send_via(provider_id, to, subject, html, text)` — send through specific provider
  - `reset_daily_counts()` — cron job at midnight
  - `test_connection(provider_id)` — verify SMTP creds
- [ ] Modify existing `email_service.py` to use `SmtpPool` instead of hardcoded Gmail
- [ ] Add provider CRUD API endpoints
- [ ] Migration script for new table + column

### Phase 2 — Excel Import (Backend) ◻️

- [ ] `POST /api/v1/outreach/import` endpoint
  - Accepts multipart file upload (`.xlsx`)
  - Parse, normalize, deduplicate
  - Return import report JSON
- [ ] Email verification service (`verify_email.py`)
  - MX lookup + SMTP probe (batch, rate-limited)
  - Background task after import
- [ ] Contractor name parser (LAST, FIRST → First Last)
- [ ] City-State-Zip splitter
- [ ] Registration type → industry tag mapper

### Phase 3 — Admin GUI ◻️

- [ ] Add "Mass Outreach" tab to admin sidebar
- [ ] Import wizard component (drag-drop, preview, confirm)
- [ ] SMTP provider manager cards
- [ ] Sending dashboard with real-time stats
- [ ] Prospect table with filters and bulk actions
- [ ] Template editor with variable preview
- [ ] Wire up all API calls (fetch + Firebase hybrid)

### Phase 4 — Sending Engine ◻️

- [ ] Warm-up scheduler (auto-ramp daily volume over 2 weeks)
- [ ] Business-hours enforcement (8am-6pm CT, skip weekends)
- [ ] Per-provider rate limiter (spread sends across the day)
- [ ] Stagger sends with 3-5 min random jitter
- [ ] Auto-pause on high bounce rate (>5% in any hour)
- [ ] Provider fallback (if one fails, redistribute to others)

### Phase 5 — Templates & Sequences ◻️

- [ ] Create 3-touch drip templates per contractor category
- [ ] A/B subject line testing framework
- [ ] Dynamic portfolio link injection (match prospect industry)
- [ ] Auto-attach free audit report for email 3

---

## Compliance & Safety

### CAN-SPAM Requirements (mandatory)
- ✅ Physical mailing address in every email footer
- ✅ Clear "Unsubscribe" link (one-click, already implemented in email_tracker)
- ✅ Process unsubscribes within 10 business days (we do it instantly)
- ✅ No misleading subject lines
- ✅ Identify as advertisement (first email)

### Reputation Protection
- **Dedicated sending domain** — don't use your main domain. Use e.g. `mail.ajayadesign.com`
- **SPF record** — include all 7 providers' SPF domains
- **DKIM** — sign with your domain key (each provider has setup instructions)
- **DMARC** — `v=DMARC1; p=none; rua=mailto:dmarc@ajayadesign.com`
- **List-Unsubscribe header** — one-click RFC 8058 compliant
- **Bounce handling** — auto-disable after 2 hard bounces to same address
- **Daily limit safety** — never exceed 80% of any provider's stated limit

### Data Handling
- Prospect data stays in local PostgreSQL (never third-party)
- SMTP passwords encrypted at rest in database
- Import files deleted after processing
- Audit trail: every email send logged with provider, timestamp, status

---

## Timeline

| Phase | Scope | Effort |
|-------|-------|--------|
| Phase 1 | Provider Pool backend | Small |
| Phase 2 | Excel Import backend | Small |
| Phase 3 | Admin GUI | Medium |
| Phase 4 | Sending Engine | Small (mostly wiring existing code) |
| Phase 5 | Templates | Small |
| **Signup** | Register 6 free SMTP accounts | 30 min manual |
| **DNS** | Add SPF/DKIM/DMARC records | 20 min manual |
| **Warm-up** | 2-week ramp before full volume | Automated |

---

## Quick Start (After Implementation)

```bash
# 1. Start the stack
docker compose -f automation/docker-compose.api.yml up -d

# 2. Add SMTP providers via admin GUI (or API)
curl -X POST localhost:3001/api/v1/outreach/providers \
  -H 'Content-Type: application/json' \
  -d '{"name":"gmail","host":"smtp.gmail.com","port":587,...}'

# 3. Import contractors
# → Admin GUI → Mass Outreach → Import → drag Registered_Contractors.xlsx

# 4. Verify emails (auto-runs after import)
# → Watch progress in admin GUI

# 5. Start sending
# → Admin GUI → Mass Outreach → Start Sending
# → Warm-up mode auto-engages for first 2 weeks
```
