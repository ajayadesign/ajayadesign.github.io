"""
Pipeline Orchestrator — drives all 8 phases with DB logging and SSE events.
"""

import asyncio
import traceback
import logging
from datetime import datetime, timezone
from typing import Callable, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from api.models.build import Build, BuildPhase, BuildLog, BuildPage
from api.pipeline.phases import p01_repo, p02_council, p03_design, p04_generate, p05_assemble, p06_test, p07_deploy, p08_notify
from api.config import settings

logger = logging.getLogger(__name__)

PHASES = [
    (1, "repository",   "Create GitHub Repository"),
    (2, "council",      "AI Council — Strategist ↔ Critic"),
    (3, "design",       "Design System Generation"),
    (4, "generate",     "Page Content Generation"),
    (5, "assemble",     "Assembly & Link Stitching"),
    (6, "test",         "Quality Gate — Tests & Fixes"),
    (7, "deploy",       "Deploy to GitHub Pages"),
    (8, "notify",       "Telegram Notification"),
]


class BuildOrchestrator:
    """Runs the full 8-phase pipeline for one build."""

    def __init__(
        self,
        build: Build,
        session: AsyncSession,
        event_callback: Optional[Callable] = None,
    ):
        self.build = build
        self.session = session
        self._event_fn = event_callback
        self._log_seq = 0
        # Intermediate results
        self.repo: dict = {}
        self.blueprint: dict = {}
        self.creative_spec: dict = {}
        self.design_system: dict = {}
        self.page_results: list[dict] = []
        self.test_result: dict = {}
        self._page_records: list = []  # Track BuildPage objects locally

    # ── Public API ──────────────────────────────────────

    async def run(self) -> Build:
        """Execute the full pipeline. Returns updated Build."""
        self.build.status = "running"
        self.build.started_at = datetime.now(timezone.utc)
        await self._flush()
        self._sync_build_firebase()  # Sync running status to Firebase
        self._emit("build", {"status": "running", "build_id": self.build.short_id})

        try:
            await self._phase_1_repo()
            await self._phase_2_council()
            await self._phase_3_design()
            await self._phase_4_generate()
            await self._phase_5_assemble()
            await self._phase_6_test()
            await self._phase_7_deploy()
            await self._phase_8_notify()

            self.build.status = "complete"
            self.build.finished_at = datetime.now(timezone.utc)
            await self._flush()
            await self._sync_firebase("deployed")
            self._sync_build_firebase()  # Sync final status to Firebase
            self._emit("build", {"status": "complete", "build_id": self.build.short_id})
            self._log_msg("🎉 Build complete!", level="info", category="build")
            return self.build

        except Exception as exc:
            self.build.status = "failed"
            self.build.finished_at = datetime.now(timezone.utc)
            await self._flush()
            await self._sync_firebase("failed")
            self._sync_build_firebase()  # Sync failed status to Firebase
            self._emit("build", {"status": "failed", "error": str(exc)})
            self._log_msg(f"💥 Build failed: {exc}", level="error", category="build")
            logger.error("Build %s failed:\n%s", self.build.short_id, traceback.format_exc())
            raise

    # ── Individual Phases ───────────────────────────────

    async def _phase_1_repo(self):
        phase = await self._start_phase(1)
        self.repo = await p01_repo.create_repo(
            self.build.client_name,
            self.build.niche,
            self.build.goals or "",
            self.build.email or "",
            log_fn=lambda m: self._log_msg(m, category="repo"),
        )
        self.build.repo_name = self.repo["repo_name"]
        self.build.repo_full = self.repo["repo_full"]
        self.build.live_url = self.repo["live_url"]
        await self._end_phase(phase)

    async def _phase_2_council(self):
        phase = await self._start_phase(2)
        extra_context = {
            k: v for k, v in {
                "phone": getattr(self.build, "phone", None),
                "location": getattr(self.build, "location", None),
                "existing_website": getattr(self.build, "existing_website", None),
                "brand_colors": getattr(self.build, "brand_colors", None),
                "tagline": getattr(self.build, "tagline", None),
                "target_audience": getattr(self.build, "target_audience", None),
                "competitor_urls": getattr(self.build, "competitor_urls", None),
                "additional_notes": getattr(self.build, "additional_notes", None),
            }.items() if v
        } or None

        result = await p02_council.ai_council(
            self.build.client_name,
            self.build.niche,
            self.build.goals or "",
            self.build.email or "",
            max_rounds=settings.max_council_rounds,
            extra_context=extra_context,
            log_fn=lambda m: self._log_msg(m, category="council"),
            event_fn=lambda t, d: self._emit(t, d),
        )
        self.blueprint = result["blueprint"]
        self.creative_spec = result.get("creative_spec", {})
        self.build.blueprint = self.blueprint
        self.build.pages_count = len(self.blueprint.get("pages", []))
        await self._end_phase(phase)

    async def _phase_3_design(self):
        phase = await self._start_phase(3)
        self.design_system = await p03_design.generate_design_system(
            self.blueprint,
            creative_spec=self.creative_spec,
            log_fn=lambda m: self._log_msg(m, category="design"),
        )
        self.build.design_system = self.design_system
        await self._end_phase(phase)

    async def _phase_4_generate(self):
        phase = await self._start_phase(4)
        self.page_results = await p04_generate.generate_pages(
            self.blueprint,
            self.design_system,
            self.repo["dir"],
            creative_spec=self.creative_spec,
            log_fn=lambda m: self._log_msg(m, category="generate"),
            event_fn=lambda t, d: self._emit(t, d),
        )
        # Save page records
        for pr in self.page_results:
            page_record = BuildPage(
                build_id=self.build.id,
                slug=pr["slug"],
                title=next(
                    (p.get("title", pr["slug"]) for p in self.blueprint.get("pages", []) if p["slug"] == pr["slug"]),
                    pr["slug"],
                ),
                filename=pr["filename"],
                status=pr["status"],
                html_content=pr.get("html_content"),
                main_content=pr.get("main_content"),
                word_count=len(pr.get("main_content", "").split()) if pr.get("main_content") else 0,
            )
            self.session.add(page_record)
            self._page_records.append(page_record)
        await self._flush()
        await self._end_phase(phase)

    async def _phase_5_assemble(self):
        phase = await self._start_phase(5)
        await p05_assemble.assemble(
            self.blueprint,
            self.design_system,
            self.repo["dir"],
            creative_spec=self.creative_spec,
            log_fn=lambda m: self._log_msg(m, category="assemble"),
        )
        await self._end_phase(phase)

    async def _phase_6_test(self):
        phase = await self._start_phase(6)
        self.test_result = await p06_test.quality_gate(
            self.blueprint,
            self.design_system,
            self.repo["dir"],
            max_fix=settings.max_fix_attempts,
            log_fn=lambda m: self._log_msg(m, category="test"),
            event_fn=lambda t, d: self._emit(t, d),
        )
        # Update page records with test results (use local list, not lazy relationship)
        for pr in self.page_results:
            for page_record in self._page_records:
                if page_record.slug == pr["slug"]:
                    page_record.test_passed = self.test_result.get("passed", False)
                    page_record.fix_attempts = self.test_result.get("attempts", 0)
        await self._flush()
        await self._end_phase(phase)

    async def _phase_7_deploy(self):
        phase = await self._start_phase(7)
        await p07_deploy.deploy(
            self.repo,
            self.blueprint,
            log_fn=lambda m: self._log_msg(m, category="deploy"),
        )
        await self._end_phase(phase)

    async def _phase_8_notify(self):
        phase = await self._start_phase(8)
        page_count = len(self.blueprint.get("pages", []))
        await p08_notify.notify(
            self.build.client_name,
            self.build.niche,
            self.build.goals or "",
            self.build.email or "",
            self.build.repo_full or "",
            self.build.live_url or "",
            page_count,
            log_fn=lambda m: self._log_msg(m, category="notify"),
        )
        await self._end_phase(phase)

    # ── Helpers ─────────────────────────────────────────

    async def _start_phase(self, phase_number: int) -> BuildPhase:
        _, name, description = PHASES[phase_number - 1]
        self._log_msg(f"▶ Phase {phase_number}/8: {description}", category=name)
        self._emit("phase", {"number": phase_number, "name": name, "status": "running"})
        self._sync_phase_firebase(phase_number, name, "running")

        phase = BuildPhase(
            build_id=self.build.id,
            phase_number=phase_number,
            phase_name=name,
            status="running",
            started_at=datetime.now(timezone.utc),
        )
        self.session.add(phase)
        await self._flush()
        return phase

    async def _end_phase(self, phase: BuildPhase):
        phase.status = "complete"
        phase.finished_at = datetime.now(timezone.utc)
        await self._flush()
        self._emit("phase", {
            "number": phase.phase_number,
            "name": phase.phase_name,
            "status": "complete",
        })
        self._sync_phase_firebase(phase.phase_number, phase.phase_name, "complete")

    def _log_msg(
        self,
        message: str,
        level: str = "info",
        category: str = "general",
    ):
        self._log_seq += 1
        log_entry = BuildLog(
            build_id=self.build.id,
            sequence=self._log_seq,
            level=level,
            category=category,
            message=message,
        )
        self.session.add(log_entry)
        # Also log to Python logger
        getattr(logger, level, logger.info)(
            "[%s] %s", self.build.short_id, message
        )

    def _emit(self, event_type: str, data: dict):
        if self._event_fn:
            self._event_fn(event_type, data)

    async def _flush(self):
        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

    async def _sync_firebase(self, status: str):
        """Sync build status back to Firebase RTDB if firebase_id is present."""
        if not self.build.firebase_id:
            return
        try:
            from api.services.firebase import update_lead_status

            extra: dict = {}
            if status == "deployed":
                extra = {
                    "live_url": self.build.live_url or "",
                    "repo_full": self.build.repo_full or "",
                }
            elif status == "failed":
                extra = {"error": (self.build.error_message or "")[:500]}

            update_lead_status(self.build.firebase_id, status, extra)
            self._log_msg(f"🔥 Firebase synced: {status}", category="firebase")
        except Exception as e:
            self._log_msg(
                f"⚠️ Firebase sync failed: {e}", level="warning", category="firebase"
            )

    def _sync_build_firebase(self):
        """Sync the full build record to Firebase RTDB builds/ node."""
        try:
            from api.services.firebase import sync_build_to_firebase

            sync_build_to_firebase({
                "short_id": self.build.short_id,
                "client_name": self.build.client_name,
                "niche": self.build.niche,
                "email": self.build.email or "",
                "status": self.build.status,
                "created_at": self.build.created_at.isoformat() if self.build.created_at else "",
                "started_at": self.build.started_at.isoformat() if self.build.started_at else "",
                "finished_at": self.build.finished_at.isoformat() if self.build.finished_at else "",
                "live_url": self.build.live_url or "",
                "repo_full": self.build.repo_full or "",
                "pages_count": self.build.pages_count or 0,
            })
        except Exception as e:
            logger.debug("Firebase build sync failed (non-critical): %s", e)

    def _sync_phase_firebase(self, phase_number: int, phase_name: str, status: str):
        """Sync phase status to Firebase for real-time admin dashboard."""
        try:
            from api.services.firebase import sync_build_phase_to_firebase

            sync_build_phase_to_firebase(
                self.build.short_id, phase_number, phase_name, status
            )
        except Exception:
            pass  # Non-critical — dashboard will still work via SSE
