"""
Phase 4b (sub-phase): Visual Asset Pipeline — stock image sourcing.
Called from Phase 4 (Generate) after page HTML is created.
Sources images from Unsplash API, falls back to CSS gradients.
Gracefully no-ops when no API key is configured.
"""

import os
import re
import logging

import aiohttp

from api.config import settings

logger = logging.getLogger(__name__)

UNSPLASH_SEARCH = "https://api.unsplash.com/search/photos"
TIMEOUT = aiohttp.ClientTimeout(total=15)


async def source_images(
    blueprint: dict,
    creative_spec: dict,
    project_dir: str,
    *,
    log_fn=None,
) -> dict[str, str]:
    """
    Source high-quality images from Unsplash based on creative_spec.
    Downloads images to project_dir/images/.
    Returns {slug: local_path} mapping.

    Gracefully returns {} if no API key is configured.
    """
    api_key = getattr(settings, "unsplash_access_key", "")
    if not api_key:
        _log(log_fn, "  📷 No Unsplash API key — using CSS gradient fallbacks")
        return {}

    _log(log_fn, "📷 Sourcing images from Unsplash")

    images_dir = os.path.join(project_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    image_map: dict[str, str] = {}
    search_terms = creative_spec.get("imageSearchTerms", {})

    pages = blueprint.get("pages", [])
    for page in pages:
        slug = page["slug"]
        queries = search_terms.get(slug, [])
        if not queries:
            # Generate a default search query from niche
            niche = blueprint.get("tagline", blueprint.get("siteName", "business"))
            queries = [f"{niche} professional"]

        query = queries[0] if isinstance(queries, list) else str(queries)

        try:
            image_url = await _search_unsplash(api_key, query)
            if image_url:
                local_path = await _download_image(image_url, images_dir, slug)
                if local_path:
                    image_map[slug] = f"images/{os.path.basename(local_path)}"
                    _log(log_fn, f"  ✅ {slug}: downloaded image for '{query}'")
                else:
                    _log(log_fn, f"  ⚠️ {slug}: download failed for '{query}'")
            else:
                _log(log_fn, f"  ⚠️ {slug}: no results for '{query}'")
        except Exception as e:
            _log(log_fn, f"  ⚠️ {slug}: image search error: {e}")

    _log(log_fn, f"  📷 Sourced {len(image_map)} images total")
    return image_map


def inject_images_into_html(
    project_dir: str,
    image_map: dict[str, str],
    blueprint: dict,
) -> None:
    """
    Replace img-slot placeholders in generated HTML with actual image paths.
    Also finds <img> tags with placeholder/missing src and replaces them.
    """
    if not image_map:
        return

    pages = blueprint.get("pages", [])
    for page in pages:
        slug = page["slug"]
        if slug not in image_map:
            continue

        filename = "index.html" if slug == "index" else f"{slug}.html"
        filepath = os.path.join(project_dir, filename)
        if not os.path.exists(filepath):
            continue

        with open(filepath, "r", encoding="utf-8") as f:
            html = f.read()

        img_src = image_map[slug]

        # Replace img-slot placeholder divs
        html = re.sub(
            r'<div\s+class="img-slot"[^>]*>.*?</div>',
            f'<img src="{img_src}" alt="{page.get("title", slug)}" '
            f'class="w-full h-full object-cover" loading="lazy">',
            html,
            flags=re.DOTALL,
        )

        # Replace placeholder image src attributes
        html = re.sub(
            r'src="(https?://via\.placeholder\.com[^"]*|placeholder\.[^"]*|#)"',
            f'src="{img_src}"',
            html,
        )

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)


# ── Internal Helpers ────────────────────────────────────


async def _search_unsplash(api_key: str, query: str) -> str | None:
    """Search Unsplash for an image. Returns the regular-size URL or None."""
    headers = {"Authorization": f"Client-ID {api_key}"}
    params = {"query": query, "per_page": 1, "orientation": "landscape"}

    try:
        async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
            async with session.get(UNSPLASH_SEARCH, headers=headers, params=params) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                results = data.get("results", [])
                if results:
                    return results[0]["urls"].get("regular")
    except Exception:
        pass
    return None


async def _download_image(url: str, images_dir: str, slug: str) -> str | None:
    """Download an image and save to disk. Returns local path or None."""
    ext = ".jpg"
    local_path = os.path.join(images_dir, f"{slug}-hero{ext}")

    try:
        async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return None
                data = await resp.read()
                if len(data) < 1000:  # Too small, probably an error
                    return None
                with open(local_path, "wb") as f:
                    f.write(data)
                return local_path
    except Exception:
        return None


def _log(fn, msg):
    if fn:
        fn(msg)
    logger.info(msg)
