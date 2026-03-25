"""Directory-style user queries used by admin management screens."""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole


def list_judge_capable_users(db: Session) -> list[User]:
    """Return users who hold the `judge` system role.

    The admin UI uses this directory to assign a specific responsible judge to
    each game without exposing a raw free-form user-id input.
    """

    statement = (
        select(User)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .options(selectinload(User.user_roles).selectinload(UserRole.role))
        .where(Role.role_key == "judge", User.account_status == "active")
        .order_by(User.display_name.asc(), User.id.asc())
    )
    return list(db.scalars(statement).unique().all())
