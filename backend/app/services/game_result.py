"""Result-draft loading, persistence, permission, and submission helpers."""

from collections import defaultdict
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import GameStatus, ScoreAdjustmentType
from app.models.event_day import EventDay
from app.models.game import Game
from app.models.game_player import GamePlayer
from app.models.game_format import GameFormat
from app.models.registration import Registration
from app.models.score_adjustment import ScoreAdjustment
from app.models.user import User
from app.models.user_role import UserRole
from app.schemas.game import GameDetail, GameSummary
from app.schemas.game_format import FormatRoleRead
from app.schemas.game_result import (
    GameResultAdjustmentRead,
    GameResultDraftRead,
    GameResultDraftWrite,
    GameResultPlayerRead,
    SelectablePlayerRead,
    ValidationSummary,
)
from app.services.result_scoring import calculate_adjustment_score, calculate_base_score, calculate_final_score
from app.services.result_validation import validate_game_result_payload


GAME_RESULT_LOAD_OPTIONS = (
    selectinload(Game.event_day).selectinload(EventDay.season),
    selectinload(Game.event_day).selectinload(EventDay.registrations).selectinload(Registration.user),
    selectinload(Game.format).selectinload(GameFormat.format_roles),
    selectinload(Game.judge).selectinload(User.user_roles).selectinload(UserRole.role),
    selectinload(Game.players).selectinload(GamePlayer.user),
    selectinload(Game.players).selectinload(GamePlayer.adjustments),
)


def get_game_result_or_404(db: Session, game_id: int) -> Game:
    """Return a game with result-related context preloaded or raise 404."""

    statement = select(Game).options(*GAME_RESULT_LOAD_OPTIONS).where(Game.id == game_id)
    game = db.scalar(statement)
    if game is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found.")
    return game


def ensure_can_view_game_result(game: Game, current_user: User) -> None:
    """Enforce result-draft visibility rules for admins and the assigned judge."""

    if "admin" in current_user.roles:
        return
    if current_user.id == game.judge_user_id and "judge" in current_user.roles:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this game result.")


def ensure_can_edit_game_result(game: Game, current_user: User) -> None:
    """Enforce judge-owned edit rules for draft and in-progress games only."""

    if "judge" not in current_user.roles or current_user.id != game.judge_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the assigned judge can edit this game result.")
    if game.status not in {GameStatus.DRAFT, GameStatus.IN_PROGRESS}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Submitted or closed games can no longer be edited by the judge.",
        )


def _build_game_detail(game: Game, current_user: User) -> GameDetail:
    """Reuse the existing game detail shape inside result-draft payloads."""

    can_view_internal_fields = "admin" in current_user.roles or current_user.id == game.judge_user_id
    return GameDetail(
        **GameSummary.model_validate(game).model_dump(),
        event_day_venue=game.event_day.venue,
        format=game.format,
        judge=game.judge,
        has_result_draft=game.has_result_draft,
        submitted_at=game.submitted_at if can_view_internal_fields else None,
        submitted_by=game.submitted_by if can_view_internal_fields else None,
        confirmed_at=game.confirmed_at if can_view_internal_fields else None,
        confirmed_by=game.confirmed_by if can_view_internal_fields else None,
    )


def _build_selectable_players(game: Game) -> list[SelectablePlayerRead]:
    """Return event-day registration users that can be picked in the result UI.

    The assigned judge is excluded because the same user cannot judge and play
    in the same game.
    """

    options: dict[int, SelectablePlayerRead] = {}
    for registration in game.event_day.registrations:
        if registration.user_id == game.judge_user_id:
            continue
        options[registration.user_id] = SelectablePlayerRead(
            user_id=registration.user_id,
            username=registration.username,
            display_name=registration.display_name,
            registration_status=registration.registration_status.value,
            check_in_status=registration.check_in_status.value,
        )

    for game_player in game.players:
        if game_player.user_id is None or game_player.user_id == game.judge_user_id:
            continue
        options.setdefault(
            game_player.user_id,
            SelectablePlayerRead(
                user_id=game_player.user_id,
                username=game_player.username,
                display_name=game_player.display_name,
            ),
        )

    return sorted(options.values(), key=lambda option: (option.display_name.lower(), option.user_id))


def _build_validation(game: Game) -> tuple[GameResultDraftWrite, ValidationSummary]:
    """Build a validation-ready payload from persisted rows."""

    payload = GameResultDraftWrite(
        players=[
            {
                "user_id": player.user_id,
                "seat_number": player.seat_number,
                "role_name": player.role_name,
                "faction": player.faction,
                "final_status": player.final_status,
                "is_winner": player.is_winner,
                "remarks": player.remarks,
            }
            for player in game.players
        ],
        adjustments=[
            {
                "target_seat_number": adjustment.target_seat_number,
                "adjustment_type": adjustment.adjustment_type,
                "delta": adjustment.delta,
                "reason": adjustment.reason,
            }
            for player in game.players
            for adjustment in player.adjustments
            if adjustment.target_seat_number is not None
        ],
    )
    return payload, validate_game_result_payload(game, payload, submit_mode=True)


