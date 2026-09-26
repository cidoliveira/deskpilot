import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import API_V1_PREFIX, Settings, get_settings
from app.core.exceptions import register_exception_handlers

DESCRIPTION = """
DeskPilot is an internal IT Help Desk / Service Desk API.

**Authentication:** use *Authorize* with your e-mail and password (OAuth2 password flow),
or send `Authorization: Bearer <token>` obtained from `POST /auth/login`.

**Roles:** `USER` opens and follows own tickets; `TECHNICIAN` works the queue; `ADMIN` sees
everything and manages users, categories and metrics. Every single-ticket response includes
`allowed_actions` for the current user.

**Errors** always share one format: `{"error": "<code>", "message": "<text>"}` (plus
`details` for validation errors). Branch on `error`; `message` is for humans.
"""

TAGS = [
    {"name": "auth", "description": "Sign up, log in and the current user."},
    {
        "name": "tickets",
        "description": "Tickets, their workflow (status, assignee, "
        "priority) and audit history. Results are limited to what the caller may see.",
    },
    {"name": "comments", "description": "Conversation on a ticket."},
    {"name": "categories", "description": "Ticket categories (managed by admins)."},
    {"name": "users", "description": "User management (admins only)."},
    {"name": "dashboard", "description": "Service desk metrics (admins only)."},
    {"name": "health", "description": "Liveness and database check."},
]


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description=DESCRIPTION,
        openapi_tags=TAGS,
        docs_url=f"{API_V1_PREFIX}/docs",
        redoc_url=f"{API_V1_PREFIX}/redoc",
        openapi_url=f"{API_V1_PREFIX}/openapi.json",
    )
    if settings.cors_origin_list:
        # Only needed when the frontend is served from another domain. Bearer tokens are
        # sent in a header, not cookies, so credentials are not allowed.
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_methods=["GET", "POST", "PUT", "PATCH"],
            allow_headers=["Authorization", "Content-Type"],
        )
    register_exception_handlers(app)
    app.include_router(api_router)
    return app


app = create_app()
