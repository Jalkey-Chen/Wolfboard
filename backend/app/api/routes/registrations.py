"""Registration mutation endpoints for self-cancel and admin check-in updates."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.registration import RegistrationAdminUpdate, RegistrationRead
from app.services.registration import admin_update_registration, cancel_registration, get_registration_or_404


router = APIRouter(prefix="/registrations", tags=["registrations"])


@router.patch("/{registration_id}", response_model=RegistrationRead)
def update_registration_endpoint(
    registration_id: int,
    payload: RegistrationAdminUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> RegistrationRead:
    """Allow admins to update registration and check-in fields."""

    _ = current_user
    registration = get_registration_or_404(db, registration_id)
    registration = admin_update_registration(db, registration, payload)
    return RegistrationRead.model_validate(registration)


@router.patch("/{registration_id}/cancel", response_model=RegistrationRead)
def cancel_registration_endpoint(
    registration_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RegistrationRead:
    """Allow a user to cancel their own registration while registration is open."""

    registration = get_registration_or_404(db, registration_id)
    registration = cancel_registration(db, registration, current_user)
    return RegistrationRead.model_validate(registration)
