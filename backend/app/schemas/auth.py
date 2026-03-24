"""Pydantic schemas used by authentication endpoints."""

from pydantic import BaseModel, ConfigDict

from app.schemas.user import UserRead


class LoginRequest(BaseModel):
    """Credentials used to obtain a JWT access token."""

    username: str
    password: str


class AuthResponse(BaseModel):
    """Authentication response returned after a successful login.

    The frontend consumes both `user` and `roles` so it can decide where to
    route the user and which navigation branches should be visible.
    """

    access_token: str
    token_type: str = "bearer"
    user: UserRead
    roles: list[str]

    model_config = ConfigDict(from_attributes=True)


class MeResponse(BaseModel):
    """Profile payload returned for the current authenticated user."""

    user: UserRead
    roles: list[str]

    model_config = ConfigDict(from_attributes=True)
