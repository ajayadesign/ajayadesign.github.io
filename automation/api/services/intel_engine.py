"""
Intel Engine — Website Grading & Analysis.

Audits prospect websites using Lighthouse CLI + Playwright screenshots +
heuristic design judge. The killer feature — every audit produces specific,
verifiable data that feeds into personalized outreach emails.

Phase 3 of OUTREACH_AGENT_PLAN.md (§5).
"""

import asyncio
import gzip
import json
import logging
import os
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.database import async_session_factory
from api.models.prospect import Prospect, WebsiteAudit

logger = logging.getLogger("outreach.intel")

# ─── Constants ─────────────────────────────────────────────────────────
DATA_DIR = Path("/data")
SCREENSHOTS_DIR = DATA_DIR / "screenshots"
AUDITS_DIR = DATA_DIR / "audits"

# Ensure dirs exist (Docker volume mount — gracefully skip if no permission)
try:
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    AUDITS_DIR.mkdir(parents=True, exist_ok=True)
except PermissionError:
    pass  # Running outside Docker (e.g. tests) — dirs created on demand

# Timeouts
LIGHTHOUSE_TIMEOUT = 60  # seconds
PLAYWRIGHT_TIMEOUT = 30000  # ms


# ─── Heuristic Design Judge (§5.3) ────────────────────────────────────

def judge_design_era(html: str, tech_stack: list[str], url: str) -> dict:
    """
    Rule-based design era detection. NO AI needed.
    Returns {'score': int, 'era': str, 'sins': list[str]}.
    """
    score = 50  # Start neutral
    sins = []
    html_lower = html.lower()

    # ─── Ancient signals (subtract points) ─────────────────────────
    if "flash" in html_lower or "shockwave" in html_lower:
        score -= 30
        sins.append("Flash/Shockwave detected")

    if "<marquee" in html_lower:
        score -= 20
        sins.append("<marquee> tag detected (prehistoric)")

    if "<blink" in html_lower:
        score -= 20
        sins.append("<blink> tag detected")

    # Table-based layout detection
    table_count = html_lower.count("<table")
    if table_count > 3:
        non_data = sum(1 for _ in re.finditer(r'<table[^>]*(width\s*=\s*"?100%|cellpadding|cellspacing)', html_lower))
        if non_data > 2:
            score -= 20
            sins.append("Table-based layout detected")

    # jQuery version check
    jquery_match = re.search(r'jquery[.-]?(\d+)\.(\d+)', html_lower)
    if jquery_match:
        major = int(jquery_match.group(1))
        if major <= 1:
            score -= 15
            sins.append(f"jQuery {major}.x (ancient)")
        elif major == 2:
            score -= 5
            sins.append("jQuery 2.x (dated)")

    # Bootstrap version
    bs_match = re.search(r'bootstrap[.-]?(\d+)', html_lower)
    if bs_match:
        version = int(bs_match.group(1))
        if version <= 3:
            score -= 10
            sins.append(f"Bootstrap {version} (outdated)")

    # ─── Dated signals ─────────────────────────────────────────────
    # Copyright year in footer
    copyright_match = re.search(r'(?:©|copyright|&copy;)\s*(\d{4})', html_lower)
    if copyright_match:
        year = int(copyright_match.group(1))
        current_year = datetime.now().year
        if year < current_year - 2:
            penalty = min(20, (current_year - year) * 2)
            score -= penalty
            sins.append(f"Copyright stuck on {year}")

    # Viewport meta
    has_viewport = bool(re.search(r'<meta[^>]*name\s*=\s*["\']viewport["\']', html_lower))
    if not has_viewport:
        score -= 15
        sins.append("No viewport meta tag (not mobile-friendly)")

    # Placeholder text
    if "lorem ipsum" in html_lower:
        score -= 20
        sins.append("Lorem ipsum placeholder text found")

    if "under construction" in html_lower:
        score -= 25
        sins.append('"Under construction" text on page')

    if "coming soon" in html_lower and "store" not in html_lower:
        score -= 15
        sins.append('"Coming soon" text detected')

    # Inline styles excessive uso
    inline_count = html_lower.count('style="')
    if inline_count > 50:
        score -= 5
        sins.append(f"Excessive inline styles ({inline_count})")

    # ─── Modern signals (add points) ──────────────────────────────
    if has_viewport:
        score += 10

    # Web fonts
    if re.search(r'fonts\.googleapis\.com|fonts\.gstatic\.com|@font-face', html_lower):
        score += 5

    # CSS Grid or Flexbox
    if re.search(r'display\s*:\s*(grid|flex)', html_lower):
        score += 10
    if re.search(r'grid-template|flex-wrap|flex-direction', html_lower):
        score += 5

    # Lazy loading
    if 'loading="lazy"' in html_lower or "lazyload" in html_lower:
        score += 5

    # Modern JS
    if 'type="module"' in html_lower:
        score += 5

    # Service worker / PWA
    if "serviceWorker" in html or "service-worker" in html_lower:
        score += 5

    # Schema.org / structured data
    if "application/ld+json" in html_lower or "itemscope" in html_lower:
        score += 5

    # SVG usage (modern design indicator)
    if "<svg" in html_lower:
        score += 3

    # Dark mode support
    if "prefers-color-scheme" in html_lower:
        score += 3

    # ─── Era classification ───────────────────────────────────────
    score = max(0, min(100, score))
    if score >= 70:
        era = "2022-modern"
    elif score >= 50:
        era = "2018-recent"
    elif score >= 30:
        era = "2015-dated"
    elif score >= 15:
        era = "2010-ancient"
    else:
        era = "pre-2010-prehistoric"

    return {"score": score, "era": era, "sins": sins}


