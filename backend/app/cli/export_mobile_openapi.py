# Writes the phone app's API contract to mobile/openapi/mobile-v1.json: the
# OpenAPI description of ONLY the /api/mobile/v1 endpoints (plus the data
# shapes they use). The mobile app generates its typed API client from this
# file (npm run gen:api, inside mobile/), so it is the one and only link
# between the backend and the app — no source code is shared.
#
# Run from the backend/ folder after changing anything under app/mobile/:
#   .venv/Scripts/python -m app.cli.export_mobile_openapi
# A backend test (tests/mobile/test_openapi_contract.py) fails when the
# committed file is out of date, so the two can't silently drift apart.

import json
from pathlib import Path

from app.main import app

MOBILE_PREFIX = "/api/mobile/v1"

# backend/app/cli/export_mobile_openapi.py -> parents[3] is the repo root.
OUTPUT_PATH = Path(__file__).resolve().parents[3] / "mobile" / "openapi" / "mobile-v1.json"


def _collect_refs(node: object, found: set[str]) -> None:
    """Find every "#/components/schemas/<Name>" reference inside a JSON tree."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "$ref" and isinstance(value, str) and value.startswith("#/components/schemas/"):
                found.add(value.rsplit("/", 1)[1])
            else:
                _collect_refs(value, found)
    elif isinstance(node, list):
        for item in node:
            _collect_refs(item, found)


def build_mobile_contract() -> dict:
    """The full OpenAPI document, trimmed down to the phone's endpoints."""
    full = app.openapi()

    # Keep only the phone's paths.
    paths = {path: spec for path, spec in full["paths"].items() if path.startswith(MOBILE_PREFIX)}

    # Keep only the data shapes those paths use, directly or through other
    # shapes, so web-only shapes never leak into the phone's contract.
    needed: set[str] = set()
    _collect_refs(paths, needed)
    all_schemas = full.get("components", {}).get("schemas", {})
    pending = list(needed)
    while pending:
        name = pending.pop()
        found: set[str] = set()
        _collect_refs(all_schemas.get(name, {}), found)
        for other in found - needed:
            needed.add(other)
            pending.append(other)

    return {
        "openapi": full["openapi"],
        "info": {"title": "RW Crew mobile API", "version": "v1"},
        "paths": paths,
        "components": {"schemas": {name: all_schemas[name] for name in sorted(needed) if name in all_schemas}},
    }


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    # sort_keys + trailing newline keep the file stable, so git diffs only
    # show real API changes.
    OUTPUT_PATH.write_text(json.dumps(build_mobile_contract(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
