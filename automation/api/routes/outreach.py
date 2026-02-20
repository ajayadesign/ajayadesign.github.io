"""
Outreach Agent — API Routes.

CRUD for prospects, geo-rings, emails, sequences.
Agent control endpoints (start, pause, status).
File serving for screenshots and audit data.
"""

import csv
import io
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select, case, text, or_
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.config import settings
from api.models.prospect import (
    GeoRing,
    OutreachEmail,
    OutreachSequence,
    Prospect,
    ProspectActivity,
    WebsiteAudit,
)
from api.services.firebase_summarizer import (
    push_agent_status,
    push_activity,
    push_log,
    _safe_push,
)

logger = logging.getLogger(__name__)

outreach_router = APIRouter(prefix="/outreach", tags=["outreach"])

# ── In-memory agent state (will be replaced with persistent state later) ──
_agent_state = {
    "status": "idle",       # idle, running, paused, error
    "current_task": None,   # e.g. "crawling Ring 0", "auditing joesplumbing.com"
    "started_at": None,
    "paused_at": None,
    "error": None,
}


# ═══════════════════════════════════════════════════════════════════
# AGENT CONTROL
# ═══════════════════════════════════════════════════════════════════

@outreach_router.get("/agent/status")
async def get_agent_status():
    """Get current agent status."""
    return {
        "status": _agent_state["status"],
        "current_task": _agent_state["current_task"],
        "started_at": _agent_state["started_at"],
        "paused_at": _agent_state["paused_at"],
        "error": _agent_state["error"],
    }


@outreach_router.post("/agent/start")
async def start_agent():
    """Start or resume the outreach agent (enables crawler)."""
    if _agent_state["status"] == "running":
        return {"message": "Agent already running", "status": "running"}
    _agent_state["status"] = "running"
    _agent_state["started_at"] = datetime.now(timezone.utc).isoformat()
    _agent_state["paused_at"] = None
    _agent_state["error"] = None
    # Enable the Maps API crawler in the pipeline worker
    from api.services.pipeline_worker import set_crawl_enabled
    set_crawl_enabled(True)
    logger.info("Outreach agent started (crawler enabled)")
    # Push to Firebase so all connected dashboards update in real-time
    await push_agent_status("running", _agent_state.get("current_task", "") or "")
    await push_activity("system", "Agent started", "Outreach agent resumed scanning")
    return {"message": "Agent started", "status": "running"}


@outreach_router.post("/agent/pause")
async def pause_agent():
    """Pause the outreach agent (disables crawler, worker keeps running)."""
    _agent_state["status"] = "paused"
    _agent_state["paused_at"] = datetime.now(timezone.utc).isoformat()
    # Disable the Maps API crawler — worker (audit/recon/enqueue) keeps running
    from api.services.pipeline_worker import set_crawl_enabled
    set_crawl_enabled(False)
    logger.info("Outreach agent paused (crawler disabled, worker still running)")
    await push_agent_status("paused")
    await push_activity("system", "Agent paused", "Crawler paused — audit/recon/enqueue still active")
    return {"message": "Agent paused (crawler disabled, worker still processing)", "status": "paused"}


@outreach_router.post("/agent/kill")
async def kill_agent():
    """Emergency stop the agent."""
    _agent_state["status"] = "idle"
    _agent_state["current_task"] = None
    _agent_state["started_at"] = None
    _agent_state["paused_at"] = None
    _agent_state["error"] = None
    # Disable the crawler
    from api.services.pipeline_worker import set_crawl_enabled
    set_crawl_enabled(False)
    logger.info("Outreach agent killed (crawler disabled)")
    await push_agent_status("idle")
    await push_activity("system", "Agent killed", "Emergency stop triggered")
    return {"message": "Agent killed", "status": "idle"}


@outreach_router.post("/sync-firebase")
async def sync_firebase(db: AsyncSession = Depends(get_db)):
    """Force rebuild of all outreach data in Firebase RTDB from PostgreSQL."""
    from api.services.firebase_summarizer import rebuild_firebase_from_postgres
    await rebuild_firebase_from_postgres(db)
    return {"message": "Firebase outreach data rebuilt from PostgreSQL", "status": "ok"}


# ═══════════════════════════════════════════════════════════════════
# PROSPECTS
# ═══════════════════════════════════════════════════════════════════

@outreach_router.get("/prospects/types")
async def list_business_types(db: AsyncSession = Depends(get_db)):
    """Return distinct business types for filter dropdowns."""
    result = await db.execute(
        select(Prospect.business_type, func.count(Prospect.id).label("cnt"))
        .where(Prospect.business_type.isnot(None))
        .group_by(Prospect.business_type)
        .order_by(func.count(Prospect.id).desc())
    )
    return [{"type": row.business_type, "count": row.cnt} for row in result.all()]

@outreach_router.get("/prospects")
async def list_prospects(
    status: Optional[str] = None,
    ring_id: Optional[str] = None,
    business_type: Optional[str] = None,
    has_website: Optional[str] = None,
    qualified: Optional[str] = None,
    search: Optional[str] = None,
    sort: str = "priority_score",
    order: str = "desc",
    limit: int = Query(50, le=500),
    offset: int = 0,
    brief: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """List prospects with filtering, sorting, and pagination."""
    query = select(Prospect)

    if status:
        query = query.where(Prospect.status == status)
    if ring_id:
        query = query.where(Prospect.geo_ring_id == uuid.UUID(ring_id))
    if business_type:
        query = query.where(Prospect.business_type == business_type)
    if has_website == "false":
        query = query.where(Prospect.has_website == False)  # noqa: E712
    elif has_website == "true":
        query = query.where(Prospect.has_website == True)  # noqa: E712
    # Qualified vs Scanned filter
    _QUALIFIED_STATUSES = ["audited", "enriched", "queued", "contacted", "replied", "meeting_booked", "promoted"]
    if qualified == "true":
        query = query.where(Prospect.status.in_(_QUALIFIED_STATUSES))
    elif qualified == "false":
        query = query.where(Prospect.status == "discovered")
    if search:
        query = query.where(Prospect.business_name.ilike(f"%{search}%"))

    # Sorting
    sort_col = getattr(Prospect, sort, Prospect.priority_score)
    if order == "desc":
        query = query.order_by(sort_col.desc())
    else:
        query = query.order_by(sort_col.asc())

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    # Paginate
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    prospects = result.scalars().all()

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "prospects": [p.to_dict(brief=brief) for p in prospects],
    }


@outreach_router.get("/prospects/export")
async def export_prospects_csv(
    status: Optional[str] = None,
    ring_id: Optional[str] = None,
    business_type: Optional[str] = None,
    has_website: Optional[str] = None,
    qualified: Optional[str] = None,
    search: Optional[str] = None,
    sort: str = "priority_score",
    order: str = "desc",
    db: AsyncSession = Depends(get_db),
):
    """Export filtered prospects as CSV file with all fields."""
    query = select(Prospect)

    if status:
        query = query.where(Prospect.status == status)
    if ring_id:
        query = query.where(Prospect.geo_ring_id == uuid.UUID(ring_id))
    if business_type:
        query = query.where(Prospect.business_type == business_type)
    if has_website == "false":
        query = query.where(Prospect.has_website == False)  # noqa: E712
    elif has_website == "true":
        query = query.where(Prospect.has_website == True)  # noqa: E712
    _QUALIFIED_STATUSES = ["audited", "enriched", "queued", "contacted", "replied", "meeting_booked", "promoted"]
    if qualified == "true":
        query = query.where(Prospect.status.in_(_QUALIFIED_STATUSES))
    elif qualified == "false":
        query = query.where(Prospect.status == "discovered")
    if search:
        query = query.where(Prospect.business_name.ilike(f"%{search}%"))

    sort_col = getattr(Prospect, sort, Prospect.priority_score)
    if order == "desc":
        query = query.order_by(sort_col.desc())
    else:
        query = query.order_by(sort_col.asc())

    result = await db.execute(query)
    prospects = result.scalars().all()

    CSV_COLUMNS = [
        ("Business Name", "business_name"),
        ("Business Type", "business_type"),
        ("Status", "status"),
        ("Phone", "phone"),
        ("Address", "address"),
        ("City", "city"),
        ("State", "state"),
        ("Zip", "zip_code"),
        ("Owner Name", "owner_name"),
        ("Owner Email", "owner_email"),
        ("Owner Phone", "owner_phone"),
        ("Owner Title", "owner_title"),
        ("Email Source", "email_source"),
        ("Email Verified", "email_verified"),
        ("Has Website", "has_website"),
        ("Website URL", "website_url"),
        ("Website Platform", "website_platform"),
        ("Google Rating", "google_rating"),
        ("Google Reviews", "google_reviews"),
        ("Google Maps URL", "google_maps_url"),
        ("Priority Score", "priority_score"),
        ("Notes", "notes"),
        ("Created", "created_at"),
    ]

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([col[0] for col in CSV_COLUMNS])

    for p in prospects:
        d = p.to_dict(brief=False)
        row = []
        for _, key in CSV_COLUMNS:
            val = d.get(key, "")
            if val is None:
                val = ""
            row.append(str(val))
        writer.writerow(row)

    buf.seek(0)
    filename = f"prospects_{status or 'all'}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@outreach_router.get("/prospects/{prospect_id}")
