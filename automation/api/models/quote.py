"""
AjayaDesign Automation — Quote model.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Text, DateTime, Numeric,
    ForeignKey, JSON, Integer, func,
)

from api.database import Base


class Quote(Base):
    """A project quote / proposal for a client."""
    __tablename__ = "quotes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    short_id = Column(String(8), unique=True, nullable=False)

    # Link to a build (optional)
    build_id = Column(String(36), ForeignKey("builds.id"), nullable=True)

    # Client info
    client_name = Column(String(200), nullable=False)
    client_email = Column(String(200), nullable=False)

    # Project info
    project_name = Column(String(300), nullable=False)
    project_description = Column(Text, default="")

    # Deliverables: [{id, description, hours, rate, amount}]
    deliverables = Column(JSON, default=list)

    # Totals
    subtotal = Column(Numeric(10, 2), default=0)
    tax_rate = Column(Numeric(5, 4), default=0)      # e.g. 0.0825 for 8.25%
    tax_amount = Column(Numeric(10, 2), default=0)
    total_amount = Column(Numeric(10, 2), nullable=False, default=0)

    # Payment
    payment_schedule = Column(Text, default="")       # e.g. "50% upfront, 50% on completion"

    # Validity
    valid_days = Column(Integer, default=30)

    # Notes
    custom_notes = Column(Text, default="")

    # Revision tracking
    revision = Column(Integer, default=1)

    # Provider info
    provider_name = Column(String(200), default="AjayaDesign")
    provider_email = Column(String(200), default="ajayadesign@gmail.com")

    # Status: draft, sent, viewed, approved, declined, expired, revised
    status = Column(String(20), default="draft")

    # Viewing / signing token
    view_token = Column(String(36), default=lambda: str(uuid.uuid4()), unique=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    signature_data = Column(Text, nullable=True)
    signer_name = Column(String(200), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    sent_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<Quote {self.short_id} – {self.client_name} (rev {self.revision})>"
