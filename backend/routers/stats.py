from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

import models
import schemas
from dependencies import get_current_user, get_db

router = APIRouter()


@router.get("/api/show-statistics/{id}", response_model=schemas.URLStatisticsResponse)
def show_statistics(
    id: int,
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

    platform_stats = (
        db.query(models.URLClick.accessed_platform, func.count(models.URLClick.id))
        .filter(models.URLClick.url_id == id)
        .group_by(models.URLClick.accessed_platform)
        .all()
    )

    browser_stats = (
        db.query(models.URLClick.accessed_browser, func.count(models.URLClick.id))
        .filter(models.URLClick.url_id == id)
        .group_by(models.URLClick.accessed_browser)
        .all()
    )

    country_stats = (
        db.query(models.URLClick.accessed_country, func.count(models.URLClick.id))
        .filter(models.URLClick.url_id == id)
        .group_by(models.URLClick.accessed_country)
        .all()
    )

    total_clicks = (
        db.query(func.count(models.URLClick.id))
        .filter(models.URLClick.url_id == id)
        .scalar()
    )

    recent_clicks = (
        db.query(models.URLClick.clicked_at)
        .filter(models.URLClick.url_id == id)
        .order_by(models.URLClick.clicked_at.asc())
        .all()
    )

    return {
        "url_id": url_entry.id,
        "short_url": url_entry.short_url,
        "original_url": url_entry.original_url,
        "total_clicks": total_clicks,
        "by_platform": [
            {
                "label": platform if platform is not None else "Unknown",
                "count": count
            }
            for platform, count in platform_stats
        ],
        "by_browser": [
            {
                "label": browser if browser is not None else "Unknown",
                "count": count
            }
            for browser, count in browser_stats
        ],
        "by_country": [
            {
                "label": country if country is not None else "Unknown",
                "count": count
            }
            for country, count in country_stats
        ],
        "recent_clicks": [
            {
                "timestamp": clicked_at.isoformat(),
                "count": 1
            }
            for (clicked_at,) in recent_clicks
        ]
    }