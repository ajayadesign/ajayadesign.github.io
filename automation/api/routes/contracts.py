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
    ClauseItem, InvoiceLineItem, PaymentPlanInstallment,
    RecordPaymentRequest,
)
from api.services.email_service import (
    send_email, build_contract_email, build_invoice_email,
    build_signed_notification_email, build_payment_reminder_email,
)
from api.services.notify import send_telegram_contract_signed
from api.services.firebase import (
    sync_contract_to_firebase, delete_contract_from_firebase,
    sync_invoice_to_firebase, delete_invoice_from_firebase,
    publish_contract_for_signing, get_pending_signatures,
    mark_signature_processed,
)
from api.routes.activity import log_activity

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/contracts", tags=["contracts"])
invoice_router = APIRouter(prefix="/invoices", tags=["invoices"])
email_router = APIRouter(prefix="/email", tags=["email"])


def _short_id() -> str:
    return uuid.uuid4().hex[:8]


def _sync_contract_fb(c: Contract) -> None:
    """Fire-and-forget sync of contract state to Firebase."""
    try:
        sync_contract_to_firebase({
            "short_id": c.short_id,
            "client_name": c.client_name,
            "client_email": c.client_email,
            "client_phone": c.client_phone or "",
            "client_address": c.client_address or "",
            "project_name": c.project_name,
            "project_description": c.project_description or "",
            "total_amount": float(c.total_amount or 0),
            "deposit_amount": float(c.deposit_amount or 0),
            "payment_method": c.payment_method or "",
            "payment_terms": c.payment_terms or "",
            "start_date": c.start_date.isoformat() if c.start_date else None,
            "estimated_completion_date": c.estimated_completion_date.isoformat() if c.estimated_completion_date else None,
            "clauses": c.clauses or [],
            "custom_notes": c.custom_notes or "",
            "status": c.status or "draft",
            "signed_at": c.signed_at.isoformat() if c.signed_at else None,
            "signer_name": c.signer_name,
            "signature_data": c.signature_data,
            "signer_ip": c.signer_ip or "",
            "sign_token": c.sign_token or "",
            "sent_at": c.sent_at.isoformat() if c.sent_at else None,
            "build_short_id": "",  # TODO: resolve if needed
        })
    except Exception as e:
        logger.warning(f"Firebase contract sync failed (non-critical): {e}")


def _sync_invoice_fb(inv: Invoice) -> None:
    """Fire-and-forget sync of invoice state to Firebase."""
    try:
        plan = inv.payment_plan or []
        pending_installments = sum(1 for i in plan if i.get("status") in ("pending", "overdue"))
        sync_invoice_to_firebase({
            "invoice_number": inv.invoice_number,
            "client_name": inv.client_name,
            "client_email": inv.client_email,
            "total_amount": float(inv.total_amount or 0),
            "subtotal": float(inv.subtotal or 0),
            "tax_amount": float(inv.tax_amount or 0),
            "amount_paid": float(inv.amount_paid or 0),
            "payment_status": inv.payment_status or "unpaid",
            "payment_method": inv.payment_method or "",
            "status": inv.status or "draft",
            "due_date": str(inv.due_date) if inv.due_date else None,
            "paid_at": inv.paid_at.isoformat() if inv.paid_at else None,
            "contract_short_id": "",
            "items": inv.items or [],
            "items_count": len(inv.items or []),
            "notes": inv.notes or "",
            "payment_plan": plan,
            "payment_plan_enabled": inv.payment_plan_enabled or "false",
            "pending_installments": pending_installments,
        })
    except Exception as e:
        logger.warning(f"Firebase invoice sync failed (non-critical): {e}")


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
        "signature_data": c.signature_data,
        "signer_ip": c.signer_ip,
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
        "payment_plan": inv.payment_plan or [],
        "payment_plan_enabled": inv.payment_plan_enabled or "false",
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
    _sync_contract_fb(contract)
    await log_activity(
        entity_type="contract", entity_id=contract.short_id,
        action="created", icon="📝",
        description=f"Contract created for {contract.client_name} — {contract.project_name}",
        metadata={"client_name": contract.client_name, "project_name": contract.project_name, "total_amount": float(contract.total_amount or 0)},
    )
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
    _sync_contract_fb(contract)
    changed_fields = list(update_data.keys())
    await log_activity(
        entity_type="contract", entity_id=short_id,
        action="updated", icon="✏️",
        description=f"Contract updated — changed: {', '.join(changed_fields)}",
        metadata={"changed_fields": changed_fields},
    )
    return _contract_to_response(contract)


