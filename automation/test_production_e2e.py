#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════
  AjayaDesign Automation — FULL PRODUCTION End-to-End Test
═══════════════════════════════════════════════════════════════════════════

This is NOT a pytest unit test. This is a standalone script that exercises
the REAL production pipeline end-to-end:

  Form submit → AI council → Design → Generate → Assemble → Test →
  Deploy (GitHub repo push) → Telegram notification

It uses REAL services:
  ✦ Real AI API calls (OpenAI via GitHub Models or Anthropic Claude)
  ✦ Real GitHub repo creation (under ajayadesign org)
  ✦ Real Playwright tests on generated pages
  ✦ Real git push to GitHub Pages
  ✦ Real Telegram notification

Usage:
  cd automation
  python test_production_e2e.py                          # default bakery test
  python test_production_e2e.py --niche "Pet Grooming"   # custom niche
  python test_production_e2e.py --dry-run                # skip deploy + notify
  python test_production_e2e.py --cleanup                # delete repo after test
  python test_production_e2e.py --skip-tests             # skip Playwright phase
  python test_production_e2e.py --timeout 900            # custom timeout (seconds)

Prerequisites:
  • .env file with GH_TOKEN, AI_TOKEN/ANTHROPIC_API_KEY, TELEGRAM_BOT_TOKEN
  • gh CLI authenticated (gh auth status)
  • Node.js + npx available (for Playwright tests in phase 6)

The script:
  1. Validates all credentials and tools before starting
  2. Submits a build request to the pipeline (in-process, no HTTP)
  3. Streams live logs with timing per phase
  4. Validates results at each checkpoint
  5. Optionally cleans up the test repo
  6. Prints a full summary report

