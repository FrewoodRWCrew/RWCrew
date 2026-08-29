# These tests check the lowest-level security building blocks in
# app/core/security.py: password hashing/verification, and creating and
# reading login tokens (JWTs). Everything else (login, access rights)
# depends on these working correctly, so we test them in isolation first.

import pytest

from app.core.security import (
    InvalidTokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_hashing_the_same_password_twice_gives_different_hashes() -> None:
    # Two random salts should make the stored hashes look different, even
    # though both were made from the exact same password.
    first_hash = hash_password("correct horse battery staple")
    second_hash = hash_password("correct horse battery staple")

    assert first_hash != second_hash


def test_verify_password_accepts_the_correct_password() -> None:
    stored_hash = hash_password("correct horse battery staple")

    assert verify_password("correct horse battery staple", stored_hash) is True


def test_verify_password_rejects_the_wrong_password() -> None:
    stored_hash = hash_password("correct horse battery staple")

    assert verify_password("some other password", stored_hash) is False


def test_access_token_round_trip_returns_the_same_user_id() -> None:
    token = create_access_token(user_id=42)

    assert decode_token(token, expected_type="access") == 42


def test_a_refresh_token_is_rejected_where_an_access_token_is_expected() -> None:
    # This guards against a security bug where a long-lived refresh token
    # could be used directly as if it were a short-lived access token.
    refresh_token = create_refresh_token(user_id=42)

    with pytest.raises(InvalidTokenError):
        decode_token(refresh_token, expected_type="access")


def test_a_tampered_token_is_rejected() -> None:
    token = create_access_token(user_id=42)
    # Flip one character roughly in the middle of the token (inside its
    # payload section), simulating someone trying to modify the token's
    # contents without knowing our secret signing key. We avoid the very
    # last character of a JWT, since a couple of its bits are unused
    # base64 padding and changing only those wouldn't actually alter the
    # token's real content.
    middle_index = len(token) // 2
    original_character = token[middle_index]
    replacement_character = "a" if original_character != "a" else "b"
    tampered_token = token[:middle_index] + replacement_character + token[middle_index + 1 :]

    with pytest.raises(InvalidTokenError):
        decode_token(tampered_token, expected_type="access")
