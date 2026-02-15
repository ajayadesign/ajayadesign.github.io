"""
Phase 0 (sub-phase): Scrape existing website for AI analysis.
Called conditionally from Phase 2 (Council) when existing_website is provided.
Uses aiohttp + regex parsing — no external dependencies.
"""

import re
import logging
from urllib.parse import urljoin, urlparse

import aiohttp

from api.services.ai import call_ai, extract_json
from api.pipeline.prompts import SCRAPER_ANALYSIS_SYSTEM, scraper_analyze

logger = logging.getLogger(__name__)

MAX_PAGES = 10
MAX_PAGE_SIZE = 500_000  # 500KB per page
TIMEOUT = aiohttp.ClientTimeout(total=30, connect=10)


async def scrape_existing_site(url: str, *, log_fn=None) -> dict:
    """
    Download and analyze an existing website.
    Returns structured analysis dict for the council.
    Gracefully returns {} on any failure.
    """
    _log(log_fn, f"🔍 Scraping existing site: {url}")

    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    pages_content: list[dict] = []
    colors_found: set[str] = set()
    fonts_found: set[str] = set()
    images_found: list[str] = []

    try:
        async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
            # Fetch homepage
            html = await _fetch_page(session, url)
            if not html:
                _log(log_fn, "  ⚠️ Could not fetch homepage, skipping scrape")
                return {}

            pages_content.append({"url": url, "content": _extract_text(html)[:3000]})
            colors_found.update(_extract_colors(html))
            fonts_found.update(_extract_fonts(html))
            images_found.extend(_extract_images(html, url)[:10])

            # Find internal links and fetch a few more pages
            links = _extract_internal_links(html, url)
            fetched = 1
            for link in links[:MAX_PAGES - 1]:
                try:
                    page_html = await _fetch_page(session, link)
                    if page_html:
                        pages_content.append(
                            {"url": link, "content": _extract_text(page_html)[:2000]}
                        )
                        colors_found.update(_extract_colors(page_html))
                        fetched += 1
                except Exception:
                    continue

            _log(log_fn, f"  📄 Fetched {fetched} pages from existing site")

    except Exception as e:
        _log(log_fn, f"  ⚠️ Scrape failed: {e} — continuing without scrape data")
        return {}

    # Ask AI to analyze the scraped content
    try:
        combined_content = "\n\n---\n\n".join(
            f"Page: {p['url']}\n{p['content']}" for p in pages_content
        )

        raw = await call_ai(
            messages=[
                {"role": "system", "content": SCRAPER_ANALYSIS_SYSTEM},
                {"role": "user", "content": scraper_analyze(
                    combined_content,
                    list(colors_found)[:10],
                    list(fonts_found)[:5],
                )},
            ],
            temperature=0.4,
            max_tokens=3000,
        )

        analysis = extract_json(raw)
        analysis["scraped_pages"] = len(pages_content)
        analysis["scraped_images"] = images_found[:5]

        _log(log_fn, f"  ✅ Site analysis complete: {analysis.get('brand_voice', 'N/A')}")
        return analysis

    except Exception as e:
        _log(log_fn, f"  ⚠️ AI analysis of scraped site failed: {e}")
        return {"scraped_pages": len(pages_content), "raw_colors": list(colors_found)}


# ── Internal helpers ────────────────────────────────────


async def _fetch_page(session: aiohttp.ClientSession, url: str) -> str | None:
    """Fetch a single page, return HTML or None."""
    try:
        async with session.get(url, allow_redirects=True) as resp:
            if resp.status != 200:
                return None
            content_type = resp.headers.get("Content-Type", "")
            if "text/html" not in content_type:
                return None
            body = await resp.read()
            if len(body) > MAX_PAGE_SIZE:
                return None
            return body.decode("utf-8", errors="replace")
    except Exception:
        return None


def _extract_text(html: str) -> str:
    """Extract visible text from HTML (regex-based, no external deps)."""
    text = re.sub(r"<(script|style|noscript)[^>]*>[\s\S]*?</\1>", "", html, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_colors(html: str) -> set[str]:
    """Extract hex color codes from HTML/inline styles/CSS."""
    return set(re.findall(r"#[0-9A-Fa-f]{3,8}", html))


def _extract_fonts(html: str) -> set[str]:
    """Extract font-family declarations."""
    fonts: set[str] = set()
    for match in re.finditer(r"font-family:\s*['\"]?([^;'\"]+)", html, re.I):
        fonts.add(match.group(1).strip().split(",")[0].strip("'\""))
    for match in re.finditer(r"fonts\.googleapis\.com/css2?\?family=([^&\"]+)", html):
        for f in match.group(1).split("|"):
            fonts.add(f.split(":")[0].replace("+", " "))
    return fonts


def _extract_images(html: str, base_url: str) -> list[str]:
    """Extract image URLs."""
    images = []
    for match in re.finditer(r'<img[^>]+src=["\']([^"\']+)["\']', html, re.I):
        src = match.group(1)
        if src.startswith(("data:", "blob:")):
            continue
        images.append(urljoin(base_url, src))
    return images


def _extract_internal_links(html: str, base_url: str) -> list[str]:
    """Extract internal links from HTML."""
    parsed_base = urlparse(base_url)
    links: set[str] = set()
    for match in re.finditer(r'<a[^>]+href=["\']([^"\'#]+)["\']', html, re.I):
        href = match.group(1)
        full_url = urljoin(base_url, href)
        parsed = urlparse(full_url)
        if parsed.netloc == parsed_base.netloc and full_url != base_url:
            links.add(full_url)
    return list(links)[:20]


def _log(fn, msg):
    if fn:
        fn(msg)
    logger.info(msg)
