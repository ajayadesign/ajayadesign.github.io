"""
AjayaDesign Automation — Portfolio routes (seed + patch builds).
"""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.models.build import Build
from api.schemas.contract import BuildPatchRequest, PortfolioSeedRequest

logger = logging.getLogger(__name__)
router = APIRouter(tags=["portfolio"])


@router.get("/portfolio")
async def list_portfolio(db: AsyncSession = Depends(get_db)):
    """List all completed/portfolio builds."""
    result = await db.execute(
        select(Build).where(
            Build.status.in_(["complete", "success", "deployed"])
        ).order_by(Build.created_at.desc())
    )
    builds = result.scalars().all()
    return {
        "sites": [
            {
                "id": str(b.id),
                "short_id": b.short_id,
                "client_name": b.client_name or "",
                "email": b.email or "",
                "phone": b.phone or "",
                "niche": b.niche or "",
                "goals": b.goals or "",
                "location": b.location or "",
                "live_url": b.live_url or "",
                "repo_name": b.repo_name or "",
                "brand_colors": b.brand_colors or "",
                "tagline": b.tagline or "",
                "status": b.status or "",
                "created_at": b.created_at.isoformat() if b.created_at else None,
                "directory_name": (b.live_url or "").split("/")[-1] if b.live_url else "",
            }
            for b in builds
        ],
        "total": len(builds),
    }


@router.patch("/builds/{short_id}")
async def patch_build(
    short_id: str,
    req: BuildPatchRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update a build's client details (for portfolio editing)."""
    result = await db.execute(
        select(Build).where(Build.short_id == short_id)
    )
    build = result.scalar_one_or_none()
    if not build:
        raise HTTPException(404, f"Build {short_id} not found")

    update_data = req.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(build, key, value)

    await db.commit()
    await db.refresh(build)

    logger.info(f"✅ Build {short_id} patched: {list(update_data.keys())}")
    return {
        "short_id": build.short_id,
        "client_name": build.client_name,
        "email": build.email,
        "niche": build.niche,
        "status": build.status,
        "updated": list(update_data.keys()),
    }


@router.post("/portfolio/seed")
async def seed_portfolio(req: PortfolioSeedRequest, db: AsyncSession = Depends(get_db)):
    """
    Seed existing portfolio websites as Build records.
    Used to populate the 4 existing client sites that don't have DB records.
    Skips sites that already exist (matched by client_name).
    """
    created = []
    skipped = []

    for site in req.sites:
        # Check if already exists
        result = await db.execute(
            select(Build).where(Build.client_name == site.client_name)
        )
        existing = result.scalar_one_or_none()
        if existing:
            skipped.append(site.client_name)
            continue

        build = Build(
            short_id=uuid.uuid4().hex[:8],
            client_name=site.client_name,
            niche=site.niche,
            goals=site.goals,
            email=site.email,
            phone=site.phone,
            location=site.location,
            live_url=site.live_url,
            repo_name=site.repo_name,
            brand_colors=site.brand_colors,
            tagline=site.tagline,
            status=site.status or "complete",
            created_at=datetime.now(timezone.utc),
        )
        db.add(build)
        created.append(site.client_name)

    await db.commit()
    logger.info(f"✅ Portfolio seeded: {len(created)} created, {len(skipped)} skipped")
    return {
        "created": created,
        "skipped": skipped,
        "total_created": len(created),
        "total_skipped": len(skipped),
    }
