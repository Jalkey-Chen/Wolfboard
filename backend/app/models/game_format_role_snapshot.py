"""Immutable role rows belonging to a per-game format snapshot."""

from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, DateTime, Enum as SqlEnum, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import FormatRoleFaction
from app.db.base_class import Base


class GameFormatRoleSnapshot(Base):
    """Historical copy of one source format-role row."""

    __tablename__ = "game_format_role_snapshots"
    __table_args__ = (
        CheckConstraint("role_count > 0", name="ck_game_format_role_snapshots_role_count"),
        Index("ix_game_format_role_snapshots_order", "format_snapshot_id", "display_order"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    format_snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("game_format_snapshots.id", ondelete="CASCADE"), index=True
    )
    source_format_role_id: Mapped[int | None] = mapped_column(
        ForeignKey("format_roles.id", ondelete="SET NULL"), nullable=True, index=True
    )
    role_name: Mapped[str] = mapped_column(String(120))
    faction: Mapped[FormatRoleFaction] = mapped_column(
        SqlEnum(FormatRoleFaction, name="format_role_faction", native_enum=False)
    )
    role_count: Mapped[int] = mapped_column(Integer())
    display_order: Mapped[int] = mapped_column(Integer(), default=0, server_default="0")
    metadata_json: Mapped[dict | None] = mapped_column(JSON(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    format_snapshot = relationship("GameFormatSnapshot", back_populates="roles")
    source_format_role = relationship("FormatRole", back_populates="game_role_snapshots")
