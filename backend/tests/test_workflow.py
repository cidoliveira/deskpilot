"""Unit tests for the status state machine: plain objects, no database."""

import pytest

from app.core.exceptions import BusinessRuleError, ConflictError, PermissionDeniedError
from app.models import Ticket, TicketAction, TicketStatus, User, UserRole
from app.services import workflow
from app.services.workflow import Actor

S = TicketStatus
AUTHOR_ID, TECH_ID, OTHER_TECH_ID, ADMIN_ID = 1, 2, 3, 4

author = User(id=AUTHOR_ID, role=UserRole.USER)
tech = User(id=TECH_ID, role=UserRole.TECHNICIAN)
other_tech = User(id=OTHER_TECH_ID, role=UserRole.TECHNICIAN)
admin = User(id=ADMIN_ID, role=UserRole.ADMIN)


def ticket(status: TicketStatus, assigned_to_id: int | None = TECH_ID) -> Ticket:
    return Ticket(created_by_id=AUTHOR_ID, assigned_to_id=assigned_to_id, status=status)


# --- actors ---------------------------------------------------------------


def test_actors() -> None:
    t = ticket(S.OPEN)

    assert workflow.actors(author, t) == {Actor.AUTHOR}
    assert workflow.actors(tech, t) == {Actor.ASSIGNEE}
    assert workflow.actors(other_tech, t) == set()
    assert workflow.actors(admin, t) == {Actor.ADMIN}


# --- valid transitions ------------------------------------------------------


@pytest.mark.parametrize(
    ("user", "source", "target"),
    [
        (tech, S.OPEN, S.IN_PROGRESS),
        (tech, S.IN_PROGRESS, S.WAITING_USER),
        (tech, S.WAITING_USER, S.IN_PROGRESS),
        (tech, S.IN_PROGRESS, S.RESOLVED),
        (tech, S.RESOLVED, S.IN_PROGRESS),
        (author, S.OPEN, S.CANCELLED),
        (author, S.RESOLVED, S.CLOSED),
        (author, S.RESOLVED, S.IN_PROGRESS),
        (admin, S.OPEN, S.IN_PROGRESS),
        (admin, S.IN_PROGRESS, S.RESOLVED),
        (admin, S.RESOLVED, S.CLOSED),
        (admin, S.OPEN, S.CANCELLED),
    ],
)
def test_allowed_transition(user: User, source: TicketStatus, target: TicketStatus) -> None:
    t = ticket(source)

    workflow.check_transition(user, t, target)  # does not raise
    assert target in workflow.allowed_transitions(user, t)


# --- invalid transitions ------------------------------------------------------


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (S.CLOSED, S.IN_PROGRESS),
        (S.CLOSED, S.OPEN),
        (S.CANCELLED, S.OPEN),
        (S.OPEN, S.RESOLVED),  # cannot skip the work
        (S.OPEN, S.CLOSED),
        (S.WAITING_USER, S.CLOSED),
        (S.IN_PROGRESS, S.OPEN),
        (S.IN_PROGRESS, S.IN_PROGRESS),
    ],
)
def test_transition_that_does_not_exist_is_a_conflict(
    source: TicketStatus, target: TicketStatus
) -> None:
    # Even an admin cannot perform a transition missing from the table.
    with pytest.raises(ConflictError) as exc_info:
        workflow.check_transition(admin, ticket(source), target)
    assert exc_info.value.error == "invalid_status_transition"


@pytest.mark.parametrize(
    ("user", "source", "target"),
    [
        (author, S.IN_PROGRESS, S.RESOLVED),  # users cannot resolve
        (author, S.OPEN, S.IN_PROGRESS),
        (author, S.IN_PROGRESS, S.WAITING_USER),
        (other_tech, S.IN_PROGRESS, S.RESOLVED),  # not the assignee
        (tech, S.RESOLVED, S.CLOSED),  # closing is the author's confirmation
        (tech, S.OPEN, S.CANCELLED),
    ],
)
def test_transition_by_wrong_actor_is_forbidden(
    user: User, source: TicketStatus, target: TicketStatus
) -> None:
    t = ticket(source)

    with pytest.raises(PermissionDeniedError):
        workflow.check_transition(user, t, target)
    assert target not in workflow.allowed_transitions(user, t)


def test_work_cannot_start_without_assignee() -> None:
    t = ticket(S.OPEN, assigned_to_id=None)

    with pytest.raises(BusinessRuleError) as exc_info:
        workflow.check_transition(admin, t, S.IN_PROGRESS)
    assert exc_info.value.error == "ticket_not_assigned"
    assert workflow.allowed_transitions(admin, t) == [S.CANCELLED]


def test_terminal_statuses_have_no_transitions() -> None:
    for status in (S.CLOSED, S.CANCELLED):
        assert workflow.allowed_transitions(admin, ticket(status)) == []


# --- history actions ----------------------------------------------------------


@pytest.mark.parametrize(
    ("source", "target", "action"),
    [
        (S.IN_PROGRESS, S.RESOLVED, TicketAction.RESOLVED),
        (S.RESOLVED, S.CLOSED, TicketAction.CLOSED),
        (S.RESOLVED, S.IN_PROGRESS, TicketAction.REOPENED),
        (S.OPEN, S.IN_PROGRESS, TicketAction.STATUS_CHANGED),
        (S.OPEN, S.CANCELLED, TicketAction.STATUS_CHANGED),
        (S.IN_PROGRESS, S.WAITING_USER, TicketAction.STATUS_CHANGED),
    ],
)
def test_event_action(source: TicketStatus, target: TicketStatus, action: TicketAction) -> None:
    assert workflow.event_action(source, target) == action
