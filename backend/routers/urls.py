import io
from datetime import datetime
from typing import List

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

import models
import schemas
import security
from config import FRONTEND_URL
from dependencies import get_current_user, get_db
from limiter import limiter
from services.url_service import create_short_url_logic, detect_client_platform, record_click_and_get_target

MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB


router = APIRouter()


@router.post("/shorten", response_model=schemas.ShortenResponse)
@limiter.limit("10/minute")
def shorten_url(
    request: Request,
    url: schemas.URLCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    result = create_short_url_logic(
        request=request,
        db=db,
        current_user=current_user,
        url_data=url
    )

    return schemas.ShortenResponse(
        short_url=result["short_url"],
        qr_code_image=result["qr_code_image"]
    )


@router.get("/api/my-urls", response_model=list[schemas.URLResponse])
@limiter.limit("10/minute")
def list_all_url(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    current_user_id = current_user["user_id"]
    url_results = db.query(models.URL).filter(models.URL.user_id == current_user_id).all()

    base_url = str(request.base_url).rstrip("/")

    return [
        {
            "id": url.id,
            "original_url": url.original_url,
            "short_url": f"{base_url}/{url.short_url}",
            "clicks": url.clicks,
            "is_active": url.is_active,
            "expires_at": url.expires_at,
            "click_limit": url.click_limit,
            "tags": url.tags,
        }
        for url in url_results
    ]


@router.delete("/api/delete-url/{id}")
@limiter.limit("10/minute")
def delete_url(
    request: Request,
    id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    current_user_id = current_user["user_id"]

    will_be_deleted = db.query(models.URL).filter(
        models.URL.id == id,
        models.URL.user_id == current_user_id
    ).first()

    if not will_be_deleted:
        raise HTTPException(status_code=404, detail="URL not found.")

    db.delete(will_be_deleted)
    db.commit()

    return {"message": f"URL with id {id} deleted successfully."}


@router.patch("/api/validate-url/{id}")
@limiter.limit("10/minute")
def validate_url(
    request: Request,
    id: int,
    payload: schemas.URLValidationUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    current_user_id = current_user["user_id"]

    url_entry = db.query(models.URL).filter(
        models.URL.id == id,
        models.URL.user_id == current_user_id
    ).first()

    if not url_entry:
        raise HTTPException(status_code=404, detail="URL not found")

    url_entry.is_active = payload.is_active
    db.commit()
    db.refresh(url_entry)

    return {
        "message": "URL status updated successfully",
        "id": url_entry.id,
        "is_active": url_entry.is_active
    }


@router.post("/api/bulk-upload", response_model=List[schemas.BulkUploadResult])
@limiter.limit("5/minute")
def bulk_upload(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    file.file.seek(0, io.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)

    if file_size > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum allowed size is {MAX_UPLOAD_SIZE // (1024 * 1024)} MB."
        )

    contents = file.file.read()
    filename = (file.filename or "").lower()

    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
        elif filename.endswith(".xlsx") or filename.endswith(".xls"):
            df = pd.read_excel(io.BytesIO(contents))
        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type. Please upload a .csv, .xlsx, or .xls file."
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")

    results = []
    df = df.astype(object).where(pd.notnull(df), None)
    
    for row in df.itertuples(index=False):
        original_url_value = getattr(row, "URL", None)
        try:
            url_data = schemas.BulkURLCreate(
                original_url=original_url_value,
                password=row.password if hasattr(row, "password") else None,
                count_limit=row.count_limit if hasattr(row, "count_limit") else None,
                custom_code=row.custom_code if hasattr(row, "custom_code") else None
            )

            result = create_short_url_logic(
                request=request,
                db=db,
                current_user=current_user,
                url_data=url_data
            )

            results.append(
                schemas.BulkUploadResult(
                    original_url=original_url_value,
                    short_url=result["short_url"],
                    status="success"
                )
            )
        except Exception as e:
            results.append(
                schemas.BulkUploadResult(
                    original_url=original_url_value or "",
                    short_url=None,
                    status="failed",
                    error=str(e)
                )
            )

    return results


@router.post("/api/protected/{short_code}", response_model=schemas.URLAccessResponse)
@limiter.limit("4/minute")
def verify_password(
    short_code: str,
    payload: schemas.URLPasswordRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    url_entry = db.query(models.URL).filter(models.URL.short_url == short_code).first()

    if not url_entry:
        raise HTTPException(status_code=404, detail="Short URL not found")

    if url_entry.owner is None or not url_entry.owner.is_active:
        raise HTTPException(status_code=403, detail="This link's owner has been banned")

    if not url_entry.is_active:
        raise HTTPException(status_code=403, detail="This short URL is inactive")

    if url_entry.expires_at and url_entry.expires_at <= datetime.utcnow():
        raise HTTPException(status_code=410, detail="Short URL has expired")

    if url_entry.click_limit is not None and url_entry.clicks >= url_entry.click_limit:
        url_entry.is_active = False
        db.commit()
        raise HTTPException(status_code=410, detail="Short URL click limit reached")

    if url_entry.password_hash is None:
        raise HTTPException(status_code=400, detail="This URL is not password protected")

    if not security.verify_password(payload.password, url_entry.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect password")

    target_url = record_click_and_get_target(db, url_entry, request)

    return {
        "message": "Password verified successfully",
        "original_url": target_url
    }


# Catch-all redirect. Kept LAST in this file (and this router included last
# in main.py) since "/{short_code}" matches any single path segment — it
# must never get a chance to shadow a more specific route.
@router.get("/{short_code}")
@limiter.limit("5/minute")
def redirect_url(request: Request, short_code: str, db: Session = Depends(get_db)):
    url_entry = db.query(models.URL).filter(models.URL.short_url == short_code).first()

    if not url_entry:
        raise HTTPException(status_code=404, detail="Short URL not found")

    if url_entry.owner is None or not url_entry.owner.is_active:
        raise HTTPException(status_code=403, detail="This link's owner has been banned")

    if not url_entry.is_active:
        raise HTTPException(status_code=403, detail="This short URL is inactive")

    if url_entry.expires_at and url_entry.expires_at <= datetime.utcnow():
        raise HTTPException(status_code=410, detail="Short URL has expired")

    if url_entry.click_limit is not None and url_entry.clicks >= url_entry.click_limit:
        raise HTTPException(status_code=410, detail="Short URL click limit reached")

    if url_entry.password_hash is not None:
        return RedirectResponse(url=f"{FRONTEND_URL}/protected/{short_code}")

    target_url = record_click_and_get_target(db, url_entry, request)
    return RedirectResponse(url=target_url)