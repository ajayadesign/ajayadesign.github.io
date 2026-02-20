"""
Template Engine — Jinja2-powered email composition.

Composes personalized outreach emails by injecting real audit data into
hand-crafted templates. No AI API calls — every email is unique because
the DATA is unique, not the phrasing.

Phase 5 of OUTREACH_AGENT_PLAN.md (§7).
"""

import logging
import os
import re
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from api.database import async_session_factory
from api.config import settings
from api.models.prospect import Prospect, WebsiteAudit, OutreachEmail

logger = logging.getLogger("outreach.template")

# ─── Template directory ────────────────────────────────────────────────
TEMPLATE_DIR = Path(__file__).parent.parent / "templates" / "email"


def _get_jinja_env() -> Environment:
    """Create a Jinja2 environment with the email templates directory."""
    return Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


# ─── Sequence Step → Template Mapping ─────────────────────────────────

SEQUENCE_TEMPLATES = {
    1: {"template": "initial_audit.html", "subject": "question about {{business_name}}'s website"},
    2: {"template": "follow_up_value.html", "subject": "re: {{business_name}} website"},
    3: {"template": "follow_up_social.html", "subject": "one more thing — {{business_name}}"},
    4: {"template": "breakup.html", "subject": "closing the loop"},
    5: {"template": "resurrection.html", "subject": "{{business_name}} — quick check-in"},
}

# Alternate subjects for businesses with NO website
NO_WEBSITE_SUBJECTS = {
    1: "{{business_name}} — quick question",
}

# Subject for businesses whose website is DOWN
WEBSITE_DOWN_SUBJECTS = {
    1: "heads up about {{business_name}}'s website",
}

# Days between sequence steps
SEQUENCE_TIMING = {
    1: 0,    # Immediate
    2: 3,    # Day 3
    3: 7,    # Day 7
    4: 14,   # Day 14
    5: 90,   # Day 90 (resurrection)
}

# Industry-specific mobile search percentages
INDUSTRY_MOBILE_PCT = {
    "restaurant": 78,
    "bakery": 72,
    "cafe": 71,
    "dental_office": 65,
    "law_firm": 58,
    "plumber": 82,
    "electrician": 79,
    "roofing": 76,
    "beauty_salon": 74,
    "real_estate": 63,
    "veterinarian": 68,
    "gym": 70,
    "photographer": 61,
    "auto_repair": 75,
    "locksmith": 85,
    "moving_company": 67,
    "pet_store": 66,
    "florist": 69,
}


# ─── Helper Functions ─────────────────────────────────────────────────

def score_to_grade(score: Optional[int]) -> str:
    """Convert 0-100 score to letter grade."""
    if score is None:
        return "N/A"
    if score >= 90:
        return "A"
    if score >= 70:
        return "B"
    if score >= 50:
        return "C"
    if score >= 30:
        return "D"
    return "F"


def estimate_bounce_rate(load_time_ms: Optional[int]) -> str:
    """Estimate bounce rate from load time (Google data)."""
    if not load_time_ms:
        return "unknown"
    seconds = load_time_ms / 1000
    if seconds <= 1:
        return "9%"
    if seconds <= 3:
        return "32%"
    if seconds <= 5:
        return "53%"
    if seconds <= 7:
        return "73%"
    return "87%"


def estimate_monthly_loss(business_type: str, score: Optional[int]) -> str:
    """Estimate revenue loss based on industry and score."""
    base_revenue = {
        "restaurant": 3500, "dental_office": 8000, "law_firm": 12000,
        "plumber": 4000, "electrician": 3800, "roofing": 6000,
        "beauty_salon": 2500, "real_estate": 7000, "veterinarian": 5000,
        "auto_repair": 3000, "bakery": 2000, "cafe": 1800,
    }
    base = base_revenue.get(business_type, 3000)
    if not score or score >= 80:
        return "minimal"
    loss_pct = max(5, min(60, 100 - score)) / 100
    loss = int(base * loss_pct)
    return f"${loss:,}/month"


def build_missing_seo_string(audit: WebsiteAudit) -> str:
    """Build human-readable list of missing SEO features."""
    missing = []
    if not audit.has_title:
        missing.append("page title")
    if not audit.has_meta_desc:
        missing.append("meta description")
    if not audit.has_h1:
        missing.append("H1 heading")
    if not audit.has_og_tags:
        missing.append("Open Graph tags")
    if not audit.has_schema:
        missing.append("structured data")
    if not audit.has_sitemap:
        missing.append("sitemap")

    return ", ".join(missing) if missing else "all basics covered"


