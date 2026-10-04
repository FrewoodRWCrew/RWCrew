# Tests for the device-facing CSV push endpoint
# (POST /api/public/tagscan-intake) — API-key auth (not user login),
# landing a file into "Unreaded Tags", and the three-way duplicate check
# that makes a retried upload safe (see app/modules/module_1/device_router.py).

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.db.models.product_type import ProductType
from app.db.models.scanner import Scanner
from app.db.models.tag_header_data import TagHeaderData

UPLOAD_URL = "/api/public/tagscan-intake"


@pytest.fixture()
def source_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(settings, "tagscan_source_dir", str(tmp_path))
    return tmp_path


def _create_product_type(db_session: Session) -> ProductType:
    product_type = ProductType(name="Reader Hardware")
    db_session.add(product_type)
    db_session.commit()
    db_session.refresh(product_type)
    return product_type


def _create_scanner_with_api_key(db_session: Session) -> tuple[Scanner, str]:
    product_type = _create_product_type(db_session)
    scanner = Scanner(scanner="Scan-01", type_id=product_type.id, technology="Raspberry Pi 4")
    db_session.add(scanner)
    db_session.commit()
    db_session.refresh(scanner)

    api_key = f"module1_{scanner.id}_secret-value"
    scanner.api_key_hash = hash_password(api_key)
    db_session.commit()
    return scanner, api_key


def _upload(client: TestClient, api_key: str, *, filename: str = "scan.csv", content: bytes = b"EPC,RSSI\nABC,70\n"):
    return client.post(UPLOAD_URL, headers={"X-API-Key": api_key}, files={"file": (filename, content, "text/csv")})


def test_upload_without_api_key_header_is_rejected(client: TestClient) -> None:
    response = client.post(UPLOAD_URL, files={"file": ("scan.csv", b"data", "text/csv")})

    assert response.status_code in (401, 422)


def test_upload_with_malformed_api_key_returns_401(client: TestClient, db_session: Session, source_dir: Path) -> None:
    _create_scanner_with_api_key(db_session)

    response = _upload(client, "not-a-real-key")

    assert response.status_code == 401


def test_upload_with_wrong_secret_returns_401(client: TestClient, db_session: Session, source_dir: Path) -> None:
    scanner, _api_key = _create_scanner_with_api_key(db_session)

    response = _upload(client, f"module1_{scanner.id}_wrong-secret")

    assert response.status_code == 401


def test_upload_for_unknown_scanner_id_returns_401(client: TestClient, db_session: Session, source_dir: Path) -> None:
    response = _upload(client, "module1_999999_whatever")

    assert response.status_code == 401


def test_upload_with_non_csv_filename_returns_400(client: TestClient, db_session: Session, source_dir: Path) -> None:
    _scanner, api_key = _create_scanner_with_api_key(db_session)

    response = _upload(client, api_key, filename="scan.txt")

    assert response.status_code == 400


def test_oversized_upload_returns_413(
    client: TestClient, db_session: Session, source_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "tagscan_intake_max_file_mb", 0)
    _scanner, api_key = _create_scanner_with_api_key(db_session)

    response = _upload(client, api_key, content=b"EPC,RSSI\nABC,70\n")

    assert response.status_code == 413


def test_successful_upload_lands_the_file_and_updates_last_used(
    client: TestClient, db_session: Session, source_dir: Path
) -> None:
    scanner, api_key = _create_scanner_with_api_key(db_session)

    response = _upload(client, api_key, content=b"EPC,RSSI\nABC,70\n")

    assert response.status_code == 201
    body = response.json()
    assert body == {"status": "received", "filename": "scan.csv"}

    saved_file = source_dir / "Unreaded Tags" / "scan.csv"
    assert saved_file.read_bytes() == b"EPC,RSSI\nABC,70\n"
    # No leftover temp file from the atomic-write step.
    assert not (source_dir / "Unreaded Tags" / "scan.csv.uploading").exists()

    db_session.refresh(scanner)
    assert scanner.api_key_last_used_at is not None


def test_reuploading_an_unreaded_file_is_a_safe_duplicate(
    client: TestClient, db_session: Session, source_dir: Path
) -> None:
    _scanner, api_key = _create_scanner_with_api_key(db_session)
    _upload(client, api_key)

    response = _upload(client, api_key)

    assert response.status_code == 201
    assert response.json() == {"status": "duplicate", "filename": "scan.csv"}


def test_reuploading_a_file_already_moved_to_read_tags_is_a_safe_duplicate(
    client: TestClient, db_session: Session, source_dir: Path
) -> None:
    _scanner, api_key = _create_scanner_with_api_key(db_session)
    readed_dir = source_dir / "Read Tags"
    readed_dir.mkdir(parents=True)
    (readed_dir / "scan.csv").write_bytes(b"EPC,RSSI\nABC,70\n")

    response = _upload(client, api_key, content=b"EPC,RSSI\nABC,70\n")

    assert response.status_code == 201
    assert response.json()["status"] == "duplicate"
    # The already-processed file in Read Tags is left untouched.
    assert (readed_dir / "scan.csv").read_bytes() == b"EPC,RSSI\nABC,70\n"
    assert not (source_dir / "Unreaded Tags" / "scan.csv").exists()


