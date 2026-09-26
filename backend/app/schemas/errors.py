"""Error envelope, documented in OpenAPI so clients see it next to every endpoint."""

from typing import Any

from pydantic import BaseModel, Field


class FieldError(BaseModel):
    field: str = Field(examples=["title"])
    message: str = Field(examples=["String should have at least 5 characters"])
    type: str = Field(
        description="Stable validation code (Pydantic error type), for client-side messages.",
        examples=["string_too_short"],
    )
    ctx: dict[str, int | float | str] | None = Field(
        default=None,
        description="Constraint values, e.g. {'min_length': 5}.",
        examples=[{"min_length": 5}],
    )


class ErrorRead(BaseModel):
    error: str = Field(
        description="Stable machine-readable code; clients should branch on it.",
        examples=["invalid_status_transition"],
    )
    message: str = Field(
        description="Human-readable explanation (English).",
        examples=["Cannot move ticket from CLOSED to IN_PROGRESS"],
    )
    details: list[FieldError] | None = Field(
        default=None, description="Only for validation_error: one entry per invalid field."
    )


def error_responses(*codes: int) -> dict[int | str, dict[str, Any]]:
    """`responses=` argument for routers/endpoints: the listed statuses use ErrorRead."""
    descriptions = {
        401: "Missing, invalid or expired token",
        403: "Authenticated, but not allowed to do this",
        404: "Not found (or not visible to the current user)",
        409: "Conflicts with the current state (e.g. invalid transition, ticket closed)",
        422: "Invalid input or business rule violation",
        429: "Too many attempts; see the Retry-After header",
    }
    return {code: {"model": ErrorRead, "description": descriptions[code]} for code in codes}
