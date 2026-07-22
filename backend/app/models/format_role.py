"""Format-role model describing the role composition of a preset format."""

from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum as SqlEnum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import FormatRoleFaction
from app.db.base_class import Base


class FormatRole(Base):
    """Role definition row belonging to a preset game format.

    The MVP stores only structural information here. `metadata_json` is kept
    intentionally flexible so later milestones can attach validation hints or
    capability flags without schema churn.
    """

    __tablename__ = "format_roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    format_id: Mapped[int] = mapped_column(ForeignKey("game_formats.id", ondelete="CASCADE"), index=True)
    role_name: Mapped[str] = mapped_column(String(120))
    faction: Mapped[FormatRoleFaction] = mapped_column(
        SqlEnum(FormatRoleFaction, name="format_role_faction", native_enum=False),
        default=FormatRoleFaction.GOOD,
        server_default=FormatRoleFaction.GOOD.value,
        index=True,
    )
    role_count: Mapped[int] = mapped_column(Integer())
    display_order: Mapped[int] = mapped_column(Integer(), default=0)
    metadata_json: Mapped[dict | None] = mapped_column(JSON(), nullable=True)
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

    format = relationship("GameFormat", back_populates="format_roles")
    game_role_snapshots = relationship("GameFormatRoleSnapshot", back_populates="source_format_role")
