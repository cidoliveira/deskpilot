from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.db.session import get_db


def test_health_reports_ok_when_database_is_reachable(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


class _BrokenSession:
    def execute(self, *_args, **_kwargs):
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))


def test_health_returns_503_when_database_is_down(app, client: TestClient) -> None:
    app.dependency_overrides[get_db] = lambda: _BrokenSession()

    response = client.get("/api/v1/health")

    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "database": "unavailable"}


def test_openapi_docs_are_published(client: TestClient) -> None:
    response = client.get("/api/v1/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "DeskPilot API"


def test_openapi_documents_the_error_envelope(client: TestClient) -> None:
    spec = client.get("/api/v1/openapi.json").json()
    status_change = spec["paths"]["/api/v1/tickets/{ticket_id}/status"]["patch"]["responses"]

    assert {"401", "403", "404", "409", "422"} <= set(status_change)
    assert status_change["409"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ErrorRead"
    }
    assert "429" in spec["paths"]["/api/v1/auth/login"]["post"]["responses"]