def extract_seo_signals(html: str, url: str) -> dict:
    """Extract SEO signals from HTML without external tools."""
    html_lower = html.lower()

    # Title
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.DOTALL | re.IGNORECASE)
    has_title = bool(title_match and title_match.group(1).strip())

    # Meta description
    meta_desc = re.search(
        r'<meta[^>]*name\s*=\s*["\']description["\'][^>]*content\s*=\s*["\']([^"\']*)',
        html, re.IGNORECASE,
    )
    has_meta_desc = bool(meta_desc and meta_desc.group(1).strip())

    # H1
    has_h1 = bool(re.search(r"<h1[^>]*>", html_lower))

    # Open Graph
    has_og = bool(re.search(r'<meta[^>]*property\s*=\s*["\']og:', html_lower))

    # Schema / structured data
    has_schema = bool(
        "application/ld+json" in html_lower or "itemscope" in html_lower
    )

    # Sitemap link
    has_sitemap_link = bool(re.search(r'sitemap\.xml', html_lower))

    # Robots meta
    robots_meta = re.search(r'<meta[^>]*name\s*=\s*["\']robots["\']', html_lower)
    noindex = bool(robots_meta and "noindex" in html_lower)

    # Canonical
    has_canonical = bool(re.search(r'<link[^>]*rel\s*=\s*["\']canonical["\']', html_lower))

    # Image alt tags
    total_images = len(re.findall(r"<img", html_lower))
    images_with_alt = len(re.findall(r'<img[^>]*alt\s*=\s*["\'][^"\']+["\']', html_lower))
    alt_coverage = (images_with_alt / total_images * 100) if total_images > 0 else 100

    return {
        "has_title": has_title,
        "has_meta_desc": has_meta_desc,
        "has_h1": has_h1,
        "has_og_tags": has_og,
        "has_schema": has_schema,
        "has_sitemap": has_sitemap_link,
        "has_canonical": has_canonical,
        "is_noindex": noindex,
        "total_images": total_images,
        "images_with_alt": images_with_alt,
        "alt_coverage_pct": round(alt_coverage, 1),
    }


