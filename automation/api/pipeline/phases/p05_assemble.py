"""
Phase 5: Assembly — Nav stitching, sitemap, robots, 404, link validation.
"""

import os
import re
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


async def assemble(
    blueprint: dict,
    design_system: dict,
    project_dir: str,
    *,
    log_fn=None,
) -> None:
    """Post-process all generated HTML files."""
    _log(log_fn, "📎 Assembly — stitching nav states, sitemap, robots, 404")

    pages = blueprint.get("pages", [])

    # 1. Nav active states
    _stitch_nav_states(project_dir, pages, design_system, log_fn)

    # 2. sitemap.xml
    _generate_sitemap(project_dir, pages, blueprint, log_fn)

    # 3. robots.txt
    _generate_robots(project_dir, blueprint, log_fn)

    # 4. 404.html
    _generate_404(project_dir, design_system, blueprint, log_fn)

    # 5. Cross-link validation
    _validate_links(project_dir, log_fn)

    _log(log_fn, "  ✅ Assembly complete")


def _stitch_nav_states(
    project_dir: str, pages: list, ds: dict, log_fn
) -> None:
    """Replace {{ACTIVE:slug}} placeholders with correct CSS classes."""
    active_class = ds.get("activeNavClass", "text-primary font-bold")
    inactive_class = ds.get("inactiveNavClass", "text-textMuted hover:text-primary transition")

    for page in pages:
        filename = "index.html" if page["slug"] == "index" else f"{page['slug']}.html"
        filepath = os.path.join(project_dir, filename)
        if not os.path.exists(filepath):
            continue

        with open(filepath, "r", encoding="utf-8") as f:
            html = f.read()

        # For this page, its slug gets active class; others get inactive
        for p in pages:
            placeholder = "{{ACTIVE:" + p["slug"] + "}}"
            replacement = active_class if p["slug"] == page["slug"] else inactive_class
            html = html.replace(placeholder, replacement)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)

    _log(log_fn, "    ✅ Nav active states stitched")


def _generate_sitemap(
    project_dir: str, pages: list, blueprint: dict, log_fn
) -> None:
    site_name = blueprint.get("siteName", "site")
    # Infer base URL from potential repo name
    repo_name = re.sub(r"[^a-z0-9-]", "-", site_name.lower()).strip("-")
    base_url = f"https://ajayadesign.github.io/{repo_name}"

    now = datetime.now().strftime("%Y-%m-%d")
    urls = []
    for page in pages:
        loc = f"{base_url}/" if page["slug"] == "index" else f"{base_url}/{page['slug']}.html"
        priority = "1.0" if page["slug"] == "index" else "0.8"
        urls.append(
            f"  <url>\n    <loc>{loc}</loc>\n"
            f"    <lastmod>{now}</lastmod>\n    <priority>{priority}</priority>\n  </url>"
        )

    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n</urlset>\n"
    )

    with open(os.path.join(project_dir, "sitemap.xml"), "w") as f:
        f.write(sitemap)
    _log(log_fn, f"    ✅ sitemap.xml ({len(pages)} URLs)")


def _generate_robots(project_dir: str, blueprint: dict, log_fn) -> None:
    site_name = blueprint.get("siteName", "site")
    repo_name = re.sub(r"[^a-z0-9-]", "-", site_name.lower()).strip("-")

    robots = (
        "User-agent: *\nAllow: /\n\n"
        f"Sitemap: https://ajayadesign.github.io/{repo_name}/sitemap.xml\n"
    )
    with open(os.path.join(project_dir, "robots.txt"), "w") as f:
        f.write(robots)
    _log(log_fn, "    ✅ robots.txt")


def _generate_404(project_dir: str, ds: dict, blueprint: dict, log_fn) -> None:
    site_name = blueprint.get("siteName", "Site")
    html = f"""<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
{ds.get('sharedHead', '')}
  <title>Page Not Found — {site_name}</title>
</head>
<body class="{ds.get('bodyClass', '')}">
{ds.get('navHtml', '')}
<main class="pt-24 min-h-[60vh] flex items-center justify-center px-6">
  <div class="text-center max-w-xl">
    <h1 class="font-heading text-6xl font-bold text-primary mb-4">404</h1>
    <p class="text-xl text-textMuted mb-8">This page doesn't exist.</p>
    <a href="/" class="inline-block px-8 py-3 bg-cta text-white font-bold rounded-lg hover:opacity-90 transition">
      Back to Home
    </a>
  </div>
</main>
{ds.get('footerHtml', '')}
{ds.get('mobileMenuJs', '')}
</body>
</html>"""
    with open(os.path.join(project_dir, "404.html"), "w") as f:
        f.write(html)
    _log(log_fn, "    ✅ 404.html")


def _validate_links(project_dir: str, log_fn) -> None:
    """Scan HTML files for broken internal links and href='#'."""
    html_files = [f for f in os.listdir(project_dir) if f.endswith(".html")]
    issues = 0

    for fname in html_files:
        filepath = os.path.join(project_dir, fname)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # Check for href="#"
        if 'href="#"' in content:
            issues += 1
            _log(log_fn, f"    ⚠️ {fname}: contains href=\"#\"")

        # Check internal links point to existing files
        for match in re.finditer(r'href="(/[\w-]+\.html)"', content):
            target = match.group(1).lstrip("/")
            if not os.path.exists(os.path.join(project_dir, target)):
                issues += 1
                _log(log_fn, f"    ⚠️ {fname}: broken link to {target}")

    if issues == 0:
        _log(log_fn, "    ✅ Link validation passed")
    else:
        _log(log_fn, f"    ⚠️ {issues} link issue(s) found")


def _log(fn, msg):
    if fn:
        fn(msg)
    logger.info(msg)
