# AjayaDesign Automation — Migration Plan
## Node.js → FastAPI + PostgreSQL

> **Author:** Copilot + AJ  
> **Date:** 2026-02-14  
> **Status:** PLANNING  

---

## Table of Contents

1. [Honest Assessment — Should We Do This?](#1-honest-assessment)
2. [What We Have Today](#2-what-we-have-today)
3. [What We'd Gain](#3-what-wed-gain)
4. [Target Architecture](#4-target-architecture)
5. [Database Schema](#5-database-schema)
6. [RAG & Future AI Architecture](#6-rag--future-ai-architecture)
7. [API Design](#7-api-design)
8. [Migration Phases](#8-migration-phases)
9. [What Stays JavaScript (And That's OK)](#9-what-stays-javascript)
10. [Docker & Infrastructure](#10-docker--infrastructure)
11. [Risk Assessment](#11-risk-assessment)
12. [Estimated Timeline](#12-estimated-timeline)
13. [Decision: Go / No-Go Criteria](#13-decision)

---

## ⚠️ Scope Boundary — What This Migration IS and ISN'T

This is critical to understand before reading anything else:

```
ajayadesign.github.io/          ← GitHub Pages (STATIC — never changes)
│
├── index.html                   🚫 NOT migrating — static HTML/CSS/JS
├── js/                          🚫 NOT migrating — client-side JS
├── css/                         🚫 NOT migrating — stylesheets
├── admin/                       🚫 NOT migrating — admin dashboard (static HTML/JS)
│   ├── index.html                   hosted on GitHub Pages, talks to API via fetch()
│   └── js/
│       ├── admin.js                 Firebase Auth + leads management
│       └── pipeline.js              SSE client for build streaming
│
├── automation/                  ✅ THIS IS WHAT WE'RE MIGRATING
│   ├── runner/server.js             Node.js HTTP server → FastAPI
│   ├── orchestrator/                8-phase pipeline → Python pipeline
│   └── docker-compose.yml           Add PostgreSQL, swap Node for Python
│
└── [client-sites]/              🚫 NOT migrating — AI-generated static sites
    └── *.html                       Always HTML/CSS/JS, deployed to GitHub Pages
```

### The Three Layers

| Layer | Technology | Hosted On | Migrating? |
|-------|-----------|-----------|------------|
| **1. Main Website** (`/`, `/js/`, `/css/`) | Static HTML/CSS/JS | GitHub Pages | ❌ No — always static |
| **2. Admin Dashboard** (`/admin/`) | Static HTML/JS + Firebase | GitHub Pages | ❌ No — stays static, just calls the API |
| **3. Automation Backend** (`/automation/`) | Node.js → **FastAPI + PostgreSQL** | Docker on drone server | ✅ **YES — this is the migration** |
| **4. Generated Client Sites** | Static HTML/CSS/JS + Tailwind | GitHub Pages (per-repo) | ❌ No — the OUTPUT is always static |

### Why This Works

The admin dashboard at `admin/index.html` is just a **static frontend** hosted on GitHub Pages. It talks to the automation backend via `fetch()` and `EventSource` (SSE). Right now it points to `http://drone:3456/build`. After migration, it points to `http://drone:8000/api/v1/builds`. That's the **only change** to the admin — one URL swap.

The AI pipeline's **output** (client websites) is always static HTML/CSS/JS deployed to GitHub Pages. Python generates the same HTML files that Node.js generates today. The hosting doesn't change.

In short: **GitHub Pages serves the frontend. Docker on drone runs the backend. We're only rewriting the backend.**

---

## 1. Honest Assessment

### The Current System Works

Let's be real — the current Node.js pipeline is **functional and deployed**. ~1,500 lines of JS across 14 files, running in Docker, building real client sites. Before committing to a rewrite, here's the honest trade-off:

| Factor | Keep Node.js | Migrate to Python/FastAPI |
|--------|-------------|--------------------------|
| **Time to value** | ✅ Zero — it works now | ❌ 2-4 weeks of rework |
| **AI/ML ecosystem** | ❌ Limited (no native langchain, vector DBs are clunky) | ✅ Best-in-class (langchain, llamaindex, pgvector, transformers) |
| **RAG / embeddings** | ❌ Would need Python sidecar anyway | ✅ Native, first-class support |
| **Async HTTP** | ⚠️ Works but raw `http` module is fragile | ✅ FastAPI is async-native with automatic OpenAPI docs |
| **Database** | ❌ JSON files on disk (not queryable, no analytics) | ✅ PostgreSQL = queryable history, analytics, vector search |
| **Type safety** | ❌ No TypeScript (raw JS) | ✅ Pydantic models, full validation |
| **Observability** | ❌ Console.log + JSON files | ✅ Structured logging, DB-backed, easy to add metrics |
| **Team scalability** | ⚠️ Fine for solo | ✅ Better for collaboration (typed APIs, auto-docs) |
| **Test infrastructure** | ⚠️ Playwright is JS — stays JS either way | Same — subprocess call |

### Verdict

**Yes, migrate — but incrementally.** The Python AI ecosystem advantage is real and growing. Storing builds in PostgreSQL instead of JSON files is a genuine quality-of-life improvement. And the RAG potential (learning from past builds, portfolio analysis, niche-specific copy training) is the real strategic win.

But do it in **phases**, not a big-bang rewrite. The Node.js runner can coexist with a new FastAPI service during transition.

---

## 2. What We Have Today

```
automation/
├── .env                          # GH_TOKEN, TELEGRAM_*, AI_MODEL
├── docker-compose.yml            # n8n + runner services
├── runner/
│   ├── Dockerfile                # node:20-slim + git + gh + Playwright + Chromium
│   └── server.js                 # HTTP server (505 lines)
│                                 #   POST /build → trigger
│                                 #   GET  /builds → history (JSON file)
│                                 #   GET  /builds/:id/stream → SSE
│                                 #   Telegram notifications
└── orchestrator/
    ├── index.js                  # BuildOrchestrator (EventEmitter, 183 lines)
    ├── lib/
    │   ├── ai.js                 # GitHub Models API wrapper (retry, JSON/HTML extract)
    │   ├── prompts.js            # All agent prompts (Strategist, Critic, Designer, Builder, Fixer)
    │   ├── shell.js              # exec/tryExec wrappers for git/gh
    │   └── testRunner.js         # Playwright test generation + execution
    └── phases/
        ├── 01-repo.js            # GitHub repo create/clone via gh CLI
        ├── 02-council.js         # Strategist ↔ Critic debate loop → blueprint JSON
        ├── 03-design.js          # AI → design system (Tailwind config, nav, footer)
        ├── 04-generate.js        # AI → per-page <main> content, wrapped in HTML shell
        ├── 05-assemble.js        # Nav stitching, sitemap, robots, 404, link validation
        ├── 06-test.js            # Playwright + axe tests → AI fix loop (up to 3 rounds)
        ├── 07-deploy.js          # git push, GitHub Pages API, submodule, portfolio card
        └── 08-notify.js          # Telegram bot notification
```

### Current Data Flow

```
Client Request (name, niche, goals, email)
     │
     ▼
[01-repo]     ──► GitHub repo created/cloned → { dir, repoName, liveUrl }
     │
     ▼
[02-council]  ──► AI Strategist ↔ Critic debate → blueprint JSON (pages, colors, fonts)
     │
     ▼
[03-design]   ──► AI Designer → design system (Tailwind, nav, footer, WCAG fixes)
     │
     ▼
[04-generate] ──► AI Page Builder × N pages → HTML files on disk
     │
     ▼
[05-assemble] ──► Nav states, sitemap.xml, robots.txt, 404.html, link validation
     │
     ▼
[06-test]     ──► Playwright/axe tests → if fail: AI Fixer → re-test (3 rounds)
     │
     ▼
[07-deploy]   ──► git push → GitHub Pages API → submodule → portfolio card
     │
     ▼
[08-notify]   ──► Telegram notification
```

### Current Storage: JSON Files on Disk

- `/workspace/.buildhistory/builds.json` — array of build metadata (capped at 200)
- `/workspace/.buildhistory/{id}.log` — raw log lines per build
- No queryability, no analytics, no search, no backup strategy

---

## 3. What We'd Gain

### Immediate Wins

1. **Queryable Build History** — "Show me all failed builds in the last month" is a SQL query, not a JSON file scan
2. **Structured Logging** — Every phase, AI call, test result → database row with timestamps, durations, token counts
3. **Auto-Generated API Docs** — FastAPI gives us Swagger/OpenAPI for free at `/docs`
4. **Pydantic Validation** — Client requests validated before the pipeline even starts
5. **Background Tasks** — FastAPI's `BackgroundTasks` or Celery for build execution
6. **WebSocket/SSE** — First-class async streaming with `starlette`

### Strategic Wins (RAG & Beyond)

7. **Vector Embeddings** — Store embeddings of every generated page in `pgvector`. Query: "Show me the best hero section for a restaurant" → instant retrieval
8. **Build Intelligence** — Which prompts produce the best test pass rates? Which niches need the most fix cycles? Data-driven prompt tuning
9. **Portfolio RAG** — When a new client says "I want something like [competitor]", the AI can retrieve similar past builds
10. **Copy Training** — Store all generated copy with quality scores. Over time, fine-tune or RAG the best copy for each niche
11. **Template Library** — Successful builds become templates. "This bakery site scored 10/10 on tests" → reuse its design system for future bakeries
12. **Client History** — If a client comes back for revisions, we have their full build context in the DB

---

## 4. Target Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Admin Dashboard                       │
│              (existing HTML/JS — unchanged)              │
│                                                         │
│  POST /api/v1/builds     GET /api/v1/builds/:id/stream │
│  GET  /api/v1/builds     GET /api/v1/builds/:id        │
│  GET  /api/v1/analytics  GET /api/v1/templates          │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP / SSE
                     ▼
┌─────────────────────────────────────────────────────────┐
│                  FastAPI Application                     │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │  Routes   │  │  Models  │  │  Schemas │             │
│  │ (builds,  │  │ (SQLAlch-│  │ (Pydantic│             │
│  │ analytics,│  │  emy ORM)│  │  request/│             │
│  │ templates)│  │          │  │  response)│            │
│  └─────┬─────┘  └────┬─────┘  └──────────┘             │
│        │              │                                  │
│  ┌─────▼──────────────▼─────────────────────┐           │
│  │         Pipeline Orchestrator             │           │
│  │                                           │           │
│  │  ┌─────────────────────────────────┐      │           │
│  │  │         Phase Runner            │      │           │
│  │  │  01_repo   → GitService         │      │           │
│  │  │  02_council → AIService         │      │           │
│  │  │  03_design  → AIService         │      │           │
│  │  │  04_generate → AIService        │      │           │
│  │  │  05_assemble → FileService      │      │           │
│  │  │  06_test    → TestService (JS!) │      │           │
│  │  │  07_deploy  → GitService        │      │           │
│  │  │  08_notify  → NotifyService     │      │           │
│  │  └─────────────────────────────────┘      │           │
│  │                                           │           │
│  │  ┌──────────┐  ┌──────────┐               │           │
│  │  │AIService │  │Embedding │               │           │
│  │  │(aiohttp) │  │ Service  │               │           │
│  │  │          │  │(pgvector)│               │           │
│  │  └──────────┘  └──────────┘               │           │
│  └───────────────────────────────────────────┘           │
│                                                         │
└────────────────────┬────────────────────────────────────┘
                     │
          ┌──────────┼──────────┐
          ▼          ▼          ▼
    ┌──────────┐ ┌────────┐ ┌──────────┐
    │PostgreSQL│ │ GitHub │ │ Telegram │
    │+ pgvector│ │  API   │ │   Bot    │
    │          │ │ + CLI  │ │          │
    └──────────┘ └────────┘ └──────────┘
```

### Project Structure

```
automation/
├── api/                          # NEW — FastAPI application
│   ├── __init__.py
│   ├── main.py                   # FastAPI app, lifespan, middleware
│   ├── config.py                 # Settings (pydantic-settings, env vars)
│   ├── database.py               # SQLAlchemy async engine + session
│   │
│   ├── models/                   # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── build.py              # Build, BuildPhase, BuildLog
│   │   ├── template.py           # DesignTemplate, PageTemplate
│   │   └── embedding.py          # PageEmbedding (pgvector)
│   │
│   ├── schemas/                  # Pydantic request/response schemas
│   │   ├── __init__.py
│   │   ├── build.py              # BuildRequest, BuildResponse, BuildStatus
│   │   └── template.py           # TemplateResponse
│   │
│   ├── routes/                   # API endpoints
│   │   ├── __init__.py
│   │   ├── builds.py             # POST /builds, GET /builds, SSE stream
│   │   ├── analytics.py          # GET /analytics (build stats, pass rates)
│   │   └── templates.py          # GET /templates, RAG search
│   │
│   ├── services/                 # Business logic layer
│   │   ├── __init__.py
│   │   ├── ai.py                 # AI API calls (aiohttp, async)
│   │   ├── git.py                # Git/GitHub operations (asyncio subprocess)
│   │   ├── notify.py             # Telegram (aiohttp)
│   │   ├── embedding.py          # Generate & store embeddings (pgvector)
│   │   └── test_runner.py        # Playwright test orchestration (calls JS subprocess)
│   │
│   ├── pipeline/                 # Build pipeline (replaces orchestrator/phases/)
│   │   ├── __init__.py
│   │   ├── orchestrator.py       # Main pipeline runner (async, DB-backed)
│   │   ├── phases/
│   │   │   ├── __init__.py
│   │   │   ├── p01_repo.py
│   │   │   ├── p02_council.py
│   │   │   ├── p03_design.py
│   │   │   ├── p04_generate.py
│   │   │   ├── p05_assemble.py
│   │   │   ├── p06_test.py
│   │   │   ├── p07_deploy.py
│   │   │   └── p08_notify.py
│   │   └── prompts.py            # All prompt templates (mostly copy-paste from JS)
│   │
│   └── tests/                    # Python tests (pytest)
│       ├── test_api.py
│       ├── test_pipeline.py
│       └── test_ai.py
│
├── js/                           # KEPT — JavaScript that must stay JS
│   ├── test_runner.js            # Playwright test generation (called via subprocess)
│   ├── inject_card.js            # Portfolio card injector
│   └── playwright.config.js      # Shared Playwright config
│
├── alembic/                      # Database migrations
│   ├── alembic.ini
│   └── versions/
│
├── docker-compose.yml            # Updated: FastAPI + PostgreSQL + (optional n8n)
├── Dockerfile                    # python:3.12-slim + Node.js + Playwright
├── requirements.txt              # Python dependencies
├── .env.example
└── MIGRATION_PLAN.md             # This file
```

---

## 5. Database Schema

### Core Tables

```sql
-- ═══════════════════════════════════════════
--  Builds — replaces builds.json
-- ═══════════════════════════════════════════
CREATE TABLE builds (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    short_id        VARCHAR(8) UNIQUE NOT NULL,     -- human-friendly ID
    client_name     VARCHAR(255) NOT NULL,
    niche           VARCHAR(255) NOT NULL,
    goals           TEXT NOT NULL,
    email           VARCHAR(255),
    
    -- Results
    status          VARCHAR(20) NOT NULL DEFAULT 'queued',  -- queued/running/success/failed
    repo_name       VARCHAR(255),
    repo_full       VARCHAR(255),                   -- org/repo
    live_url        VARCHAR(512),
    pages_count     INTEGER,
    
    -- Blueprint (the AI council output — stored as JSONB for querying)
    blueprint       JSONB,
    design_system   JSONB,                          -- Tailwind config, nav, footer
    
    -- Timing
    started_at      TIMESTAMPTZ,
    finished_at     TIMESTAMPTZ,
    duration_secs   INTEGER GENERATED ALWAYS AS (
        EXTRACT(EPOCH FROM (finished_at - started_at))
    ) STORED,
    
    -- Metadata
    error_message   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_builds_status ON builds(status);
CREATE INDEX idx_builds_niche ON builds(niche);
CREATE INDEX idx_builds_created ON builds(created_at DESC);

-- ═══════════════════════════════════════════
--  Build Phases — granular timing per phase
-- ═══════════════════════════════════════════
CREATE TABLE build_phases (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    build_id        UUID NOT NULL REFERENCES builds(id) ON DELETE CASCADE,
    phase_number    SMALLINT NOT NULL,              -- 1-8
    phase_name      VARCHAR(50) NOT NULL,           -- repo, council, design, etc.
    status          VARCHAR(20) NOT NULL DEFAULT 'pending',
    
    -- AI call tracking
    ai_calls        INTEGER DEFAULT 0,              -- how many LLM calls this phase made
    ai_tokens_in    INTEGER DEFAULT 0,              -- total input tokens
    ai_tokens_out   INTEGER DEFAULT 0,              -- total output tokens
    ai_model        VARCHAR(100),
    
    -- Timing
    started_at      TIMESTAMPTZ,
    finished_at     TIMESTAMPTZ,
    duration_secs   NUMERIC(8,2),
    
    -- Phase-specific data
    metadata        JSONB,                          -- council transcript, test results, etc.
    error_message   TEXT,
    
    UNIQUE(build_id, phase_number)
);

-- ═══════════════════════════════════════════
--  Build Logs — replaces .log files
-- ═══════════════════════════════════════════
CREATE TABLE build_logs (
    id              BIGSERIAL PRIMARY KEY,
    build_id        UUID NOT NULL REFERENCES builds(id) ON DELETE CASCADE,
    sequence        INTEGER NOT NULL,               -- ordering within build
    level           VARCHAR(10) DEFAULT 'info',     -- info, warn, error, debug
    category        VARCHAR(30),                    -- phase, ai, test, deploy
    message         TEXT NOT NULL,
    metadata        JSONB,                          -- structured data (phase info, test results)
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_build_logs_build ON build_logs(build_id, sequence);

-- ═══════════════════════════════════════════
--  Generated Pages — per-page tracking
-- ═══════════════════════════════════════════
CREATE TABLE build_pages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    build_id        UUID NOT NULL REFERENCES builds(id) ON DELETE CASCADE,
    slug            VARCHAR(100) NOT NULL,
    title           VARCHAR(255),
    filename        VARCHAR(255),
    status          VARCHAR(20),                    -- generated, fallback, fixed
    
    -- Content (for RAG and analysis)
    html_content    TEXT,                           -- full page HTML
    main_content    TEXT,                           -- just the <main> block
    word_count      INTEGER,
    
    -- Quality metrics
    fix_attempts    INTEGER DEFAULT 0,
    test_passed     BOOLEAN,
    axe_violations  INTEGER DEFAULT 0,
    
    -- SEO
    h1_text         VARCHAR(500),
    meta_description VARCHAR(500),
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_build_pages_build ON build_pages(build_id);

-- ═══════════════════════════════════════════
--  Test Results — per-test tracking
-- ═══════════════════════════════════════════
CREATE TABLE test_results (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    build_id        UUID NOT NULL REFERENCES builds(id) ON DELETE CASCADE,
    attempt         SMALLINT NOT NULL,              -- which fix cycle (1, 2, 3)
    page_slug       VARCHAR(100),
    test_name       VARCHAR(255),
    device          VARCHAR(50),                    -- Desktop, Mobile
    passed          BOOLEAN NOT NULL,
    error_message   TEXT,
    duration_ms     INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_test_results_build ON test_results(build_id, attempt);

-- ═══════════════════════════════════════════
--  Design Templates — successful builds become templates
-- ═══════════════════════════════════════════
CREATE TABLE design_templates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    build_id        UUID REFERENCES builds(id),     -- source build
    niche           VARCHAR(255) NOT NULL,
    name            VARCHAR(255) NOT NULL,
    
    blueprint       JSONB NOT NULL,
    design_system   JSONB NOT NULL,
    
    -- Quality gate
    test_pass_rate  NUMERIC(5,2),                   -- 0-100%
    quality_score   NUMERIC(3,1),                   -- 1-10 (critic score)
    
    is_active       BOOLEAN DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_templates_niche ON design_templates(niche);
```

### Vector Embeddings (pgvector — the RAG enabler)

```sql
-- Requires: CREATE EXTENSION vector;

-- ═══════════════════════════════════════════
--  Page Embeddings — for semantic search
-- ═══════════════════════════════════════════
CREATE TABLE page_embeddings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    build_page_id   UUID NOT NULL REFERENCES build_pages(id) ON DELETE CASCADE,
    build_id        UUID NOT NULL REFERENCES builds(id) ON DELETE CASCADE,
    
    niche           VARCHAR(255),
    page_slug       VARCHAR(100),
    section_type    VARCHAR(100),                   -- hero, features, testimonials, cta
    
    -- The embedding vector (1536 for OpenAI ada-002, 768 for smaller models)
    content_text    TEXT NOT NULL,                   -- the text that was embedded
    embedding       vector(1536),                   -- the embedding itself
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- HNSW index for fast similarity search
CREATE INDEX idx_embeddings_vector ON page_embeddings 
    USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_embeddings_niche ON page_embeddings(niche);
```

### Example RAG Queries

```sql
-- "Find the best hero sections for restaurants"
SELECT bp.main_content, b.client_name, bp.title, 
       pe.embedding <=> $1::vector AS distance
FROM page_embeddings pe
JOIN build_pages bp ON pe.build_page_id = bp.id
JOIN builds b ON pe.build_id = b.id
WHERE pe.niche ILIKE '%restaurant%'
  AND pe.section_type = 'hero'
  AND bp.test_passed = true
ORDER BY distance ASC
LIMIT 5;

-- "What's our average test pass rate by niche?"
SELECT b.niche, 
       COUNT(*) AS total_builds,
       AVG(CASE WHEN b.status = 'success' THEN 1.0 ELSE 0.0 END) * 100 AS success_rate,
       AVG(b.duration_secs) AS avg_duration
FROM builds b
GROUP BY b.niche
ORDER BY total_builds DESC;

-- "Which prompts produce the most fix cycles?"
SELECT bp.phase_name, 
       AVG((bp.metadata->>'fix_attempts')::int) AS avg_fixes,
       COUNT(*) AS total
FROM build_phases bp
WHERE bp.phase_name = 'test'
GROUP BY bp.phase_name;
```

---

## 6. RAG & Future AI Architecture

### Phase 1: Store & Query (Immediate)
- Store all blueprints, design systems, and generated HTML in PostgreSQL
- Query past builds by niche, quality score, or any field
- No AI embeddings yet — just structured data

### Phase 2: Embeddings & Similarity (Month 2)
- After each successful build, embed page content using OpenAI or a local model
- Store in `pgvector` for cosine similarity search
- Use case: "Find hero sections similar to this client's request"

### Phase 3: RAG-Enhanced Generation (Month 3+)
- Before AI generates a page, **retrieve** the top-3 most similar successful pages from past builds
- Include them in the prompt as few-shot examples
- This means the AI learns from YOUR portfolio, not just its training data

```python
# Future RAG flow in p04_generate.py
async def generate_page_with_rag(page_spec, design_system, blueprint, db):
    # 1. Embed the page request
    query_embedding = await embed_text(
        f"{blueprint.niche} {page_spec.title} {page_spec.purpose}"
    )
    
    # 2. Retrieve similar successful pages
    similar_pages = await db.execute(
        select(PageEmbedding)
        .where(PageEmbedding.section_type == page_spec.sections[0])
        .order_by(PageEmbedding.embedding.cosine_distance(query_embedding))
        .limit(3)
    )
    
    # 3. Build prompt with examples
    examples = "\n\n".join([
        f"EXAMPLE ({p.niche} - {p.page_slug}):\n{p.content_text[:2000]}"
        for p in similar_pages
    ])
    
    prompt = f"""Build the "{page_spec.title}" page.
    
Here are successful examples from similar businesses:
{examples}

Now generate for THIS client: {blueprint.site_name}
..."""
    
    return await ai_service.call(prompt)
```

### Phase 4: Analytics Dashboard (Month 4+)
- Build quality trends over time
- AI token usage and cost tracking
- Niche-specific insights ("bakery sites average 5 pages, 2.1 fix cycles")
- A/B test different prompts and measure outcomes

---

## 7. API Design

### Endpoints

```
# ── Builds ─────────────────────────────────────────────
POST   /api/v1/builds                    # Trigger a new build
GET    /api/v1/builds                    # List all builds (paginated, filterable)
GET    /api/v1/builds/{id}               # Build detail + phases
GET    /api/v1/builds/{id}/stream        # SSE live stream
GET    /api/v1/builds/{id}/logs          # Full log (paginated)
GET    /api/v1/builds/{id}/pages         # Generated pages for a build
DELETE /api/v1/builds/{id}               # Cancel / delete a build

# ── Analytics ──────────────────────────────────────────
GET    /api/v1/analytics/overview        # Total builds, success rate, avg duration
GET    /api/v1/analytics/niches          # Stats per niche
GET    /api/v1/analytics/ai-usage        # Token consumption, model breakdown
GET    /api/v1/analytics/test-insights   # Most common failures, fix rates

# ── Templates (RAG) ───────────────────────────────────
GET    /api/v1/templates                 # Browse successful templates by niche
GET    /api/v1/templates/search          # Semantic search (pgvector)
POST   /api/v1/templates/{id}/clone      # Start a new build from a template

# ── Health ─────────────────────────────────────────────
GET    /api/v1/health                    # Service health + DB connectivity
GET    /docs                             # Auto-generated Swagger UI (free from FastAPI)
```

### Pydantic Schemas (examples)

```python
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from enum import Enum

class BuildStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"

class BuildRequest(BaseModel):
    business_name: str = Field(..., min_length=2, max_length=255)
    niche: str = Field(..., min_length=2, max_length=255)
    goals: str = Field(..., min_length=10, max_length=2000)
    email: EmailStr | None = None
    template_id: str | None = None  # Optional: start from a past successful build

class BuildResponse(BaseModel):
    id: str
    short_id: str
    status: BuildStatus
    client_name: str
    niche: str
    live_url: str | None
    repo_url: str | None
    pages_count: int | None
    started_at: datetime | None
    finished_at: datetime | None
    duration_secs: float | None
    stream_url: str

class PhaseDetail(BaseModel):
    phase_number: int
    phase_name: str
    status: str
    duration_secs: float | None
    ai_calls: int
    ai_tokens_in: int
    ai_tokens_out: int
```

---

## 8. Migration Phases

### 🔵 Phase 0: Foundation (Week 1)

**Goal:** FastAPI skeleton + PostgreSQL running alongside existing Node.js runner.

- [ ] Set up `api/` directory with FastAPI project structure
- [ ] Add PostgreSQL + pgvector to `docker-compose.yml`
- [ ] Create Alembic migrations for all tables
- [ ] Implement `config.py` with pydantic-settings (reads same `.env`)
- [ ] Implement `database.py` with async SQLAlchemy
- [ ] Basic health endpoint + Swagger UI
- [ ] **Node.js runner still handles all builds** — Python just serves read-only endpoints

```yaml
# docker-compose.yml — Phase 0 addition
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: ajayadesign
      POSTGRES_USER: ajayadesign
      POSTGRES_PASSWORD: ${DB_PASSWORD:-localdev}
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  api:
    build:
      context: .
      dockerfile: Dockerfile.api
    ports:
      - "8000:8000"
    depends_on:
      - postgres
    environment:
      - DATABASE_URL=postgresql+asyncpg://ajayadesign:${DB_PASSWORD:-localdev}@postgres:5432/ajayadesign
      - GH_TOKEN=${GH_TOKEN}
```

### 🔵 Phase 1: Port the API Layer (Week 1-2)

**Goal:** FastAPI handles HTTP requests and SSE, but delegates build execution to the existing Node.js orchestrator via subprocess.

- [ ] `POST /api/v1/builds` — validates request, creates DB row, spawns Node.js orchestrator
- [ ] `GET /api/v1/builds` — reads from PostgreSQL (migrate history JSON → DB)
- [ ] `GET /api/v1/builds/{id}/stream` — SSE from DB logs (polled or change-notified)
- [ ] Write a **bridge**: Python spawns `node orchestrator/index.js` and captures stdout → DB
- [ ] Migrate existing JSON build history into PostgreSQL (one-time script)
- [ ] Update admin dashboard to point to `:8000/api/v1/` instead of `:3456/`

**Key insight:** The Node.js orchestrator still does all the real work. Python is just a better HTTP/DB layer in front of it.

### 🔵 Phase 2: Port Services to Python (Week 2-3)

**Goal:** Replace Node.js lib modules with Python equivalents.

| Node.js Module | Python Replacement | Notes |
|---|---|---|
| `lib/ai.js` | `services/ai.py` | `aiohttp` + retry logic. Async native. Add token counting. |
| `lib/shell.js` | `services/git.py` | `asyncio.create_subprocess_exec`. Same git/gh commands. |
| `lib/prompts.js` | `pipeline/prompts.py` | Almost literal copy — they're just template strings. |
| `lib/testRunner.js` | `services/test_runner.py` | **Keep JS test files** — Python just calls `npx playwright test` via subprocess. |

### 🔵 Phase 3: Port Pipeline Phases (Week 3-4)

**Goal:** Replace Node.js phases with Python equivalents, one at a time.

Port order (easiest → hardest):

1. **p08_notify.py** — Simple Telegram HTTP call. 20 minutes.
2. **p01_repo.py** — Shell commands to git/gh. 1 hour.
3. **p02_council.py** — AI calls with JSON parsing. 2 hours.
4. **p03_design.py** — AI call + WCAG contrast validation. 2 hours (port contrast logic).
5. **p05_assemble.py** — File manipulation (nav stitching, sitemap). 2 hours.
6. **p04_generate.py** — AI call per page + HTML wrapping. 2 hours.
7. **p06_test.py** — Complex: subprocess to JS Playwright + AI fix loop. 3 hours.
8. **p07_deploy.py** — Shell commands + GitHub API + portfolio card. 2 hours.

Each phase can be ported independently. The orchestrator can call a mix of Python phases and Node.js phases during transition.

### 🔵 Phase 4: RAG & Embeddings (Week 5+)

**Goal:** Store embeddings, enable semantic search.

- [ ] After each successful build, embed page content → `page_embeddings` table
- [ ] Add `/api/v1/templates/search` endpoint (cosine similarity)
- [ ] Modify `p04_generate.py` to retrieve similar pages before generation
- [ ] Add quality scoring (auto-promote builds with 100% test pass to templates)

### 🔵 Phase 5: Analytics & Intelligence (Week 6+)

- [ ] Build analytics dashboard endpoints
- [ ] Token usage tracking per build, per phase
- [ ] Prompt A/B testing framework
- [ ] Niche-specific performance insights

---

## 9. What Stays JavaScript (And That's OK)

This migration is **backend only**. Everything the end user sees is and always will be static HTML/CSS/JS on GitHub Pages.

### Never Migrating — Static Frontend (GitHub Pages)

| Component | Path | Why It Stays |
|-----------|------|-------------|
| **Main website** | `/index.html`, `/js/`, `/css/` | Static portfolio site. Pure HTML/CSS/JS. Hosted on GitHub Pages. No server needed. |
| **Admin dashboard** | `/admin/index.html`, `/admin/js/` | Static SPA hosted on GitHub Pages. Uses Firebase Auth for login, `fetch()` + `EventSource` to talk to the automation API. The **only change** post-migration: swap `http://drone:3456/build` → `http://drone:8000/api/v1/builds` in the JS. |
| **Contact form / leads** | `/admin/js/admin.js` | Firebase Realtime Database for leads. Has nothing to do with the build pipeline. |
| **Generated client sites** | `github.com/ajayadesign/{client}/` | The whole point of the pipeline is to OUTPUT static HTML/CSS/JS. Python generates the exact same files Node.js does. Deployed to GitHub Pages via `git push`. |

### Stays JS Inside the Backend (subprocess calls)

| Component | Why It Stays JS |
|-----------|----------------|
| **Playwright tests** (`.spec.js`) | Playwright's Node.js API is first-class. The axe-core/playwright integration is JS-native. Python just calls `npx playwright test` via subprocess — same as calling `git`. |
| **inject_card.js** | Tiny DOM script that adds portfolio cards to the main site. 50 lines, called via `node inject_card.js`. Not worth porting. |

### The Key Insight

```
┌─────────────────────────────────────────────────────┐
│           GitHub Pages (Static Hosting)              │
│                                                     │
│  Main Site    Admin Dashboard    Client Sites        │
│  (HTML/JS)    (HTML/JS)          (HTML/JS)           │
│                   │                                  │
│                   │ fetch() / SSE                    │
└───────────────────┼─────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────┐
│           Docker on Drone Server                     │
│                                                     │
│  ┌─────────────────────────────────────────────┐    │
│  │  FastAPI (Python)          ← THIS MIGRATES  │    │
│  │  • POST /api/v1/builds                      │    │
│  │  • GET  /api/v1/builds/:id/stream (SSE)     │    │
│  │  • 8-phase build pipeline                   │    │
│  │  • AI agent calls                           │    │
│  └──────────────────┬──────────────────────────┘    │
│                     │                               │
│  ┌──────────────────▼──────────────────────────┐    │
│  │  PostgreSQL + pgvector                      │    │
│  │  • Build history, logs, analytics           │    │
│  │  • Page embeddings for RAG                  │    │
│  └─────────────────────────────────────────────┘    │
│                                                     │
└─────────────────────────────────────────────────────┘
```

The Python pipeline calls JS tools (Playwright, inject_card) via `asyncio.create_subprocess_exec` — exactly like it already calls `git` and `gh`. No friction.

---

## 10. Docker & Infrastructure

### New Dockerfile (multi-stage)

```dockerfile
# ── Stage 1: Python base ────────────────────
FROM python:3.12-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl jq ca-certificates gnupg sudo \
    # Playwright/Chromium deps
    libnss3 libnspr4 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libgbm1 libgtk-3-0 libpango-1.0-0 \
    libcairo2 libgdk-pixbuf2.0-0 libasound2 libxshmfence1 \
    libx11-xcb1 libxcomposite1 libxrandr2 libxdamage1 \
    && rm -rf /var/lib/apt/lists/*

# ── Node.js (for Playwright + test runner) ──
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g serve @playwright/test @axe-core/playwright \
    && npx playwright install --with-deps chromium

# ── GitHub CLI ──
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
    | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
    | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update && apt-get install -y gh

# ── Python dependencies ──
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### requirements.txt

```
# Web framework
fastapi>=0.115.0
uvicorn[standard]>=0.34.0
sse-starlette>=2.0.0

# Database
sqlalchemy[asyncio]>=2.0.0
asyncpg>=0.30.0
alembic>=1.14.0
pgvector>=0.3.0

# HTTP client (for AI API, Telegram)
aiohttp>=3.11.0
httpx>=0.28.0

# Validation & settings
pydantic>=2.10.0
pydantic-settings>=2.7.0
email-validator>=2.0.0

# AI & Embeddings (for RAG phase)
# tiktoken>=0.8.0             # Token counting
# openai>=1.60.0              # For embeddings (or use GitHub Models)

# Dev & testing
pytest>=8.0.0
pytest-asyncio>=0.24.0
```

### Updated docker-compose.yml

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    container_name: ajayadesign-db
    restart: unless-stopped
    environment:
      POSTGRES_DB: ajayadesign
      POSTGRES_USER: ajayadesign
      POSTGRES_PASSWORD: ${DB_PASSWORD:-localdev}
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ajayadesign"]
      interval: 5s
      retries: 5

  api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: ajayadesign-api
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://ajayadesign:${DB_PASSWORD:-localdev}@postgres:5432/ajayadesign
      - GH_TOKEN=${GH_TOKEN}
      - AI_MODEL=${AI_MODEL:-gpt-4o}
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN:-}
      - TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID:-}
    volumes:
      - /home/aj/website:/workspace
      - ~/.config/gh:/root/.config/gh:ro
    depends_on:
      postgres:
        condition: service_healthy

  # n8n stays optional
  n8n:
    image: n8nio/n8n:latest
    container_name: ajayadesign-n8n
    restart: unless-stopped
    ports:
      - "5678:5678"
    environment:
      - N8N_HOST=0.0.0.0
      - WEBHOOK_URL=http://localhost:5678/
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=${N8N_USER:-admin}
      - N8N_BASIC_AUTH_PASSWORD=${N8N_PASSWORD:-changeme}
    volumes:
      - n8n_data:/home/node/.n8n
    depends_on:
      - api

volumes:
  pgdata:
  n8n_data:
```

---

## 11. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| **Rewrite takes longer than expected** | High | Medium | Incremental approach — Node.js runner works throughout. Never have downtime. |
| **Playwright integration from Python** | Low | Medium | Already solved pattern: `asyncio.create_subprocess_exec("npx", "playwright", "test")`. Same as calling `git`. |
| **PostgreSQL adds operational complexity** | Medium | Low | `pgvector/pgvector:pg16` Docker image is production-ready. Add backups via `pg_dump` cron. |
| **Async Python debugging harder than Node** | Medium | Low | Use `structlog` for structured logging. FastAPI's error handling is excellent. |
| **AI API differences between `https` and `aiohttp`** | Low | Low | Same HTTP calls, just async. The prompts don't change at all. |
| **Admin dashboard SSE breaks** | Medium | Medium | Test SSE thoroughly. FastAPI's `sse-starlette` is battle-tested. Keep endpoint contract identical. |
| **Performance regression** | Low | Medium | Python async is comparable to Node for I/O-bound work (which this is — all waiting on AI APIs and git). |

---

## 12. Estimated Timeline

| Phase | Effort | Calendar Time | Cumulative |
|-------|--------|---------------|------------|
| **Phase 0** — Foundation (FastAPI + DB + Docker) | 6 hours | 1-2 days | Week 1 |
| **Phase 1** — API layer (HTTP + SSE + bridge to Node) | 8 hours | 2-3 days | Week 1-2 |
| **Phase 2** — Port services (AI, git, prompts) | 6 hours | 1-2 days | Week 2 |
| **Phase 3** — Port all 8 phases | 12 hours | 3-4 days | Week 3-4 |
| **Phase 4** — RAG & embeddings | 8 hours | 2-3 days | Week 5 |
| **Phase 5** — Analytics & intelligence | 8 hours | 2-3 days | Week 6 |
| **Total** | **~48 hours** | **~6 weeks** (part-time) | |

> **Part-time estimate** assumes ~8-10 hours/week. Full-time could compress to 2-3 weeks.

---

## 13. Decision

### Go Criteria ✅

- [x] We want RAG/embeddings in the future → Python ecosystem is far superior
- [x] JSON file storage is limiting → PostgreSQL is a clear upgrade
- [x] The Node.js server (`http.createServer`) has no validation, no docs, no middleware
- [x] We want build analytics → need a real database
- [x] The pipeline is stable enough to rewrite incrementally
- [x] Prompts (the hard part) are language-agnostic strings — they transfer 1:1

### No-Go Criteria ❌

- [ ] ~~We need features shipped this week~~ → The incremental approach avoids this
- [ ] ~~The team doesn't know Python~~ → You know Python
- [ ] ~~Playwright won't work~~ → It's a subprocess call, works from any language

### Recommendation

**GO** — Start with Phase 0 + 1 (FastAPI skeleton + DB + bridge to Node.js orchestrator). This gives us:

1. Real database immediately (queryable builds, proper history)
2. Auto-documented API (Swagger)
3. Input validation (Pydantic)
4. Zero downtime (Node.js runner still works during migration)

Then port phases incrementally, and add RAG when the data starts accumulating.

---

*Last updated: 2026-02-14*
