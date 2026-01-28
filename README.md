# Thesis Sprint - VC Target Discovery Tool

A web application for VC investors to efficiently discover, validate, and manage target companies during thesis sprint research. Built with FastAPI, HTMX, and designed around evidence-based decision-making.

## Features

### Core Functionality
- **Sprint Management**: Create and manage multiple thesis sprints with customizable criteria
- **Company Discovery**: Browse, filter, and search companies with funding context
- **Confidence Scoring**: Visual indicators for data quality (High/Medium/Low/Conflict)
- **Claims & Evidence**: Track funding facts with source citations and timestamps
- **Shortlist Builder**: Quick actions to pursue, watch, or dismiss companies
- **Export Options**: Multiple formats (CSV, Investment Memo, Email Summary, CRM Import)

### Key Workflows
1. **Thesis Sprint Setup** → Define criteria (stage, geography, keywords)
2. **Company Validation** → Review funding context with evidence
3. **Shortlist Building** → Add rationale and share with team

### Design Principles
- **Evidence-first**: All key facts traceable to sources
- **Confidence over precision**: Explicit uncertainty markers
- **Progressive disclosure**: Quick triage → deep validation
- **Freshness indicators**: Clear data recency (Fresh/Recent/Stale/Old)

## Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: HTMX + Jinja2 templates
- **Styling**: Custom CSS (dark theme)
- **Data**: In-memory store (for prototype)

## Installation

### Local Development

```bash
# Clone the repository
git clone https://github.com/JoeWangAI/vc-thesis-sprint.git
cd vc-thesis-sprint

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
uvicorn main:app --reload
```

Visit http://localhost:8000

### Deploy to Render

This project is configured for one-click deployment to Render:

