"""
Thesis Sprint - VC Target Discovery Tool
FastAPI application with HTMX frontend
"""
from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Optional
import csv
import io

from models import ShortlistStatus, ClaimStatus
from services.data_store import store

app = FastAPI(title="Thesis Sprint")

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def get_common_context(sprint_id: str = "ai-dev-tools"):
    """Get common template context."""
    current_sprint = store.get_sprint(sprint_id)
    companies = store.get_companies_for_sprint(sprint_id)
    shortlist = store.get_shortlist_for_sprint(sprint_id)
    sprints = store.get_all_sprints()

    return {
        "current_sprint": current_sprint,
        "companies": companies,
        "shortlist": shortlist,
        "sprints": sprints,
        "current_sprint_id": sprint_id,
    }


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main page - shows first sprint by default."""
    context = get_common_context("ai-dev-tools")
    context["request"] = request
    context["selected_company"] = None
    context["selected_company_id"] = None
    return templates.TemplateResponse("index.html", context)


@app.get("/sprints/{sprint_id}", response_class=HTMLResponse)
async def get_sprint(request: Request, sprint_id: str):
    """Load a sprint - returns full page for HTMX swap."""
    context = get_common_context(sprint_id)
    context["request"] = request
    context["selected_company"] = None
    context["selected_company_id"] = None
    return templates.TemplateResponse("index.html", context)


@app.get("/sprints/{sprint_id}/companies", response_class=HTMLResponse)
async def get_companies(
    request: Request,
    sprint_id: str,
    filter: Optional[str] = Query(None),
    sort: Optional[str] = Query("confidence"),
    q: Optional[str] = Query(None)
):
    """Get filtered/sorted company list."""
    companies = store.get_companies_for_sprint(sprint_id)
    current_sprint = store.get_sprint(sprint_id)
    shortlist_ids = {e.company_id for e in current_sprint.shortlist} if current_sprint else set()

    # Apply filters
    if filter == "needs_review":
        companies = [c for c in companies if c.confidence.value in ("low", "medium")]
    elif filter == "conflicts":
        companies = [c for c in companies if c.confidence.value == "conflict"]
    elif filter == "shortlisted":
        companies = [c for c in companies if c.id in shortlist_ids]

    # Apply search
    if q:
        q_lower = q.lower()
        companies = [c for c in companies if q_lower in c.name.lower() or q_lower in c.description.lower()]

    # Apply sorting
    if sort == "confidence":
        order = {"high": 0, "medium": 1, "conflict": 2, "low": 3}
        companies = sorted(companies, key=lambda c: order.get(c.confidence.value, 99))
    elif sort == "last_raised":
        companies = sorted(companies, key=lambda c: c.funding_events[0].date if c.funding_events else None, reverse=True)
    elif sort == "name":
        companies = sorted(companies, key=lambda c: c.name)

    context = {
        "request": request,
        "companies": companies,
        "current_sprint": current_sprint,
        "selected_company_id": None,
    }
    return templates.TemplateResponse("partials/company_list.html", context)


@app.get("/companies/{company_id}", response_class=HTMLResponse)
async def get_company_detail(request: Request, company_id: str):
    """Get company detail panel."""
    company = store.get_company(company_id)
    current_sprint = store.get_sprint("ai-dev-tools")  # TODO: track current sprint

    context = {
        "request": request,
        "company": company,
        "current_sprint": current_sprint,
    }
    return templates.TemplateResponse("partials/detail_panel.html", context)


@app.post("/sprints/{sprint_id}/shortlist/{company_id}", response_class=HTMLResponse)
async def add_to_shortlist(
    request: Request,
    sprint_id: str,
    company_id: str,
    status: str = Query("pursue")
):
    """Add company to shortlist."""
    status_enum = ShortlistStatus(status)
    store.add_to_shortlist(sprint_id, company_id, status_enum)

    shortlist = store.get_shortlist_for_sprint(sprint_id)
    context = {
        "request": request,
        "shortlist": shortlist,
    }
    return templates.TemplateResponse("partials/shortlist.html", context)


@app.delete("/sprints/{sprint_id}/shortlist/{company_id}", response_class=HTMLResponse)
async def remove_from_shortlist(request: Request, sprint_id: str, company_id: str):
    """Remove company from shortlist."""
    store.remove_from_shortlist(sprint_id, company_id)

    shortlist = store.get_shortlist_for_sprint(sprint_id)
    context = {
        "request": request,
        "shortlist": shortlist,
    }
    return templates.TemplateResponse("partials/shortlist.html", context)


@app.post("/claims/{claim_id}/verify", response_class=HTMLResponse)
async def verify_claim(request: Request, claim_id: str):
    """Mark a claim as verified."""
    store.update_claim_status(claim_id, ClaimStatus.VERIFIED)

    # Find the company for this claim to return updated detail panel
    for company in store.companies.values():
        for claim in company.claims:
            if claim.id == claim_id:
                current_sprint = store.get_sprint("ai-dev-tools")
                context = {
                    "request": request,
                    "company": company,
                    "current_sprint": current_sprint,
                }
                return templates.TemplateResponse("partials/detail_panel.html", context)

    return HTMLResponse(status_code=404)


@app.post("/companies/{company_id}/notes", response_class=HTMLResponse)
async def update_notes(request: Request, company_id: str):
    """Update thesis fit notes for a company."""
    form = await request.form()
    notes = form.get("notes", "")

    company = store.get_company(company_id)
    if company:
        company.thesis_fit_notes = notes

    return HTMLResponse(status_code=204)


@app.get("/sprints/new", response_class=HTMLResponse)
async def new_sprint_form(request: Request):
    """Show new sprint form modal."""
    return HTMLResponse("""
    <div class="modal-overlay active" id="new-sprint-modal">
        <div class="modal">
            <div class="modal-header">
                <span class="modal-title">Create New Sprint</span>
                <button class="close-btn" onclick="document.getElementById('new-sprint-modal').remove()">×</button>
            </div>
            <form hx-post="/sprints" hx-target="#app" hx-swap="innerHTML">
                <div class="modal-content">
                    <div class="new-sprint-form">
                        <div class="form-group">
                            <label class="form-label">Sprint Name</label>
                            <input type="text" name="name" class="form-input" placeholder="e.g., AI Developer Tools" required>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Thesis Description</label>
                            <textarea name="description" class="notes-textarea" placeholder="Describe the thesis and target company characteristics..." required></textarea>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" onclick="document.getElementById('new-sprint-modal').remove()">Cancel</button>
                    <button type="submit" class="btn btn-primary">Create Sprint</button>
                </div>
            </form>
        </div>
    </div>
    """)


@app.post("/sprints", response_class=HTMLResponse)
async def create_sprint(request: Request):
    """Create a new sprint."""
    form = await request.form()
    name = form.get("name", "New Sprint")
    description = form.get("description", "")

    new_sprint = store.create_sprint(name, description)

    context = get_common_context(new_sprint.id)
    context["request"] = request
    context["selected_company"] = None
    context["selected_company_id"] = None
    return templates.TemplateResponse("index.html", context)


@app.get("/export")
async def export_shortlist(format: str = Query("csv")):
    """Export shortlist as CSV."""
    sprint = store.get_sprint("ai-dev-tools")
    shortlist = store.get_shortlist_for_sprint("ai-dev-tools")

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            "Company", "Status", "Stage", "Last Round", "Date", "Amount",
            "Lead Investor", "Confidence", "Notes", "Sources"
        ])

        # Data
        for company, entry in shortlist:
            latest = company.funding_events[0] if company.funding_events else None
            writer.writerow([
                company.name,
                entry.status.value,
                company.stage or "",
                latest.round_type if latest else "",
                latest.date.strftime("%Y-%m-%d") if latest else "",
                latest.amount or "" if latest else "",
                latest.lead or "" if latest else "",
                company.confidence.value,
                company.thesis_fit_notes or "",
                company.source_count
            ])

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=thesis-sprint-shortlist.csv"}
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