def test_same_filename_with_different_content_is_stored_not_dropped(
    client: TestClient, db_session: Session, source_dir: Path
) -> None:
    _scanner, api_key = _create_scanner_with_api_key(db_session)
    _upload(client, api_key, content=b"EPC,RSSI\nABC,70\n")

    response = _upload(client, api_key, content=b"EPC,RSSI\nXYZ,55\n")

    # The second, different file must not be lost: it lands under a
    # content-hash name next to the original, which stays untouched.
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "received"
    assert body["filename"] != "scan.csv"
    assert body["filename"].startswith("scan__") and body["filename"].endswith(".csv")
    assert (source_dir / "Unreaded Tags" / "scan.csv").read_bytes() == b"EPC,RSSI\nABC,70\n"
    assert (source_dir / "Unreaded Tags" / body["filename"]).read_bytes() == b"EPC,RSSI\nXYZ,55\n"


def test_retrying_a_content_conflicting_upload_is_a_safe_duplicate(
    client: TestClient, db_session: Session, source_dir: Path
) -> None:
    _scanner, api_key = _create_scanner_with_api_key(db_session)
    _upload(client, api_key, content=b"EPC,RSSI\nABC,70\n")
    first = _upload(client, api_key, content=b"EPC,RSSI\nXYZ,55\n")

    retry = _upload(client, api_key, content=b"EPC,RSSI\nXYZ,55\n")

    assert retry.status_code == 201
    assert retry.json() == {"status": "duplicate", "filename": first.json()["filename"]}
    # Exactly the original plus the one de-conflicted copy — no third file.
    assert len(list((source_dir / "Unreaded Tags").iterdir())) == 2


def test_reuploading_a_file_already_logged_as_header_data_is_a_safe_duplicate(
    client: TestClient, db_session: Session, source_dir: Path
) -> None:
    _scanner, api_key = _create_scanner_with_api_key(db_session)
    db_session.add(TagHeaderData(filename="scan.csv", line_count=1))
    db_session.commit()

    response = _upload(client, api_key)

    assert response.status_code == 201
    assert response.json()["status"] == "duplicate"
    assert not (source_dir / "Unreaded Tags" / "scan.csv").exists()


def test_upload_rejects_a_filename_trying_to_escape_the_intake_folder(
    client: TestClient, db_session: Session, source_dir: Path
) -> None:
    _scanner, api_key = _create_scanner_with_api_key(db_session)

    response = _upload(client, api_key, filename="../../evil.csv")

    # Path(...).name strips any directory components, so this lands as a
    # plain "evil.csv" inside Unreaded Tags rather than escaping it.
    assert response.status_code == 201
    assert response.json()["filename"] == "evil.csv"
    assert (source_dir / "Unreaded Tags" / "evil.csv").exists()
    assert not (source_dir.parent / "evil.csv").exists()


# --- Routing by the CSV's "Mode" column (test <-> production) ---------------
# See app/modules/module_1/intake_forward.py. The other environment is never
# really called: httpx.post is replaced by a fake that records the call.

PROD_CSV = b"Scanner,Mode,EPC\nScan-01,PROD,ABC\n"
TEST_CSV = b"Scanner,Mode,EPC\nScan-01,test,ABC\n"


class _FakeResponse:
    def __init__(self, status_code: int, body: dict) -> None:
        self.status_code = status_code
        self.is_success = 200 <= status_code < 300
        self._body = body
        self.text = str(body)

    def json(self) -> dict:
        return self._body


