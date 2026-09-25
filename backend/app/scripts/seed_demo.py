"""Populate a development database with realistic demo data.

Usage: python -m app.scripts.seed_demo

Tickets are created through the real services (create, assign, change status, comment),
so their history is genuine. Some creation dates are then moved into the past to show
every SLA state. Refuses to run in production and does nothing if demo users exist.
"""

import logging
import sys
from dataclasses import dataclass, field
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Environment, get_settings
from app.db.session import SessionLocal
from app.models import (
    Category,
    Ticket,
    TicketComment,
    TicketEvent,
    TicketPriority,
    TicketStatus,
    User,
    UserRole,
)
from app.schemas.comment import CommentCreate
from app.schemas.ticket import (
    TicketAssigneeUpdate,
    TicketCreate,
    TicketStatusUpdate,
)
from app.schemas.user import UserCreate
from app.services import comment_service, sla, ticket_service, ticket_workflow_service, user_service

logger = logging.getLogger("deskpilot.seed_demo")

S = TicketStatus
P = TicketPriority

DEMO_USERS = [
    ("Carla Mendes", "carla@deskpilot.dev", UserRole.TECHNICIAN),
    ("Diego Rocha", "diego@deskpilot.dev", UserRole.TECHNICIAN),
    ("Ana Souza", "ana@deskpilot.dev", UserRole.USER),
    ("Bruno Lima", "bruno@deskpilot.dev", UserRole.USER),
    ("Juliana Costa", "juliana@deskpilot.dev", UserRole.USER),
]


@dataclass
class DemoTicket:
    author: str
    category: str
    priority: TicketPriority
    title: str
    description: str
    hours_ago: float
    tech: str | None = None
    # Target status, reached by walking the real workflow.
    status: TicketStatus = S.OPEN
    conversation: list[tuple[str, str]] = field(default_factory=list)
    resolution: str | None = None


DEMO_TICKETS = [
    DemoTicket(
        "ana",
        "Network",
        P.CRITICAL,
        "VPN não conecta fora do escritório",
        "Desde a atualização de ontem, a VPN falha com erro 809 em casa. Preciso acessar o ERP.",
        hours_ago=6,
        tech="carla",
        status=S.IN_PROGRESS,
        conversation=[
            ("carla", "Consegue me mandar um print da tela de erro?"),
            ("ana", "Enviei por e-mail agora."),
        ],
    ),
    DemoTicket(
        "bruno",
        "Hardware",
        P.HIGH,
        "Notebook desliga sozinho",
        "O notebook desliga sem aviso depois de uns 20 minutos de uso, mesmo na tomada.",
        hours_ago=7,
        tech="diego",
        status=S.WAITING_USER,
        conversation=[("diego", "Pode deixar o notebook na TI amanhã às 9h para diagnóstico?")],
    ),
    DemoTicket(
        "juliana",
        "Access",
        P.HIGH,
        "Sem acesso à pasta do Financeiro",
        "Fui transferida para o Financeiro e não consigo abrir a pasta compartilhada do setor.",
        hours_ago=1,
        status=S.OPEN,
    ),
    DemoTicket(
        "ana",
        "Email",
        P.MEDIUM,
        "Caixa de e-mail cheia",
        "O Outlook avisa que a caixa está cheia e não recebo mais mensagens externas.",
        hours_ago=3,
        status=S.OPEN,
    ),
    DemoTicket(
        "bruno",
        "Printer",
        P.LOW,
        "Impressora do 3º andar com papel atolado",
        "A impressora perto da copa mostra erro de papel atolado, mas não há papel preso.",
        hours_ago=30,
        tech="carla",
        status=S.IN_PROGRESS,
    ),
    DemoTicket(
        "juliana",
        "Software",
        P.MEDIUM,
        "Excel trava ao abrir planilhas grandes",
        "Planilhas acima de 50 MB congelam o Excel por vários minutos.",
        hours_ago=40,
        tech="diego",
        status=S.RESOLVED,
        conversation=[
            ("diego", "Atualizei o Office para a versão 64 bits, pode testar?"),
            ("juliana", "Abriu bem mais rápido agora."),
        ],
        resolution="Office reinstalado na versão 64 bits e cache de complementos limpo.",
    ),
    DemoTicket(
        "ana",
        "Software",
        P.HIGH,
        "Licença do Adobe expirada",
        "O Acrobat pede para renovar a licença e não deixa editar PDFs.",
        hours_ago=50,
        tech="carla",
        status=S.CLOSED,
        resolution="Licença reatribuída ao usuário no console da Adobe.",
    ),
    DemoTicket(
        "bruno",
        "Network",
        P.MEDIUM,
        "Wi-Fi lento na sala de reuniões",
        "Na sala 2 o Wi-Fi cai durante as videochamadas.",
        hours_ago=70,
        tech="diego",
        status=S.CLOSED,
        resolution="Access point da sala 2 substituído; sinal medido acima de -60 dBm.",
    ),
    DemoTicket(
        "juliana",
        "Other",
        P.LOW,
        "Pedido de segundo monitor",
        "Gostaria de um segundo monitor para a minha estação.",
        hours_ago=20,
        status=S.CANCELLED,
    ),
]


