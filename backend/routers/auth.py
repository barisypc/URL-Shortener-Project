import re

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

import models
import schemas
import security
from dependencies import get_db
from limiter import limiter

router = APIRouter()


@router.post("/signup/", response_model=schemas.UserResponse)
@limiter.limit("4/minute")
def create_user(request: Request, user: schemas.UserCreate, db: Session = Depends(get_db)):
    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,20}$"
    if not re.match(email_pattern, user.email):
        raise HTTPException(status_code=400, detail="Invalid mail format.")

    password_pattern = r"^(?=.*[0-9])(?=.*[a-z])(?=.*[A-Z])(?=.*[.@#$%^&+=])(?=\S+$).{4,20}$"
    if not re.match(password_pattern, user.password):
        raise HTTPException(status_code=400, detail="Invalid password format.")

    existing_user = db.query(models.User).filter(
        (models.User.username == user.username) | (models.User.email == user.email)
    ).first()

    if existing_user:
        raise HTTPException(status_code=400, detail="Username or email already registered")

    hashed_password = security.hash_password(user.password)

    new_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.post("/login/", response_model=schemas.TokenResponse)
@limiter.limit("5/minute")
def login(request: Request, user: schemas.Userlogin, response: Response, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()

    if not db_user or not security.verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    if not db_user.is_active:
        raise HTTPException(status_code=403, detail="Your account has been banned.")

    token_data = {"user_id": db_user.id, "username": db_user.username}
    access_token = security.create_Token(token_data)

    return schemas.TokenResponse(access_token=access_token)


@router.post("/change-password/", response_model=schemas.AdminMessageResponse)
@limiter.limit("3/minute")
def change_password(request: Request, payload: schemas.ChangePasswordRequest, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == payload.email).first()

    if not db_user or not security.verify_password(payload.current_password, db_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or current password")

    password_pattern = r"^(?=.*[0-9])(?=.*[a-z])(?=.*[A-Z])(?=.*[.@#$%^&+=])(?=\S+$).{4,20}$"
    if not re.match(password_pattern, payload.new_password):
        raise HTTPException(status_code=400, detail="Invalid password format.")

    db_user.hashed_password = security.hash_password(payload.new_password)
    db.commit()

    return {"message": "Password updated successfully. Please log in with your new password."}