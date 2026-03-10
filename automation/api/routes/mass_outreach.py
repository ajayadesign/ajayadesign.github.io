"""
Mass Outreach Routes — SMTP Provider Pool, Excel Import, Email Verification.

Extends the outreach system with:
- Multi-SMTP provider management (CRUD + test + pool status)
- Excel file import (contractor registry → prospects)
- Batch email verification
"""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.models.smtp_provider import SmtpProvider
from api.models.prospect import Prospect

logger = logging.getLogger(__name__)

mass_router = APIRouter(prefix="/outreach/mass", tags=["mass-outreach"])


# ═══════════════════════════════════════════════════════════════════
# SMTP PROVIDERS
# ═══════════════════════════════════════════════════════════════════

class ProviderCreate(BaseModel):
    name: str
    host: str
    port: int = 587
    username: str
    password: str
    use_tls: bool = True
    from_email: str | None = None
    from_name: str | None = None
    daily_limit: int = 100
    priority: int = 0


class ProviderUpdate(BaseModel):
    name: str | None = None
    host: str | None = None
    port: int | None = None
    username: str | None = None
    password: str | None = None
    use_tls: bool | None = None
    from_email: str | None = None
    from_name: str | None = None
    daily_limit: int | None = None
    enabled: bool | None = None
    priority: int | None = None


@mass_router.get("/providers")
async def list_providers(db: AsyncSession = Depends(get_db)):
    """List all SMTP providers with quota status."""
    result = await db.execute(
        select(SmtpProvider).order_by(SmtpProvider.priority.desc())
    )
    providers = result.scalars().all()
    return {"providers": [p.to_dict() for p in providers]}


