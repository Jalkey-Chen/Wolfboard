"""Game endpoints for admin management and judge-owned work queues."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.enums import GamePlayStatus, GameResultStatus
from app.core.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.game import GameCancelRequest, GameCreate, GameDetail, GameSummary, JudgeOptionRead, GameUpdate
from app.schemas.game_review import GameConfirmRequest, GameRejectRequest, GameReviewSummary, GameRevisionWrite
from app.schemas.game_result import GameResultDraftRead, GameResultDraftWrite
from app.schemas.game_format_context import GameFormatContextRead
from app.services.event_day import get_event_day_or_404
from app.services.game import create_game, get_game_or_404, list_games_for_event_day, list_games_for_judge, update_game
from app.services.game_review import (
    confirm_game_result,
    get_review_game_or_404,
    list_submitted_games_for_review,
    reject_game_result,
    revise_game_result,
)
from app.services.game_result import (
    build_game_result_response,
    ensure_can_view_game_result,
    get_game_result_or_404,
    save_game_result_draft,
    submit_game_result,
)
from app.services.game_state import cancel_game, end_game, start_game
from app.services.format_snapshot import build_game_format_context, get_game_format_context_or_404
from app.services.user_directory import list_judge_capable_users


router = APIRouter(tags=["games"])


def build_game_detail_payload(game_id: int, db: Session, current_user: User) -> GameDetail:
    """Build a game detail response with role-aware visibility.

    Admins and the assigned judge may see lifecycle metadata such as submit and
    confirm markers. Other authenticated users receive the same structural
    payload, but internal moderation fields are omitted.
    """

    game = get_game_or_404(db, game_id)
    can_view_internal_fields = "admin" in current_user.roles or current_user.id == game.judge_user_id

    return GameDetail(
        **GameSummary.model_validate(game).model_dump(),
        event_day_venue=game.event_day.venue,
        format=game.format,
        judge=game.judge,
        has_result_draft=game.has_result_draft,
        # Lifecycle metadata stays hidden from unrelated viewers even though the
        # public setup fields of a game are already visible on event-day pages.
        submitted_at=game.submitted_at if can_view_internal_fields else None,
        submitted_by=game.submitted_by if can_view_internal_fields else None,
        confirmed_at=game.confirmed_at if can_view_internal_fields else None,
        confirmed_by=game.confirmed_by if can_view_internal_fields else None,
    )


@router.get("/event-days/{event_day_id}/games", response_model=list[GameSummary])
def read_event_day_games(
    event_day_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[GameSummary]:
    """Return all games attached to an event day for authenticated users."""

    _ = current_user
    _ = get_event_day_or_404(db, event_day_id)
    games = list_games_for_event_day(db, event_day_id)
    return [GameSummary.model_validate(game) for game in games]


@router.post("/games", response_model=GameDetail)
def create_game_endpoint(
    payload: GameCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> GameDetail:
    """Allow admins to create a game for an event day."""

    _ = current_user
    game = create_game(db, payload)
    return build_game_detail_payload(game.id, db, current_user)


@router.get("/games/{game_id}", response_model=GameDetail)
def read_game(
    game_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GameDetail:
    """Return a game detail payload with internal fields filtered by role."""

    return build_game_detail_payload(game_id, db, current_user)


@router.get("/games/{game_id}/format-context", response_model=GameFormatContextRead)
def read_game_format_context(
    game_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GameFormatContextRead:
    """Return live pre-start or immutable started-game format context."""

    _ = current_user
    return build_game_format_context(get_game_format_context_or_404(db, game_id))


@router.get("/admin/games/review", response_model=list[GameReviewSummary])
def read_review_queue(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> list[GameReviewSummary]:
    """Return submitted games waiting for admin review."""

    _ = current_user
    return list_submitted_games_for_review(db)


@router.get("/games/{game_id}/result-draft", response_model=GameResultDraftRead)
def read_game_result_draft(
    game_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GameResultDraftRead:
    """Return the current draft plus selection options for the result-entry page."""

    game = get_game_result_or_404(db, game_id)
    ensure_can_view_game_result(game, current_user)
    return build_game_result_response(game, current_user)


@router.put("/games/{game_id}/result-draft", response_model=GameResultDraftRead)
def update_game_result_draft(
    game_id: int,
    payload: GameResultDraftWrite,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GameResultDraftRead:
    """Allow the assigned judge to replace the current draft payload."""

    game = get_game_result_or_404(db, game_id)
    game = save_game_result_draft(db, game, payload, current_user)
    return build_game_result_response(game, current_user)


@router.post("/games/{game_id}/submit-result", response_model=GameResultDraftRead)
def submit_game_result_endpoint(
    game_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GameResultDraftRead:
    """Allow the assigned judge to submit a fully validated result draft."""

    game = get_game_result_or_404(db, game_id)
    game = submit_game_result(db, game, current_user)
    return build_game_result_response(game, current_user)


@router.post("/games/{game_id}/confirm-result", response_model=GameResultDraftRead)
def confirm_game_result_endpoint(
    game_id: int,
    payload: GameConfirmRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> GameResultDraftRead:
    """Confirm a submitted result and make its score logs effective."""

    game = get_review_game_or_404(db, game_id)
    game = confirm_game_result(db, game, current_user, comment=payload.comment)
    return build_game_result_response(game, current_user)


@router.post("/games/{game_id}/reject-result", response_model=GameResultDraftRead)
def reject_game_result_endpoint(
    game_id: int,
    payload: GameRejectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> GameResultDraftRead:
    """Reject a submitted result and return it to draft status."""

    game = get_review_game_or_404(db, game_id)
    game = reject_game_result(db, game, current_user, comment=payload.comment)
    return build_game_result_response(game, current_user)


@router.post("/games/{game_id}/revise-result", response_model=GameResultDraftRead)
def revise_game_result_endpoint(
    game_id: int,
    payload: GameRevisionWrite,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> GameResultDraftRead:
    """Apply an admin revision and rebuild the formal score ledger."""

    game = get_review_game_or_404(db, game_id)
    game = revise_game_result(db, game, payload, current_user)
    return build_game_result_response(game, current_user)


@router.patch("/games/{game_id}", response_model=GameDetail)
def update_game_endpoint(
    game_id: int,
    payload: GameUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> GameDetail:
    """Allow admins to edit the setup metadata of an existing game."""

    _ = current_user
    game = get_game_or_404(db, game_id)
    game = update_game(db, game, payload)
    return build_game_detail_payload(game.id, db, current_user)


@router.post("/games/{game_id}/start", response_model=GameDetail)
def start_game_endpoint(
    game_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GameDetail:
    """Start a scheduled game as its assigned judge or an admin."""

    game = start_game(db, get_game_or_404(db, game_id), current_user)
    return build_game_detail_payload(game.id, db, current_user)


@router.post("/games/{game_id}/end", response_model=GameDetail)
def end_game_endpoint(
    game_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GameDetail:
    """End an in-progress game as its assigned judge or an admin."""

    game = end_game(db, get_game_or_404(db, game_id), current_user)
    return build_game_detail_payload(game.id, db, current_user)


@router.post("/games/{game_id}/cancel", response_model=GameDetail)
def cancel_game_endpoint(
    game_id: int,
    payload: GameCancelRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> GameDetail:
    """Cancel an unreviewed game as an admin."""

    game = cancel_game(db, get_game_or_404(db, game_id), current_user, reason=payload.reason)
    return build_game_detail_payload(game.id, db, current_user)


@router.get("/judges/me/games", response_model=list[GameSummary])
def read_my_judge_games(
    play_status_filter: GamePlayStatus | None = Query(default=None, alias="play_status"),
    result_status_filter: GameResultStatus | None = Query(default=None, alias="result_status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("judge")),
) -> list[GameSummary]:
    """Return games assigned to the current judge user."""

    games = list_games_for_judge(
        db,
        current_user.id,
        play_status_filter=play_status_filter,
        result_status_filter=result_status_filter,
    )
    return [GameSummary.model_validate(game) for game in games]


@router.get("/users/judges", response_model=list[JudgeOptionRead])
def read_judge_directory(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> list[JudgeOptionRead]:
    """Return judge-capable users for admin assignment controls."""

    _ = current_user
    return [JudgeOptionRead.model_validate(user) for user in list_judge_capable_users(db)]
