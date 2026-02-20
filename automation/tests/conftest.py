"""
Shared test fixtures — async DB, mock services, FastAPI test client.
"""

import asyncio
import json
import os
import tempfile
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from api.database import Base, get_db
from api.main import app
from api.models.build import Build


# ── Async Event Loop ────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ── Test Database (SQLite in-memory) ────────────────────

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture()
async def db_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture()
async def db_session(db_engine):
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture()
async def client(db_engine):
    """FastAPI test client with test DB injected."""
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def _override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ── Sample Build Data ───────────────────────────────────

SAMPLE_BUILD_REQUEST = {
    "businessName": "Sunrise Bakery",
    "niche": "Artisan Bakery & Café",
    "goals": "Showcase our handmade pastries and drive catering orders",
    "email": "hello@sunrise-bakery.com",
}

SAMPLE_BLUEPRINT = {
    "siteName": "Sunrise Bakery",
    "tagline": "Handmade Pastries & Fresh-Baked Joy",
    "brandVoice": "warm, artisanal, inviting",
    "siteGoals": "Showcase pastries, drive catering orders",
    "colorDirection": {
        "primary": "#D4763C",
        "accent": "#2D5F3A",
        "surface": "#0E0E12",
        "surfaceAlt": "#16161D",
        "textMain": "#E5E7EB",
        "textMuted": "#9CA3AF",
    },
    "typography": {"headings": "Playfair Display", "body": "Inter"},
    "pages": [
        {"slug": "index", "title": "Home", "navLabel": "Home", "purpose": "Hero + intro"},
        {"slug": "menu", "title": "Our Menu", "navLabel": "Menu", "purpose": "Pastry gallery"},
        {"slug": "about", "title": "About Us", "navLabel": "About", "purpose": "Our story"},
        {"slug": "contact", "title": "Contact", "navLabel": "Contact", "purpose": "Contact form"},
    ],
}

SAMPLE_DESIGN_SYSTEM = {
    "tailwindConfig": """tailwind.config = {
      theme: { extend: { colors: {
        primary: '#D4763C', accent: '#2D5F3A', cta: '#D4763C',
        surface: '#0E0E12', surfaceAlt: '#16161D',
        textMain: '#E5E7EB', textMuted: '#9CA3AF'
      }, fontFamily: { heading: ['Playfair Display'], body: ['Inter'] } } }
    }""",
    "googleFontsUrl": "https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Playfair+Display:wght@700&display=swap",
    "navHtml": '<nav class="fixed top-0 w-full bg-surface/90 backdrop-blur z-50 px-6 py-4"><a href="/">Sunrise Bakery</a></nav>',
    "footerHtml": '<footer class="bg-surfaceAlt py-12 text-center text-textMuted">© 2025 Sunrise Bakery</footer>',
    "bodyClass": "bg-surface text-textMain font-body antialiased",
    "activeNavClass": "text-primary font-bold",
    "inactiveNavClass": "text-textMuted hover:text-primary transition",
    "mobileMenuJs": "",
    "siteName": "Sunrise Bakery",
    "sharedHead": '<meta charset="UTF-8"><script src="https://cdn.tailwindcss.com"></script>',
}

SAMPLE_PAGE_HTML = """<main class="pt-20">
  <section class="min-h-screen flex items-center justify-center px-6">
    <div class="text-center max-w-3xl">
      <h1 class="font-heading text-5xl font-bold text-textMain mb-6">Welcome to Sunrise Bakery</h1>
      <p class="text-xl text-textMuted mb-8">Handmade Pastries &amp; Fresh-Baked Joy</p>
      <a href="/contact.html" class="px-8 py-3 bg-primary text-white rounded-lg">Get in Touch</a>
    </div>
  </section>
</main>"""

SAMPLE_CRITIC_RESPONSE = {
    "approved": True,
    "score": 9,
    "summary": "Strong bakery site plan",
    "critiques": [],
}

