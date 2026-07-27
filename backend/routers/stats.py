from collections import Counter
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

    # Tek GROUP BY: platform, browser, country kombinasyonuna göre gruplanmış sayımlar
    grouped_stats = (
        db.query(
            models.URLClick.accessed_platform,
            models.URLClick.accessed_browser,
            models.URLClick.accessed_country,
            func.count(models.URLClick.id).label("count"),
        )
        .filter(models.URLClick.url_id == id)
        .group_by(
            models.URLClick.accessed_platform,
            models.URLClick.accessed_browser,
            models.URLClick.accessed_country,
        )
        .all()
    )

    platform_counter = Counter()
    browser_counter = Counter()
    country_counter = Counter()
    total_clicks = 0

    for platform, browser, country, count in grouped_stats:
        platform_counter[platform or "Unknown"] += count
        browser_counter[browser or "Unknown"] += count
        country_counter[country or "Unknown"] += count
        total_clicks += count

    # recent_clicks tekil zaman damgası gerektirdiği için ayrı bir sorgu şart —
    # gruplanmış veriden geri türetilemez.
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
            {"label": label, "count": count} for label, count in platform_counter.items()
        ],
        "by_browser": [
            {"label": label, "count": count} for label, count in browser_counter.items()
        ],
        "by_country": [
            {"label": label, "count": count} for label, count in country_counter.items()
        ],
        "recent_clicks": [
            {"timestamp": clicked_at.isoformat(), "count": 1}
            for (clicked_at,) in recent_clicks
        ]
    }