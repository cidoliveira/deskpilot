from enum import StrEnum


class UserRole(StrEnum):
    USER = "USER"
    TECHNICIAN = "TECHNICIAN"
    ADMIN = "ADMIN"


class TicketStatus(StrEnum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_USER = "WAITING_USER"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"
    # Opened by mistake or duplicated: leaves SLA and resolution metrics untouched.
    CANCELLED = "CANCELLED"


# Tickets in these states are final and cannot be edited or commented on.
TERMINAL_STATUSES = frozenset({TicketStatus.CLOSED, TicketStatus.CANCELLED})


class TicketPriority(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class TicketAction(StrEnum):
    """Kind of change recorded in the ticket history."""

    CREATED = "CREATED"
    ASSIGNED = "ASSIGNED"
    STATUS_CHANGED = "STATUS_CHANGED"
    PRIORITY_CHANGED = "PRIORITY_CHANGED"
    CATEGORY_CHANGED = "CATEGORY_CHANGED"
    # Status changes with their own action, so the timeline reads naturally.
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"
    REOPENED = "REOPENED"
