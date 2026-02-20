"""
Outreach Agent — Firebase Summarizer.

Pushes pre-computed aggregates from PostgreSQL to Firebase RTDB.
All the Budget Maximizer nodes: snapshots, hot, funnel, heatmap,
tpl_stats, industries, scorecard, alerts, health.

Every write is idempotent (set/overwrite) — safe to call multiple times.
Designed for §13.7.4 of OUTREACH_AGENT_PLAN.md.
"""

import logging
import random
import time
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select, and_, extract
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.prospect import (
    GeoRing,
    OutreachEmail,
    OutreachSequence,
    Prospect,
    WebsiteAudit,
)

logger = logging.getLogger(__name__)

# Firebase Admin SDK (conditional import — same pattern as firebase.py)
try:
    from firebase_admin import db as firebase_db

    _HAS_FIREBASE = True
except ImportError:
    _HAS_FIREBASE = False
    firebase_db = None


# ────────────────────────────────────────────────────────
# Utility — safe Firebase ref wrapper
# ────────────────────────────────────────────────────────

def _ref(path: str):
    """Get a Firebase RTDB reference, or None if unavailable."""
    if not _HAS_FIREBASE or firebase_db is None:
        return None
    try:
        from api.services.firebase import is_initialized
        if not is_initialized():
            return None
        return firebase_db.reference(path)
    except Exception:
        return None


async def _safe_set(path: str, data):
    """Set data at path. Silently skip if Firebase is unavailable."""
    ref = _ref(path)
    if ref:
        try:
            ref.set(data)
        except Exception as e:
            logger.error(f"Firebase set {path} failed: {e}")


async def _safe_push(path: str, data):
    """Push data to path. Silently skip if Firebase is unavailable."""
    ref = _ref(path)
    if ref:
        try:
            ref.push(data)
        except Exception as e:
            logger.error(f"Firebase push {path} failed: {e}")


# ────────────────────────────────────────────────────────
# PRUNE helpers
# ────────────────────────────────────────────────────────

async def prune_firebase_node(path: str, max_children: int = 50):
    """Prune a Firebase node to at most max_children entries (FIFO by push ID)."""
    ref = _ref(path)
    if not ref:
        return
    try:
        snapshot = ref.get()
        if not snapshot or not isinstance(snapshot, dict):
            return
        if len(snapshot) <= max_children:
            return
        # Push IDs sort chronologically — sort and delete oldest
        keys = sorted(snapshot.keys())
        to_delete = keys[: len(keys) - max_children]
        ref.update({k: None for k in to_delete})
        logger.info(f"🧹 Pruned {len(to_delete)} entries from {path}")
    except Exception as e:
        logger.error(f"Prune {path} failed: {e}")


async def prune_by_age(path: str, max_age_days: int = 0, max_age_hours: int = 0):
    """Delete entries older than max_age from a keyed Firebase node."""
    ref = _ref(path)
    if not ref:
        return
    try:
        snapshot = ref.get()
        if not snapshot or not isinstance(snapshot, dict):
            return
        cutoff = int(time.time()) - (max_age_days * 86400) - (max_age_hours * 3600)
        to_delete = {}
        for key, val in snapshot.items():
            ts = val.get("ts", 0) if isinstance(val, dict) else 0
            if 0 < ts < cutoff:
                to_delete[key] = None
        if to_delete:
            ref.update(to_delete)
            logger.info(f"🧹 Pruned {len(to_delete)} expired entries from {path}")
    except Exception as e:
        logger.error(f"Prune by age {path} failed: {e}")


# ────────────────────────────────────────────────────────
# Data computation helpers (PostgreSQL aggregates)
# ────────────────────────────────────────────────────────

