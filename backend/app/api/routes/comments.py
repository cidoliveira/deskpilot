from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.comment import CommentCreate, CommentRead
from app.services import comment_service

router = APIRouter(prefix="/tickets/{ticket_id}/comments", tags=["comments"])


@router.get("", response_model=list[CommentRead])
def list_comments(ticket_id: int, db: DbSession, current_user: CurrentUser) -> list[CommentRead]:
    """Comments of a visible ticket, oldest first."""
    comments = comment_service.list_comments(db, ticket_id, current_user)
    return [CommentRead.model_validate(comment) for comment in comments]


@router.post("", response_model=CommentRead, status_code=status.HTTP_201_CREATED)
def add_comment(
    ticket_id: int, data: CommentCreate, db: DbSession, current_user: CurrentUser
) -> CommentRead:
    """Anyone who can see the ticket may comment, until it is CLOSED or CANCELLED (409)."""
    comment = comment_service.add_comment(db, ticket_id, data, current_user)
    return CommentRead.model_validate(comment)
