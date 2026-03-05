"""
AjayaDesign Automation — Quote API routes.
"""

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.models.quote import Quote
from api.schemas.quote import (
    QuoteCreateRequest, QuoteUpdateRequest, QuoteResponse,
    QuoteListResponse, DeliverableItem,
)
from api.services.email_service import send_email, build_quote_email
from api.services.firebase import (
    sync_quote_to_firebase, delete_quote_from_firebase,
    publish_quote_for_viewing,
)
from api.routes.activity import log_activity

logger = logging.getLogger(__name__)
quote_router = APIRouter(prefix="/quotes", tags=["quotes"])


def _short_id() -> str:
    return uuid.uuid4().hex[:8]


def _quote_to_response(q: Quote) -> dict:
    """Convert Quote ORM object to response dict."""
    return {
        "id": q.id,
        "short_id": q.short_id,
        "build_id": q.build_id,
        "client_name": q.client_name,
        "client_email": q.client_email,
        "project_name": q.project_name,
        "project_description": q.project_description or "",
        "deliverables": q.deliverables or [],
        "subtotal": q.subtotal or 0,
        "tax_rate": q.tax_rate or 0,
        "tax_amount": q.tax_amount or 0,
        "total_amount": q.total_amount or 0,
        "payment_schedule": q.payment_schedule or "",
        "valid_days": q.valid_days or 30,
        "custom_notes": q.custom_notes or "",
        "revision": q.revision or 1,
        "provider_name": q.provider_name or "AjayaDesign",
        "provider_email": q.provider_email or "ajayadesign@gmail.com",
        "status": q.status or "draft",
        "view_token": q.view_token or "",
        "approved_at": q.approved_at.isoformat() if q.approved_at else None,
        "signer_name": q.signer_name,
        "created_at": q.created_at.isoformat() if q.created_at else None,
        "updated_at": q.updated_at.isoformat() if q.updated_at else None,
        "sent_at": q.sent_at.isoformat() if q.sent_at else None,
    }


def _sync_quote_fb(q: Quote) -> None:
    """Fire-and-forget sync of quote state to Firebase."""
    try:
        sync_quote_to_firebase({
            "short_id": q.short_id,
            "client_name": q.client_name,
            "client_email": q.client_email,
            "project_name": q.project_name,
            "project_description": q.project_description or "",
            "deliverables": q.deliverables or [],
            "subtotal": float(q.subtotal or 0),
            "tax_rate": float(q.tax_rate or 0),
            "tax_amount": float(q.tax_amount or 0),
            "total_amount": float(q.total_amount or 0),
            "payment_schedule": q.payment_schedule or "",
            "valid_days": q.valid_days or 30,
            "custom_notes": q.custom_notes or "",
            "revision": q.revision or 1,
            "status": q.status or "draft",
            "view_token": q.view_token,
            "sent_at": q.sent_at.isoformat() if q.sent_at else None,
            "approved_at": q.approved_at.isoformat() if q.approved_at else None,
            "signer_name": q.signer_name,
        })
    except Exception as e:
        logger.warning(f"Quote Firebase sync failed: {e}")


# ═══════════════════════════════════════════════════════
#  Quote CRUD
# ═══════════════════════════════════════════════════════

@quote_router.get("", response_model=QuoteListResponse)
async def list_quotes(db: AsyncSession = Depends(get_db)):
    """List all quotes, newest first."""
    result = await db.execute(
        select(Quote).order_by(Quote.created_at.desc())
    )
    quotes = result.scalars().all()
    return {
        "quotes": [_quote_to_response(q) for q in quotes],
        "total": len(quotes),
    }