def get_top_competitor(prospect: Prospect) -> dict:
    """Get the highest-scoring competitor from prospect data."""
    competitors = prospect.competitors or []
    if not competitors:
        return {"name": "a competitor nearby", "score": 75}
    sorted_c = sorted(competitors, key=lambda c: c.get("score", 0), reverse=True)
    return sorted_c[0]


def simple_render(template_str: str, variables: dict) -> str:
    """
    Simple {{variable}} replacement with {{#if var}}...{{/if}} conditionals.
    Used for subject lines (not full Jinja2).
    """
    # Handle conditionals first
    def replace_conditional(match):
        var_name = match.group(1)
        content = match.group(2)
        return content if variables.get(var_name) else ""

    result = re.sub(
        r"\{\{#if (\w+)\}\}(.*?)\{\{/if\}\}",
        replace_conditional,
        template_str,
        flags=re.DOTALL,
    )

    # Replace variables
    for key, val in variables.items():
        result = result.replace("{{" + key + "}}", str(val) if val is not None else "")

    return result


# ─── Main Compose Function ────────────────────────────────────────────

async def compose_email(
    prospect_id: str,
    sequence_step: int = 1,
) -> Optional[dict]:
    """
    Compose a fully personalized email for a prospect at a given sequence step.
    Returns dict with subject, body_html, body_text, variables, template_id.
    """
    async with async_session_factory() as db:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        prospect = await db.get(Prospect, prospect_id)
        if not prospect:
            logger.warning("compose_email: prospect %s not found", prospect_id)
            return None

        # Get latest audit
        result = await db.execute(
            select(WebsiteAudit)
            .where(WebsiteAudit.prospect_id == prospect.id)
            .order_by(WebsiteAudit.audited_at.desc())
            .limit(1)
        )
        audit = result.scalar_one_or_none()

        # Template configuration
        step_config = SEQUENCE_TEMPLATES.get(sequence_step)
        if not step_config:
            logger.warning("No template for sequence step %d", sequence_step)
            return None

        # Build variable map from real data
        variables = _build_variables(prospect, audit)

        # Render subject line — use no-website variant if applicable
        subject_template = step_config["subject"]
        template_name = step_config["template"]

        # Website is DOWN (has URL but unreachable) → special template
        if prospect.has_website and prospect.website_url and not audit and sequence_step == 1:
            if prospect.notes and "unreachable" in prospect.notes.lower():
                subject_template = WEBSITE_DOWN_SUBJECTS.get(sequence_step, subject_template)
                template_name = "website_down.html"
        # No website at all → different template
        elif not prospect.has_website and sequence_step == 1:
            subject_template = NO_WEBSITE_SUBJECTS.get(sequence_step, subject_template)
            template_name = "no_website_intro.html"
        subject = simple_render(subject_template, variables)

        # Render HTML body using Jinja2
        try:
            env = _get_jinja_env()
            template = env.get_template(template_name)
            body_html = template.render(**variables)
        except Exception as e:
            logger.error("Template render error: %s", e)
            return None

        # Plain text version (strip HTML)
        body_text = re.sub(r"<style[^>]*>.*?</style>", "", body_html, flags=re.DOTALL)
        body_text = re.sub(r"<[^>]+>", "", body_text)
        body_text = re.sub(r"\n\s*\n", "\n\n", body_text).strip()

        return {
            "subject": subject,
            "body_html": body_html,
            "body_text": body_text,
            "variables": variables,
            "template_id": step_config["template"],
            "sequence_step": sequence_step,
        }


# ── Positive-match first names list ─────────────────────────────────────
# Instead of blacklisting bad words (whack-a-mole), we only accept names
# whose first word appears in a curated ~2 000-name set of common US first
# names.  Unknown first words → "Hi there,".
_COMMON_FIRST_NAMES: set[str] = set()