def detect_tech_stack(html: str, headers: dict) -> list[str]:
    """Detect CMS, frameworks, libraries from HTML and headers."""
    stack = []
    html_lower = html.lower()

    # CMS detection
    if "wp-content" in html_lower or "wordpress" in html_lower:
        version = re.search(r'content="WordPress\s+(\d+\.\d+)', html, re.IGNORECASE)
        stack.append(f"WordPress {version.group(1)}" if version else "WordPress")
    if "wix.com" in html_lower or "wixsite" in html_lower:
        stack.append("Wix")
    if "squarespace" in html_lower:
        stack.append("Squarespace")
    if "shopify" in html_lower:
        stack.append("Shopify")
    if "weebly" in html_lower:
        stack.append("Weebly")
    if "godaddy" in html_lower or "secureserver" in html_lower:
        stack.append("GoDaddy Builder")

    # Frameworks
    if "react" in html_lower or "__NEXT_DATA__" in html:
        stack.append("React")
    if "__NUXT__" in html or "nuxt" in html_lower:
        stack.append("Vue/Nuxt")
    if "ng-app" in html_lower or "ng-version" in html_lower:
        stack.append("Angular")

    # CSS frameworks
    if "bootstrap" in html_lower:
        bs_ver = re.search(r'bootstrap[/.-](\d+)', html_lower)
        stack.append(f"Bootstrap {bs_ver.group(1)}" if bs_ver else "Bootstrap")
    if "tailwind" in html_lower:
        stack.append("Tailwind CSS")
    if "foundation" in html_lower and "zurb" in html_lower:
        stack.append("Foundation")

    # JS libraries
    if "jquery" in html_lower:
        jq_ver = re.search(r'jquery[/.-](\d+\.\d+)', html_lower)
        stack.append(f"jQuery {jq_ver.group(1)}" if jq_ver else "jQuery")

    # Analytics
    if "google-analytics" in html_lower or "gtag" in html_lower or "ga.js" in html_lower:
        stack.append("Google Analytics")
    if "facebook.net/en_US/fbevents" in html_lower:
        stack.append("Facebook Pixel")

    # Server headers
    server = headers.get("server", headers.get("Server", ""))
    if server:
        stack.append(f"Server: {server}")
    powered = headers.get("x-powered-by", headers.get("X-Powered-By", ""))
    if powered:
        stack.append(f"Powered: {powered}")

    return stack


def detect_cms_platform(tech_stack: list[str]) -> str:
    """Determine primary CMS from tech stack."""
    for platform in ["WordPress", "Wix", "Squarespace", "Shopify", "Weebly", "GoDaddy Builder"]:
        if any(platform.lower() in t.lower() for t in tech_stack):
            return platform.lower()
    return "custom"


def extract_security_signals(html: str, headers: dict, url: str) -> dict:
    """Check security headers and SSL indicators."""
    security_headers = {}
    header_checks = [
        "content-security-policy", "strict-transport-security",
        "x-frame-options", "x-content-type-options", "x-xss-protection",
        "referrer-policy", "permissions-policy",
    ]
    for h in header_checks:
        val = headers.get(h, headers.get(h.title(), ""))
        if val:
            security_headers[h] = val[:200]  # truncate

    has_hsts = "strict-transport-security" in security_headers
    has_csp = "content-security-policy" in security_headers
    has_xfo = "x-frame-options" in security_headers

    # SSL check (basic — more thorough check could use ssllabs)
    is_https = url.startswith("https://")

    # Grade
    sec_count = len(security_headers)
    if sec_count >= 5 and is_https:
        grade = "A"
    elif sec_count >= 3 and is_https:
        grade = "B"
    elif is_https:
        grade = "C"
    else:
        grade = "F"

    return {
        "ssl_valid": is_https,
        "ssl_grade": grade,
        "security_headers": security_headers,
        "has_hsts": has_hsts,
        "has_csp": has_csp,
    }


def compute_composite_score(lighthouse: dict, design: dict, seo: dict, security: dict) -> dict:
    """
    Calculate composite 0-100 score and sub-scores (§5.2).
    Weights: Speed 25%, Mobile 20%, SEO 20%, Design 15%, Security 10%, A11y 10%.
    """
    # Lighthouse scores (0-100 or None)
    perf = lighthouse.get("performance", 0) or 0
    a11y = lighthouse.get("accessibility", 0) or 0
    bp = lighthouse.get("best_practices", 0) or 0
    seo_score = lighthouse.get("seo", 0) or 0

    # Design score from heuristic judge
    design_score = design.get("score", 50)

    # Security score
    sec_grade = security.get("ssl_grade", "F")
    sec_map = {"A+": 100, "A": 90, "B": 70, "C": 50, "F": 10}
    sec_score = sec_map.get(sec_grade, 30)

    # Mobile = (perf + responsive check) / 2
    mobile_score = int((perf + (80 if design_score > 40 else 30)) / 2)

    # Composite = weighted average
    composite = int(
        perf * 0.25 +
        mobile_score * 0.20 +
        seo_score * 0.20 +
        design_score * 0.15 +
        sec_score * 0.10 +
        a11y * 0.10
    )

    return {
        "composite": max(0, min(100, composite)),
        "speed": perf,
        "mobile": mobile_score,
        "seo": seo_score,
        "design": design_score,
        "security": sec_score,
        "accessibility": a11y,
        "best_practices": bp,
    }


