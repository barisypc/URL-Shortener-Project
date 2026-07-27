from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import models
import schemas
from dependencies import get_current_user, get_db

router = APIRouter()


@router.get("/api/me", response_model=schemas.CurrentUserResponse)
def get_me(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    user = db.query(models.User).filter(models.User.id == current_user["user_id"]).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user