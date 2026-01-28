"""
Discovery service - Generate candidate companies from thesis description.
Uses Claude API to generate relevant companies with fit scoring and rationale.
"""
import os
from typing import List, Dict, Optional
import json
import uuid
from anthropic import Anthropic
from models import Company, Confidence, StageEstimate, ConfidenceLevel


class DiscoveryService:
    """Service for discovering candidate companies based on thesis criteria."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize with optional API key (falls back to env var)."""
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client = Anthropic(api_key=self.api_key) if self.api_key else None

    def generate_candidates(
        self,
        thesis_description: str,
        keywords_include: List[str] = None,
        keywords_exclude: List[str] = None,
        stage_preference: str = "Series B+",
        geography: str = "US, EU",
        target_count: int = 50,
        demo_mode: bool = False
    ) -> List[Company]:
        """
        Generate candidate companies matching the thesis.

        Args:
            thesis_description: The thesis description
            keywords_include: Keywords to include
            keywords_exclude: Keywords to exclude
            stage_preference: Preferred funding stage (default: Series B+)
            geography: Geographic focus
            target_count: Target number of candidates (30-60 recommended)
            demo_mode: If True, return demo fixtures

        Returns:
            List of Company objects with fit_score, fit_reasons, stage_estimate
        """
        if demo_mode or not self.client:
            return self._generate_demo_candidates(thesis_description, target_count)

        try:
            return self._generate_with_claude(
                thesis_description,
                keywords_include or [],
                keywords_exclude or [],
                stage_preference,
                geography,
                target_count
            )
        except Exception as e:
            print(f"Discovery error: {e}")
            return self._generate_demo_candidates(thesis_description, target_count)

    def _generate_with_claude(
        self,
        thesis: str,
        include_kw: List[str],
        exclude_kw: List[str],
        stage: str,
        geo: str,
        count: int
    ) -> List[Company]:
        """Generate candidates using Claude API."""
        if not self.client:
            return []

        # Build prompt for Claude
        prompt = self._build_discovery_prompt(thesis, include_kw, exclude_kw, stage, geo, count)

        try:
            # Call Claude API
            response = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=8000,
                temperature=0.3,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            # Parse response into Company objects
            companies = self._parse_claude_response(response.content[0].text)
            return companies

        except Exception as e:
            print(f"Claude API error: {e}")
            return []

    def _build_discovery_prompt(
        self,
        thesis: str,
        include_kw: List[str],
        exclude_kw: List[str],
        stage: str,
        geo: str,
        count: int
    ) -> str:
        """Build discovery prompt for Claude."""
        kw_include_str = ", ".join(include_kw) if include_kw else "none specified"
        kw_exclude_str = ", ".join(exclude_kw) if exclude_kw else "none"

        return f"""You are a senior VC researcher. Generate a list of {count} companies that match this investment thesis.

THESIS:
{thesis}

CRITERIA:
- Stage preference: {stage} (but include promising earlier-stage companies in separate section)
- Geography: {geo}
- Include keywords: {kw_include_str}
- Exclude keywords: {kw_exclude_str}

REQUIREMENTS:
1. Generate exactly {count} companies (aim for 50-60 if not specified)
2. Prioritize growth-stage (Series B+) companies but include notable Seed/A companies
3. Focus on B2B/enterprise software and tech-enabled services
4. For each company, provide:
   - Company name
   - Domain (if publicly known, or "unknown")
   - 1-line description (15-25 words)
   - Stage estimate (Seed/Series A/Series B/Series C+/Growth)
   - Fit score (0-100, where 100 is perfect thesis fit)
   - 2-3 brief reasons why it fits the thesis (bullet points, 10-15 words each)
   - Next action for borderline fits (what to validate next)

5. Ensure companies are real, findable businesses (not hypothetical)
6. Prefer companies with recent funding activity (last 18-24 months)
7. Include a mix of well-known and emerging players

OUTPUT FORMAT (JSON):
Return a JSON array of company objects with this structure:

[
  {{
    "name": "Company Name",
    "domain": "company.com",
    "description": "Brief description of what they do",
    "stage": "Series B",
    "fit_score": 85,
    "fit_reasons": [
      "Reason 1",
      "Reason 2",
      "Reason 3"
    ],
    "tags": ["tag1", "tag2", "tag3"],
    "next_action": "Verify enterprise focus vs SMB" // only for borderline fits (score < 70)
  }},
  ...
]

IMPORTANT:
- Return ONLY the JSON array, no markdown formatting or explanation
- Ensure valid JSON syntax
- All companies must be real businesses you're confident exist
- Vary the fit scores realistically (not all 90+)
"""

    def _parse_claude_response(self, response_text: str) -> List[Company]:
        """Parse Claude's JSON response into Company objects."""
        try:
            # Extract JSON from response (handle markdown code blocks if present)
            json_text = response_text.strip()
            if json_text.startswith("```"):
                # Remove markdown code block markers
                lines = json_text.split("\n")
                json_text = "\n".join(lines[1:-1]) if len(lines) > 2 else json_text
                json_text = json_text.replace("```json", "").replace("```", "").strip()

            # Parse JSON
            companies_data = json.loads(json_text)

            # Convert to Company objects
            companies = []
            for data in companies_data:
                # Determine confidence level based on fit score
                fit_score = data.get("fit_score", 50)
                if fit_score >= 80:
                    conf_level = ConfidenceLevel.HIGH
                elif fit_score >= 60:
                    conf_level = ConfidenceLevel.MEDIUM
                else:
                    conf_level = ConfidenceLevel.LOW

                # Create stage estimate
                stage_est = StageEstimate(
                    stage=data.get("stage", "Unknown"),
                    confidence=conf_level,
                    basis="AI-generated estimate"
                )

                company = Company(
                    id=str(uuid.uuid4()),
                    name=data.get("name", "Unknown"),
                    description=data.get("description", ""),
                    website=data.get("domain") if data.get("domain") != "unknown" else None,
                    tags=data.get("tags", []),
                    stage=data.get("stage", "Unknown"),
                    confidence=conf_level,
                    fit_score=fit_score,
                    fit_reasons=data.get("fit_reasons", []),
                    stage_estimate=stage_est,
                    next_action=data.get("next_action"),
                    validation_status="pending"
                )
                companies.append(company)

            return companies

        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            print(f"Response text: {response_text[:500]}")
            return []
        except Exception as e:
            print(f"Error parsing Claude response: {e}")
            return []

    def _generate_demo_candidates(self, thesis: str, count: int) -> List[Company]:
        """Generate demo candidates as fallback."""
        # Return empty for now - will use existing fixtures in data_store
        return []

    def rank_candidates(
        self,
        companies: List[Company],
        thesis_description: str
    ) -> Dict[str, List[Company]]:
        """
        Rank candidates into buckets: Recommended (top 10), Worth a look, Maybe.

        Args:
            companies: List of companies with fit_score
            thesis_description: Original thesis for context

        Returns:
            Dict with keys: "recommended", "worth_a_look", "maybe"
        """
        # Sort by fit_score (assumes companies have a fit_score attribute)
        sorted_companies = sorted(
            companies,
            key=lambda c: getattr(c, 'fit_score', 0),
            reverse=True
        )

        # Bucket by fit score thresholds
        recommended = []
        worth_a_look = []
        maybe = []

        for company in sorted_companies:
            score = getattr(company, 'fit_score', 0)
            if score >= 80 and len(recommended) < 10:
                recommended.append(company)
            elif score >= 60:
                worth_a_look.append(company)
            else:
                maybe.append(company)

        return {
            "recommended": recommended,
            "worth_a_look": worth_a_look,
            "maybe": maybe
        }


# Global instance
discovery_service = DiscoveryService()
