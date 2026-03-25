"""Service helpers for player registration and admin check-in flows.

This module contains the core business rules for who may register, when
registration is open, and how admins change attendance state after signup.
"""

from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import EventDayStatus, RegistrationStatus
from app.models.event_day import EventDay
from app.models.registration import Registration
from app.models.user import User
from app.schemas.registration import RegistrationAdminUpdate, RegistrationCreate


REGISTRATION_LOAD_OPTIONS = (
    selectinload(Registration.user),
    selectinload(Registration.event_day).selectinload(EventDay.season),
)


def get_registration_or_404(db: Session, registration_id: int) -> Registration:
    """Return a registration with user and event-day context or raise 404."""

    statement = (
        select(Registration)
        .options(*REGISTRATION_LOAD_OPTIONS)
        .where(Registration.id == registration_id)
    )
    registration = db.scalar(statement)
    if registration is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registration not found.")
    return registration


def get_registration_for_user(db: Session, event_day_id: int, user_id: int) -> Registration | None:
    """Return the current user's registration for the given event day, if any."""

    statement = (
        select(Registration)
        .options(*REGISTRATION_LOAD_OPTIONS)
        .where(Registration.event_day_id == event_day_id, Registration.user_id == user_id)
    )
    return db.scalar(statement)


def list_registrations_for_event_day(
    db: Session,
    event_day_id: int,
    current_user: User,
    include_all: bool,
) -> list[Registration]:
    """List registrations for an event day with admin or self-only visibility.

    Admins receive the full list needed for check-in management. Non-admin
    callers are intentionally scoped down to their own row.
    """

    statement = (
        select(Registration)
        .options(*REGISTRATION_LOAD_OPTIONS)
        .where(Registration.event_day_id == event_day_id)
        .order_by(Registration.created_at.asc(), Registration.id.asc())
    )

    if not include_all:
        statement = statement.where(Registration.user_id == current_user.id)

    return list(db.scalars(statement).all())


def registration_window_is_open(event_day: EventDay) -> bool:
    """Return whether the event day is currently accepting registrations.

    Both the event-day status and the configured open/close timestamps must
    allow registration before a player can create or cancel a signup.
    """

    if event_day.status != EventDayStatus.OPEN_FOR_REGISTRATION:
        return False

    now = datetime.now()
    if event_day.registration_open_at is not None and now < event_day.registration_open_at:
        return False
    if event_day.registration_close_at is not None and now > event_day.registration_close_at:
        return False
    return True


def create_registration(
    db: Session,
    event_day: EventDay,
    payload: RegistrationCreate,
    current_user: User,
) -> Registration:
    """Create a self-registration for the current authenticated user.

    The function enforces the MVP rule that players can only create one signup
    record per event day and only while the registration window is open.
    """

    if not registration_window_is_open(event_day):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This event day is not open for registration.",
        )

    existing_registration = get_registration_for_user(db, event_day.id, current_user.id)
    if existing_registration is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already registered for this event day.",
        )

    registration = Registration(
        event_day_id=event_day.id,
        user_id=current_user.id,
        registration_type=payload.registration_type,
        note=payload.note,
    )
    db.add(registration)
    db.commit()
    return get_registration_or_404(db, registration.id)


def cancel_registration(db: Session, registration: Registration, current_user: User) -> Registration:
    """Cancel a self-registration while the event day is still open.

    Cancellation is intentionally conservative in Milestone 2: once the window
    closes, only admins should be able to adjust the record.
    """

    if registration.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only cancel your own registration.")

    if not registration_window_is_open(registration.event_day):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This registration can no longer be cancelled.",
        )

    registration.registration_status = RegistrationStatus.CANCELLED
    db.add(registration)
    db.commit()
    return get_registration_or_404(db, registration.id)


def admin_update_registration(
    db: Session,
    registration: Registration,
    payload: RegistrationAdminUpdate,
) -> Registration:
    """Apply an admin-managed update to registration or check-in state.

    Admins can resolve attendance, promote substitutes, or mark absences
    without creating new rows or bypassing the unique registration constraint.
    """

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(registration, field, value)
    db.add(registration)
    db.commit()
    return get_registration_or_404(db, registration.id)
