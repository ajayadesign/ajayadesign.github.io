"""
Pipeline Worker — Autonomous Prospect Processing Engine.

Continuously moves prospects through the pipeline:
  discovered → audited → enriched → queued → [pending_approval]

The ONLY step that requires human action is APPROVING the email for send.
Everything else is automated with rate limiting and recovery.

Supports MULTI-AGENT mode: spawn N concurrent workers, each processing
different prospects via row-level locking (SELECT ... FOR UPDATE SKIP LOCKED).

Status Flow:
  discovered + has_website → [audit] → audited
  discovered + no_website  → [recon] → enriched  (skip audit — no site to audit)
  audited                  → [recon] → enriched
  enriched + has_email     → [enqueue] → queued + pending_approval email

Recovery:
  - Detects prospects stuck in intermediate states for too long
  - Resets stuck prospects back to a safe state for re-processing
  - All operations are idempotent and crash-safe
"""

import asyncio
import logging
import time
from collections import deque
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select, update, func, and_, or_, text

from api.database import async_session_factory
from api.models.prospect import Prospect, OutreachEmail

logger = logging.getLogger("outreach.pipeline")

# ─── Configuration ─────────────────────────────────────────────────────
PIPELINE_INTERVAL_SEC = 120          # Run every 2 minutes
AUDIT_BATCH_SIZE = 5                 # Max audits per cycle per agent
RECON_BATCH_SIZE = 5                 # Max recons per cycle per agent
ENQUEUE_BATCH_SIZE = 10              # Max enqueue per cycle per agent
ENRICH_BATCH_SIZE = 3                # Max deep enrichments per cycle per agent
SCORE_BATCH_SIZE = 20                # Max scores per cycle per agent
BACKFILL_BATCH_SIZE = 5              # Max backfill enrichments per cycle per agent
ACTIVATE_BATCH_SIZE = 20             # Max imported→enriched activations per cycle
STUCK_THRESHOLD_MIN = 15             # Minutes before a task is considered stuck
MAX_RETRIES = 3                      # Max retries for any single prospect
MAX_AGENTS = 5                       # Maximum number of concurrent agents

# ─── Crawler Gate ──────────────────────────────────────────────────────
# The crawler (Google Maps API discovery) is OFF by default.
# User must explicitly enable it via the dashboard Start button.
# The pipeline worker (audit/recon/enqueue/recovery) always runs.
_crawl_enabled = False


def set_crawl_enabled(enabled: bool):
    """Enable or disable the auto-crawl phase (Maps API discovery)."""
    global _crawl_enabled
    _crawl_enabled = enabled
    logger.info("Crawler %s", "ENABLED" if enabled else "DISABLED")


def is_crawl_enabled() -> bool:
    """Check if the crawler is currently enabled."""
    return _crawl_enabled

# Rate limits (respect API quotas)
AUDIT_DELAY_SEC = 3                  # Seconds between audits
RECON_DELAY_SEC = 2                  # Seconds between recons
ENQUEUE_DELAY_SEC = 0.5              # Seconds between enqueues
ENRICH_DELAY_SEC = 3                 # Seconds between deep enrichments


# ─── Pipeline Log Ring Buffer ──────────────────────────────────────────
# In-memory ring buffer that captures real pipeline events for the Mission
# Control terminal (replaces the fake/simulated log lines).
_PIPELINE_LOG_BUFFER: deque = deque(maxlen=200)


def pipeline_log(tag: str, msg: str, biz: str = "", extra: dict = None):
    """Append a real pipeline event to the ring buffer."""
    entry = {
        "ts": datetime.now(timezone.utc).strftime("%H:%M:%S"),
        "tag": tag.upper(),
        "msg": msg,
        "biz": biz,
        "time": time.time(),
    }
    if extra:
        entry.update(extra)
    _PIPELINE_LOG_BUFFER.append(entry)


def get_pipeline_logs(since: float = 0, limit: int = 100) -> list:
    """Get recent pipeline log entries, optionally after a timestamp."""
    if since:
        return [e for e in _PIPELINE_LOG_BUFFER if e.get("time", 0) > since][-limit:]
    return list(_PIPELINE_LOG_BUFFER)[-limit:]


