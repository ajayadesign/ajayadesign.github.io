"""
Phase 4: Page Generation — AI builds each page's <main> content.
"""

import os
import re
import logging

from api.services.ai import call_ai, strip_fences
from api.pipeline.prompts import PAGE_BUILDER_SYSTEM, page_builder_create

logger = logging.getLogger(__name__)


async def generate_pages(
    blueprint: dict,
    design_system: dict,
    project_dir: str,
    *,
    log_fn=None,
    event_fn=None,
) -> list[dict]:
    """Generate HTML for each page in the blueprint. Returns page result list."""
    pages = blueprint.get("pages", [])
    results = []

    _log(log_fn, f"📝 Generating {len(pages)} pages")

    for i, page in enumerate(pages):
        filename = "index.html" if page["slug"] == "index" else f"{page['slug']}.html"
        _log(log_fn, f"  [{i + 1}/{len(pages)}] Generating {filename}...")

        if event_fn:
            event_fn("agent", {"page": page["slug"], "action": "generating"})

        try:
            raw = await call_ai(
                messages=[
                    {"role": "system", "content": PAGE_BUILDER_SYSTEM},
                    {"role": "user", "content": page_builder_create(page, design_system, blueprint)},
                ],
                temperature=0.7,
                max_tokens=8000,
            )

            main_content = _extract_main(raw)
            full_html = _wrap_with_design_system(main_content, design_system, blueprint, page)

            filepath = os.path.join(project_dir, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(full_html)

            size = len(full_html.encode("utf-8"))
            _log(log_fn, f"    ✅ {filename} ({size} bytes)")

            results.append({
                "slug": page["slug"],
                "filename": filename,
                "status": "generated",
                "size": size,
                "main_content": main_content,
                "html_content": full_html,
            })

        except Exception as err:
            _log(log_fn, f"    ❌ {filename} FAILED: {err}")

            fallback = _generate_fallback(design_system, blueprint, page)
            filepath = os.path.join(project_dir, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(fallback)

            _log(log_fn, f"    ⚠️ {filename} — using fallback page")
            results.append({
                "slug": page["slug"],
                "filename": filename,
                "status": "fallback",
                "size": len(fallback.encode("utf-8")),
            })

    return results


def _extract_main(raw: str) -> str:
    """Extract <main>...</main> from AI output."""
    main_match = re.search(r"<main[\s>][\s\S]*</main>", raw, re.IGNORECASE)
    if main_match:
        return main_match.group(0)

    if "<section" in raw or "<div" in raw:
        return f"<main>\n{raw}\n</main>"

    return f'<main class="pt-20">\n{raw}\n</main>'


def _wrap_with_design_system(
    main_content: str, ds: dict, blueprint: dict, page_spec: dict
) -> str:
    """Wrap <main> with full HTML shell."""
    title = f"{page_spec.get('title', '')} — {ds.get('siteName', blueprint.get('siteName', ''))}"
    description = (
        page_spec.get("purpose")
        or blueprint.get("tagline")
        or f"{ds.get('siteName', '')} - {page_spec.get('title', '')}"
    )

    return f"""<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
{ds.get('sharedHead', '')}
  <title>{_esc(title)}</title>
  <meta name="description" content="{_esc(description)}">
  <meta property="og:title" content="{_esc(title)}">
  <meta property="og:description" content="{_esc(description)}">
  <meta property="og:type" content="website">
</head>
<body class="{ds.get('bodyClass', '')}">

{ds.get('navHtml', '')}

{main_content}

{ds.get('footerHtml', '')}

{ds.get('mobileMenuJs', '')}
</body>
</html>"""


def _generate_fallback(ds: dict, blueprint: dict, page_spec: dict) -> str:
    """Static fallback page — no AI needed."""
    main_content = f"""<main class="pt-24">
  <section class="min-h-[60vh] flex items-center justify-center px-6">
    <div class="text-center max-w-3xl">
      <h1 class="font-heading text-4xl md:text-6xl font-bold text-textMain mb-6">{_esc(page_spec.get('title', 'Welcome'))}</h1>
      <p class="text-xl text-textMuted mb-8">{_esc(page_spec.get('purpose', blueprint.get('tagline', '')))}</p>
      <a href="/contact.html" class="inline-block px-8 py-3 bg-cta text-white font-body font-bold rounded-lg hover:opacity-90 transition">
        Get in Touch
      </a>
    </div>
  </section>
</main>"""
    return _wrap_with_design_system(main_content, ds, blueprint, page_spec)


def _esc(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _log(fn, msg):
    if fn:
        fn(msg)
    logger.info(msg)
