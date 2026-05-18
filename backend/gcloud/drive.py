"""
Google Drive file storage.

Uploads use your real Google account's OAuth credentials (so files are stored
in YOUR Drive, using YOUR quota — not the service account's zero-quota storage).

Run  backend/authorize_drive.py  once to set:
    GOOGLE_OAUTH_CLIENT_ID
    GOOGLE_OAUTH_CLIENT_SECRET
    GOOGLE_OAUTH_REFRESH_TOKEN

If those are missing the module falls back to service account auth (which will
only work if you have a Shared Drive configured).
"""
import os
import json
import base64
import io
from typing import Optional

from google.oauth2.credentials import Credentials as OAuthCredentials
from google.oauth2.service_account import Credentials as SACredentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload

DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]

_drive_service = None


def _get_oauth_credentials() -> Optional[OAuthCredentials]:
    """Build OAuth user credentials from env vars set by authorize_drive.py."""
    client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "").strip()
    client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "").strip()
    refresh_token = os.environ.get("GOOGLE_OAUTH_REFRESH_TOKEN", "").strip()

    if not (client_id and client_secret and refresh_token):
        return None

    creds = OAuthCredentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=DRIVE_SCOPES,
    )
    # Refresh to get a valid access token
    creds.refresh(Request())
    return creds


def _parse_service_account_json() -> dict:
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if raw.endswith(".json") and os.path.isfile(raw):
        with open(raw) as f:
            return json.load(f)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    try:
        return json.loads(base64.b64decode(raw).decode("utf-8"))
    except Exception:
        raise ValueError(
            "GOOGLE_SERVICE_ACCOUNT_JSON must be raw JSON, base64-encoded JSON, or a path to a JSON file"
        )


def _get_service():
    """
    Returns a Drive API service client.
    Prefers OAuth user credentials (your personal Google account quota).
    Falls back to service account (requires Shared Drive for uploads).
    """
    global _drive_service
    if _drive_service is not None:
        return _drive_service

    oauth_creds = _get_oauth_credentials()
    if oauth_creds:
        _drive_service = build("drive", "v3", credentials=oauth_creds)
        print("Drive: using OAuth user credentials (personal account storage)")
    else:
        info = _parse_service_account_json()
        sa_creds = SACredentials.from_service_account_info(info, scopes=DRIVE_SCOPES)
        _drive_service = build("drive", "v3", credentials=sa_creds)
        print("Drive: using service account credentials (requires Shared Drive for uploads)")

    return _drive_service


def get_or_create_folder(name: str, parent_id: Optional[str] = None) -> str:
    """Get existing folder by name under parent, or create it."""
    service = _get_service()
    parent_id = parent_id or os.environ["GOOGLE_DRIVE_FOLDER_ID"]

    query = (
        f"name='{name}' and mimeType='application/vnd.google-apps.folder' "
        f"and '{parent_id}' in parents and trashed=false"
    )
    results = service.files().list(
        q=query,
        fields="files(id, name)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    ).execute()
    files = results.get("files", [])
    if files:
        return files[0]["id"]

    metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    folder = service.files().create(
        body=metadata,
        fields="id",
        supportsAllDrives=True,
    ).execute()
    return folder["id"]


def upload_file(file_bytes: bytes, filename: str, mime_type: str,
                engagement_id: str) -> str:
    """Upload a file to the engagement's Drive folder. Returns file ID."""
    service = _get_service()
    root_folder = os.environ["GOOGLE_DRIVE_FOLDER_ID"]
    eng_folder_id = get_or_create_folder(engagement_id, root_folder)

    metadata = {"name": filename, "parents": [eng_folder_id]}
    media = MediaIoBaseUpload(
        io.BytesIO(file_bytes), mimetype=mime_type, resumable=True
    )
    uploaded = service.files().create(
        body=metadata,
        media_body=media,
        fields="id",
        supportsAllDrives=True,
    ).execute()
    return uploaded["id"]


def download_file(file_id: str) -> bytes:
    """Download a file from Drive by ID and return raw bytes."""
    service = _get_service()
    request = service.files().get_media(fileId=file_id)
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buffer.getvalue()


def upload_pdf(pdf_bytes: bytes, engagement_id: str, filename: str) -> str:
    """Upload a generated PDF report to the engagement folder."""
    return upload_file(pdf_bytes, filename, "application/pdf", engagement_id)
