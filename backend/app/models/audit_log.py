"""Audit-log model for critical administrative actions."""

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class AuditLog(Base):
    """Administrative audit trail with before/after JSON snapshots."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True)
    entity_type: Mapped[str] = mapped_column(String(50), index=True)
    entity_id: Mapped[int] = mapped_column(index=True)
    action_type: Mapped[str] = mapped_column(String(50), index=True)
    old_value_json: Mapped[dict | list | None] = mapped_column(JSON(), nullable=True)
    new_value_json: Mapped[dict | list | None] = mapped_column(JSON(), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    actor = relationship("User", back_populates="audit_logs")


