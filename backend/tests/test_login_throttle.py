import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.exceptions import TooManyRequestsError
from app.services.auth_service import login_throttle
from app.services.login_throttle import LoginThrottle
from tests.factories import DEFAULT_PASSWORD, make_user

LOGIN_URL = "/api/v1/auth/login"


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


# --- unit ---------------------------------------------------------------------


def test_blocks_after_too_many_failures_and_reports_when_to_retry() -> None:
    clock = FakeClock()
    throttle = LoginThrottle(max_failures=3, window_seconds=60, clock=clock)
    for _ in range(3):
        throttle.check("ip|ana")
        throttle.record_failure("ip|ana")
    clock.now += 20

    with pytest.raises(TooManyRequestsError) as exc_info:
        throttle.check("ip|ana")
    assert exc_info.value.headers == {"Retry-After": "40"}


def test_old_failures_leave_the_window() -> None:
    clock = FakeClock()
    throttle = LoginThrottle(max_failures=2, window_seconds=60, clock=clock)
    throttle.record_failure("k")
    throttle.record_failure("k")
    clock.now += 61

    throttle.check("k")  # does not raise


def test_keys_are_independent_and_reset_clears_one() -> None:
    throttle = LoginThrottle(max_failures=1, window_seconds=60, clock=FakeClock())
    throttle.record_failure("ip1|ana")
    throttle.record_failure("ip1|bruno")

    throttle.check("ip2|ana")  # same e-mail, other client: allowed
    throttle.reset("ip1|ana")
    throttle.check("ip1|ana")
    with pytest.raises(TooManyRequestsError):
        throttle.check("ip1|bruno")


# --- API ----------------------------------------------------------------------


def _login(client: TestClient, email: str, password: str):
    return client.post(LOGIN_URL, data={"username": email, "password": password})


def test_login_is_blocked_after_repeated_failures(client: TestClient, db_session: Session) -> None:
    make_user(db_session, email="ana@example.com")
    for _ in range(login_throttle.max_failures):
        assert _login(client, "ana@example.com", "wrong-password").status_code == 401

    blocked = _login(client, "ANA@example.com", DEFAULT_PASSWORD)  # even the right one

    assert blocked.status_code == 429
    assert blocked.json()["error"] == "too_many_requests"
    assert int(blocked.headers["Retry-After"]) > 0


def test_successful_login_clears_previous_failures(client: TestClient, db_session: Session) -> None:
    make_user(db_session, email="ana@example.com")
    for _ in range(login_throttle.max_failures - 1):
        _login(client, "ana@example.com", "wrong-password")
    assert _login(client, "ana@example.com", DEFAULT_PASSWORD).status_code == 200

    for _ in range(login_throttle.max_failures - 1):
        _login(client, "ana@example.com", "wrong-password")

    assert _login(client, "ana@example.com", DEFAULT_PASSWORD).status_code == 200


def test_unknown_emails_are_throttled_too(client: TestClient) -> None:
    for _ in range(login_throttle.max_failures):
        _login(client, "nobody@example.com", "guess")

    assert _login(client, "nobody@example.com", "guess").status_code == 429
