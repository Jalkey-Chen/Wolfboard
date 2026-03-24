from app.core.security import create_access_token, decode_access_token, get_password_hash, verify_password


def test_password_hash_roundtrip() -> None:
    hashed_password = get_password_hash("password123")

    assert hashed_password != "password123"
    assert verify_password("password123", hashed_password)


def test_access_token_roundtrip() -> None:
    token = create_access_token("42")

    assert decode_access_token(token) == "42"
