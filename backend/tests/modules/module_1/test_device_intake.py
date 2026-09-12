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
    (readed_dir / "scan.csv").write_bytes(b"already processed")

    response = _upload(client, api_key)

    assert response.status_code == 201
    assert response.json()["status"] == "duplicate"
    # The already-processed file in Read Tags is left untouched.
    assert (readed_dir / "scan.csv").read_bytes() == b"already processed"
    assert not (source_dir / "Unreaded Tags" / "scan.csv").exists()


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