@mass_router.post("/providers")
async def create_provider(body: ProviderCreate, db: AsyncSession = Depends(get_db)):
    """Add a new SMTP provider to the pool."""
    # Check duplicate name
    existing = await db.execute(
        select(SmtpProvider).where(SmtpProvider.name == body.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, f"Provider '{body.name}' already exists")

    provider = SmtpProvider(
        id=uuid.uuid4(),
        name=body.name,
        host=body.host,
        port=body.port,
        username=body.username,
        password=body.password,
        use_tls=body.use_tls,
        from_email=body.from_email,
        from_name=body.from_name,
        daily_limit=body.daily_limit,
        priority=body.priority,
    )
    db.add(provider)
    await db.commit()
    await db.refresh(provider)
    logger.info("Created SMTP provider: %s (%s:%d)", body.name, body.host, body.port)
    return provider.to_dict()


@mass_router.patch("/providers/{provider_id}")
async def update_provider(provider_id: str, body: ProviderUpdate, db: AsyncSession = Depends(get_db)):
    """Update an SMTP provider."""
    provider = await db.get(SmtpProvider, provider_id)
    if not provider:
        raise HTTPException(404, "Provider not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(provider, field, value)

    await db.commit()
    await db.refresh(provider)
    return provider.to_dict()


@mass_router.delete("/providers/{provider_id}")
async def delete_provider(provider_id: str, db: AsyncSession = Depends(get_db)):
    """Delete an SMTP provider."""
    provider = await db.get(SmtpProvider, provider_id)
    if not provider:
        raise HTTPException(404, "Provider not found")

    await db.delete(provider)
    await db.commit()
    return {"deleted": True, "name": provider.name}


@mass_router.post("/providers/{provider_id}/test")
async def test_provider_connection(provider_id: str):
    """Send a test email through the provider to verify credentials."""
    from api.services.smtp_pool import test_provider
    result = await test_provider(provider_id)
    return result


@mass_router.get("/providers/pool-status")
async def get_pool_status():
    """Get aggregated pool capacity and per-provider usage."""
    from api.services.smtp_pool import get_pool_status
    return await get_pool_status()


# ═══════════════════════════════════════════════════════════════════
# EXCEL IMPORT
# ═══════════════════════════════════════════════════════════════════

@mass_router.post("/import/preview")
async def preview_import(file: UploadFile = File(...)):
    """Parse Excel file and return preview without importing."""
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(400, "File must be .xlsx or .xls")

    content = await file.read()
    if len(content) > 50 * 1024 * 1024:  # 50 MB max
        raise HTTPException(400, "File too large (max 50 MB)")

    from api.services.contractor_import import parse_contractors_excel
    result = parse_contractors_excel(content)

    # Return preview (first 20 rows) + stats
    return {
        "filename": file.filename,
        "total_rows": result["total"],
        "with_email": result["with_email"],
        "skipped_no_email": result["skipped_no_email"],
        "duplicates_in_file": result["duplicates"],
        "registration_types": result["registration_types"],
        "preview": result["rows"][:20],
        "errors": result["errors"],
    }


@mass_router.post("/import/execute")
async def execute_import(file: UploadFile = File(...)):
    """Parse Excel file and import as prospects."""
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(400, "File must be .xlsx or .xls")

    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 50 MB)")

    from api.services.contractor_import import parse_contractors_excel, import_prospects

    parsed = parse_contractors_excel(content)
    if not parsed["rows"]:
        raise HTTPException(400, "No valid rows with email addresses found")

    result = await import_prospects(parsed["rows"])

    logger.info("Import executed: %d created, %d skipped", result["created"], result["skipped_existing"])
    return {
        "filename": file.filename,
        "parsed_total": parsed["total"],
        "parsed_with_email": parsed["with_email"],
        "duplicates_in_file": parsed["duplicates"],
        "created": result["created"],
        "skipped_existing": result["skipped_existing"],
        "errors": result["errors"],
        "registration_types": parsed["registration_types"],
    }


@mass_router.get("/import/stats")
async def import_stats(db: AsyncSession = Depends(get_db)):
    """Get stats on imported prospects."""
    # Count by status
    result = await db.execute(
        select(Prospect.status, func.count(Prospect.id))
        .where(Prospect.source == "contractor_registry")
        .group_by(Prospect.status)
    )
    status_counts = {row[0]: row[1] for row in result.all()}

    # Count verified/unverified
    result = await db.execute(
        select(Prospect.email_verified, func.count(Prospect.id))
        .where(Prospect.source == "contractor_registry")
        .group_by(Prospect.email_verified)
    )
    verify_counts = {str(row[0]): row[1] for row in result.all()}

    # Count by registration type
    result = await db.execute(
        select(func.count(Prospect.id))
        .where(Prospect.source == "contractor_registry")
    )
    total = result.scalar() or 0

    return {
        "total": total,
        "by_status": status_counts,
        "by_verified": verify_counts,
    }


# ═══════════════════════════════════════════════════════════════════
# EMAIL VERIFICATION
# ═══════════════════════════════════════════════════════════════════

@mass_router.post("/verify/batch")
async def verify_batch(limit: int = 50):
    """Verify a batch of unverified prospect emails (MX + SMTP probe)."""
    from api.services.email_verify import batch_verify
    result = await batch_verify(limit=limit)
    return result


@mass_router.post("/verify/single")
async def verify_single(email: str):
    """Verify a single email address."""
    from api.services.email_verify import verify_email_address
    return verify_email_address(email)


# ═══════════════════════════════════════════════════════════════════
# SENDING (via SMTP Pool)
# ═══════════════════════════════════════════════════════════════════

@mass_router.post("/send-test")
async def send_test_via_pool(to: str, subject: str = "Test Email", body: str = "<p>Test from SMTP pool</p>"):
    """Send a test email through the SMTP pool (for debugging)."""
    from api.services.smtp_pool import send_via_pool
    return await send_via_pool(to=to, subject=subject, body_html=body)


@mass_router.get("/dashboard")
async def mass_dashboard(db: AsyncSession = Depends(get_db)):
    """Combined dashboard data — pool status + import stats + send stats."""
    from api.services.smtp_pool import get_pool_status
    from api.models.prospect import OutreachEmail

    pool = await get_pool_status()

    # Today's send stats
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    result = await db.execute(
        select(OutreachEmail.status, func.count(OutreachEmail.id))
        .where(OutreachEmail.sent_at >= today_start)
        .group_by(OutreachEmail.status)
    )
    today_sends = {row[0]: row[1] for row in result.all()}

    # Imported prospect counts
    result = await db.execute(
        select(Prospect.status, func.count(Prospect.id))
        .where(Prospect.source == "contractor_registry")
        .group_by(Prospect.status)
    )
    import_counts = {row[0]: row[1] for row in result.all()}

    # Total prospects with verified email
    result = await db.execute(
        select(func.count(Prospect.id))
        .where(Prospect.email_verified == True)  # noqa: E712
    )
    total_verified = result.scalar() or 0

    return {
        "pool": pool,
        "today_sends": today_sends,
        "import_counts": import_counts,
        "total_verified_emails": total_verified,
    }


# ═══════════════════════════════════════════════════════════════════
# BATCH ACTIVATE — move imported → queued (enqueue into cadence)
# ═══════════════════════════════════════════════════════════════════

class ActivateRequest(BaseModel):
    limit: int = 200
    business_types: list[str] | None = None
    only_verified: bool = False


@mass_router.post("/activate")
async def activate_imported_prospects(body: ActivateRequest, db: AsyncSession = Depends(get_db)):
    """
    Move imported prospects into the outreach pipeline.

    For each prospect:
    1. Status → 'enriched' (so cadence engine's enqueue picks them up)
    2. Calls enqueue_prospect() → creates step-1 email as pending_approval
    3. Status ends at 'queued' with a draft email waiting for approval

    Uses contractor-specific templates (3-touch drip) automatically
    because source='contractor_registry' is detected by compose_email().
    """
    from api.services.cadence_engine import enqueue_prospect

    # ── Phase 1: Collect IDs and batch-update status ──────────
    query = (
        select(Prospect.id)
        .where(
            Prospect.status == "imported",
            Prospect.owner_email.isnot(None),
        )
        .order_by(Prospect.created_at)
        .limit(body.limit)
    )

    if body.only_verified:
        query = query.where(Prospect.email_verified == True)  # noqa: E712

    if body.business_types:
        query = query.where(Prospect.business_type.in_(body.business_types))

    result = await db.execute(query)
    prospect_ids = [str(row[0]) for row in result.all()]

    if not prospect_ids:
        return {"activated": 0, "skipped": 0, "errors": 0, "total": 0}

    # Batch update all to 'enriched' in one shot
    from sqlalchemy import update
    await db.execute(
        update(Prospect)
        .where(Prospect.id.in_([uuid.UUID(pid) for pid in prospect_ids]))
        .values(status="enriched")
    )
    await db.commit()
    # Release the route's DB connection so enqueue_prospect() can use the pool
    await db.close()

    # ── Phase 2: Enqueue each prospect (uses its own session) ─
    stats = {"activated": 0, "skipped": 0, "errors": 0, "total": len(prospect_ids)}

    for pid in prospect_ids:
        try:
            email_id = await enqueue_prospect(pid)
            if email_id:
                stats["activated"] += 1
            else:
                stats["skipped"] += 1
        except Exception as e:
            stats["errors"] += 1
            logger.warning("Failed to activate %s: %s", pid, e)

    logger.info("Batch activate: %d activated, %d skipped, %d errors out of %d",
                stats["activated"], stats["skipped"], stats["errors"], stats["total"])
    return stats


@mass_router.get("/activate/preview")
async def preview_activation(
    limit: int = 200,
    business_types: str | None = None,
    only_verified: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """Preview how many prospects would be activated."""
    query = select(func.count(Prospect.id)).where(
        Prospect.status == "imported",
        Prospect.owner_email.isnot(None),
    )
    if only_verified:
        query = query.where(Prospect.email_verified == True)  # noqa: E712
    if business_types:
        types = [t.strip() for t in business_types.split(",")]
        query = query.where(Prospect.business_type.in_(types))

    result = await db.execute(query)
    total_eligible = result.scalar() or 0

    # Breakdown by business_type
    result = await db.execute(
        select(Prospect.business_type, func.count(Prospect.id))
        .where(
            Prospect.status == "imported",
            Prospect.owner_email.isnot(None),
        )
        .group_by(Prospect.business_type)
        .order_by(func.count(Prospect.id).desc())
    )
    by_type = {row[0]: row[1] for row in result.all()}

    return {
        "total_eligible": total_eligible,
        "will_activate": min(limit, total_eligible),
        "by_type": by_type,
    }