def build_game_result_response(game: Game, current_user: User) -> GameResultDraftRead:
    """Serialize a game result draft with options, validation, and editability."""

    payload, validation = _build_validation(game)
    _ = payload
    return GameResultDraftRead(
        game=_build_game_detail(game, current_user),
        players=[GameResultPlayerRead.model_validate(player) for player in game.players],
        adjustments=[
            GameResultAdjustmentRead.model_validate(adjustment)
            for player in game.players
            for adjustment in player.adjustments
        ],
        format_roles=[FormatRoleRead.model_validate(format_role) for format_role in game.format.format_roles],
        selectable_players=_build_selectable_players(game),
        validation=validation,
        editable=("judge" in current_user.roles and current_user.id == game.judge_user_id and game.status in {GameStatus.DRAFT, GameStatus.IN_PROGRESS}),
    )


def _collect_adjustment_notes(adjustments: list[ScoreAdjustment]) -> tuple[str | None, str | None]:
    """Derive aggregate bonus and penalty note strings for a player row."""

    bonus_reasons = [
        adjustment.reason
        for adjustment in adjustments
        if adjustment.adjustment_type == ScoreAdjustmentType.JUDGE_BONUS and adjustment.reason
    ]
    penalty_reasons = [
        adjustment.reason
        for adjustment in adjustments
        if adjustment.adjustment_type in {ScoreAdjustmentType.LATE_PENALTY, ScoreAdjustmentType.CONDUCT_PENALTY} and adjustment.reason
    ]
    return (
        "; ".join(bonus_reasons) if bonus_reasons else None,
        "; ".join(penalty_reasons) if penalty_reasons else None,
    )


def save_game_result_draft(db: Session, game: Game, payload: GameResultDraftWrite, current_user: User) -> Game:
    """Replace the current draft rows for a game and mark it in progress."""

    ensure_can_edit_game_result(game, current_user)
    validation = validate_game_result_payload(game, payload, submit_mode=False)
    if validation.errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Draft validation failed.",
                "errors": [message.model_dump() for message in validation.errors],
                "warnings": [message.model_dump() for message in validation.warnings],
            },
        )

    db.execute(delete(ScoreAdjustment).where(ScoreAdjustment.game_player_id.in_(select(GamePlayer.id).where(GamePlayer.game_id == game.id))))
    db.execute(delete(GamePlayer).where(GamePlayer.game_id == game.id))
    db.flush()

    players_by_seat: dict[int, GamePlayer] = {}
    created_players: list[GamePlayer] = []

    for player_input in payload.players:
        game_player = GamePlayer(
            game_id=game.id,
            user_id=player_input.user_id,
            seat_number=player_input.seat_number,
            role_name=player_input.role_name,
            faction=player_input.faction,
            final_status=player_input.final_status,
            is_winner=player_input.is_winner,
            remarks=player_input.remarks,
            base_score=calculate_base_score(player_input.faction, player_input.is_winner),
            adjustment_score=0.0,
            final_score=calculate_base_score(player_input.faction, player_input.is_winner),
        )
        db.add(game_player)
        db.flush()
        created_players.append(game_player)
        if player_input.seat_number is not None:
            players_by_seat[player_input.seat_number] = game_player

    adjustments_by_player_id: dict[int, list[ScoreAdjustment]] = defaultdict(list)
    deltas_by_player_id: dict[int, list[float]] = defaultdict(list)

    for adjustment_input in payload.adjustments:
        target_player = players_by_seat[adjustment_input.target_seat_number]
        adjustment = ScoreAdjustment(
            game_player_id=target_player.id,
            adjustment_type=adjustment_input.adjustment_type,
            delta=adjustment_input.delta,
            reason=adjustment_input.reason,
            created_by=current_user.id,
        )
        db.add(adjustment)
        adjustments_by_player_id[target_player.id].append(adjustment)
        deltas_by_player_id[target_player.id].append(adjustment_input.delta)

    for player in created_players:
        adjustment_score = calculate_adjustment_score(deltas_by_player_id[player.id])
        player.adjustment_score = adjustment_score
        player.final_score = calculate_final_score(player.base_score, adjustment_score)
        player.judge_bonus_note, player.penalty_note = _collect_adjustment_notes(adjustments_by_player_id[player.id])
        db.add(player)

    game.status = GameStatus.IN_PROGRESS
    db.add(game)
    db.commit()
    return get_game_result_or_404(db, game.id)


def submit_game_result(db: Session, game: Game, current_user: User) -> Game:
    """Validate the current persisted draft and mark the game as submitted."""

    ensure_can_edit_game_result(game, current_user)
    payload, validation = _build_validation(game)
    _ = payload
    if validation.errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Result submission validation failed.",
                "errors": [message.model_dump() for message in validation.errors],
                "warnings": [message.model_dump() for message in validation.warnings],
            },
        )

    game.status = GameStatus.SUBMITTED
    game.submitted_at = datetime.now(timezone.utc)
    game.submitted_by = current_user.id
    db.add(game)
    db.commit()
    return get_game_result_or_404(db, game.id)
