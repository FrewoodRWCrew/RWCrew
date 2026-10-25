# Tests for the karcode: the formula evaluator (module_2/karcode_formula.py)
# and the Karcode Simulator + Instellingen endpoints (module_2/karcode_router.py).

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models.kartracker_settings import KarTrackerSettings
from app.db.models.kartracker_user_role import KarTrackerUserRole
from app.modules.module_2.karcode_formula import KarcodeError, compute_code, validate_formula
from app.modules.module_2.screens import sync_screens
from tests.modules.module_2.conftest import (
    create_kartracker_module,
    create_role_with_permissions,
    create_user,
    grant_module_access,
    login,
)
from tests.modules.module_2.test_initial_delivery import _login_admin

KARCODE_URL = "/api/modules/module-2/karcode"
SETTINGS_URL = "/api/modules/module-2/settings"
PREVIEW_URL = "/api/modules/module-2/settings/karcode/preview"
UPDATE_URL = "/api/modules/module-2/settings/karcode"


# --- Evaluator ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("formula", "kar", "code"),
    [
        # The old Excel sheet: 36*500+3118 = 21118 -> first 4 digits.
        ("LEFT(kar*500+3118; 4)", "36", "2111"),
        ("=left((kar*500)+3118;4)", "36", "2111"),
        ("RIGHT(kar*500+3118; 3)", "36", "118"),
        ("MID(kar*1000; 2; 3)", "36", "600"),
        ("MOD(kar; 7)", "36", "1"),
        # Decimal comma, Excel-style rounding of halves away from zero.
        ("ROUND(kar*0,8; 0)", "36", "29"),
        ("ROUND(2,5; 0)", "1", "3"),
        ("INT(kar/7)", "36", "5"),
        ("2^3+kar", "1", "9"),
        ("kar/4", "10", "2.5"),
        # Text from LEFT is read back as a number in a calculation.
        ("LEFT(kar*500; 2)+1", "36", "19"),
        ("kar", " 036 ", "36"),
    ],
)
def test_formula_computes_the_code(formula: str, kar: str, code: str) -> None:
    assert compute_code(formula, kar) == code


@pytest.mark.parametrize(
    ("formula", "error_code"),
    [
        ("__import__('os')", "invalid_character"),
        ("kar.real", "invalid_syntax"),
        ("LEFT(kar, 4)", "invalid_syntax"),
        ("foo + 1", "unknown_name"),
        ("SUM(kar)", "unknown_function"),
        ("LEFT()", "wrong_arguments"),
        ("1/0", "division_by_zero"),
        ("MOD(kar; 0)", "division_by_zero"),
        ("9^999", "number_too_large"),
        ("10000000^64", "number_too_large"),
        ("LEFT(kar; 0)", "empty_result"),
        ("", "empty_formula"),
        ("1+" * 300 + "1", "too_long"),
    ],
)
def test_formula_refuses_bad_input(formula: str, error_code: str) -> None:
    with pytest.raises(KarcodeError) as raised:
        validate_formula(formula)
    assert raised.value.code == error_code


@pytest.mark.parametrize("kar", ["", "K12", "3.5", "1" * 21])
def test_kar_number_must_be_a_whole_number(kar: str) -> None:
    with pytest.raises(KarcodeError) as raised:
        compute_code("kar", kar)
    assert raised.value.code == "kar_not_numeric"


# --- Endpoints ---------------------------------------------------------------


def _login_with_right(client: TestClient, db_session: Session, **rights: object) -> None:
    """Log in as a plain module user whose role has `rights` on one screen."""
    sync_screens(db_session)
    module = create_kartracker_module(db_session)
    user = create_user(db_session, email="user@example.com")
    grant_module_access(db_session, user, module)
    role = create_role_with_permissions(db_session, name="Role", **rights)
    db_session.add(KarTrackerUserRole(user_id=user.id, role_id=role.id))
    db_session.commit()
    login(client, "user@example.com")


def test_simulator_uses_the_default_and_then_the_saved_formula(client: TestClient, db_session: Session) -> None:
    _login_admin(client, db_session)
    # No row yet (tests don't run migrations) -> the Excel formula.
    assert client.get(KARCODE_URL, params={"kar": "36"}).json() == {"kar": "36", "code": "2111"}
    assert client.get(SETTINGS_URL).json()["karcode_formula"] == "LEFT(kar*500+3118; 4)"

    # Preview doesn't save.
    preview = client.post(PREVIEW_URL, json={"formula": "kar*2", "kar": "36"})
    assert preview.json()["code"] == "72"
    assert db_session.get(KarTrackerSettings, 1) is None

    # Saving stores the formula and its author; the simulator follows it.
    saved = client.put(UPDATE_URL, json={"formula": "  RIGHT(kar*7; 3) "})
    assert saved.status_code == 200
    assert saved.json()["karcode_formula"] == "RIGHT(kar*7; 3)"
    assert saved.json()["karcode_updated_by_name"] == "admin@example.com"
    assert saved.json()["karcode_updated_at"] is not None
    assert client.get(KARCODE_URL, params={"kar": "36"}).json()["code"] == "252"


def test_errors_come_back_as_translatable_codes(client: TestClient, db_session: Session) -> None:
    _login_admin(client, db_session)
    response = client.get(KARCODE_URL, params={"kar": "K12"})
    assert response.status_code == 400
    assert response.json()["detail"] == "kar_not_numeric|K12"

    response = client.put(UPDATE_URL, json={"formula": "SUM(kar)"})
    assert response.status_code == 400
    assert response.json()["detail"] == "unknown_function|SUM"
    # The invalid formula wasn't stored.
    assert client.get(SETTINGS_URL).json()["karcode_formula"] == "LEFT(kar*500+3118; 4)"


def test_simulator_needs_its_own_screen_right(client: TestClient, db_session: Session) -> None:
    _login_with_right(client, db_session, screen_key="kartracker.karcodesimulator", can_view=True)
    assert client.get(KARCODE_URL, params={"kar": "36"}).status_code == 200
    # The simulator right doesn't show (or change) the formula.
    assert client.get(SETTINGS_URL).status_code == 403
    assert client.post(PREVIEW_URL, json={"formula": "kar", "kar": "1"}).status_code == 403
    assert client.put(UPDATE_URL, json={"formula": "kar"}).status_code == 403


def test_settings_view_can_test_but_only_edit_can_save(client: TestClient, db_session: Session) -> None:
    _login_with_right(client, db_session, screen_key="kartracker.settings", can_view=True)
    assert client.get(SETTINGS_URL).status_code == 200
    assert client.post(PREVIEW_URL, json={"formula": "kar", "kar": "1"}).status_code == 200
    assert client.put(UPDATE_URL, json={"formula": "kar"}).status_code == 403
    assert client.get(KARCODE_URL, params={"kar": "36"}).status_code == 403


def test_settings_edit_right_can_save(client: TestClient, db_session: Session) -> None:
    _login_with_right(client, db_session, screen_key="kartracker.settings", can_view=True, can_edit=True)
    assert client.put(UPDATE_URL, json={"formula": "kar+1"}).status_code == 200
    assert db_session.get(KarTrackerSettings, 1).karcode_formula == "kar+1"
