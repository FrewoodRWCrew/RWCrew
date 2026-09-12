# This file reads all the "settings" our backend needs from environment
# variables (values set outside the code, e.g. in a .env file or by the
# hosting server). Keeping settings here means secrets like passwords and
# keys never need to be hard-coded into the rest of the program.

# pydantic-settings gives us a convenient way to declare which settings we
# expect, and to automatically read them from a ".env" file or the real
# operating-system environment variables.
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Tell pydantic-settings to also look inside a file called ".env"
    # (in the backend folder) for these values, in addition to normal
    # environment variables. "extra=ignore" means unrelated variables in
    # that file are simply skipped instead of causing an error.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # The connection string PostgreSQL/SQLAlchemy uses to find our database.
    # Port 5433 (not the Postgres default 5432) is used for local
    # development because another project's database already occupies
    # 5432 on this machine — see docker-compose.yml.
    database_url: str = "postgresql+pg8000://rwcrew:rwcrew_dev_password@localhost:5433/rwcrew"

    # A secret string used to cryptographically sign login tokens (JWTs).
    # Anyone who knows this secret could forge valid login tokens, so in a
    # real deployment this MUST be overridden with a long, random value via
    # an environment variable — never left as this default.
    jwt_secret: str = "change-this-secret-in-your-.env-file"

    # Which "algorithm" (mathematical method) is used to sign tokens.
    jwt_algorithm: str = "HS256"

    # How long a short-lived "access token" stays valid, in minutes.
    # This is the token the frontend sends with every request to prove
    # who the user is.
    access_token_minutes: int = 15

    # How long a longer-lived "refresh token" stays valid, in days.
    # This token is only used to silently obtain a new access token
    # once the short one expires, without forcing the user to log in again.
    refresh_token_days: int = 30

    # Which website(s) are allowed to call this API from a browser
    # (Cross-Origin Resource Sharing). During local development this is
    # the address the Next.js frontend runs on.
    cors_allowed_origins: list[str] = ["http://localhost:3000"]

    # Where TagScan's incoming CSV files currently land. This is a
    # temporary location (see CLAUDE.md/the TagScan module docs) — it's a
    # setting rather than a hard-coded path so it can move later without a
    # code change. Defaults to the "TagScans" folder at the repo root
    # (this file lives at backend/app/core/config.py, so parents[3] is the
    # repo root).
    tagscan_source_dir: str = str(Path(__file__).resolve().parents[3] / "TagScans")

    # The largest CSV file TagScan's device-intake endpoint
    # (POST /api/public/tagscan-intake) will accept from a Raspberry Pi's
    # watcher script, in megabytes. Deliberately generous for a CSV of RFID
    # scan lines, while still rejecting an obviously-wrong/corrupt upload.
    tagscan_intake_max_file_mb: int = 20


# Create one shared Settings object that the rest of the app can import
# and reuse, instead of re-reading the environment every time.
settings = Settings()