@router.delete("/{short_id}", status_code=204)
async def delete_contract(short_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a contract. Only draft/sent contracts can be deleted."""
    result = await db.execute(
        select(Contract).where(Contract.short_id == short_id)
    )
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(404, f"Contract {short_id} not found")
    if contract.status in ("signed", "executed", "completed"):
        raise HTTPException(
            403,
            f"Cannot delete a {contract.status} contract. Signed/executed contracts are permanent records.",
        )
    client_name = contract.client_name
    await db.delete(contract)
    await db.commit()
    delete_contract_from_firebase(short_id)
    await log_activity(
        entity_type="contract", entity_id=short_id,
        action="deleted", icon="🗑️",
        description=f"Contract for {client_name} deleted",
    )


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
    _sync_contract_fb(contract)
    await log_activity(
        entity_type="contract", entity_id=contract.short_id,
        action="signed", icon="✍️",
        description=f"Contract signed by {req.signer_name}",
        actor=f"client:{req.signer_name}",
        metadata={"signer_name": req.signer_name, "signer_ip": contract.signer_ip},
    )

    # Send notification to admin (email + Telegram)
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
        logger.warning(f"Failed to send signing email notification: {e}")

    try:
        from datetime import timezone, timedelta
        cst = timezone(timedelta(hours=-6))
        now_cst = now.replace(tzinfo=timezone.utc).astimezone(cst)
        await send_telegram_contract_signed(
            contract_id=contract.short_id,
            client_name=contract.client_name,
            project_name=contract.project_name,
            total_amount=float(contract.total_amount or 0),
            signer_name=req.signer_name,
            signed_at=now_cst.strftime("%B %d, %Y at %I:%M %p CST"),
        )
    except Exception as e:
        logger.warning(f"Failed to send signing Telegram notification: {e}")

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
        _sync_contract_fb(contract)
        await log_activity(
            entity_type="contract", entity_id=contract.short_id,
            action="sent", icon="📧",
            description=f"Contract emailed to {contract.client_email}",
            metadata={"client_email": contract.client_email},
        )

        # ── Publish to Firebase for public signing ──
        publish_contract_for_signing(str(contract.sign_token), {
            "short_id": contract.short_id,
            "client_name": contract.client_name,
            "project_name": contract.project_name,
            "project_description": contract.project_description or "",
            "total_amount": float(contract.total_amount or 0),
            "deposit_amount": float(contract.deposit_amount or 0),
            "payment_method": contract.payment_method or "",
            "payment_terms": contract.payment_terms or "",
            "start_date": str(contract.start_date) if contract.start_date else None,
            "estimated_completion_date": str(contract.estimated_completion_date) if contract.estimated_completion_date else None,
            "clauses": [c for c in (contract.clauses or []) if c.get("enabled", True)],
            "custom_notes": contract.custom_notes or "",
            "provider_name": contract.provider_name or "AjayaDesign",
            "provider_email": contract.provider_email or "ajayadesign@gmail.com",
            "provider_address": contract.provider_address or "",
        })

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
        items=[item.model_dump(mode="json") for item in req.items],
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
        payment_plan=[inst.model_dump(mode="json") for inst in req.payment_plan] if req.payment_plan else [],
        payment_plan_enabled=req.payment_plan_enabled,
    )
    db.add(invoice)
    await db.commit()
    await db.refresh(invoice)
    logger.info(f"✅ Invoice created: {invoice.invoice_number} for {invoice.client_name}")
    _sync_invoice_fb(invoice)
    await log_activity(
        entity_type="invoice", entity_id=invoice.invoice_number,
        action="created", icon="💰",
        description=f"Invoice {invoice.invoice_number} created for {invoice.client_name} — ${float(invoice.total_amount or 0):.2f}",
        metadata={"client_name": invoice.client_name, "total_amount": float(invoice.total_amount or 0)},
    )
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
            item.model_dump(mode="json") if hasattr(item, "model_dump") else item
            for item in update_data["items"]
        ]
    if "payment_plan" in update_data and update_data["payment_plan"] is not None:
        # Serialize payment plan entries — convert date/Decimal to str/float
        serialized_plan = []
        for inst in update_data["payment_plan"]:
            if hasattr(inst, "model_dump"):
                serialized_plan.append(inst.model_dump(mode="json"))
            else:
                # Already a dict from model_dump — convert native types
                entry = dict(inst)
                for k, v in entry.items():
                    if hasattr(v, 'isoformat'):
                        entry[k] = v.isoformat() if v is not None else None
                    elif hasattr(v, '__float__'):
                        entry[k] = float(v)
                serialized_plan.append(entry)
        update_data["payment_plan"] = serialized_plan

    for key, value in update_data.items():
        setattr(invoice, key, value)

    await db.commit()
    await db.refresh(invoice)
    _sync_invoice_fb(invoice)
    changed_fields = list(update_data.keys())
    await log_activity(
        entity_type="invoice", entity_id=invoice_number,
        action="updated", icon="✏️",
        description=f"Invoice {invoice_number} updated — changed: {', '.join(changed_fields)}",
        metadata={"changed_fields": changed_fields},
    )
    return _invoice_to_response(invoice)


@invoice_router.delete("/{invoice_number}", status_code=204)
async def delete_invoice(invoice_number: str, db: AsyncSession = Depends(get_db)):
    """Delete an invoice. Only draft/pending invoices can be deleted. Paid invoices are permanent records."""
    result = await db.execute(
        select(Invoice).where(Invoice.invoice_number == invoice_number)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(404, f"Invoice {invoice_number} not found")
    # Protect paid/partially-paid invoices — they are permanent financial records
    if invoice.status in ("paid", "partial", "overdue"):
        raise HTTPException(
            403,
            f"Cannot delete a {invoice.status} invoice. Paid and active invoices are permanent financial records.",
        )
    client_name = invoice.client_name
    await db.delete(invoice)
    await db.commit()
    delete_invoice_from_firebase(invoice_number)
    await log_activity(
        entity_type="invoice", entity_id=invoice_number,
        action="deleted", icon="🗑️",
        description=f"Invoice {invoice_number} for {client_name} deleted",
    )


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
        f'<td style="padding:8px;border-bottom:1px solid #e5e7eb;text-align:right">${float(item.get("unit_price",0)):.2f}</td>'
        f'<td style="padding:8px;border-bottom:1px solid #e5e7eb;text-align:right">${float(item.get("amount",0)):.2f}</td></tr>'
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
        _sync_invoice_fb(invoice)
        await log_activity(
            entity_type="invoice", entity_id=invoice.invoice_number,
            action="sent", icon="📧",
            description=f"Invoice {invoice.invoice_number} emailed to {invoice.client_email}",
            metadata={"client_email": invoice.client_email},
        )

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
    _sync_invoice_fb(invoice)
    await log_activity(
        entity_type="invoice", entity_id=invoice_number,
        action="paid", icon="✅",
        description=f"Invoice {invoice_number} marked as paid — ${float(invoice.total_amount or 0):.2f}",
        metadata={"total_amount": float(invoice.total_amount or 0), "paid_at": invoice.paid_at.isoformat() if invoice.paid_at else None},
    )
    return _invoice_to_response(invoice)


@invoice_router.post("/{invoice_number}/record-payment")
async def record_installment_payment(
    invoice_number: str,
    req: RecordPaymentRequest,
    db: AsyncSession = Depends(get_db),
):
    """Record a payment for a specific installment in the payment plan."""
    result = await db.execute(
        select(Invoice).where(Invoice.invoice_number == invoice_number)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(404, f"Invoice {invoice_number} not found")

    plan = [dict(inst) for inst in (invoice.payment_plan or [])]
    found = False
    inst_amount = 0
    for inst in plan:
        if inst.get("id") == req.installment_id:
            inst_amount = float(req.amount or inst.get("amount", 0))
            inst["status"] = "paid"
            inst["paid_at"] = datetime.now(timezone.utc).isoformat()
            found = True
            break

    if not found:
        raise HTTPException(404, f"Installment {req.installment_id} not found")

    invoice.payment_plan = plan
    # Update total amount_paid
    new_paid = float(invoice.amount_paid or 0) + inst_amount
    invoice.amount_paid = new_paid

    # Update payment_status based on total
    total = float(invoice.total_amount or 0)
    if new_paid >= total:
        invoice.payment_status = "paid"
        invoice.status = "paid"
        invoice.paid_at = datetime.now(timezone.utc)
    else:
        invoice.payment_status = "partial"

    if req.payment_method:
        invoice.payment_method = req.payment_method

    await db.commit()
    await db.refresh(invoice)
    _sync_invoice_fb(invoice)

    await log_activity(
        entity_type="invoice", entity_id=invoice_number,
        action="payment_received", icon="💵",
        description=f"Payment of ${inst_amount:.2f} received for {invoice_number} (installment {req.installment_id})",
        metadata={
            "installment_id": req.installment_id,
            "amount": inst_amount,
            "total_paid": new_paid,
            "total_due": total,
        },
    )
    logger.info(f"💵 Installment payment recorded: ${inst_amount:.2f} on {invoice_number}")
    return _invoice_to_response(invoice)


@invoice_router.post("/{invoice_number}/send-reminder")
async def send_payment_reminder(
    invoice_number: str,
    db: AsyncSession = Depends(get_db),
):
    """Send a payment reminder email for the next unpaid installment."""
    result = await db.execute(
        select(Invoice).where(Invoice.invoice_number == invoice_number)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(404, f"Invoice {invoice_number} not found")

    plan = [dict(inst) for inst in (invoice.payment_plan or [])]
    # Find next pending/overdue installment
    next_inst = None
    for inst in plan:
        if inst.get("status") in ("pending", "overdue"):
            next_inst = inst
            break

    if not next_inst:
        return {"success": False, "message": "No pending installments found"}

    inst_amount = float(next_inst.get("amount", 0))
    inst_due = next_inst.get("due_date", "")
    remaining = float(invoice.total_amount or 0) - float(invoice.amount_paid or 0)

    subject, html = build_payment_reminder_email(
        client_name=invoice.client_name,
        invoice_number=invoice.invoice_number,
        installment_amount=f"{inst_amount:.2f}",
        due_date=inst_due,
        remaining_balance=f"{remaining:.2f}",
        payment_method=invoice.payment_method or "",
    )

    email_result = await send_email(
        to=invoice.client_email,
        subject=subject,
        body_html=html,
    )

    if email_result["success"]:
        # Mark reminder_sent_at on the installment
        next_inst["reminder_sent_at"] = datetime.now(timezone.utc).isoformat()
        invoice.payment_plan = plan
        await db.commit()
        _sync_invoice_fb(invoice)

        await log_activity(
            entity_type="invoice", entity_id=invoice_number,
            action="reminder_sent", icon="🔔",
            description=f"Payment reminder sent to {invoice.client_email} — ${inst_amount:.2f} due {inst_due}",
            metadata={
                "installment_id": next_inst.get("id"),
                "amount": inst_amount,
                "due_date": inst_due,
            },
        )
        logger.info(f"🔔 Payment reminder sent for {invoice_number} to {invoice.client_email}")

    return email_result


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
