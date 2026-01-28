"""
Validation service - Extract and validate funding context with source triangulation.
Handles conflict resolution using source trust hierarchy.
"""
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from models import Claim, Source, FundingEvent, Company, Confidence


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
    ) -> Tuple[List[FundingEvent], List[Claim], bool, Optional[str]]:
        """
        Validate funding context for a company.

        Args:
            company_name: Company name to validate
            domain: Optional company domain
            demo_mode: If True, use fixtures

        Returns:
            Tuple of (funding_events, claims, has_conflicts, resolution_note)
        """
        if demo_mode or not self.data_provider:
            return self._validate_demo(company_name)

        try:
            # Get claims from data provider
            claims = self.data_provider.fetch_funding_claims(company_name, domain)

            # Resolve conflicts and build funding snapshot
            funding_events, has_conflicts, resolution_note = self._resolve_funding_claims(claims)

            return funding_events, claims, has_conflicts, resolution_note

        except Exception as e:
            print(f"Validation error for {company_name}: {e}")
            return [], [], False, None

    def _resolve_funding_claims(
        self,
        claims: List[Claim]
    ) -> Tuple[List[FundingEvent], bool, Optional[str]]:
        """
        Resolve conflicting claims using source trust hierarchy.

        Args:
            claims: List of claims to resolve

        Returns:
            Tuple of (funding_events, has_conflicts, resolution_note)
        """
        if not claims:
            return [], False, None

        # Group claims by funding round (approximate by date similarity)
        rounds_dict = self._group_claims_by_round(claims)

        funding_events = []
        has_conflicts = False
        resolution_notes = []

        for round_key, round_claims in rounds_dict.items():
            # Resolve each field for this round
            resolved_round, conflicts = self._resolve_round_fields(round_claims)
            if conflicts:
                has_conflicts = True
                resolution_notes.extend(conflicts)

            if resolved_round:
                funding_events.append(resolved_round)

        # Sort by date (most recent first)
        funding_events.sort(key=lambda e: e.date, reverse=True)

        resolution_note = "; ".join(resolution_notes) if resolution_notes else None

        return funding_events, has_conflicts, resolution_note

    def _group_claims_by_round(self, claims: List[Claim]) -> Dict[str, List[Claim]]:
        """Group claims by funding round based on date and round type."""
        # TODO: Implement smart grouping logic
        # For now, return single group
        return {"default": claims}

    def _resolve_round_fields(
        self,
        claims: List[Claim]
    ) -> Tuple[Optional[FundingEvent], List[str]]:
        """Resolve all fields for a single funding round."""
        # TODO: Implement field-by-field resolution using source trust
        # For now, return None
        return None, []

    def _validate_demo(
        self,
        company_name: str
    ) -> Tuple[List[FundingEvent], List[Claim], bool, Optional[str]]:
        """Return demo validation results."""
        return [], [], False, None

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


# Global instance
validation_service = ValidationService()