@quote_router.get("/{short_id}")
async def get_quote(short_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single quote by short_id."""
    result = await db.execute(
        select(Quote).where(Quote.short_id == short_id)
    )
    quote = result.scalar_one_or_none()
    if not quote:
        raise HTTPException(404, f"Quote {short_id} not found")
    return _quote_to_response(quote)


@quote_router.post("", status_code=201)
async def create_quote(req: QuoteCreateRequest, db: AsyncSession = Depends(get_db)):
    """Create a new quote."""
    quote = Quote(
        short_id=_short_id(),
        build_id=req.build_id,
        client_name=req.client_name,
        client_email=req.client_email,
        project_name=req.project_name,
        project_description=req.project_description,
        deliverables=[{k: float(v) if isinstance(v, Decimal) else v for k, v in d.model_dump().items()} for d in req.deliverables] if req.deliverables else [],
        subtotal=req.subtotal,
        tax_rate=req.tax_rate,
        tax_amount=req.tax_amount,
        total_amount=req.total_amount,
        payment_schedule=req.payment_schedule,
        valid_days=req.valid_days,
        custom_notes=req.custom_notes,
        revision=req.revision,
    )
    db.add(quote)
    await db.commit()
    await db.refresh(quote)
    _sync_quote_fb(quote)

    await log_activity(
        entity_type="quote", entity_id=quote.short_id,
        action="created", icon="📋",
        description=f"Quote created for {quote.client_name}",
        metadata={"project_name": quote.project_name, "total": float(quote.total_amount or 0)},
    )

    return _quote_to_response(quote)


@quote_router.patch("/{short_id}")
async def update_quote(short_id: str, req: QuoteUpdateRequest, db: AsyncSession = Depends(get_db)):
    """Update a quote."""
    result = await db.execute(
        select(Quote).where(Quote.short_id == short_id)
    )
    quote = result.scalar_one_or_none()
    if not quote:
        raise HTTPException(404, f"Quote {short_id} not found")

    update_data = req.model_dump(exclude_unset=True)
    if "deliverables" in update_data and update_data["deliverables"] is not None:
        update_data["deliverables"] = [
            {k: float(v) if isinstance(v, Decimal) else v for k, v in (d.model_dump() if hasattr(d, "model_dump") else d).items()}
            for d in update_data["deliverables"]
        ]

    for key, val in update_data.items():
        setattr(quote, key, val)

    await db.commit()
    await db.refresh(quote)
    _sync_quote_fb(quote)

    return _quote_to_response(quote)


@quote_router.delete("/{short_id}")
async def delete_quote(short_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a quote."""
    result = await db.execute(
        select(Quote).where(Quote.short_id == short_id)
    )
    quote = result.scalar_one_or_none()
    if not quote:
        raise HTTPException(404, f"Quote {short_id} not found")

    await db.delete(quote)
    await db.commit()
    delete_quote_from_firebase(short_id)

    await log_activity(
        entity_type="quote", entity_id=short_id,
        action="deleted", icon="🗑️",
        description=f"Quote {short_id} deleted",
    )

    return {"success": True, "message": f"Quote {short_id} deleted"}


# ═══════════════════════════════════════════════════════
#  Send Quote
# ═══════════════════════════════════════════════════════

@quote_router.post("/{short_id}/send")
async def send_quote(short_id: str, db: AsyncSession = Depends(get_db)):
    """Send quote to client for review & approval via email."""
    result = await db.execute(
        select(Quote).where(Quote.short_id == short_id)
    )
    quote = result.scalar_one_or_none()
    if not quote:
        raise HTTPException(404, f"Quote {short_id} not found")

    # Build the viewing URL
    view_url = f"https://ajayadesign.github.io/admin/quote.html?token={quote.view_token}"

    subject, html = build_quote_email(
        client_name=quote.client_name,
        project_name=quote.project_name,
        deliverables=quote.deliverables or [],
        total_amount=float(quote.total_amount or 0),
        payment_schedule=quote.payment_schedule or "",
        valid_days=quote.valid_days or 30,
        revision=quote.revision or 1,
        view_url=view_url,
        provider_name=quote.provider_name or "AjayaDesign",
    )

    result_email = await send_email(
        to=quote.client_email,
        subject=subject,
        body_html=html,
    )

    if result_email["success"]:
        quote.status = "sent"
        quote.sent_at = datetime.now(timezone.utc)
        await db.commit()
        _sync_quote_fb(quote)

        await log_activity(
            entity_type="quote", entity_id=quote.short_id,
            action="sent", icon="📧",
            description=f"Quote emailed to {quote.client_email} (rev {quote.revision})",
            metadata={"client_email": quote.client_email, "revision": quote.revision},
        )

        # Publish to Firebase for public viewing
        publish_quote_for_viewing(str(quote.view_token), {
            "short_id": quote.short_id,
            "client_name": quote.client_name,
            "project_name": quote.project_name,
            "project_description": quote.project_description or "",
            "deliverables": quote.deliverables or [],
            "subtotal": float(quote.subtotal or 0),
            "tax_rate": float(quote.tax_rate or 0),
            "tax_amount": float(quote.tax_amount or 0),
            "total_amount": float(quote.total_amount or 0),
            "payment_schedule": quote.payment_schedule or "",
            "valid_days": quote.valid_days or 30,
            "custom_notes": quote.custom_notes or "",
            "revision": quote.revision or 1,
            "provider_name": quote.provider_name or "AjayaDesign",
            "provider_email": quote.provider_email or "ajayadesign@gmail.com",
        })

    return result_email
