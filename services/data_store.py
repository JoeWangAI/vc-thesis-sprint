"""
In-memory data store with sample data for the prototype.
"""
from datetime import datetime, timedelta
from models import (
    ThesisSprint, Company, FundingEvent, Claim, Source, ShortlistEntry,
    ConfidenceLevel, ClaimStatus, ShortlistStatus, FreshnessLevel
)


class DataStore:
    def __init__(self):
        self.sprints: dict[str, ThesisSprint] = {}
        self.companies: dict[str, Company] = {}
        self._init_sample_data()

    def _init_sample_data(self):
        """Initialize with sample data from the wireframe."""

        # Sample sources
        def make_source(id: str, url: str, stype: str, title: str, days_ago: int) -> Source:
            return Source(
                id=id,
                url=url,
                source_type=stype,
                title=title,
                timestamp=datetime.now() - timedelta(days=days_ago)
            )

        # Company 1: Cursor (High confidence)
        cursor_sources = [
            make_source("s1", "https://techcrunch.com/cursor-series-b", "news", "TechCrunch article", 11),
            make_source("s2", "https://cursor.sh/blog/series-b", "official", "Cursor blog post", 11),
            make_source("s3", "https://crunchbase.com/cursor", "database", "Crunchbase", 10),
            make_source("s4", "https://twitter.com/cursor", "social", "Cursor Twitter", 12),
        ]

        cursor = Company(
            id="cursor",
            name="Cursor",
            description="AI-first code editor built on VS Code, featuring native AI code generation, chat, and codebase understanding.",
            website="cursor.sh",
            location="San Francisco, CA",
            tags=["AI coding", "IDE", "Developer Tools"],
            stage="Series B",
            confidence=ConfidenceLevel.HIGH,
            funding_events=[
                FundingEvent(
                    id="cursor-b",
                    company_id="cursor",
                    round_type="Series B",
                    date=datetime(2025, 1, 16),
                    amount="$105M",
                    lead="Thrive Capital",
                    participants=["a16z", "Spark Capital"],
                    valuation_signal="~$2.5B (signal)",
                    freshness=FreshnessLevel.FRESH
                ),
                FundingEvent(
                    id="cursor-a",
                    company_id="cursor",
                    round_type="Series A",
                    date=datetime(2023, 10, 1),
                    amount="$20M",
                    lead="OpenAI Startup Fund",
                    participants=[],
                    freshness=FreshnessLevel.STALE
                ),
            ],
            claims=[
                Claim(
                    id="cursor-c1",
                    company_id="cursor",
                    statement="Cursor raised $105M Series B at ~$2.5B valuation led by Thrive Capital",
                    sources=cursor_sources[:3],
                    confidence=ConfidenceLevel.HIGH,
                    status=ClaimStatus.VERIFIED
                ),
                Claim(
                    id="cursor-c2",
                    company_id="cursor",
                    statement="Cursor has over 50,000 paid users",
                    sources=[cursor_sources[3]],
                    confidence=ConfidenceLevel.MEDIUM,
                    status=ClaimStatus.UNVERIFIED
                ),
            ],
            thesis_fit_notes="Strong fit: Direct AI coding tool, high growth trajectory, well-funded, strong technical team. Watch: Late stage (Series B) may limit upside. Competition from GitHub Copilot and emerging players.",
            source_count=4,
            updated=True
        )

        # Company 2: Codeium (Has conflicts)
        codeium = Company(
            id="codeium",
            name="Codeium",
            description="Free AI-powered code completion and search tool supporting 70+ languages with enterprise features.",
            website="codeium.com",
            location="Mountain View, CA",
            tags=["AI coding", "Code completion", "Enterprise"],
            stage="Series C",
            confidence=ConfidenceLevel.CONFLICT,
            funding_events=[
                FundingEvent(
                    id="codeium-c",
                    company_id="codeium",
                    round_type="Series C",
                    date=datetime(2024, 8, 15),
                    amount="$150M",
                    lead="Greenoaks",
                    participants=["General Catalyst", "Kleiner Perkins"],
                    freshness=FreshnessLevel.RECENT
                ),
            ],
            claims=[
                Claim(
                    id="codeium-c1",
                    company_id="codeium",
                    statement="Codeium raised $150M Series C led by Greenoaks",
                    sources=[make_source("cs1", "https://techcrunch.com/codeium", "news", "TechCrunch", 160)],
                    confidence=ConfidenceLevel.HIGH,
                    status=ClaimStatus.VERIFIED
                ),
                Claim(
                    id="codeium-c2",
                    company_id="codeium",
                    statement="Round size was $150M",
                    sources=[make_source("cs2", "https://crunchbase.com/codeium", "database", "Crunchbase", 158)],
                    confidence=ConfidenceLevel.MEDIUM,
                    status=ClaimStatus.CONFLICTING
                ),
                Claim(
                    id="codeium-c3",
                    company_id="codeium",
                    statement="Round size was $165M",
                    sources=[make_source("cs3", "https://pitchbook.com/codeium", "database", "PitchBook", 155)],
                    confidence=ConfidenceLevel.MEDIUM,
                    status=ClaimStatus.CONFLICTING
                ),
            ],
            source_count=6,
            updated=False
        )

        # Company 3: Replit (Medium confidence)
        replit = Company(
            id="replit",
            name="Replit",
            description="Browser-based IDE with AI coding assistant, multiplayer collaboration, and instant deployment.",
            website="replit.com",
            location="San Francisco, CA",
            tags=["AI coding", "Cloud IDE", "Education"],
            stage="Series B",
            confidence=ConfidenceLevel.MEDIUM,
            funding_events=[
                FundingEvent(
                    id="replit-b",
                    company_id="replit",
                    round_type="Series B",
                    date=datetime(2023, 4, 1),
                    amount="$97.4M",
                    lead="a16z",
                    participants=["Khosla Ventures", "Coatue"],
                    freshness=FreshnessLevel.STALE
                ),
            ],
            claims=[
                Claim(
                    id="replit-c1",
                    company_id="replit",
                    statement="Replit raised $97.4M Series B led by a16z in April 2023",
                    sources=[
                        make_source("rs1", "https://replit.com/blog/series-b", "official", "Replit Blog", 640),
                        make_source("rs2", "https://crunchbase.com/replit", "database", "Crunchbase", 635),
                    ],
                    confidence=ConfidenceLevel.HIGH,
                    status=ClaimStatus.VERIFIED
                ),
            ],
            source_count=3,
            updated=False
        )

        # Company 4: CodeWhisperer Labs (Low confidence - stealth)
        codewhisperer = Company(
            id="codewhisperer-labs",
            name="CodeWhisperer Labs",
            description="Stealth-mode AI debugging platform with automated root cause analysis.",
            website=None,
            location="Unknown",
            tags=["AI coding", "Debugging", "Stealth"],
            stage="Seed (rumored)",
            confidence=ConfidenceLevel.LOW,
            funding_events=[
                FundingEvent(
                    id="cwl-seed",
                    company_id="codewhisperer-labs",
                    round_type="Seed",
                    date=datetime(2024, 9, 1),
                    amount=None,
                    lead=None,
                    freshness=FreshnessLevel.RECENT
                ),
            ],
            claims=[
                Claim(
                    id="cwl-c1",
                    company_id="codewhisperer-labs",
                    statement="CodeWhisperer Labs raised a seed round in Q3 2024",
                    sources=[make_source("cwls1", "https://twitter.com/vcinsider", "social", "VC Insider tweet", 120)],
                    confidence=ConfidenceLevel.LOW,
                    status=ClaimStatus.UNVERIFIED
                ),
            ],
            source_count=1,
            updated=False
        )

        # Company 5: Sourcegraph (High confidence)
        sourcegraph = Company(
            id="sourcegraph",
            name="Sourcegraph",
            description="Code intelligence platform with universal code search and AI-powered coding assistant (Cody).",
            website="sourcegraph.com",
            location="San Francisco, CA",
            tags=["AI coding", "Code Search", "Enterprise"],
            stage="Series D",
            confidence=ConfidenceLevel.HIGH,
            funding_events=[
                FundingEvent(
                    id="sg-d",
                    company_id="sourcegraph",
                    round_type="Series D",
                    date=datetime(2021, 7, 1),
                    amount="$125M",
                    lead="Andreessen Horowitz",
                    participants=["Insight Partners", "Geodesic Capital"],
                    freshness=FreshnessLevel.OLD
                ),
            ],
            claims=[
                Claim(
                    id="sg-c1",
                    company_id="sourcegraph",
                    statement="Sourcegraph raised $125M Series D led by a16z in July 2021",
                    sources=[
                        make_source("sgs1", "https://sourcegraph.com/blog/series-d", "official", "Sourcegraph Blog", 1300),
                        make_source("sgs2", "https://techcrunch.com/sourcegraph", "news", "TechCrunch", 1298),
                        make_source("sgs3", "https://crunchbase.com/sourcegraph", "database", "Crunchbase", 1295),
                    ],
                    confidence=ConfidenceLevel.HIGH,
                    status=ClaimStatus.VERIFIED
                ),
            ],
            thesis_fit_notes=None,
            source_count=5,
            updated=False
        )

        # Store companies
        for company in [cursor, codeium, replit, codewhisperer, sourcegraph]:
            self.companies[company.id] = company

        # Create main sprint
        ai_dev_tools_sprint = ThesisSprint(
            id="ai-dev-tools",
            name="AI Developer Tools",
            description="Companies building AI-powered tools that augment software developers' productivity, including code generation, code review, debugging assistants, and intelligent IDE features. Focus on Series A–B stage with demonstrated traction.",
            keywords_include=["AI coding", "copilot", "code generation", "IDE"],
            keywords_exclude=["blockchain", "crypto"],
            stage_focus="Seed – Series B",
            geography="US, EU",
            last_raise_filter="Within 18 months",
            status="active",
            company_ids=["cursor", "codeium", "replit", "codewhisperer-labs", "sourcegraph"],
            shortlist=[
                ShortlistEntry(company_id="cursor", status=ShortlistStatus.PURSUE, added_at=datetime.now() - timedelta(days=2)),
                ShortlistEntry(company_id="codeium", status=ShortlistStatus.PURSUE, added_at=datetime.now() - timedelta(days=3)),
                ShortlistEntry(company_id="replit", status=ShortlistStatus.WATCH, added_at=datetime.now() - timedelta(days=1)),
                ShortlistEntry(company_id="sourcegraph", status=ShortlistStatus.PURSUE, added_at=datetime.now() - timedelta(days=4)),
            ]
        )

        # Additional sprints for sidebar
        climate_sprint = ThesisSprint(
            id="climate-fintech",
            name="Climate Fintech",
            description="Financial technology solutions focused on climate and sustainability.",
            keywords_include=["climate", "carbon", "ESG", "sustainability"],
            keywords_exclude=[],
            status="active",
            company_ids=[],
            shortlist=[]
        )

        healthcare_sprint = ThesisSprint(
            id="healthcare-llms",
            name="Healthcare LLMs",
            description="Large language models and AI applications in healthcare.",
            keywords_include=["healthcare", "medical AI", "clinical"],
            keywords_exclude=[],
            status="active",
            company_ids=[],
            shortlist=[]
        )

        # Store sprints
        self.sprints["ai-dev-tools"] = ai_dev_tools_sprint
        self.sprints["climate-fintech"] = climate_sprint
        self.sprints["healthcare-llms"] = healthcare_sprint

    def get_sprint(self, sprint_id: str) -> ThesisSprint | None:
        return self.sprints.get(sprint_id)

    def get_all_sprints(self) -> list[ThesisSprint]:
        return list(self.sprints.values())

    def get_company(self, company_id: str) -> Company | None:
        return self.companies.get(company_id)

    def get_companies_for_sprint(self, sprint_id: str) -> list[Company]:
        sprint = self.get_sprint(sprint_id)
        if not sprint:
            return []
        return [self.companies[cid] for cid in sprint.company_ids if cid in self.companies]

    def get_shortlist_for_sprint(self, sprint_id: str) -> list[tuple[Company, ShortlistEntry]]:
        sprint = self.get_sprint(sprint_id)
        if not sprint:
            return []
        result = []
        for entry in sprint.shortlist:
            company = self.companies.get(entry.company_id)
            if company:
                result.append((company, entry))
        return result

    def add_to_shortlist(self, sprint_id: str, company_id: str, status: ShortlistStatus) -> bool:
        sprint = self.get_sprint(sprint_id)
        if not sprint or company_id not in self.companies:
            return False

        # Remove existing entry if present
        sprint.shortlist = [e for e in sprint.shortlist if e.company_id != company_id]

        # Add new entry
        sprint.shortlist.append(ShortlistEntry(
            company_id=company_id,
            status=status,
            added_at=datetime.now()
        ))
        return True

    def remove_from_shortlist(self, sprint_id: str, company_id: str) -> bool:
        sprint = self.get_sprint(sprint_id)
        if not sprint:
            return False
        sprint.shortlist = [e for e in sprint.shortlist if e.company_id != company_id]
        return True

    def update_claim_status(self, claim_id: str, new_status: ClaimStatus) -> bool:
        for company in self.companies.values():
            for claim in company.claims:
                if claim.id == claim_id:
                    claim.status = new_status
                    return True
        return False

    def create_sprint(self, name: str, description: str) -> ThesisSprint:
        import uuid
        sprint_id = str(uuid.uuid4())[:8]
        sprint = ThesisSprint(
            id=sprint_id,
            name=name,
            description=description,
            company_ids=[],
            shortlist=[]
        )
        self.sprints[sprint_id] = sprint
        return sprint

    def delete_sprint(self, sprint_id: str) -> bool:
        """Delete a sprint. Returns True if deleted, False if not found."""
        if sprint_id in self.sprints:
            del self.sprints[sprint_id]
            return True
        return False

    def get_default_sprint_id(self) -> str:
        """Get a default sprint ID (first available sprint)."""
        if self.sprints:
            return next(iter(self.sprints.keys()))
        return "ai-dev-tools"  # Fallback to default


# Global singleton
store = DataStore()
