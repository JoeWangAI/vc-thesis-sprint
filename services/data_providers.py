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
from models import Claim, Source


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

    def fetch_funding_claims(
        self,
        company_name: str,
        domain: Optional[str] = None
    ) -> List[Claim]:
        """
        Fetch funding claims from public web sources.

        Strategy:
        1. Search for "[company name] funding round"
        2. Extract structured data from search results and pages
        3. Return claims with source attribution

        Args:
            company_name: Company name
            domain: Optional company domain (helps with search precision)

        Returns:
            List of Claim objects
        """
        # TODO: Implement web scraping logic
        # For Phase 1, return empty list (will implement in Phase 3)
        return []

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