class PipelineWorker:
    """
    Autonomous background worker that processes prospects through the full pipeline.
    
    Runs on a timer, picks up work in priority order, respects rate limits,
    and recovers from any bad state.

    Supports multi-agent: each worker has an agent_id and uses row-level
    locking to avoid processing the same prospect as another worker.
    """

    def __init__(self, agent_id: int = 0):
        self._agent_id = agent_id
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._cycle_count = 0
        self._stats = {
            "audits_completed": 0,
            "recons_completed": 0,
            "enqueues_completed": 0,
            "crawls_completed": 0,
            "enrichments_completed": 0,
            "backfill_completed": 0,
            "scores_completed": 0,
            "recoveries": 0,
            "errors": 0,
            "last_cycle": None,
            "started_at": None,
        }

    @property
    def agent_id(self):
        return self._agent_id

    @property
    def stats(self):
        return {
            **self._stats,
            "running": self._running,
            "cycle_count": self._cycle_count,
            "agent_id": self._agent_id,
        }

    def start(self):
        """Start the pipeline worker loop."""
        if self._running:
            logger.warning("Pipeline agent #%d already running", self._agent_id)
            return
        self._running = True
        self._stats["started_at"] = datetime.now(timezone.utc).isoformat()
        self._task = asyncio.create_task(self._loop())
        logger.info("🚀 Pipeline agent #%d started (interval=%ds)", self._agent_id, PIPELINE_INTERVAL_SEC)

    def stop(self):
        """Stop the pipeline worker gracefully."""
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("Pipeline agent #%d stopped", self._agent_id)

    async def _loop(self):
        """Main worker loop — runs forever until stopped."""
        # Small initial delay to let the API fully boot
        # Stagger agents so they don't all hit the DB at once
        await asyncio.sleep(10 + self._agent_id * 5)
        
        while self._running:
            try:
                await self._run_cycle()
            except asyncio.CancelledError:
                logger.info("Pipeline agent #%d cancelled", self._agent_id)
                break
            except Exception as e:
                self._stats["errors"] += 1
                logger.error("Pipeline agent #%d cycle error: %s", self._agent_id, e, exc_info=True)

            await asyncio.sleep(PIPELINE_INTERVAL_SEC)

    async def _run_cycle(self):
        """Single pipeline cycle: recover → crawl → audit → recon → enqueue."""
        self._cycle_count += 1
        self._stats["last_cycle"] = datetime.now(timezone.utc).isoformat()
        
        cycle_start = time.time()
        pipeline_log("SYS", f"Agent #{self._agent_id} — cycle #{self._cycle_count} started")

        # Phase 0: Recovery — fix any stuck/bad states
        recovered = await self._recover_stuck_prospects()

        # Phase 0.5: Auto-crawl — only runs when crawler is enabled by user
        crawled = 0
        if _crawl_enabled:
            crawled = await self._process_crawl()
        else:
            pipeline_log("CRAWL", "Crawler paused — skipping auto-crawl (use Start Agent to enable)")
        
        # Phase 0.7: Auto-activate imported prospects that already have emails
        activated = await self._process_auto_activate()

        # Phase 1: Audit discovered prospects that have websites
        audited = await self._process_audits()
        
        # Phase 2: Deep Enrichment — GBP, DNS, social, records, ads/hiring
        enriched = await self._process_deep_enrichments()

        # Phase 2b: Backfill — enrich existing prospects that skipped deep enrichment
        backfilled = await self._process_backfill_enrichments()

        # Phase 3: Recon — find owner info for audited prospects AND no-website discovered prospects
        reconned = await self._process_recons()
        
        # Phase 4: Score — calculate Website Purchase Likelihood Score
        scored = await self._process_scoring()

        # Phase 5: Enqueue — generate email drafts for enriched prospects with emails
        enqueued = await self._process_enqueues()
        
        elapsed = round(time.time() - cycle_start, 1)
        
        pipeline_log("SYS", f"Cycle #{self._cycle_count} done in {elapsed}s — activated={activated} crawled={crawled} audited={audited} enriched={enriched} backfilled={backfilled} reconned={reconned} scored={scored} enqueued={enqueued}")

        if recovered or activated or crawled or audited or enriched or backfilled or reconned or scored or enqueued:
            logger.info(
                "Agent #%d cycle #%d done in %.1fs: recovered=%d, activated=%d, crawled=%d, audited=%d, enriched=%d, backfilled=%d, reconned=%d, scored=%d, enqueued=%d",
                self._agent_id, self._cycle_count, elapsed, recovered, activated, crawled, audited, enriched, backfilled, reconned, scored, enqueued,
            )
            # Push stats to Firebase
            await self._push_stats()

    # ── Phase 0: Recovery ──────────────────────────────────────────────

    async def _recover_stuck_prospects(self) -> int:
        """
        Find and fix prospects stuck in bad states.
        
        Recovery rules:
        - Prospect with status 'auditing' for > STUCK_THRESHOLD_MIN → reset to 'discovered'
        - Prospect with status 'recon_in_progress' for > STUCK_THRESHOLD_MIN → reset to prior state
        - OutreachEmail stuck in 'sending' → reset to 'approved' 
        - OutreachEmail stuck in 'failed' with retries left → reset to 'approved'
        """
        recovered = 0
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=STUCK_THRESHOLD_MIN)

        async with async_session_factory() as db:
            # --- Recover stuck audits ---
            # If website_status was set to 'auditing' but never completed
            result = await db.execute(
                select(Prospect).where(
                    Prospect.status == "discovered",
                    Prospect.has_website == True,
                    Prospect.website_url.isnot(None),
                    Prospect.updated_at < cutoff,
                    # Has been in this state too long — likely a stuck audit
                )
            )
            # These are just sitting as discovered — they'll be re-picked by audit.
            # No reset needed, just ensure they're eligible.

            # --- Recover stuck enrichments ---
            result = await db.execute(
                select(Prospect).where(
                    Prospect.status == "enriching",
                    Prospect.updated_at < cutoff,
                )
            )
            stuck_enriching = result.scalars().all()
            for p in stuck_enriching:
                p.status = "audited"  # Reset to audited so enrichment retries
                p.updated_at = datetime.now(timezone.utc)
                recovered += 1
                pipeline_log("RECOVER", f"Stuck enrichment → reset to audited: {p.business_name}", biz=p.business_name)

            # --- Recover stuck emails ---
            result = await db.execute(
                select(OutreachEmail).where(
                    OutreachEmail.status == "failed",
                    OutreachEmail.error_message.isnot(None),
                    OutreachEmail.created_at < cutoff,
                )
            )
            failed_emails = result.scalars().all()
            for email in failed_emails:
                # Reset failed emails to pending_approval so user can review the error and retry
                email.status = "pending_approval"
                email.error_message = f"[AUTO-RECOVERED] Previous error: {email.error_message}"
                recovered += 1
                logger.info("Recovered failed email %s for prospect %s", email.id, email.prospect_id)

            # --- Recover bounced emails — use Hunter.io for high-value, skip low-value ---
            result = await db.execute(
                select(OutreachEmail).where(
                    OutreachEmail.status == "bounced",
                    OutreachEmail.created_at > cutoff - timedelta(hours=24),
                )
            )
            bounced = result.scalars().all()
            bounce_recon_queue = []
            for email in bounced:
                prospect_result = await db.execute(
                    select(Prospect).where(Prospect.id == email.prospect_id)
                )
                prospect = prospect_result.scalar_one_or_none()
                if prospect and prospect.owner_email:
                    old_email = prospect.owner_email
                    prospect.email_verified = False
                    prospect.notes = (prospect.notes or "") + f"\n[{datetime.now().strftime('%Y-%m-%d')}] Email bounced: {old_email}"
                    # High-value bounce → queue for Hunter.io re-recon
                    if (prospect.priority_score or 0) >= 35:
                        prospect.owner_email = None
                        prospect.email_source = None
                        prospect.status = "audited"  # Reset to allow re-recon
                        bounce_recon_queue.append(str(prospect.id))
                        pipeline_log("BOUNCE", f"High-value bounce → queued for re-recon via Hunter.io", old_email)
                    else:
                        prospect.status = "dead"
                        pipeline_log("BOUNCE", f"Low-value bounce → marked dead", old_email)
                    # Cancel any remaining scheduled emails
                    email.status = "cancelled"
                    recovered += 1

            if recovered:
                await db.commit()

            # Trigger re-recon for high-value bounced prospects (outside transaction)
            if bounce_recon_queue:
                from api.services.recon_engine import recon_prospect
                for pid in bounce_recon_queue:
                    try:
                        result = await recon_prospect(pid)
                        if result and result.get("owner_email"):
                            pipeline_log("BOUNCE", f"Re-recon found new email", result["owner_email"])
                    except Exception as e:
                        logger.error("Bounce re-recon failed for %s: %s", pid, e)
                    await asyncio.sleep(1)

        self._stats["recoveries"] += recovered
        return recovered

    # ── Phase 0.5: Auto-Crawl ──────────────────────────────────────────

    async def _process_crawl(self) -> int:
        """
        Auto-crawl incomplete rings to discover new businesses.
        
        Finds rings that have un-crawled categories and runs ONE category per cycle
        to keep the pipeline moving without monopolizing API quota.
        """
        from api.services.crawl_engine import crawl_ring
        from api.models.prospect import GeoRing

        async with async_session_factory() as db:
            # Find the first active/pending ring with incomplete categories
            result = await db.execute(
                select(GeoRing).where(
                    GeoRing.status.in_(["active", "pending"]),
                ).order_by(GeoRing.ring_number)
            )
            rings = result.scalars().all()

        if not rings:
            return 0

        # Pick the first ring that still has work to do
        target_ring = None
        for ring in rings:
            cats_done = ring.categories_done or []
            cats_total = ring.categories_total or []
            if len(cats_done) < len(cats_total):
                target_ring = ring
                break

        if not target_ring:
            return 0

        try:
            cats_done_len = len(target_ring.categories_done or [])
            cats_total_len = len(target_ring.categories_total or [])
            pipeline_log("CRAWL", f"Auto-crawl: {target_ring.name} ({cats_done_len}/{cats_total_len} categories done)")
            logger.info("Auto-crawl: ring=%s (%d/%d categories done)",
                        target_ring.name, cats_done_len, cats_total_len)
            result = await crawl_ring(str(target_ring.id))
            found = result.get("total_found", 0)
            self._stats["crawls_completed"] += 1
            if found > 0:
                pipeline_log("CRAWL", f"Discovered {found} new prospects in {target_ring.name}")
                logger.info("Auto-crawl: discovered %d new prospects in ring=%s",
                            found, target_ring.name)
            return found
        except Exception as e:
            logger.error("Auto-crawl error for ring %s: %s", target_ring.name, e)
            self._stats["errors"] += 1
            return 0

    # ── Phase 0.7: Auto-Activate Imported Prospects ──────────────────

    async def _process_auto_activate(self) -> int:
        """
        Move imported prospects (with owner_email) → enriched so the
        enqueue phase picks them up and creates step-1 email drafts.

        This bridges the gap for bulk-imported prospects that already
        have emails but never entered the discovery→audit→recon flow.

        Uses FOR UPDATE SKIP LOCKED so concurrent agents claim
        different rows.
        """
        from sqlalchemy import update as sql_update

        async with async_session_factory() as db:
            result = await db.execute(
                select(Prospect.id, Prospect.business_name)
                .where(
                    Prospect.status == "imported",
                    Prospect.owner_email.isnot(None),
                )
                .order_by(Prospect.created_at)
                .limit(ACTIVATE_BATCH_SIZE)
                .with_for_update(skip_locked=True)
            )
            rows = result.fetchall()

            if not rows:
                return 0

            ids = [r[0] for r in rows]
            await db.execute(
                sql_update(Prospect)
                .where(Prospect.id.in_(ids))
                .values(status="enriched")
            )
            await db.commit()

        for row in rows:
            pipeline_log("ACTIVATE", f"Auto-activated {row[1] or 'Unknown'} → enriched", biz=row[1] or 'Unknown')
        pipeline_log("ACTIVATE", f"Auto-activated {len(rows)} imported prospects → enriched")
        return len(rows)

    # ── Phase 1: Audits ────────────────────────────────────────────────

    async def _process_audits(self) -> int:
        """Audit discovered prospects that have websites."""
        from api.services.intel_engine import audit_prospect

        # Get top prospects needing audit (exclude already-unreachable sites)
        # FOR UPDATE SKIP LOCKED so concurrent agents claim different rows
        async with async_session_factory() as db:
            result = await db.execute(
                select(Prospect.id).where(
                    Prospect.status == "discovered",
                    Prospect.has_website == True,
                    Prospect.website_url.isnot(None),
                    or_(
                        Prospect.notes.is_(None),
                        ~Prospect.notes.ilike("%unreachable%"),
                    ),
                ).order_by(
                    Prospect.priority_score.desc()
                ).limit(AUDIT_BATCH_SIZE)
                .with_for_update(skip_locked=True)
            )
            prospect_ids = [str(r[0]) for r in result.fetchall()]

        if not prospect_ids:
            return 0

        # Load names for logging
        name_map = {}
        async with async_session_factory() as db:
            result = await db.execute(
                select(Prospect.id, Prospect.business_name, Prospect.website_url)
                .where(Prospect.id.in_([__import__('uuid').UUID(i) for i in prospect_ids]))
            )
            for row in result.fetchall():
                name_map[str(row[0])] = (row[1] or 'Unknown', row[2] or '')

        count = 0
        for pid in prospect_ids:
            biz_name, url = name_map.get(pid, ('Unknown', ''))
            pipeline_log("AUDIT", f"Lighthouse audit initiated → {url or biz_name}", biz=biz_name)
            try:
                result = await audit_prospect(pid)
                if result:
                    count += 1
                    self._stats["audits_completed"] += 1
                    perf = result.get('perf_score') or result.get('score_overall', '?')
                    pipeline_log("AUDIT", f"Audit complete → {biz_name}: perf={perf}", biz=biz_name)
            except Exception as e:
                logger.error("Audit failed for %s: %s", pid, e)
                pipeline_log("AUDIT", f"Audit FAILED → {biz_name}: {str(e)[:60]}", biz=biz_name)
                self._stats["errors"] += 1
            await asyncio.sleep(AUDIT_DELAY_SEC)

        return count

    # ── Phase 2: Deep Enrichment ───────────────────────────────────────

    async def _process_deep_enrichments(self) -> int:
        """
        Run deep enrichment (GBP, DNS, social, records, ads/hiring) on
        audited prospects that haven't been enriched yet.
        """
        from api.services.deep_enrichment import deep_enrich_prospect

        # FOR UPDATE SKIP LOCKED so concurrent agents claim different rows
        async with async_session_factory() as db:
            result = await db.execute(
                select(Prospect.id).where(
                    Prospect.status == "audited",
                    Prospect.enriched_at.is_(None),
                    Prospect.has_website == True,
                ).order_by(
                    Prospect.priority_score.desc()
                ).limit(ENRICH_BATCH_SIZE)
                .with_for_update(skip_locked=True)
            )
            prospect_ids = [str(r[0]) for r in result.fetchall()]

        if not prospect_ids:
            return 0

        # Load names for logging
        name_map = {}
        async with async_session_factory() as db:
            result = await db.execute(
                select(Prospect.id, Prospect.business_name)
                .where(Prospect.id.in_([__import__('uuid').UUID(i) for i in prospect_ids]))
            )
            for row in result.fetchall():
                name_map[str(row[0])] = row[1] or 'Unknown'

        count = 0
        for pid in prospect_ids:
            biz_name = name_map.get(pid, 'Unknown')
            pipeline_log("ENRICH", f"Deep enrichment started → {biz_name}", biz=biz_name)
            try:
                enrichment = await deep_enrich_prospect(pid)
                if enrichment:
                    count += 1
                    self._stats["enrichments_completed"] += 1
                    signals = len([k for k, v in enrichment.items() if v])
                    pipeline_log("ENRICH", f"Enrichment complete → {biz_name}: {signals} data sources", biz=biz_name)
            except Exception as e:
                logger.error("Deep enrichment failed for %s: %s", pid, e)
                pipeline_log("ENRICH", f"Enrichment FAILED → {biz_name}: {str(e)[:60]}", biz=biz_name)
                self._stats["errors"] += 1
            await asyncio.sleep(ENRICH_DELAY_SEC)

        return count

    # ── Phase 2b: Backfill Enrichment ──────────────────────────────────

    async def _process_backfill_enrichments(self) -> int:
        """
        Backfill deep enrichment for existing prospects that were
        already past the audited stage before deep enrichment was added.
        Preserves their current pipeline status.

        Targets prospects in enriched/queued/contacted/replied/meeting_booked
        that have no enrichment data yet.  Once all are backfilled this
        phase becomes a no-op automatically.
        """
        from api.services.deep_enrichment import backfill_enrich_prospect
        from api.services.scoring_engine import score_prospect

        backfill_statuses = [
            "enriched", "queued", "contacted", "replied",
            "meeting_booked", "promoted",
        ]

        async with async_session_factory() as db:
            result = await db.execute(
                select(Prospect.id).where(
                    Prospect.status.in_(backfill_statuses),
                    or_(
                        Prospect.enrichment.is_(None),
                        Prospect.enrichment == {},
                    ),
                ).order_by(
                    Prospect.wp_score.desc().nullslast(),
                    Prospect.priority_score.desc(),
                ).limit(BACKFILL_BATCH_SIZE)
                .with_for_update(skip_locked=True)
            )
            prospect_ids = [str(r[0]) for r in result.fetchall()]

        if not prospect_ids:
            return 0

        # Load names for logging
        name_map = {}
        async with async_session_factory() as db:
            result = await db.execute(
                select(Prospect.id, Prospect.business_name, Prospect.status)
                .where(Prospect.id.in_([__import__('uuid').UUID(i) for i in prospect_ids]))
            )
            for row in result.fetchall():
                name_map[str(row[0])] = (row[1] or 'Unknown', row[2])

        remaining = await self._count_backfill_remaining()
        pipeline_log(
            "BACKFILL",
            f"Starting backfill batch: {len(prospect_ids)} prospects ({remaining} total remaining)",
        )

        count = 0
        for pid in prospect_ids:
            biz_name, status = name_map.get(pid, ('Unknown', 'unknown'))
            pipeline_log("BACKFILL", f"Enriching → {biz_name} (status={status})", biz=biz_name)
            try:
                enrichment = await backfill_enrich_prospect(pid)
                if enrichment:
                    count += 1
                    self._stats["backfill_completed"] += 1
                    signals = len([k for k, v in enrichment.items() if v])
                    pipeline_log("BACKFILL", f"Enriched → {biz_name}: {signals} data sources", biz=biz_name)

                    # Score immediately after backfill enrichment
                    try:
                        score_result = await score_prospect(pid)
                        if score_result:
                            self._stats["scores_completed"] += 1
                            pipeline_log(
                                "BACKFILL",
                                f"Scored → {biz_name}: wp_score={score_result['wp_score']} ({score_result['tier']})",
                                biz=biz_name,
                            )
                    except Exception as se:
                        logger.error("Backfill scoring failed for %s: %s", pid, se)
            except Exception as e:
                logger.error("Backfill enrichment failed for %s: %s", pid, e)
                pipeline_log("BACKFILL", f"FAILED → {biz_name}: {str(e)[:60]}", biz=biz_name)
                self._stats["errors"] += 1
            await asyncio.sleep(ENRICH_DELAY_SEC)

        return count

    async def _count_backfill_remaining(self) -> int:
        """Count how many prospects still need backfill enrichment."""
        async with async_session_factory() as db:
            result = await db.execute(
                select(func.count()).select_from(Prospect).where(
                    Prospect.status.in_(["enriched", "queued", "contacted", "replied", "meeting_booked", "promoted"]),
                    or_(
                        Prospect.enrichment.is_(None),
                        Prospect.enrichment == {},
                    ),
                )
            )
            return result.scalar() or 0

    # ── Phase 3: Recon ─────────────────────────────────────────────────

    async def _process_recons(self) -> int:
        """
        Recon prospects to find owner contact info.
        
        Handles TWO paths:
        1. audited prospects → normal flow
        2. discovered + no website → skip audit, go straight to recon
        """
        from api.services.recon_engine import recon_prospect

        async with async_session_factory() as db:
            # Fast-track: audited prospects that ALREADY have owner_email → enriched
            already_have_email = await db.execute(
                select(Prospect.id).where(
                    Prospect.status == "audited",
                    Prospect.owner_email.isnot(None),
                )
            )
            fast_track_ids = [r[0] for r in already_have_email.fetchall()]
            if fast_track_ids:
                await db.execute(
                    update(Prospect)
                    .where(Prospect.id.in_(fast_track_ids))
                    .values(status="enriched", updated_at=datetime.now(timezone.utc))
                )
                await db.commit()
                logger.info("Fast-tracked %d audited prospects (already have email) → enriched", len(fast_track_ids))

            # Path 1: Audited prospects needing recon
            # FOR UPDATE SKIP LOCKED so concurrent agents claim different rows
            result1 = await db.execute(
                select(Prospect.id).where(
                    Prospect.status == "audited",
                    Prospect.owner_email.is_(None),
                ).order_by(
                    Prospect.priority_score.desc()
                ).limit(RECON_BATCH_SIZE)
                .with_for_update(skip_locked=True)
            )
            audited_ids = [str(r[0]) for r in result1.fetchall()]

            # Path 2: No-website prospects — skip audit, go directly to recon
            # Also includes website-down prospects (has URL but site unreachable)
            remaining = max(0, RECON_BATCH_SIZE - len(audited_ids))
            nosite_ids = []
            if remaining > 0:
                result2 = await db.execute(
                    select(Prospect.id).where(
                        or_(
                            # No website at all
                            and_(
                                Prospect.status == "discovered",
                                or_(
                                    Prospect.has_website == False,
                                    Prospect.website_url.is_(None),
                                ),
                            ),
                            # Website exists but is down/unreachable
                            and_(
                                Prospect.status == "discovered",
                                Prospect.has_website == True,
                                Prospect.notes.ilike("%unreachable%"),
                            ),
                        ),
                    ).order_by(
                        Prospect.priority_score.desc()
                    ).limit(remaining)
                    .with_for_update(skip_locked=True)
                )
                nosite_ids = [str(r[0]) for r in result2.fetchall()]

        prospect_ids = audited_ids + nosite_ids
        if not prospect_ids:
            return 0

        # For no-website prospects, we need to fast-track their status to "audited"
        # so recon_prospect will transition them to "enriched"
        if nosite_ids:
            async with async_session_factory() as db:
                await db.execute(
                    update(Prospect)
                    .where(Prospect.id.in_([__import__('uuid').UUID(i) for i in nosite_ids]))
                    .values(status="audited", updated_at=datetime.now(timezone.utc))
                )
                await db.commit()
            logger.info("Fast-tracked %d no-website prospects to 'audited' for recon", len(nosite_ids))

        # Load names for logging
        name_map = {}
        async with async_session_factory() as db:
            result = await db.execute(
                select(Prospect.id, Prospect.business_name, Prospect.website_url)
                .where(Prospect.id.in_([__import__('uuid').UUID(i) for i in prospect_ids]))
            )
            for row in result.fetchall():
                name_map[str(row[0])] = (row[1] or 'Unknown', row[2] or '')

        count = 0
        for pid in prospect_ids:
            biz_name, url = name_map.get(pid, ('Unknown', ''))
            pipeline_log("RECON", f"Enriching contact → {biz_name}", biz=biz_name)
            try:
                result = await recon_prospect(pid)
                if result and result.get("owner_email"):
                    count += 1
                    self._stats["recons_completed"] += 1
                    owner = result.get('owner_name', '?')
                    pipeline_log("RECON", f"Found: {owner} @ {biz_name} ({result['owner_email']})", biz=biz_name)
                else:
                    # Track failed recon attempts — mark dead after 3 tries
                    async with async_session_factory() as fail_db:
                        p = await fail_db.get(Prospect, __import__('uuid').UUID(pid))
                        if p:
                            attempts = (p.tags or []).count('recon_fail') + 1
                            p.tags = (p.tags or []) + ['recon_fail']
                            if attempts >= 3:
                                p.status = 'dead'
                                p.notes = (p.notes or '') + f' | Recon failed {attempts}x — marked dead'
                                pipeline_log("RECON", f"Giving up on {biz_name} after {attempts} attempts → dead", biz=biz_name)
                            await fail_db.commit()
                    pipeline_log("RECON", f"No contact found for {biz_name}", biz=biz_name)
            except Exception as e:
                logger.error("Recon failed for %s: %s", pid, e)
                pipeline_log("RECON", f"Recon FAILED → {biz_name}: {str(e)[:60]}", biz=biz_name)
                self._stats["errors"] += 1
            await asyncio.sleep(RECON_DELAY_SEC)

        return count

    # ── Phase 4: Scoring ───────────────────────────────────────────────

    async def _process_scoring(self) -> int:
        """
        Calculate wp_score for enriched prospects that haven't been scored yet.
        Also scores queued/contacted prospects that gained new enrichment data.
        """
        from api.services.scoring_engine import score_prospect

        # FOR UPDATE SKIP LOCKED so concurrent agents claim different rows
        async with async_session_factory() as db:
            result = await db.execute(
                select(Prospect.id).where(
                    Prospect.wp_score.is_(None),
                    Prospect.status.in_(["enriched", "queued", "contacted"]),
                ).order_by(
                    Prospect.created_at.asc()
                ).limit(SCORE_BATCH_SIZE)
                .with_for_update(skip_locked=True)
            )
            prospect_ids = [str(r[0]) for r in result.fetchall()]

        if not prospect_ids:
            return 0

        # Load names for logging
        name_map = {}
        async with async_session_factory() as db:
            result = await db.execute(
                select(Prospect.id, Prospect.business_name)
                .where(Prospect.id.in_([__import__('uuid').UUID(i) for i in prospect_ids]))
            )
            for row in result.fetchall():
                name_map[str(row[0])] = row[1] or 'Unknown'

        count = 0
        for pid in prospect_ids:
            biz_name = name_map.get(pid, 'Unknown')
            try:
                result = await score_prospect(pid)
                if result:
                    count += 1
                    self._stats["scores_completed"] += 1
                    pipeline_log(
                        "SCORE",
                        f"wp_score={result['wp_score']} ({result['tier'].upper()}) → {biz_name}",
                        biz=biz_name,
                    )
            except Exception as e:
                logger.error("Scoring failed for %s: %s", pid, e)
                self._stats["errors"] += 1

        return count

    # ── Phase 5: Enqueue ───────────────────────────────────────────────

    async def _process_enqueues(self) -> int:
        """
        Generate email drafts (pending_approval) for enriched prospects.
        
        Uses wp_score to filter (only score >= 40) and to select the best
        email template based on the prospect's strongest signal cluster.
        """
        from api.services.cadence_engine import enqueue_prospect

        # Collect owner_emails that already have active outreach to avoid
        # emailing the same person through different prospect records
        async with async_session_factory() as db:
            already_emailed = await db.execute(
                select(Prospect.owner_email)
                .join(OutreachEmail, OutreachEmail.prospect_id == Prospect.id)
                .where(
                    OutreachEmail.sequence_step == 1,
                    OutreachEmail.status.in_(["sent", "pending_approval", "approved"]),
                )
                .distinct()
            )
            skip_emails = {r[0].lower() for r in already_emailed.fetchall() if r[0]}

        # 50/50 split: half contractors, half crawler-found local businesses.
        # If one pool has fewer prospects, the other fills the remaining slots.
        half = ENQUEUE_BATCH_SIZE // 2  # 5 each by default

        _base_filter = [
            Prospect.status == "enriched",
            Prospect.owner_email.isnot(None),
            or_(
                Prospect.wp_score >= 40,
                Prospect.wp_score.is_(None),  # backward compat: unscored prospects
            ),
        ]
        _ordering = [
            Prospect.wp_score.desc().nullslast(),
            Prospect.priority_score.desc(),
        ]

        async with async_session_factory() as db:
            # Contractor pool
            contractor_result = await db.execute(
                select(Prospect.id).where(
                    *_base_filter,
                    Prospect.source == "contractor_registry",
                ).order_by(*_ordering)
                .limit(ENQUEUE_BATCH_SIZE)  # fetch up to full batch as fallback
                .with_for_update(skip_locked=True)
            )
            contractor_ids = [str(r[0]) for r in contractor_result.fetchall()]

            # Local business pool (crawler-found)
            local_result = await db.execute(
                select(Prospect.id).where(
                    *_base_filter,
                    or_(
                        Prospect.source != "contractor_registry",
                        Prospect.source.is_(None),
                    ),
                ).order_by(*_ordering)
                .limit(ENQUEUE_BATCH_SIZE)
                .with_for_update(skip_locked=True)
            )
            local_ids = [str(r[0]) for r in local_result.fetchall()]

        # Take half from each; if one pool is short, the other fills the gap
        c_take = min(len(contractor_ids), half)
        l_take = min(len(local_ids), half)
        c_take = min(len(contractor_ids), ENQUEUE_BATCH_SIZE - l_take)
        l_take = min(len(local_ids), ENQUEUE_BATCH_SIZE - c_take)
        prospect_ids = contractor_ids[:c_take] + local_ids[:l_take]

        if not prospect_ids:
            return 0

        # Load names for logging
        name_map = {}
        async with async_session_factory() as db:
            result = await db.execute(
                select(Prospect.id, Prospect.business_name, Prospect.owner_email)
                .where(Prospect.id.in_([__import__('uuid').UUID(i) for i in prospect_ids]))
            )
            for row in result.fetchall():
                name_map[str(row[0])] = (row[1] or 'Unknown', row[2] or '')

        count = 0
        for pid in prospect_ids:
            biz_name, email = name_map.get(pid, ('Unknown', ''))
            # Skip if this owner_email already has active outreach
            if email and email.lower() in skip_emails:
                pipeline_log("EMAIL", f"Skipped {biz_name} — {email} already has outreach", biz=biz_name)
                continue
            pipeline_log("EMAIL", f'Composing email for {biz_name} (wp_score-driven template)', biz=biz_name)
            try:
                email_id = await enqueue_prospect(pid)
                if email_id:
                    count += 1
                    self._stats["enqueues_completed"] += 1
                    skip_emails.add(email.lower())  # prevent same email in this batch
                    pipeline_log("EMAIL", f"Email queued → {email} (pending approval)", biz=biz_name)
            except Exception as e:
                logger.error("Enqueue failed for %s: %s", pid, e)
                pipeline_log("EMAIL", f"Enqueue FAILED → {biz_name}: {str(e)[:60]}", biz=biz_name)
                self._stats["errors"] += 1
            await asyncio.sleep(ENQUEUE_DELAY_SEC)

        return count

    # ── Firebase Stats Push ─────────────────────────────────────────

    async def _push_stats(self):
        """Push pipeline worker stats to Firebase for dashboard display."""
        try:
            from api.services.firebase_summarizer import _ref
            ref = _ref(f"outreach/pipeline_worker/agent_{self._agent_id}")
            if ref:
                ref.set({
                    **self._stats,
                    "running": self._running,
                    "cycle_count": self._cycle_count,
                    "agent_id": self._agent_id,
                    "updated_at": int(time.time()),
                })
        except Exception as e:
            logger.debug("Firebase stats push failed: %s", e)


