"""
AjayaDesign Automation — Contract & Invoice Pydantic schemas.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ── Clause ──────────────────────────────────────────────
class ClauseItem(BaseModel):
    id: str
    title: str
    body: str
    enabled: bool = True


# ── Contract ────────────────────────────────────────────
class ContractCreateRequest(BaseModel):
    build_id: Optional[str] = None
    client_name: str
    client_email: str
    client_address: str = ""
    client_phone: str = ""
    project_name: str
    project_description: str = ""
    total_amount: Decimal = Decimal("0")
    deposit_amount: Decimal = Decimal("0")
    payment_method: str = ""
    payment_terms: str = ""
    start_date: Optional[date] = None
    estimated_completion_date: Optional[date] = None
    clauses: list[ClauseItem] = []
    custom_notes: str = ""


class ContractUpdateRequest(BaseModel):
    client_name: Optional[str] = None
    client_email: Optional[str] = None
    client_address: Optional[str] = None
    client_phone: Optional[str] = None
    project_name: Optional[str] = None
    project_description: Optional[str] = None
    total_amount: Optional[Decimal] = None
    deposit_amount: Optional[Decimal] = None
    payment_method: Optional[str] = None
    payment_terms: Optional[str] = None
    start_date: Optional[date] = None
    estimated_completion_date: Optional[date] = None
    clauses: Optional[list[ClauseItem]] = None
    custom_notes: Optional[str] = None
    status: Optional[str] = None


class ContractResponse(BaseModel):
    id: str
    short_id: str
    build_id: Optional[str] = None
    client_name: str
    client_email: str
    client_address: str
    client_phone: str
    project_name: str
    project_description: str
    total_amount: Decimal
    deposit_amount: Decimal
    payment_method: str
    payment_terms: str
    start_date: Optional[date] = None
    estimated_completion_date: Optional[date] = None
    clauses: list[ClauseItem] = []
    custom_notes: str
    provider_name: str
    provider_email: str
    provider_address: str
    status: str
    sign_token: str
    signed_at: Optional[datetime] = None
    signer_name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    invoices: list["InvoiceResponse"] = []

    class Config:
        from_attributes = True


class ContractListResponse(BaseModel):
    contracts: list[ContractResponse]
    total: int


class ContractSignRequest(BaseModel):
    signer_name: str
    signature_data: str  # base64 PNG


# ── Invoice ─────────────────────────────────────────────
class InvoiceLineItem(BaseModel):
    description: str
    quantity: int = 1
    unit_price: Decimal = Decimal("0")
    amount: Decimal = Decimal("0")


class InvoiceCreateRequest(BaseModel):
    contract_id: Optional[str] = None
    build_id: Optional[str] = None
    client_name: str
    client_email: str
    items: list[InvoiceLineItem] = []
    subtotal: Decimal = Decimal("0")
    tax_rate: Decimal = Decimal("0")
    tax_amount: Decimal = Decimal("0")
    total_amount: Decimal = Decimal("0")
    amount_paid: Decimal = Decimal("0")
    payment_method: str = ""
    payment_status: str = "unpaid"
    due_date: Optional[date] = None
    notes: str = ""


class InvoiceUpdateRequest(BaseModel):
    client_name: Optional[str] = None
    client_email: Optional[str] = None
    items: Optional[list[InvoiceLineItem]] = None
    subtotal: Optional[Decimal] = None
    tax_rate: Optional[Decimal] = None
    tax_amount: Optional[Decimal] = None
    total_amount: Optional[Decimal] = None
    amount_paid: Optional[Decimal] = None
    payment_method: Optional[str] = None
    payment_status: Optional[str] = None
    due_date: Optional[date] = None
    notes: Optional[str] = None
    status: Optional[str] = None


class InvoiceResponse(BaseModel):
    id: str
    invoice_number: str
    contract_id: Optional[str] = None
    build_id: Optional[str] = None
    client_name: str
    client_email: str
    items: list[InvoiceLineItem] = []
    subtotal: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    amount_paid: Decimal
    payment_method: str
    payment_status: str
    due_date: Optional[date] = None
    paid_at: Optional[datetime] = None
    provider_name: str
    provider_email: str
    provider_address: str
    notes: str
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class InvoiceListResponse(BaseModel):
    invoices: list[InvoiceResponse]
    total: int


# ── Email ───────────────────────────────────────────────
class SendEmailRequest(BaseModel):
    to: str
    subject: str
    body_html: str
    contract_id: Optional[str] = None
    invoice_id: Optional[str] = None


class SendEmailResponse(BaseModel):
    success: bool
    message: str


# ── Portfolio / Build Patch ─────────────────────────────
class BuildPatchRequest(BaseModel):
    client_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    niche: Optional[str] = None
    location: Optional[str] = None
    goals: Optional[str] = None
    live_url: Optional[str] = None
    brand_colors: Optional[str] = None
    tagline: Optional[str] = None
    status: Optional[str] = None


class PortfolioSeedRequest(BaseModel):
    """Seed existing portfolio sites as Build records."""
    sites: list["PortfolioSiteInfo"]


class PortfolioSiteInfo(BaseModel):
    client_name: str
    niche: str
    goals: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    live_url: str = ""
    repo_name: str = ""
    directory_name: str = ""  # e.g., "chhayaphotography"
    brand_colors: str = ""
    tagline: str = ""
    status: str = "complete"
