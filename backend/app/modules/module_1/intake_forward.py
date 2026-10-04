# Passing a device CSV on to the OTHER environment (test <-> production).
#
# The Raspberry Pi has one intake connection to the VPS, but the VPS runs a
# test and a production stack, each with its own "Unreaded Tags" folder in
# its own Docker volume that the other cannot reach. Each CSV says in its
# "Mode" column which environment it is meant for; when that is not the
# environment that received it, the file is re-POSTed to the other
# environment's normal intake endpoint (see device_router.py), so it lands
# there through exactly the same checks and duplicate handling.

import logging

import httpx
from fastapi import HTTPException, status

from app.core.config import settings
from app.schemas.tagscan import IntakeUploadResponse

logger = logging.getLogger(__name__)

# Sent along with a forwarded file. The receiving side always stores a file
# carrying it, so a misconfiguration can never bounce a file back and forth.
FORWARDED_HEADER = "X-TagScan-Forwarded"

# How long to wait for the other environment before giving up, in seconds.
REQUEST_TIMEOUT_SECONDS = 30.0

# The Mode values the scanners write, mapped to our environment names
# (compared in lower case).
_MODE_TO_ENVIRONMENT = {
    "test": "test",
    "prod": "production",
    "production": "production",
}


def normalize_environment(mode: str | None) -> str | None:
    """"test"/"prod"/"production" (any case) -> "test" or "production";
    anything else (empty, unknown) -> None, meaning "keep it here".
    """
    if mode is None:
        return None
    return _MODE_TO_ENVIRONMENT.get(mode.strip().lower())


def should_forward(target_environment: str | None, already_forwarded: bool) -> bool:
    """True when this file belongs to the other environment and must be
    passed on instead of stored here.
    """
    # Routing is off when this environment doesn't know its own name.
    if not settings.tagscan_environment:
        return False
    # Unknown/missing Mode, or a file that was already forwarded once: keep it.
    if target_environment is None or already_forwarded:
        return False
    return target_environment != settings.tagscan_environment.strip().lower()


def forward_csv(filename: str, contents: bytes, target_environment: str) -> IntakeUploadResponse:
    """Re-POST the file to the other environment's intake endpoint.

    Raises 503 when forwarding isn't configured and 502 when the other side
    can't be reached or refuses the file. Both are errors to the Pi's
    watcher, so it keeps the file and retries — nothing is ever lost.
    """
    if not settings.tagscan_forward_url or not settings.tagscan_forward_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Forwarding to {target_environment} is not configured",
        )

    # Send it exactly as the Pi would, plus the "already forwarded" marker.
    try:
        response = httpx.post(
            settings.tagscan_forward_url,
            files={"file": (filename, contents, "text/csv")},
            headers={"X-API-Key": settings.tagscan_forward_api_key, FORWARDED_HEADER: "1"},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except httpx.HTTPError as error:
        logger.error("Forwarding %s to %s failed: %s", filename, target_environment, error)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Could not reach the {target_environment} environment"
        ) from error

    if not response.is_success:
        logger.error(
            "Forwarding %s to %s refused: HTTP %s %s", filename, target_environment, response.status_code, response.text
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"The {target_environment} environment refused the file (HTTP {response.status_code})",
        )

    # Report the name the other side stored it under (it may have added a
    # content-hash suffix to avoid a name clash).
    stored_name = response.json().get("filename", filename)
    logger.info("Forwarded %s to %s as %s", filename, target_environment, stored_name)
    return IntakeUploadResponse(status="forwarded", filename=stored_name, environment=target_environment)
