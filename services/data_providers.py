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


class BraveSearchProvider(DataProvider):
    """
    Brave Search provider for real-time web search results.
    Free tier: 2000 queries/month. Provides up-to-date funding information.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize with Brave Search API key.

        Args:
            api_key: Brave Search API key (or use BRAVE_SEARCH_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("BRAVE_SEARCH_API_KEY")
        self.client = httpx.Client(timeout=15.0)
        self.base_url = "https://api.search.brave.com/res/v1/web/search"

        # Claude for parsing search results
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        self.anthropic = Anthropic(api_key=anthropic_key) if anthropic_key else None

    def fetch_funding_claims(
        self,
        company_name: str,
        domain: Optional[str] = None
    ) -> List[Claim]:
        """
        Fetch funding claims using Brave Search + Claude analysis.

        Strategy:
        1. Search Brave for recent funding news about the company
        2. Extract relevant snippets and URLs
        3. Use Claude to analyze and structure the information
        4. Return claims with source attribution

        Args:
            company_name: Company name
            domain: Optional company domain

        Returns:
            List of Claim objects with sources
        """
        if not self.api_key:
            print("No Brave Search API key - falling back to Claude knowledge")
            return self._fallback_to_claude(company_name, domain)

        try:
            # Search for funding information
            search_results = self._search_brave(company_name, domain)

            if not search_results:
                print(f"No Brave search results for {company_name}")
                return self._fallback_to_claude(company_name, domain)

            # Use Claude to analyze search results and extract funding info
            claims = self._analyze_with_claude(company_name, search_results)
            return claims

        except Exception as e:
            print(f"Brave Search error for {company_name}: {e}")
            return self._fallback_to_claude(company_name, domain)

    def search_company(self, company_name: str) -> Optional[Dict]:
        """
        Search for basic company info using Brave Search.

        Args:
            company_name: Company name

        Returns:
            Dict with name, domain, description
        """
        if not self.api_key:
            return None

        try:
            results = self._search_brave(company_name, query_type="company_info")
            if results:
                # Extract basic info from first result
                first_result = results[0]
                return {
                    "name": company_name,
                    "domain": first_result.get("url", "").replace("https://", "").replace("http://", "").split("/")[0],
                    "description": first_result.get("description", "")
                }
        except Exception as e:
            print(f"Brave company search error: {e}")

        return None

    def _search_brave(
        self,
        company_name: str,
        domain: Optional[str] = None,
        query_type: str = "funding"
    ) -> List[Dict]:
        """
        Perform Brave Search API call.

        Args:
            company_name: Company name
            domain: Optional domain to narrow search
            query_type: "funding" or "company_info"

        Returns:
            List of search result dicts
        """
        # Build search query
        if query_type == "funding":
            query = f'"{company_name}" funding round Series valuation 2024 2025 2026'
            if domain:
                query += f' site:{domain}'
        else:
            query = f'"{company_name}" company'

        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self.api_key
        }

        params = {
            "q": query,
            "count": 10,  # Get top 10 results
            "freshness": "2024-01-01",  # Only recent results
        }

        response = self.client.get(
            self.base_url,
            headers=headers,
            params=params
        )
        response.raise_for_status()

        data = response.json()

        # Extract web results
        web_results = data.get("web", {}).get("results", [])

        # Format results
        results = []
        for result in web_results:
            results.append({
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "description": result.get("description", ""),
                "age": result.get("age", "")  # How recent the page is
            })

        return results

    def _analyze_with_claude(
        self,
        company_name: str,
        search_results: List[Dict]
    ) -> List[Claim]:
        """
        Use Claude to analyze search results and extract funding information.

        Args:
            company_name: Company name
            search_results: List of search result dicts from Brave

        Returns:
            List of Claim objects
        """
        if not self.anthropic:
            return []

        # Format search results for Claude
        results_text = "\n\n".join([
            f"**{r['title']}**\nURL: {r['url']}\n{r['description']}"
            for r in search_results[:5]  # Analyze top 5 results
        ])

        prompt = f"""Analyze these recent web search results about {company_name}'s funding and extract structured information.

SEARCH RESULTS:
{results_text}

Based on these search results, provide the most recent funding information in JSON format:

