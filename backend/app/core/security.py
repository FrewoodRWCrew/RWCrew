# This file contains our security-related helper functions:
#   1. Turning a plain-text password into a safely stored "hash", and
#      checking a login attempt against that hash.
#   2. Creating and reading the JWT tokens we use to recognise logged-in
#      users on later requests.
#
# We deliberately use only Python's built-in "hashlib" and "secrets"
# modules for password hashing (instead of an extra third-party library),
# because they need no extra compiled software to install and are trusted,
# well-reviewed parts of the Python standard library.

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import jwt

from app.core.config import settings

# How many random bytes to use for each password's unique "salt".
# A salt makes sure that two users with the same password end up with
# completely different stored hashes.
_SALT_BYTES = 16

# How many times to repeat the hashing calculation. A higher number makes
# password cracking slower for an attacker, at the cost of a small delay
# (a fraction of a second) each time we check a password.
_HASH_ITERATIONS = 260_000


def hash_password(plain_password: str) -> str:
    """Turn a plain-text password into a safe-to-store string.

    The result contains the random salt and the hash together, separated
    by a "$", so we don't need a separate database column for the salt.
    """
    # Generate a fresh random salt for this password.
    salt = secrets.token_hex(_SALT_BYTES)
    # Combine the password and salt using PBKDF2-HMAC-SHA256, a standard,
    # deliberately-slow hashing algorithm designed for passwords.
    digest = hashlib.pbkdf2_hmac(
        "sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), _HASH_ITERATIONS
    )
    # Store the salt and the resulting hash together, as readable hex text.
    return f"{salt}${digest.hex()}"


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """Check whether a plain-text password matches a previously stored hash."""
    # Split the stored value back into its salt and hash parts.
    salt, _, expected_hex = stored_hash.partition("$")
    if not salt or not expected_hex:
        # The stored value isn't in the format we expect, so it can't match.
        return False
    # Redo the same hashing calculation with the candidate password.
    candidate_digest = hashlib.pbkdf2_hmac(
        "sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), _HASH_ITERATIONS
    )
    # Compare the two hashes using a "constant time" comparison, which
    # avoids leaking timing information that could help an attacker guess
    # the password character by character.
    return hmac.compare_digest(candidate_digest.hex(), expected_hex)


def create_access_token(user_id: int) -> str:
    """Create a short-lived JWT that proves who the logged-in user is."""
    return _create_token(user_id, token_type="access", expires_delta=timedelta(minutes=settings.access_token_minutes))


def create_refresh_token(user_id: int) -> str:
    """Create a longer-lived JWT used only to request a new access token."""
    return _create_token(user_id, token_type="refresh", expires_delta=timedelta(days=settings.refresh_token_days))


def _create_token(user_id: int, token_type: Literal["access", "refresh"], expires_delta: timedelta) -> str:
    # The "payload" is the information stored inside the token:
    #   sub   -> the user's id ("subject" of the token)
    #   type  -> whether this is an access or refresh token
    #   iat   -> the moment the token was issued (rounded to the second)
    #   exp   -> the exact moment the token stops being valid
    #   jti   -> a random "token ID", unique to this one token
    #
    # Without "jti", two tokens created for the same user in the same
    # second would end up as the EXACT same text (since "sub"/"type"/"iat"
    # (rounded to the second)/"exp" would then all match too) — which
    # would defeat refresh-token rotation, since the "old" and "new"
    # tokens could no longer be told apart. The random jti guarantees
    # every token we ever issue is unique.
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "jti": secrets.token_hex(16),
    }
    # Sign the payload with our secret key, producing the final token text.
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


class InvalidTokenError(Exception):
    """Raised when a token is missing, expired, malformed, or the wrong type."""


def decode_token(token: str, expected_type: Literal["access", "refresh"]) -> int:
    """Read a JWT and return the user id stored inside it.

    Raises InvalidTokenError if the token is expired, was tampered with,
    or is not the type of token we expected (e.g. someone tried to use a
    refresh token where an access token was required).
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as error:
        # Any problem decoding/verifying the token becomes our own,
        # simpler error type, so the rest of the app doesn't need to know
        # about the PyJWT library's specific exception classes.
        raise InvalidTokenError("Token is invalid or expired") from error

    if payload.get("type") != expected_type:
        raise InvalidTokenError(f"Expected a '{expected_type}' token")

    try:
        return int(payload["sub"])
    except (KeyError, ValueError) as error:
        raise InvalidTokenError("Token is missing a valid user id") from error
