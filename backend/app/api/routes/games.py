"""Game endpoints for admin management and judge-owned work queues."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.enums import GameStatus
from app.core.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.game import GameCreate, GameDetail, GameSummary, JudgeOptionRead, GameUpdate
from app.services.event_day import get_event_day_or_404
from app.services.game import create_game, get_game_or_404, list_games_for_event_day, list_games_for_judge, update_game
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


@router.get("/judges/me/games", response_model=list[GameSummary])
def read_my_judge_games(
    status_filter: GameStatus | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("judge")),
) -> list[GameSummary]:
    """Return games assigned to the current judge user."""

    games = list_games_for_judge(db, current_user.id, status_filter=status_filter)
    return [GameSummary.model_validate(game) for game in games]


@router.get("/users/judges", response_model=list[JudgeOptionRead])
def read_judge_directory(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> list[JudgeOptionRead]:
    """Return judge-capable users for admin assignment controls."""

    _ = current_user
    return [JudgeOptionRead.model_validate(user) for user in list_judge_capable_users(db)]