{{
  "last_round_date": "YYYY-MM" or null,
  "last_round_type": "Seed/Series A/Series B/Series C/Series D/Series E/etc" or null,
  "amount": "$XM" or null,
  "lead_investor": "Investor name" or null,
  "post_money_valuation": "Valuation or estimate" or null,
  "valuation_basis": "direct/secondary/implied/rumor/estimate",
  "sources": [
    {{
      "url": "exact URL from search results above",
      "source_type": "company_press/sec_filing/business_press/investor_blog/wikipedia/social/unknown",
      "title": "Article title from above",
      "confidence": "high/medium/low"
    }}
  ],
  "overall_confidence": "high/medium/low",
  "notes": "Any important context or uncertainties"
}}

IMPORTANT:
- Only extract information explicitly mentioned in the search results
- Use ONLY the URLs provided in the search results above
- Mark confidence as "low" if information is vague or from unreliable sources
- If search results don't contain funding info, return all fields as null
- Current date context: We're in 2026, so 2025-2026 funding is very recent

Return ONLY the JSON, no markdown formatting."""

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

            # Parse JSON response
            import json
            json_text = response.content[0].text.strip()

            # Remove markdown code blocks if present
            if json_text.startswith("```"):
                lines = json_text.split("\n")
                json_text = "\n".join(lines[1:-1]) if len(lines) > 2 else json_text
                json_text = json_text.replace("```json", "").replace("```", "").strip()

            data = json.loads(json_text)

            # Convert to Claim objects
            claims = []

            # Create main funding claim if we have data
            if data.get("last_round_type"):
                sources = [
                    Source(
                        id=str(uuid.uuid4()),
                        url=s["url"],
                        source_type=s["source_type"],
                        title=s["title"],
                        timestamp=datetime.now()
                    )
                    for s in data.get("sources", [])
                ]

                confidence_map = {
                    "high": ConfidenceLevel.HIGH,
                    "medium": ConfidenceLevel.MEDIUM,
                    "low": ConfidenceLevel.LOW
                }

                statement = f"Raised {data.get('amount', 'undisclosed')} {data['last_round_type']}"
                if data.get("last_round_date"):
                    statement += f" in {data['last_round_date']}"
                if data.get("lead_investor"):
                    statement += f" led by {data['lead_investor']}"

                claim = Claim(
                    id=str(uuid.uuid4()),
                    company_id="",  # Will be set by caller
                    statement=statement,
                    sources=sources,
                    confidence=confidence_map.get(data.get("overall_confidence", "medium"), ConfidenceLevel.MEDIUM),
                    status=ClaimStatus.VERIFIED if sources else ClaimStatus.UNVERIFIED
                )

                claims.append(claim)

            return claims

        except Exception as e:
            print(f"Claude analysis error: {e}")
            return []

    def _fallback_to_claude(
        self,
        company_name: str,
        domain: Optional[str]
    ) -> List[Claim]:
        """
        Fallback to Claude's built-in knowledge if Brave Search fails.

        Args:
            company_name: Company name
            domain: Optional domain

        Returns:
            List of Claim objects
        """
        if not self.anthropic:
            return []

        # Use the existing PublicWebProvider logic as fallback
        fallback = PublicWebProvider()
        return fallback.fetch_funding_claims(company_name, domain)

    def __del__(self):
        """Clean up HTTP client."""
        try:
            self.client.close()
        except:
            pass


class PerplexityProvider(DataProvider):
    """
    Perplexity API provider for AI-powered search with real-time data.
    Purpose-built for AI inference use cases. More expensive but higher quality.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize with Perplexity API key.

        Args:
            api_key: Perplexity API key (or use PERPLEXITY_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY")
        self.client = httpx.Client(timeout=30.0)  # Perplexity can take longer
        self.base_url = "https://api.perplexity.ai/chat/completions"

    def fetch_funding_claims(
        self,
        company_name: str,
        domain: Optional[str] = None
    ) -> List[Claim]:
        """
        Fetch funding claims using Perplexity's AI search.

        Strategy:
        1. Ask Perplexity to research the company's funding
        2. Perplexity searches the web and provides structured response
        3. Parse response into Claim objects
        4. Return claims with source attribution

        Args:
            company_name: Company name
            domain: Optional company domain

        Returns:
            List of Claim objects with sources
        """
        if not self.api_key:
            print("No Perplexity API key - cannot fetch funding claims")
            return []

        try:
            # Query Perplexity for funding information
            funding_data = self._query_perplexity(company_name, domain)

            if not funding_data:
                print(f"No funding data returned from Perplexity for {company_name}")
                return []

            # Convert to Claim objects
            claims = self._parse_funding_data(funding_data)
            return claims

        except Exception as e:
            print(f"Perplexity API error for {company_name}: {e}")
            return []

    def search_company(self, company_name: str) -> Optional[Dict]:
        """
        Search for basic company info using Perplexity.

        Args:
            company_name: Company name

        Returns:
            Dict with name, domain, description
        """
        if not self.api_key:
            return None

        try:
            prompt = f"What is {company_name}? Provide: company domain, and a one-sentence description."

            response = self._call_perplexity_api(prompt, return_citations=False)

            if response:
                # Simple parsing of the response
                # This is a basic implementation - could be improved
                return {
                    "name": company_name,
                    "domain": "unknown",  # Would need to parse from response
                    "description": response.get("content", "")
                }
        except Exception as e:
            print(f"Perplexity company search error: {e}")

        return None

    def _query_perplexity(
        self,
        company_name: str,
        domain: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Query Perplexity API for funding information.

        Args:
            company_name: Company name
            domain: Optional domain

        Returns:
            Dict with funding information and citations
        """
        # Build research prompt
        domain_hint = f" (domain: {domain})" if domain else ""
        prompt = f"""Research the most recent funding information for {company_name}{domain_hint}.

Provide the following information in JSON format:

{{
  "last_round_date": "YYYY-MM" or null,
  "last_round_type": "Seed/Series A/Series B/Series C/Series D/Series E/Growth/etc" or null,
  "amount": "$XM" or null (e.g., "$50M"),
  "lead_investor": "Investor name" or null,
  "post_money_valuation": "Valuation or estimate" or null,
  "valuation_basis": "direct/secondary/implied/rumor/estimate",
  "sources": [
    {{
      "url": "source URL",
      "title": "Article or source title"
    }}
  ],
  "overall_confidence": "high/medium/low",
  "notes": "Any important context or caveats"
}}

IMPORTANT:
- Focus on the MOST RECENT funding round (2024-2026 preferred)
- Only include information from reliable sources
- Include source URLs for verification
- Mark confidence as "low" if information is uncertain
- Current date context: We're in 2026

Return ONLY the JSON, no additional text."""

        try:
            response = self._call_perplexity_api(prompt, return_citations=True)
            return response

        except Exception as e:
            print(f"Perplexity query error: {e}")
            return None

    def _call_perplexity_api(
        self,
        prompt: str,
        return_citations: bool = True
    ) -> Optional[Dict]:
        """
        Make API call to Perplexity.

        Args:
            prompt: Query prompt
            return_citations: Whether to include citations

        Returns:
            Response dict with content and optional citations
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # Use sonar model for real-time search
        # sonar models have internet access and return citations
        model = "sonar" if return_citations else "sonar-pro"

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a precise research assistant. Provide accurate, well-sourced information in the requested format."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1,
            "return_citations": return_citations,
            "return_images": False
        }

        response = self.client.post(
            self.base_url,
            headers=headers,
            json=payload
        )
        response.raise_for_status()

        data = response.json()

        # Extract content and citations
        result = {
            "content": data["choices"][0]["message"]["content"],
            "citations": data.get("citations", []) if return_citations else []
        }

        return result

    def _parse_funding_data(self, funding_data: Dict) -> List[Claim]:
        """
        Parse Perplexity response into Claim objects.

        Args:
            funding_data: Response from Perplexity with content and citations

        Returns:
            List of Claim objects
        """
        import json

        content = funding_data.get("content", "")
        citations = funding_data.get("citations", [])

        # Remove markdown code blocks if present
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1]) if len(lines) > 2 else content
            content = content.replace("```json", "").replace("```", "").strip()

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            print(f"Failed to parse Perplexity response as JSON: {e}")
            return []

        claims = []

        # Create main funding claim if we have data
        if data.get("last_round_type"):
            # Create Source objects from citations and sources in response
            sources = []

            # Add sources from the JSON response
            for source_data in data.get("sources", []):
                sources.append(Source(
                    id=str(uuid.uuid4()),
                    url=source_data.get("url", ""),
                    source_type=self._classify_source_type(source_data.get("url", "")),
                    title=source_data.get("title", "Unknown source"),
                    timestamp=datetime.now()
                ))

            # Add citations from Perplexity
            for citation in citations:
                sources.append(Source(
                    id=str(uuid.uuid4()),
                    url=citation,
                    source_type=self._classify_source_type(citation),
                    title="Perplexity citation",
                    timestamp=datetime.now()
                ))

            # Map confidence
            confidence_map = {
                "high": ConfidenceLevel.HIGH,
                "medium": ConfidenceLevel.MEDIUM,
                "low": ConfidenceLevel.LOW
            }

            # Build claim statement
            statement = f"Raised {data.get('amount', 'undisclosed')} {data['last_round_type']}"
            if data.get("last_round_date"):
                statement += f" in {data['last_round_date']}"
            if data.get("lead_investor"):
                statement += f" led by {data['lead_investor']}"

            claim = Claim(
                id=str(uuid.uuid4()),
                company_id="",  # Will be set by caller
                statement=statement,
                sources=sources,
                confidence=confidence_map.get(data.get("overall_confidence", "medium"), ConfidenceLevel.MEDIUM),
                status=ClaimStatus.VERIFIED if sources else ClaimStatus.UNVERIFIED
            )

            claims.append(claim)

        return claims

    def _classify_source_type(self, url: str) -> str:
        """
        Classify source type based on URL.

        Args:
            url: Source URL

        Returns:
            Source type string
        """
        url_lower = url.lower()

        if any(domain in url_lower for domain in ["techcrunch.com", "bloomberg.com", "reuters.com", "wsj.com"]):
            return "business_press"
        elif any(domain in url_lower for domain in [".gov", "sec.gov"]):
            return "sec_filing"
        elif "crunchbase.com" in url_lower:
            return "crunchbase"
        elif "wikipedia.org" in url_lower:
            return "wikipedia"
        elif any(domain in url_lower for domain in ["twitter.com", "linkedin.com", "x.com"]):
            return "social"
        else:
            return "unknown"

    def __del__(self):
        """Clean up HTTP client."""
        try:
            self.client.close()
        except:
            pass


