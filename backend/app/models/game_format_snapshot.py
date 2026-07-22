"""Immutable format context captured for one started game."""

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum as SqlEnum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import FormatCategory, FormatSnapshotOrigin
from app.db.base_class import Base


class GameFormatSnapshot(Base):
    """Historical copy of the format template used when a game started."""

    __tablename__ = "game_format_snapshots"
    __table_args__ = (
        CheckConstraint("snapshot_schema_version >= 1", name="ck_game_format_snapshots_schema_version"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(
        ForeignKey("games.id", ondelete="CASCADE"), unique=True, index=True
    )
    source_format_id: Mapped[int | None] = mapped_column(
        ForeignKey("game_formats.id", ondelete="SET NULL"), nullable=True, index=True
    )
    format_key: Mapped[str] = mapped_column(String(120))
    format_name: Mapped[str] = mapped_column(String(120))
    player_count: Mapped[int] = mapped_column(Integer())
    category: Mapped[FormatCategory] = mapped_column(
        SqlEnum(FormatCategory, name="format_category", native_enum=False)
    )
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    is_system_preset: Mapped[bool] = mapped_column(Boolean())
    source_format_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    snapshot_origin: Mapped[FormatSnapshotOrigin] = mapped_column(
        SqlEnum(
            FormatSnapshotOrigin,
            name="format_snapshot_origin",
            native_enum=False,
            values_callable=lambda enum: [item.value for item in enum],
        )
    )
    snapshot_schema_version: Mapped[int] = mapped_column(Integer(), default=1, server_default="1")
    frozen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    frozen_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    game = relationship("Game", back_populates="format_snapshot")
    source_format = relationship("GameFormat", back_populates="game_snapshots")
    frozen_by_user = relationship("User", back_populates="frozen_format_snapshots")
    roles = relationship(
        "GameFormatRoleSnapshot",
        back_populates="format_snapshot",
        cascade="all, delete-orphan",
        order_by="GameFormatRoleSnapshot.display_order.asc(), GameFormatRoleSnapshot.id.asc()",
    )
