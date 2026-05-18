"""
Google Sheets as the application database.
All reads/writes go through this module using gspread + service account.
"""
import os
import json
import base64
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

TAB_USERS = "Users"
TAB_ENGAGEMENTS = "Engagements"
TAB_ONBOARDING = "OnboardingAnswers"
TAB_UPLOADS = "Uploads"

_client: Optional[gspread.Client] = None
_spreadsheet: Optional[gspread.Spreadsheet] = None


def _parse_service_account_json() -> dict:
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    # Support file path (e.g. GOOGLE_SERVICE_ACCOUNT_JSON=/path/to/sa.json)
    if raw.endswith(".json") and os.path.isfile(raw):
        with open(raw) as f:
            return json.load(f)
    # Try raw JSON first
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    # Try base64-encoded JSON
    try:
        return json.loads(base64.b64decode(raw).decode("utf-8"))
    except Exception:
        raise ValueError(
            "GOOGLE_SERVICE_ACCOUNT_JSON must be raw JSON, base64-encoded JSON, or a path to a JSON file"
        )


def _get_client() -> gspread.Client:
    global _client
    if _client is None:
        info = _parse_service_account_json()
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        _client = gspread.authorize(creds)
    return _client


def get_spreadsheet() -> gspread.Spreadsheet:
    global _spreadsheet
    if _spreadsheet is None:
        _spreadsheet = _get_client().open_by_key(os.environ["GOOGLE_SHEETS_ID"])
    return _spreadsheet


def _get_or_create_tab(name: str, headers: List[str]) -> gspread.Worksheet:
    ss = get_spreadsheet()
    try:
        ws = ss.worksheet(name)
    except gspread.WorksheetNotFound:
        ws = ss.add_worksheet(title=name, rows=1000, cols=len(headers))
        ws.append_row(headers)
    return ws


def init_tabs():
    """Create all required tabs with headers if they don't exist."""
    _get_or_create_tab(TAB_USERS, [
        "id", "email", "hashed_password", "name", "role",
        "engagement_id", "created_at",
    ])
    _get_or_create_tab(TAB_ENGAGEMENTS, [
        "id", "consultant_id", "client_id", "client_name", "client_email",
        "company", "industry", "deadline", "onboarding_complete",
        "status", "brief_json", "created_at",
    ])
    _get_or_create_tab(TAB_ONBOARDING, [
        "id", "engagement_id", "question", "answer", "timestamp",
    ])
    _get_or_create_tab(TAB_UPLOADS, [
        "id", "engagement_id", "category", "filename",
        "drive_file_id", "status", "uploaded_at",
    ])


# ── Users ─────────────────────────────────────────────────────────────────────

def create_user(email: str, hashed_password: str, name: str, role: str,
                engagement_id: str = "") -> Dict:
    ws = _get_or_create_tab(TAB_USERS, [
        "id", "email", "hashed_password", "name", "role",
        "engagement_id", "created_at",
    ])
    user_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    row = [user_id, email, hashed_password, name, role, engagement_id, now]
    ws.append_row(row)
    return {"id": user_id, "email": email, "name": name, "role": role,
            "engagement_id": engagement_id, "created_at": now}


def get_user_by_email(email: str) -> Optional[Dict]:
    ws = _get_or_create_tab(TAB_USERS, [
        "id", "email", "hashed_password", "name", "role",
        "engagement_id", "created_at",
    ])
    records = ws.get_all_records()
    for r in records:
        if r.get("email", "").lower() == email.lower():
            return r
    return None


def get_user_by_id(user_id: str) -> Optional[Dict]:
    ws = _get_or_create_tab(TAB_USERS, [
        "id", "email", "hashed_password", "name", "role",
        "engagement_id", "created_at",
    ])
    records = ws.get_all_records()
    for r in records:
        if r.get("id") == user_id:
            return r
    return None


def update_user_engagement(user_id: str, engagement_id: str):
    ws = get_spreadsheet().worksheet(TAB_USERS)
    records = ws.get_all_records()
    for i, r in enumerate(records, start=2):
        if r.get("id") == user_id:
            ws.update_cell(i, 6, engagement_id)
            return


# ── Engagements ───────────────────────────────────────────────────────────────