# Global instances
default_provider = PublicWebProvider()
brave_search_provider = None  # Initialized on demand
perplexity_provider = None  # Initialized on demand


def get_data_provider() -> DataProvider:
    """
    Get the appropriate data provider based on environment configuration.

    Checks DATA_PROVIDER env var and returns the corresponding provider:
    - "perplexity": PerplexityProvider (requires PERPLEXITY_API_KEY) - RECOMMENDED
    - "brave_search": BraveSearchProvider (requires BRAVE_SEARCH_API_KEY)
    - "crunchbase": CrunchbaseProvider (requires CRUNCHBASE_API_KEY)
    - "pitchbook": PitchBookProvider (requires PITCHBOOK_API_KEY)
    - "public_web" or default: PublicWebProvider (uses Claude's knowledge)

    Returns:
        DataProvider instance
    """
    global brave_search_provider, perplexity_provider

    provider_type = os.getenv("DATA_PROVIDER", "public_web").lower()

    if provider_type == "perplexity":
        if perplexity_provider is None:
            perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")
            if not perplexity_api_key:
                print("Warning: DATA_PROVIDER=perplexity but no PERPLEXITY_API_KEY found. Falling back to public_web.")
                return default_provider
            perplexity_provider = PerplexityProvider(api_key=perplexity_api_key)
        return perplexity_provider

    elif provider_type == "brave_search":
        if brave_search_provider is None:
            brave_api_key = os.getenv("BRAVE_SEARCH_API_KEY")
            if not brave_api_key:
                print("Warning: DATA_PROVIDER=brave_search but no BRAVE_SEARCH_API_KEY found. Falling back to public_web.")
                return default_provider
            brave_search_provider = BraveSearchProvider(api_key=brave_api_key)
        return brave_search_provider

    elif provider_type == "crunchbase":
        crunchbase_key = os.getenv("CRUNCHBASE_API_KEY")
        if not crunchbase_key:
            print("Warning: DATA_PROVIDER=crunchbase but no CRUNCHBASE_API_KEY found. Falling back to public_web.")
            return default_provider
        return CrunchbaseProvider(api_key=crunchbase_key)

    elif provider_type == "pitchbook":
        pitchbook_key = os.getenv("PITCHBOOK_API_KEY")
        if not pitchbook_key:
            print("Warning: DATA_PROVIDER=pitchbook but no PITCHBOOK_API_KEY found. Falling back to public_web.")
            return default_provider
        return PitchBookProvider(api_key=pitchbook_key)

    else:
        # Default to public web provider
        return default_provider