def build_missing_seo_string(seo_signals: dict) -> str:
    """Build human-readable missing SEO features string."""
    missing = []
    if not seo_signals.get("has_title"):
        missing.append("page title")
    if not seo_signals.get("has_meta_desc"):
        missing.append("meta description")
    if not seo_signals.get("has_h1"):
        missing.append("H1 heading")
    if not seo_signals.get("has_og_tags"):
        missing.append("Open Graph tags")
    if not seo_signals.get("has_schema"):
        missing.append("structured data")
    if not seo_signals.get("has_sitemap"):
        missing.append("sitemap")
    return ", ".join(missing) if missing else "none detected"


async def fetch_page(url: str) -> tuple[str, dict, int, float]:
    """
    Fetch a page and return (html, headers, status_code, load_time_ms).
    Uses aiohttp for speed. Playwright is used separately for screenshots.
    """
    import time as _time

    start = _time.monotonic()
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=20),
                allow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 AjayaDesign AuditBot/1.0"},
            ) as resp:
                html = await resp.text(errors="replace")
                elapsed = (_time.monotonic() - start) * 1000
                headers = {k: v for k, v in resp.headers.items()}
                return html, headers, resp.status, elapsed
        except Exception as e:
            elapsed = (_time.monotonic() - start) * 1000
            logger.warning("Failed to fetch %s: %s", url, e)
            return "", {}, 0, elapsed


