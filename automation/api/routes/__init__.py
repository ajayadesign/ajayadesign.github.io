"""
API Routes — Build CRUD, SSE streaming, health.
"""

import asyncio
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from api.database import get_db
from api.models.build import Build, BuildLog
from api.schemas import (
    BuildRequest,
    BuildResponse,
    BuildListResponse,
    BuildDetailResponse,
    PhaseDetail,
    LogEntry,
    HealthResponse,
    ParseClientRequest,
    ParseClientResponse,
    ParsedClientFields,
)
from api.pipeline.orchestrator import BuildOrchestrator

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory SSE event queues per build
_event_queues: dict[str, asyncio.Queue] = {}


# ── Health ──────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse, tags=["system"])
async def health():
    return HealthResponse(
        status="ok",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version="2.0.0-python",
    )


# ── Create Build ────────────────────────────────────────

@router.post("/builds", response_model=BuildResponse, status_code=201, tags=["builds"])
async def create_build(
    req: BuildRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db),
):
    short_id = uuid.uuid4().hex[:8]

    build = Build(
        short_id=short_id,
        client_name=req.business_name,
        niche=req.niche,
        goals=req.goals,
        email=req.email,
        firebase_id=req.firebase_id,
        source=req.source,
        phone=req.phone,
        location=req.location,
        existing_website=req.existing_website,
        brand_colors=req.brand_colors,
        tagline=req.tagline,
        target_audience=req.target_audience,
        competitor_urls=req.competitor_urls,
        additional_notes=req.additional_notes,
        rebuild=req.rebuild,
        status="queued",
    )
    session.add(build)
    await session.commit()
    await session.refresh(build)

    # Create SSE queue for this build
    _event_queues[short_id] = asyncio.Queue()

    # Launch pipeline in background
    background_tasks.add_task(_run_pipeline, build.id, short_id)

    return BuildResponse(
        id=build.id,
        short_id=short_id,
        status="queued",
        client_name=req.business_name,
        niche=req.niche,
        message=f"Build {short_id} queued. Stream at /api/v1/builds/{short_id}/stream",
    )


async def _run_pipeline(build_id: int, short_id: str):
    """Background task: run the full pipeline."""
    from api.database import async_session

    async with async_session() as session:
        stmt = select(Build).where(Build.id == build_id).options(
            selectinload(Build.phases),
            selectinload(Build.logs),
            selectinload(Build.pages),
        )
        result = await session.execute(stmt)
        build = result.scalar_one()

        queue = _event_queues.get(short_id)

        def event_callback(event_type: str, data: dict):
            if queue:
                try:
                    queue.put_nowait({"type": event_type, **data})
                except asyncio.QueueFull:
                    pass

        orchestrator = BuildOrchestrator(build, session, event_callback)
        try:
            await orchestrator.run()
        except Exception as exc:
            logger.error("Pipeline failed for %s: %s", short_id, exc)
        finally:
            if queue:
                await queue.put(None)  # Signal end of stream


# ── List Builds ─────────────────────────────────────────

@router.get("/builds", response_model=BuildListResponse, tags=["builds"])
async def list_builds(
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
):
    stmt = select(Build).order_by(Build.created_at.desc()).limit(limit).offset(offset)
    if status:
        stmt = stmt.where(Build.status == status)

    result = await session.execute(stmt)
    builds = result.scalars().all()

    return BuildListResponse(
        builds=[
            BuildResponse(
                id=b.id,
                short_id=b.short_id,
                status=b.status,
                client_name=b.client_name,
                niche=b.niche,
                message=f"{b.client_name} ({b.niche})",
            )
            for b in builds
        ],
        total=len(builds),
    )


# ── Get Build Detail ────────────────────────────────────

@router.get("/builds/{short_id}", response_model=BuildDetailResponse, tags=["builds"])
async def get_build(
    short_id: str,
    session: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Build)
        .where(Build.short_id == short_id)
        .options(
            selectinload(Build.phases),
            selectinload(Build.pages),
        )
    )
    result = await session.execute(stmt)
    build = result.scalar_one_or_none()

    if not build:
        raise HTTPException(status_code=404, detail=f"Build {short_id} not found")

    return BuildDetailResponse(
        id=build.id,
        short_id=build.short_id,
        client_name=build.client_name,
        niche=build.niche,
        goals=build.goals,
        email=build.email,
        status=build.status,
        repo_name=build.repo_name,
        repo_full=build.repo_full,
        live_url=build.live_url,
        pages_count=build.pages_count or 0,
        blueprint=build.blueprint,
        design_system=build.design_system,
        phases=[
            PhaseDetail(
                phase_number=p.phase_number,
                phase_name=p.phase_name,
                status=p.status,
                started_at=p.started_at.isoformat() if p.started_at else None,
                finished_at=p.finished_at.isoformat() if p.finished_at else None,
            )
            for p in sorted(build.phases, key=lambda x: x.phase_number)
        ],
        created_at=build.created_at.isoformat() if build.created_at else None,
        started_at=build.started_at.isoformat() if build.started_at else None,
        finished_at=build.finished_at.isoformat() if build.finished_at else None,
    )


# ── Build Logs ──────────────────────────────────────────

@router.get("/builds/{short_id}/logs", response_model=list[LogEntry], tags=["builds"])
async def get_build_logs(
    short_id: str,
    session: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Build)
        .where(Build.short_id == short_id)
        .options(selectinload(Build.logs))
    )
    result = await session.execute(stmt)
    build = result.scalar_one_or_none()

    if not build:
        raise HTTPException(status_code=404, detail=f"Build {short_id} not found")

    return [
        LogEntry(
            sequence=log.sequence,
            level=log.level,
            category=log.category,
            message=log.message,
            created_at=log.created_at,
        )
        for log in sorted(build.logs, key=lambda x: x.sequence)
    ]


# ── SSE Stream ──────────────────────────────────────────

@router.get("/builds/{short_id}/stream", tags=["builds"])
async def stream_build(short_id: str):
    """Server-Sent Events stream for a running build."""
    queue = _event_queues.get(short_id)

    if not queue:
        raise HTTPException(status_code=404, detail=f"No active build stream for {short_id}")

    async def event_generator():
        try:
            while True:
                event = await asyncio.wait_for(queue.get(), timeout=300)
                if event is None:
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"
                    break
                yield f"data: {json.dumps(event)}\n\n"
        except asyncio.TimeoutError:
            yield f"data: {json.dumps({'type': 'timeout'})}\n\n"
        finally:
            _event_queues.pop(short_id, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Parse Client (AI text extraction) ──────────────────

@router.post("/parse-client", response_model=ParseClientResponse, tags=["tools"])
async def parse_client(req: ParseClientRequest):
    """Extract structured client fields from raw unstructured text using AI."""
    from api.services.ai import call_ai, extract_json
    from api.pipeline.prompts import PARSE_CLIENT_SYSTEM, parse_client_text

    try:
        raw_response = await call_ai(
            system=PARSE_CLIENT_SYSTEM,
            user=parse_client_text(req.raw_text),
        )
        parsed_data = extract_json(raw_response)
    except Exception as exc:
        logger.error("AI parse-client failed: %s", exc)
        raise HTTPException(status_code=502, detail="AI extraction failed — try again or fill manually")

    confidence = parsed_data.pop("confidence", "medium")
    # Validate confidence value
    if confidence not in ("high", "medium", "low"):
        confidence = "medium"

    return ParseClientResponse(
        parsed=ParsedClientFields(**{k: v for k, v in parsed_data.items() if v is not None}),
        confidence=confidence,
    )
