"""
Phase 6: Quality Gate — Playwright test + AI fix loop.
"""

import os
import re
import logging

from api.services.ai import call_ai, extract_html
from api.services.test_runner import setup_tests, run_tests
from api.pipeline.prompts import FIXER_SYSTEM, fixer_fix

logger = logging.getLogger(__name__)


async def quality_gate(
    blueprint: dict,
    design_system: dict,
    project_dir: str,
    max_fix: int = 3,
    *,
    log_fn=None,
    event_fn=None,
) -> dict:
    """Run tests, auto-fix failures with AI, retry. Returns result dict."""
    pages = blueprint.get("pages", [])

    _log(log_fn, "🧪 Quality Gate — setting up tests")
    setup_tests(project_dir, [{"slug": p["slug"], "title": p.get("title", p["slug"])} for p in pages])
    _log(log_fn, f"  Test files created for {len(pages)} pages + integration")

    attempt = 1
    while attempt <= max_fix:
        _log(log_fn, f"  [Attempt {attempt}/{max_fix}] ▶ Running full test suite...")

        if event_fn:
            event_fn("test", {"action": "run", "attempt": attempt})

        test_result = await run_tests(project_dir)

        if test_result["passed"]:
            _log(log_fn, f"  ✅ All tests passed on attempt {attempt}!")
            if event_fn:
                event_fn("test", {"action": "pass", "attempt": attempt})
            return {"passed": True, "attempts": attempt}

        fail_count = len(test_result["failures"])
        _log(log_fn, f"  ❌ Tests failed ({fail_count} issue(s)) on attempt {attempt}")

        if event_fn:
            event_fn("test", {"action": "fail", "attempt": attempt, "failures": fail_count})

        if attempt >= max_fix:
            _log(log_fn, f"  ❌ TESTS FAILED after {max_fix} attempts — proceeding anyway")
            return {
                "passed": False,
                "attempts": attempt,
                "failures": test_result["failures"],
            }

        # ── AI auto-fix ──
        _log(log_fn, f"  🔧 Attempting AI auto-fix (attempt {attempt + 1})...")

        failed_pages = test_result.get("failed_pages", [])
        targets = failed_pages if failed_pages else [p["slug"] for p in pages]

        for slug in targets:
            await _fix_page(slug, project_dir, test_result["failures"], design_system, blueprint, log_fn)

        attempt += 1

    return {"passed": False, "attempts": attempt}


async def _fix_page(
    slug: str,
    project_dir: str,
    failures: list[str],
    ds: dict,
    blueprint: dict,
    log_fn,
) -> None:
    """Use AI to fix a single page's test failures."""
    filename = "index.html" if slug == "index" else f"{slug}.html"
    filepath = os.path.join(project_dir, filename)

    if not os.path.exists(filepath):
        return

    _log(log_fn, f"    🔧 Fixing {filename}...")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            full_html = f.read()

        main_match = re.search(r"<main[\s>][\s\S]*</main>", full_html, re.IGNORECASE)
        if not main_match:
            _log(log_fn, f"    ⚠️ Could not extract <main> from {filename}")
            return

        main_content = main_match.group(0)
        error_summary = "\n".join(failures[:15])

        fixed_main = await call_ai(
            messages=[
                {"role": "system", "content": FIXER_SYSTEM},
                {"role": "user", "content": fixer_fix(main_content, error_summary)},
            ],
            temperature=0.3,
            max_tokens=8000,
            retries=4,
        )

        clean_fixed = extract_html(fixed_main)
        if "<main" not in clean_fixed and "<section" not in clean_fixed:
            _log(log_fn, f"    ⚠️ AI fix for {filename} invalid, keeping original")
            return

        if not clean_fixed.startswith("<main"):
            clean_fixed = f"<main>\n{clean_fixed}\n</main>"

        # Rebuild page preserving head/nav/footer
        rebuilt = _rebuild_page(clean_fixed, ds, blueprint, slug, full_html)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(rebuilt)

        _log(log_fn, f"    ✅ {filename} fixed ({len(rebuilt)} bytes)")

    except Exception as err:
        _log(log_fn, f"    ⚠️ Fix failed for {filename}: {err}")


def _rebuild_page(
    new_main: str, ds: dict, blueprint: dict, slug: str, original_html: str
) -> str:
    """Reconstruct full page with new <main>, preserving head/nav/footer."""
    # Keep original head
    head_match = re.search(r"<head>([\s\S]*?)</head>", original_html, re.IGNORECASE)
    head = head_match.group(1) if head_match else ds.get("sharedHead", "")

    # Keep original nav (has correct active states)
    nav_match = re.search(r"<nav[\s>][\s\S]*?</nav>", original_html, re.IGNORECASE)
    nav = nav_match.group(0) if nav_match else ds.get("navHtml", "")

    # Keep original footer
    footer_match = re.search(r"<footer[\s>][\s\S]*?</footer>", original_html, re.IGNORECASE)
    footer = footer_match.group(0) if footer_match else ds.get("footerHtml", "")

    # Preserve inline/linked scripts from end of original <body>
    # (AOS.init, scroll progress, back-to-top, etc. injected by Phase 5)
    body_close = re.search(r"</footer>([\s\S]*?)</body>", original_html, re.IGNORECASE)
    tail_scripts = ""
    if body_close:
        tail_raw = body_close.group(1).strip()
        # Extract all <script> blocks from the tail
        scripts = re.findall(r"<script[\s>][\s\S]*?</script>", tail_raw, re.IGNORECASE)
        if scripts:
            tail_scripts = "\n".join(scripts)

    mobile_menu = ds.get('mobileMenuJs', '')

    return f"""<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
{head}
</head>
<body class="{ds.get('bodyClass', '')}">
{nav}
{new_main}
{footer}
{mobile_menu}
{tail_scripts}
</body>
</html>"""


def _log(fn, msg):
    if fn:
        fn(msg)
    logger.info(msg)
