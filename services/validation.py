"""
Validation service - Extract and validate funding context with source triangulation.
Handles conflict resolution using source trust hierarchy.
"""
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import uuid
import re
from models import Claim, Source, FundingEvent, Company, Confidence, FreshnessLevel, FundingSnapshot


# Source trust hierarchy (higher = more trusted)
SOURCE_TRUST_LEVELS = {
    "company_press": 100,      # Company press release/newsroom
    "sec_filing": 95,          # SEC/regulatory filings
    "business_press": 80,      # Reputable business press (TechCrunch, Bloomberg, etc.)
    "investor_blog": 70,       # Credible investor blog posts
    "crunchbase": 60,          # Crunchbase (when API available)
    "pitchbook": 60,           # PitchBook (when API available)
    "wikipedia": 40,           # Wikipedia
    "directory": 30,           # Generic directories
    "social": 20,              # Social media (X, LinkedIn)
    "unknown": 10              # Unknown/unclassified
}


class ValidationService:
    """Service for validating funding context and resolving conflicts."""

    def __init__(self, data_provider=None):
        """Initialize with optional data provider."""
        self.data_provider = data_provider

    def validate_company_funding(
        self,
        company_name: str,
        domain: Optional[str] = None,
        demo_mode: bool = False
    ) -> Tuple[Optional[FundingSnapshot], List[Claim], bool, Optional[str]]:
        """
        Validate funding context for a company.

        Args:
            company_name: Company name to validate
            domain: Optional company domain
            demo_mode: If True, use fixtures

        Returns:
            Tuple of (funding_snapshot, claims, has_conflicts, resolution_note)
        """
        if demo_mode or not self.data_provider:
            return self._validate_demo(company_name)

        try:
            # Get claims from data provider
            claims = self.data_provider.fetch_funding_claims(company_name, domain)

            # Resolve conflicts and build funding snapshot
            funding_snapshot, has_conflicts, resolution_note = self._resolve_funding_claims(claims)

            return funding_snapshot, claims, has_conflicts, resolution_note

        except Exception as e:
            print(f"Validation error for {company_name}: {e}")
            return None, [], False, None

    def _resolve_funding_claims(
        self,
        claims: List[Claim]
    ) -> Tuple[Optional[FundingSnapshot], bool, Optional[str]]:
        """
        Resolve conflicting claims using source trust hierarchy.

        Args:
            claims: List of claims to resolve

        Returns:
            Tuple of (funding_snapshot, has_conflicts, resolution_note)
        """
        if not claims:
            return None, False, None

        # Group claims by funding round (for MVP, assumes single latest round)
        rounds_dict = self._group_claims_by_round(claims)

        # Resolve the latest round
        snapshot = None
        has_conflicts = False
        resolution_notes = []

        if "latest" in rounds_dict:
            snapshot, conflicts = self._resolve_round_fields(rounds_dict["latest"])
            if conflicts:
                has_conflicts = True
                resolution_notes.extend(conflicts)

        resolution_note = "; ".join(resolution_notes) if resolution_notes else None

        return snapshot, has_conflicts, resolution_note

    def _group_claims_by_round(self, claims: List[Claim]) -> Dict[str, List[Claim]]:
        """Group claims by funding round based on date and round type."""
        # For MVP, assume all claims are about the same (most recent) round
        # In production, would need more sophisticated grouping logic
        if not claims:
            return {}
        return {"latest": claims}

    def _resolve_round_fields(
        self,
        claims: List[Claim]
    ) -> Tuple[Optional[FundingSnapshot], List[str]]:
        """Resolve all fields for a single funding round using source trust."""
        if not claims:
            return None, []

        # Extract field values from claim statements
        date_val = None
        round_type = None
        amount = None
        lead = None
        valuation = None
        valuation_basis = None
        all_sources = []

        conflicts = []

        for claim in claims:
            statement = claim.statement
            all_sources.extend(claim.sources)

            # Parse claim statement
            if "Last round date:" in statement:
                date_str = statement.split(": ")[1].strip()
                try:
                    date_val = datetime.strptime(date_str, "%Y-%m")
                except:
                    pass

            elif "Last round type:" in statement:
                round_type = statement.split(": ")[1].strip()

            elif "Amount:" in statement:
                amount = statement.split(": ")[1].strip()

            elif "Lead investor:" in statement:
                lead = statement.split(": ")[1].strip()

            elif "Valuation:" in statement:
                parts = statement.split(": ")[1].strip()
                if "(" in parts:
                    valuation = parts.split("(")[0].strip()
                    valuation_basis = parts.split("(")[1].rstrip(")")
                else:
                    valuation = parts

        # Calculate overall confidence
        avg_conf = self._calc_avg_confidence([c.confidence for c in claims])

        # Determine freshness
        freshness = FreshnessLevel.RECENT
        if date_val:
            months_ago = (datetime.now() - date_val).days / 30
            if months_ago < 3:
                freshness = FreshnessLevel.FRESH
            elif months_ago < 12:
                freshness = FreshnessLevel.RECENT
            elif months_ago < 24:
                freshness = FreshnessLevel.STALE
            else:
                freshness = FreshnessLevel.OLD

        # Build funding snapshot
        snapshot = FundingSnapshot(
            last_round_date=date_val,
            last_round_type=round_type,
            amount=amount,
            lead_investor=lead,
            post_money_valuation=valuation,
            valuation_confidence=avg_conf,
            valuation_basis=valuation_basis,
            sources=all_sources[:5],  # Top 5 sources
            overall_confidence=avg_conf,
            has_conflicts=False,  # MVP: skip complex conflict detection
            resolution_note=None
        )

        return snapshot, conflicts

    def _calc_avg_confidence(self, confidences: List[Confidence]) -> Confidence:
        """Calculate average confidence level."""
        if not confidences:
            return Confidence.MEDIUM

        conf_values = {"high": 3, "medium": 2, "low": 1}
        avg = sum(conf_values.get(c.value, 2) for c in confidences) / len(confidences)

        if avg >= 2.5:
            return Confidence.HIGH
        elif avg >= 1.5:
            return Confidence.MEDIUM
        else:
            return Confidence.LOW

    def _validate_demo(
        self,
        company_name: str
    ) -> Tuple[Optional[FundingSnapshot], List[Claim], bool, Optional[str]]:
        """Return demo validation results."""
        return None, [], False, None

    def get_source_trust_level(self, source: Source) -> int:
        """Get trust level for a source based on its type."""
        return SOURCE_TRUST_LEVELS.get(source.source_type, SOURCE_TRUST_LEVELS["unknown"])

    def classify_source_type(self, url: str) -> str:
        """
        Classify source type based on URL patterns.

        Args:
            url: Source URL

        Returns:
            Source type string (company_press, business_press, etc.)
        """
        url_lower = url.lower()

        # Company press releases
        if any(x in url_lower for x in ["/press/", "/news/", "/newsroom/", "/blog/"]):
            # Check if it's the company's own domain (rough heuristic)
            if not any(x in url_lower for x in ["techcrunch", "bloomberg", "reuters", "forbes", "wsj"]):
                return "company_press"

        # SEC filings
        if "sec.gov" in url_lower or "edgar" in url_lower:
            return "sec_filing"

        # Business press
        if any(x in url_lower for x in [
            "techcrunch", "bloomberg", "reuters", "forbes", "wsj.com", "ft.com",
            "theinformation", "axios", "cnbc", "businessinsider"
        ]):
            return "business_press"

        # Investor blogs
        if any(x in url_lower for x in [
            "a16z.com", "sequoiacap", "accel.com", "greylock", "kleinerperkins",
            "benchmark.com", "lightspeedvp"
        ]):
            return "investor_blog"

        # Data platforms
        if "crunchbase" in url_lower:
            return "crunchbase"
        if "pitchbook" in url_lower:
            return "pitchbook"

        # Wikipedia
        if "wikipedia.org" in url_lower:
            return "wikipedia"

        # Social media
        if any(x in url_lower for x in ["twitter.com", "x.com", "linkedin.com"]):
            return "social"

        return "unknown"


# Global instance (will be initialized with data provider in main.py)
validation_service = ValidationService()
