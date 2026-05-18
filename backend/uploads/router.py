import logging
import mimetypes
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form

from models.schemas import UploadOut, ChecklistStatus, DOCUMENT_CATEGORIES, CATEGORY_LABELS
from gcloud.sheets import (
    create_upload_record, get_uploads_by_engagement,
    update_upload_status, get_engagement_by_id,
)
from gcloud.chroma import get_collection, embed_texts
from uploads.processor import extract_text, chunk_text
from auth.utils import require_client, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("/{engagement_id}", response_model=UploadOut, status_code=201)
async def upload_document(
    engagement_id: str,
    category: str = Form(...),
    file: UploadFile = File(...),
    client: dict = Depends(require_client),
):
    if client.get("engagement_id") != engagement_id:
        raise HTTPException(status_code=403, detail="Access denied")

    if category not in DOCUMENT_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category. Must be one of: {DOCUMENT_CATEGORIES}",
        )

    eng = get_engagement_by_id(engagement_id)
    if not eng:
        raise HTTPException(status_code=404, detail="Engagement not found")

    file_bytes = await file.read()
    filename = file.filename or "upload"

    # Track upload in Sheets (no Drive — file processed in memory only)
    record = create_upload_record(
        engagement_id=engagement_id,
        category=category,
        filename=filename,
        drive_file_id="",
        status="processing",
    )

    # Extract text → embed into ChromaDB for RAG analysis
    try:
        text = extract_text(file_bytes, filename)
        chunks = chunk_text(text)
        if chunks:
            collection = get_collection(engagement_id)
            ids = [f"{record['id']}_{i}" for i in range(len(chunks))]
            metadatas = [{"category": category, "filename": filename,
                          "upload_id": record["id"]} for _ in chunks]
            embeddings = embed_texts(chunks)
            collection.add(documents=chunks, embeddings=embeddings,
                           ids=ids, metadatas=metadatas)
        update_upload_status(record["id"], "ready")
        record["status"] = "ready"
    except Exception as e:
        logger.error("Upload processing failed for %s (%s): %s", filename, category, e, exc_info=True)
        update_upload_status(record["id"], "error")
        record["status"] = "error"

    return UploadOut(**record)


@router.get("/{engagement_id}", response_model=ChecklistStatus)
async def get_checklist(
    engagement_id: str,
    user: dict = Depends(get_current_user),
):
    if user.get("role") == "client" and user.get("engagement_id") != engagement_id:
        raise HTTPException(status_code=403, detail="Access denied")

    uploads = get_uploads_by_engagement(engagement_id)

    categories_data = {}
    for cat in DOCUMENT_CATEGORIES:
        cat_uploads = [u for u in uploads if u.get("category") == cat]
        ready = [u for u in cat_uploads if u.get("status") == "ready"]
        categories_data[cat] = {
            "label": CATEGORY_LABELS[cat],
            "uploaded": len(ready) > 0,
            "files": [{"id": u["id"], "filename": u["filename"],
                       "status": u["status"]} for u in cat_uploads],
        }

    all_complete = all(v["uploaded"] for v in categories_data.values())

    return ChecklistStatus(
        engagement_id=engagement_id,
        categories=categories_data,
        all_complete=all_complete,
    )