async def get_prospect(prospect_id: str, db: AsyncSession = Depends(get_db)):
    """Get full prospect detail including audits, email history, and score breakdown."""
    result = await db.execute(
        select(Prospect).where(Prospect.id == uuid.UUID(prospect_id))
    )
    prospect = result.scalar_one_or_none()
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")

    data = prospect.to_dict(brief=False)
    # Include prospect-level composite scores in each audit record
    audits_list = []
    for a in prospect.audits:
        ad = a.to_dict()
        # Add prospect-level scores so the UI can display them
        ad["composite_score"] = prospect.score_overall
        ad["design_score"] = prospect.score_design
        ad["security_score"] = prospect.score_security
        ad["mobile_score"] = prospect.score_mobile
        audits_list.append(ad)
    data["audits"] = audits_list
    data["emails"] = [e.to_dict() for e in prospect.emails]
    data["activities"] = [a.to_dict() for a in prospect.activities]

    # Compute score breakdown so the UI can show exactly how the score was calculated
    from api.services.crawl_engine import INDUSTRY_VALUES
    overall = prospect.score_overall if prospect.score_overall is not None else 0
    site_badness = round(40 - (overall * 0.4), 1)
    rating = float(prospect.google_rating) if prospect.google_rating else 0
    reviews = prospect.google_reviews or 0
    review_score = round(min(25, rating * 4 + min(10, reviews / 10)), 1)
    dist = float(prospect.distance_miles) if prospect.distance_miles else 100
    proximity_score = round(max(0, 15 - (dist / 5)), 1)
    industry_mult = INDUSTRY_VALUES.get(prospect.business_type or "", 5)
    reach = 0
    if prospect.owner_email:
        reach += 5
    if prospect.email_verified:
        reach += 3
    if prospect.owner_name:
        reach += 2

    data["score_breakdown"] = {
        "site_badness": {"value": site_badness, "max": 40, "label": "Website Badness", "detail": f"Worse site = higher priority (audit score: {overall})"},
        "business_health": {"value": review_score, "max": 25, "label": "Business Health", "detail": f"Rating: {rating}★ · {reviews} reviews"},
        "proximity": {"value": proximity_score, "max": 15, "label": "Proximity", "detail": f"{round(dist, 1)} miles away"},
        "industry_value": {"value": industry_mult, "max": 10, "label": "Industry Value", "detail": f"{(prospect.business_type or 'unknown').replace('_', ' ').title()}"},
        "reachability": {"value": reach, "max": 10, "label": "Reachability", "detail": f"{'Email ✓' if prospect.owner_email else 'No email'} · {'Verified ✓' if prospect.email_verified else ''} · {'Named ✓' if prospect.owner_name else ''}".strip(' ·')},
        "total": {"value": int(site_badness + review_score + proximity_score + industry_mult + reach), "max": 100},
    }

    return data


@outreach_router.post("/prospects")
async def create_prospect(body: dict, db: AsyncSession = Depends(get_db)):
    """Create a new prospect manually."""
    prospect = Prospect(
        business_name=body["business_name"],
        city=body.get("city", "Manor"),
        state=body.get("state", "TX"),
        business_type=body.get("business_type"),
        website_url=body.get("website_url"),
        has_website=bool(body.get("website_url")),
        phone=body.get("phone"),
        owner_name=body.get("owner_name"),
        owner_email=body.get("owner_email"),
        source=body.get("source", "manual"),
        notes=body.get("notes"),
        status="discovered",
    )
    db.add(prospect)
    await db.commit()
    await db.refresh(prospect)
    logger.info(f"Prospect created: {prospect.business_name}")
    return prospect.to_dict()


@outreach_router.patch("/prospects/{prospect_id}")
async def update_prospect(prospect_id: str, body: dict, db: AsyncSession = Depends(get_db)):
    """Update a prospect's fields."""
    result = await db.execute(
        select(Prospect).where(Prospect.id == uuid.UUID(prospect_id))
    )
    prospect = result.scalar_one_or_none()
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")

    allowed_fields = {
        "status", "notes", "tags", "owner_name", "owner_email", "owner_phone",
        "owner_title", "email_verified", "priority_score", "business_type",
        "industry_tag",
    }
    for key, value in body.items():
        if key in allowed_fields:
            setattr(prospect, key, value)

    prospect.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(prospect)
    return prospect.to_dict()


@outreach_router.delete("/prospects/{prospect_id}")
async def delete_prospect(prospect_id: str, db: AsyncSession = Depends(get_db)):
    """Soft-delete a prospect (mark as do_not_contact). PostgreSQL data is never destroyed."""
    result = await db.execute(
        select(Prospect).where(Prospect.id == uuid.UUID(prospect_id))
    )
    prospect = result.scalar_one_or_none()
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")

    prospect.status = "do_not_contact"
    prospect.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(prospect)
    return {"message": f"Prospect {prospect_id} marked as do_not_contact", "prospect": prospect.to_dict()}


@outreach_router.post("/prospects/{prospect_id}/promote")
async def promote_to_lead(prospect_id: str, db: AsyncSession = Depends(get_db)):
    """Promote a prospect to a CRM lead."""
    result = await db.execute(
        select(Prospect).where(Prospect.id == uuid.UUID(prospect_id))
    )
    prospect = result.scalar_one_or_none()
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")

    prospect.status = "promoted"
    prospect.updated_at = datetime.now(timezone.utc)
    await db.commit()
    logger.info(f"Prospect promoted to lead: {prospect.business_name}")
    return {"message": f"Promoted {prospect.business_name} to lead", "prospect": prospect.to_dict()}


# ═══════════════════════════════════════════════════════════════════
# MAP DOTS (lightweight for Leaflet)
# ═══════════════════════════════════════════════════════════════════

