"""Security utilities for password hashing and JWT token management."""

from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings


password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against its persisted bcrypt hash."""

    return password_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password for persistent storage.

    Passwords are never stored in plaintext. The returned value can be written
    directly into the `users.password_hash` column.
    """

    return password_context.hash(password)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT access token.

    The `subject` is the authenticated user ID serialized as a string. The
    expiration time defaults to the configured access token lifetime.
    """

    expire = datetime.now(UTC) + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> str:
    """Decode a JWT access token and return the subject claim.

    The caller is responsible for turning the subject back into a database
    record and deciding whether the resulting user is still allowed to log in.
    """

    payload = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )
    subject = payload.get("sub")
    if subject is None:
        raise JWTError("Token is missing the subject claim.")
    return subject