async def run_lighthouse(url: str, prospect_id: str) -> dict:
    """
    Run Lighthouse CLI if available, or return empty dict.
    Stores raw JSON to filesystem, extracts key metrics.
    """
    try:
        # Check if lighthouse is installed
        check = await asyncio.create_subprocess_exec(
            "which", "lighthouse",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await check.wait()
        if check.returncode != 0:
            logger.info("Lighthouse CLI not found — using heuristic-only mode")
            return {}

        # Create temp output dir
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "report.json")
            proc = await asyncio.create_subprocess_exec(
                "lighthouse", url,
                "--output=json",
                f"--output-path={output_path}",
                "--chrome-flags=--headless --no-sandbox --disable-gpu",
                "--quiet",
                "--only-categories=performance,accessibility,best-practices,seo",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                await asyncio.wait_for(proc.wait(), timeout=LIGHTHOUSE_TIMEOUT)
            except asyncio.TimeoutError:
                proc.kill()
                logger.warning("Lighthouse timed out for %s", url)
                return {}

            if not os.path.exists(output_path):
                return {}

            with open(output_path, "r") as f:
                raw = json.load(f)

            # Store gzipped raw JSON
            audit_dir = AUDITS_DIR / prospect_id
            audit_dir.mkdir(parents=True, exist_ok=True)
            gz_path = audit_dir / "lighthouse.json.gz"
            with gzip.open(str(gz_path), "wt") as gz:
                json.dump(raw, gz)

            # Extract key scores
            cats = raw.get("categories", {})
            audits = raw.get("audits", {})

            return {
                "performance": int((cats.get("performance", {}).get("score", 0) or 0) * 100),
                "accessibility": int((cats.get("accessibility", {}).get("score", 0) or 0) * 100),
                "best_practices": int((cats.get("best-practices", {}).get("score", 0) or 0) * 100),
                "seo": int((cats.get("seo", {}).get("score", 0) or 0) * 100),
                "fcp_ms": _get_audit_ms(audits, "first-contentful-paint"),
                "lcp_ms": _get_audit_ms(audits, "largest-contentful-paint"),
                "cls": _get_audit_value(audits, "cumulative-layout-shift"),
                "tbt_ms": _get_audit_ms(audits, "total-blocking-time"),
                "ttfb_ms": _get_audit_ms(audits, "server-response-time"),
                "page_size_kb": _get_resource_size(audits),
                "request_count": _get_request_count(audits),
                "lighthouse_json_path": str(gz_path),
            }

    except Exception as e:
        logger.exception("Lighthouse error for %s: %s", url, e)
        return {}


def _get_audit_ms(audits: dict, key: str) -> Optional[int]:
    val = audits.get(key, {}).get("numericValue")
    return int(val) if val is not None else None


def _get_audit_value(audits: dict, key: str):
    return audits.get(key, {}).get("numericValue")


def _get_resource_size(audits: dict) -> Optional[int]:
    val = audits.get("total-byte-weight", {}).get("numericValue")
    return int(val / 1024) if val else None


def _get_request_count(audits: dict) -> Optional[int]:
    val = audits.get("network-requests", {}).get("details", {}).get("items")
    return len(val) if val else None


async def take_screenshots(url: str, prospect_id: str) -> dict:
    """
    Take desktop + mobile screenshots using Playwright.
    Returns dict with file paths. Falls back gracefully if Playwright unavailable.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.info("Playwright not installed — skipping screenshots")
        return {}

    screenshot_dir = SCREENSHOTS_DIR / prospect_id
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    paths = {}

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-gpu"],
            )

            # Desktop screenshot (1920x1080)
            page = await browser.new_page(viewport={"width": 1920, "height": 1080})
            try:
                await page.goto(url, timeout=PLAYWRIGHT_TIMEOUT, wait_until="networkidle")
                desktop_path = str(screenshot_dir / "desktop.webp")
                await page.screenshot(path=desktop_path, full_page=True, type="png")
                paths["desktop_screenshot"] = desktop_path
            except Exception as e:
                logger.warning("Desktop screenshot failed for %s: %s", url, e)
            finally:
                await page.close()

            # Mobile screenshot (375x812 — iPhone X)
            page = await browser.new_page(viewport={"width": 375, "height": 812})
            try:
                await page.goto(url, timeout=PLAYWRIGHT_TIMEOUT, wait_until="networkidle")
                mobile_path = str(screenshot_dir / "mobile.webp")
                await page.screenshot(path=mobile_path, full_page=True, type="png")
                paths["mobile_screenshot"] = mobile_path
            except Exception as e:
                logger.warning("Mobile screenshot failed for %s: %s", url, e)
            finally:
                await page.close()

            await browser.close()

    except Exception as e:
        logger.exception("Playwright error for %s: %s", url, e)

    return paths


async def audit_prospect(prospect_id: str, db: Optional[AsyncSession] = None) -> Optional[dict]:
    """
    Full audit pipeline for a single prospect (§5.1).
    Steps: Fetch → Lighthouse → Screenshots → Tech → SEO → Security → Design → Score.
    Returns the audit result dict or None on failure.
    """
    from api.services.telegram_outreach import notify_audit
    from api.services.firebase_summarizer import _safe_set
    from api.services.crawl_engine import calculate_priority_score
    import time as _time

    own_session = db is None
    if own_session:
        session_ctx = async_session_factory()
        db = await session_ctx.__aenter__()

    try:
        prospect = await db.get(Prospect, prospect_id)
        if not prospect or not prospect.website_url:
            logger.warning("Prospect %s has no website URL — skipping audit", prospect_id)
            return None

        url = prospect.website_url
        pid = str(prospect_id)
        logger.info("Auditing %s (%s)", prospect.business_name, url)

        # 1. Fetch page
        html, headers, status_code, load_time_ms = await fetch_page(url)
        if not html:
            # Track fetch attempts via tags
            attempts = (prospect.tags or []).count('audit_fail') + 1
            prospect.tags = (prospect.tags or []) + ['audit_fail']
            if attempts >= 3:
                # Give up auditing — route through recon with website_down template
                logger.warning("Could not fetch %s after %d attempts — routing to recon", url, attempts)
                prospect.notes = f"Website unreachable ({url}) — skipped audit"
                prospect.status = "discovered"  # stays discovered, recon path picks it up via notes
            else:
                logger.info("Fetch failed for %s (attempt %d/3) — will retry next cycle", url, attempts)
            prospect.updated_at = datetime.now(timezone.utc)
            await db.commit()
            return None

        # 2. Lighthouse (if available)
        lighthouse = await run_lighthouse(url, pid)

        # 3. Screenshots (if Playwright available)
        screenshots = await take_screenshots(url, pid)

        # 4. Tech stack detection
        tech_stack = detect_tech_stack(html, headers)
        cms = detect_cms_platform(tech_stack)

        # 5. SEO signals
        seo_signals = extract_seo_signals(html, url)

        # 6. Security
        security = extract_security_signals(html, headers, url)

        # 7. Heuristic design judge
        design = judge_design_era(html, tech_stack, url)

        # 8. Composite score
        scores = compute_composite_score(lighthouse, design, seo_signals, security)

        # Create audit record
        audit = WebsiteAudit(
            id=uuid4(),
            prospect_id=prospect.id,
            url=url,
            # Lighthouse
            perf_score=lighthouse.get("performance") or scores["speed"],
            a11y_score=lighthouse.get("accessibility") or scores["accessibility"],
            bp_score=lighthouse.get("best_practices") or scores["best_practices"],
            seo_score=lighthouse.get("seo") or scores["seo"],
            # Speed
            fcp_ms=lighthouse.get("fcp_ms"),
            lcp_ms=lighthouse.get("lcp_ms") or int(load_time_ms),
            cls=lighthouse.get("cls"),
            tbt_ms=lighthouse.get("tbt_ms"),
            ttfb_ms=lighthouse.get("ttfb_ms"),
            page_size_kb=lighthouse.get("page_size_kb"),
            request_count=lighthouse.get("request_count"),
            # SEO
            has_title=seo_signals.get("has_title", False),
            has_meta_desc=seo_signals.get("has_meta_desc", False),
            has_h1=seo_signals.get("has_h1", False),
            has_og_tags=seo_signals.get("has_og_tags", False),
            has_schema=seo_signals.get("has_schema", False),
            has_sitemap=seo_signals.get("has_sitemap", False),
            mobile_friendly=scores["mobile"] > 50,
            # Tech
            tech_stack=tech_stack,
            cms_platform=cms,
            # Design
            design_era=design["era"],
            design_sins=design["sins"],
            # Security
            ssl_valid=security["ssl_valid"],
            ssl_grade=security["ssl_grade"],
            security_headers=security["security_headers"],
            # Screenshots
            desktop_screenshot=screenshots.get("desktop_screenshot"),
            mobile_screenshot=screenshots.get("mobile_screenshot"),
            # Raw data
            lighthouse_json_path=lighthouse.get("lighthouse_json_path"),
        )
        db.add(audit)

        # Update prospect scores
        prospect.score_speed = scores["speed"]
        prospect.score_seo = scores["seo"]
        prospect.score_design = scores["design"]
        prospect.score_security = scores["security"]
        prospect.score_mobile = scores["mobile"]
        prospect.score_overall = scores["composite"]
        prospect.score_a11y = scores["accessibility"]
        prospect.status = "audited"
        prospect.website_platform = cms
        prospect.audit_date = datetime.now(timezone.utc)
        prospect.screenshot_desktop = screenshots.get("desktop_screenshot")
        prospect.screenshot_mobile = screenshots.get("mobile_screenshot")

        # Recalculate priority
        prospect.priority_score = calculate_priority_score(
            score_overall=scores["composite"],
            google_rating=float(prospect.google_rating) if prospect.google_rating else None,
            google_reviews=prospect.google_reviews,
            distance_miles=float(prospect.distance_miles) if prospect.distance_miles else None,
            business_type=prospect.business_type,
            has_email=bool(prospect.owner_email),
            email_verified=prospect.email_verified or False,
            has_owner_name=bool(prospect.owner_name),
        )

        await db.commit()

        # Notify
        await notify_audit(
            prospect.business_name,
            scores["composite"],
            prospect.website_url,
        )

        # Push to Firebase activity
        await _safe_set(f"outreach/stats/last_audit", {
            "name": prospect.business_name,
            "score": scores["composite"],
            "ts": int(_time.time()),
        })

        result = {
            "prospect_id": pid,
            "scores": scores,
            "design": design,
            "seo": seo_signals,
            "security": security,
            "tech_stack": tech_stack,
            "cms": cms,
            "screenshots": screenshots,
        }

        logger.info("Audit complete: %s → %d/100", prospect.business_name, scores["composite"])
        return result

    except Exception as e:
        logger.exception("Audit failed for prospect %s: %s", prospect_id, e)
        return None

    finally:
        if own_session:
            await session_ctx.__aexit__(None, None, None)


async def batch_audit_prospects(limit: int = 10) -> int:
    """
    Audit up to `limit` prospects that have website but no audit.
    Returns count of successful audits.
    """
    async with async_session_factory() as db:
        from sqlalchemy import select
        result = await db.execute(
            select(Prospect.id)
            .where(
                Prospect.has_website == True,
                Prospect.status == "discovered",
                Prospect.website_url.isnot(None),
            )
            .order_by(Prospect.priority_score.desc())
            .limit(limit)
        )
        prospect_ids = [str(row[0]) for row in result.fetchall()]

    count = 0
    for pid in prospect_ids:
        result = await audit_prospect(pid)
        if result:
            count += 1
        # Rate limit between audits
        await asyncio.sleep(2)

    return count
