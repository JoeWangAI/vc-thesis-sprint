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

## Roadmap

### Phase 1: Prototype ✅
- Core UI/UX
- Manual data entry
- Basic export

### Phase 2: AI Integration (Next)
- Claude API for company generation from thesis
- Automated funding research with web search
- Confidence scoring based on source triangulation

### Phase 3: Production Features
- Database persistence (PostgreSQL)
- User authentication
- Team collaboration
- CRM integrations (Affinity, Attio)
- Real-time data updates

## Contributing

This is a prototype built during an AI prototyping workshop. Contributions welcome.

## License

MIT

## Built With

- FastAPI
- HTMX
- Claude (design & prototyping assistance)
