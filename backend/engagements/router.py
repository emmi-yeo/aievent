import os
import secrets
import string

import resend
from fastapi import APIRouter, Depends, HTTPException

from models.schemas import EngagementCreate, EngagementOut, EngagementListItem, DOCUMENT_CATEGORIES
from gcloud.sheets import (
    create_engagement, get_engagements_by_consultant,
    get_engagement_by_id, get_uploads_by_engagement,
    create_user, get_user_by_email, init_tabs,
)
from auth.utils import hash_password, require_consultant

router = APIRouter(prefix="/engagements", tags=["engagements"])


def _generate_temp_password(length: int = 12) -> str:
    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


def _build_upload_summary(engagement_id: str) -> dict:
    uploads = get_uploads_by_engagement(engagement_id)
    uploaded_categories = {u["category"] for u in uploads if u.get("status") == "ready"}
    return {cat: cat in uploaded_categories for cat in DOCUMENT_CATEGORIES}


def _send_client_welcome(client_email: str, client_name: str, company: str,
                          temp_password: str, frontend_url: str):
    resend.api_key = os.environ["RESEND_API_KEY"]
    login_url = f"{frontend_url}/login"
    # Use configured sender or fall back to Resend test address
    from_address = os.environ.get("EMAIL_FROM", "onboarding@resend.dev")
    resend.Emails.send({
        "from": from_address,
        "to": client_email,
        "subject": f"Your Market Research Portal Access — {company}",
        "html": f"""
        <div style="font-family: sans-serif; max-width: 600px; margin: auto;">
          <h2>Welcome, {client_name}</h2>
          <p>Your consultant has created a workspace for <strong>{company}</strong>.</p>
          <p>Please log in to complete your onboarding and upload your documents:</p>
          <p><strong>Portal:</strong> <a href="{login_url}">{login_url}</a></p>
          <p><strong>Email:</strong> {client_email}</p>
          <p><strong>Temporary Password:</strong> <code>{temp_password}</code></p>
          <p style="color:#888; font-size:12px;">Please change your password after first login.</p>
        </div>
        """,
    })


@router.post("", response_model=EngagementOut, status_code=201)
async def create(body: EngagementCreate, consultant: dict = Depends(require_consultant)):
    init_tabs()
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")

    # Create or reuse client account
    existing_client = get_user_by_email(body.client_email)
    temp_password = None
    if existing_client:
        client_id = existing_client["id"]
    else:
        temp_password = _generate_temp_password()
        client = create_user(
            email=body.client_email,
            hashed_password=hash_password(temp_password),
            name=body.client_name,
            role="client",
        )
        client_id = client["id"]

    engagement = create_engagement(
        consultant_id=consultant["id"],
        client_id=client_id,
        client_name=body.client_name,
        client_email=body.client_email,
        company=body.company,
        industry=body.industry,
        deadline=body.deadline,
        client_temp_password=temp_password or "",
    )

    # Update client's engagement_id
    from gcloud.sheets import update_user_engagement
    update_user_engagement(client_id, engagement["id"])

    # Send welcome email with credentials
    email_sent = False
    email_error = None
    if temp_password:
        try:
            _send_client_welcome(
                body.client_email, body.client_name, body.company,
                temp_password, frontend_url,
            )
            email_sent = True
        except Exception as e:
            email_error = str(e)
            print(f"Email send failed: {e}")

    return EngagementOut(
        **engagement,
        temp_password=temp_password,  # always return once so consultant can copy it
        email_sent=email_sent,
    )


@router.get("", response_model=list[EngagementListItem])
async def list_engagements(consultant: dict = Depends(require_consultant)):
    engagements = get_engagements_by_consultant(consultant["id"])
    result = []
    for eng in engagements:
        result.append(EngagementListItem(
            id=eng["id"],
            company=eng["company"],
            client_name=eng["client_name"],
            industry=eng["industry"],
            deadline=eng["deadline"],
            onboarding_complete=str(eng.get("onboarding_complete", "")).upper() == "TRUE",
            status=eng.get("status", "pending"),
            upload_summary=_build_upload_summary(eng["id"]),
        ))
    return result


@router.get("/{engagement_id}", response_model=EngagementOut)
async def get_engagement(engagement_id: str, consultant: dict = Depends(require_consultant)):
    eng = get_engagement_by_id(engagement_id)
    if not eng:
        raise HTTPException(status_code=404, detail="Engagement not found")
    if eng["consultant_id"] != consultant["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    eng["onboarding_complete"] = str(eng.get("onboarding_complete", "")).upper() == "TRUE"
    return EngagementOut(**eng)