⚠️  This creates a REAL GitHub repo and burns AI tokens. Use intentionally.
═══════════════════════════════════════════════════════════════════════════
"""

import argparse
import asyncio
import json
import logging
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ── Ensure we can import the automation package ──
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")


# ═══════════════════════════════════════════════════════
#  Configuration
# ═══════════════════════════════════════════════════════

# Test client presets — realistic enough to exercise the pipeline well
TEST_CLIENTS = {
    "bakery": {
        "business_name": "E2E Test — Sunrise Bakery",
        "niche": "Artisan Bakery & Café",
        "goals": "Showcase handmade pastries and drive catering orders",
        "email": "e2e-test@ajayadesign.test",
        "phone": "(503) 555-0199",
        "location": "Portland, OR",
        "brand_colors": "Warm gold, cream, forest green",
        "tagline": "Handmade Pastries & Fresh-Baked Joy",
        "target_audience": "Local food lovers, wedding planners",
        "additional_notes": "E2E production test — safe to delete",
    },
    "saas": {
        "business_name": "E2E Test — CloudPulse",
        "niche": "SaaS Analytics Platform",
        "goals": "Drive demo signups and showcase product features",
        "email": "e2e-test@ajayadesign.test",
        "location": "San Francisco, CA",
        "brand_colors": "Electric blue, dark navy, white",
        "tagline": "Analytics That Actually Make Sense",
        "target_audience": "Startup founders, product managers",
        "additional_notes": "E2E production test — safe to delete",
    },
    "pet": {
        "business_name": "E2E Test — Happy Paws Grooming",
        "niche": "Pet Grooming & Spa",
        "goals": "Book more grooming appointments online",
        "email": "e2e-test@ajayadesign.test",
        "phone": "(971) 555-0123",
        "location": "Austin, TX",
        "brand_colors": "Warm orange, teal, cream",
        "tagline": "Where Every Pet Leaves Happy",
        "target_audience": "Pet owners, dog lovers",
        "additional_notes": "E2E production test — safe to delete",
    },
}


# ═══════════════════════════════════════════════════════
#  Preflight Checks
# ═══════════════════════════════════════════════════════

class PreflightError(Exception):
    pass


def preflight_checks(dry_run: bool = False, skip_tests: bool = False) -> dict:
    """Verify all credentials, tools, and config before starting. Returns env info."""
    checks = {}
    errors = []

    print("\n🔍 Preflight checks...\n")

    # 1. .env loaded (optional in Docker — env vars come from compose)
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        print("  ✅ .env file found")
    else:
        print("  ⚠️  No .env file (OK if running in Docker with env vars from compose)")

    # 2. AI credentials
    ai_provider = os.getenv("AI_PROVIDER", "github-models")
    checks["ai_provider"] = ai_provider
    if ai_provider == "anthropic":
        key = os.getenv("ANTHROPIC_API_KEY", "")
        if key:
            print(f"  ✅ Anthropic API key: ...{key[-4:]}")
            checks["ai_model"] = os.getenv("AI_MODEL", "claude-sonnet-4-20250514")
        else:
            errors.append("ANTHROPIC_API_KEY not set (AI_PROVIDER=anthropic)")
    else:
        token = os.getenv("AI_TOKEN", "") or os.getenv("GH_TOKEN", "")
        if token:
            print(f"  ✅ AI token (GitHub Models): ...{token[-4:]}")
            checks["ai_model"] = os.getenv("AI_MODEL", "gpt-4o")
        else:
            errors.append("AI_TOKEN or GH_TOKEN not set for GitHub Models AI")

    # 3. GitHub token
    gh_token = os.getenv("GH_TOKEN", "")
    if gh_token:
        print(f"  ✅ GH_TOKEN: ...{gh_token[-4:]}")
    elif not dry_run:
        errors.append("GH_TOKEN not set — needed for repo creation")

    # 4. gh CLI
    if not dry_run:
        gh_path = shutil.which("gh")
        if gh_path:
            print(f"  ✅ gh CLI: {gh_path}")
        else:
            errors.append("gh CLI not found — needed for repo creation (brew install gh)")

    # 5. Telegram
    tg_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    tg_chat = os.getenv("TELEGRAM_CHAT_ID", "")
    if tg_token and tg_chat:
        print(f"  ✅ Telegram: bot ...{tg_token[-4:]}, chat {tg_chat}")
        checks["telegram"] = True
    else:
        print("  ⚠️  Telegram not configured — notification will be skipped")
        checks["telegram"] = False

    # 6. Node.js (for Playwright tests)
    if not skip_tests:
        npx_path = shutil.which("npx")
        if npx_path:
            print(f"  ✅ npx: {npx_path}")
        else:
            print("  ⚠️  npx not found — Playwright tests will be skipped")

    # 7. git
    git_path = shutil.which("git")
    if git_path:
        print(f"  ✅ git: {git_path}")
    elif not dry_run:
        errors.append("git not found")

    if errors:
        print("\n❌ Preflight FAILED:\n")
        for e in errors:
            print(f"  • {e}")
        raise PreflightError(f"{len(errors)} preflight check(s) failed")

    print()
    return checks


# ═══════════════════════════════════════════════════════
#  Pipeline Runner
# ═══════════════════════════════════════════════════════

async def run_production_pipeline(
    client_data: dict,
    *,
    dry_run: bool = False,
    skip_tests: bool = False,
    timeout_secs: int = 600,
    cleanup: bool = False,
) -> dict:
    """
    Run the full production pipeline for a test client.
    Returns a result dict with status, timing, and artifacts.
    """

    # ── Import here (after env is loaded) to pick up correct settings ──
    from api.config import settings
    from api.database import Base
    from api.models.build import Build, BuildPhase, BuildLog, BuildPage
    from api.pipeline.orchestrator import BuildOrchestrator
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    result = {
        "status": "unknown",
        "client_name": client_data["business_name"],
        "phases": {},
        "timings": {},
        "errors": [],
        "artifacts": {},
    }

    # ── Temp DB for this test run (SQLite file in /tmp) ──
    db_path = f"/tmp/ajayadesign_e2e_{int(time.time())}.db"
    db_url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(db_url, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    t_start = time.monotonic()

    # ── Apply dry-run overrides ──
    if dry_run:
        # Monkey-patch deploy + notify to no-op
        import api.pipeline.phases.p07_deploy as p07
        import api.pipeline.phases.p08_notify as p08

        original_deploy = p07.deploy
        original_notify = p08.notify

        async def _noop_deploy(*a, **kw):
            print("  🟡 [DRY-RUN] Skipping deploy (would push to GitHub)")

        async def _noop_notify(*a, **kw):
            print("  🟡 [DRY-RUN] Skipping Telegram notification")

        p07.deploy = _noop_deploy
        p08.notify = _noop_notify

    if skip_tests:
        import api.pipeline.phases.p06_test as p06

        original_quality_gate = p06.quality_gate

        async def _noop_tests(*a, **kw):
            kw.get("log_fn", lambda m: None)("  🟡 [SKIP] Playwright tests skipped")
            return {"passed": True, "failures": [], "failed_pages": [], "skipped": True}

        p06.quality_gate = _noop_tests

    # ── Create Build record ──
    async with session_factory() as session:
        short_id = f"e2e{int(time.time()) % 100000:05d}"
        build = Build(
            short_id=short_id,
            client_name=client_data["business_name"],
            niche=client_data["niche"],
            goals=client_data.get("goals", ""),
            email=client_data.get("email", ""),
            phone=client_data.get("phone"),
            location=client_data.get("location"),
            existing_website=client_data.get("existing_website"),
            brand_colors=client_data.get("brand_colors"),
            tagline=client_data.get("tagline"),
            target_audience=client_data.get("target_audience"),
            competitor_urls=client_data.get("competitor_urls"),
            additional_notes=client_data.get("additional_notes"),
            rebuild=client_data.get("rebuild", False),
            source="e2e-production-test",
            status="queued",
        )
        session.add(build)
        await session.commit()
        await session.refresh(build)

        print(f"📋 Build created: {short_id} — {client_data['business_name']}")
        print(f"   Niche: {client_data['niche']}")
        print(f"   AI: {settings.ai_provider} / {settings.ai_effective_model}")
        print()

        # ── Event capture ──
        events = []
        phase_timings = {}
        current_phase_start = None

        def event_callback(event_type: str, data: dict):
            events.append({"type": event_type, **data, "ts": time.monotonic()})

            # Track phase timings
            if event_type == "phase":
                phase_name = data.get("name", "?")
                phase_num = data.get("number", 0)
                if data.get("status") == "running":
                    phase_timings[phase_name] = {"start": time.monotonic(), "number": phase_num}
                elif data.get("status") == "complete":
                    if phase_name in phase_timings:
                        elapsed = time.monotonic() - phase_timings[phase_name]["start"]
                        phase_timings[phase_name]["elapsed"] = elapsed
                        print(f"  ✅ Phase {phase_num} ({phase_name}) — {elapsed:.1f}s")

        # ── Live log callback ──
        original_log_msg = BuildOrchestrator._log_msg

        def _patched_log_msg(self, message, level="info", category="general"):
            # Print to console in real-time
            prefix = {"error": "❌", "warning": "⚠️"}.get(level, "  ")
            print(f"{prefix} {message}")
            # Still do the original DB + firebase logging
            original_log_msg(self, message, level=level, category=category)

        BuildOrchestrator._log_msg = _patched_log_msg

        # ── Run the pipeline ──
        orchestrator = BuildOrchestrator(build, session, event_callback)

        try:
            completed_build = await asyncio.wait_for(
                orchestrator.run(),
                timeout=timeout_secs,
            )

            result["status"] = completed_build.status
            result["artifacts"] = {
                "repo_name": completed_build.repo_name,
                "repo_full": completed_build.repo_full,
                "live_url": completed_build.live_url,
                "pages_count": completed_build.pages_count,
            }

        except asyncio.TimeoutError:
            result["status"] = "timeout"
            result["errors"].append(f"Pipeline timed out after {timeout_secs}s")
            print(f"\n❌ TIMEOUT after {timeout_secs}s")

        except Exception as exc:
            result["status"] = "failed"
            result["errors"].append(str(exc))
            print(f"\n❌ PIPELINE FAILED: {exc}")

            import traceback
            traceback.print_exc()

        finally:
            # Restore monkey-patched methods
            BuildOrchestrator._log_msg = original_log_msg
            if dry_run:
                p07.deploy = original_deploy
                p08.notify = original_notify
            if skip_tests:
                p06.quality_gate = original_quality_gate

        t_total = time.monotonic() - t_start
        result["timings"] = {
            "total_secs": round(t_total, 1),
            "phases": {
                name: round(info.get("elapsed", 0), 1)
                for name, info in phase_timings.items()
            },
        }

        # ── Validate results ──
        print("\n" + "═" * 60)
        print("  VALIDATION CHECKS")
        print("═" * 60)

        checks_passed = 0
        checks_failed = 0

        def check(name: str, condition: bool, detail: str = ""):
            nonlocal checks_passed, checks_failed
            if condition:
                checks_passed += 1
                print(f"  ✅ {name}" + (f" — {detail}" if detail else ""))
            else:
                checks_failed += 1
                print(f"  ❌ {name}" + (f" — {detail}" if detail else ""))
                result["errors"].append(f"Check failed: {name}")

        check("Build status = complete", result["status"] == "complete", result["status"])

        # Blueprint
        bp = orchestrator.blueprint
        check("Blueprint has pages", bool(bp and bp.get("pages")),
              f"{len(bp.get('pages', []))} pages" if bp else "no blueprint")
        if bp:
            check("Blueprint has designStyle", bool(bp.get("designStyle")),
                  bp.get("designStyle", "missing"))
            check("Blueprint has colorDirection", bool(bp.get("colorDirection")))
            check("Blueprint has typography", bool(bp.get("typography")))

        # Creative spec
        cs = orchestrator.creative_spec
        check("Creative spec produced", bool(cs and cs.get("visualConcept")),
              (cs.get("visualConcept", "")[:60] + "...") if cs else "none")

        # Design system
        ds = orchestrator.design_system
        check("Design system has tailwindConfig", bool(ds and ds.get("tailwindConfig")))
        check("Design system has navHtml", bool(ds and ds.get("navHtml")))
        check("Design system has footerHtml", bool(ds and ds.get("footerHtml")))

        # Pages generated
        check("Page results exist", len(orchestrator.page_results) >= 2,
              f"{len(orchestrator.page_results)} pages")
        generated = [p for p in orchestrator.page_results if p.get("status") == "generated"]
        check("Pages generated (not fallback)", len(generated) >= 2,
              f"{len(generated)}/{len(orchestrator.page_results)}")

        # Files on disk
        repo_dir = orchestrator.repo.get("dir", "")
        if repo_dir and os.path.exists(repo_dir):
            index_exists = os.path.exists(os.path.join(repo_dir, "index.html"))
            check("index.html exists on disk", index_exists)

            if index_exists:
                with open(os.path.join(repo_dir, "index.html"), "r") as f:
                    html = f.read()
                check("index.html has <!DOCTYPE>", "<!DOCTYPE" in html)
                check("index.html has <nav>", "<nav" in html)
                check("index.html has <main>", "<main" in html)
                check("index.html has <footer>", "<footer" in html)
                check("index.html has AOS.init", "AOS.init" in html)

            # Assembly artifacts
            check("sitemap.xml created", os.path.exists(os.path.join(repo_dir, "sitemap.xml")))
            check("robots.txt created", os.path.exists(os.path.join(repo_dir, "robots.txt")))
            check("404.html created", os.path.exists(os.path.join(repo_dir, "404.html")))
            check("favicon.svg created", os.path.exists(os.path.join(repo_dir, "favicon.svg")))

            # List generated files
            all_files = os.listdir(repo_dir)
            html_files = [f for f in all_files if f.endswith(".html")]
            result["artifacts"]["html_files"] = html_files
            result["artifacts"]["all_files"] = all_files

        # Repo created (non-dry-run)
        if not dry_run:
            check("Repo name set", bool(result["artifacts"].get("repo_name")))
            check("Live URL set", bool(result["artifacts"].get("live_url")))
            check("Site verified live", orchestrator.repo.get("verified_live", False))

        # DB records
        stmt = select(BuildPhase).where(BuildPhase.build_id == build.id)
        phases_result = await session.execute(stmt)
        phases = phases_result.scalars().all()
        check("All 8 phases recorded in DB", len(phases) == 8, f"{len(phases)} phases")
        completed_phases = [p for p in phases if p.status == "complete"]
        check("All phases completed", len(completed_phases) == 8,
              f"{len(completed_phases)}/8 complete")

        stmt = select(BuildLog).where(BuildLog.build_id == build.id)
        logs_result = await session.execute(stmt)
        logs = logs_result.scalars().all()
        check("Substantial logging", len(logs) > 20, f"{len(logs)} log entries")

        # SSE events
        phase_events = [e for e in events if e.get("type") == "phase"]
        check("SSE phase events emitted", len(phase_events) >= 16,
              f"{len(phase_events)} phase events")

        result["checks"] = {"passed": checks_passed, "failed": checks_failed}

    # ── Cleanup ──
    if cleanup and result["artifacts"].get("repo_full") and not dry_run:
        print(f"\n🧹 Cleaning up repo: {result['artifacts']['repo_full']}")
        try:
            proc = await asyncio.create_subprocess_shell(
                f'gh repo delete "{result["artifacts"]["repo_full"]}" --yes',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, "GH_TOKEN": os.getenv("GH_TOKEN", "")},
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode == 0:
                print("  ✅ Repo deleted")
            else:
                print(f"  ⚠️  Repo deletion failed: {stderr.decode()[:200]}")
        except Exception as e:
            print(f"  ⚠️  Cleanup error: {e}")

    if repo_dir and os.path.exists(repo_dir) and cleanup:
        shutil.rmtree(repo_dir, ignore_errors=True)
        print("  ✅ Local directory cleaned")

    # Cleanup temp DB
    await engine.dispose()
    try:
        os.remove(db_path)
    except OSError:
        pass

    return result


# ═══════════════════════════════════════════════════════
#  Report
# ═══════════════════════════════════════════════════════

def print_report(result: dict):
    """Print a formatted summary report."""
    print("\n" + "═" * 60)
    print("  E2E PRODUCTION TEST REPORT")
    print("═" * 60)

    status_icon = {"complete": "✅", "failed": "❌", "timeout": "⏰"}.get(result["status"], "❓")
    print(f"\n  Status:  {status_icon}  {result['status'].upper()}")
    print(f"  Client:  {result['client_name']}")
    print(f"  Total:   {result['timings'].get('total_secs', '?')}s")

    # Phase timings
    if result["timings"].get("phases"):
        print("\n  Phase Timings:")
        for name, elapsed in result["timings"]["phases"].items():
            bar_len = min(int(elapsed / 2), 40)
            bar = "█" * bar_len
            print(f"    {name:<12} {elapsed:>6.1f}s  {bar}")

    # Artifacts
    arts = result.get("artifacts", {})
    if arts.get("live_url"):
        print(f"\n  🔗 Live URL:   {arts['live_url']}")
    if arts.get("repo_full"):
        print(f"  📦 Repo:       https://github.com/{arts['repo_full']}")
    if arts.get("html_files"):
        print(f"  📄 Pages:      {', '.join(sorted(arts['html_files']))}")
    if arts.get("all_files"):
        print(f"  📁 Files:      {len(arts['all_files'])} total")

    # Checks
    checks = result.get("checks", {})
    print(f"\n  Checks:  {checks.get('passed', 0)} passed, {checks.get('failed', 0)} failed")

    # Errors
    if result["errors"]:
        print(f"\n  ❌ Errors ({len(result['errors'])}):")
        for err in result["errors"]:
            print(f"    • {err[:120]}")

    print("\n" + "═" * 60)

    return result["status"] == "complete" and checks.get("failed", 1) == 0


# ═══════════════════════════════════════════════════════
#  CLI Entry Point
# ═══════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="AjayaDesign — Full Production E2E Pipeline Test",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_production_e2e.py                          # default bakery test
  python test_production_e2e.py --preset saas            # SaaS preset
  python test_production_e2e.py --preset pet --cleanup   # pet grooming, delete repo after
  python test_production_e2e.py --dry-run                # skip deploy + notify
  python test_production_e2e.py --name "My Business" --niche "Coffee Shop"
  python test_production_e2e.py --timeout 900 --skip-tests
        """,
    )

    parser.add_argument(
        "--preset", choices=list(TEST_CLIENTS.keys()), default="bakery",
        help="Use a predefined test client (default: bakery)",
    )
    parser.add_argument("--name", help="Custom business name (overrides preset)")
    parser.add_argument("--niche", help="Custom niche (overrides preset)")
    parser.add_argument("--goals", help="Custom goals (overrides preset)")
    parser.add_argument("--email", help="Custom email (overrides preset)")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Run pipeline but skip deploy (no GitHub push) and notification",
    )
    parser.add_argument(
        "--cleanup", action="store_true",
        help="Delete the GitHub repo after the test completes",
    )
    parser.add_argument(
        "--skip-tests", action="store_true",
        help="Skip the Playwright testing phase (phase 6)",
    )
    parser.add_argument(
        "--timeout", type=int, default=600,
        help="Pipeline timeout in seconds (default: 600)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable debug-level logging",
    )

    args = parser.parse_args()

    # ── Banner ──
    print()
    print("═" * 60)
    print("  🚀 AjayaDesign — Production E2E Pipeline Test")
    print("═" * 60)

    if args.dry_run:
        print("  🟡 DRY-RUN mode — no GitHub deploy, no Telegram")
    if args.cleanup:
        print("  🧹 CLEANUP mode — repo will be deleted after test")
    if args.skip_tests:
        print("  ⏭️  SKIP-TESTS — Playwright phase will be skipped")

    # ── Setup logging ──
    log_level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    )
    # Quiet noisy loggers unless verbose
    if not args.verbose:
        logging.getLogger("httpx").setLevel(logging.ERROR)
        logging.getLogger("httpcore").setLevel(logging.ERROR)
        logging.getLogger("aiohttp").setLevel(logging.ERROR)
        logging.getLogger("sqlalchemy").setLevel(logging.ERROR)

    # ── Preflight ──
    try:
        env_info = preflight_checks(dry_run=args.dry_run, skip_tests=args.skip_tests)
    except PreflightError:
        sys.exit(1)

    # ── Build client data ──
    client_data = dict(TEST_CLIENTS[args.preset])
    if args.name:
        client_data["business_name"] = args.name
    if args.niche:
        client_data["niche"] = args.niche
    if args.goals:
        client_data["goals"] = args.goals
    if args.email:
        client_data["email"] = args.email

    print(f"  Client: {client_data['business_name']}")
    print(f"  Niche:  {client_data['niche']}")
    print(f"  AI:     {env_info.get('ai_provider', '?')} / {env_info.get('ai_model', '?')}")
    print()

    # ── Run ──
    result = asyncio.run(
        run_production_pipeline(
            client_data,
            dry_run=args.dry_run,
            skip_tests=args.skip_tests,
            timeout_secs=args.timeout,
            cleanup=args.cleanup,
        )
    )

    # ── Report ──
    success = print_report(result)

    # ── Save report to file ──
    report_path = Path(__file__).parent / f"e2e_report_{int(time.time())}.json"
    with open(report_path, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\n  📄 Full report saved: {report_path.name}")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
