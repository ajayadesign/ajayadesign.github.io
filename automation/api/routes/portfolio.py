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
from api.services.firebase import sync_portfolio_site_to_firebase, sync_build_to_firebase

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

    # Sync to Firebase (both portfolio/ and builds/ nodes)
    portfolio_data = {
        "short_id": build.short_id,
        "client_name": build.client_name or "",
        "email": getattr(build, "email", "") or "",
        "phone": getattr(build, "phone", "") or "",
        "niche": build.niche or "",
        "goals": build.goals or "",
        "location": getattr(build, "location", "") or "",
        "live_url": build.live_url or "",
        "repo_name": build.repo_name or "",
        "brand_colors": getattr(build, "brand_colors", "") or "",
        "tagline": getattr(build, "tagline", "") or "",
        "status": build.status or "complete",
    }
    sync_portfolio_site_to_firebase(portfolio_data)
    sync_build_to_firebase({
        "short_id": build.short_id,
        "client_name": build.client_name or "",
        "niche": build.niche or "",
        "email": getattr(build, "email", "") or "",
        "status": build.status or "complete",
        "created_at": build.created_at.isoformat() if build.created_at else "",
        "started_at": "",
        "finished_at": "",
        "live_url": build.live_url or "",
        "repo_full": "",
        "protected": build.protected if hasattr(build, 'protected') else False,
    })

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
        created.append({"client_name": site.client_name, "short_id": build.short_id})

    await db.commit()

    # Sync all newly created sites to Firebase (both portfolio/ and builds/ nodes)
    for item in created:
        sid = item["short_id"]
        # Find the matching site data from request
        site_data = next((s for s in req.sites if s.client_name == item["client_name"]), None)
        if site_data:
            sync_portfolio_site_to_firebase({
                "short_id": sid,
                "client_name": site_data.client_name,
                "email": site_data.email or "",
                "phone": site_data.phone or "",
                "niche": site_data.niche or "",
                "goals": site_data.goals or "",
                "location": site_data.location or "",
                "live_url": site_data.live_url or "",
                "repo_name": site_data.repo_name or "",
                "brand_colors": site_data.brand_colors or "",
                "tagline": site_data.tagline or "",
                "status": site_data.status or "complete",
            })
            # Also sync to builds/ node for admin dashboard Firebase fallback
            sync_build_to_firebase({
                "short_id": sid,
                "client_name": site_data.client_name,
                "niche": site_data.niche or "",
                "email": site_data.email or "",
                "status": site_data.status or "complete",
                "created_at": "",
                "started_at": "",
                "finished_at": "",
                "live_url": site_data.live_url or "",
                "repo_full": "",
                "protected": True,
            })

    created_names = [c["client_name"] for c in created]
    logger.info(f"✅ Portfolio seeded: {len(created_names)} created, {len(skipped)} skipped")
    return {
        "created": created_names,
        "skipped": skipped,
        "total_created": len(created_names),
        "total_skipped": len(skipped),
    }
