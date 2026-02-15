"""
Phase 1: Create GitHub Repository.

Handles repo name collisions: if 'sunrise-bakery' already belongs to a
different client, automatically tries 'sunrise-bakery-2', '-3', etc.
"""

import os
import shutil
import logging

from api.config import settings
from api.services.git import run_cmd, try_cmd, sanitize_repo_name, find_unique_repo_name

logger = logging.getLogger(__name__)


async def create_repo(
    business_name: str,
    niche: str,
    goals: str,
    email: str,
    *,
    log_fn=None,
    db_session=None,
) -> dict:
    """Create (or clone existing) GitHub repo. Returns repo info dict."""
    github_org = settings.github_org
    base_dir = settings.base_dir

    # Find a unique repo name (handles collisions with different clients)
    repo_name = await find_unique_repo_name(
        business_name, github_org, db_session=db_session
    )
    repo_full = f"{github_org}/{repo_name}"
    project_dir = os.path.join(base_dir, repo_name)
    live_url = f"https://ajayadesign.github.io/{repo_name}"

    _log(log_fn, f"🏗️ Creating GitHub repo: {repo_full}")

    os.makedirs(base_dir, exist_ok=True)

    # Clean stale directory
    if os.path.exists(project_dir):
        _log(log_fn, f"  ⚠️ Directory {repo_name} exists, cleaning...")
        shutil.rmtree(project_dir, ignore_errors=True)

    # Check if repo already exists (it may — find_unique_repo_name allows reuse for same client)
    ok, _ = await try_cmd(f'gh repo view "{repo_full}" 2>/dev/null')

    if ok:
        _log(log_fn, f"  Repo {repo_full} already exists (same client rebuild), cloning...")
        await run_cmd(f'git clone "https://github.com/{repo_full}.git" "{project_dir}"')
    else:
        _log(log_fn, f"  Creating repo under org {github_org}...")
        ok, output = await try_cmd(
            f'gh repo create "{repo_full}" --public --add-readme '
            f'--description "Client site for {business_name} — built by AjayaDesign"'
        )
        if not ok:
            raise RuntimeError(
                f"Failed to create repo: {output}\n"
                "Check GH_TOKEN permissions (needs Administration: Write for org repos)."
            )
        # Give GitHub API a moment
        import asyncio
        await asyncio.sleep(3)
        await run_cmd(f'git clone "https://github.com/{repo_full}.git" "{project_dir}"')

    _log(log_fn, f"  ✅ Repo ready: {repo_full} → {project_dir}")

    return {
        "dir": project_dir,
        "repo_name": repo_name,
        "repo_full": repo_full,
        "live_url": live_url,
    }


def _log(fn, msg):
    if fn:
        fn(msg)
    logger.info(msg)
