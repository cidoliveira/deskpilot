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