SAMPLE_CREATIVE_SPEC = {
    "visualConcept": "Warm artisanal bakery with inviting golden tones",
    "heroTreatment": {
        "type": "parallax-image",
        "description": "Full-viewport image of fresh bread with warm overlay",
        "ctaStyle": "solid-lift",
        "textAnimation": "fade-up-stagger",
    },
    "motionDesign": {
        "scrollRevealDefault": "fade-up",
        "staggerDelay": "100ms",
        "hoverScale": "1.02",
    },
    "colorEnhancements": {
        "useGradientText": True,
        "useNoiseOverlay": False,
        "useGlassMorphism": False,
    },
    "imageSearchTerms": {
        "index": ["artisan bread warm lighting"],
        "about": ["bakery kitchen professional"],
    },
}


@pytest.fixture
def sample_request():
    return dict(SAMPLE_BUILD_REQUEST)


@pytest.fixture
def sample_blueprint():
    return json.loads(json.dumps(SAMPLE_BLUEPRINT))


@pytest.fixture
def sample_design_system():
    return json.loads(json.dumps(SAMPLE_DESIGN_SYSTEM))


# ── Temp Project Directory ──────────────────────────────

@pytest.fixture
def project_dir(tmp_path):
    """Temp directory simulating a cloned repo."""
    d = tmp_path / "sunrise-bakery"
    d.mkdir()
    return str(d)


# ── Mock AI Service ─────────────────────────────────────

@pytest.fixture
def mock_ai():
    """Patches api.services.ai.call_ai at ALL import points (service + phases)."""
    call_count = {"n": 0}

    async def _fake_call_ai(messages, **kwargs):
        call_count["n"] += 1
        system = messages[0]["content"].lower() if messages else ""
        user = messages[-1]["content"].lower() if messages else ""

        # Strategist — matches "web strategist" in STRATEGIST_SYSTEM
        if "web strategist" in system:
            return "```json\n" + json.dumps(SAMPLE_BLUEPRINT) + "\n```"

        # Critic — matches "ux critic" in CRITIC_SYSTEM
        if "ux critic" in system:
            return "```json\n" + json.dumps(SAMPLE_CRITIC_RESPONSE) + "\n```"

        # Creative Director — matches "creative director" in CREATIVE_DIRECTOR_SYSTEM
        if "creative director" in system:
            return "```json\n" + json.dumps(SAMPLE_CREATIVE_SPEC) + "\n```"

        # Designer — matches "visual designer" in DESIGNER_SYSTEM
        if "visual designer" in system:
            return "```json\n" + json.dumps(SAMPLE_DESIGN_SYSTEM) + "\n```"

        # Page builder — matches "frontend developer" in PAGE_BUILDER_SYSTEM
        if "frontend developer" in system and "<main>" in system:
            return SAMPLE_PAGE_HTML

        # Fixer — matches "fixing accessibility" in FIXER_SYSTEM
        if "fixing accessibility" in system:
            return SAMPLE_PAGE_HTML

        # Polish — matches "visual polish" in POLISH_SYSTEM
        if "visual polish" in system:
            return SAMPLE_PAGE_HTML

        # Scraper analysis — matches "analyze an existing website" in SCRAPER_ANALYSIS_SYSTEM
        if "analyze" in system and "existing website" in system:
            return '```json\n{"brand_voice": "warm, inviting", "sentiment": "premium"}\n```'

        # Default
        return '{"ok": true}'

    with patch("api.services.ai.call_ai", side_effect=_fake_call_ai) as m, \
         patch("api.pipeline.phases.p02_council.call_ai", side_effect=_fake_call_ai), \
         patch("api.pipeline.phases.p03_design.call_ai", side_effect=_fake_call_ai), \
         patch("api.pipeline.phases.p04_generate.call_ai", side_effect=_fake_call_ai), \
         patch("api.pipeline.phases.p06_test.call_ai", side_effect=_fake_call_ai):
        m.call_count_tracker = call_count
        yield m


# ── Mock Git Service ────────────────────────────────────

