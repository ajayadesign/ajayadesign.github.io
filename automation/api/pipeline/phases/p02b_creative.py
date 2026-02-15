"""
Phase 2b (sub-phase): Creative Director — Visual Treatment Specification.
Called from Phase 2 (Council) after blueprint is approved.
Produces a creative_spec that guides design system, page generation, and polish.
"""

import logging

from api.services.ai import call_ai, extract_json
from api.pipeline.prompts import CREATIVE_DIRECTOR_SYSTEM, creative_director_create

logger = logging.getLogger(__name__)

# Reasonable default when AI creative direction fails
DEFAULT_CREATIVE_SPEC = {
    "visualConcept": "Clean, modern, professional site with subtle animations",
    "heroTreatment": {
        "type": "parallax-image",
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
        "useNoiseOverlay": True,
        "useGlassMorphism": False,
    },
    "imageSearchTerms": {},
}


async def creative_direction(
    blueprint: dict,
    *,
    scraped_data: dict | None = None,
    log_fn=None,
) -> dict:
    """
    Run the Creative Director agent to produce a visual treatment spec.
    Returns a creative_spec dict used by design, generation, and polish phases.
    """
    _log(log_fn, "🎬 Creative Director deliberating...")

    try:
        raw = await call_ai(
            messages=[
                {"role": "system", "content": CREATIVE_DIRECTOR_SYSTEM},
                {"role": "user", "content": creative_director_create(blueprint, scraped_data)},
            ],
            temperature=0.75,
            max_tokens=3000,
        )

        spec = extract_json(raw)

        # Ensure required keys exist
        spec.setdefault("visualConcept", DEFAULT_CREATIVE_SPEC["visualConcept"])
        spec.setdefault("heroTreatment", DEFAULT_CREATIVE_SPEC["heroTreatment"])
        spec.setdefault("motionDesign", DEFAULT_CREATIVE_SPEC["motionDesign"])
        spec.setdefault("colorEnhancements", DEFAULT_CREATIVE_SPEC["colorEnhancements"])
        spec.setdefault("imageSearchTerms", {})

        _log(log_fn, f"  🎬 Visual concept: {spec['visualConcept']}")
        _log(log_fn, f"  🎬 Hero treatment: {spec['heroTreatment'].get('type', 'N/A')}")

        return spec

    except Exception as e:
        _log(log_fn, f"  ⚠️ Creative Director failed: {e} — using defaults")
        return dict(DEFAULT_CREATIVE_SPEC)


def _log(fn, msg):
    if fn:
        fn(msg)
    logger.info(msg)
