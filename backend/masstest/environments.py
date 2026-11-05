# The environments a mass test can run against: the backend's base address
# (the API lives under /api on each of them) and the frontend address the
# screen check opens.

from dataclasses import dataclass


@dataclass(frozen=True)
class Environment:
    """One place the mass test can load data into."""

    key: str
    api_url: str
    web_url: str
    # Production needs extra confirmation (see __main__.py).
    is_production: bool = False


ENVIRONMENTS = {
    "local": Environment("local", "http://localhost:8020", "http://localhost:3000"),
    "test": Environment("test", "https://test.rwcrew.eu", "https://test.rwcrew.eu"),
    "prod": Environment("prod", "https://rwcrew.eu", "https://rwcrew.eu", is_production=True),
}
