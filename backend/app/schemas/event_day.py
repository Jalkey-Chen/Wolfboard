"""Schemas for event-day read and write operations.

The detail schema includes viewer-specific registration context so the frontend
can render self-service signup state without making an extra request.
"""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, model_validator

from app.core.enums import EventDayCategory, EventDayStatus
from app.schemas.registration import RegistrationRead


class EventDayCreate(BaseModel):
    """Payload used by admins to create a new event day."""

    season_id: int
    title: str
    event_date: date
    venue: str
    category: EventDayCategory
    notes: str | None = None
    registration_open_at: datetime | None = None
    registration_close_at: datetime | None = None
    status: EventDayStatus = EventDayStatus.DRAFT

    @model_validator(mode="after")
    def validate_registration_window(self) -> "EventDayCreate":
        """Ensure the registration close time does not precede the open time."""

        if (
            self.registration_open_at is not None
            and self.registration_close_at is not None
            and self.registration_close_at < self.registration_open_at
        ):
            raise ValueError("registration_close_at must be on or after registration_open_at.")
        return self


class EventDayUpdate(BaseModel):
    """Partial admin update payload for an existing event day."""

    title: str | None = None
    event_date: date | None = None
    venue: str | None = None
    category: EventDayCategory | None = None
    notes: str | None = None
    registration_open_at: datetime | None = None
    registration_close_at: datetime | None = None
    status: EventDayStatus | None = None

    @model_validator(mode="after")
    def validate_registration_window(self) -> "EventDayUpdate":
        """Validate the registration window when both values are supplied."""

        if (
            self.registration_open_at is not None
            and self.registration_close_at is not None
            and self.registration_close_at < self.registration_open_at
        ):
            raise ValueError("registration_close_at must be on or after registration_open_at.")
        return self


class EventDaySummary(BaseModel):
    """Compact event-day payload used inside season detail pages."""

    id: int
    season_id: int
    title: str
    event_date: date
    venue: str
    category: EventDayCategory
    registration_open_at: datetime | None
    registration_close_at: datetime | None
    status: EventDayStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EventDayDetail(EventDaySummary):
    """Detailed event-day response with self-registration context.

    `viewer_registration` is populated only for the authenticated caller and is
    safe to expose to players because it contains only their own registration.
    """

    notes: str | None
    season_name: str
    registration_count: int
    viewer_registration: RegistrationRead | None = None
