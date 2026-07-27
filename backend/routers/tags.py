from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

import models
import schemas
from dependencies import get_current_user, get_db

router = APIRouter()


@router.post("/api/create-tag", response_model=schemas.TagResponse)
def create_tag(
    payload: schemas.TagCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["user_id"]

    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Tag name cannot be empty.")

    if len(name) > 30:
        raise HTTPException(status_code=400, detail="Tag name must be 30 characters or fewer.")

    existing = db.query(models.Tag).filter(
        models.Tag.user_id == user_id,
        func.lower(models.Tag.name) == name.lower()
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="You already have a tag with this name.")

    new_tag = models.Tag(name=name, user_id=user_id)
    db.add(new_tag)
    db.commit()
    db.refresh(new_tag)

    return new_tag


@router.get("/api/my-tags", response_model=list[schemas.TagResponse])
def list_my_tags(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["user_id"]
    return (
        db.query(models.Tag)
        .filter(models.Tag.user_id == user_id)
        .order_by(models.Tag.name)
        .all()
    )


@router.patch("/api/rename-tag/{tag_id}", response_model=schemas.TagResponse)
def rename_tag(
    tag_id: int,
    payload: schemas.TagUpdateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["user_id"]

    tag = db.query(models.Tag).filter(
        models.Tag.id == tag_id,
        models.Tag.user_id == user_id
    ).first()

    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found.")

    if payload.name is not None:
        new_name = payload.name.strip()

        if not new_name:
            raise HTTPException(status_code=400, detail="Tag name cannot be empty.")

        duplicate = db.query(models.Tag).filter(
            models.Tag.user_id == user_id,
            func.lower(models.Tag.name) == new_name.lower(),
            models.Tag.id != tag_id
        ).first()

        if duplicate:
            raise HTTPException(status_code=400, detail="You already have a tag with this name.")

        tag.name = new_name

    db.commit()
    db.refresh(tag)

    return tag


@router.patch("/api/change-tag/{url_id}", response_model=schemas.URLResponse)
def change_tag(
    url_id: int,
    payload: schemas.URLTagsUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["user_id"]

    url_entry = db.query(models.URL).filter(
        models.URL.id == url_id,
        models.URL.user_id == user_id
    ).first()

    if not url_entry:
        raise HTTPException(status_code=404, detail="URL not found.")

    unique_tag_ids = list(set(payload.tag_ids))

    tags = db.query(models.Tag).filter(
        models.Tag.id.in_(unique_tag_ids),
        models.Tag.user_id == user_id
    ).all()

    found_ids = {tag.id for tag in tags}
    missing_ids = [tid for tid in unique_tag_ids if tid not in found_ids]

    if missing_ids:
        raise HTTPException(
            status_code=400,
            detail=f"Tag id(s) {missing_ids} not found or don't belong to you."
        )

    # Replacing the whole collection lets SQLAlchemy add/remove association
    # rows in one shot — this single endpoint covers adding, removing, and
    # updating a URL's tags depending on what's in the new list.
    url_entry.tags = tags
    db.commit()
    db.refresh(url_entry)

    base_url = str(request.base_url).rstrip("/")

    return {
        "id": url_entry.id,
        "original_url": url_entry.original_url,
        "short_url": f"{base_url}/{url_entry.short_url}",
        "clicks": url_entry.clicks,
        "is_active": url_entry.is_active,
        "expires_at": url_entry.expires_at,
        "click_limit": url_entry.click_limit,
        "tags": url_entry.tags,
    }


@router.delete("/api/delete-tag/{tag_id}", response_model=schemas.AdminMessageResponse)
def delete_tag(
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["user_id"]

    tag = db.query(models.Tag).filter(
        models.Tag.id == tag_id,
        models.Tag.user_id == user_id
    ).first()

    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found.")

    tag_name = tag.name
    db.delete(tag)
    db.commit()

    return {"message": f"Tag '{tag_name}' deleted successfully."}