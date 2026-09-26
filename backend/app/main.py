import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import API_V1_PREFIX, Settings, get_settings
from app.core.exceptions import register_exception_handlers

DESCRIPTION = """
DeskPilot is an internal IT Help Desk / Service Desk API.

All errors share the same format: `{"error": "<code>", "message": "<text>"}`.
"""


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
