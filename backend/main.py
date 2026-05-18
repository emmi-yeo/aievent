import json
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response

from auth.router import router as auth_router
from engagements.router import router as engagements_router
from onboarding.router import router as onboarding_router
from uploads.router import router as uploads_router
from auth.utils import require_consultant
from agents.orchestrator import run_analysis
from gcloud.sheets import get_engagement_by_id, init_tabs
from pdf.generator import generate_pdf
from reminders.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_tabs()
        print("Google Sheets initialised successfully.")
    except Exception as e:
        print(f"WARNING: Google Sheets init skipped ({type(e).__name__}). Tabs will be created on first use.")
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="Market Research Tool API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.environ.get("FRONTEND_URL", "http://localhost:3000"), "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(engagements_router)
app.include_router(onboarding_router)
app.include_router(uploads_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/analysis/{engagement_id}")
async def trigger_analysis(
    engagement_id: str,
    consultant: dict = Depends(require_consultant),
):
    """Stream AI analysis for a given engagement."""
    eng = get_engagement_by_id(engagement_id)
    if not eng:
        raise HTTPException(status_code=404, detail="Engagement not found")
    if eng["consultant_id"] != consultant["id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    return StreamingResponse(
        run_analysis(engagement_id),
        media_type="application/x-ndjson",
    )


@app.get("/report/{engagement_id}")
async def download_report(
    engagement_id: str,
    consultant: dict = Depends(require_consultant),
):
    """Generate and return the PDF report for an engagement."""
    eng = get_engagement_by_id(engagement_id)
    if not eng:
        raise HTTPException(status_code=404, detail="Engagement not found")
    if eng["consultant_id"] != consultant["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    if not eng.get("brief_json"):
        raise HTTPException(status_code=400, detail="Analysis not yet completed")

    brief = json.loads(eng["brief_json"])
    brief["company"] = eng["company"]
    brief["industry"] = eng["industry"]

    pdf_bytes = generate_pdf(brief)
    filename = f"{eng['company'].replace(' ', '_')}_Strategy_Brief.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
