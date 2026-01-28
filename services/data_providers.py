"""
Data provider abstraction layer for funding information.
Supports pluggable providers: PublicWebProvider (MVP), Crunchbase, PitchBook (future).
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict
from datetime import datetime
import httpx
from bs4 import BeautifulSoup
import time
import os
import uuid
from anthropic import Anthropic
from models import Claim, Source, ConfidenceLevel, ClaimStatus


class DataProvider(ABC):
    """Base interface for data providers."""

    @abstractmethod
    def fetch_funding_claims(
        self,
        company_name: str,
        domain: Optional[str] = None
    ) -> List[Claim]:
        """
        Fetch funding claims for a company.

        Args:
            company_name: Company name
            domain: Optional company domain

        Returns:
            List of Claim objects with sources
        """
        pass

    @abstractmethod
    def search_company(self, company_name: str) -> Optional[Dict]:
        """
        Search for basic company info (domain, description).

        Args:
            company_name: Company name

        Returns:
            Dict with keys: name, domain, description (or None if not found)
        """
        pass


class PublicWebProvider(DataProvider):
    """
    Public web provider using web search and scraping.
    MVP implementation with rate limiting and caching.
    """

    def __init__(self):
        """Initialize with HTTP client and cache."""
        self.client = httpx.Client(timeout=10.0, follow_redirects=True)
        self.cache: Dict[str, tuple] = {}  # url -> (content, timestamp)
        self.cache_ttl = 3600  # 1 hour cache
        self.rate_limit_delay = 1.0  # 1 second between requests
        self.last_request_time = 0

        # Claude API for information extraction
        api_key = os.getenv("ANTHROPIC_API_KEY")
        self.anthropic = Anthropic(api_key=api_key) if api_key else None

    def fetch_funding_claims(
        self,
        company_name: str,
        domain: Optional[str] = None
    ) -> List[Claim]:
        """
        Fetch funding claims from public web sources.

        Strategy:
        1. Use Claude to research funding information
        2. Extract structured claims with source attribution
        3. Return claims for conflict resolution

        Args:
            company_name: Company name
            domain: Optional company domain (helps with search precision)

        Returns:
            List of Claim objects
        """
        if not self.anthropic:
            print(f"No Anthropic API key available for validation")
            return []

        try:
            # Use Claude to research funding information
            claims = self._research_with_claude(company_name, domain)
            return claims

        except Exception as e:
            print(f"Error fetching funding claims for {company_name}: {e}")
            return []

    def _research_with_claude(
        self,
        company_name: str,
        domain: Optional[str]
    ) -> List[Claim]:
        """Use Claude to research funding information."""
        prompt = f"""Research the most recent funding information for {company_name}.

IMPORTANT: Only provide information you're confident about. For any uncertain information, mark confidence as "low" and include a note explaining the uncertainty.

Provide the following information in JSON format:

{{
  "last_round_date": "YYYY-MM" or null,
  "last_round_type": "Seed/Series A/Series B/etc" or null,
  "amount": "$XM" or null,
  "lead_investor": "Investor name" or null,
  "post_money_valuation": "Valuation or estimate" or null,
  "valuation_basis": "direct/secondary/implied/rumor/estimate",
  "sources": [
    {{
      "url": "source URL",
      "source_type": "company_press/sec_filing/business_press/investor_blog/wikipedia/social/unknown",
      "title": "Article title or source name",
      "confidence": "high/medium/low"
    }}
  ],
  "overall_confidence": "high/medium/low",
  "notes": "Any caveats or uncertainties"
}}