1. Fork this repository
2. Sign up at [render.com](https://render.com)
3. Click "New +" → "Web Service"
4. Connect your GitHub repository
5. Render will auto-detect settings from `render.yaml`
6. Click "Create Web Service"

Your app will be live at `https://your-app-name.onrender.com`

## Project Structure

```
├── main.py                  # FastAPI application & endpoints
├── models.py                # Pydantic data models
├── requirements.txt         # Python dependencies
├── render.yaml             # Render deployment config
├── services/
│   └── data_store.py       # In-memory data store with sample data
├── static/
│   └── styles.css          # Application styles
└── templates/
    ├── base.html           # Base template
    ├── index.html          # Main app layout
    ├── partials/           # HTMX partial templates
    │   ├── company_card.html
    │   ├── company_list.html
    │   ├── detail_panel.html
    │   ├── shortlist.html
    │   ├── sprint_header.html
    │   └── sprint_list.html
    └── components/
        └── modals.html     # Export modal & scripts
```

## Usage

### Creating a Sprint
1. Click "+ New Sprint" in the sidebar
2. Enter sprint name and thesis description
3. Sprint is created with default criteria
4. Use "Edit Criteria" to customize filters

### Validating Companies
1. Click on any company card to view details
2. Review funding history with freshness indicators
3. Examine claims with source citations
4. Add thesis fit notes in the text area
5. Use quick actions: Pursue / Watch / Dismiss

### Building a Shortlist
1. Click "✓ Pursue" or "◐ Watch" on company cards
2. Companies appear in sidebar shortlist
3. Click "Export Shortlist" to download:
   - **CSV**: For spreadsheets/CRM import
   - **Investment Memo**: Formatted markdown document
   - **Email Summary**: Quick digest for team

### Filtering & Sorting
- **View Tabs**: All / Needs Review / Conflicts / Shortlisted
- **Search**: Filter by company name or description
- **Sort**: By confidence, last raised, amount, or name

## Sample Data

The prototype includes 5 sample companies from the "AI Developer Tools" thesis:
- **Cursor**: High confidence, recently funded (Series B)
- **Codeium**: Has conflicting funding reports
- **Replit**: Medium confidence, data is stale
- **CodeWhisperer Labs**: Low confidence, stealth mode
- **Sourcegraph**: High confidence, but old funding data

## How It Works

### Discovery: AI-Powered Candidate Generation

When you click **"Generate Candidates"** on a sprint:

1. **LLM-Based Research**: Uses Claude API to generate 30-60 candidate companies matching your thesis
2. **Smart Filtering**: Companies evaluated based on:
   - Thesis description alignment
   - Stage preference (Series B+ by default, with Seed/A watchlist)
   - Geography and keyword criteria
   - Recent funding activity (last 18-24 months preferred)
3. **Fit Scoring**: Each company receives a 0-100 thesis fit score with 2-3 bullet-point rationales
4. **Automatic Bucketing**:
   - **Top Recommendations** (80%+ fit): High-confidence matches
   - **Worth a Look** (60-79% fit): Good candidates requiring validation
   - **Maybe** (<60% fit): Borderline companies with "next action" guidance

**Configuration**: Set stage preference, geography, keywords in sprint criteria (editable in UI)

### Validation: Funding Context with Confidence Scoring

Click **"Validate Funding"** on any company to:

1. **AI Research**: Claude researches recent funding information
2. **Structured Extraction**: Extracts last round date, type, amount, lead, valuation
3. **Source Attribution**: Links to sources with trust hierarchy (press release > SEC filing > business press > blog > social)
4. **Conflict Resolution**: Auto-selects value from highest-trust source when sources disagree, shows conflict badge (⚠)
5. **Confidence Labels**: High/Medium/Low based on source quality, agreement, recency

**Required Fields**:
- Last round date (month/year)
- Round type (Seed/Series A/B/C+)
- Amount
- Lead investor
- Post-money valuation (or estimate with basis: direct/secondary/implied/rumor/estimate)
- Source link (when available)

**Uncertainty Handling**: Estimates marked with confidence, missing data shown as "N/A" (never invented)

### Claims & Evidence System

Every funding fact backed by:
- **Claim**: Single assertion with sources
- **Source**: URL, source type, title, timestamp
- **Confidence**: High/Medium/Low based on source trust
- **Status**: Verified, Conflicting, or Unverified

Enables transparent decision-making and easy verification.

## Known Limitations (MVP)

### Data Sources
- **Public web only**: Uses Claude's knowledge base (cutoff: January 2025)
- **No paid APIs**: Crunchbase/PitchBook stubbed but not implemented
- **No real-time scraping**: Future enhancement

### Discovery
- **AI hallucination risk**: Companies validated for existence but may have inaccuracies
- **Bias toward well-known companies**: Less coverage of stealth/early-stage startups

### Validation
- **Knowledge cutoff**: Information may be stale for very recent rounds
- **Limited conflict resolution**: Simple source trust hierarchy (no manual override yet)

### Technical
- **In-memory storage**: Data lost on restart (no database)
- **Single-user**: No authentication or team collaboration
- **No CRM integration**: Manual export only (CSV/Word)

## Configuration

### Environment Variables

Set `ANTHROPIC_API_KEY` to enable AI features:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
uvicorn main:app --reload
```

### Sprint Criteria (Editable in UI)

- **Stage Focus**: Pre-Seed to Growth, All Stages
- **Geography**: US, US/Canada, North America, US/EU, Global, Europe, Asia, Latin America
- **Last Raise Filter**: Within 6/12/18/24/36 months, Any time

### Code Configuration

Edit [services/discovery.py](services/discovery.py):
- `target_count`: Companies to generate (default: 50)
- `demo_mode`: Use fixtures for testing

Edit [services/validation.py](services/validation.py):
- `SOURCE_TRUST_LEVELS`: Adjust trust hierarchy
- `cache_ttl`: Cache duration (default: 3600s)

## Roadmap

### Phase 1-4: MVP ✅
- AI-powered discovery with fit scoring
- Funding validation with source attribution
- Conflict detection and resolution
- Word memo and enhanced CSV export

### Phase 5: Production Polish (Next)
- Demo mode toggle in UI
- Stage filter enforcement
- Bulk validation
- Error handling improvements

### Phase 6: Production Features
- Database persistence (PostgreSQL)
- User authentication
- Real-time web scraping
- Crunchbase/PitchBook integration
- CRM integrations (Affinity, Attio)

## Contributing

This is a prototype built during an AI prototyping workshop. Contributions welcome.

## License

MIT

## Built With

- FastAPI
- HTMX
- Claude (design & prototyping assistance)
