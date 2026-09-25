import logging

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import API_V1_PREFIX, get_settings
from app.core.exceptions import register_exception_handlers

DESCRIPTION = """
DeskPilot is an internal IT Help Desk / Service Desk API.

All errors share the same format: `{"error": "<code>", "message": "<text>"}`.
"""


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description=DESCRIPTION,
        docs_url=f"{API_V1_PREFIX}/docs",
        redoc_url=f"{API_V1_PREFIX}/redoc",
        openapi_url=f"{API_V1_PREFIX}/openapi.json",
    )
    register_exception_handlers(app)
    app.include_router(api_router)
    return app


app = create_app()
