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

    # 1b. Rewrite root-relative links to relative (subdirectory hosting)
    _rewrite_links_for_subdirectory(project_dir, log_fn)

    # 2. sitemap.xml
    _generate_sitemap(project_dir, pages, blueprint, log_fn)

    # 3. robots.txt
    _generate_robots(project_dir, blueprint, log_fn)

    # 4. 404.html
    _generate_404(project_dir, design_system, blueprint, log_fn)

    # 5. Cross-link validation
    _validate_links(project_dir, log_fn)

    # 6. Fix broken local image paths → placeholder
    _fix_local_image_paths(project_dir, log_fn)

    # 7. Enhanced features
    _inject_scroll_progress(project_dir, pages, blueprint, log_fn)
    _inject_back_to_top(project_dir, pages, log_fn)
    _generate_favicon(project_dir, blueprint, log_fn)
    _inject_json_ld(project_dir, blueprint, log_fn)
    _inject_performance_hints(project_dir, pages, log_fn)

    # 8. Add JS error guard for mobileMenuJs null refs
    _inject_js_safety_guard(project_dir, pages, log_fn)

    _log(log_fn, "  ✅ Assembly complete")


def _rewrite_links_for_subdirectory(project_dir: str, log_fn) -> None:
    """Convert root-relative links to relative links for GitHub Pages subdirectory hosting.

    Root-relative links like /menu.html resolve to ajayadesign.github.io/menu.html
    instead of ajayadesign.github.io/repo-name/menu.html.  By converting them to
    relative paths (menu.html), the browser resolves them correctly regardless of
    which subdirectory the site is served from.

    Conversions:
      href="/"              → href="index.html"
      href="/page.html"     → href="page.html"
      href="/page"          → href="page.html"       (adds missing .html)
      src="/favicon.svg"    → src="favicon.svg"
      src="/images/foo.jpg" → src="images/foo.jpg"   (drops leading /)
    """
    html_files = [f for f in os.listdir(project_dir) if f.endswith(".html")]
    total_rewrites = 0

    for fname in html_files:
        fpath = os.path.join(project_dir, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            html = f.read()

        original = html
        count = 0

        # 1. href="/" → href="index.html"
        html, n = re.subn(r'(href=")/"', r'\1index.html"', html)
        count += n

        # 2. href="/page.html" → href="page.html"
        html, n = re.subn(r'(href=")/([A-Za-z0-9][\w-]*\.html)"', r'\1\2"', html)
        count += n

        # 3. href="/page" (no extension, no . in path) → href="page.html"
        #    But skip external links, anchor links, javascript:, mailto:, tel:, https:, http:
        def _fix_bare_root_link(m):
            attr = m.group(1)   # href=" or src="
            slug = m.group(2)   # page name without extension
            # Only rewrite href (not src) for bare page links
            if attr.startswith('href'):
                return f'{attr}{slug}.html"'
            return m.group(0)

        html, n = re.subn(
            r'(href=")/([A-Za-z0-9][\w-]*)"(?![./])',
            _fix_bare_root_link,
            html,
        )
        count += n

        # 4. src="/anything" → src="anything" (images, scripts, etc.)
        html, n = re.subn(r'((?:src|href)=")/(?=[A-Za-z0-9])', r'\1', html)
        count += n

        if html != original:
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(html)
            total_rewrites += count

    if total_rewrites:
        _log(log_fn, f"    ✅ Rewrote {total_rewrites} root-relative links to relative")
    else:
        _log(log_fn, "    ✅ No root-relative links to rewrite")


def _fix_local_image_paths(project_dir: str, log_fn) -> None:
    """Replace local/non-existent image src paths with placehold.co fallbacks.

    AI sometimes generates src="/images/foo.jpg" or src="images/foo.jpg" paths
    that don't exist. Replace them with visually appropriate placeholders.
    """
    html_files = [f for f in os.listdir(project_dir) if f.endswith(".html")]
    total = 0

    def _placeholder(m):
        src = m.group(2)
        # Skip external URLs (https://, http://, data:, //)
        if re.match(r'(https?://|data:|//)', src):
            return m.group(0)
        # Skip files that actually exist
        clean = src.lstrip("/")
        if os.path.exists(os.path.join(project_dir, clean)):
            return m.group(0)
        # Extract a label from the path for the placeholder
        label = os.path.splitext(os.path.basename(clean))[0].replace("-", "+").replace("_", "+")
        return f'{m.group(1)}https://placehold.co/800x600/1a1a2e/ffffff?text={label}"'

    for fname in html_files:
        fpath = os.path.join(project_dir, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            html = f.read()
        original = html
        html = re.sub(r'(src=")([^"]+)"', _placeholder, html)
        if html != original:
            n = sum(1 for a, b in zip(original.split('src="'), html.split('src="')) if a != b)
            total += n
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(html)

    if total:
        _log(log_fn, f"    ✅ Replaced {total} broken local image paths with placeholders")
    else:
        _log(log_fn, "    ✅ No broken image paths to fix")


def _inject_js_safety_guard(project_dir: str, pages: list, log_fn) -> None:
    """Wrap inline <script> blocks with try/catch to prevent null-ref crashes.

    AI-generated mobileMenuJs often references elements by ID/class that may
    not exist, causing 'Cannot read properties of null' errors.
    """
    html_files = [f for f in os.listdir(project_dir) if f.endswith(".html")]
    guard_marker = "/* js-safety-guard */"
    total = 0

    for fname in html_files:
        fpath = os.path.join(project_dir, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            html = f.read()
        if guard_marker in html:
            continue

        # Find inline scripts that aren't libraries / AOS / tailwind / JSON-LD
        def _wrap_script(m):
            nonlocal total
            script_tag = m.group(0)
            content = m.group(1)
            # Skip well-known safe scripts
            if any(kw in content for kw in [
                "tailwind.config", "AOS.init", "application/ld+json",
                "scroll-progress", "back-to-top", guard_marker,
            ]):
                return script_tag
            # Wrap in try-catch
            total += 1
            return f"<script>{guard_marker}\ntry {{\n{content}\n}} catch(e) {{ console.warn('Script error:', e); }}\n</script>"

        html = re.sub(r"<script>([^<]*(?:(?!</script>)<[^<]*)*)</script>", _wrap_script, html, flags=re.DOTALL)
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(html)

    if total:
        _log(log_fn, f"    ✅ Wrapped {total} inline scripts with safety guards")
    else:
        _log(log_fn, "    ✅ No scripts needed safety guards")


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
    <a href="index.html" class="inline-block px-8 py-3 bg-cta text-white font-bold rounded-lg hover:opacity-90 transition">
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

        # Flag any remaining root-relative links (should all be relative by now)
        for match in re.finditer(r'href="(/[\w-]+(?:\.html)?)"', content):
            issues += 1
            _log(log_fn, f"    ⚠️ {fname}: root-relative link {match.group(1)} — should be relative")

        # Check relative links point to existing files
        for match in re.finditer(r'href="([\w-]+\.html)"', content):
            target = match.group(1)
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
            html = html.replace("</head>", '  <link rel="icon" href="favicon.svg" type="image/svg+xml">\n</head>', 1)
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
