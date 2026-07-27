from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

import models
import security
from database import SessionLocal

securityy = HTTPBearer()
securityy_optional = HTTPBearer(auto_error=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(securityy)):
    token = credentials.credentials
    payload = security.verify_Token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload


def get_current_admin(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)):

    user = db.query(models.User).filter(models.User.id == current_user["user_id"]).first()

    if not user:
        raise HTTPException(status_code=404, detail="Current user not found")

    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    return user


def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(securityy_optional)
):
    if credentials is None:
        return None

    payload = security.verify_Token(credentials.credentials)
    # An expired/invalid token on an optional-auth route shouldn't block the
    # request — just treat the caller as anonymous.
    return payload