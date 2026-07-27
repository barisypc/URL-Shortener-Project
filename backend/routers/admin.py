from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

import models
import schemas
from dependencies import get_current_admin, get_db
from limiter import limiter

router = APIRouter()


@router.delete("/api/admin/delete-user/{user_id}", response_model=schemas.AdminMessageResponse)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(get_current_admin)
):
    user_to_delete = db.query(models.User).filter(models.User.id == user_id).first()

    if not user_to_delete:
        raise HTTPException(status_code=404, detail="User not found")

    if user_to_delete.is_admin:
        raise HTTPException(status_code=400, detail="Cannot delete another admin")

    db.delete(user_to_delete)
    db.commit()

    return {"message": f"User with id {user_id} deleted successfully."}


@router.patch("/api/admin/ban-user/{user_id}", response_model=schemas.AdminMessageResponse)
def ban_user(
    user_id: int,
    payload: schemas.AdminUserBanRequest,
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(get_current_admin)
):
    user_entry = db.query(models.User).filter(models.User.id == user_id).first()

    if not user_entry:
        raise HTTPException(status_code=404, detail="User not found")

    if user_entry.is_admin:
        raise HTTPException(status_code=400, detail="Cannot ban another admin")

    user_entry.is_active = payload.is_active
    db.commit()
    db.refresh(user_entry)

    return {"message": "User status updated successfully"}


@router.get("/api/admin/dashboard", response_model=schemas.AdminDashboardStats)
def admin_dashboard(
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(get_current_admin)
):
    total_users = db.query(func.count(models.User.id)).scalar()
    active_users = db.query(func.count(models.User.id)).filter(models.User.is_active == True).scalar()
    banned_users = total_users - active_users

    total_urls = db.query(func.count(models.URL.id)).scalar()
    active_urls = db.query(func.count(models.URL.id)).filter(models.URL.is_active == True).scalar()
    inactive_urls = total_urls - active_urls
    protected_urls = db.query(func.count(models.URL.id)).filter(models.URL.password_hash.isnot(None)).scalar()
    total_clicks = db.query(func.coalesce(func.sum(models.URL.clicks), 0)).scalar()

    return {
        "total_users": total_users,
        "active_users": active_users,
        "banned_users": banned_users,
        "total_urls": total_urls,
        "active_urls": active_urls,
        "inactive_urls": inactive_urls,
        "protected_urls": protected_urls,
        "total_clicks": total_clicks,
    }


@router.get("/api/admin/users", response_model=list[schemas.AdminUserListItem])
def list_all_users(
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(get_current_admin)
):
    rows = (
        db.query(
            models.User.id,
            models.User.username,
            models.User.email,
            models.User.is_active,
            models.User.is_admin,
            func.count(models.URL.id).label("url_count"),
            func.coalesce(func.sum(models.URL.clicks), 0).label("total_clicks"),
        )
        .outerjoin(models.URL, models.URL.user_id == models.User.id)
        .group_by(models.User.id)
        .all()
    )

    return [
        {
            "id": row.id,
            "username": row.username,
            "email": row.email,
            "is_active": row.is_active,
            "is_admin": row.is_admin,
            "url_count": row.url_count,
            "total_clicks": row.total_clicks,
        }
        for row in rows]


@router.get("/api/admin/user-urls/{user_id}", response_model=list[schemas.URLResponse])
def get_user_urls(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(get_current_admin)
):
    user = db.query(models.User).filter(models.User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    url_results = db.query(models.URL).filter(models.URL.user_id == user_id).all()

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


@router.get("/api/admin/abuse-reports", response_model=list[schemas.AdminAbuseReportItem])
def list_all_abuse_reports(
    request: Request,
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(get_current_admin)
):
    reports = (
        db.query(models.AbuseReport)
        .order_by(models.AbuseReport.created_at.desc())
        .all()
    )

    base_url = str(request.base_url).rstrip("/")
    result = []

    for report in reports:
        url = report.url
        if url is None:
            continue

        result.append(
            schemas.AdminAbuseReportItem(
                abuse_id=report.id,
                url_id=report.url_id,
                short_code=url.short_url,
                short_url=f"{base_url}/{url.short_url}",
                original_url=url.original_url,
                reason=report.reason,
                created_at=report.created_at,
                reporter_id=report.user_id,
                reporter_email=report.owner.email if report.owner else None,
                owner_email=url.owner.email if url.owner else None,
                url_is_active=url.is_active,
            )
        )

    return result


@router.post("/api/admin/accept-abuse", response_model=schemas.AcceptAbuseResponse)
@limiter.limit("2/minute")
def accept_abuse(
    payload: schemas.AcceptAbuseRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(get_current_admin)
):
    abuse_report = db.query(models.AbuseReport).filter(
        models.AbuseReport.id == payload.abuse_id
    ).first()

    if not abuse_report:
        raise HTTPException(status_code=404, detail="Abuse report not found")

    url = db.query(models.URL).filter(models.URL.id == abuse_report.url_id).first()
    if not url:
        raise HTTPException(status_code=404, detail="Associated URL not found")

    url.is_active = False
    db.delete(abuse_report)
    db.commit()

    return schemas.AcceptAbuseResponse(
        message="Abuse report accepted and URL disabled successfully"
    )


@router.post("/api/admin/refuse-abuse", response_model=schemas.RefuseAbuseResponse)
@limiter.limit("2/minute")
def refuse_abuse(
    payload: schemas.RefuseAbuseRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(get_current_admin)
):
    abuse_report = db.query(models.AbuseReport).filter(
        models.AbuseReport.id == payload.abuse_id
    ).first()

    if not abuse_report:
        raise HTTPException(status_code=404, detail="Abuse report not found")

    db.delete(abuse_report)
    db.commit()

    return schemas.RefuseAbuseResponse(
        message="Abuse report refused successfully"
    )