"""
AjayaDesign Automation — Quote Pydantic schemas.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


# ── Deliverable item ────────────────────────────────────
class DeliverableItem(BaseModel):
    id: str
    description: str
    hours: float = 0
    rate: Decimal = Decimal("0")
    amount: Decimal = Decimal("0")


# ── Quote Create ────────────────────────────────────────
class QuoteCreateRequest(BaseModel):
    build_id: Optional[str] = None
    client_name: str
    client_email: str
    project_name: str
    project_description: str = ""
    deliverables: list[DeliverableItem] = []
    subtotal: Decimal = Decimal("0")
    tax_rate: Decimal = Decimal("0")
    tax_amount: Decimal = Decimal("0")
    total_amount: Decimal = Decimal("0")
    payment_schedule: str = ""
    valid_days: int = 30
    custom_notes: str = ""
    revision: int = 1


# ── Quote Update ────────────────────────────────────────
class QuoteUpdateRequest(BaseModel):
    client_name: Optional[str] = None
    client_email: Optional[str] = None
    project_name: Optional[str] = None
    project_description: Optional[str] = None
    deliverables: Optional[list[DeliverableItem]] = None
    subtotal: Optional[Decimal] = None
    tax_rate: Optional[Decimal] = None
    tax_amount: Optional[Decimal] = None
    total_amount: Optional[Decimal] = None
    payment_schedule: Optional[str] = None
    valid_days: Optional[int] = None
    custom_notes: Optional[str] = None
    status: Optional[str] = None
    revision: Optional[int] = None


# ── Quote Response ──────────────────────────────────────
class QuoteResponse(BaseModel):
    id: str
    short_id: str
    build_id: Optional[str] = None
    client_name: str
    client_email: str
    project_name: str
    project_description: str
    deliverables: list[DeliverableItem] = []
    subtotal: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    payment_schedule: str
    valid_days: int
    custom_notes: str
    revision: int
    provider_name: str
    provider_email: str
    status: str
    view_token: str
    approved_at: Optional[datetime] = None
    signer_name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class QuoteListResponse(BaseModel):
    quotes: list[QuoteResponse]
    total: int
