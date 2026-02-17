"""
Phase 7: Deploy — git push, GitHub Pages API, submodule, portfolio card.
"""

import asyncio
import html
import os
import logging
from pathlib import Path

import httpx

from api.config import settings
from api.services.git import run_cmd, try_cmd, ensure_git_identity

logger = logging.getLogger(__name__)

PORTFOLIO_MARKER = "<!-- %%PORTFOLIO_INJECT%% -->"

NICHE_EMOJI = {
    "photo": "📸", "camera": "📸", "food": "🍰", "bakery": "🍰",
    "restaurant": "🍰", "cafe": "🍰", "tech": "⚡", "engineer": "⚡",
    "software": "⚡", "child": "👶", "nanny": "👶", "health": "💪",
    "fitness": "💪", "gym": "💪", "yoga": "💪", "music": "🎵",
    "art": "🎨", "design": "🎨", "shop": "🛍️", "store": "🛍️",
    "real estate": "🏠", "property": "🏠", "law": "⚖️", "legal": "⚖️",
    "pet": "🐾", "animal": "🐾", "beauty": "💅", "salon": "💅",
    "spa": "💅", "auto": "🔧", "car": "🔧", "construct": "🏗️",
    "education": "📚", "tutor": "📚", "travel": "✈️", "tour": "✈️",
    "wedding": "💍", "event": "💍", "clean": "✨", "garden": "🌿",
    "landscape": "🌿",
}


def _pick_emoji(niche: str) -> str:
    n = niche.lower()
    for keyword, emoji in NICHE_EMOJI.items():
        if keyword in n:
            return emoji
    return "🌐"


def inject_portfolio_card(
    index_path: str,
    *,
    repo_name: str,
    client_name: str,
    niche: str = "Professional Services",
    goals: str = "",
    emoji: str = "🌐",
) -> bool:
    """
    Inject a portfolio card into index.html at the PORTFOLIO_MARKER.

    Pure-Python replacement for the old inject_card.js Node script.
    Returns True if a card was injected, False otherwise.
    """
    path = Path(index_path)
    if not path.exists():
        logger.warning("inject_portfolio_card: %s not found", index_path)
        return False

    content = path.read_text(encoding="utf-8")
    if PORTFOLIO_MARKER not in content:
        logger.warning("inject_portfolio_card: marker not found in %s", index_path)
        return False

    # Avoid duplicate cards
    card_id = f'id="card-{html.escape(repo_name)}"'
    if card_id in content:
        logger.info("inject_portfolio_card: card for %s already exists, skipping", repo_name)
        return False

    safe_name = html.escape(client_name)
    safe_niche = html.escape(niche)
    safe_goals = html.escape(goals) if goals else ""
    safe_repo = html.escape(repo_name)
    # Use relative path so it works both locally and on GitHub Pages
    live_url = f"/{safe_repo}/"

    subtitle = safe_goals if safe_goals else safe_niche

    card_html = (
        f'\n        <div class="portfolio-card" {card_id}>\n'
        f"          <span class=\"card-emoji\">{emoji}</span>\n"
        f'          <h3><a href="{live_url}" target="_blank" rel="noopener noreferrer">{safe_name}</a></h3>\n'
        f"          <p>{subtitle}</p>\n"
        f"        </div>\n"
        f"        {PORTFOLIO_MARKER}"
    )

    new_content = content.replace(PORTFOLIO_MARKER, card_html, 1)
    path.write_text(new_content, encoding="utf-8")
    logger.info("inject_portfolio_card: injected card for %s", repo_name)
    return True


