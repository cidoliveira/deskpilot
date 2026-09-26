"""The API must answer every error with the same envelope and never leak internals."""

from typing import Annotated

import pytest
from fastapi import FastAPI, Query
from fastapi.testclient import TestClient

from app.core.exceptions import (
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    UnauthorizedError,
)


@pytest.fixture
def error_client(app: FastAPI) -> TestClient:
    @app.get("/_test/not-found")
    def raise_not_found() -> None:
        raise NotFoundError("Ticket not found", error="ticket_not_found")

    @app.get("/_test/conflict")
    def raise_conflict() -> None:
        raise ConflictError(
            "Cannot move ticket from CLOSED to IN_PROGRESS", error="invalid_status_transition"
        )

    @app.get("/_test/business-rule")
    def raise_business_rule() -> None:
        raise BusinessRuleError("A resolution is required")

    @app.get("/_test/unauthorized")
    def raise_unauthorized() -> None:
        raise UnauthorizedError("Invalid token", error="invalid_token")

    @app.get("/_test/crash")
    def crash() -> None:
        raise RuntimeError("secret database password is hunter2")

    @app.get("/_test/validation")
    def validated(page: int) -> dict[str, int]:
        return {"page": page}

    @app.get("/_test/too-short")
    def too_short(name: Annotated[str, Query(min_length=3)]) -> dict[str, str]:
        return {"name": name}

    # raise_server_exceptions=False: behave like a real server instead of re-raising.
    return TestClient(app, raise_server_exceptions=False)


def test_domain_error_uses_error_envelope(error_client: TestClient) -> None:
    response = error_client.get("/_test/not-found")

    assert response.status_code == 404
    assert response.json() == {"error": "ticket_not_found", "message": "Ticket not found"}


def test_conflict_error_returns_409(error_client: TestClient) -> None:
    response = error_client.get("/_test/conflict")

    assert response.status_code == 409
    assert response.json()["error"] == "invalid_status_transition"


def test_business_rule_error_uses_default_code(error_client: TestClient) -> None:
    response = error_client.get("/_test/business-rule")

    assert response.status_code == 422
    assert response.json() == {
        "error": "business_rule_violation",
        "message": "A resolution is required",
    }


def test_unauthorized_error_tells_client_to_use_bearer_token(error_client: TestClient) -> None:
    response = error_client.get("/_test/unauthorized")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert response.json()["error"] == "invalid_token"


def test_unknown_route_uses_error_envelope(error_client: TestClient) -> None:
    response = error_client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {"error": "not_found", "message": "Not Found"}


def test_wrong_method_uses_error_envelope(error_client: TestClient) -> None:
    response = error_client.post("/api/v1/health")

    assert response.status_code == 405
    assert response.json()["error"] == "method_not_allowed"


def test_validation_error_lists_invalid_fields(error_client: TestClient) -> None:
    response = error_client.get("/_test/validation", params={"page": "abc"})

    body = response.json()
    assert response.status_code == 422
    assert body["error"] == "validation_error"
    assert body["details"][0]["field"] == "page"


def test_validation_details_carry_type_and_constraints(error_client: TestClient) -> None:
    response = error_client.get("/_test/too-short", params={"name": "ab"})

    [detail] = response.json()["details"]
    assert detail["field"] == "name"
    assert detail["type"] == "string_too_short"
    assert detail["ctx"] == {"min_length": 3}


def test_unexpected_error_does_not_leak_details(error_client: TestClient) -> None:
    response = error_client.get("/_test/crash")

    assert response.status_code == 500
    assert response.json() == {
        "error": "internal_error",
        "message": "An unexpected error occurred",
    }
    assert "hunter2" not in response.text
