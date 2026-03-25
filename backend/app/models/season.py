"""Season model for grouping event days within a competitive cycle."""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum as SqlEnum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import SeasonStatus
from app.db.base_class import Base


class Season(Base):
    """Tournament season with status, date range, and event-day children.

    A season is the top-level organizing unit for the MVP. Event days attach to
    a season, and later milestones will hang games and standings underneath it.
    """

    __tablename__ = "seasons"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    start_date: Mapped[date] = mapped_column(Date())
    end_date: Mapped[date] = mapped_column(Date())
    status: Mapped[SeasonStatus] = mapped_column(
        SqlEnum(SeasonStatus, name="season_status", native_enum=False),
        default=SeasonStatus.DRAFT,
        server_default=SeasonStatus.DRAFT.value,
        index=True,
    )
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
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

    creator = relationship("User", back_populates="created_seasons")
    event_days = relationship(
        "EventDay",
        back_populates="season",
        cascade="all, delete-orphan",
        order_by="EventDay.event_date.desc()",
    )
