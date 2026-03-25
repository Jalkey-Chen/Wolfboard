"""Admin audit-log endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.audit_log import AuditLogRead
from app.services.audit import list_audit_logs


router = APIRouter(tags=["audit-logs"])


@router.get("/audit-logs", response_model=list[AuditLogRead])
def read_audit_logs(
    entity_type: str | None = Query(default=None),
    actor_user_id: int | None = Query(default=None),
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> list[AuditLogRead]:
    """Return audit logs with basic admin-facing filters."""

    _ = current_user
    audit_logs = list_audit_logs(
        db,
        entity_type=entity_type,
        actor_user_id=actor_user_id,
        created_from=created_from,
        created_to=created_to,
    )
    return [AuditLogRead.model_validate(audit_log) for audit_log in audit_logs]
