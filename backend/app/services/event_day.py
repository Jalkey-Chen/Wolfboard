"""Service helpers for event-day queries and admin mutations.

Event-day services centralize read patterns and validation that are shared by
public pages, player registration flows, and admin management screens.
"""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.game import Game
from app.models.event_day import EventDay
from app.models.registration import Registration
from app.models.season import Season
from app.models.user import User
from app.models.user_role import UserRole
from app.schemas.event_day import EventDayCreate, EventDayUpdate


EVENT_DAY_LOAD_OPTIONS = (
    selectinload(EventDay.season),
    selectinload(EventDay.registrations).selectinload(Registration.user),
    selectinload(EventDay.games).selectinload(Game.format),
    selectinload(EventDay.games).selectinload(Game.judge).selectinload(User.user_roles).selectinload(UserRole.role),
)


def list_event_days_for_season(db: Session, season_id: int) -> list[EventDay]:
    """List event days for a specific season ordered by date descending."""

    statement = (
        select(EventDay)
        .where(EventDay.season_id == season_id)
        .order_by(EventDay.event_date.desc(), EventDay.id.desc())
    )
    return list(db.scalars(statement).all())


def get_event_day_or_404(db: Session, event_day_id: int) -> EventDay:
    """Return an event day with season and registrations loaded or raise 404.

    The eager-loading strategy avoids repeated lazy queries when the frontend
    needs both event-day metadata and viewer-specific registration state.
    """

    statement = (
        select(EventDay)
        .options(*EVENT_DAY_LOAD_OPTIONS)
        .where(EventDay.id == event_day_id)
    )
    event_day = db.scalar(statement)
    if event_day is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event day not found.")
    return event_day


def create_event_day(db: Session, payload: EventDayCreate, current_user: User) -> EventDay:
    """Create a new event day inside an existing season."""

    season = db.get(Season, payload.season_id)
    if season is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Season not found.")

    event_day = EventDay(**payload.model_dump(), created_by=current_user.id)
    db.add(event_day)
    db.commit()
    return get_event_day_or_404(db, event_day.id)


def update_event_day(db: Session, event_day: EventDay, payload: EventDayUpdate) -> EventDay:
    """Apply a partial event-day update and persist it."""

    update_data = payload.model_dump(exclude_unset=True)

    next_open_at = update_data.get("registration_open_at", event_day.registration_open_at)
    next_close_at = update_data.get("registration_close_at", event_day.registration_close_at)
    if next_open_at is not None and next_close_at is not None and next_close_at < next_open_at:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="registration_close_at must be on or after registration_open_at.",
        )

    for field, value in update_data.items():
        setattr(event_day, field, value)
    db.add(event_day)
    db.commit()
    return get_event_day_or_404(db, event_day.id)
