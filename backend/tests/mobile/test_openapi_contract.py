# Guards the phone app's API contract (mobile/openapi/mobile-v1.json): it
# must only describe phone endpoints, and it must match what the backend
# currently serves, so the app's generated client can't silently go stale.

import json

from app.cli.export_mobile_openapi import MOBILE_PREFIX, OUTPUT_PATH, build_mobile_contract


def test_contract_only_contains_phone_endpoints() -> None:
    contract = build_mobile_contract()

    assert contract["paths"]
    assert all(path.startswith(MOBILE_PREFIX) for path in contract["paths"])


def test_contract_has_no_delete_or_web_only_endpoints() -> None:
    contract = build_mobile_contract()

    for path, spec in contract["paths"].items():
        assert "delete" not in spec, f"{path} must not offer DELETE on the phone"
        assert "/pdf" not in path
    assert not any("/roles" in path or "/intervention-statuses" in path or "/teamkar" in path for path in contract["paths"])


def test_committed_contract_is_up_to_date() -> None:
    committed = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))

    assert committed == build_mobile_contract(), (
        "mobile/openapi/mobile-v1.json is out of date. Regenerate it with: "
        ".venv/Scripts/python -m app.cli.export_mobile_openapi (from backend/), then run npm run gen:api in mobile/."
    )
