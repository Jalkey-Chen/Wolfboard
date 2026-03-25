"""Schemas for administrative audit-log responses."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditActorRead(BaseModel):
    """Compact actor payload shown in audit-log listings."""

    id: int
    username: str
    display_name: str

    model_config = ConfigDict(from_attributes=True)


class AuditLogRead(BaseModel):
    """Administrative audit-log entry with before/after snapshots."""

    id: int
    actor_user_id: int | None
    actor: AuditActorRead | None = None
    entity_type: str
    entity_id: int
    action_type: str
    old_value_json: dict | list | None
    new_value_json: dict | list | None
    reason: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

