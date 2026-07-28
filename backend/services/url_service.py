import base64
import random
import re
import string
from datetime import datetime, timedelta
from io import BytesIO

import qrcode
from fastapi import HTTPException, Request
from sqlalchemy.orm import Session
from user_agents import parse

import models
import security


def generate_short_code(length=6):
    characters = string.ascii_letters + string.digits
    return "".join(random.choices(characters, k=length))


def generate_qr_base64(data: str) -> str:
    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=4
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{img_base64}"


def detect_client_platform(request: Request) -> tuple[str, str]:
    """Returns (platform, browser) parsed from the request's User-Agent header.

    Pulled out of redirect_url/verify_password in urls.py since both routes
    did this exact same parsing before recording a click.
    """
    ua_string = request.headers.get("user-agent", "")
    user_agent = parse(ua_string)
    browser = user_agent.browser.family

    if user_agent.is_mobile:
        platform = "Mobile"
    elif user_agent.is_tablet:
        platform = "Tablet"
    elif user_agent.is_pc:
        platform = "PC"
    else:
        platform = "Other"

    return platform, browser


def create_short_url_logic(*, request: Request, db: Session, current_user: dict, url_data):
    user_id = current_user["user_id"]

    user_entry = db.query(models.User).filter(models.User.id == user_id).first()
    if not user_entry or not user_entry.is_active:
        raise HTTPException(status_code=403, detail="Your account has been banned.")

    base_url = str(request.base_url).rstrip("/")

    url_pattern = r"^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,20}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$"
    if not re.match(url_pattern, str(url_data.original_url)):
        raise HTTPException(status_code=400, detail="Invalid URL format.")

    existing_url = db.query(models.URL).filter(
        models.URL.original_url == str(url_data.original_url),
        models.URL.user_id == user_id
    ).first()

    # Validate a requested custom code up front, excluding the row we're
    # about to update from the "is it taken" check (otherwise a URL always
    # collides with its own current code).
    requested_custom_code = None
    if getattr(url_data, "custom_code", None) and url_data.custom_code.strip():
        requested_custom_code = url_data.custom_code.strip()

        custom_code_pattern = r"^[a-zA-Z0-9_-]{3,30}$"
        if not re.match(custom_code_pattern, requested_custom_code):
            raise HTTPException(
                status_code=400,
                detail="Custom code must be 3-30 characters and contain only letters, numbers, hyphens, or underscores."
            )

        conflict = db.query(models.URL).filter(
            models.URL.short_url == requested_custom_code,
            models.URL.id != (existing_url.id if existing_url else -1)
        ).first()
        if conflict:
            raise HTTPException(status_code=400, detail="This custom code is already taken.")

    # Shared field computation — identical for both create and update.
    expires_at = None
    if getattr(url_data, "expiration_minutes", None) is not None:
        if url_data.expiration_minutes <= 0:
            raise HTTPException(status_code=400, detail="Expiration time must be greater than 0.")
        expires_at = datetime.utcnow() + timedelta(minutes=url_data.expiration_minutes)

    click_limit = None
    if getattr(url_data, "count_limit", None) is not None:
        if url_data.count_limit <= 0:
            raise HTTPException(status_code=400, detail="Count limit must be greater than 0.")
        click_limit = url_data.count_limit

    password_hash = None
    if getattr(url_data, "password", None) and url_data.password.strip():
        password_hash = security.hash_password(url_data.password.strip())

    if existing_url:
        was_deactivated_by_click_limit = (
            not existing_url.is_active
            and existing_url.click_limit is not None
            and existing_url.clicks >= existing_url.click_limit
        )
 
        if requested_custom_code:
            existing_url.short_url = requested_custom_code
 
        existing_url.expires_at = expires_at
        existing_url.click_limit = click_limit
        existing_url.password_hash = password_hash
 
        # Raising or removing the limit revives a limit-exhausted link.
        # Anything switched off for another reason — an accepted abuse report,
        # a manual toggle — is left alone, so re-submitting a URL cannot be
        # used to undo a moderation decision.
        if was_deactivated_by_click_limit and (
            click_limit is None or existing_url.clicks < click_limit
        ):
            existing_url.is_active = True

        db.commit()
        db.refresh(existing_url)

        final_short_url = f"{base_url}/{existing_url.short_url}"
        qr_code_image = generate_qr_base64(final_short_url) if getattr(url_data, "qr_code", False) else None
        return {"short_url": final_short_url, "qr_code_image": qr_code_image}

    # No existing row for this (user, original_url) pair — create fresh.
    if requested_custom_code:
        short_code = requested_custom_code
    else:
        short_code = generate_short_code()
        while db.query(models.URL).filter(models.URL.short_url == short_code).first():
            short_code = generate_short_code()

    new_url = models.URL(
        original_url=str(url_data.original_url),
        short_url=short_code,
        user_id=user_id,
        expires_at=expires_at,
        click_limit=click_limit,
        password_hash=password_hash,
        is_active=True
    )
    db.add(new_url)
    db.commit()
    db.refresh(new_url)

    final_short_url = f"{base_url}/{short_code}"
    qr_code_image = generate_qr_base64(final_short_url) if getattr(url_data, "qr_code", False) else None
    return {"short_url": final_short_url, "qr_code_image": qr_code_image}