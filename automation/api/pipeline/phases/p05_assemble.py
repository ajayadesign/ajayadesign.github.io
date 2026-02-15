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
    creative_spec: dict | None = None,
    log_fn=None,
) -> None:
    """Post-process all generated HTML files."""
    _log(log_fn, "📎 Assembly — stitching nav states, sitemap, robots, 404 + enhancements")

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

    # 6. Enhanced features
    _inject_scroll_progress(project_dir, pages, blueprint, log_fn)
    _inject_back_to_top(project_dir, pages, log_fn)
    _generate_favicon(project_dir, blueprint, log_fn)
    _inject_json_ld(project_dir, blueprint, log_fn)
    _inject_performance_hints(project_dir, pages, log_fn)

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


# ── Enhanced Assembly Features ──────────────────────────


def _inject_scroll_progress(project_dir: str, pages: list, blueprint: dict, log_fn) -> None:
    """Add a scroll progress indicator bar to all pages."""
    progress_html = (
        '<div id="scroll-progress" style="position:fixed;top:0;left:0;width:0;height:3px;'
        'background:linear-gradient(90deg,var(--tw-gradient-from,#ED1C24),var(--tw-gradient-to,#00D4FF));'
        'z-index:9999;transition:width 0.1s;"></div>'
    )
    progress_script = """<script>
  window.addEventListener('scroll', () => {
    const h = document.documentElement;
    const pct = (h.scrollTop / (h.scrollHeight - h.clientHeight)) * 100;
    document.getElementById('scroll-progress').style.width = pct + '%';
  });
</script>"""

    for page in pages:
        fname = "index.html" if page["slug"] == "index" else f"{page['slug']}.html"
        fpath = os.path.join(project_dir, fname)
        if not os.path.exists(fpath):
            continue
        with open(fpath, "r", encoding="utf-8") as f:
            html = f.read()
        if "scroll-progress" in html:
            continue
        html = html.replace("<body", f"{progress_html}\n<body", 1)
        html = html.replace("</body>", f"{progress_script}\n</body>", 1)
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(html)

    _log(log_fn, "    ✅ Scroll progress indicator injected")


def _inject_back_to_top(project_dir: str, pages: list, log_fn) -> None:
    """Add a back-to-top floating button."""
    btn_html = (
        '<button id="back-to-top" onclick="window.scrollTo({top:0,behavior:\'smooth\'})" '
        'aria-label="Back to top" '
        'style="position:fixed;bottom:2rem;right:2rem;width:48px;height:48px;border-radius:50%;'
        'background:rgba(255,255,255,0.1);backdrop-filter:blur(8px);border:1px solid rgba(255,255,255,0.15);'
        'color:#fff;font-size:1.2rem;cursor:pointer;opacity:0;transition:opacity 0.3s;z-index:999;">'
        '↑</button>'
    )
    btn_script = """<script>
  window.addEventListener('scroll', () => {
    document.getElementById('back-to-top').style.opacity = window.scrollY > 400 ? '1' : '0';
  });
</script>"""

    for page in pages:
        fname = "index.html" if page["slug"] == "index" else f"{page['slug']}.html"
        fpath = os.path.join(project_dir, fname)
        if not os.path.exists(fpath):
            continue
        with open(fpath, "r", encoding="utf-8") as f:
            html = f.read()
        if "back-to-top" in html:
            continue
        html = html.replace("</body>", f"{btn_html}\n{btn_script}\n</body>", 1)
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(html)

    _log(log_fn, "    ✅ Back-to-top button injected")


def _generate_favicon(project_dir: str, blueprint: dict, log_fn) -> None:
    """Generate a simple SVG favicon from the business name initial."""
    name = blueprint.get("siteName", "S")
    initial = name[0].upper() if name else "S"
    primary = blueprint.get("colorDirection", {}).get("primary", "#ED1C24")

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
        f'<rect width="100" height="100" rx="20" fill="{primary}"/>'
        f'<text x="50" y="68" font-size="56" font-weight="bold" font-family="system-ui" '
        f'fill="white" text-anchor="middle">{initial}</text></svg>'
    )

    favicon_path = os.path.join(project_dir, "favicon.svg")
    with open(favicon_path, "w") as f:
        f.write(svg)

    # Inject favicon link into all HTML files
    html_files = [f for f in os.listdir(project_dir) if f.endswith(".html")]
    for fname in html_files:
        fpath = os.path.join(project_dir, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            html = f.read()
        if "favicon" not in html:
            html = html.replace("</head>", '  <link rel="icon" href="/favicon.svg" type="image/svg+xml">\n</head>', 1)
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(html)

    _log(log_fn, "    ✅ SVG favicon generated")


def _inject_json_ld(project_dir: str, blueprint: dict, log_fn) -> None:
    """Add JSON-LD structured data to index.html."""
    import json as _json

    index_path = os.path.join(project_dir, "index.html")
    if not os.path.exists(index_path):
        return

    site_name = blueprint.get("siteName", "Business")
    niche = blueprint.get("keyDifferentiators", ["Professional services"])
    if isinstance(niche, list):
        niche = ", ".join(niche[:3])

    ld = {
        "@context": "https://schema.org",
        "@type": "LocalBusiness",
        "name": site_name,
        "description": blueprint.get("tagline", f"Professional {niche}"),
    }

    script_tag = f'<script type="application/ld+json">{_json.dumps(ld, indent=2)}</script>'

    with open(index_path, "r", encoding="utf-8") as f:
        html = f.read()
    if "application/ld+json" not in html:
        html = html.replace("</head>", f"  {script_tag}\n</head>", 1)
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(html)

    _log(log_fn, "    ✅ JSON-LD structured data injected")


def _inject_performance_hints(project_dir: str, pages: list, log_fn) -> None:
    """Add lazy loading to images and preconnect hints."""
    for page in pages:
        fname = "index.html" if page["slug"] == "index" else f"{page['slug']}.html"
        fpath = os.path.join(project_dir, fname)
        if not os.path.exists(fpath):
            continue
        with open(fpath, "r", encoding="utf-8") as f:
            html = f.read()

        # Add loading="lazy" to images that don't have it
        html = re.sub(
            r'<img(?![^>]*loading=)([^>]*?)(/?>)',
            r'<img loading="lazy"\1\2',
            html,
        )

        with open(fpath, "w", encoding="utf-8") as f:
            f.write(html)

    _log(log_fn, "    ✅ Performance hints (lazy loading) injected")