Return ONLY the JSON, no markdown formatting or explanation."""

        try:
            response = self.anthropic.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=2000,
                temperature=0.1,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            # Parse response into Claim objects
            import json
            json_text = response.content[0].text.strip()
            if json_text.startswith("```"):
                lines = json_text.split("\n")
                json_text = "\n".join(lines[1:-1]) if len(lines) > 2 else json_text
                json_text = json_text.replace("```json", "").replace("```", "").strip()

            data = json.loads(json_text)
            claims = self._convert_to_claims(company_name, data)
            return claims

        except Exception as e:
            print(f"Claude research error: {e}")
            return []

    def _convert_to_claims(
        self,
        company_name: str,
        data: Dict
    ) -> List[Claim]:
        """Convert research data to Claim objects."""
        claims = []

        # Create sources
        sources = []
        for source_data in data.get("sources", []):
            source = Source(
                id=str(uuid.uuid4()),
                url=source_data.get("url", ""),
                source_type=source_data.get("source_type", "unknown"),
                title=source_data.get("title", ""),
                timestamp=datetime.now()
            )
            sources.append(source)

        # Map confidence strings to enum
        conf_map = {
            "high": ConfidenceLevel.HIGH,
            "medium": ConfidenceLevel.MEDIUM,
            "low": ConfidenceLevel.LOW
        }
        overall_conf = conf_map.get(data.get("overall_confidence", "medium"), ConfidenceLevel.MEDIUM)

        # Create claims for each field
        if data.get("last_round_date"):
            claims.append(Claim(
                id=str(uuid.uuid4()),
                company_id="",  # Will be set by caller
                statement=f"Last round date: {data['last_round_date']}",
                sources=sources,
                confidence=overall_conf,
                status=ClaimStatus.VERIFIED
            ))

        if data.get("last_round_type"):
            claims.append(Claim(
                id=str(uuid.uuid4()),
                company_id="",
                statement=f"Last round type: {data['last_round_type']}",
                sources=sources,
                confidence=overall_conf,
                status=ClaimStatus.VERIFIED
            ))

        if data.get("amount"):
            claims.append(Claim(
                id=str(uuid.uuid4()),
                company_id="",
                statement=f"Amount: {data['amount']}",
                sources=sources,
                confidence=overall_conf,
                status=ClaimStatus.VERIFIED
            ))

        if data.get("lead_investor"):
            claims.append(Claim(
                id=str(uuid.uuid4()),
                company_id="",
                statement=f"Lead investor: {data['lead_investor']}",
                sources=sources,
                confidence=overall_conf,
                status=ClaimStatus.VERIFIED
            ))

        if data.get("post_money_valuation"):
            claims.append(Claim(
                id=str(uuid.uuid4()),
                company_id="",
                statement=f"Valuation: {data['post_money_valuation']} ({data.get('valuation_basis', 'unknown')})",
                sources=sources,
                confidence=overall_conf,
                status=ClaimStatus.VERIFIED
            ))

        return claims

    def search_company(self, company_name: str) -> Optional[Dict]:
        """
        Search for basic company info.

        Args:
            company_name: Company name

        Returns:
            Dict with company info or None
        """
        # TODO: Implement company search
        # For Phase 1, return None (will implement in Phase 2/3)
        return None

    def _rate_limit(self):
        """Apply rate limiting between requests."""
        now = time.time()
        elapsed = now - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()

    def _fetch_url(self, url: str) -> Optional[str]:
        """
        Fetch URL content with caching and error handling.

        Args:
            url: URL to fetch

        Returns:
            HTML content or None on error
        """
        # Check cache
        if url in self.cache:
            content, timestamp = self.cache[url]
            if time.time() - timestamp < self.cache_ttl:
                return content

        # Apply rate limiting
        self._rate_limit()

        try:
            response = self.client.get(url)
            response.raise_for_status()
            content = response.text

            # Cache the result
            self.cache[url] = (content, time.time())

            return content

        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None

    def _parse_funding_page(self, html: str, url: str) -> List[Claim]:
        """
        Parse funding information from HTML page.

        Args:
            html: HTML content
            url: Source URL

        Returns:
            List of extracted claims
        """
        # TODO: Implement parsing logic
        # Will be implemented in Phase 3
        return []

    def __del__(self):
        """Clean up HTTP client."""
        try:
            self.client.close()
        except:
            pass


class CrunchbaseProvider(DataProvider):
    """
    Crunchbase provider (stub for future implementation).
    Requires API key.
    """

    def __init__(self, api_key: str):
        """Initialize with API key."""
        self.api_key = api_key
        # TODO: Initialize Crunchbase client

    def fetch_funding_claims(
        self,
        company_name: str,
        domain: Optional[str] = None
    ) -> List[Claim]:
        """Fetch funding claims from Crunchbase."""
        # TODO: Implement Crunchbase API calls
        raise NotImplementedError("Crunchbase provider not yet implemented")

    def search_company(self, company_name: str) -> Optional[Dict]:
        """Search for company in Crunchbase."""
        # TODO: Implement Crunchbase search
        raise NotImplementedError("Crunchbase provider not yet implemented")


class PitchBookProvider(DataProvider):
    """
    PitchBook provider (stub for future implementation).
    Requires API key and license.
    """

    def __init__(self, api_key: str):
        """Initialize with API key."""
        self.api_key = api_key
        # TODO: Initialize PitchBook client

    def fetch_funding_claims(
        self,
        company_name: str,
        domain: Optional[str] = None
    ) -> List[Claim]:
        """Fetch funding claims from PitchBook."""
        # TODO: Implement PitchBook API calls
        raise NotImplementedError("PitchBook provider not yet implemented")

    def search_company(self, company_name: str) -> Optional[Dict]:
        """Search for company in PitchBook."""
        # TODO: Implement PitchBook search
        raise NotImplementedError("PitchBook provider not yet implemented")


# Global instance (default to public web)
default_provider = PublicWebProvider()
