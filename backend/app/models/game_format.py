"""Game-format model representing a preset ruleset configuration."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import FormatCategory
from app.db.base_class import Base


class GameFormat(Base):
    """Preset format definition used when admins create games.

    Formats are seeded and mostly read-only in the MVP. The schema already
    supports activation toggles and rich descriptions so later milestones can
    expand management capabilities without reworking the table.
    """

    __tablename__ = "game_formats"

    id: Mapped[int] = mapped_column(primary_key=True)
    format_name: Mapped[str] = mapped_column(String(120), index=True)
    format_key: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    player_count: Mapped[int] = mapped_column(index=True)
    category: Mapped[FormatCategory] = mapped_column(
        SqlEnum(FormatCategory, name="format_category", native_enum=False),
        default=FormatCategory.STANDARD,
        server_default=FormatCategory.STANDARD.value,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean(), default=True, server_default="true", index=True)
    is_system_preset: Mapped[bool] = mapped_column(Boolean(), default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    format_roles = relationship(
        "FormatRole",
        back_populates="format",
        cascade="all, delete-orphan",
        order_by="FormatRole.display_order.asc()",
    )
    games = relationship("Game", back_populates="format")
    game_snapshots = relationship("GameFormatSnapshot", back_populates="source_format")
