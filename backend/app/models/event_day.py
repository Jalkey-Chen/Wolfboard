"""Event-day model representing a single tournament day inside a season."""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum as SqlEnum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import EventDayCategory, EventDayStatus
from app.db.base_class import Base


class EventDay(Base):
    """Scheduled tournament day with registration state and metadata.

    The model captures only the event-day layer in Milestone 2. It deliberately
    stops short of game scheduling so Milestone 3 can add game management
    without reworking registration or season structure.
    """

    __tablename__ = "event_days"

    id: Mapped[int] = mapped_column(primary_key=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(140))
    event_date: Mapped[date] = mapped_column(Date(), index=True)
    venue: Mapped[str] = mapped_column(String(180))
    category: Mapped[EventDayCategory] = mapped_column(
        SqlEnum(EventDayCategory, name="event_day_category", native_enum=False),
        default=EventDayCategory.OFFICIAL,
        server_default=EventDayCategory.OFFICIAL.value,
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    registration_open_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    registration_close_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    status: Mapped[EventDayStatus] = mapped_column(
        SqlEnum(EventDayStatus, name="event_day_status", native_enum=False),
        default=EventDayStatus.DRAFT,
        server_default=EventDayStatus.DRAFT.value,
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

    season = relationship("Season", back_populates="event_days")
    creator = relationship("User", back_populates="created_event_days")
    registrations = relationship(
        "Registration",
        back_populates="event_day",
        cascade="all, delete-orphan",
        order_by="Registration.created_at.asc()",
    )

    @property
    def season_name(self) -> str:
        """Expose the parent season name for response serialization."""

        return self.season.name if self.season is not None else ""

    @property
    def registration_count(self) -> int:
        """Return the current number of registrations loaded for this event day.

        The property avoids duplicating a denormalized counter column while the
        MVP still works with relatively small registration lists.
        """

        return len(self.registrations)
