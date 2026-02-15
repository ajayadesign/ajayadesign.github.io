"""
AjayaDesign Automation — Git / GitHub CLI service.
Async subprocess wrappers for git and gh commands.
"""

import asyncio
import logging
import os
import time

from api.config import settings

logger = logging.getLogger(__name__)

# ── Retry classification ────────────────────────────────

RATE_LIMIT_PHRASES = [
    "rate limit",
    "api rate limit exceeded",
    "403",
    "secondary rate limit",
    "abuse detection",
]

TRANSIENT_PHRASES = [
    "could not resolve host",
    "connection timed out",
    "the remote end hung up",
    "ssl_error",
    "early eof",
    "connection reset",
    "broken pipe",
]


def _is_rate_limited(msg: str) -> bool:
    """Check if an error message indicates a GitHub API rate limit."""
    msg_lower = msg.lower()
    return any(phrase in msg_lower for phrase in RATE_LIMIT_PHRASES)


def _is_transient(msg: str) -> bool:
    """Check if an error message indicates a transient network failure."""
    msg_lower = msg.lower()
    return any(phrase in msg_lower for phrase in TRANSIENT_PHRASES)


async def run_cmd(
    cmd: str,
    cwd: str | None = None,
    timeout: int = 300,
    retries: int = 3,
    env_extra: dict | None = None,
) -> str:
    """Run a shell command async, return stdout. Retries on rate limits and transient failures."""
    env = {**os.environ, "HOME": "/root"}
    if env_extra:
        env.update(env_extra)

    last_err: RuntimeError | None = None

    for attempt in range(1, retries + 1):
        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )

            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            except asyncio.TimeoutError:
                proc.kill()
                raise RuntimeError(f"Command timed out ({timeout}s): {cmd}")

            out = stdout.decode().strip() if stdout else ""
            err = stderr.decode().strip() if stderr else ""

            if proc.returncode != 0:
                raise RuntimeError(
                    f"Command failed (exit {proc.returncode}): {cmd}\n{err or out}"
                )

            return out

        except RuntimeError as e:
            last_err = e
            msg = str(e)

            is_rl = _is_rate_limited(msg)
            is_tr = _is_transient(msg)

            if (is_rl or is_tr) and attempt < retries:
                if is_rl:
                    wait = await _get_github_rate_limit_wait()
                    wait = max(wait, 60)  # minimum 60s for rate limits
                else:
                    wait = attempt * 10  # 10s, 20s for transient errors

                logger.warning(
                    "git.run_cmd retry %d/%d in %ds%s: %s",
                    attempt, retries, wait,
                    " (rate-limited)" if is_rl else " (transient)",
                    msg[:200],
                )
                await asyncio.sleep(wait)
                continue

            raise

    # Should not reach here, but safety net
    raise last_err  # type: ignore[misc]


async def try_cmd(
    cmd: str, cwd: str | None = None, timeout: int = 300, retries: int = 3
) -> tuple[bool, str]:
    """Run a command, return (success, output) without raising. Inherits retry logic."""
    try:
        output = await run_cmd(cmd, cwd=cwd, timeout=timeout, retries=retries)
        return True, output
    except RuntimeError as e:
        return False, str(e)


async def _get_github_rate_limit_wait() -> int:
    """Query GitHub API for rate limit reset time. Returns seconds to wait."""
    try:
        proc = await asyncio.create_subprocess_shell(
            'gh api rate_limit --jq ".rate.reset"',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, "HOME": "/root"},
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), 10)
        reset_epoch = int(stdout.decode().strip())
        wait = max(0, reset_epoch - int(time.time())) + 5  # 5s buffer
        return min(wait, 3600)  # cap at 1 hour
    except Exception:
        return 120  # default 2 min if we can't query


async def ensure_git_identity() -> None:
    """Set git identity (needed inside Docker)."""
    await try_cmd('git config --global user.email "ajayadahal1000@gmail.com"')
    await try_cmd('git config --global user.name "Ajaya Dahal"')
    await try_cmd("git config --global --add safe.directory '*'")

    if settings.gh_token:
        await try_cmd(
            f'git config --global url."https://{settings.gh_token}@github.com/".insteadOf "https://github.com/"'
        )


def sanitize_repo_name(business_name: str) -> str:
    """Convert business name to a valid GitHub repo slug."""
    import re

    slug = business_name.lower()
    slug = re.sub(r"[^a-z0-9-]", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")
    # GitHub repo names have a 100-char limit
    if len(slug) > 100:
        slug = slug[:100].rstrip("-")
    # Fallback for names that sanitize to empty
    return slug or "client-site"


async def find_unique_repo_name(
    business_name: str,
    github_org: str,
    *,
    db_session=None,
) -> str:
    """
    Return a repo name guaranteed to be unique within the GitHub org.

    If 'sunrise-bakery' already exists on GitHub AND belongs to a different
    client (or we can't tell), append -2, -3, etc. until we find a free name.

    If db_session is provided, also checks in-progress builds in the database
    to prevent two concurrent builds from racing for the same slug.
    """
    base_name = sanitize_repo_name(business_name)

    # Check DB for in-progress builds with the same slug
    db_slugs: set[str] = set()
    if db_session:
        try:
            from sqlalchemy import select
            from api.models.build import Build

            result = await db_session.execute(
                select(Build.repo_name).where(
                    Build.repo_name.ilike(f"{base_name}%"),
                    Build.status.in_(["queued", "running"]),
                )
            )
            db_slugs = {row[0] for row in result.fetchall() if row[0]}
        except Exception:
            logger.warning("Could not query DB for repo name conflicts", exc_info=True)

    candidate = base_name

    for suffix in range(1, 100):
        # If this candidate is claimed by an in-progress build, skip
        if candidate in db_slugs:
            candidate = f"{base_name}-{suffix + 1}"
            continue

        # Check if repo exists on GitHub
        repo_full = f"{github_org}/{candidate}"
        exists, _ = await try_cmd(f'gh repo view "{repo_full}" 2>/dev/null')

        if not exists:
            # Free name — use it
            return candidate

        # Repo exists. Check its description to see if it's the SAME client
        # (our repos include "Client site for {name}" in the description)
        ok, desc = await try_cmd(
            f'gh repo view "{repo_full}" --json description -q .description 2>/dev/null'
        )
        if ok and f"Client site for {business_name}" in desc:
            # Same client — reuse (this is a rebuild)
            logger.info(f"Repo {repo_full} exists for same client — reusing")
            return candidate

        # Different client or can't tell — try next suffix
        logger.info(f"Repo {repo_full} exists for different client — trying suffix")
        candidate = f"{base_name}-{suffix + 1}"

    # Extremely unlikely — 100 collisions
    raise RuntimeError(
        f"Could not find unique repo name for '{business_name}' after 100 attempts"
    )
