# The token the wristband company sends in every webhook message: one per
# environment, generated on the Scans module's Settings screen and stored only
# as a hash in the single Tagscan_settings row. The key itself is shown once.
# A plain SHA-256 is enough (and fast, this runs on every scan) because the key
# is 32 random bytes, not something a person chose. Without a token every
# webhook message is refused. Never commits.

import hashlib
import hmac
import secrets
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.models.tagscan_settings import TagscanSettings
from app.modules.module_1.file_browser import SETTINGS_ROW_ID

TOKEN_PREFIX = "wristband_"


def hash_token(token: str) -> str:
    """What's stored for a token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _settings_row(db: Session) -> TagscanSettings:
    """The single settings row (created when missing)."""
    row = db.get(TagscanSettings, SETTINGS_ROW_ID)
    if row is None:
        row = TagscanSettings(id=SETTINGS_ROW_ID)
        db.add(row)
        db.flush()
    return row


def token_status(db: Session) -> TagscanSettings | None:
    """The row holding the token's state, if there is one (never creates it)."""
    return db.get(TagscanSettings, SETTINGS_ROW_ID)


def generate_token(db: Session) -> str:
    """Make a new token, which replaces the old one immediately, and return it:
    this is the only moment the key exists in readable form."""
    token = f"{TOKEN_PREFIX}{secrets.token_urlsafe(32)}"
    row = _settings_row(db)
    row.wristband_token_hash = hash_token(token)
    row.wristband_token_generated_at = datetime.now(timezone.utc)
    row.wristband_token_last_used_at = None
    db.flush()
    return token


def revoke_token(db: Session) -> None:
    """Remove the token: every webhook message is refused from now on."""
    row = _settings_row(db)
    row.wristband_token_hash = None
    row.wristband_token_generated_at = None
    row.wristband_token_last_used_at = None
    db.flush()


def token_is_valid(db: Session, token: str) -> bool:
    """Whether this is the current token, compared in constant time; a valid
    one is noted as last used."""
    row = token_status(db)
    if row is None or not row.wristband_token_hash or not token:
        return False
    if not hmac.compare_digest(hash_token(token), row.wristband_token_hash):
        return False
    row.wristband_token_last_used_at = datetime.now(timezone.utc)
    return True
