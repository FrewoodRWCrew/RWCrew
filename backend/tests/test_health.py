# Tests for /api/health: the basic "is the API up" check, which also reports
# the deployed version (commit date · short hash) set by deploy.sh.

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings


def test_health_reports_dev_without_a_deployed_version(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "dev"}


def test_health_reports_the_deployed_version(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "app_commit", "97cdc36")
    monkeypatch.setattr(settings, "app_commit_date", "2026.10.04")

    assert client.get("/api/health").json()["version"] == "2026.10.04 · 97cdc36"
