from typing import Optional

from sqlalchemy.orm import Session

import models


def log_admin_action(
    db: Session,
    admin_id: int,
    action: str,
    target_type: Optional[str] = None,
    target_id: Optional[int] = None,
    detail: Optional[str] = None,
) -> models.AdminAuditLog:
    entry = models.AdminAuditLog(
        admin_id=admin_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=detail,
    )
    db.add(entry)
    return entry