@pytest.fixture
def mock_git(project_dir):
    """Patches git commands to no-op (creates dirs instead).
    Default: repo does NOT exist → fresh create."""

    async def _fake_run_cmd(cmd, cwd=None, **kwargs):
        if "clone" in cmd:
            os.makedirs(project_dir, exist_ok=True)
            return ""
        if "gh repo" in cmd:
            return "ok"
        return ""

    async def _fake_try_cmd(cmd, cwd=None, **kwargs):
        if "gh repo view" in cmd:
            return (False, "")  # repo doesn't exist → create new
        if "gh repo create" in cmd:
            return (True, "created")
        if "gh api" in cmd:
            return (True, "ok")
        return (True, "ok")

    # Also mock find_unique_repo_name so it just uses sanitize_repo_name
    from api.services.git import sanitize_repo_name as _san

    async def _fake_find_unique(business_name, github_org, **kwargs):
        return _san(business_name)

    with patch("api.services.git.run_cmd", side_effect=_fake_run_cmd) as m_run, \
         patch("api.services.git.try_cmd", side_effect=_fake_try_cmd) as m_try, \
         patch("api.services.git.find_unique_repo_name", side_effect=_fake_find_unique), \
         patch("api.pipeline.phases.p01_repo.run_cmd", side_effect=_fake_run_cmd), \
         patch("api.pipeline.phases.p01_repo.try_cmd", side_effect=_fake_try_cmd), \
         patch("api.pipeline.phases.p01_repo.find_unique_repo_name", side_effect=_fake_find_unique), \
         patch("api.pipeline.phases.p07_deploy.run_cmd", side_effect=_fake_run_cmd), \
         patch("api.pipeline.phases.p07_deploy.try_cmd", side_effect=_fake_try_cmd):
        yield m_run, m_try


# ── Mock Telegram ───────────────────────────────────────

@pytest.fixture
def mock_telegram():
    with patch("api.services.notify.send_telegram", new_callable=AsyncMock, return_value=True) as m, \
         patch("api.pipeline.phases.p08_notify.send_telegram", new_callable=AsyncMock, return_value=True):
        yield m

# ── Mock Firebase ───────────────────────────────────

@pytest.fixture
def mock_firebase():
    """Mock Firebase — use in tests where builds have firebase_id."""
    with patch("api.services.firebase.update_lead_status", return_value=True) as m:
        yield m

# ── Mock Test Runner ────────────────────────────────────

@pytest.fixture
def mock_test_runner():
    """Patches test runner to always pass."""
    with patch("api.services.test_runner.setup_tests") as m_setup, \
         patch("api.services.test_runner.run_tests", new_callable=AsyncMock) as m_run, \
         patch("api.pipeline.phases.p06_test.setup_tests") as m_setup2, \
         patch("api.pipeline.phases.p06_test.run_tests", new_callable=AsyncMock) as m_run2:
        pass_result = {"passed": True, "failures": [], "failed_pages": []}
        m_run.return_value = pass_result
        m_run2.return_value = pass_result
        yield m_setup, m_run


# ── Mock Settings ───────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_settings(tmp_path):
    """Override settings for tests — patches at ALL import points."""
    mock_s = MagicMock()
    mock_s.database_url = TEST_DB_URL
    mock_s.gh_token = "ghp_test_token_fake"
    mock_s.github_org = "test-org"
    mock_s.ai_api_url = "https://models.inference.ai.azure.com/chat/completions"
    mock_s.ai_model = "gpt-4o"
    mock_s.telegram_bot_token = ""
    mock_s.telegram_chat_id = ""
    mock_s.base_dir = str(tmp_path / "repos")
    mock_s.main_site_dir = str(tmp_path / "site")
    mock_s.max_council_rounds = 1
    mock_s.max_fix_attempts = 1
    mock_s.host_uid = 1000
    mock_s.host_gid = 1000
    mock_s.firebase_cred_path = ""
    mock_s.firebase_db_url = "https://test.firebaseio.com"
    mock_s.firebase_poll_interval = 60
    mock_s.unsplash_access_key = ""
    mock_s.sender_name = "Ajaya Dahal"
    mock_s.sender_email = "ajayadahal10@gmail.com"
    mock_s.sender_company = "AjayaDesign"
    mock_s.smtp_email = "ajayadahal10@gmail.com"
    mock_s.smtp_app_password = ""
    os.makedirs(mock_s.base_dir, exist_ok=True)

    with patch("api.config.settings", mock_s), \
         patch("api.pipeline.orchestrator.settings", mock_s), \
         patch("api.pipeline.phases.p01_repo.settings", mock_s), \
         patch("api.pipeline.phases.p07_deploy.settings", mock_s):
        yield mock_s
