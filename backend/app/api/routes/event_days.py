"""Event-day detail, admin CRUD, and nested registration endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.event_day import EventDay
from app.models.user import User
from app.schemas.event_day import EventDayCreate, EventDayDetail, EventDaySummary, EventDayUpdate
from app.schemas.registration import RegistrationCreate, RegistrationRead
from app.services.event_day import create_event_day, get_event_day_or_404, update_event_day
from app.services.registration import create_registration, list_registrations_for_event_day


router = APIRouter(prefix="/event-days", tags=["event-days"])


def build_event_day_detail(event_day: EventDay, current_user: User) -> EventDayDetail:
    """Build a detail payload with viewer-specific registration context."""

    viewer_registration = None
    for registration in event_day.registrations:
        if registration.user_id == current_user.id:
            viewer_registration = RegistrationRead.model_validate(registration)
            break

    return EventDayDetail(
        **EventDaySummary.model_validate(event_day).model_dump(),
        notes=event_day.notes,
        season_name=event_day.season_name,
        registration_count=event_day.registration_count,
        viewer_registration=viewer_registration,
    )


@router.get("/{event_day_id}", response_model=EventDayDetail)
def read_event_day(
    event_day_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EventDayDetail:
    """Return event-day details for any authenticated user."""

    event_day = get_event_day_or_404(db, event_day_id)
    return build_event_day_detail(event_day, current_user)


@router.post("", response_model=EventDayDetail)
def create_event_day_endpoint(
    payload: EventDayCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> EventDayDetail:
    """Create a new event day as an admin."""

    event_day = create_event_day(db, payload, current_user)
    return build_event_day_detail(event_day, current_user)


@router.patch("/{event_day_id}", response_model=EventDayDetail)
def update_event_day_endpoint(
    event_day_id: int,
    payload: EventDayUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> EventDayDetail:
    """Update an existing event day as an admin."""

    event_day = get_event_day_or_404(db, event_day_id)
    event_day = update_event_day(db, event_day, payload)
    return build_event_day_detail(event_day, current_user)


@router.get("/{event_day_id}/registrations", response_model=list[RegistrationRead])
def read_event_day_registrations(
    event_day_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[RegistrationRead]:
    """Return admin-visible or self-visible registration rows for an event day."""

    _ = get_event_day_or_404(db, event_day_id)
    include_all = "admin" in current_user.roles
    registrations = list_registrations_for_event_day(db, event_day_id, current_user, include_all=include_all)
    return [RegistrationRead.model_validate(registration) for registration in registrations]


@router.post("/{event_day_id}/registrations", response_model=RegistrationRead)
def create_event_day_registration(
    event_day_id: int,
    payload: RegistrationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RegistrationRead:
    """Create a self-registration for the current user."""

    event_day = get_event_day_or_404(db, event_day_id)
    registration = create_registration(db, event_day, payload, current_user)
    return RegistrationRead.model_validate(registration)