# ═══════════════════════════════════════════════════════════════════════
# Multi-Agent Manager
# ═══════════════════════════════════════════════════════════════════════

class PipelineAgentManager:
    """
    Manages multiple concurrent PipelineWorker agents.
    
    - Agent #0 is always created on startup (singleton behavior preserved)
    - Additional agents can be spawned/stopped via API
    - Each agent processes different prospects (staggered timing + locking)
    - Stats are aggregated across all agents
    """

    def __init__(self):
        self._agents: dict[int, PipelineWorker] = {}

    @property
    def agent_count(self) -> int:
        return sum(1 for a in self._agents.values() if a._running)

    @property
    def stats(self) -> dict:
        """Aggregated stats across all agents."""
        agg = {
            "audits_completed": 0,
            "recons_completed": 0,
            "enqueues_completed": 0,
            "crawls_completed": 0,
            "enrichments_completed": 0,
            "backfill_completed": 0,
            "scores_completed": 0,
            "recoveries": 0,
            "errors": 0,
            "last_cycle": None,
            "started_at": None,
            "running": False,
            "cycle_count": 0,
            "agent_count": self.agent_count,
            "agents": [],
        }
        for agent in self._agents.values():
            s = agent.stats
            agg["audits_completed"] += s.get("audits_completed", 0)
            agg["recons_completed"] += s.get("recons_completed", 0)
            agg["enqueues_completed"] += s.get("enqueues_completed", 0)
            agg["crawls_completed"] += s.get("crawls_completed", 0)
            agg["enrichments_completed"] += s.get("enrichments_completed", 0)
            agg["backfill_completed"] += s.get("backfill_completed", 0)
            agg["scores_completed"] += s.get("scores_completed", 0)
            agg["recoveries"] += s.get("recoveries", 0)
            agg["errors"] += s.get("errors", 0)
            agg["cycle_count"] += s.get("cycle_count", 0)
            if s.get("running"):
                agg["running"] = True
            # Track earliest started_at and latest last_cycle
            if s.get("started_at"):
                if not agg["started_at"] or s["started_at"] < agg["started_at"]:
                    agg["started_at"] = s["started_at"]
            if s.get("last_cycle"):
                if not agg["last_cycle"] or s["last_cycle"] > agg["last_cycle"]:
                    agg["last_cycle"] = s["last_cycle"]
            agg["agents"].append(s)
        return agg

    def start_agent(self, agent_id: int = 0) -> PipelineWorker:
        """Start a specific agent. Creates it if it doesn't exist."""
        if agent_id >= MAX_AGENTS:
            raise ValueError(f"Max {MAX_AGENTS} agents allowed")
        if agent_id not in self._agents:
            self._agents[agent_id] = PipelineWorker(agent_id=agent_id)
        agent = self._agents[agent_id]
        agent.start()
        return agent

    def stop_agent(self, agent_id: int) -> bool:
        """Stop a specific agent."""
        if agent_id in self._agents:
            self._agents[agent_id].stop()
            return True
        return False

    def stop_all(self):
        """Stop all agents."""
        for agent in self._agents.values():
            agent.stop()

    def start_multiple(self, count: int) -> list[int]:
        """Start N agents (0 through count-1). Returns list of agent_ids started."""
        count = min(count, MAX_AGENTS)
        started = []
        for i in range(count):
            self.start_agent(i)
            started.append(i)
        return started

    def get_agent(self, agent_id: int) -> Optional[PipelineWorker]:
        return self._agents.get(agent_id)