async def _compute_aggregate_stats(db: AsyncSession) -> dict:
    """
    Compute all-time + today aggregate stats for outreach/stats.
    Powers sidebar KPIs and Mission Control stat cards.
    Plan §13.1 — outreach/stats/ (~500 bytes).
    """
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    # All-time totals
    total_prospects = (await db.execute(
        select(func.count()).select_from(Prospect)
    )).scalar() or 0

    total_contacted = (await db.execute(
        select(func.count()).select_from(Prospect).where(
            Prospect.status.in_([
                "contacted", "follow_up_1", "follow_up_2", "follow_up_3",
                "replied", "meeting_booked", "promoted",
            ])
        )
    )).scalar() or 0

    total_opened = (await db.execute(
        select(func.count()).select_from(OutreachEmail).where(
            OutreachEmail.opened_at.isnot(None)
        )
    )).scalar() or 0

    total_replied = (await db.execute(
        select(func.count()).select_from(OutreachEmail).where(
            OutreachEmail.replied_at.isnot(None)
        )
    )).scalar() or 0

    total_meetings = (await db.execute(
        select(func.count()).select_from(Prospect).where(
            Prospect.status.in_(["meeting_booked", "promoted"])
        )
    )).scalar() or 0

    total_bounced = (await db.execute(
        select(func.count()).select_from(OutreachEmail).where(
            OutreachEmail.status == "bounced"
        )
    )).scalar() or 0

    # Today counts
    today_sent = (await db.execute(
        select(func.count()).select_from(OutreachEmail).where(
            and_(
                OutreachEmail.sent_at >= today_start,
                OutreachEmail.status.in_(["sent", "delivered", "opened", "clicked", "replied"]),
            )
        )
    )).scalar() or 0

    today_opened = (await db.execute(
        select(func.count()).select_from(OutreachEmail).where(
            and_(
                OutreachEmail.opened_at >= today_start,
                OutreachEmail.opened_at.isnot(None),
            )
        )
    )).scalar() or 0

    today_replied = (await db.execute(
        select(func.count()).select_from(OutreachEmail).where(
            and_(
                OutreachEmail.replied_at >= today_start,
                OutreachEmail.replied_at.isnot(None),
            )
        )
    )).scalar() or 0

    # Pre-calculated rates
    total_emails = (await db.execute(
        select(func.count()).select_from(OutreachEmail).where(
            OutreachEmail.status.in_(["sent", "delivered", "opened", "clicked", "replied", "bounced"])
        )
    )).scalar() or 0

    open_rate = round(total_opened / max(total_emails, 1) * 100, 1)
    reply_rate = round(total_replied / max(total_emails, 1) * 100, 1)

    return {
        "total_prospects": total_prospects,
        "total_contacted": total_contacted,
        "total_opened": total_opened,
        "total_replied": total_replied,
        "total_meetings": total_meetings,
        "total_bounced": total_bounced,
        "today_sent": today_sent,
        "today_opened": today_opened,
        "today_replied": today_replied,
        "open_rate": open_rate,
        "reply_rate": reply_rate,
        "updated_at": int(time.time()),
    }


async def compute_daily_stats(db: AsyncSession) -> dict:
    """Compute today's outreach stats."""
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    result = {}

    # Discovered today
    q = select(func.count()).select_from(Prospect).where(
        Prospect.created_at >= today_start
    )
    result["discovered"] = (await db.execute(q)).scalar() or 0

    # Emails sent today
    q = select(func.count()).select_from(OutreachEmail).where(
        and_(
            OutreachEmail.sent_at >= today_start,
            OutreachEmail.status.in_(["sent", "delivered", "opened", "clicked", "replied"]),
        )
    )
    result["sent"] = (await db.execute(q)).scalar() or 0

    # Opened today
    q = select(func.count()).select_from(OutreachEmail).where(
        and_(
            OutreachEmail.opened_at >= today_start,
            OutreachEmail.opened_at.isnot(None),
        )
    )
    result["opened"] = (await db.execute(q)).scalar() or 0

    # Replied today
    q = select(func.count()).select_from(OutreachEmail).where(
        and_(
            OutreachEmail.replied_at >= today_start,
            OutreachEmail.replied_at.isnot(None),
        )
    )
    result["replied"] = (await db.execute(q)).scalar() or 0

    # Bounced today
    q = select(func.count()).select_from(OutreachEmail).where(
        and_(
            OutreachEmail.sent_at >= today_start,
            OutreachEmail.status == "bounced",
        )
    )
    result["bounced"] = (await db.execute(q)).scalar() or 0

    # Meetings booked today
    q = select(func.count()).select_from(Prospect).where(
        and_(
            Prospect.status.in_(["meeting_booked", "promoted"]),
            Prospect.updated_at >= today_start,
        )
    )
    result["meetings"] = (await db.execute(q)).scalar() or 0

    # Computed rates
    total_sent = result["sent"] or 0
    result["open_rate"] = round(result["opened"] / max(total_sent, 1) * 100, 1)
    result["reply_rate"] = round(result["replied"] / max(total_sent, 1) * 100, 1)

    # Pipeline value placeholder (sum of estimated deal sizes)
    result["pipeline_value"] = 0  # Will be populated when deal tracking is wired

    result["ts"] = int(time.time())
    return result


