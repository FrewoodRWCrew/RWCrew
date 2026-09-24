# The "version gate": lets the backend refuse requests from smartphone app
# builds that are too old to talk to the current API safely. Old builds stay
# installed on phones for a long time (app-store updates aren't instant), so
# the API needs a way to say "please update" instead of misbehaving.

from fastapi import Header, HTTPException, status

from app.core.config import settings


def parse_version(value: str) -> tuple[int, int, int] | None:
    """Turn "1.4.0", "v1.4.0" or "1.4.0-test.3" into (1, 4, 0); None if unreadable."""
    # Drop a leading "v" and any "-prerelease"/"+build" suffix.
    cleaned = value.strip().lstrip("vV").split("-")[0].split("+")[0]
    parts = cleaned.split(".")
    if not 1 <= len(parts) <= 3 or not all(part.isdigit() for part in parts):
        return None
    # Pad short versions ("1.4" -> 1.4.0) so tuples always compare cleanly.
    numbers = [int(part) for part in parts] + [0] * (3 - len(parts))
    return (numbers[0], numbers[1], numbers[2])


def require_supported_app_version(x_app_version: str | None = Header(default=None)) -> None:
    """Reject the request with 426 if the app is older than the minimum.

    Add this as a dependency on every phone router. With the default
    minimum ("0.0.0") nothing is ever rejected.
    """
    minimum = parse_version(settings.mobile_min_app_version)
    if minimum is None or minimum == (0, 0, 0):
        return

    # A minimum is configured, so the app MUST tell us its version.
    current = parse_version(x_app_version) if x_app_version else None
    if current is None or current < minimum:
        raise HTTPException(
            status_code=status.HTTP_426_UPGRADE_REQUIRED,
            detail=f"Please update the RWCrew app (minimum version {settings.mobile_min_app_version})",
        )
