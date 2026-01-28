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
async def get_company_detail(request: Request, company_id: str, sprint_id: str = Query("ai-dev-tools")):
    """Get company detail panel."""
    company = store.get_company(company_id)
    current_sprint = store.get_sprint(sprint_id)

    # Check if company is in shortlist
    is_shortlisted = False
    if current_sprint:
        is_shortlisted = any(e.company_id == company_id for e in current_sprint.shortlist)

    context = {
        "request": request,
        "company": company,
        "current_sprint": current_sprint,
        "is_shortlisted": is_shortlisted,
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


@app.get("/sprints/{sprint_id}/edit", response_class=HTMLResponse)
async def edit_sprint_form(request: Request, sprint_id: str):
    """Show edit sprint criteria modal."""
    sprint = store.get_sprint(sprint_id)
    return HTMLResponse(f"""
    <div class="modal-overlay active" id="edit-criteria-modal">
        <div class="modal">
            <div class="modal-header">
                <span class="modal-title">Edit Criteria - {sprint.name}</span>
                <button class="close-btn" onclick="document.getElementById('edit-criteria-modal').remove()">×</button>
            </div>
            <form hx-post="/sprints/{sprint_id}/update" hx-target="#sprint-header" hx-swap="innerHTML">
                <div class="modal-content">
                    <div class="new-sprint-form">
                        <div class="form-group">
                            <label class="form-label">Thesis Description</label>
                            <textarea name="description" class="notes-textarea" required>{sprint.description}</textarea>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Stage Focus</label>
                            <input type="text" name="stage_focus" class="form-input" value="{sprint.stage_focus}">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Geography</label>
                            <input type="text" name="geography" class="form-input" value="{sprint.geography}">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Last Raise Filter</label>
                            <input type="text" name="last_raise_filter" class="form-input" value="{sprint.last_raise_filter}">
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" onclick="document.getElementById('edit-criteria-modal').remove()">Cancel</button>
                    <button type="submit" class="btn btn-primary" onclick="document.getElementById('edit-criteria-modal').remove()">Save Changes</button>
                </div>
            </form>
        </div>
    </div>
    """)


@app.post("/sprints/{sprint_id}/update", response_class=HTMLResponse)
async def update_sprint(request: Request, sprint_id: str):
    """Update sprint criteria."""
    form = await request.form()
    sprint = store.get_sprint(sprint_id)

    if sprint:
        sprint.description = form.get("description", sprint.description)
        sprint.stage_focus = form.get("stage_focus", sprint.stage_focus)
        sprint.geography = form.get("geography", sprint.geography)
        sprint.last_raise_filter = form.get("last_raise_filter", sprint.last_raise_filter)

    context = {
        "request": request,
        "current_sprint": sprint,
    }
    return templates.TemplateResponse("partials/sprint_header.html", context)


@app.get("/export")
async def export_shortlist(format: str = Query("csv"), sprint_id: str = Query("ai-dev-tools")):
    """Export shortlist in various formats."""
    sprint = store.get_sprint(sprint_id)
    shortlist = store.get_shortlist_for_sprint(sprint_id)

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

    elif format == "memo":
        # Generate investment memo
        output = io.StringIO()
        output.write(f"# Investment Memo: {sprint.name}\n\n")
        output.write(f"## Thesis\n{sprint.description}\n\n")
        output.write(f"## Shortlisted Companies ({len(shortlist)})\n\n")

        for company, entry in shortlist:
            output.write(f"### {company.name}\n")
            output.write(f"**Status:** {entry.status.value.capitalize()}\n\n")
            output.write(f"{company.description}\n\n")

            if company.funding_events:
                latest = company.funding_events[0]
                output.write(f"**Latest Funding:** {latest.round_type}")
                if latest.amount:
                    output.write(f" - {latest.amount}")
                if latest.lead:
                    output.write(f" led by {latest.lead}")
                output.write(f" ({latest.date.strftime('%B %Y')})\n\n")

            if company.thesis_fit_notes:
                output.write(f"**Notes:** {company.thesis_fit_notes}\n\n")

            output.write("---\n\n")

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename=investment-memo.md"}
        )

    elif format == "email":
        # Generate email summary
        output = io.StringIO()
        output.write(f"Subject: {sprint.name} - Shortlist Summary\n\n")
        output.write(f"Thesis: {sprint.description}\n\n")
        output.write(f"We've identified {len(shortlist)} companies worth pursuing:\n\n")

        for company, entry in shortlist:
            output.write(f"• {company.name}")
            if company.funding_events:
                latest = company.funding_events[0]
                output.write(f" - {latest.round_type}")
                if latest.amount:
                    output.write(f" ({latest.amount})")
            output.write(f" [{entry.status.value}]\n")

        output.write("\n\nSee attached for full details.\n")
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/plain",
            headers={"Content-Disposition": f"attachment; filename=email-summary.txt"}
        )

    else:
        # Default to CSV for CRM import
        return await export_shortlist(format="csv", sprint_id=sprint_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