async def compute_funnel_counts(db: AsyncSession) -> dict:
    """Compute prospect counts by pipeline stage."""
    stages = [
        "discovered", "audited", "enriched", "queued", "contacted",
        "follow_up_1", "follow_up_2", "follow_up_3", "replied",
        "meeting_booked", "promoted", "dead",
    ]
    funnel = {}
    for stage in stages:
        q = select(func.count()).select_from(Prospect).where(
            Prospect.status == stage
        )
        funnel[stage] = (await db.execute(q)).scalar() or 0

    # Qualified = priority score above threshold
    q = select(func.count()).select_from(Prospect).where(
        Prospect.priority_score >= 40
    )
    funnel["qualified"] = (await db.execute(q)).scalar() or 0

    funnel["updated_at"] = int(time.time())
    return funnel


async def get_hot_prospects(db: AsyncSession, limit: int = 10) -> list[dict]:
    """Get top prospects by priority score who haven't been promoted or killed."""
    # Subquery: count replies per prospect
    reply_sub = (
        select(
            OutreachEmail.prospect_id,
            func.count().label("reply_count"),
        )
        .where(OutreachEmail.replied_at.isnot(None))
        .group_by(OutreachEmail.prospect_id)
        .subquery()
    )

    q = (
        select(Prospect, reply_sub.c.reply_count)
        .outerjoin(reply_sub, Prospect.id == reply_sub.c.prospect_id)
        .where(Prospect.status.notin_(["promoted", "dead", "do_not_contact"]))
        .order_by(Prospect.priority_score.desc().nullslast())
        .limit(limit)
    )
    rows = (await db.execute(q)).all()
    results = []
    for row in rows:
        p = row[0]
        replies = row[1] or 0
        results.append({
            "name": p.business_name,
            "score": float(p.priority_score or 0),
            "status": p.status,
            "industry": p.business_type,
            "opens": p.emails_opened or 0,
            "replies": replies,
        })
    return results


async def compute_email_heatmap(db: AsyncSession) -> dict:
    """Compute email performance by day-of-week × hour-of-day."""
    days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    heatmap = {}

    # Get all sent emails with timestamps
    q = select(
        OutreachEmail.sent_at,
        OutreachEmail.opened_at,
        OutreachEmail.replied_at,
    ).where(OutreachEmail.sent_at.isnot(None))
    rows = (await db.execute(q)).all()

    for sent_at, opened_at, replied_at in rows:
        if not sent_at:
            continue
        day = days[sent_at.weekday()]
        hour = str(sent_at.hour)
        if day not in heatmap:
            heatmap[day] = {}
        if hour not in heatmap[day]:
            heatmap[day][hour] = {"sent": 0, "opened": 0, "replied": 0}
        heatmap[day][hour]["sent"] += 1
        if opened_at:
            heatmap[day][hour]["opened"] += 1
        if replied_at:
            heatmap[day][hour]["replied"] += 1

    return heatmap


async def compute_template_stats(db: AsyncSession) -> dict:
    """Compute performance stats per email template."""
    q = select(
        OutreachEmail.template_id,
        func.count().label("sent"),
        func.count(OutreachEmail.opened_at).label("opened"),
        func.count(OutreachEmail.replied_at).label("replied"),
    ).where(
        OutreachEmail.template_id.isnot(None)
    ).group_by(OutreachEmail.template_id)

    rows = (await db.execute(q)).all()
    stats = {}
    for row in rows:
        sent = row.sent or 0
        opened = row.opened or 0
        replied = row.replied or 0
        stats[row.template_id] = {
            "sent": sent,
            "opened": opened,
            "replied": replied,
            "open_rate": round(opened / sent * 100, 1) if sent > 0 else 0,
            "reply_rate": round(replied / sent * 100, 1) if sent > 0 else 0,
        }
    return stats