def _load_first_names() -> set[str]:
    """Load common_first_names.txt once at import time."""
    names_path = Path(__file__).resolve().parent.parent / "data" / "common_first_names.txt"
    names: set[str] = set()
    try:
        with open(names_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    names.add(line.lower())
    except FileNotFoundError:
        log.warning("common_first_names.txt not found at %s — all salutations will be generic", names_path)
    return names

_COMMON_FIRST_NAMES = _load_first_names()

def _is_real_person_name(name: str) -> bool:
    """Check if a name looks like an actual person's name using positive matching.

    Returns True only if the first word of the name is in our curated
    common-first-names list.  This catches all garbage (business names,
    scraped HTML, articles like 'The', etc.) without maintaining a blacklist.
    """
    if not name or name.lower() == "there":
        return False
    words = name.split()
    # Must be 2-4 words (first + last, maybe middle)
    if len(words) < 2 or len(words) > 4:
        return False
    first_word = words[0]
    # Must start with uppercase letter
    if not first_word[0].isupper():
        return False
    # The key check: first word must be a known first name
    if first_word.lower() not in _COMMON_FIRST_NAMES:
        return False
    # Each word should be 2+ chars and start with a letter
    if not all(len(w) >= 2 and w[0].isalpha() for w in words):
        return False
    return True


def _build_variables(prospect: Prospect, audit: Optional[WebsiteAudit]) -> dict:
    """Build the complete template variable map from real prospect + audit data."""
    raw_name = prospect.owner_name or ""
    # Only use the name if it looks like a real person's name
    if _is_real_person_name(raw_name):
        owner_name = raw_name
        first_name = raw_name.split()[0]
    else:
        owner_name = "there"
        first_name = "there"

    variables = {
        # From Google Maps
        "business_name": prospect.business_name,
        "owner_first_name": first_name,
        "owner_name": owner_name,
        "city": prospect.city,
        "state": prospect.state or "TX",
        "business_type": (prospect.business_type or "business").replace("_", " "),
        "google_rating": str(prospect.google_rating or "N/A"),
        "google_reviews": str(prospect.google_reviews or "0"),

        # Website (for website_down template)
        "website_url": prospect.website_url or "",

        # Industry data
        "industry_mobile_pct": str(
            INDUSTRY_MOBILE_PCT.get(prospect.business_type, 70)
        ),

        # Tracking
        "sender_name": settings.sender_name or "Ajaya Dahal",
        "sender_company": "AjayaDesign",
        "sender_location": "Manor, TX",
        "sender_url": "ajayadesign.github.io",

        # Resurrection
        "months_later": "a few months",
    }

    # Audit-specific variables (only if audit exists)
    if audit:
        # Use composite/overall score if perf_score is missing (for subject line)
        effective_speed = audit.perf_score or prospect.score_overall or prospect.score_speed
        lcp_ms = audit.lcp_ms or 3000
        load_time_s = lcp_ms / 1000
        mobile_val = prospect.score_mobile or audit.a11y_score
        missing_seo = build_missing_seo_string(audit)

        # Threshold flags for green/red conditional display
        speed_good = load_time_s < 2.5         # Google recommends < 2s, give slight buffer
        mobile_good = (mobile_val or 0) >= 70  # 70+ is respectable
        seo_good = missing_seo == "all basics covered"
        ssl_good = bool(audit.ssl_valid)

        variables.update({
            "speed_score": str(effective_speed) if effective_speed else "low",
            "speed_grade": score_to_grade(effective_speed),
            "load_time": f"{load_time_s:.1f} seconds",
            "mobile_score": str(mobile_val or "N/A"),
            "seo_score": str(audit.seo_score or "N/A"),
            "platform": audit.cms_platform or "custom-built",
            "ssl_status": "valid" if audit.ssl_valid else "expired/missing",
            "design_era": audit.design_era or "unknown",
            "page_size": f"{(audit.page_size_kb or 0) / 1024:.1f}MB",
            "missing_seo": missing_seo,
            "bounce_rate_est": estimate_bounce_rate(audit.lcp_ms),
            "estimated_loss": estimate_monthly_loss(
                prospect.business_type or "business",
                audit.perf_score,
            ),

            # Conditional flags for template red/green dots
            "speed_good": speed_good,
            "mobile_good": mobile_good,
            "seo_good": seo_good,
            "ssl_good": ssl_good,
            "ssl_expired": not audit.ssl_valid,
            "has_broken_things": bool(audit.design_sins),
            "worst_broken_thing": (audit.design_sins or [""])[0],
            "has_audit": True,
            # Overall: any metric bad?
            "any_bad": not speed_good or not mobile_good or not seo_good,
            "all_good": speed_good and mobile_good and seo_good and ssl_good,
        })
    else:
        variables.update({
            "speed_score": "N/A",
            "speed_grade": "N/A",
            "load_time": "unknown",
            "mobile_score": "N/A",
            "seo_score": "N/A",
            "platform": "unknown",
            "ssl_status": "unknown",
            "design_era": "unknown",
            "page_size": "unknown",
            "missing_seo": "could not be determined",
            "bounce_rate_est": "unknown",
            "estimated_loss": "unknown",
            "ssl_expired": False,
            "has_broken_things": False,
            "worst_broken_thing": "",
            "has_audit": False,
        })

    # No-website variant
    if not prospect.has_website:
        variables["no_website"] = True
        variables["platform"] = "none"
    else:
        variables["no_website"] = False

    return variables


async def preview_email(prospect_id: str, sequence_step: int = 1) -> Optional[dict]:
    """
    Preview an email without creating an OutreachEmail record.
    Used by the dashboard for approval workflow.
    """
    return await compose_email(prospect_id, sequence_step)