def create_engagement(consultant_id: str, client_id: str, client_name: str,
                      client_email: str, company: str, industry: str,
                      deadline: str, client_temp_password: str = "") -> Dict:
    ws = _get_or_create_tab(TAB_ENGAGEMENTS, [
        "id", "consultant_id", "client_id", "client_name", "client_email",
        "company", "industry", "deadline", "onboarding_complete",
        "status", "brief_json", "created_at", "client_temp_password",
    ])
    eng_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    row = [eng_id, consultant_id, client_id, client_name, client_email,
           company, industry, deadline, "FALSE", "pending", "", now, client_temp_password]
    ws.append_row(row)
    return {
        "id": eng_id, "consultant_id": consultant_id, "client_id": client_id,
        "client_name": client_name, "client_email": client_email,
        "company": company, "industry": industry, "deadline": deadline,
        "onboarding_complete": False, "status": "pending",
        "brief_json": "", "created_at": now,
    }


def get_engagements_by_consultant(consultant_id: str) -> List[Dict]:
    ws = _get_or_create_tab(TAB_ENGAGEMENTS, [
        "id", "consultant_id", "client_id", "client_name", "client_email",
        "company", "industry", "deadline", "onboarding_complete",
        "status", "brief_json", "created_at",
    ])
    records = ws.get_all_records()
    return [r for r in records if r.get("consultant_id") == consultant_id]


def get_engagement_by_id(engagement_id: str) -> Optional[Dict]:
    ws = _get_or_create_tab(TAB_ENGAGEMENTS, [
        "id", "consultant_id", "client_id", "client_name", "client_email",
        "company", "industry", "deadline", "onboarding_complete",
        "status", "brief_json", "created_at",
    ])
    records = ws.get_all_records()
    for r in records:
        if r.get("id") == engagement_id:
            return r
    return None


def update_engagement_field(engagement_id: str, field: str, value: Any):
    ws = get_spreadsheet().worksheet(TAB_ENGAGEMENTS)
    headers = ws.row_values(1)
    if field not in headers:
        return
    col = headers.index(field) + 1
    records = ws.get_all_records()
    for i, r in enumerate(records, start=2):
        if r.get("id") == engagement_id:
            ws.update_cell(i, col, value)
            return


def get_all_engagements() -> List[Dict]:
    ws = _get_or_create_tab(TAB_ENGAGEMENTS, [
        "id", "consultant_id", "client_id", "client_name", "client_email",
        "company", "industry", "deadline", "onboarding_complete",
        "status", "brief_json", "created_at",
    ])
    return ws.get_all_records()


# ── Onboarding Answers ────────────────────────────────────────────────────────

def save_onboarding_answer(engagement_id: str, question: str, answer: str):
    ws = _get_or_create_tab(TAB_ONBOARDING, [
        "id", "engagement_id", "question", "answer", "timestamp",
    ])
    ws.append_row([
        str(uuid.uuid4()), engagement_id, question, answer,
        datetime.utcnow().isoformat(),
    ])


def get_onboarding_answers(engagement_id: str) -> List[Dict]:
    ws = _get_or_create_tab(TAB_ONBOARDING, [
        "id", "engagement_id", "question", "answer", "timestamp",
    ])
    records = ws.get_all_records()
    return [r for r in records if r.get("engagement_id") == engagement_id]


# ── Uploads ───────────────────────────────────────────────────────────────────

def create_upload_record(engagement_id: str, category: str, filename: str,
                         drive_file_id: str, status: str = "processing") -> Dict:
    ws = _get_or_create_tab(TAB_UPLOADS, [
        "id", "engagement_id", "category", "filename",
        "drive_file_id", "status", "uploaded_at",
    ])
    upload_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    ws.append_row([upload_id, engagement_id, category, filename,
                   drive_file_id, status, now])
    return {
        "id": upload_id, "engagement_id": engagement_id, "category": category,
        "filename": filename, "drive_file_id": drive_file_id,
        "status": status, "uploaded_at": now,
    }


def get_uploads_by_engagement(engagement_id: str) -> List[Dict]:
    ws = _get_or_create_tab(TAB_UPLOADS, [
        "id", "engagement_id", "category", "filename",
        "drive_file_id", "status", "uploaded_at",
    ])
    records = ws.get_all_records()
    return [r for r in records if r.get("engagement_id") == engagement_id]


def update_upload_status(upload_id: str, status: str):
    ws = get_spreadsheet().worksheet(TAB_UPLOADS)
    records = ws.get_all_records()
    for i, r in enumerate(records, start=2):
        if r.get("id") == upload_id:
            ws.update_cell(i, 6, status)
            return
