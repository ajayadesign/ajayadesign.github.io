"""
AjayaDesign Automation — Pydantic request/response schemas.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, EmailStr, Field


class BuildStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"
    STALLED = "stalled"


class BuildRequest(BaseModel):
    business_name: str = Field(..., alias="businessName", min_length=2, max_length=255)
    niche: str = Field(..., min_length=2, max_length=255)
    goals: str = Field("", max_length=2000)
    email: EmailStr | None = None
    firebase_id: str | None = Field(None, alias="firebaseId", max_length=255)
    source: str | None = Field(None, max_length=50)
    # Enhanced fields (Task 1)
    phone: str | None = Field(None, max_length=30)
    location: str | None = Field(None, max_length=255)
    existing_website: str | None = Field(None, alias="existingWebsite", max_length=512)
    brand_colors: str | None = Field(None, alias="brandColors", max_length=255)
    tagline: str | None = Field(None, max_length=255)
    target_audience: str | None = Field(None, alias="targetAudience", max_length=500)
    competitor_urls: str | None = Field(None, alias="competitorUrls", max_length=2000)
    additional_notes: str | None = Field(None, alias="additionalNotes", max_length=2000)
    rebuild: bool = Field(False)


class BuildResponse(BaseModel):
    id: str
    short_id: str
    status: BuildStatus
    client_name: str | None = None
    niche: str | None = None
    message: str | None = None
    live_url: str | None = None
    repo_full: str | None = None
    pages_count: int | None = None
    created_at: datetime | str | None = None
    started_at: datetime | str | None = None
    finished_at: datetime | str | None = None
    duration_secs: float | None = None
    error_message: str | None = None
    stream_url: str | None = None
    protected: bool = False

    model_config = {"from_attributes": True}


class BuildListResponse(BaseModel):
    builds: list[BuildResponse]
    total: int


class PhaseDetail(BaseModel):
    phase_number: int
    phase_name: str
    status: str
    ai_calls: int = 0
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_message: str | None = None

    model_config = {"from_attributes": True}


class BuildDetailResponse(BuildResponse):
    goals: str | None = None
    email: str | None = None
    repo_name: str | None = None
    blueprint: dict | None = None
    design_system: dict | None = None
    phases: list[PhaseDetail] = []


class LogEntry(BaseModel):
    sequence: int
    level: str
    category: str | None = None
    message: str
    created_at: datetime

    model_config = {"from_attributes": True}


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "2.0.0-python"
    timestamp: str | None = None
    database: str = "connected"
    active_builds: int = 0


# ── Parse Client (Task 5) ──────────────────────────────────
class ParseClientRequest(BaseModel):
    raw_text: str = Field(..., alias="rawText", min_length=10, max_length=10000)


class ParsedClientFields(BaseModel):
    business_name: str | None = Field(None, alias="businessName")
    niche: str | None = None
    goals: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    existing_website: str | None = Field(None, alias="existingWebsite")
    brand_colors: str | None = Field(None, alias="brandColors")
    tagline: str | None = None
    target_audience: str | None = Field(None, alias="targetAudience")
    competitor_urls: str | None = Field(None, alias="competitorUrls")
    additional_notes: str | None = Field(None, alias="additionalNotes")

    model_config = {"populate_by_name": True}


class ParseClientResponse(BaseModel):
    parsed: ParsedClientFields
    confidence: str = "medium"  # "high", "medium", "low"