def _walk_to(session: Session, ticket: Ticket, demo: DemoTicket, people: dict[str, User]):
    """Move the ticket to its target status using the real workflow operations."""
    tech = people.get(demo.tech) if demo.tech else None
    author = people[demo.author]

    def move(status: TicketStatus, actor: User, resolution: str | None = None) -> None:
        ticket_workflow_service.change_status(
            session, ticket.id, TicketStatusUpdate(status=status, resolution=resolution), actor
        )

    if demo.status == S.CANCELLED:
        move(S.CANCELLED, author)
        return
    if tech is None:
        return
    ticket_workflow_service.assign(
        session, ticket.id, TicketAssigneeUpdate(assignee_id=tech.id), tech
    )
    move(S.IN_PROGRESS, tech)
    for who, message in demo.conversation:
        comment_service.add_comment(session, ticket.id, CommentCreate(message=message), people[who])
    if demo.status == S.WAITING_USER:
        move(S.WAITING_USER, tech)
    if demo.status in (S.RESOLVED, S.CLOSED):
        move(S.RESOLVED, tech, demo.resolution)
    if demo.status == S.CLOSED:
        move(S.CLOSED, author)


def _backdate(session: Session, ticket: Ticket, hours_ago: float) -> None:
    """Move the ticket into the past so SLA states are varied, and spread its history and
    comments over that time so the timeline looks like real work."""
    shift = timedelta(hours=hours_ago)
    ticket.created_at -= shift
    ticket.sla_due_at = sla.due_at(ticket.created_at, ticket.priority)
    if ticket.resolved_at is not None:
        # Resolved a fraction of the way through the window: a mix of MET and BREACHED.
        ticket.resolved_at = ticket.created_at + shift * 0.6
    if ticket.closed_at is not None:
        ticket.closed_at = ticket.created_at + shift * 0.8

    rows = [
        *session.scalars(select(TicketEvent).where(TicketEvent.ticket_id == ticket.id)),
        *session.scalars(select(TicketComment).where(TicketComment.ticket_id == ticket.id)),
    ]
    # Oldest first (creation order), then evenly spaced over the busy part of the window.
    rows.sort(key=lambda row: row.created_at)
    span = (ticket.resolved_at or ticket.created_at + shift * 0.5) - ticket.created_at
    for index, row in enumerate(rows):
        row.created_at = ticket.created_at + span * (index / max(len(rows) - 1, 1))
    if ticket.closed_at is not None and rows:
        rows[-1].created_at = ticket.closed_at


def seed(session: Session, password: str) -> None:
    if session.scalar(select(User).where(User.email == DEMO_USERS[0][1])):
        logger.info("Demo data already present, nothing to do")
        return

    people: dict[str, User] = {}
    for name, email, role in DEMO_USERS:
        user = user_service.create_user(
            session, UserCreate(name=name, email=email, password=password, role=role)
        )
        people[email.split("@")[0]] = user

    categories = {c.name: c for c in session.scalars(select(Category))}
    for demo in DEMO_TICKETS:
        author = people[demo.author]
        ticket = ticket_service.create_ticket(
            session,
            TicketCreate(
                title=demo.title,
                description=demo.description,
                category_id=categories[demo.category].id,
                priority=demo.priority,
            ),
            author,
        )
        _walk_to(session, ticket, demo, people)
        _backdate(session, session.get(Ticket, ticket.id), demo.hours_ago)
        session.commit()
    logger.info("Created %d users and %d tickets", len(people), len(DEMO_TICKETS))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")
    settings = get_settings()
    if settings.environment == Environment.PRODUCTION:
        logger.error("Refusing to seed demo data in production")
        sys.exit(1)
    if settings.demo_password is None:
        logger.error("Set DEMO_PASSWORD to create the demo accounts")
        sys.exit(1)
    with SessionLocal() as session:
        seed(session, settings.demo_password.get_secret_value())


if __name__ == "__main__":
    main()
