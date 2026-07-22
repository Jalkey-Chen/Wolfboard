"""Service helpers for admin game management and judge-owned game queries."""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.event_day import EventDay
from app.models.game import Game
from app.models.game_format import GameFormat
from app.models.game_format_snapshot import GameFormatSnapshot
from app.models.user import User
from app.models.user_role import UserRole
from app.core.enums import GamePlayStatus, GameResultStatus
from app.schemas.game import GameCreate, GameUpdate


GAME_LOAD_OPTIONS = (
    selectinload(Game.event_day).selectinload(EventDay.season),
    selectinload(Game.format),
    selectinload(Game.format_snapshot).selectinload(GameFormatSnapshot.roles),
    selectinload(Game.judge).selectinload(User.user_roles).selectinload(UserRole.role),
)


def list_games_for_event_day(db: Session, event_day_id: int) -> list[Game]:
    """Return all games for an event day ordered by table and game number."""

    statement = (
        select(Game)
        .options(*GAME_LOAD_OPTIONS)
        .where(Game.event_day_id == event_day_id)
        .order_by(Game.table_number.asc(), Game.game_number.asc(), Game.id.asc())
    )
    return list(db.scalars(statement).all())


def list_games_for_judge(
    db: Session,
    judge_user_id: int,
    play_status_filter: GamePlayStatus | None = None,
    result_status_filter: GameResultStatus | None = None,
) -> list[Game]:
    """Return games assigned to a judge user, optionally filtered by status."""

    statement = (
        select(Game)
        .options(*GAME_LOAD_OPTIONS)
        .where(Game.judge_user_id == judge_user_id)
        .order_by(Game.updated_at.desc(), Game.id.desc())
    )
    if play_status_filter is not None:
        statement = statement.where(Game.play_status == play_status_filter)
    if result_status_filter is not None:
        statement = statement.where(Game.result_status == result_status_filter)
    return list(db.scalars(statement).all())


def get_game_or_404(db: Session, game_id: int) -> Game:
    """Return a game with related context loaded or raise a 404 error."""

    statement = select(Game).options(*GAME_LOAD_OPTIONS).where(Game.id == game_id)
    game = db.scalar(statement)
    if game is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found.")
    return game


def validate_judge_assignment(db: Session, judge_user_id: int) -> User:
    """Ensure the assigned judge exists and holds the `judge` system role."""

    statement = (
        select(User)
        .options(selectinload(User.user_roles).selectinload(UserRole.role))
        .where(User.id == judge_user_id, User.account_status == "active")
    )
    judge_user = db.scalar(statement)
    if judge_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Judge user not found.")
    if "judge" not in judge_user.roles:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The selected user does not have the judge role.",
        )
    return judge_user


def validate_references(db: Session, payload: GameCreate | GameUpdate, event_day_id: int | None = None) -> None:
    """Validate that referenced event-day, format, and judge rows exist.

    Game creation and editing happen from admin-controlled forms that submit
    integer foreign keys. This helper keeps referential validation in one
    place, so both create and update flows fail consistently before any write
    attempts hit the database.
    """

    resolved_event_day_id = event_day_id if event_day_id is not None else payload.event_day_id
    if resolved_event_day_id is not None and db.get(EventDay, resolved_event_day_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event day not found.")

    if payload.format_id is not None:
        game_format = db.get(GameFormat, payload.format_id)
        if game_format is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game format not found.")

    if payload.judge_user_id is not None:
        validate_judge_assignment(db, payload.judge_user_id)


def persist_game(db: Session, game: Game) -> Game:
    """Persist a game while mapping uniqueness conflicts to a 400 response.

    The unique constraint on `(event_day_id, table_number, game_number)` is a
    core scheduling invariant. Surfacing a user-facing validation error here is
    clearer than leaking a raw database integrity exception back to the client.
    """

    db.add(game)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A game with this table number and game number already exists for the event day.",
        ) from exc
    return get_game_or_404(db, game.id)


def create_game(db: Session, payload: GameCreate) -> Game:
    """Create a new game under an existing event day."""

    validate_references(db, payload)

    game = Game(
        event_day_id=payload.event_day_id,
        game_number=payload.game_number,
        table_number=payload.table_number,
        format_id=payload.format_id,
        judge_user_id=payload.judge_user_id,
        game_type=payload.game_type,
        play_status=GamePlayStatus.SCHEDULED,
        result_status=GameResultStatus.EMPTY,
        notes=payload.notes,
    )
    return persist_game(db, game)


def update_game(db: Session, game: Game, payload: GameUpdate) -> Game:
    """Apply an admin-managed patch to a game's setup fields."""

    changes = payload.model_dump(exclude_unset=True)
    if game.play_status == GamePlayStatus.CANCELLED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cancelled games are read-only.")
    frozen_fields = {"game_number", "format_id", "game_type"} & changes.keys()
    if frozen_fields and (
        game.play_status != GamePlayStatus.SCHEDULED
        or game.result_status != GameResultStatus.EMPTY
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Game number, format, and game type are frozen after play or result entry begins.",
        )
    validate_references(db, payload, event_day_id=game.event_day_id)
    for field, value in changes.items():
        setattr(game, field, value)
    return persist_game(db, game)
