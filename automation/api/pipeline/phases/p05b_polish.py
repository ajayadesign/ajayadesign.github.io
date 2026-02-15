"""
Phase 5b (sub-phase): Visual Polish Pass.
Called from Phase 5 (Assemble) after initial assembly is complete.
AI enhances each page with micro-details that elevate quality.
"""

import os
import re
import logging

from api.services.ai import call_ai, extract_html
from api.pipeline.prompts import POLISH_SYSTEM, polish_enhance

logger = logging.getLogger(__name__)


async def polish_pages(
    blueprint: dict,
    design_system: dict,
    creative_spec: dict | None,
    project_dir: str,
    *,
    log_fn=None,
) -> None:
    """
    Run AI visual polish on each generated page.
    Adds micro-details: section dividers, background variety, shadow depth, etc.
    """
    pages = blueprint.get("pages", [])
    _log(log_fn, f"  ✨ Polish pass on {len(pages)} pages")

    for page in pages:
        slug = page["slug"]
        filename = "index.html" if slug == "index" else f"{slug}.html"
        filepath = os.path.join(project_dir, filename)

        if not os.path.exists(filepath):
            continue

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                full_html = f.read()

            # Extract <main> for polishing
            main_match = re.search(r"<main[\s>][\s\S]*</main>", full_html, re.IGNORECASE)
            if not main_match:
                _log(log_fn, f"    ⚠️ {filename}: no <main> found, skipping polish")
                continue

            main_content = main_match.group(0)

            polished_main = await call_ai(
                messages=[
                    {"role": "system", "content": POLISH_SYSTEM},
                    {"role": "user", "content": polish_enhance(
                        main_content, page, creative_spec or {}
                    )},
                ],
                temperature=0.6,
                max_tokens=8000,
            )

            clean = extract_html(polished_main)

            if "<main" not in clean and "<section" not in clean:
                _log(log_fn, f"    ⚠️ {filename}: polish output invalid, keeping original")
                continue

            if not clean.startswith("<main"):
                clean = f"<main>\n{clean}\n</main>"

            # Replace <main> in full HTML
            new_html = full_html[:main_match.start()] + clean + full_html[main_match.end():]

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_html)

            _log(log_fn, f"    ✨ {filename} polished ({len(new_html)} bytes)")

        except Exception as e:
            _log(log_fn, f"    ⚠️ {filename}: polish failed: {e} — keeping original")


def _log(fn, msg):
    if fn:
        fn(msg)
    logger.info(msg)