# ─── Singleton Manager ──────────────────────────────────────────────────
_manager: Optional[PipelineAgentManager] = None


def get_pipeline_manager() -> PipelineAgentManager:
    """Get or create the singleton pipeline agent manager."""
    global _manager
    if _manager is None:
        _manager = PipelineAgentManager()
    return _manager


def get_pipeline_worker() -> PipelineAgentManager:
    """Backward-compatible: returns the manager (used by existing API routes)."""
    return get_pipeline_manager()


async def start_pipeline_worker():
    """Start 5 agents by default (called from main.py lifespan)."""
    mgr = get_pipeline_manager()
    mgr.start_multiple(5)
    return mgr


async def stop_pipeline_worker():
    """Stop all agents (called from main.py shutdown)."""
    mgr = get_pipeline_manager()
    mgr.stop_all()


# ─── Recovery Functions (can be called independently) ──────────────────

async def recover_all_bad_states() -> dict:
    """
    One-shot recovery: scan all prospects and emails for bad states and fix them.
    Called on startup and available via API for manual trigger.
    
    Returns summary of what was recovered.
    """
    recovered = {
        "stuck_discovered": 0,
        "orphaned_queued": 0,
        "failed_emails_reset": 0,
        "stale_enriched": 0,
        "total": 0,
    }

    async with async_session_factory() as db:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=STUCK_THRESHOLD_MIN)

        # 1. Prospects marked "queued" but no pending/approved email → reset to enriched
        result = await db.execute(
            select(Prospect).where(Prospect.status == "queued")
        )
        queued_prospects = result.scalars().all()
        for p in queued_prospects:
            email_result = await db.execute(
                select(OutreachEmail).where(
                    OutreachEmail.prospect_id == p.id,
                    OutreachEmail.status.in_(["pending_approval", "approved", "scheduled"]),
                ).limit(1)
            )
            if not email_result.scalars().first():
                # Orphaned — queued but no email waiting
                if p.owner_email:
                    p.status = "enriched"  # Can be re-enqueued
                else:
                    p.status = "audited"   # Needs recon again
                p.updated_at = now
                recovered["orphaned_queued"] += 1

        # 2. Failed emails → reset to pending_approval for review
        result = await db.execute(
            select(OutreachEmail).where(
                OutreachEmail.status == "failed",
            )
        )
        for email in result.scalars().all():
            email.status = "pending_approval"
            email.error_message = f"[STARTUP-RECOVERED] {email.error_message or 'unknown error'}"
            recovered["failed_emails_reset"] += 1

        # 3. Prospects stuck as "enriched" with email for > 24 hours and no outreach email
        #    (the enqueue step was missed)
        day_ago = now - timedelta(hours=24)
        result = await db.execute(
            select(Prospect).where(
                Prospect.status == "enriched",
                Prospect.owner_email.isnot(None),
                Prospect.updated_at < day_ago,
            )
        )
        stale_enriched_ids = []
        for p in result.scalars().all():
            email_result = await db.execute(
                select(OutreachEmail).where(OutreachEmail.prospect_id == p.id).limit(1)
            )
            if not email_result.scalars().first():
                # Reset to imported so activate can pick them up again
                if p.source == "contractor_registry":
                    p.status = "imported"
                else:
                    p.status = "discovered"
                p.updated_at = now
                recovered["stale_enriched"] += 1
                stale_enriched_ids.append(str(p.id))

        if stale_enriched_ids:
            logger.warning("Reset %d stale enriched prospects: %s",
                           len(stale_enriched_ids), stale_enriched_ids[:5])

        recovered["total"] = sum(v for k, v in recovered.items() if k != "total")

        if recovered["total"] > 0:
            await db.commit()
            logger.info("Recovery complete: %s", recovered)

    return recovered