@pytest.fixture()
def routing(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    """This backend acts as "test", forwarding to a fake production; returns
    the list of forwarded calls.
    """
    monkeypatch.setattr(settings, "tagscan_environment", "test")
    monkeypatch.setattr(settings, "tagscan_forward_url", "https://prod.example/api/public/tagscan-intake")
    monkeypatch.setattr(settings, "tagscan_forward_api_key", "module1_7_prod-secret")
    calls: list[dict] = []

    def fake_post(url: str, **kwargs) -> _FakeResponse:
        calls.append({"url": url, **kwargs})
        filename = kwargs["files"]["file"][0]
        return _FakeResponse(201, {"status": "received", "filename": filename})

    monkeypatch.setattr("app.modules.module_1.intake_forward.httpx.post", fake_post)
    return calls


def test_csv_for_the_other_environment_is_forwarded_not_stored(
    client: TestClient, db_session: Session, source_dir: Path, routing: list[dict]
) -> None:
    _scanner, api_key = _create_scanner_with_api_key(db_session)

    response = _upload(client, api_key, content=PROD_CSV)

    assert response.status_code == 201
    assert response.json() == {"status": "forwarded", "filename": "scan.csv", "environment": "production"}
    assert len(routing) == 1
    assert routing[0]["url"] == "https://prod.example/api/public/tagscan-intake"
    assert routing[0]["headers"] == {"X-API-Key": "module1_7_prod-secret", "X-TagScan-Forwarded": "1"}
    assert routing[0]["files"]["file"][1] == PROD_CSV
    assert not (source_dir / "Unreaded Tags" / "scan.csv").exists()


def test_csv_for_this_environment_is_stored_here(
    client: TestClient, db_session: Session, source_dir: Path, routing: list[dict]
) -> None:
    _scanner, api_key = _create_scanner_with_api_key(db_session)

    response = _upload(client, api_key, content=TEST_CSV)

    assert response.json() == {"status": "received", "filename": "scan.csv"}
    assert routing == []
    assert (source_dir / "Unreaded Tags" / "scan.csv").read_bytes() == TEST_CSV


@pytest.mark.parametrize(
    "content",
    [
        b"Scanner,EPC\nScan-01,ABC\n",  # no Mode column (older CSV)
        b"Scanner,Mode,EPC\nScan-01,,ABC\n",  # Mode empty
        b"Scanner,Mode,EPC\nScan-01,staging,ABC\n",  # unknown Mode
    ],
)
def test_csv_without_a_known_mode_is_stored_here(
    client: TestClient, db_session: Session, source_dir: Path, routing: list[dict], content: bytes
) -> None:
    _scanner, api_key = _create_scanner_with_api_key(db_session)

    response = _upload(client, api_key, content=content)

    assert response.json()["status"] == "received"
    assert routing == []


def test_routing_is_off_when_this_environment_has_no_name(
    client: TestClient,
    db_session: Session,
    source_dir: Path,
    routing: list[dict],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "tagscan_environment", "")
    _scanner, api_key = _create_scanner_with_api_key(db_session)

    response = _upload(client, api_key, content=PROD_CSV)

    assert response.json()["status"] == "received"
    assert routing == []


def test_an_already_forwarded_file_is_always_stored(
    client: TestClient, db_session: Session, source_dir: Path, routing: list[dict]
) -> None:
    _scanner, api_key = _create_scanner_with_api_key(db_session)

    response = client.post(
        UPLOAD_URL,
        headers={"X-API-Key": api_key, "X-TagScan-Forwarded": "1"},
        files={"file": ("scan.csv", PROD_CSV, "text/csv")},
    )

    # Even though Mode names the other environment: no ping-pong.
    assert response.json()["status"] == "received"
    assert routing == []
    assert (source_dir / "Unreaded Tags" / "scan.csv").exists()


def test_forwarding_without_configuration_returns_503(
    client: TestClient,
    db_session: Session,
    source_dir: Path,
    routing: list[dict],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "tagscan_forward_api_key", "")
    _scanner, api_key = _create_scanner_with_api_key(db_session)

    response = _upload(client, api_key, content=PROD_CSV)

    assert response.status_code == 503
    assert routing == []
    assert not (source_dir / "Unreaded Tags" / "scan.csv").exists()


def test_forwarding_refused_by_the_other_side_returns_502(
    client: TestClient, db_session: Session, source_dir: Path, monkeypatch: pytest.MonkeyPatch, routing: list[dict]
) -> None:
    monkeypatch.setattr(
        "app.modules.module_1.intake_forward.httpx.post",
        lambda url, **kwargs: _FakeResponse(401, {"detail": "Invalid API key"}),
    )
    _scanner, api_key = _create_scanner_with_api_key(db_session)

    response = _upload(client, api_key, content=PROD_CSV)

    # An error makes the Pi keep the file and retry later.
    assert response.status_code == 502
    assert not (source_dir / "Unreaded Tags" / "scan.csv").exists()


def test_forwarding_network_error_returns_502(
    client: TestClient, db_session: Session, source_dir: Path, monkeypatch: pytest.MonkeyPatch, routing: list[dict]
) -> None:
    import httpx

    def failing_post(url: str, **kwargs):
        raise httpx.ConnectError("unreachable")

    monkeypatch.setattr("app.modules.module_1.intake_forward.httpx.post", failing_post)
    _scanner, api_key = _create_scanner_with_api_key(db_session)

    response = _upload(client, api_key, content=PROD_CSV)

    assert response.status_code == 502
    assert not (source_dir / "Unreaded Tags" / "scan.csv").exists()


def test_read_csv_mode_and_normalize_environment() -> None:
    from app.modules.module_1.intake_forward import normalize_environment
    from app.modules.module_1.tag_line_data import read_csv_mode

    # A leading BOM doesn't hide the header; the first non-empty Mode wins.
    assert read_csv_mode(b"\xef\xbb\xbfScanner,Mode\nA,\nB, Prod \n") == "Prod"
    assert read_csv_mode(b"Scanner,EPC\nA,1\n") is None

    assert normalize_environment("TEST") == "test"
    assert normalize_environment("prod") == "production"
    assert normalize_environment("Production") == "production"
    assert normalize_environment("staging") is None
    assert normalize_environment(None) is None
