"""
SMTP Provider Pool — Model for multi-provider email sending.

Allows aggregating free tiers from multiple SMTP providers
(Gmail, Brevo, Mailjet, SendGrid, etc.) to exceed single-provider daily limits.
"""

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Column, Date, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID

from api.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class SmtpProvider(Base):
    """An SMTP relay provider with daily quota tracking."""

    __tablename__ = "smtp_providers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True)         # "gmail", "brevo", "mailjet"
    host = Column(String, nullable=False)                      # "smtp.gmail.com"
    port = Column(Integer, nullable=False, default=587)
    username = Column(String, nullable=False)
    password = Column(String, nullable=False)                  # app password / API key
    use_tls = Column(Boolean, default=True)
    from_email = Column(String)                                # override From address, or NULL = default
    from_name = Column(String)                                 # override From name, or NULL = default

    daily_limit = Column(Integer, nullable=False, default=100)
    daily_sent = Column(Integer, nullable=False, default=0)
    last_reset = Column(Date, nullable=False, default=date.today)
    enabled = Column(Boolean, default=True)
    priority = Column(Integer, default=0)                      # higher = preferred

    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    def to_dict(self, safe=True):
        """Convert to dict. safe=True masks the password."""
        d = {
            "id": str(self.id),
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "use_tls": self.use_tls,
            "from_email": self.from_email,
            "from_name": self.from_name,
            "daily_limit": self.daily_limit,
            "daily_sent": self.daily_sent,
            "last_reset": self.last_reset.isoformat() if self.last_reset else None,
            "enabled": self.enabled,
            "priority": self.priority,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if not safe:
            d["password"] = self.password
        return d