async def compute_industry_stats(db: AsyncSession, limit: int = 10) -> list[dict]:
    """Compute top industries by reply rate."""
    # Subquery: replies per prospect (derived from OutreachEmail.replied_at)
    reply_sub = (
        select(
            OutreachEmail.prospect_id,
            func.count().label("reply_count"),
        )
        .where(OutreachEmail.replied_at.isnot(None))
        .group_by(OutreachEmail.prospect_id)
        .subquery()
    )

    q = select(
        Prospect.business_type,
        func.count().label("count"),
        func.sum(Prospect.emails_sent).label("contacted"),
        func.coalesce(func.sum(reply_sub.c.reply_count), 0).label("replied"),
    ).outerjoin(
        reply_sub, Prospect.id == reply_sub.c.prospect_id
    ).where(
        Prospect.business_type.isnot(None)
    ).group_by(
        Prospect.business_type
    ).having(
        func.sum(Prospect.emails_sent) > 0
    ).order_by(
        (func.coalesce(func.sum(reply_sub.c.reply_count), 0) * 100.0 / func.sum(Prospect.emails_sent)).desc()
    ).limit(limit)

    rows = (await db.execute(q)).all()
    results = []
    for row in rows:
        contacted = row.contacted or 0
        replied = row.replied or 0
        results.append({
            "name": row.business_type,
            "count": row.count,
            "contacted": contacted,
            "replied": replied,
            "reply_rate": round(replied / contacted * 100, 1) if contacted > 0 else 0,
        })
    return results