async def deploy(
    repo: dict,
    blueprint: dict,
    *,
    log_fn=None,
) -> None:
    """Commit, push, enable GitHub Pages, add submodule, inject card."""
    project_dir = repo["dir"]
    repo_name = repo["repo_name"]
    repo_full = repo["repo_full"]
    main_site_dir = settings.main_site_dir

    _log(log_fn, f"🚀 Deploying {repo_full} to GitHub Pages")

    # ── Ensure git identity + safe.directory (critical for mounted volumes) ──
    await ensure_git_identity()

    # ── Git add, commit, push ──
    await run_cmd("git add -A", cwd=project_dir)

    client_name = blueprint.get("siteName", repo_name)
    tagline = blueprint.get("tagline", "")
    page_count = len(blueprint.get("pages", []))

    await try_cmd(
        f'git commit -m "feat: {page_count}-page site for {client_name}\n\n{tagline}\nBuilt by AjayaDesign v2"',
        cwd=project_dir,
    )
    await run_cmd("git push -u origin main", cwd=project_dir)
    _log(log_fn, "  ✅ Pushed to GitHub")

    # Fix ownership
    uid, gid = settings.host_uid, settings.host_gid
    await try_cmd(f'chown -R {uid}:{gid} "{project_dir}" 2>/dev/null')

    # ── Enable GitHub Pages ──
    _log(log_fn, "  Enabling GitHub Pages...")
    pages_payload = '{"source":{"branch":"main","path":"/"}}'

    # Use echo pipe instead of <<< heredoc (dash shell doesn't support <<<)
    ok, _ = await try_cmd(
        f"echo '{pages_payload}' | gh api -X POST 'repos/{repo_full}/pages' --input -",
        cwd=project_dir,
    )
    if not ok:
        ok, _ = await try_cmd(
            f"echo '{pages_payload}' | gh api -X PUT 'repos/{repo_full}/pages' --input -",
            cwd=project_dir,
        )

    _log(log_fn, "  ✅ GitHub Pages enabled" if ok else "  ⚠️ Pages may already be enabled")

    # ── Submodule + portfolio card ──
    if os.path.exists(main_site_dir):
        _log(log_fn, "  Adding submodule to main site...")
        submodule_path = os.path.join(main_site_dir, repo_name)

        if not os.path.exists(submodule_path):
            await try_cmd(f'rm -rf ".git/modules/{repo_name}"', cwd=main_site_dir)
            ok, out = await try_cmd(
                f'git submodule add --force "https://github.com/{repo_full}.git" "{repo_name}"',
                cwd=main_site_dir,
            )
            _log(log_fn, "    ✅ Submodule added" if ok else f"    ⚠️ Submodule failed: {out[:100]}")
        else:
            await try_cmd(f'git submodule update --remote "{repo_name}"', cwd=main_site_dir)
            _log(log_fn, "    ⚠️ Submodule already exists, updated")

        # Inject portfolio card (pure Python — no Node dependency)
        main_index = os.path.join(main_site_dir, "index.html")
        emoji = _pick_emoji(tagline)
        card_ok = inject_portfolio_card(
            main_index,
            repo_name=repo_name,
            client_name=client_name,
            niche=tagline or "Professional Services",
            goals=blueprint.get("siteGoals", ""),
            emoji=emoji,
        )
        _log(log_fn, "    ✅ Portfolio card injected" if card_ok else "    ⚠️ Card injection skipped")

        # Commit + push main site
        await try_cmd("git add -A", cwd=main_site_dir)
        await try_cmd(
            f'git commit -m "feat: add {client_name} portfolio (submodule + card)"',
            cwd=main_site_dir,
        )
        await try_cmd("git push", cwd=main_site_dir)
        _log(log_fn, "  ✅ Main site updated and pushed")

        # Fix ownership
        await try_cmd(f'chown -R {uid}:{gid} "{main_site_dir}/.git" 2>/dev/null')
        await try_cmd(f'chown -R {uid}:{gid} "{main_site_dir}/{repo_name}" 2>/dev/null')
    else:
        _log(log_fn, f"  ⚠️ Main site not found at {main_site_dir}, skipping submodule")

    # ── Verify site is live ──
    live_url = repo["live_url"]
    is_live = await verify_site_live(live_url, log_fn=log_fn)
    repo["verified_live"] = is_live

    _log(log_fn, f"  🔗 Live URL: {live_url}")


async def verify_site_live(
    url: str,
    *,
    max_attempts: int = 10,
    delay_secs: int = 6,
    log_fn=None,
) -> bool:
    """
    Poll the live URL until it returns 200 with real HTML content.
    GitHub Pages can take 10-60s to propagate after the first push.
    """
    _log(log_fn, f"  🔍 Verifying site is live: {url}")

    for attempt in range(1, max_attempts + 1):
        try:
            async with httpx.AsyncClient(
                follow_redirects=True, timeout=10
            ) as client:
                resp = await client.get(url)
                if resp.status_code == 200 and "<!DOCTYPE" in resp.text[:500]:
                    _log(log_fn, f"  ✅ Site is live! (attempt {attempt}/{max_attempts})")
                    return True
                _log(
                    log_fn,
                    f"  ⏳ Attempt {attempt}/{max_attempts}: HTTP {resp.status_code}, waiting {delay_secs}s...",
                )
        except Exception as e:
            _log(
                log_fn,
                f"  ⏳ Attempt {attempt}/{max_attempts}: {type(e).__name__}, waiting {delay_secs}s...",
            )

        if attempt < max_attempts:
            await asyncio.sleep(delay_secs)

    _log(log_fn, f"  ⚠️ Site not live after {max_attempts * delay_secs}s — notification will still be sent")
    return False


def _log(fn, msg):
    if fn:
        fn(msg)
    logger.info(msg)
