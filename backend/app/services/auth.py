"""Authentication-related database access helpers."""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

import app.models  # noqa: F401
from app.core.security import verify_password
from app.models.user import User
from app.models.user_role import UserRole


ROLE_LOAD_OPTIONS = (
    selectinload(User.user_roles).selectinload(UserRole.role),
)


def get_user_by_username(db: Session, username: str) -> User | None:
    """Fetch a user and eagerly load assigned roles for authentication.

    Eager loading avoids additional lazy queries when the endpoint needs to
    serialize the user's role list immediately after authentication.
    """

    statement = (
        select(User)
        .options(*ROLE_LOAD_OPTIONS)
        .where(User.username == username)
    )
    return db.scalar(statement)


def get_user_by_id(db: Session, user_id: int) -> User | None:
    """Fetch a user and eagerly load assigned roles by primary key."""

    statement = select(User).options(*ROLE_LOAD_OPTIONS).where(User.id == user_id)
    return db.scalar(statement)


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    """Authenticate an active user with a username and password.

    A user must exist, be active, and provide a valid password hash match. The
    function returns `None` instead of raising so API handlers can shape the
    final HTTP response consistently.
    """

    user = get_user_by_username(db, username)
    if user is None:
        return None
    if user.account_status != "active":
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user