@outreach_router.get("/map-dots")
async def get_map_dots(
    ring_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get minimal prospect data for map plotting (~50 bytes/dot)."""
    query = select(Prospect).where(
        Prospect.lat.isnot(None),
        Prospect.lng.isnot(None),
    )
    if ring_id:
        query = query.where(Prospect.geo_ring_id == uuid.UUID(ring_id))

    result = await db.execute(query)
    prospects = result.scalars().all()
    return {"dots": [p.to_map_dot() for p in prospects]}


# ═══════════════════════════════════════════════════════════════════
# GEO RINGS
# ═══════════════════════════════════════════════════════════════════

@outreach_router.get("/rings")
async def list_rings(db: AsyncSession = Depends(get_db)):
    """List all geo-rings with progress stats."""
    result = await db.execute(
        select(GeoRing).order_by(GeoRing.ring_number)
    )
    rings = result.scalars().all()
    return {"rings": [r.to_dict() for r in rings]}


@outreach_router.post("/rings")
async def create_ring(body: dict, db: AsyncSession = Depends(get_db)):
    """Create a new geo-ring."""
    ring = GeoRing(
        name=body["name"],
        ring_number=body.get("ring_number", 0),
        radius_miles=body["radius_miles"],
        center_lat=body.get("center_lat", 30.3427),
        center_lng=body.get("center_lng", -97.5567),
        categories_total=body.get("categories_total", []),
    )
    db.add(ring)
    await db.commit()
    await db.refresh(ring)
    return ring.to_dict()


@outreach_router.get("/rings/{ring_id}")
async def get_ring(ring_id: str, db: AsyncSession = Depends(get_db)):
    """Get ring details with prospect counts per status."""
    result = await db.execute(
        select(GeoRing).where(GeoRing.id == uuid.UUID(ring_id))
    )
    ring = result.scalar_one_or_none()
    if not ring:
        raise HTTPException(status_code=404, detail="Ring not found")

    # Count prospects per status in this ring
    status_counts = await db.execute(
        select(Prospect.status, func.count(Prospect.id))
        .where(Prospect.geo_ring_id == ring.id)
        .group_by(Prospect.status)
    )
    counts = {row[0]: row[1] for row in status_counts.all()}

    data = ring.to_dict()
    data["prospect_counts"] = counts
    data["total_prospects"] = sum(counts.values())
    return data


# ═══════════════════════════════════════════════════════════════════
# EMAILS
# ═══════════════════════════════════════════════════════════════════

@outreach_router.get("/emails")
async def list_emails(
    status: Optional[str] = None,
    prospect_id: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """List outreach emails with filtering."""
    query = select(OutreachEmail).order_by(OutreachEmail.created_at.desc())
    if status:
        query = query.where(OutreachEmail.status == status)
    if prospect_id:
        query = query.where(OutreachEmail.prospect_id == uuid.UUID(prospect_id))

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    emails = result.scalars().all()
    return {"emails": [e.to_dict() for e in emails]}


@outreach_router.get("/emails/pending")
async def list_pending_emails(
    db: AsyncSession = Depends(get_db),
    limit: int = 25,
    offset: int = 0,
    sort: str = "created_at",
    order: str = "desc",
    has_website: Optional[str] = None,
    prospect_status: Optional[str] = None,
    sequence_step: Optional[str] = None,
):
    """List emails awaiting operator approval, with prospect context. Supports pagination, sorting, and filtering."""
    # Base filter
    base_filter = OutreachEmail.status == "pending_approval"
    join_cond = Prospect.id == OutreachEmail.prospect_id

    # Website filter
    website_filter = None
    if has_website == "true":
        website_filter = Prospect.has_website == True  # noqa: E712
    elif has_website == "false":
        website_filter = Prospect.has_website == False  # noqa: E712

    # Prospect status filter
    status_filter = None
    if prospect_status:
        status_filter = Prospect.status == prospect_status

    # Sequence step filter (supports single step or comma-separated range)
    step_filter = None
    if sequence_step:
        steps = [int(s.strip()) for s in sequence_step.split(",") if s.strip().isdigit()]
        if len(steps) == 1:
            step_filter = OutreachEmail.sequence_step == steps[0]
        elif steps:
            step_filter = OutreachEmail.sequence_step.in_(steps)

    # Count
    count_q = select(func.count(OutreachEmail.id)).join(Prospect, join_cond).where(base_filter)
    if website_filter is not None:
        count_q = count_q.where(website_filter)
    if status_filter is not None:
        count_q = count_q.where(status_filter)
    if step_filter is not None:
        count_q = count_q.where(step_filter)
    total = (await db.execute(count_q)).scalar() or 0

    # Sorting
    sort_map = {
        "created_at": OutreachEmail.created_at,
        "score": Prospect.priority_score,
        "business_name": Prospect.business_name,
    }
    sort_col = sort_map.get(sort, OutreachEmail.created_at)
    order_col = sort_col.desc() if order == "desc" else sort_col.asc()

    # Query
    q = (select(OutreachEmail, Prospect)
         .join(Prospect, join_cond)
         .where(base_filter))
    if website_filter is not None:
        q = q.where(website_filter)
    if status_filter is not None:
        q = q.where(status_filter)
    if step_filter is not None:
        q = q.where(step_filter)
    q = q.order_by(order_col).limit(limit).offset(offset)

    result = await db.execute(q)
    rows = result.all()
    out = []
    for email, prospect in rows:
        d = email.to_dict()
        d["prospect_name"] = prospect.business_name
        d["prospect_type"] = prospect.business_type
        d["prospect_city"] = prospect.city
        d["prospect_website"] = prospect.website_url
        d["prospect_score"] = prospect.priority_score
        out.append(d)

    # Per-step counts for tab badges
    step_counts_q = (
        select(OutreachEmail.sequence_step, func.count(OutreachEmail.id))
        .where(OutreachEmail.status == "pending_approval")
        .group_by(OutreachEmail.sequence_step)
    )
    step_counts = {row[0]: row[1] for row in (await db.execute(step_counts_q)).all()}

    return {
        "emails": out,
        "total": total,
        "limit": limit,
        "offset": offset,
        "step_counts": step_counts,
    }


@outreach_router.post("/emails/batch-approve")
async def batch_approve_emails(body: dict, db: AsyncSession = Depends(get_db)):
    """Approve multiple emails at once. Body: {email_ids: [...]} or {all: true}."""
    if body.get("all"):
        result = await db.execute(
            select(OutreachEmail).where(OutreachEmail.status == "pending_approval")
        )
    else:
        ids = body.get("email_ids", [])
        if not ids:
            raise HTTPException(status_code=400, detail="No email IDs provided")
        result = await db.execute(
            select(OutreachEmail).where(
                OutreachEmail.id.in_([uuid.UUID(i) for i in ids]),
                OutreachEmail.status == "pending_approval",
            )
        )
    emails = result.scalars().all()
    now = datetime.now(timezone.utc)
    for e in emails:
        e.status = "approved"
        e.scheduled_for = now  # Send at next queue cycle
        e.updated_at = now
    await db.commit()
    return {"message": f"Approved {len(emails)} emails", "count": len(emails)}


# ═══════════════════════════════════════════════════════════════════
# SEQUENCES
# ═══════════════════════════════════════════════════════════════════

@outreach_router.get("/sequences")
async def list_sequences(db: AsyncSession = Depends(get_db)):
    """List all outreach sequences."""
    result = await db.execute(
        select(OutreachSequence).order_by(OutreachSequence.created_at.desc())
    )
    sequences = result.scalars().all()
    return {"sequences": [s.to_dict() for s in sequences]}


@outreach_router.post("/sequences")
async def create_sequence(body: dict, db: AsyncSession = Depends(get_db)):
    """Create a new outreach sequence."""
    seq = OutreachSequence(
        name=body["name"],
        industry_tag=body.get("industry_tag"),
        steps=body["steps"],
    )
    db.add(seq)
    await db.commit()
    await db.refresh(seq)
    return seq.to_dict()


# ═══════════════════════════════════════════════════════════════════
# STATS (for dashboard KPIs)
# ═══════════════════════════════════════════════════════════════════

@outreach_router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Get aggregate outreach statistics for the dashboard."""
    # Total prospects
    total = (await db.execute(select(func.count(Prospect.id)))).scalar() or 0

    # Status breakdown
    status_query = await db.execute(
        select(Prospect.status, func.count(Prospect.id)).group_by(Prospect.status)
    )
    status_counts = {row[0]: row[1] for row in status_query.all()}

    # Totals from all prospects
    agg = await db.execute(
        select(
            func.sum(Prospect.emails_sent).label("total_sent"),
            func.sum(Prospect.emails_opened).label("total_opened"),
            func.sum(Prospect.emails_clicked).label("total_clicked"),
        )
    )
    row = agg.one()
    total_sent = row.total_sent or 0
    total_opened = row.total_opened or 0
    total_clicked = row.total_clicked or 0

    # Replied count
    replied = status_counts.get("replied", 0) + status_counts.get("meeting_booked", 0)
    meetings = status_counts.get("meeting_booked", 0)

    return {
        "total_prospects": total,
        "status_counts": status_counts,
        "total_sent": total_sent,
        "total_contacted": total_sent,  # alias for dashboard KPI
        "total_opened": total_opened,
        "total_clicked": total_clicked,
        "total_replied": replied,
        "total_meetings": meetings,
        "open_rate": round(total_opened / total_sent * 100, 1) if total_sent > 0 else 0,
        "reply_rate": round(replied / total_sent * 100, 1) if total_sent > 0 else 0,
        "click_rate": round(total_clicked / total_sent * 100, 1) if total_sent > 0 else 0,
    }


# ═══════════════════════════════════════════════════════════════════
# PIPELINE FUNNEL
# ═══════════════════════════════════════════════════════════════════

@outreach_router.get("/funnel")
async def get_funnel(db: AsyncSession = Depends(get_db)):
    """Get pipeline funnel counts by stage."""
    STAGE_ORDER = [
        "discovered", "audited", "enriched", "queued", "contacted",
        "follow_up_1", "follow_up_2", "follow_up_3",
        "replied", "meeting_booked", "promoted",
    ]

    result = await db.execute(
        select(Prospect.status, func.count(Prospect.id)).group_by(Prospect.status)
    )
    raw = {row[0]: row[1] for row in result.all()}

    funnel = []
    for stage in STAGE_ORDER:
        funnel.append({"stage": stage, "count": raw.get(stage, 0)})
    return {"funnel": funnel}


# ── Telegram Webhook ────────────────────────────────────

@outreach_router.post("/telegram-webhook")
async def telegram_webhook(update: dict):
    """Receive Telegram webhook updates."""
    try:
        from api.services.telegram_outreach import handle_telegram_update
        return await handle_telegram_update(update)
    except Exception as e:
        logger.error(f"Telegram webhook error: {e}")
        return {"ok": True}  # Always return 200 to Telegram


# ═══════════════════════════════════════════════════════════════════
# EMAIL PERFORMANCE TRACKING STATS
# ═══════════════════════════════════════════════════════════════════

@outreach_router.get("/email-stats")
async def get_email_stats(db: AsyncSession = Depends(get_db)):
    """
    Comprehensive email tracking stats for the dashboard.
    Returns: sent, delivered, opened, clicked, replied, bounced, failed, unsubscribed.
    Plus rates, per-step breakdown, and recent engagement timeline.
    """
    # Overall status counts
    status_q = await db.execute(
        select(OutreachEmail.status, func.count(OutreachEmail.id))
        .group_by(OutreachEmail.status)
    )
    status_counts = {row[0]: row[1] for row in status_q.all()}

    total_sent = status_counts.get("sent", 0) + status_counts.get("delivered", 0)
    total_opened = 0
    total_clicked = 0
    total_bounced = status_counts.get("bounced", 0)
    total_failed = status_counts.get("failed", 0)
    total_pending = status_counts.get("pending_approval", 0)
    total_scheduled = status_counts.get("scheduled", 0)

    # Aggregate open & click counts from email records
    agg = await db.execute(
        select(
            func.sum(OutreachEmail.open_count).label("opens"),
            func.sum(OutreachEmail.click_count).label("clicks"),
            func.count(case((OutreachEmail.opened_at.isnot(None), 1))).label("unique_opens"),
            func.count(case((OutreachEmail.clicked_at.isnot(None), 1))).label("unique_clicks"),
            func.count(case((OutreachEmail.replied_at.isnot(None), 1))).label("replies"),
        ).where(OutreachEmail.sent_at.isnot(None))
    )
    row = agg.one()
    total_opens = row.opens or 0
    total_clicks = row.clicks or 0
    unique_opens = row.unique_opens or 0
    unique_clicks = row.unique_clicks or 0
    total_replied = row.replies or 0

    # Unsubscribed = prospects marked do_not_contact with an email in the table
    unsub_q = await db.execute(
        select(func.count(Prospect.id)).where(Prospect.status == "do_not_contact")
    )
    total_unsubscribed = unsub_q.scalar() or 0

    # Per-step breakdown
    step_q = await db.execute(
        select(
            OutreachEmail.sequence_step,
            func.count(OutreachEmail.id).label("total"),
            func.count(case((OutreachEmail.sent_at.isnot(None), 1))).label("sent"),
            func.count(case((OutreachEmail.opened_at.isnot(None), 1))).label("opened"),
            func.count(case((OutreachEmail.clicked_at.isnot(None), 1))).label("clicked"),
            func.count(case((OutreachEmail.replied_at.isnot(None), 1))).label("replied"),
            func.count(case((OutreachEmail.status == "bounced", 1))).label("bounced"),
        )
        .group_by(OutreachEmail.sequence_step)
        .order_by(OutreachEmail.sequence_step)
    )
    per_step = []
    for r in step_q.all():
        step_sent = r.sent or 0
        per_step.append({
            "step": r.sequence_step,
            "total": r.total,
            "sent": step_sent,
            "opened": r.opened,
            "clicked": r.clicked,
            "replied": r.replied,
            "bounced": r.bounced,
            "open_rate": round(r.opened / step_sent * 100, 1) if step_sent > 0 else 0,
            "click_rate": round(r.clicked / step_sent * 100, 1) if step_sent > 0 else 0,
        })

    # Recent engagement (last 20 events)
    recent_q = await db.execute(
        select(
            OutreachEmail.id,
            OutreachEmail.subject,
            OutreachEmail.opened_at,
            OutreachEmail.clicked_at,
            OutreachEmail.replied_at,
            OutreachEmail.open_count,
            OutreachEmail.click_count,
            Prospect.business_name,
        )
        .join(Prospect, OutreachEmail.prospect_id == Prospect.id)
        .where(
            or_(
                OutreachEmail.opened_at.isnot(None),
                OutreachEmail.clicked_at.isnot(None),
                OutreachEmail.replied_at.isnot(None),
            )
        )
        .order_by(
            func.coalesce(
                OutreachEmail.replied_at,
                OutreachEmail.clicked_at,
                OutreachEmail.opened_at,
            ).desc()
        )
        .limit(20)
    )
    recent = []
    for r in recent_q.all():
        event_type = "replied" if r.replied_at else ("clicked" if r.clicked_at else "opened")
        event_ts = r.replied_at or r.clicked_at or r.opened_at
        recent.append({
            "business": r.business_name,
            "subject": (r.subject or "")[:60],
            "event": event_type,
            "ts": event_ts.isoformat() if event_ts else None,
            "opens": r.open_count or 0,
            "clicks": r.click_count or 0,
        })

    delivered = total_sent  # Assume sent = delivered for now (no DSN parsing yet)
    return {
        "overview": {
            "pending_approval": total_pending,
            "scheduled": total_scheduled,
            "sent": total_sent,
            "delivered": delivered,
            "bounced": total_bounced,
            "failed": total_failed,
            "unsubscribed": total_unsubscribed,
        },
        "engagement": {
            "total_opens": total_opens,
            "unique_opens": unique_opens,
            "total_clicks": total_clicks,
            "unique_clicks": unique_clicks,
            "replied": total_replied,
            "open_rate": round(unique_opens / total_sent * 100, 1) if total_sent > 0 else 0,
            "click_rate": round(unique_clicks / total_sent * 100, 1) if total_sent > 0 else 0,
            "reply_rate": round(total_replied / total_sent * 100, 1) if total_sent > 0 else 0,
            "bounce_rate": round(total_bounced / total_sent * 100, 1) if total_sent > 0 else 0,
        },
        "per_step": per_step,
        "recent_engagement": recent,
    }


# ═══════════════════════════════════════════════════════════════════
# EMAIL TRACKING LIST + UNSUBSCRIBE MANAGEMENT
# ═══════════════════════════════════════════════════════════════════


@outreach_router.get("/email-tracking-list")
async def get_email_tracking_list(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(25, le=200),
    offset: int = Query(0, ge=0),
    filter: str = Query("all"),  # all, sent, opened, clicked, replied, bounced, unsubscribed
    sort: str = Query("sent_at"),  # sent_at, opened_at, clicked_at, business_name
    order: str = Query("desc"),
    search: str = Query(""),
):
    """
    Paginated email tracking list with filter support.
    Returns individual email records with tracking data.
    """
    base_q = select(
        OutreachEmail.id,
        OutreachEmail.subject,
        Prospect.owner_email.label("to_email"),
        OutreachEmail.status,
        OutreachEmail.sequence_step,
        OutreachEmail.sent_at,
        OutreachEmail.opened_at,
        OutreachEmail.clicked_at,
        OutreachEmail.replied_at,
        OutreachEmail.open_count,
        OutreachEmail.click_count,
        OutreachEmail.tracking_id,
        Prospect.business_name,
        Prospect.id.label("prospect_id"),
        Prospect.status.label("prospect_status"),
    ).join(Prospect, OutreachEmail.prospect_id == Prospect.id)

    # Apply filter
    if filter == "sent":
        base_q = base_q.where(OutreachEmail.sent_at.isnot(None))
    elif filter == "opened":
        base_q = base_q.where(OutreachEmail.opened_at.isnot(None))
    elif filter == "clicked":
        base_q = base_q.where(OutreachEmail.clicked_at.isnot(None))
    elif filter == "replied":
        base_q = base_q.where(OutreachEmail.replied_at.isnot(None))
    elif filter == "bounced":
        base_q = base_q.where(OutreachEmail.status == "bounced")
    elif filter == "unsubscribed":
        base_q = base_q.where(Prospect.status == "do_not_contact")
    else:
        # "all" — show only emails that have been sent
        base_q = base_q.where(OutreachEmail.sent_at.isnot(None))

    # Search
    if search:
        base_q = base_q.where(
            or_(
                Prospect.business_name.ilike(f"%{search}%"),
                Prospect.owner_email.ilike(f"%{search}%"),
                OutreachEmail.subject.ilike(f"%{search}%"),
            )
        )

    # Count
    from sqlalchemy import func as fn2
    count_q = select(fn2.count()).select_from(base_q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Sort
    sort_map = {
        "sent_at": OutreachEmail.sent_at,
        "opened_at": OutreachEmail.opened_at,
        "clicked_at": OutreachEmail.clicked_at,
        "business_name": Prospect.business_name,
        "open_count": OutreachEmail.open_count,
        "click_count": OutreachEmail.click_count,
    }
    sort_col = sort_map.get(sort, OutreachEmail.sent_at)
    if sort_col is not None:
        base_q = base_q.order_by(sort_col.desc().nullslast() if order == "desc" else sort_col.asc().nullsfirst())
    else:
        base_q = base_q.order_by(OutreachEmail.sent_at.desc().nullslast())

    base_q = base_q.offset(offset).limit(limit)
    rows = (await db.execute(base_q)).all()

    emails = []
    for r in rows:
        emails.append({
            "id": str(r.id),
            "subject": r.subject or "",
            "to_email": r.to_email or "",
            "status": r.status,
            "sequence_step": r.sequence_step,
            "sent_at": r.sent_at.isoformat() if r.sent_at else None,
            "opened_at": r.opened_at.isoformat() if r.opened_at else None,
            "clicked_at": r.clicked_at.isoformat() if r.clicked_at else None,
            "replied_at": r.replied_at.isoformat() if r.replied_at else None,
            "open_count": r.open_count or 0,
            "click_count": r.click_count or 0,
            "tracking_id": str(r.tracking_id) if r.tracking_id else None,
            "business_name": r.business_name or "",
            "prospect_id": str(r.prospect_id),
            "prospect_status": r.prospect_status,
        })

    return {"emails": emails, "total": total, "limit": limit, "offset": offset}


@outreach_router.post("/prospects/{prospect_id}/resubscribe")
async def resubscribe_prospect(prospect_id: str, db: AsyncSession = Depends(get_db)):
    """Re-subscribe a prospect that was marked do_not_contact."""
    prospect = await db.get(Prospect, uuid.UUID(prospect_id))
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    if prospect.status != "do_not_contact":
        raise HTTPException(status_code=400, detail=f"Prospect is '{prospect.status}', not do_not_contact")

    prospect.status = "audited"  # Go back to audited so cadence can pick them up
    await db.commit()

    return {"message": f"Re-subscribed {prospect.business_name}", "status": prospect.status}


@outreach_router.get("/unsubscribed-list")
async def get_unsubscribed_list(db: AsyncSession = Depends(get_db)):
    """List all prospects marked as do_not_contact (unsubscribed)."""
    result = await db.execute(
        select(
            Prospect.id,
            Prospect.business_name,
            Prospect.owner_email,
            Prospect.owner_name,
            Prospect.business_type,
            Prospect.city,
            Prospect.updated_at,
        )
        .where(Prospect.status == "do_not_contact")
        .order_by(Prospect.updated_at.desc())
    )
    prospects = []
    for r in result.all():
        prospects.append({
            "id": str(r.id),
            "business_name": r.business_name or "",
            "email": r.owner_email or "",
            "owner_name": r.owner_name or "",
            "business_type": r.business_type or "",
            "city": r.city or "",
            "unsubscribed_at": r.updated_at.isoformat() if r.updated_at else None,
        })
    return {"prospects": prospects, "total": len(prospects)}


# ═══════════════════════════════════════════════════════════════════

from fastapi.responses import Response, RedirectResponse


@outreach_router.get("/track/open/{tracking_id}.png")
async def track_open(tracking_id: str):
    """Return 1x1 tracking pixel and record open event."""
    from api.services.email_tracker import record_open, TRACKING_PIXEL
    await record_open(tracking_id)
    return Response(
        content=TRACKING_PIXEL,
        media_type="image/png",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
    )


@outreach_router.get("/track/click/{tracking_id}")
async def track_click(tracking_id: str, url: str = ""):
    """Record click event and redirect to destination."""
    from api.services.email_tracker import record_click
    from urllib.parse import unquote
    destination = unquote(url)
    if not destination or not destination.startswith(("http://", "https://")):
        destination = "https://ajayadesign.github.io"
    await record_click(tracking_id, destination)
    return RedirectResponse(url=destination, status_code=302)


@outreach_router.get("/track/unsubscribe/{tracking_id}")
async def track_unsubscribe(tracking_id: str):
    """Handle unsubscribe request."""
    from api.services.email_tracker import record_unsubscribe
    success = await record_unsubscribe(tracking_id)
    return Response(
        content="<html><body><h2>You have been unsubscribed.</h2>"
                "<p>You will no longer receive emails from AjayaDesign.</p>"
                "</body></html>",
        media_type="text/html",
    )


# ═══════════════════════════════════════════════════════════════════
# ENGINE ACTION ENDPOINTS (Crawl, Audit, Recon, Compose, Send)
# ═══════════════════════════════════════════════════════════════════

@outreach_router.post("/rings/{ring_id}/crawl")
async def trigger_crawl(ring_id: str):
    """Manually trigger a crawl for a specific ring."""
    from api.services.crawl_engine import crawl_ring
    import asyncio
    asyncio.create_task(crawl_ring(ring_id))
    return {"message": f"Crawl started for ring {ring_id}", "status": "started"}


@outreach_router.post("/prospects/{prospect_id}/audit")
async def trigger_audit(prospect_id: str):
    """Trigger a website audit for a specific prospect."""
    from api.services.intel_engine import audit_prospect
    import asyncio
    asyncio.create_task(audit_prospect(prospect_id))
    return {"message": f"Audit started for prospect {prospect_id}"}


@outreach_router.post("/prospects/{prospect_id}/recon")
async def trigger_recon(prospect_id: str):
    """Trigger email/owner recon for a specific prospect."""
    from api.services.recon_engine import recon_prospect
    import asyncio
    asyncio.create_task(recon_prospect(prospect_id))
    return {"message": f"Recon started for prospect {prospect_id}"}


@outreach_router.get("/prospects/{prospect_id}/email-preview")
async def preview_prospect_email(
    prospect_id: str,
    step: int = Query(1, ge=1, le=5),
):
    """Preview the email that would be sent for a prospect at a given step."""
    from api.services.template_engine import preview_email
    result = await preview_email(prospect_id, step)
    if not result:
        raise HTTPException(status_code=400, detail="Could not compose email")
    return result


@outreach_router.post("/prospects/{prospect_id}/enqueue")
async def enqueue_prospect_email(prospect_id: str):
    """Enqueue a prospect into the outreach sequence."""
    from api.services.cadence_engine import enqueue_prospect
    email_id = await enqueue_prospect(prospect_id)
    if not email_id:
        raise HTTPException(status_code=400, detail="Could not enqueue prospect")
    return {"message": "Enqueued", "email_id": email_id}


@outreach_router.post("/prospects/{prospect_id}/test-email")
async def create_test_email(prospect_id: str, body: dict = {}, db: AsyncSession = Depends(get_db)):
    """
    Create a test email in the approval queue for ANY prospect, regardless of status.
    
    Skips all pipeline gates — just compose the email and put it in pending_approval
    so you can preview and test the template rendering before sending to real customers.
    
    Body: { "to_email": "optional@override.com", "step": 1 }
    """
    from api.services.template_engine import compose_email
    from api.models.prospect import OutreachEmail

    step = body.get("step", 1) if body else 1

    # Verify prospect exists
    prospect = await db.get(Prospect, uuid.UUID(prospect_id))
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")

    # Compose email (works even without audit data — template handles N/A gracefully)
    result = await compose_email(prospect_id, step)
    if not result:
        raise HTTPException(status_code=400, detail="Could not compose email — check template")

    # Create email record in pending_approval
    email = OutreachEmail(
        id=uuid.uuid4(),
        prospect_id=prospect.id,
        subject=result["subject"],
        body_html=result["body_html"],
        body_text=result["body_text"],
        template_id=result["template_id"],
        sequence_step=result["sequence_step"],
        personalization=result["variables"],
        status="pending_approval",
    )
    db.add(email)
    await db.commit()
    await db.refresh(email)

    return {
        "message": f"Test email created for {prospect.business_name}",
        "email_id": str(email.id),
        "subject": email.subject,
        "status": "pending_approval",
    }


# ── Prospect Activities (Call Logs, Notes) ──────────────
@outreach_router.get("/prospects/{prospect_id}/activities")
async def list_activities(prospect_id: str, db: AsyncSession = Depends(get_db)):
    """List all activity logs for a prospect, newest first."""
    result = await db.execute(
        select(ProspectActivity)
        .where(ProspectActivity.prospect_id == uuid.UUID(prospect_id))
        .order_by(ProspectActivity.created_at.desc())
    )
    activities = result.scalars().all()
    return {"activities": [a.to_dict() for a in activities]}


@outreach_router.post("/prospects/{prospect_id}/activities")
async def log_activity(prospect_id: str, body: dict, db: AsyncSession = Depends(get_db)):
    """Log a phone call, meeting, or other interaction with a prospect.

    Body: {
        activity_type: "phone_call" | "meeting" | "voicemail" | "text_message" | "in_person" | "note",
        outcome: "interested" | "not_interested" | "callback" | "no_answer" | "voicemail" | "other",
        notes: "Free-form notes about the interaction",
        duration_minutes: 5,
        contact_name: "Who we spoke with"
    }
    """
    prospect = await db.get(Prospect, uuid.UUID(prospect_id))
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")

    valid_types = {"phone_call", "meeting", "voicemail", "text_message", "in_person", "note"}
    activity_type = body.get("activity_type", "phone_call")
    if activity_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid activity_type. Must be one of: {', '.join(sorted(valid_types))}")

    activity = ProspectActivity(
        prospect_id=prospect.id,
        activity_type=activity_type,
        outcome=body.get("outcome"),
        notes=body.get("notes"),
        duration_minutes=body.get("duration_minutes"),
        contact_name=body.get("contact_name"),
    )
    db.add(activity)
    await db.commit()
    await db.refresh(activity)

    logger.info(f"Activity logged for {prospect.business_name}: {activity_type} — {body.get('outcome', 'n/a')}")
    return activity.to_dict()


@outreach_router.delete("/activities/{activity_id}")
async def delete_activity(activity_id: str, db: AsyncSession = Depends(get_db)):
    """Delete an activity log entry."""
    activity = await db.get(ProspectActivity, uuid.UUID(activity_id))
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    await db.delete(activity)
    await db.commit()
    return {"message": "Activity deleted"}


@outreach_router.post("/emails/{email_id}/send")
async def send_email(email_id: str):
    """Manually send a specific scheduled email."""
    from api.services.cadence_engine import send_email_record
    success = await send_email_record(email_id)
    if not success:
        raise HTTPException(status_code=400, detail="Send failed")
    return {"message": "Email sent"}


@outreach_router.post("/emails/{email_id}/send-test")
async def send_test_email(email_id: str, body: dict = {}, db: AsyncSession = Depends(get_db)):
    """
    Send a test copy of an email to yourself (or any address) WITHOUT
    affecting the real email record or prospect status.

    Body: { "to_email": "your@email.com" }  (defaults to SMTP_EMAIL)
    """
    from api.services.email_service import send_email as smtp_send
    from api.services.email_tracker import inject_tracking
    from api.models.prospect import OutreachEmail

    email = await db.get(OutreachEmail, uuid.UUID(email_id))
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")

    to_email = (body.get("to_email") or "").strip()
    if not to_email:
        to_email = settings.smtp_email
    if not to_email:
        raise HTTPException(status_code=400, detail="No recipient. Provide to_email or configure SMTP_EMAIL.")

    # Inject tracking
    tracked_html = inject_tracking(email.body_html, email.tracking_id) if email.tracking_id else email.body_html

    # Prefix subject with [TEST] so it's clear
    test_subject = f"[TEST] {email.subject}"

    result = await smtp_send(
        to=to_email,
        subject=test_subject,
        body_html=tracked_html,
        reply_to=settings.smtp_email,
    )

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("message", "Send failed"))

    return {
        "message": f"Test email sent to {to_email}",
        "to": to_email,
        "subject": test_subject,
    }


@outreach_router.post("/emails/{email_id}/reply")
async def process_email_reply(email_id: str, body: dict):
    """Process an incoming reply for an email (called manually or via webhook)."""
    from api.services.reply_classifier import process_reply
    result = await process_reply(email_id, body.get("text", ""))
    return result


@outreach_router.get("/queue")
async def get_queue(db: AsyncSession = Depends(get_db)):
    """Get email queue status."""
    from api.services.cadence_engine import get_queue_status
    return await get_queue_status()


@outreach_router.post("/batch/audit")
async def trigger_batch_audit(limit: int = Query(10, le=50)):
    """Trigger batch audits for discovered prospects."""
    from api.services.intel_engine import batch_audit_prospects
    import asyncio
    asyncio.create_task(batch_audit_prospects(limit))
    return {"message": f"Batch audit started (limit={limit})"}


@outreach_router.post("/batch/recon")
async def trigger_batch_recon(limit: int = Query(10, le=50)):
    """Trigger batch recon for audited prospects."""
    from api.services.recon_engine import batch_recon_prospects
    import asyncio
    asyncio.create_task(batch_recon_prospects(limit))
    return {"message": f"Batch recon started (limit={limit})"}


@outreach_router.post("/batch/enqueue")
async def trigger_batch_enqueue(limit: int = Query(10, le=50)):
    """Batch-enqueue enriched prospects into send pipeline."""
    from api.services.cadence_engine import batch_enqueue_prospects
    count = await batch_enqueue_prospects(limit)
    return {"message": f"Enqueued {count} prospects"}


@outreach_router.post("/batch/send")
async def trigger_batch_send():
    """Process the send queue (normally done by scheduler)."""
    from api.services.cadence_engine import process_send_queue
    stats = await process_send_queue()
    return stats


# ── Bulk Selection Endpoints (operate on a list of IDs) ──────────────

@outreach_router.post("/bulk/audit")
async def bulk_audit(body: dict):
    """Trigger audits for a specific list of prospect IDs."""
    ids = body.get("prospect_ids", [])
    if not ids:
        raise HTTPException(status_code=400, detail="No prospect_ids provided")
    from api.services.intel_engine import audit_prospect
    import asyncio

    async def _run():
        count = 0
        for pid in ids:
            try:
                result = await audit_prospect(str(pid))
                if result:
                    count += 1
            except Exception as e:
                logger.error("Bulk audit failed for %s: %s", pid, e)
            await asyncio.sleep(2)
        logger.info("Bulk audit complete: %d/%d succeeded", count, len(ids))

    asyncio.create_task(_run())
    return {"message": f"Bulk audit started for {len(ids)} prospects"}


@outreach_router.post("/bulk/recon")
async def bulk_recon(body: dict):
    """Trigger recon for a specific list of prospect IDs."""
    ids = body.get("prospect_ids", [])
    if not ids:
        raise HTTPException(status_code=400, detail="No prospect_ids provided")
    from api.services.recon_engine import recon_prospect
    import asyncio

    async def _run():
        count = 0
        for pid in ids:
            try:
                result = await recon_prospect(str(pid))
                if result and result.get("owner_email"):
                    count += 1
            except Exception as e:
                logger.error("Bulk recon failed for %s: %s", pid, e)
            await asyncio.sleep(1)
        logger.info("Bulk recon complete: %d/%d found emails", count, len(ids))

    asyncio.create_task(_run())
    return {"message": f"Bulk recon started for {len(ids)} prospects"}


@outreach_router.post("/bulk/enqueue")
async def bulk_enqueue(body: dict):
    """Generate email drafts for a specific list of prospect IDs."""
    ids = body.get("prospect_ids", [])
    if not ids:
        raise HTTPException(status_code=400, detail="No prospect_ids provided")
    from api.services.cadence_engine import enqueue_prospect

    count = 0
    errors = []
    for pid in ids:
        try:
            email_id = await enqueue_prospect(str(pid))
            if email_id:
                count += 1
        except Exception as e:
            errors.append({"id": pid, "error": str(e)})
    return {"message": f"Enqueued {count}/{len(ids)} prospects", "enqueued": count, "errors": errors}


@outreach_router.post("/bulk/advance")
async def bulk_advance(body: dict):
    """
    Smart advance: automatically determines the next step for each prospect
    and triggers it. This is the "do everything" button.
    """
    ids = body.get("prospect_ids", [])
    if not ids:
        raise HTTPException(status_code=400, detail="No prospect_ids provided")

    from api.services.intel_engine import audit_prospect
    from api.services.recon_engine import recon_prospect
    from api.services.cadence_engine import enqueue_prospect
    import asyncio

    async def _run():
        stats = {"audit": 0, "recon": 0, "enqueue": 0, "skip": 0, "error": 0}
        async with async_session_factory() as db:
            for pid in ids:
                try:
                    result = await db.execute(
                        select(Prospect).where(Prospect.id == uuid.UUID(str(pid)))
                    )
                    p = result.scalar_one_or_none()
                    if not p:
                        stats["skip"] += 1
                        continue

                    if p.status == "discovered" and p.has_website and p.website_url:
                        await audit_prospect(str(pid))
                        stats["audit"] += 1
                    elif p.status == "discovered" and (not p.has_website or not p.website_url):
                        # Fast-track no-website to audited, then recon
                        p.status = "audited"
                        p.updated_at = datetime.now(timezone.utc)
                        await db.commit()
                        await recon_prospect(str(pid))
                        stats["recon"] += 1
                    elif p.status == "audited":
                        await recon_prospect(str(pid))
                        stats["recon"] += 1
                    elif p.status == "enriched" and p.owner_email:
                        await enqueue_prospect(str(pid))
                        stats["enqueue"] += 1
                    else:
                        stats["skip"] += 1

                    await asyncio.sleep(1)
                except Exception as e:
                    logger.error("Bulk advance failed for %s: %s", pid, e)
                    stats["error"] += 1

        logger.info("Bulk advance complete: %s", stats)

    asyncio.create_task(_run())
    return {"message": f"Advancing {len(ids)} prospects through pipeline"}


# ── Pipeline Worker Control Endpoints ──────────────────────────────

@outreach_router.get("/pipeline/status")
async def pipeline_status(db: AsyncSession = Depends(get_db)):
    """Get pipeline worker status and stats, including DB status counts."""
    from api.services.pipeline_worker import get_pipeline_worker
    worker = get_pipeline_worker()
    stats = worker.stats

    # Include live DB-sourced status counts so pipeline bar doesn't depend on _lastStats
    try:
        result = await db.execute(
            select(
                Prospect.status,
                func.count(Prospect.id),
            ).group_by(Prospect.status)
        )
        status_counts = {row[0]: row[1] for row in result.fetchall()}
        stats["db_status_counts"] = status_counts
    except Exception:
        stats["db_status_counts"] = {}

    return stats


@outreach_router.post("/pipeline/start")
async def pipeline_start(body: dict = {}):
    """Start the pipeline worker. Pass {count: N} to start N concurrent agents."""
    from api.services.pipeline_worker import get_pipeline_manager
    mgr = get_pipeline_manager()
    count = body.get("count", 1) if body else 1
    count = max(1, min(count, 5))  # clamp 1-5
    started = mgr.start_multiple(count)
    return {"message": f"Started {len(started)} pipeline agents", "agents": started, "stats": mgr.stats}


@outreach_router.post("/pipeline/stop")
async def pipeline_stop(body: dict = {}):
    """Stop pipeline worker(s). Pass {agent_id: N} to stop one, or omit to stop all."""
    from api.services.pipeline_worker import get_pipeline_manager
    mgr = get_pipeline_manager()
    agent_id = body.get("agent_id") if body else None
    if agent_id is not None:
        mgr.stop_agent(int(agent_id))
        return {"message": f"Agent #{agent_id} stopped"}
    else:
        mgr.stop_all()
        return {"message": "All pipeline agents stopped"}


@outreach_router.get("/pipeline/logs")
async def pipeline_logs(since: float = Query(0, description="Unix timestamp — only return logs after this time"), limit: int = Query(100, le=500)):
    """Get recent real pipeline log entries for Mission Control terminal."""
    from api.services.pipeline_worker import get_pipeline_logs
    entries = get_pipeline_logs(since=since, limit=limit)
    return {"logs": entries, "count": len(entries)}


@outreach_router.post("/pipeline/scale")
async def pipeline_scale(body: dict):
    """Scale to exactly N agents. Starts new ones or stops excess."""
    from api.services.pipeline_worker import get_pipeline_manager
    mgr = get_pipeline_manager()
    target = max(0, min(body.get("count", 1), 5))
    current = mgr.agent_count
    if target > current:
        for i in range(target):
            mgr.start_agent(i)
    elif target < current:
        # Stop agents from highest ID down
        for agent_id in sorted(mgr._agents.keys(), reverse=True):
            if mgr.agent_count <= target:
                break
            if mgr._agents[agent_id]._running:
                mgr.stop_agent(agent_id)
    return {
        "message": f"Scaled to {mgr.agent_count} agents (was {current})",
        "agent_count": mgr.agent_count,
        "stats": mgr.stats,
    }


@outreach_router.post("/pipeline/recover")
async def pipeline_recover():
    """Run one-shot recovery to fix all bad states."""
    from api.services.pipeline_worker import recover_all_bad_states
    result = await recover_all_bad_states()
    return {"message": "Recovery complete", "recovered": result}


@outreach_router.get("/rings-summary")
async def get_rings_summary():
    """Get all rings with stats for the geo war room sidebar."""
    from api.services.geo_ring_manager import get_all_rings_summary
    return await get_all_rings_summary()


@outreach_router.post("/rings/{ring_id}/expand")
async def trigger_ring_expansion(ring_id: str):
    """Approve expansion from current ring to next."""
    from api.services.geo_ring_manager import expand_to_next_ring
    result = await expand_to_next_ring()
    return result


# ═══════════════════════════════════════════════════════════════════
# MISSING ENDPOINTS (per plan audit)
# ═══════════════════════════════════════════════════════════════════

@outreach_router.get("/emails/{email_id}")
async def get_email(email_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single email by ID with prospect context."""
    result = await db.execute(
        select(OutreachEmail).where(OutreachEmail.id == uuid.UUID(email_id))
    )
    email = result.scalar_one_or_none()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    d = email.to_dict()
    # Add prospect context for the editor
    prospect = await db.get(Prospect, email.prospect_id)
    if prospect:
        d["prospect_name"] = prospect.business_name
        d["to_email"] = prospect.owner_email
    return d


@outreach_router.post("/emails/{email_id}/approve")
async def approve_email(email_id: str, db: AsyncSession = Depends(get_db)):
    """Approve a pending email — marks it ready for the send queue."""
    result = await db.execute(
        select(OutreachEmail).where(OutreachEmail.id == uuid.UUID(email_id))
    )
    email = result.scalar_one_or_none()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    if email.status not in ("pending_approval", "draft"):
        raise HTTPException(status_code=400, detail=f"Cannot approve email in '{email.status}' status")
    email.status = "approved"
    # Reset scheduled_for to now so it sends at the next queue cycle
    email.scheduled_for = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(email)
    return {"message": "Email approved — will send at next queue cycle", "email": email.to_dict()}


@outreach_router.patch("/emails/{email_id}")
async def edit_email(email_id: str, body: dict, db: AsyncSession = Depends(get_db)):
    """Edit a pending/draft email's subject, body, or scheduled time before approval."""
    result = await db.execute(
        select(OutreachEmail).where(OutreachEmail.id == uuid.UUID(email_id))
    )
    email = result.scalar_one_or_none()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    if email.status not in ("pending_approval", "draft", "approved"):
        raise HTTPException(status_code=400, detail=f"Cannot edit email in '{email.status}' status")

    allowed = {"subject", "body_html", "body_text", "scheduled_for"}
    for key in body:
        if key not in allowed:
            continue
        if key == "scheduled_for" and body[key]:
            setattr(email, key, datetime.fromisoformat(body[key]))
        else:
            setattr(email, key, body[key])
    await db.commit()
    await db.refresh(email)
    return {"message": "Email updated", "email": email.to_dict()}


@outreach_router.delete("/emails/{email_id}")
async def delete_email(email_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a draft email (only drafts can be deleted)."""
    result = await db.execute(
        select(OutreachEmail).where(OutreachEmail.id == uuid.UUID(email_id))
    )
    email = result.scalar_one_or_none()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    if email.status not in ("draft", "approved", "pending_approval"):
        raise HTTPException(status_code=400, detail="Can only delete draft/pending/approved emails")
    await db.delete(email)
    await db.commit()
    return {"message": f"Email {email_id} deleted"}


@outreach_router.delete("/emails/{email_id}")
async def delete_email(email_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a draft email (only drafts can be deleted)."""
    result = await db.execute(
        select(OutreachEmail).where(OutreachEmail.id == uuid.UUID(email_id))
    )
    email = result.scalar_one_or_none()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    if email.status not in ("draft", "approved", "pending_approval"):
        raise HTTPException(status_code=400, detail="Can only delete draft/pending/approved emails")
    await db.delete(email)
    await db.commit()
    return {"message": f"Email {email_id} deleted"}


@outreach_router.post("/emails/{email_id}/regenerate")
async def regenerate_email(email_id: str, db: AsyncSession = Depends(get_db)):
    """Re-compose an email using current audit data. Fixes stale/wrong values."""
    from api.services.template_engine import compose_email as _compose

    result = await db.execute(
        select(OutreachEmail).where(OutreachEmail.id == uuid.UUID(email_id))
    )
    email = result.scalar_one_or_none()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    if email.status not in ("draft", "pending_approval", "approved"):
        raise HTTPException(status_code=400, detail=f"Cannot regenerate email in '{email.status}' status")

    composed = await _compose(str(email.prospect_id), sequence_step=email.sequence_step)
    if not composed:
        raise HTTPException(status_code=500, detail="Template render failed")

    email.subject = composed["subject"]
    email.body_html = composed["body_html"]
    email.body_text = composed["body_text"]
    email.personalization = composed["variables"]
    email.template_id = composed["template_id"]
    await db.commit()
    await db.refresh(email)
    return {"message": "Email regenerated with current data", "email": email.to_dict()}


@outreach_router.post("/emails/batch-regenerate")
async def batch_regenerate_emails(body: dict, db: AsyncSession = Depends(get_db)):
    """Regenerate all pending/approved emails with current audit data.
    Body: {email_ids: [...]} or {all_pending: true}."""
    from api.services.template_engine import compose_email as _compose

    if body.get("all_pending"):
        result = await db.execute(
            select(OutreachEmail).where(
                OutreachEmail.status.in_(["pending_approval", "draft", "approved"])
            )
        )
    else:
        ids = body.get("email_ids", [])
        if not ids:
            raise HTTPException(status_code=400, detail="No email IDs provided")
        result = await db.execute(
            select(OutreachEmail).where(
                OutreachEmail.id.in_([uuid.UUID(i) for i in ids])
            )
        )

    emails = result.scalars().all()
    regenerated = 0
    errors = 0

    for email in emails:
        try:
            composed = await _compose(str(email.prospect_id), sequence_step=email.sequence_step)
            if composed:
                email.subject = composed["subject"]
                email.body_html = composed["body_html"]
                email.body_text = composed["body_text"]
                email.personalization = composed["variables"]
                regenerated += 1
            else:
                errors += 1
        except Exception as e:
            logger.warning("Regen failed for %s: %s", email.id, e)
            errors += 1

    await db.commit()
    return {"message": f"Regenerated {regenerated} emails ({errors} errors)", "regenerated": regenerated, "errors": errors}


@outreach_router.patch("/rings/{ring_id}")
async def update_ring(ring_id: str, body: dict, db: AsyncSession = Depends(get_db)):
    """Update ring fields (status, categories_done, etc.)."""
    result = await db.execute(
        select(GeoRing).where(GeoRing.id == uuid.UUID(ring_id))
    )
    ring = result.scalar_one_or_none()
    if not ring:
        raise HTTPException(status_code=404, detail="Ring not found")

    allowed = {"status", "categories_done", "businesses_found", "businesses_with_websites", "businesses_without_websites"}
    for key, value in body.items():
        if key in allowed:
            setattr(ring, key, value)
    await db.commit()
    await db.refresh(ring)
    return ring.to_dict()


@outreach_router.patch("/sequences/{sequence_id}")
async def update_sequence(sequence_id: str, body: dict, db: AsyncSession = Depends(get_db)):
    """Update a sequence's name, steps, or active status."""
    result = await db.execute(
        select(OutreachSequence).where(OutreachSequence.id == uuid.UUID(sequence_id))
    )
    seq = result.scalar_one_or_none()
    if not seq:
        raise HTTPException(status_code=404, detail="Sequence not found")

    allowed = {"name", "industry_tag", "steps", "is_active"}
    for key, value in body.items():
        if key in allowed:
            setattr(seq, key, value)
    seq.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(seq)
    return seq.to_dict()


@outreach_router.get("/agent/log")
async def get_agent_log_stream():
    """Get recent agent log entries from Firebase (SSE-style polling fallback)."""
    from api.services.firebase_summarizer import _ref
    ref = _ref("outreach/log")
    if not ref:
        return {"log": [], "message": "Firebase unavailable"}
    try:
        data = ref.order_by_child("ts").limit_to_last(100).get()
        if not data:
            return {"log": []}
        entries = sorted(data.values(), key=lambda x: x.get("ts", 0), reverse=True)
        return {"log": entries}
    except Exception as e:
        logger.error(f"Agent log fetch failed: {e}")
        return {"log": [], "error": str(e)}


@outreach_router.get("/files/screenshot/{prospect_id}/{screenshot_type}")
async def get_screenshot(prospect_id: str, screenshot_type: str, db: AsyncSession = Depends(get_db)):
    """Serve a prospect's screenshot (desktop or mobile)."""
    from fastapi.responses import FileResponse
    import os
    result = await db.execute(
        select(Prospect).where(Prospect.id == uuid.UUID(prospect_id))
    )
    prospect = result.scalar_one_or_none()
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")

    path = prospect.screenshot_desktop if screenshot_type == "desktop" else prospect.screenshot_mobile
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Screenshot not found")
    return FileResponse(path, media_type="image/png")


@outreach_router.get("/files/audit/{prospect_id}")
async def get_audit_file(prospect_id: str, db: AsyncSession = Depends(get_db)):
    """Get audit JSON data for a prospect."""
    result = await db.execute(
        select(Prospect).where(Prospect.id == uuid.UUID(prospect_id))
    )
    prospect = result.scalar_one_or_none()
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    if not prospect.audit_json:
        raise HTTPException(status_code=404, detail="No audit data available")
    return {
        "prospect_id": str(prospect.id),
        "business_name": prospect.business_name,
        "audit": prospect.audit_json,
        "audit_date": prospect.audit_date.isoformat() if prospect.audit_date else None,
    }
