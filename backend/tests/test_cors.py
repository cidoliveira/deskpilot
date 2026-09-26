from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app

PREFLIGHT = {
    "Access-Control-Request-Method": "GET",
    "Access-Control-Request-Headers": "Authorization",
}


def _client(cors_origins: str) -> TestClient:
    settings = get_settings().model_copy(update={"cors_origins": cors_origins})
    return TestClient(create_app(settings))


def test_configured_origin_may_call_the_api() -> None:
    client = _client("https://deskpilot.example.com, https://admin.example.com")

    response = client.options(
        "/api/v1/health", headers={"Origin": "https://admin.example.com", **PREFLIGHT}
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://admin.example.com"
    assert "access-control-allow-credentials" not in response.headers


def test_other_origins_are_not_allowed() -> None:
    client = _client("https://deskpilot.example.com")

    response = client.options(
        "/api/v1/health", headers={"Origin": "https://evil.example.com", **PREFLIGHT}
    )

    assert "access-control-allow-origin" not in response.headers


def test_cors_is_off_by_default() -> None:
    client = _client("")

    response = client.get("/api/v1/health", headers={"Origin": "https://deskpilot.example.com"})

    assert "access-control-allow-origin" not in response.headers
