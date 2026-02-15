"""
Phase 2: AI Council — Strategist ↔ Critic Debate.
"""

import re
import json
import logging

from api.services.ai import call_ai, extract_json
from api.pipeline.prompts import (
    STRATEGIST_SYSTEM,
    strategist_propose,
    strategist_revise,
    CRITIC_SYSTEM,
    critic_review,
)

logger = logging.getLogger(__name__)

# Safe defaults if AI omits fields
DEFAULT_COLORS = {
    "primary": "#ED1C24",
    "accent": "#00D4FF",
    "surface": "#0A0A0F",
    "surfaceAlt": "#111118",
    "textMain": "#E5E7EB",
    "textMuted": "#9CA3AF",
}

DEFAULT_TYPOGRAPHY = {"headings": "JetBrains Mono", "body": "Inter"}


async def ai_council(
    business_name: str,
    niche: str,
    goals: str,
    email: str,
    max_rounds: int = 2,
    *,
    extra_context: dict | None = None,
    log_fn=None,
    event_fn=None,
) -> dict:
    """Run Strategist ↔ Critic debate. Returns {blueprint, transcript}."""
    blueprint = None
    critique = None
    transcript = []

    _log(log_fn, "🧠 AI Council convened — Strategist vs. Critic")

    for round_num in range(1, max_rounds + 1):
        # ── Strategist proposes / revises ──
        action = "proposing" if round_num == 1 else "revising"
        _log(log_fn, f"  [Round {round_num}/{max_rounds}] 🧠 Strategist {action}...")

        if event_fn:
            event_fn("council", {
                "round": round_num,
                "speaker": "strategist",
                "action": action,
            })

        user_msg = (
            strategist_propose(business_name, niche, goals, email, extra_context=extra_context)
            if round_num == 1
            else strategist_revise(blueprint, critique)
        )

        raw = await call_ai(
            messages=[
                {"role": "system", "content": STRATEGIST_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.7,
            max_tokens=4000,
        )

        blueprint = extract_json(raw)

        # Validate
        if not blueprint.get("pages") or not isinstance(blueprint["pages"], list):
            raise ValueError("Strategist produced invalid blueprint — no pages array")

        for page in blueprint["pages"]:
            if not page.get("slug"):
                page["slug"] = re.sub(
                    r"[^a-z0-9-]", "-", page.get("title", "page").lower()
                ).strip("-")

        page_list = ", ".join(p.get("navLabel", p["title"]) for p in blueprint["pages"])
        _log(log_fn, f"  🧠 Strategist proposed {len(blueprint['pages'])} pages: {page_list}")

        transcript.append({
            "round": round_num,
            "speaker": "strategist",
            "summary": f"Proposed {len(blueprint['pages'])}-page site: {page_list}",
        })

        # ── Critic reviews ──
        _log(log_fn, f"  [Round {round_num}/{max_rounds}] 🔍 Critic reviewing...")

        raw_critique = await call_ai(
            messages=[
                {"role": "system", "content": CRITIC_SYSTEM},
                {"role": "user", "content": critic_review(blueprint)},
            ],
            temperature=0.4,
            max_tokens=3000,
        )

        critique = extract_json(raw_critique)
        high = sum(1 for c in critique.get("critiques", []) if c.get("severity") == "high")
        score = critique.get("score", "?")

        _log(
            log_fn,
            f"  🔍 Critic: score={score}/10, {high} high issues. "
            f"Approved: {'YES ✅' if critique.get('approved') else 'NO ❌'}",
        )

        transcript.append({
            "round": round_num,
            "speaker": "critic",
            "summary": critique.get("summary", f"Score: {score}/10"),
        })

        if critique.get("approved"):
            _log(log_fn, f"  ✅ Council approved blueprint after {round_num} round(s)")
            break

        if round_num == max_rounds:
            _log(log_fn, "  ⚠️ Max council rounds reached — proceeding with current blueprint")

    # ── Post-process ──
    _sanitize_blueprint(blueprint, business_name, niche)

    _log(
        log_fn,
        f"  📋 Final blueprint: {len(blueprint['pages'])} pages, "
        f"voice=\"{blueprint.get('brandVoice', 'N/A')}\", "
        f"colors: {blueprint.get('colorDirection', {}).get('primary', '?')}"
        f"/{blueprint.get('colorDirection', {}).get('accent', '?')}",
    )

    return {"blueprint": blueprint, "transcript": transcript}


def _sanitize_blueprint(blueprint: dict, business_name: str, niche: str) -> None:
    """Strip rationale text from colors/typography, set safe defaults."""
    # Sanitize colors
    if blueprint.get("colorDirection"):
        for k, v in list(blueprint["colorDirection"].items()):
            match = re.search(r"#[0-9A-Fa-f]{3,8}", str(v))
            blueprint["colorDirection"][k] = match.group(0) if match else DEFAULT_COLORS.get(k, "#888888")
    else:
        blueprint["colorDirection"] = dict(DEFAULT_COLORS)

    # Sanitize typography
    if blueprint.get("typography"):
        for k, v in list(blueprint["typography"].items()):
            blueprint["typography"][k] = str(v).split("—")[0].split(" - ")[0].strip()
    else:
        blueprint["typography"] = dict(DEFAULT_TYPOGRAPHY)

    # Required fields
    blueprint.setdefault("siteName", business_name)
    blueprint.setdefault("tagline", f"Professional {niche} services")
    blueprint.setdefault("brandVoice", "professional, clean, modern")


def _log(fn, msg):
    if fn:
        fn(msg)
    logger.info(msg)
