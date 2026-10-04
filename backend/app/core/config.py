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

    # The absolute lifetime of a login session, in hours. The refresh token
    # silently renews the short access token, but only until this many hours
    # after the moment the password was entered; rotating the refresh token
    # never extends it. After that the user must log in again, so the login
    # history reflects real, recent logins (no session left open overnight).
    session_max_hours: int = 6

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

    # The Raspberry Pi has only one intake connection to the VPS, but each CSV
    # says in its "Mode" column whether it is meant for "test" or
    # "production". tagscan_environment is THIS environment's own name; empty
    # (local dev, tests) switches that routing off and every file is simply
    # stored here. A file whose Mode names the other environment is passed on
    # to tagscan_forward_url (the other environment's intake endpoint) with
    # tagscan_forward_api_key (a scanner API key generated ON that other
    # environment, since keys only work where they were made). See
    # app/modules/module_1/intake_forward.py.
    tagscan_environment: str = ""
    tagscan_forward_url: str = ""
    tagscan_forward_api_key: str = ""

    # Outgoing email (see app/core/mail.py), sent through Resend's HTTP API
    # (https://resend.com). The API key is secret and set per environment in
    # the server's .env; left empty (the default, and in local dev/tests),
    # every mail is simply skipped with a log line instead of failing.
    resend_api_key: str = ""
    # The sender shown on every mail, e.g. "RWCrew <noreply@rwcrew.eu>". Its
    # domain must be verified in the Resend account.
    mail_from: str = ""
    # Put in front of every subject, e.g. "[TEST] " on test.rwcrew.eu, so a
    # mail from the test environment can't be mistaken for a real one.
    mail_subject_prefix: str = ""
    # The public address of the web app (e.g. "https://rwcrew.eu"), used to
    # put a clickable "open in RWCrew" link in mails and for the phone app's
    # install link and QR code (module-10). Empty = no link / no QR code.
    app_public_url: str = ""
    # The deployed version: commit date (Belgian time, "2026.10.04") and short
    # commit hash, exported by deploy/scripts/deploy.sh. Empty locally.
    app_commit: str = ""
    app_commit_date: str = ""


# Create one shared Settings object that the rest of the app can import
# and reuse, instead of re-reading the environment every time.
settings = Settings()
