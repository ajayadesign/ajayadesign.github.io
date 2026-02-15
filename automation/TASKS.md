# AjayaDesign — Enhancement Tasks

> **Created:** 2026-02-14  
> **Status:** Active  

---

## Table of Contents

- [Task 1: Enhanced Client Intake Form](#task-1-enhanced-client-intake-form)
- [Task 2: GitHub API Rate Limit Handling](#task-2-github-api-rate-limit-handling)
- [Task 3: Firebase ↔ Internal DB Bridge](#task-3-firebase--internal-db-bridge)
- [Task 4: Offline Resilience — Firebase Polling on Startup](#task-4-offline-resilience--firebase-polling-on-startup)
- [Task 5: Admin "Add Client" — Manual Form + AI Paste-to-Parse](#task-5-admin-add-client--manual-form--ai-paste-to-parse)

---

## Task 1: Enhanced Client Intake Form

### Problem

The current form in `index.html` only collects 4 fields: business name, niche, goals, email. That's the bare minimum. The AI agents would produce significantly better sites with more context — existing branding, photos, competitor examples, etc.

### Current Form Fields

| Field | Required | Type |
|-------|----------|------|
| Business Name | ✅ | text |
| Niche/Industry | ✅ | text |
| Goals | ✅ | textarea |
| Email | ✅ | email |

### New Fields to Add

#### Required Fields (mandatory — form won't submit without them)

| Field | Type | Why | Validation |
|-------|------|-----|------------|
| **Phone Number** | `tel` | Professional contact, SMS updates | Min 10 digits, `pattern="[0-9+\-() ]+"` |
| **Business Location** | `text` | SEO local keywords, timezone | Min 3 chars (city/state minimum) |

#### Optional Fields (help AI get closer to the real business)

| Field | Type | Why | Default / Placeholder |
|-------|------|-----|----------------------|
| **Existing Website URL** | `url` | AI can analyze current site, preserve branding/content | `"https://your-current-site.com"` |
| **Logo Upload** | `file` (image) | Use real logo instead of AI placeholder | Accept: `.png, .jpg, .svg, .webp` — max 5MB |
| **Product/Service Photos** | `file` (multiple) | Real imagery in hero, gallery, etc. | Accept: `.png, .jpg, .webp` — max 10MB total |
| **Brand Colors** | `text` | Preserve existing brand identity | `"e.g. Navy blue #1a365d, Gold #d4a843"` |
| **Tagline / Slogan** | `text` | Headline copy the business already uses | `"e.g. Fresh Baked Daily Since 1985"` |
| **Target Audience** | `textarea` | Sharper copy targeting | `"e.g. Young professionals aged 25-40 in Austin, TX"` |
| **Competitor URLs** | `textarea` | AI studies competitors for differentiation | `"One URL per line"` |
| **Anything Else** | `textarea` | Free-form context dump | `"Special hours, certifications, awards, etc."` |

#### The Rebuild Checkbox — With Safety

| Field | Type | Behavior |
|-------|------|----------|
| **Rebuild Existing Site** | `checkbox` | Unchecked by default. When checked, shows a **confirmation warning + text input** |

**Accidental-check protection** (3 layers):

1. **Checkbox unchecked by default** — must be intentional
2. **Reveal panel** — Checking it slides open a yellow warning box:
   > ⚠️ This will **replace** your existing site with a fresh build. Your current site will be backed up as a git branch before rebuild.
3. **Confirmation text field** — User must type the business name to confirm:
   > Type **"Sunrise Bakery"** to confirm rebuild
   
   Form won't submit unless the typed text matches the business name field (case-insensitive)

**Backend behavior for rebuild:**
- Phase 1 (repo) detects repo exists AND `rebuild: true` in payload
- Creates a git branch `backup/{date}` from current `main` before any changes
- Logs the backup branch URL in the build record
- Proceeds with full rebuild on `main`

### Data Schema Change

```js
// Current payload
{ business_name, niche, goals, email }

// New payload
{
  business_name,          // required
  niche,                  // required
  goals,                  // required
  email,                  // required
  phone,                  // required (new)
  location,               // required (new)
  existing_website: "",   // optional
  brand_colors: "",       // optional
  tagline: "",            // optional
  target_audience: "",    // optional
  competitor_urls: [],    // optional
  additional_notes: "",   // optional
  rebuild: false,         // default false
  // Files handled separately via FormData
  logo: File | null,      // optional
  photos: File[] | [],    // optional
}
```

### Files to Modify

| File | Change |
|------|--------|
| `index.html` | Add new form fields, rebuild checkbox with confirmation panel, file upload styling |
| `js/main.js` | Update `handleSubmit()` — collect new fields, file upload to Firebase Storage, triple-send updated payload |
| `admin/js/admin.js` | Display new fields in lead detail view (existing website link, location, photos, etc.) |
| `automation/api/schemas/__init__.py` | Add new fields to `BuildRequest` Pydantic model |
| `automation/api/models/build.py` | Add columns: `phone`, `location`, `existing_website`, `brand_colors`, etc. |
| `automation/api/pipeline/prompts.py` | Feed new context (existing site, brand colors, audience) into Strategist + Page Builder prompts |
| `automation/api/pipeline/phases/p01_repo.py` | Handle `rebuild=true` → backup branch before overwrite |
| `automation/api/pipeline/phases/p02_council.py` | Pass competitor URLs, existing site, audience to Strategist |

### Implementation Order

1. **HTML form** — Add fields with proper validation + rebuild safety UI
2. **js/main.js** — File uploads → Firebase Storage, expanded payload
3. **Backend schemas + models** — Accept and store new fields
4. **Pipeline prompts** — Feed context to AI agents
5. **Rebuild flow** — Backup branch logic in p01_repo
6. **Admin display** — Show new fields in lead detail
7. **Tests** — Rebuild safety, file upload validation, schema validation

---

## Task 2: GitHub API Rate Limit Handling

### Problem

The AI API retry (`429 → parse wait time → retry`) is solid. But **GitHub API rate limits have zero handling**:

- `gh repo create` — 5,000 requests/hour (authenticated)
- `gh repo view` — same pool
- `gh api` (Pages enable) — same pool
- `git push` — no explicit rate limit but can fail transiently

When `gh` gets rate-limited, the build just **crashes** with an unhelpful error. We need graceful retry with delay.

### Current State

| Component | AI API Rate Limits | GitHub API Rate Limits |
|-----------|-------------------|----------------------|
| Node.js `ai.js` | ✅ Parse `wait X seconds`, retry with backoff | — |
| Node.js `shell.js` | — | ❌ No retry at all |
| Python `ai.py` | ✅ Same logic ported | — |
| Python `git.py` | — | ❌ No retry at all |

### Solution

Add rate-limit-aware retry to `git.py`'s `run_cmd` and `try_cmd`:

```python
# In git.py — enhanced run_cmd

async def run_cmd(cmd, cwd=None, timeout=300, retries=3, env_extra=None):
    """Run shell command with retry on rate limits and transient failures."""
    for attempt in range(1, retries + 1):
        try:
            # ... existing subprocess logic ...
            return out
        except RuntimeError as e:
            msg = str(e)
            
            # GitHub rate limit detection
            is_rate_limited = any(phrase in msg.lower() for phrase in [
                "rate limit", "api rate limit exceeded",
                "403", "secondary rate limit",
                "abuse detection",
            ])
            
            # Transient git errors worth retrying
            is_transient = any(phrase in msg.lower() for phrase in [
                "could not resolve host",
                "connection timed out",
                "the remote end hung up",
                "ssl_error",
                "early eof",
            ])
            
            if (is_rate_limited or is_transient) and attempt < retries:
                if is_rate_limited:
                    # Check X-RateLimit-Reset header via gh api
                    wait = await _get_github_rate_limit_wait()
                    wait = max(wait, 60)  # minimum 60s for rate limits
                else:
                    wait = attempt * 10  # 10s, 20s, 30s for transient
                
                logger.warning(f"Retry {attempt}/{retries} in {wait}s: {msg[:200]}")
                await asyncio.sleep(wait)
                continue
            
            raise  # exhausted retries or non-retryable error


async def _get_github_rate_limit_wait() -> int:
    """Query GitHub API for rate limit reset time."""
    try:
        proc = await asyncio.create_subprocess_shell(
            'gh api rate_limit --jq ".rate.reset"',
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), 10)
        reset_epoch = int(stdout.decode().strip())
        wait = max(0, reset_epoch - int(time.time())) + 5  # 5s buffer
        return min(wait, 3600)  # cap at 1 hour
    except Exception:
        return 120  # default 2 min wait
```

### Also Back-Port to Node.js

Update `orchestrator/lib/shell.js` with the same retry logic for `gh` commands. The JS side is still used until the full Python migration completes.

### Files to Modify

| File | Change |
|------|--------|
| `automation/api/services/git.py` | Add retry loop to `run_cmd` with GH rate limit detection + `_get_github_rate_limit_wait()` |
| `automation/orchestrator/lib/shell.js` | Add retry for `gh` commands (mirror Python logic) |
| `automation/tests/test_services.py` | Add tests: rate limit retry, transient failure retry, non-retryable failure |

---

## Task 3: Firebase ↔ Internal DB Bridge

### Problem

There's a **data silo**:

```
Client form  →  Firebase RTDB (leads/{id})
Admin clicks →  POST /build → Python API → PostgreSQL (builds table)
```

The build system has **zero awareness** of Firebase. Leads live in Firebase, builds live in PostgreSQL, and the only bridge is the admin manually clicking "Trigger Build." If the admin is asleep, or n8n is down, or the server reboots — leads sit in Firebase with `status: "new"` forever.

### Current Flow

```
Client submits form
    ├──→ Firebase RTDB: leads/{timestamp_random} (status: "new")
    ├──→ FormSubmit.co: email notification
    └──→ n8n webhook: localhost:5678 (FAILS from production — localhost!)

Admin opens dashboard
    └──→ Reads leads from Firebase
    └──→ Clicks "Trigger Build"
         └──→ POST /build to runner API
              └──→ Build stored in JSON file / PostgreSQL
              └──→ Firebase lead.status updated to "building" (by admin.js)
```

### Target Flow

```
Client submits form
    ├──→ Firebase RTDB: leads/{id} (status: "new")
    ├──→ FormSubmit.co: email notification
    └──→ [n8n webhook — still fires but not critical]

FastAPI startup / periodic poll (every 60s)
    └──→ Read Firebase RTDB leads where status = "new"
    └──→ For each: check if build exists in PostgreSQL
    └──→ If not → create build row, push to queue
    └──→ Update Firebase lead status to "queued" / "building" / "deployed"

Build completes
    └──→ PostgreSQL build.status = "complete"
    └──→ Firebase leads/{id}/status = "deployed"  (synced back!)
    └──→ Firebase leads/{id}/live_url = "https://..."
```

### Implementation

#### 3a. Add Firebase Admin SDK to Python API

```python
# api/services/firebase.py
import firebase_admin
from firebase_admin import credentials, db as firebase_db

def init_firebase():
    """Initialize Firebase Admin SDK (uses service account key or ADC)."""
    if not firebase_admin._apps:
        # In Docker: mount service-account-key.json
        cred = credentials.Certificate("/app/firebase-service-account.json")
        firebase_admin.initialize_app(cred, {
            "databaseURL": "https://ajayadesign-6d739-default-rtdb.firebaseio.com"
        })

def get_new_leads() -> list[dict]:
    """Fetch all leads with status='new' from Firebase RTDB."""
    ref = firebase_db.reference("leads")
    snapshot = ref.order_by_child("status").equal_to("new").get()
    if not snapshot:
        return []
    return [{"firebase_id": k, **v} for k, v in snapshot.items()]

def update_lead_status(firebase_id: str, status: str, extra: dict = None):
    """Update a lead's status in Firebase RTDB."""
    ref = firebase_db.reference(f"leads/{firebase_id}")
    update = {"status": status}
    if extra:
        update.update(extra)
    ref.update(update)
```

#### 3b. Sync on Form Submit (Real-Time)

The form already writes to Firebase. The Python API can **also** receive the submission directly (dual-write for reliability):

```js
// In main.js handleSubmit() — add 4th channel:
// 4. Direct to Python API (if reachable)
fetch(`${AUTOMATION_API}/api/v1/builds`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ business_name, niche, goals, email, firebase_id: leadId }),
}).catch(() => {}); // Silently fail — Firebase is the source of truth
```

### Files to Create/Modify

| File | Change |
|------|--------|
| `automation/api/services/firebase.py` | **NEW** — Firebase Admin SDK wrapper |
| `automation/api/main.py` | Init Firebase on startup, start periodic poller |
| `automation/api/models/build.py` | Add `firebase_id` column to link builds ↔ leads |
| `automation/Dockerfile` | Install `firebase-admin` pip package |
| `automation/requirements.txt` | Add `firebase-admin` |
| `automation/docker-compose.yml` | Mount service account key |
| `js/main.js` | Add 4th submission channel (direct to Python API) |

---

## Task 4: Offline Resilience — Firebase Polling on Startup

### Problem

If the Docker stack is down (server reboot, deploy, crash), leads accumulate in Firebase with `status: "new"`. When the system comes back:
- n8n missed the webhooks
- The Python API has no record of these leads
- Builds never start

### Solution: Startup Reconciliation + Periodic Polling

```
FastAPI Startup
    │
    ▼
[1] Init Firebase Admin SDK
    │
    ▼
[2] Fetch ALL leads from Firebase RTDB
    │
    ▼
[3] For each lead:
    │   ├── Has firebase_id in PostgreSQL builds table?
    │   │       YES → already processed, skip
    │   │       (but sync status back if mismatched)
    │   │
    │   └── NO → This lead was missed!
    │           ├── Create build row in PostgreSQL (status: "queued")
    │           ├── Update Firebase: status = "queued"
    │           └── Push to build queue
    │
    ▼
[4] Start periodic poller (every 60s)
    │   └── Same logic as step 2-3, but only fetches status="new"
    │
    ▼
[5] Process build queue
        └── FIFO — one build at a time (or configurable concurrency)
        └── Each build: full 8-phase pipeline
        └── On complete: update Firebase status to "deployed" + live_url
        └── On failure: update Firebase status to "failed" + error
```

### Build Queue Design

```python
# api/services/queue.py
import asyncio
from collections import deque

class BuildQueue:
    """Simple async FIFO queue for builds. One build at a time."""
    
    def __init__(self, max_concurrent: int = 1):
        self._queue: deque = deque()
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._running = False
        self._worker_task: asyncio.Task | None = None
    
    async def enqueue(self, build_id: str, db_session_factory):
        """Add a build to the queue."""
        self._queue.append(build_id)
        logger.info(f"Build {build_id} queued (position {len(self._queue)})")
        if not self._running:
            self._worker_task = asyncio.create_task(self._worker(db_session_factory))
    
    async def _worker(self, db_session_factory):
        """Process builds one at a time."""
        self._running = True
        while self._queue:
            build_id = self._queue.popleft()
            async with self._semaphore:
                try:
                    await self._run_build(build_id, db_session_factory)
                except Exception as e:
                    logger.error(f"Build {build_id} failed: {e}")
        self._running = False
    
    @property
    def pending(self) -> int:
        return len(self._queue)
```

### Startup Hook

```python
# In api/main.py

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──
    await init_db()
    init_firebase()
    
    # Reconcile Firebase ↔ PostgreSQL
    missed = await reconcile_firebase_leads()
    if missed:
        logger.info(f"🔄 Found {len(missed)} unprocessed leads — queueing builds")
        for lead in missed:
            await build_queue.enqueue(lead["build_id"], get_session)
    
    # Start periodic poller
    poller_task = asyncio.create_task(periodic_firebase_poll(interval=60))
    
    yield
    
    # ── Shutdown ──
    poller_task.cancel()


async def reconcile_firebase_leads():
    """Compare Firebase leads with PostgreSQL builds. Queue any missing."""
    firebase_leads = get_all_leads()  # from Firebase
    missed = []
    
    async with get_session() as db:
        for lead in firebase_leads:
            # Check if we already have a build for this Firebase lead
            existing = await db.execute(
                select(Build).where(Build.firebase_id == lead["firebase_id"])
            )
            if existing.scalar_one_or_none():
                # Already tracked — sync status if needed
                continue
            
            if lead["status"] in ("new", "contacted"):
                # Unprocessed lead — create build and queue it
                build = Build(
                    firebase_id=lead["firebase_id"],
                    client_name=lead["business_name"],
                    niche=lead["niche"],
                    goals=lead["goals"],
                    email=lead.get("email", ""),
                    status="queued",
                )
                db.add(build)
                await db.commit()
                await db.refresh(build)
                
                update_lead_status(lead["firebase_id"], "queued")
                missed.append({"build_id": str(build.id), **lead})
    
    return missed
```

### Edge Cases to Handle

| Scenario | Handling |
|----------|---------|
| **Lead in Firebase but build already complete in DB** | Skip — already done. Sync Firebase status to "deployed" if mismatched. |
| **Lead in Firebase, build in DB but failed** | Don't auto-retry (failures need human review). Log it. |
| **Lead in Firebase with status "building"** but no running build | Stale state from a crash. Re-queue it. |
| **Duplicate leads** (same client submits twice) | Deduplicate by `business_name + email` within 5-minute window. |
| **Firebase unreachable at startup** | Log warning, continue without sync. Retry on next poll cycle. |
| **PostgreSQL unreachable** | Fatal — FastAPI won't start. Docker health check will restart. |

### Files to Create/Modify

| File | Change |
|------|--------|
| `automation/api/services/firebase.py` | **NEW** — Firebase Admin SDK: `get_new_leads()`, `get_all_leads()`, `update_lead_status()` |
| `automation/api/services/queue.py` | **NEW** — `BuildQueue` async FIFO with semaphore-based concurrency |
| `automation/api/main.py` | Add lifespan: init Firebase, reconcile, start poller |
| `automation/api/models/build.py` | Add `firebase_id` column (nullable, for linking) |
| `automation/api/routes/__init__.py` | Expose queue status: `GET /api/v1/queue` (pending count, current build) |
| `automation/tests/test_firebase.py` | **NEW** — Mock Firebase SDK, test reconciliation logic |
| `automation/tests/test_queue.py` | **NEW** — Test queue ordering, concurrency limit, error handling |

---

## Task 5: Admin "Add Client" — Manual Form + AI Paste-to-Parse

### Problem

Not every client will fill out the website form themselves. Sometimes AJ talks to a client on the phone, over email, or gets a referral with details in a text message. Right now the only way to create a lead is through the public form on `index.html`. The admin should be able to:

1. **Manually fill a form** in the admin dashboard (for structured input)
2. **Paste raw text** (email, text message, notes) and let AI extract the fields automatically

Both paths end with the same result: a lead in Firebase RTDB + a build ready to trigger.

### Feature A: Manual "Add Client" Form in Admin

A modal/panel in the admin dashboard with the same fields as the public form (plus the new fields from Task 1), pre-filled with defaults where possible.

#### UI Design

```
┌─────────────────────────────────────────────────────┐
│  ➕ Add New Client                           [✕]   │
│─────────────────────────────────────────────────────│
│                                                     │
│  [Tab: Manual Form]  [Tab: AI Paste & Parse]        │
│                                                     │
│  ── Manual Form ──────────────────────────────────  │
│                                                     │
│  Business Name *    [________________________]      │
│  Niche/Industry *   [________________________]      │
│  Goals *            [________________________]      │
│                     [________________________]      │
│  Email *            [________________________]      │
│  Phone              [________________________]      │
│  Location           [________________________]      │
│  Existing Website   [________________________]      │
│  Brand Colors       [________________________]      │
│  Tagline            [________________________]      │
│  Target Audience    [________________________]      │
│  Competitor URLs    [________________________]      │
│  Notes              [________________________]      │
│                                                     │
│  ☐ Rebuild existing site                            │
│                                                     │
│  [Cancel]                    [Save Lead & Build ▶]  │
│                              [Save Lead Only]       │
└─────────────────────────────────────────────────────┘
```

- **"Save Lead & Build ▶"** — Creates the lead in Firebase AND immediately triggers the build pipeline
- **"Save Lead Only"** — Creates the lead in Firebase with `status: "new"` for later manual trigger
- All the same validations as the public form (required fields, email format, etc.)
- Source field set to `"admin"` instead of `"ajayadesign.github.io"` so we can tell it apart

### Feature B: AI Paste & Parse

This is the time-saver. Paste any unstructured text — an email thread, a text message, meeting notes, a LinkedIn message — and AI extracts the structured fields.

#### UI Design

```
┌─────────────────────────────────────────────────────┐
│  ➕ Add New Client                           [✕]   │
│─────────────────────────────────────────────────────│
│                                                     │
│  [Tab: Manual Form]  [Tab: AI Paste & Parse]        │
│                                                     │
│  ── AI Paste & Parse ─────────────────────────────  │
│                                                     │
│  Paste client details below — email, text message,  │
│  notes, anything. AI will extract the fields.       │
│                                                     │
│  ┌───────────────────────────────────────────────┐  │
│  │ Hey Aj, I run a bakery called Sunrise Bakery  │  │
│  │ in Portland OR. We need a website to showcase │  │
│  │ our artisan breads and drive catering orders.  │  │
│  │ Our current site is sunrisebakerypdx.com but  │  │
│  │ it's outdated. We use navy blue and gold for  │  │
│  │ our brand. Email me at hello@sunrise.com or   │  │
│  │ call 503-555-1234.                            │  │
│  └───────────────────────────────────────────────┘  │
│                                                     │
│                          [🤖 Parse with AI]         │
│                                                     │
│  ── Extracted Fields (editable) ─────────────────   │
│                                                     │
│  Business Name *    [Sunrise Bakery_____________]   │
│  Niche/Industry *   [Artisan Bakery & Catering__]   │
│  Goals *            [Showcase breads, drive ...]     │
│  Email *            [hello@sunrise.com__________]   │
│  Phone              [503-555-1234_______________]   │
│  Location           [Portland, OR_______________]   │
│  Existing Website   [sunrisebakerypdx.com_______]   │
│  Brand Colors       [Navy blue, Gold____________]   │
│  ✅ Parsed successfully — review and edit if needed │
│                                                     │
│  [Cancel]                    [Save Lead & Build ▶]  │
│                              [Save Lead Only]       │
└─────────────────────────────────────────────────────┘
```

#### How the AI Parse Works

1. Admin pastes raw text into the textarea
2. Clicks "🤖 Parse with AI"
3. Frontend sends `POST /api/v1/parse-client` with `{ raw_text: "..." }`
4. Backend calls the AI with a structured extraction prompt:

```python
# In api/services/ai.py or a new api/routes/parse.py

PARSE_CLIENT_PROMPT = """Extract client information from this text. Return ONLY valid JSON:
{
  "business_name": "extracted or null",
  "niche": "extracted or null",
  "goals": "extracted or null",
  "email": "extracted or null",
  "phone": "extracted or null",
  "location": "extracted or null",
  "existing_website": "extracted or null",
  "brand_colors": "extracted or null",
  "tagline": "extracted or null",
  "target_audience": "extracted or null",
  "competitor_urls": ["url1", "url2"] or [],
  "additional_notes": "anything else relevant that didn't fit above"
}

Rules:
- Extract what's explicitly stated. Don't invent.
- For goals: synthesize into a clear 1-2 sentence summary
- For niche: infer from context (e.g. "bakery" from "artisan breads")
- If a field can't be extracted, use null
- For phone: normalize to digits + formatting
- For website: add https:// if missing
- For brand_colors: extract color names or hex codes mentioned
"""
```

5. Backend returns the parsed JSON
6. Frontend populates the form fields (all editable — AI can be wrong)
7. Admin reviews, corrects, and submits

**Key point: AI fills, human confirms.** The parsed fields are always editable. Required fields that AI couldn't extract are highlighted in red so the admin knows what to fill in.

### New API Endpoint

```
POST /api/v1/parse-client
  Body: { "raw_text": "Hey Aj, I run a bakery called..." }
  Response: { "parsed": { "business_name": "Sunrise Bakery", ... }, "confidence": "high" }
```

This is a single AI call — fast (~2s), cheap (small prompt), and the infrastructure (`call_ai` + `extract_json`) already exists.

### Admin-Created Leads vs Public Leads

| Field | Public Form | Admin Manual | Admin AI Parse |
|-------|------------|--------------|----------------|
| `source` | `"ajayadesign.github.io"` | `"admin-manual"` | `"admin-ai-parse"` |
| `created_by` | — | `"aj@admin"` | `"aj@admin"` |
| `raw_text` | — | — | Stored for audit trail |
| Saved to Firebase | ✅ | ✅ | ✅ |
| Saved to PostgreSQL | Via bridge (Task 3) | Via bridge (Task 3) | Via bridge (Task 3) |

### Files to Create/Modify

| File | Change |
|------|--------|
| `admin/index.html` | Add "➕ Add Client" button in header + modal HTML (two tabs) |
| `admin/js/admin.js` | `openAddClientModal()`, `switchAddClientTab()`, `parseWithAI()`, `saveNewLead()`, form validation |
| `admin/css/` or inline | Modal styling, tab switching, parsed-field highlighting |
| `automation/api/routes/__init__.py` | Add `POST /api/v1/parse-client` endpoint |
| `automation/api/pipeline/prompts.py` | Add `PARSE_CLIENT_PROMPT` template |
| `automation/api/schemas/__init__.py` | Add `ParseClientRequest`, `ParseClientResponse` schemas |
| `automation/tests/test_routes.py` | Test parse endpoint with sample texts |
| `automation/tests/test_services.py` | Test AI parse prompt returns valid structured JSON |

### Implementation Order

1. **Backend** — `POST /api/v1/parse-client` endpoint + prompt (~1 hour)
2. **Admin HTML** — Modal with two tabs, form fields (~2 hours)
3. **Admin JS** — Tab switching, AI parse call, form population, save logic (~2 hours)
4. **Firebase write** — Admin-created leads write to Firebase RTDB same as public form (~30 min)
5. **Tests** — Parse endpoint, edge cases (empty text, non-English, multiple clients mentioned) (~1 hour)

**Estimated effort: ~6 hours**

---

## Priority & Dependencies

```
Task 2 (Rate Limits)          ← Independent, smallest scope, do first
    │
    ▼
Task 3 (Firebase Bridge)      ← Needs firebase-admin SDK + service account
    │
    ▼
Task 4 (Offline Resilience)   ← Builds on Task 3 (needs Firebase service)
    │
    ▼
Task 1 (Enhanced Form)        ← Biggest scope, can be parallelized with Task 2
│                                But backend changes (Task 3) should land first
│                                so new fields flow through Firebase → DB
▼
Task 5 (Admin Add Client)     ← Shares fields with Task 1, needs parse endpoint
                                 Can start the backend parse route independently
```

### Recommended Order

| Order | Task | Effort | Why This Order |
|-------|------|--------|----------------|
| **1st** | Task 2: Rate Limits | ~2 hours | Quick win, prevents build crashes |
| **2nd** | Task 3: Firebase Bridge | ~4 hours | Unlocks Task 4, needs service account setup |
| **3rd** | Task 4: Offline Resilience | ~4 hours | Depends on Task 3 |
| **4th** | Task 1: Enhanced Form | ~6 hours | Largest scope, touches frontend + backend + prompts |
| **5th** | Task 5: Admin Add Client | ~6 hours | Reuses Task 1 fields, needs parse endpoint |

**Total estimated effort: ~22 hours**

---

*Last updated: 2026-02-14*
