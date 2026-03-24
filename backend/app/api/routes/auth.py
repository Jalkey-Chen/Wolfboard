from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.core.security import create_access_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import AuthResponse, LoginRequest, MeResponse
from app.schemas.user import UserRead
from app.services.auth import authenticate_user


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    """Authenticate a user and return a JWT plus the resolved role list."""

    user = authenticate_user(db, payload.username, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    access_token = create_access_token(str(user.id))
    user_data = UserRead.model_validate(user)

    return AuthResponse(
        access_token=access_token,
        token_type="bearer",
        user=user_data,
        roles=user.roles,
    )


@router.get("/me", response_model=MeResponse)
def read_current_user(current_user: User = Depends(get_current_user)) -> MeResponse:
    """Return the authenticated user profile and role keys."""

    return MeResponse(
        user=UserRead.model_validate(current_user),
        roles=current_user.roles,
    )
