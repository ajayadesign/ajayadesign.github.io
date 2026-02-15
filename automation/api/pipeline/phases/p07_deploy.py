"""
Phase 7: Deploy — git push, GitHub Pages API, submodule, portfolio card.
"""

import os
import re
import logging

from api.config import settings
from api.services.git import run_cmd, try_cmd

logger = logging.getLogger(__name__)

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

    ok, _ = await try_cmd(
        f"gh api -X POST 'repos/{repo_full}/pages' --input - <<< '{pages_payload}'",
        cwd=project_dir,
    )
    if not ok:
        ok, _ = await try_cmd(
            f"gh api -X PUT 'repos/{repo_full}/pages' --input - <<< '{pages_payload}'",
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

        # Inject portfolio card
        inject_script = os.path.join(main_site_dir, "automation", "inject_card.js")
        main_index = os.path.join(main_site_dir, "index.html")

        if os.path.exists(inject_script) and os.path.exists(main_index):
            with open(main_index, "r") as f:
                if "%%PORTFOLIO_INJECT%%" in f.read():
                    emoji = _pick_emoji(tagline)
                    import json

                    card_data = json.dumps({
                        "repoName": repo_name,
                        "clientName": client_name,
                        "niche": tagline or "Professional Services",
                        "goals": blueprint.get("siteGoals", ""),
                        "emoji": emoji,
                        "indexPath": main_index,
                    })
                    ok, _ = await try_cmd(
                        f"echo '{card_data}' | node \"{inject_script}\"",
                        cwd=main_site_dir,
                    )
                    _log(log_fn, "    ✅ Portfolio card injected" if ok else "    ⚠️ Card injection failed")

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

    _log(log_fn, f"  🔗 Live URL: {repo['live_url']}")


def _log(fn, msg):
    if fn:
        fn(msg)
    logger.info(msg)
