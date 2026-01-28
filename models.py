from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    CONFLICT = "conflict"


# Alias for backwards compatibility
Confidence = ConfidenceLevel


class ClaimStatus(str, Enum):
    VERIFIED = "verified"
    CONFLICTING = "conflicting"
    UNVERIFIED = "unverified"


class ShortlistStatus(str, Enum):
    PURSUE = "pursue"
    WATCH = "watch"
    DEPRIORITIZE = "deprioritize"


class FreshnessLevel(str, Enum):
    FRESH = "fresh"      # < 3 months
    RECENT = "recent"    # 3-12 months
    STALE = "stale"      # 12-24 months
    OLD = "old"          # > 24 months


class Source(BaseModel):
    id: str
    url: str
    source_type: str  # "news", "official", "database", "social"
    title: str
    timestamp: datetime


class Claim(BaseModel):
    id: str
    company_id: str
    statement: str
    sources: list[Source]
    confidence: ConfidenceLevel
    status: ClaimStatus


class FundingEvent(BaseModel):
    id: str
    company_id: str
    round_type: str
    date: datetime
    amount: Optional[str] = None
    lead: Optional[str] = None
    participants: list[str] = []
    valuation_signal: Optional[str] = None
    freshness: FreshnessLevel = FreshnessLevel.RECENT


class StageEstimate(BaseModel):
    """Stage estimate with confidence."""
    stage: str  # "Seed", "Series A", "Series B", "Series C+", "Growth"
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    basis: Optional[str] = None  # Explanation of how stage was determined


class FundingSnapshot(BaseModel):
    """Consolidated funding view with conflict resolution."""
    last_round_date: Optional[datetime] = None
    last_round_type: Optional[str] = None
    amount: Optional[str] = None
    lead_investor: Optional[str] = None
    post_money_valuation: Optional[str] = None
    valuation_confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    valuation_basis: Optional[str] = None  # "direct", "secondary", "implied", "rumor", "estimate"
    sources: list[Source] = []
    overall_confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    has_conflicts: bool = False
    resolution_note: Optional[str] = None


class Company(BaseModel):
    id: str
    name: str
    description: str
    website: Optional[str] = None
    location: Optional[str] = None
    tags: list[str] = []
    stage: Optional[str] = None
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    funding_events: list[FundingEvent] = []
    claims: list[Claim] = []
    thesis_fit_notes: Optional[str] = None
    source_count: int = 0
    updated: bool = False

    # Discovery/ranking fields
    fit_score: int = 0  # 0-100 thesis fit score
    fit_reasons: list[str] = []  # Bullet points explaining fit
    stage_estimate: Optional[StageEstimate] = None
    next_action: Optional[str] = None  # For "maybe" bucket: what to check next

    # Validation fields
    funding_snapshot: Optional[FundingSnapshot] = None
    validation_status: str = "pending"  # "pending", "validated", "failed"


class ShortlistEntry(BaseModel):
    company_id: str
    status: ShortlistStatus
    rationale: Optional[str] = None
    added_at: datetime


class ThesisSprint(BaseModel):
    id: str
    name: str
    description: str
    keywords_include: list[str] = []
    keywords_exclude: list[str] = []
    stage_focus: str = "Seed – Series B"
    geography: str = "US, EU"
    last_raise_filter: str = "Within 18 months"
    status: str = "active"
    company_ids: list[str] = []
    shortlist: list[ShortlistEntry] = []
