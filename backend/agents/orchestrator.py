"""
Analysis orchestrator: validates state, runs synthesis, saves result.
"""
import json
from datetime import datetime

from gcloud.sheets import (
    get_engagement_by_id, get_onboarding_answers,
    get_uploads_by_engagement, update_engagement_field,
)
from agents.synthesis import generate_analysed_summary
from models.schemas import DOCUMENT_CATEGORIES


async def run_analysis(engagement_id: str):
    """
    Async generator that streams analysis events and saves the final brief to Sheets.
    """
    eng = get_engagement_by_id(engagement_id)
    if not eng:
        yield json.dumps({"event": "error", "message": "Engagement not found"}) + "\n"
        return

    # Check at least some documents are uploaded
    uploads = get_uploads_by_engagement(engagement_id)
    ready_uploads = [u for u in uploads if u.get("status") == "ready"]
    if not ready_uploads:
        yield json.dumps({"event": "error", "message": "No documents have been processed yet"}) + "\n"
        return

    update_engagement_field(engagement_id, "status", "analysing")
    yield json.dumps({"event": "status", "message": "Analysis started"}) + "\n"

    onboarding_answers = get_onboarding_answers(engagement_id)
    company = eng.get("company", "")
    industry = eng.get("industry", "")

    async for chunk in generate_analysed_summary(
        engagement_id, onboarding_answers, company, industry
    ):
        data = json.loads(chunk.strip())
        if data.get("event") == "done":
            # Save BEFORE yielding "done" — client may disconnect immediately
            # on receipt of this event, which would cancel any code after yield.
            final_brief = data.get("brief")
            if final_brief:
                try:
                    brief_json = json.dumps(final_brief)
                    update_engagement_field(engagement_id, "brief_json", brief_json)
                    update_engagement_field(engagement_id, "status", "complete")
                except Exception as e:
                    print(f"ERROR: Failed to save brief to Sheets: {e}")
        yield chunk
