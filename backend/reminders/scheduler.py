"""
Daily email reminder scheduler.
Checks Google Sheets for engagements with missing uploads near deadline.
"""
import os
from datetime import datetime, date, timedelta
from typing import List

import resend
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from gcloud.sheets import get_all_engagements, get_uploads_by_engagement
from models.schemas import DOCUMENT_CATEGORIES, CATEGORY_LABELS

scheduler = AsyncIOScheduler()


def _get_missing_categories(engagement_id: str) -> List[str]:
    uploads = get_uploads_by_engagement(engagement_id)
    uploaded = {u["category"] for u in uploads if u.get("status") == "ready"}
    return [cat for cat in DOCUMENT_CATEGORIES if cat not in uploaded]


def _send_reminder(client_email: str, client_name: str, company: str,
                    missing: List[str], deadline: str, frontend_url: str):
    resend.api_key = os.environ["RESEND_API_KEY"]
    missing_labels = [CATEGORY_LABELS[cat] for cat in missing]
    missing_list = "".join(f"<li>{label}</li>" for label in missing_labels)
    upload_url = f"{frontend_url}/client/upload"

    resend.Emails.send({
        "from": "reminders@resend.dev",
        "to": client_email,
        "subject": f"Action Required: Upload Documents for {company} by {deadline}",
        "html": f"""
        <div style="font-family: sans-serif; max-width: 600px; margin: auto;">
          <h2>Documents Still Needed — {company}</h2>
          <p>Hi {client_name},</p>
          <p>Your consultant's deadline is <strong>{deadline}</strong>.
             The following documents are still missing from your workspace:</p>
          <ul>{missing_list}</ul>
          <p>Please upload them as soon as possible:</p>
          <p><a href="{upload_url}" style="background:#0f3460; color:white; padding:12px 24px;
             text-decoration:none; border-radius:6px; display:inline-block;">
             Upload Documents
          </a></p>
          <p style="color:#888; font-size:12px;">
            If you have already uploaded these, please ignore this message.
          </p>
        </div>
        """,
    })


async def check_and_send_reminders():
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
    engagements = get_all_engagements()
    today = date.today()

    for eng in engagements:
        if eng.get("status") == "complete":
            continue

        try:
            deadline = date.fromisoformat(eng.get("deadline", ""))
        except ValueError:
            continue

        days_until = (deadline - today).days
        if days_until < 0 or days_until > 7:
            continue

        missing = _get_missing_categories(eng["id"])
        if not missing:
            continue

        try:
            _send_reminder(
                client_email=eng["client_email"],
                client_name=eng["client_name"],
                company=eng["company"],
                missing=missing,
                deadline=eng["deadline"],
                frontend_url=frontend_url,
            )
        except Exception:
            pass


def start_scheduler():
    scheduler.add_job(
        check_and_send_reminders,
        trigger="cron",
        hour=9,
        minute=0,
        id="daily_reminders",
        replace_existing=True,
    )
    scheduler.start()


def stop_scheduler():
    scheduler.shutdown(wait=False)
