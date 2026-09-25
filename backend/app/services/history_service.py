"""Ticket audit trail.

`record()` only adds the event to the session: the caller commits it together with the
change itself, so a change and its history are saved atomically (both or neither).
"""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Category, Ticket, TicketAction, TicketEvent, User

# Actions whose values are ids that should be shown with a readable label.
_USER_ID_ACTIONS = frozenset({TicketAction.ASSIGNED})
_CATEGORY_ID_ACTIONS = frozenset({TicketAction.CATEGORY_CHANGED})


@dataclass(frozen=True)
class HistoryEntry:
    id: int
    action: TicketAction
    changed_by: User
    old_value: str | None
    new_value: str | None
    old_label: str | None
    new_label: str | None
    created_at: datetime


def _as_text(value: object) -> str | None:
    return None if value is None else str(value)


def record(
    session: Session,
    ticket: Ticket,
    action: TicketAction,
    changed_by: User,
    *,
    old: object = None,
    new: object = None,
) -> TicketEvent:
    event = TicketEvent(
        ticket_id=ticket.id,
        action=action,
        changed_by=changed_by,
        old_value=_as_text(old),
        new_value=_as_text(new),
    )
    session.add(event)
    return event


def _names_by_id(session: Session, model: type[User] | type[Category], ids: set[int]) -> dict:
    if not ids:
        return {}
    rows = session.execute(select(model.id, model.name).where(model.id.in_(ids)))
    return {str(row_id): name for row_id, name in rows}


def list_history(session: Session, ticket: Ticket) -> list[HistoryEntry]:
    events = session.scalars(
        select(TicketEvent)
        .where(TicketEvent.ticket_id == ticket.id)
        .order_by(TicketEvent.created_at, TicketEvent.id)
        .options(selectinload(TicketEvent.changed_by))
    ).all()

    def ids_for(actions: frozenset[TicketAction]) -> set[int]:
        values = (v for e in events if e.action in actions for v in (e.old_value, e.new_value))
        return {int(v) for v in values if v is not None}

    # One query per label type, instead of one query per event.
    user_names = _names_by_id(session, User, ids_for(_USER_ID_ACTIONS))
    category_names = _names_by_id(session, Category, ids_for(_CATEGORY_ID_ACTIONS))

    def label(event: TicketEvent, value: str | None) -> str | None:
        if value is None:
            return None
        if event.action in _USER_ID_ACTIONS:
            return user_names.get(value)
        if event.action in _CATEGORY_ID_ACTIONS:
            return category_names.get(value)
        return None  # statuses and priorities are already readable

    return [
        HistoryEntry(
            id=event.id,
            action=event.action,
            changed_by=event.changed_by,
            old_value=event.old_value,
            new_value=event.new_value,
            old_label=label(event, event.old_value),
            new_label=label(event, event.new_value),
            created_at=event.created_at,
        )
        for event in events
    ]