async def compute_weekly_scorecard(db: AsyncSession) -> dict:
    """Compute this week's scorecard (Mon–Sun) with delta vs previous week."""
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    prev_week_start = week_start - timedelta(weeks=1)

    async def _week_stats(start: date) -> dict:
        end = start + timedelta(days=7)
        start_dt = datetime.combine(start, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_dt = datetime.combine(end, datetime.min.time()).replace(tzinfo=timezone.utc)

        q_sent = select(func.count()).select_from(OutreachEmail).where(
            and_(OutreachEmail.sent_at >= start_dt, OutreachEmail.sent_at < end_dt)
        )
        q_opened = select(func.count()).select_from(OutreachEmail).where(
            and_(OutreachEmail.opened_at >= start_dt, OutreachEmail.opened_at < end_dt)
        )
        q_replied = select(func.count()).select_from(OutreachEmail).where(
            and_(OutreachEmail.replied_at >= start_dt, OutreachEmail.replied_at < end_dt)
        )
        q_discovered = select(func.count()).select_from(Prospect).where(
            and_(Prospect.created_at >= start_dt, Prospect.created_at < end_dt)
        )
        sent = (await db.execute(q_sent)).scalar() or 0
        opened = (await db.execute(q_opened)).scalar() or 0
        replied = (await db.execute(q_replied)).scalar() or 0
        discovered = (await db.execute(q_discovered)).scalar() or 0
        return {"sent": sent, "opened": opened, "replied": replied, "discovered": discovered}

    this_week = await _week_stats(week_start)
    prev_week = await _week_stats(prev_week_start)

    def _delta(cur, prev_val):
        if prev_val == 0:
            return "+∞" if cur > 0 else "0%"
        pct = round((cur - prev_val) / prev_val * 100)
        return f"+{pct}%" if pct > 0 else f"{pct}%"

    return {
        **this_week,
        "meetings": 0,  # Placeholder — will be populated when meetings are tracked
        "delta_sent": _delta(this_week["sent"], prev_week["sent"]),
        "delta_replied": _delta(this_week["replied"], prev_week["replied"]),
        "week_start": int(datetime.combine(week_start, datetime.min.time()).replace(
            tzinfo=timezone.utc
        ).timestamp()),
    }


# ────────────────────────────────────────────────────────
# MAIN PUSH FUNCTIONS (called by scheduler)
# ────────────────────────────────────────────────────────

async def push_firebase_summaries(db: AsyncSession):
    """
    Compute aggregates from PostgreSQL → push to Firebase. Idempotent.
    Called nightly by APScheduler + on-demand via Telegram /refresh.
    """
    if not _HAS_FIREBASE:
        logger.warning("Firebase unavailable — skipping summary push")
        return

    logger.info("📊 Pushing Firebase summaries...")

    try:
        # 0. Aggregate KPIs → outreach/stats (sidebar + Mission Control)
        agg = await _compute_aggregate_stats(db)
        await _safe_set("outreach/stats", agg)

        # 1. Daily snapshot
        today = date.today().isoformat()
        daily = await compute_daily_stats(db)
        await _safe_set(f"outreach/snapshots/{today}", daily)

        # 2. Hot prospects (top 10)
        hot = await get_hot_prospects(db, limit=10)
        await _safe_set("outreach/hot", {str(i): p for i, p in enumerate(hot)})

        # 3. Pipeline funnel counts
        funnel = await compute_funnel_counts(db)
        await _safe_set("outreach/funnel", funnel)

        # 4. Send-time heatmap
        heatmap = await compute_email_heatmap(db)
        await _safe_set("outreach/heatmap", heatmap)

        # 5. Template leaderboard
        tpl = await compute_template_stats(db)
        await _safe_set("outreach/tpl_stats", tpl)

        # 6. Industry breakdown (top 10)
        industries = await compute_industry_stats(db, limit=10)
        await _safe_set("outreach/industries", {str(i): ind for i, ind in enumerate(industries)})

        # 7. Weekly scorecard (if today is Sunday)
        if date.today().weekday() == 6:
            week_key = date.today().strftime("%G-W%V")
            scorecard = await compute_weekly_scorecard(db)
            await _safe_set(f"outreach/scorecard/{week_key}", scorecard)

        # 8. Ring progress
        from api.models.prospect import GeoRing
        ring_rows = (await db.execute(select(GeoRing).order_by(GeoRing.ring_number))).scalars().all()
        if ring_rows:
            await push_ring_progress([r.to_dict() for r in ring_rows])

        logger.info("✅ Firebase summaries pushed successfully")
    except Exception as e:
        logger.error(f"Firebase summary push failed: {e}")

# Alias expected by scheduler in main.py
push_all_outreach_stats = push_firebase_summaries


async def push_alert(
    alert_type: str,
    priority: str,
    title: str,
    detail: str,
    icon: str,
):
    """
    Push an actionable alert. Auto-prunes to 20 on every 5th push.
    Types: reply, meeting, error, ring_complete, milestone.
    Priority: high, medium, low.
    """
    await _safe_push("outreach/alerts", {
        "type": alert_type,
        "priority": priority,
        "icon": icon,
        "title": title,
        "detail": detail,
        "read": False,
        "ts": int(time.time()),
    })
    # Prune on ~1 in 5 push (randomized to reduce Firebase reads)
    if random.randint(1, 5) == 1:
        await prune_firebase_node("outreach/alerts", max_children=20)


async def push_health_snapshot():
    """Push agent resource usage to Firebase. Keyed by hour — self-overwriting."""
    if not _HAS_FIREBASE:
        return
    try:
        import psutil
    except ImportError:
        logger.debug("psutil not installed — skipping health push")
        return

    key = datetime.now().strftime("%H-%m%d")  # e.g., "14-0221"
    await _safe_set(f"outreach/health/{key}", {
        "cpu_pct": psutil.cpu_percent(),
        "mem_mb": psutil.Process().memory_info().rss // (1024 * 1024),
        "queue_depth": 0,  # Updated when queue system is wired
        "errors_1h": 0,    # Updated when error tracking is wired
        "emails_1h": 0,    # Updated when email sending is wired
        "ts": int(time.time()),
    })


async def push_agent_status(status: str, current_ring: str = "", uptime_s: int = 0, current_task: str = "", error_msg: str = None):
    """Push agent status to Firebase for Command Center Anywhere."""
    data = {
        "status": status,
        "current_ring": current_ring,
        "uptime": uptime_s,
        "last_heartbeat": int(time.time()),
    }
    if current_task:
        data["current_task"] = current_task
    if error_msg:
        data["error_msg"] = error_msg
    await _safe_set("outreach/agent", data)


async def push_ring_progress(rings: list[dict]):
    """Push geo-ring progress data to Firebase."""
    data = {}
    for r in rings:
        total_cats = max(len(r.get("categories_total", [])) or 1, 1)
        done_cats = len(r.get("categories_done", []))
        data[str(r.get("ring_number", 0))] = {
            "name": r.get("name", ""),
            "status": r.get("status", ""),
            "pct": round(done_cats / total_cats * 100, 1),
            "businesses_found": r.get("businesses_found", 0),
            "contacted_pct": round(r.get("contacted", 0) / max(r.get("businesses_found", 1), 1) * 100, 1),
            "replied_count": r.get("replied_count", 0),
        }
    await _safe_set("outreach/rings", data)


async def push_log(log_type: str, msg: str, extra: dict = None):
    """
    Push a structured log entry to outreach/log.
    Types: crawl, audit, recon, email, score, ring, sys.
    Auto-prunes to 200 entries on ~1/10 pushes.
    """
    entry = {
        "type": log_type,
        "msg": msg,
        "time": datetime.now().strftime("%H:%M:%S"),
        "ts": int(time.time()),
    }
    if extra:
        entry.update(extra)
    await _safe_push("outreach/log", entry)
    if random.randint(1, 10) == 1:
        await prune_firebase_node("outreach/log", max_children=200)


async def push_activity(activity_type: str, name: str, detail: str = "", city: str = "", lat: float = None, lng: float = None):
    """
    Push an activity item to outreach/activity with correct field names per plan §13.5.
    Types: crawl, audit, recon, email, ring, system.
    Auto-prunes to 50 entries on ~1/5 pushes.
    """
    entry = {
        "type": activity_type,
        "name": name,
        "detail": detail,
        "ts": int(time.time()),
    }
    if city:
        entry["city"] = city
    if lat is not None:
        entry["lat"] = lat
    if lng is not None:
        entry["lng"] = lng
    await _safe_push("outreach/activity", entry)
    if random.randint(1, 5) == 1:
        await prune_firebase_node("outreach/activity", max_children=50)


# ────────────────────────────────────────────────────────
# REBUILD — full regeneration from PostgreSQL
# ────────────────────────────────────────────────────────

async def rebuild_firebase_from_postgres(db: AsyncSession | None = None):
    """
    Nuclear option: regenerate ALL Firebase summary nodes from PostgreSQL.
    Called on first boot if Firebase is empty, or via Telegram /rebuild.
    Every write is idempotent set() — safe to run anytime.
    """
    if not _HAS_FIREBASE:
        logger.warning("Firebase unavailable — cannot rebuild")
        return

    logger.info("🔄 Rebuilding Firebase summaries from PostgreSQL...")

    if db is None:
        # Get a fresh session if not provided
        from api.database import async_session
        async with async_session() as db:
            await _do_rebuild(db)
    else:
        await _do_rebuild(db)


async def _do_rebuild(db: AsyncSession):
    """Internal rebuild logic."""
    try:
        # 1. Rebuild daily snapshots (last 90 days)
        for day_offset in range(90):
            day = date.today() - timedelta(days=day_offset)
            stats = await compute_daily_stats(db)
            if stats.get("sent", 0) > 0 or stats.get("discovered", 0) > 0:
                await _safe_set(f"outreach/snapshots/{day.isoformat()}", stats)

        # 2. Rebuild weekly scorecards (last 12 weeks)
        for week_offset in range(12):
            week_start = date.today() - timedelta(weeks=week_offset)
            week_key = week_start.strftime("%G-W%V")
            scorecard = await compute_weekly_scorecard(db)
            if scorecard.get("sent", 0) > 0:
                await _safe_set(f"outreach/scorecard/{week_key}", scorecard)

        # 3. Rebuild all overwrite nodes
        await push_firebase_summaries(db)

        logger.info("✅ Firebase rebuild complete — all nodes refreshed from PostgreSQL")
    except Exception as e:
        logger.error(f"Firebase rebuild failed: {e}")


# ────────────────────────────────────────────────────────
# BOOT CHECK
# ────────────────────────────────────────────────────────

async def check_and_rebuild_on_boot(db: AsyncSession):
    """
    Called once at FastAPI startup. If outreach/agent is missing,
    assume Firebase is empty and trigger a full rebuild.
    """
    if not _HAS_FIREBASE:
        return
    try:
        from api.services.firebase import is_initialized
        if not is_initialized():
            return
        ref = firebase_db.reference("outreach/agent")
        agent = ref.get()
        if not agent:
            logger.warning("Firebase outreach data missing — triggering rebuild...")
            await rebuild_firebase_from_postgres(db)
        else:
            logger.info("✅ Firebase outreach data present — skipping rebuild")
    except Exception as e:
        logger.error(f"Firebase boot check failed: {e}")
