"""
AjayaDesign Automation — Activity Log API routes.
Provides a full audit trail for contracts, invoices, and portfolio actions.
"""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db, async_session
from api.models.activity_log import ActivityLog

logger = logging.getLogger(__name__)
activity_router = APIRouter(prefix="/activity", tags=["activity"])


# ═══════════════════════════════════════════════════════
#  Helper — fire-and-forget log writer
# ═══════════════════════════════════════════════════════

async def log_activity(
    entity_type: str,
    entity_id: str,
    action: str,
    description: str = "",
    icon: str = "📋",
    actor: str = "admin",
    metadata: dict | None = None,
    db: AsyncSession | None = None,
) -> None:
    """
    Record an activity log entry.
    Can be called from anywhere — if no db session is passed, opens its own.
    """
    entry = ActivityLog(
        id=str(uuid.uuid4()),
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        description=description,
        icon=icon,
        actor=actor,
        metadata=metadata or {},
    )

    try:
        if db:
            db.add(entry)
            # Don't commit here — the caller's commit will include this
        else:
            async with async_session() as session:
                session.add(entry)
                await session.commit()
    except Exception as e:
        logger.warning(f"Failed to write activity log: {e}")

    # Also sync to Firebase for real-time feed
    try:
        from api.services.firebase import sync_activity_to_firebase
        sync_activity_to_firebase({
            "id": entry.id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "action": action,
            "description": description,
            "icon": icon,
            "actor": actor,
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception:
        pass  # Non-critical


# ═══════════════════════════════════════════════════════
#  API Endpoints
# ═══════════════════════════════════════════════════════

@activity_router.get("")
async def list_activities(
    entity_type: str | None = Query(None, description="Filter by entity type"),
    entity_id: str | None = Query(None, description="Filter by entity ID"),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """
    List activity log entries, newest first.
    Optional filters: entity_type, entity_id.
    """
    stmt = select(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(limit)

    if entity_type:
        stmt = stmt.where(ActivityLog.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(ActivityLog.entity_id == entity_id)

    result = await db.execute(stmt)
    logs = result.scalars().all()

    return {
        "activities": [
            {
                "id": log.id,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "action": log.action,
                "description": log.description,
                "icon": log.icon,
                "actor": log.actor,
                "metadata": log.metadata or {},
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ],
        "total": len(logs),
    }


@activity_router.get("/entity/{entity_type}/{entity_id}")
async def get_entity_history(
    entity_type: str,
    entity_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get full history for a specific entity (contract, invoice, etc.)."""
    result = await db.execute(
        select(ActivityLog)
        .where(ActivityLog.entity_type == entity_type)
        .where(ActivityLog.entity_id == entity_id)
        .order_by(ActivityLog.created_at.asc())
    )
    logs = result.scalars().all()

    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "history": [
            {
                "id": log.id,
                "action": log.action,
                "description": log.description,
                "icon": log.icon,
                "actor": log.actor,
                "metadata": log.metadata or {},
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ],
        "total": len(logs),
    }
