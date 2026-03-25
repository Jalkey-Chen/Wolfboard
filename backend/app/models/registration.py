"""Registration model linking a user to an event day."""

from datetime import datetime

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import CheckInStatus, RegistrationStatus, RegistrationType
from app.db.base_class import Base


class Registration(Base):
    """A user's signup and check-in record for a specific event day."""

    __tablename__ = "registrations"
    __table_args__ = (
        UniqueConstraint("event_day_id", "user_id", name="uq_registrations_event_day_id_user_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    event_day_id: Mapped[int] = mapped_column(ForeignKey("event_days.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    registration_status: Mapped[RegistrationStatus] = mapped_column(
        SqlEnum(RegistrationStatus, name="registration_status", native_enum=False),
        default=RegistrationStatus.REGISTERED,
        server_default=RegistrationStatus.REGISTERED.value,
        index=True,
    )
    check_in_status: Mapped[CheckInStatus] = mapped_column(
        SqlEnum(CheckInStatus, name="check_in_status", native_enum=False),
        default=CheckInStatus.NOT_CHECKED_IN,
        server_default=CheckInStatus.NOT_CHECKED_IN.value,
        index=True,
    )
    registration_type: Mapped[RegistrationType] = mapped_column(
        SqlEnum(RegistrationType, name="registration_type", native_enum=False),
        default=RegistrationType.MAIN,
        server_default=RegistrationType.MAIN.value,
    )
    note: Mapped[str | None] = mapped_column(Text(), nullable=True)
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

    event_day = relationship("EventDay", back_populates="registrations")
    user = relationship("User", back_populates="registrations")

    @property
    def username(self) -> str:
        """Expose the related username for admin tables and self views."""

        return self.user.username if self.user is not None else ""

    @property
    def display_name(self) -> str:
        """Expose the related display name for admin tables and self views."""

        return self.user.display_name if self.user is not None else ""
