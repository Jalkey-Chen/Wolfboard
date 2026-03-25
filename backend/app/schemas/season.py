"""Schemas for season list, detail, create, and update flows."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, model_validator

from app.core.enums import SeasonStatus
from app.schemas.event_day import EventDaySummary


class SeasonCreate(BaseModel):
    """Payload used by admins to create a new season."""

    name: str
    description: str | None = None
    start_date: date
    end_date: date
    status: SeasonStatus = SeasonStatus.DRAFT

    @model_validator(mode="after")
    def validate_dates(self) -> "SeasonCreate":
        """Ensure the season end date does not precede the start date."""

        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date.")
        return self


class SeasonUpdate(BaseModel):
    """Partial admin update payload for an existing season."""

    name: str | None = None
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: SeasonStatus | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> "SeasonUpdate":
        """Validate date order when both fields are present in the patch payload."""

        if self.start_date is not None and self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date.")
        return self


class SeasonRead(BaseModel):
    """Season payload returned by list and write endpoints."""

    id: int
    name: str
    description: str | None
    start_date: date
    end_date: date
    status: SeasonStatus
    created_by: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SeasonDetail(SeasonRead):
    """Detailed season response with child event days."""

    event_days: list[EventDaySummary]
