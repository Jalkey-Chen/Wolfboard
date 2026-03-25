"""Schemas for player registrations and admin check-in updates."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.enums import CheckInStatus, RegistrationStatus, RegistrationType


class RegistrationCreate(BaseModel):
    """Payload used by an authenticated user to register for an event day."""

    registration_type: RegistrationType = RegistrationType.MAIN
    note: str | None = None


class RegistrationAdminUpdate(BaseModel):
    """Fields an admin may change while managing registrations and check-in."""

    registration_status: RegistrationStatus | None = None
    check_in_status: CheckInStatus | None = None
    registration_type: RegistrationType | None = None
    note: str | None = None


class RegistrationRead(BaseModel):
    """Registration payload returned to admin screens and self views."""

    id: int
    event_day_id: int
    user_id: int
    username: str
    display_name: str
    registration_status: RegistrationStatus
    check_in_status: CheckInStatus
    registration_type: RegistrationType
    note: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
