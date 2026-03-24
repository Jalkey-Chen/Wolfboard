"""Small regression tests for the Milestone 1 security helpers."""

from app.core.security import create_access_token, decode_access_token, get_password_hash, verify_password


def test_password_hash_roundtrip() -> None:
    """Passwords should hash irreversibly and still verify correctly."""

    hashed_password = get_password_hash("password123")

    assert hashed_password != "password123"
    assert verify_password("password123", hashed_password)


def test_access_token_roundtrip() -> None:
    """JWT helper functions should preserve the stored subject claim."""

    token = create_access_token("42")

    assert decode_access_token(token) == "42"
