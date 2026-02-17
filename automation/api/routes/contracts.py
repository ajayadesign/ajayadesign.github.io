"""
AjayaDesign Automation — Contract & Invoice API routes.
"""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, func as sqlfunc
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.models.contract import Contract, Invoice
from api.schemas.contract import (
    ContractCreateRequest, ContractUpdateRequest, ContractResponse,
    ContractListResponse, ContractSignRequest,
    InvoiceCreateRequest, InvoiceUpdateRequest, InvoiceResponse,
    InvoiceListResponse,
    SendEmailRequest, SendEmailResponse,
    ClauseItem, InvoiceLineItem,
)
from api.services.email_service import (
    send_email, build_contract_email, build_invoice_email,
    build_signed_notification_email,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/contracts", tags=["contracts"])
invoice_router = APIRouter(prefix="/invoices", tags=["invoices"])
email_router = APIRouter(prefix="/email", tags=["email"])


def _short_id() -> str:
    return uuid.uuid4().hex[:8]


def _contract_to_response(c: Contract) -> dict:
    """Convert a Contract ORM object to a response dict."""
    return {
        "id": str(c.id),
        "short_id": c.short_id,
        "build_id": str(c.build_id) if c.build_id else None,
        "client_name": c.client_name or "",
        "client_email": c.client_email or "",
        "client_address": c.client_address or "",
        "client_phone": c.client_phone or "",
        "project_name": c.project_name or "",
        "project_description": c.project_description or "",
        "total_amount": c.total_amount or 0,
        "deposit_amount": c.deposit_amount or 0,
        "payment_method": c.payment_method or "",
        "payment_terms": c.payment_terms or "",
        "start_date": c.start_date,
        "estimated_completion_date": c.estimated_completion_date,
        "clauses": c.clauses or [],
        "custom_notes": c.custom_notes or "",
        "provider_name": c.provider_name or "AjayaDesign",
        "provider_email": c.provider_email or "",
        "provider_address": c.provider_address or "",
        "status": c.status or "draft",
        "sign_token": str(c.sign_token) if c.sign_token else "",
        "signed_at": c.signed_at,
        "signer_name": c.signer_name,
        "created_at": c.created_at,
        "updated_at": c.updated_at,
        "sent_at": c.sent_at,
        "invoices": [_invoice_to_response(inv) for inv in (c.invoices or [])],
    }


def _invoice_to_response(inv: Invoice) -> dict:
    """Convert an Invoice ORM object to a response dict."""
    return {
        "id": str(inv.id),
        "invoice_number": inv.invoice_number or "",
        "contract_id": str(inv.contract_id) if inv.contract_id else None,
        "build_id": str(inv.build_id) if inv.build_id else None,
        "client_name": inv.client_name or "",
        "client_email": inv.client_email or "",
        "items": inv.items or [],
        "subtotal": inv.subtotal or 0,
        "tax_rate": inv.tax_rate or 0,
        "tax_amount": inv.tax_amount or 0,
        "total_amount": inv.total_amount or 0,
        "amount_paid": inv.amount_paid or 0,
        "payment_method": inv.payment_method or "",
        "payment_status": inv.payment_status or "unpaid",
        "due_date": inv.due_date,
        "paid_at": inv.paid_at,
        "provider_name": inv.provider_name or "AjayaDesign",
        "provider_email": inv.provider_email or "",
        "provider_address": inv.provider_address or "",
        "notes": inv.notes or "",
        "status": inv.status or "draft",
        "created_at": inv.created_at,
        "updated_at": inv.updated_at,
        "sent_at": inv.sent_at,
    }


async def _next_invoice_number(db: AsyncSession) -> str:
    """Generate the next invoice number like INV-001."""
    result = await db.execute(select(sqlfunc.count(Invoice.id)))
    count = result.scalar() or 0
    return f"INV-{count + 1:03d}"


# ═══════════════════════════════════════════════════════
#  Contract CRUD
# ═══════════════════════════════════════════════════════

@router.get("", response_model=ContractListResponse)
async def list_contracts(db: AsyncSession = Depends(get_db)):
    """List all contracts, newest first."""
    result = await db.execute(
        select(Contract).order_by(Contract.created_at.desc())
    )
    contracts = result.scalars().all()
    return {
        "contracts": [_contract_to_response(c) for c in contracts],
        "total": len(contracts),
    }


@router.get("/{short_id}")
async def get_contract(short_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single contract by short_id."""
    result = await db.execute(
        select(Contract).where(Contract.short_id == short_id)
    )
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(404, f"Contract {short_id} not found")
    return _contract_to_response(contract)


@router.post("", status_code=201)
async def create_contract(req: ContractCreateRequest, db: AsyncSession = Depends(get_db)):
    """Create a new contract."""
    contract = Contract(
        short_id=_short_id(),
        build_id=req.build_id or None,
        client_name=req.client_name,
        client_email=req.client_email,
        client_address=req.client_address,
        client_phone=req.client_phone,
        project_name=req.project_name,
        project_description=req.project_description,
        total_amount=req.total_amount,
        deposit_amount=req.deposit_amount,
        payment_method=req.payment_method,
        payment_terms=req.payment_terms,
        start_date=req.start_date,
        estimated_completion_date=req.estimated_completion_date,
        clauses=[c.model_dump() for c in req.clauses],
        custom_notes=req.custom_notes,
        status="draft",
    )
    db.add(contract)
    await db.commit()
    await db.refresh(contract)
    logger.info(f"✅ Contract created: {contract.short_id} for {contract.client_name}")
    return _contract_to_response(contract)


@router.patch("/{short_id}")
async def update_contract(
    short_id: str,
    req: ContractUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update a contract."""
    result = await db.execute(
        select(Contract).where(Contract.short_id == short_id)
    )
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(404, f"Contract {short_id} not found")

    update_data = req.model_dump(exclude_unset=True)
    if "clauses" in update_data and update_data["clauses"] is not None:
        update_data["clauses"] = [
            c.model_dump() if hasattr(c, "model_dump") else c
            for c in update_data["clauses"]
        ]

    for key, value in update_data.items():
        setattr(contract, key, value)

    await db.commit()
    await db.refresh(contract)
    return _contract_to_response(contract)


@router.delete("/{short_id}", status_code=204)
async def delete_contract(short_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a contract."""
    result = await db.execute(
        select(Contract).where(Contract.short_id == short_id)
    )
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(404, f"Contract {short_id} not found")
    await db.delete(contract)
    await db.commit()


# ── Signing ─────────────────────────────────────────────

@router.get("/sign/{sign_token}")
async def get_contract_for_signing(sign_token: str, db: AsyncSession = Depends(get_db)):
    """Public endpoint: get contract details for the signing page."""
    if not sign_token:
        raise HTTPException(400, "Invalid signing token")

    result = await db.execute(
        select(Contract).where(Contract.sign_token == sign_token)
    )
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(404, "Contract not found or link expired")

    # Return a limited view (no internal details)
    return {
        "short_id": contract.short_id,
        "client_name": contract.client_name,
        "project_name": contract.project_name,
        "project_description": contract.project_description,
        "total_amount": float(contract.total_amount or 0),
        "deposit_amount": float(contract.deposit_amount or 0),
        "payment_method": contract.payment_method,
        "payment_terms": contract.payment_terms,
        "start_date": str(contract.start_date) if contract.start_date else None,
        "estimated_completion_date": str(contract.estimated_completion_date) if contract.estimated_completion_date else None,
        "clauses": [c for c in (contract.clauses or []) if c.get("enabled", True)],
        "custom_notes": contract.custom_notes,
        "provider_name": contract.provider_name,
        "provider_email": contract.provider_email,
        "provider_address": contract.provider_address,
        "status": contract.status,
        "signed_at": contract.signed_at,
        "signer_name": contract.signer_name,
    }


@router.post("/sign/{sign_token}")
async def sign_contract(
    sign_token: str,
    req: ContractSignRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Public endpoint: sign a contract."""
    if not sign_token:
        raise HTTPException(400, "Invalid signing token")

    result = await db.execute(
        select(Contract).where(Contract.sign_token == sign_token)
    )
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(404, "Contract not found or link expired")

    if contract.signed_at:
        raise HTTPException(400, "Contract has already been signed")

    # Record signature
    now = datetime.now(timezone.utc)
    contract.signed_at = now
    contract.signature_data = req.signature_data
    contract.signer_name = req.signer_name
    contract.signer_ip = request.client.host if request.client else "unknown"
    contract.status = "signed"

    await db.commit()
    await db.refresh(contract)

    logger.info(f"✅ Contract {contract.short_id} signed by {req.signer_name}")

    # Send notification to admin
    try:
        subject, html = build_signed_notification_email(
            contract.short_id,
            contract.client_name,
            contract.project_name,
            now.strftime("%B %d, %Y at %I:%M %p UTC"),
        )
        await send_email(
            to=contract.provider_email or "ajayadesign@gmail.com",
            subject=subject,
            body_html=html,
        )
    except Exception as e:
        logger.warning(f"Failed to send signing notification: {e}")

    return {"success": True, "message": "Contract signed successfully", "signed_at": now.isoformat()}


@router.post("/{short_id}/send")
async def send_contract(short_id: str, db: AsyncSession = Depends(get_db)):
    """Send contract to client for signing via email."""
    result = await db.execute(
        select(Contract).where(Contract.short_id == short_id)
    )
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(404, f"Contract {short_id} not found")

    # Build the signing URL
    sign_url = f"https://ajayadesign.github.io/admin/sign.html?token={contract.sign_token}"

    subject, html = build_contract_email(
        client_name=contract.client_name,
        project_name=contract.project_name,
        sign_url=sign_url,
        provider_name=contract.provider_name or "AjayaDesign",
    )

    result_email = await send_email(
        to=contract.client_email,
        subject=subject,
        body_html=html,
    )

    if result_email["success"]:
        contract.status = "sent"
        contract.sent_at = datetime.now(timezone.utc)
        await db.commit()

    return result_email


# ═══════════════════════════════════════════════════════
#  Invoice CRUD
# ═══════════════════════════════════════════════════════

@invoice_router.get("", response_model=InvoiceListResponse)
async def list_invoices(db: AsyncSession = Depends(get_db)):
    """List all invoices, newest first."""
    result = await db.execute(
        select(Invoice).order_by(Invoice.created_at.desc())
    )
    invoices = result.scalars().all()
    return {
        "invoices": [_invoice_to_response(inv) for inv in invoices],
        "total": len(invoices),
    }


@invoice_router.get("/{invoice_number}")
async def get_invoice(invoice_number: str, db: AsyncSession = Depends(get_db)):
    """Get a single invoice by invoice_number."""
    result = await db.execute(
        select(Invoice).where(Invoice.invoice_number == invoice_number)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(404, f"Invoice {invoice_number} not found")
    return _invoice_to_response(invoice)


@invoice_router.post("", status_code=201)
async def create_invoice(req: InvoiceCreateRequest, db: AsyncSession = Depends(get_db)):
    """Create a new invoice."""
    inv_number = await _next_invoice_number(db)

    invoice = Invoice(
        invoice_number=inv_number,
        contract_id=req.contract_id or None,
        build_id=req.build_id or None,
        client_name=req.client_name,
        client_email=req.client_email,
        items=[item.model_dump() for item in req.items],
        subtotal=req.subtotal,
        tax_rate=req.tax_rate,
        tax_amount=req.tax_amount,
        total_amount=req.total_amount,
        amount_paid=req.amount_paid,
        payment_method=req.payment_method,
        payment_status=req.payment_status,
        due_date=req.due_date,
        notes=req.notes,
        status="draft",
    )
    db.add(invoice)
    await db.commit()
    await db.refresh(invoice)
    logger.info(f"✅ Invoice created: {invoice.invoice_number} for {invoice.client_name}")
    return _invoice_to_response(invoice)


@invoice_router.patch("/{invoice_number}")
async def update_invoice(
    invoice_number: str,
    req: InvoiceUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update an invoice."""
    result = await db.execute(
        select(Invoice).where(Invoice.invoice_number == invoice_number)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(404, f"Invoice {invoice_number} not found")

    update_data = req.model_dump(exclude_unset=True)
    if "items" in update_data and update_data["items"] is not None:
        update_data["items"] = [
            item.model_dump() if hasattr(item, "model_dump") else item
            for item in update_data["items"]
        ]

    for key, value in update_data.items():
        setattr(invoice, key, value)

    await db.commit()
    await db.refresh(invoice)
    return _invoice_to_response(invoice)


@invoice_router.delete("/{invoice_number}", status_code=204)
async def delete_invoice(invoice_number: str, db: AsyncSession = Depends(get_db)):
    """Delete an invoice."""
    result = await db.execute(
        select(Invoice).where(Invoice.invoice_number == invoice_number)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(404, f"Invoice {invoice_number} not found")
    await db.delete(invoice)
    await db.commit()


@invoice_router.post("/{invoice_number}/send")
async def send_invoice(invoice_number: str, db: AsyncSession = Depends(get_db)):
    """Send an invoice to the client via email."""
    result = await db.execute(
        select(Invoice).where(Invoice.invoice_number == invoice_number)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(404, f"Invoice {invoice_number} not found")

    # Build items HTML table
    items = invoice.items or []
    items_rows = "".join(
        f'<tr><td style="padding:8px;border-bottom:1px solid #e5e7eb">{item.get("description","")}</td>'
        f'<td style="padding:8px;border-bottom:1px solid #e5e7eb;text-align:center">{item.get("quantity",1)}</td>'
        f'<td style="padding:8px;border-bottom:1px solid #e5e7eb;text-align:right">${item.get("unit_price",0):.2f}</td>'
        f'<td style="padding:8px;border-bottom:1px solid #e5e7eb;text-align:right">${item.get("amount",0):.2f}</td></tr>'
        for item in items
    )
    items_html = f"""
    <table style="width:100%;border-collapse:collapse;margin-top:16px;">
      <thead>
        <tr style="background:#f3f4f6">
          <th style="padding:8px;text-align:left;font-size:12px;color:#6b7280">Description</th>
          <th style="padding:8px;text-align:center;font-size:12px;color:#6b7280">Qty</th>
          <th style="padding:8px;text-align:right;font-size:12px;color:#6b7280">Unit Price</th>
          <th style="padding:8px;text-align:right;font-size:12px;color:#6b7280">Amount</th>
        </tr>
      </thead>
      <tbody>{items_rows}</tbody>
    </table>
    """

    subject, html = build_invoice_email(
        client_name=invoice.client_name,
        invoice_number=invoice.invoice_number,
        total_amount=f"{float(invoice.total_amount or 0):.2f}",
        due_date=str(invoice.due_date) if invoice.due_date else "Upon receipt",
        payment_method=invoice.payment_method or "",
        items_html=items_html,
    )

    result_email = await send_email(
        to=invoice.client_email,
        subject=subject,
        body_html=html,
    )

    if result_email["success"]:
        invoice.status = "sent"
        invoice.sent_at = datetime.now(timezone.utc)
        await db.commit()

    return result_email


@invoice_router.post("/{invoice_number}/mark-paid")
async def mark_invoice_paid(invoice_number: str, db: AsyncSession = Depends(get_db)):
    """Mark an invoice as fully paid."""
    result = await db.execute(
        select(Invoice).where(Invoice.invoice_number == invoice_number)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(404, f"Invoice {invoice_number} not found")

    invoice.payment_status = "paid"
    invoice.amount_paid = invoice.total_amount
    invoice.paid_at = datetime.now(timezone.utc)
    invoice.status = "paid"
    await db.commit()
    await db.refresh(invoice)
    return _invoice_to_response(invoice)


# ═══════════════════════════════════════════════════════
#  Email (generic send)
# ═══════════════════════════════════════════════════════

@email_router.post("/send", response_model=SendEmailResponse)
async def send_generic_email(req: SendEmailRequest):
    """Send a generic email."""
    result = await send_email(
        to=req.to,
        subject=req.subject,
        body_html=req.body_html,
    )
    return result
