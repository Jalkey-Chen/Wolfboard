"""Reusable FastAPI dependencies for authentication and authorization."""

from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.services.auth import get_user_by_id


oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_prefix}/auth/login")


def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> User:
    """Resolve the authenticated user from a bearer token.

    The dependency performs three checks:
    1. the token must be a valid JWT issued by this service,
    2. the subject must map to an existing user,
    3. the user must still be in an active account state.
    """

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        subject = decode_access_token(token)
        user_id = int(subject)
    except (JWTError, ValueError) as exc:
        raise credentials_exception from exc

    user = get_user_by_id(db, user_id)
    if user is None or user.account_status != "active":
        raise credentials_exception
    return user


def require_role(role_key: str) -> Callable[[User], User]:
    """Require the authenticated user to hold a specific system role.

    This is intentionally role-only for Milestone 1. Resource ownership checks
    such as "judge must own the game" can be composed on top of it in later
    milestones without changing the authentication contract.
    """

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if role_key not in current_user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"The '{role_key}' role is required for this action.",
            )
        return current_user

    return dependency
