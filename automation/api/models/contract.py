"""
AjayaDesign Automation — Contract & Invoice models.
"""

import uuid
from datetime import datetime, date

from sqlalchemy import (
    Column, String, Text, DateTime, Date, Numeric,
    ForeignKey, JSON, Integer, func,
)
from sqlalchemy.orm import relationship

from api.database import Base


class Contract(Base):
    """A contract between AjayaDesign and a client."""
    __tablename__ = "contracts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    short_id = Column(String(8), unique=True, nullable=False)

    # Link to a build (optional — portfolio items may not have a build)
    build_id = Column(String(36), ForeignKey("builds.id"), nullable=True)

    # Client info
    client_name = Column(String(200), nullable=False)
    client_email = Column(String(200), nullable=False)
    client_address = Column(Text, default="")
    client_phone = Column(String(30), default="")

    # Project info
    project_name = Column(String(300), nullable=False)
    project_description = Column(Text, default="")

    # Financial
    total_amount = Column(Numeric(10, 2), nullable=False, default=0)
    deposit_amount = Column(Numeric(10, 2), default=0)
    payment_method = Column(String(30), default="")  # venmo, zelle, paypal, bank
    payment_terms = Column(Text, default="")

    # Timeline
    start_date = Column(Date, nullable=True)
    estimated_completion_date = Column(Date, nullable=True)

    # Contract content
    clauses = Column(JSON, default=list)  # [{id, title, body, enabled}]
    custom_notes = Column(Text, default="")

    # Provider info
    provider_name = Column(String(200), default="AjayaDesign")
    provider_email = Column(String(200), default="ajayadesign@gmail.com")
    provider_address = Column(Text, default="13721 Andrew Abernathy Pass, Manor, TX 78653")

    # Status: draft, sent, viewed, signed, completed, cancelled
    status = Column(String(20), default="draft")

    # Signing
    sign_token = Column(String(36), default=lambda: str(uuid.uuid4()), unique=True)
    signed_at = Column(DateTime(timezone=True), nullable=True)
    signature_data = Column(Text, nullable=True)  # base64 PNG of signature
    signer_ip = Column(String(50), nullable=True)
    signer_name = Column(String(200), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    sent_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    invoices = relationship("Invoice", back_populates="contract", lazy="selectin")

    def __repr__(self):
        return f"<Contract {self.short_id} – {self.client_name}>"


class Invoice(Base):
    """An invoice for services rendered."""
    __tablename__ = "invoices"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    invoice_number = Column(String(20), unique=True, nullable=False)

    # Link to contract (optional)
    contract_id = Column(String(36), ForeignKey("contracts.id"), nullable=True)
    # Link to build (optional)
    build_id = Column(String(36), ForeignKey("builds.id"), nullable=True)

    # Client info
    client_name = Column(String(200), nullable=False)
    client_email = Column(String(200), nullable=False)

    # Line items: [{description, quantity, unit_price, amount}]
    items = Column(JSON, default=list)

    # Totals
    subtotal = Column(Numeric(10, 2), default=0)
    tax_rate = Column(Numeric(5, 4), default=0)  # e.g., 0.0825 for 8.25%
    tax_amount = Column(Numeric(10, 2), default=0)
    total_amount = Column(Numeric(10, 2), nullable=False, default=0)
    amount_paid = Column(Numeric(10, 2), default=0)

    # Payment
    payment_method = Column(String(30), default="")
    payment_status = Column(String(20), default="unpaid")  # unpaid, partial, paid
    due_date = Column(Date, nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)

    # Provider info
    provider_name = Column(String(200), default="AjayaDesign")
    provider_email = Column(String(200), default="ajayadesign@gmail.com")
    provider_address = Column(Text, default="13721 Andrew Abernathy Pass, Manor, TX 78653")

    notes = Column(Text, default="")
    status = Column(String(20), default="draft")  # draft, sent, paid, overdue, cancelled

    # Payment plan: [{id, due_date, amount, status, paid_at, reminder_sent_at}]
    payment_plan = Column(JSON, default=list)
    payment_plan_enabled = Column(String(5), default="false")  # "true"/"false"

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    sent_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    contract = relationship("Contract", back_populates="invoices")

    def __repr__(self):
        return f"<Invoice {self.invoice_number} – {self.client_name}>"
