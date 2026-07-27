from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

import models
import schemas
from dependencies import get_current_user, get_db, get_optional_current_user
from limiter import limiter

router = APIRouter()


@router.post("/api/report-abuse", response_model=schemas.ReportAbuseResponse)
@limiter.limit("2/minute")
def report_abuse(
    payload: schemas.ReportAbuseRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_current_user)
):
    # Anyone can report a link, logged in or not — AbuseReport.user_id is
    # nullable specifically so anonymous reports have somewhere to land.
    # Logged-in reporters still get attributed, which is what lets us also
    # dedupe repeat reports from the same account below.
    user_id = current_user["user_id"] if current_user else None

    url = db.query(models.URL).filter(models.URL.short_url == payload.short_url).first()
    if not url:
        raise HTTPException(status_code=404, detail="URL not found")

    if user_id is not None:
        existing_report = (
            db.query(models.AbuseReport)
            .filter(
                models.AbuseReport.url_id == url.id,
                models.AbuseReport.user_id == user_id
            )
            .first()
        )

        if existing_report:
            raise HTTPException(status_code=400, detail="You have already reported this URL")

    new_report = models.AbuseReport(
        url_id=url.id,
        user_id=user_id,
        reason=payload.reason
    )

    db.add(new_report)
    db.commit()
    db.refresh(new_report)

    return schemas.ReportAbuseResponse(
        message="Abuse report submitted successfully",
        abuse_id=new_report.id
    )


@router.get("/api/get-abuse", response_model=list[schemas.GetAbuseResponse])
@limiter.limit("2/minute")
def get_abuse(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["user_id"]

    abuse_reports = (
        db.query(models.AbuseReport)
        .filter(models.AbuseReport.user_id == user_id)
        .order_by(models.AbuseReport.id)
        .all()
    )

    result = []
    for report in abuse_reports:
        result.append(
            schemas.GetAbuseResponse(
                abuse_id=report.id,
                original_url=report.url.original_url,
                short_code=report.url.short_url,
                url_id=report.url_id,
                user_id=report.user_id
            )
        )

    return result