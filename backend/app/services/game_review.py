"""Admin review, confirmation, rejection, and revision helpers."""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import GamePlayStatus, GameResultStatus, ResultConfirmationStatus
from app.models.event_day import EventDay
from app.models.game import Game
from app.models.game_participant import GameParticipant
from app.models.game_player import GamePlayer
from app.models.game_format import GameFormat
from app.models.game_format_snapshot import GameFormatSnapshot
from app.models.registration import Registration
from app.models.result_confirmation import ResultConfirmation
from app.models.score_log import ScoreLog
from app.models.user import User
from app.models.user_role import UserRole
from app.schemas.game_review import GameReviewSummary, GameRevisionWrite
from app.services.audit import build_game_snapshot, reload_game_for_audit, write_audit_log
from app.services.game_state import (
    lock_game_state,
    transition_result_status,
    validate_game_state,
)
from app.services.game_result import reconcile_game_result_rows
from app.services.result_validation import validate_game_result_payload
from app.services.score_log import create_effective_score_logs_for_game, void_score_logs_for_game


GAME_REVIEW_LOAD_OPTIONS = (
    selectinload(Game.event_day).selectinload(EventDay.season),
    selectinload(Game.event_day).selectinload(EventDay.registrations).selectinload(Registration.user),
    selectinload(Game.format).selectinload(GameFormat.format_roles),
    selectinload(Game.format_snapshot).selectinload(GameFormatSnapshot.roles),
    selectinload(Game.judge).selectinload(User.user_roles).selectinload(UserRole.role),
    selectinload(Game.participants).selectinload(GameParticipant.user),
    selectinload(Game.participants).selectinload(GameParticipant.result).selectinload(GamePlayer.adjustments),
    selectinload(Game.players).selectinload(GamePlayer.participant).selectinload(GameParticipant.user),
    selectinload(Game.players).selectinload(GamePlayer.adjustments),
    selectinload(Game.score_logs),
)


def list_submitted_games_for_review(db: Session) -> list[GameReviewSummary]:
    """Return the submitted review queue for admin review pages."""

    statement = (
        select(Game)
        .options(*GAME_REVIEW_LOAD_OPTIONS)
        .where(Game.result_status == GameResultStatus.SUBMITTED)
        .order_by(Game.submitted_at.asc(), Game.id.asc())
    )
    return [GameReviewSummary.model_validate(game) for game in db.scalars(statement)]


def get_review_game_or_404(db: Session, game_id: int) -> Game:
    """Load a game with review-related relationships or raise 404."""

    statement = (
        select(Game)
        .options(*GAME_REVIEW_LOAD_OPTIONS)
        .where(Game.id == game_id)
        .execution_options(populate_existing=True)
    )
    game = db.scalar(statement)
    if game is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found.")
    return game


def _write_result_confirmation(
    db: Session,
    *,
    game: Game,
    submitted_by: int | None,
    submitted_at: datetime | None,
    admin_user_id: int,
    confirmation_status: ResultConfirmationStatus,
    comment: str | None,
) -> None:
    """Persist a result-confirmation history row for an admin action."""

    db.add(
        ResultConfirmation(
            game_id=game.id,
            submitted_by=submitted_by,
            submitted_at=submitted_at,
            confirmed_by=admin_user_id,
            confirmed_at=datetime.now(timezone.utc),
            confirmation_status=confirmation_status,
            comment=comment,
        )
    )


def _ensure_status(game: Game, allowed_statuses: set[GameResultStatus], message: str) -> None:
    """Ensure a game is in one of the allowed statuses before admin action."""

    if game.result_status not in allowed_statuses or game.play_status != GamePlayStatus.ENDED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)


def confirm_game_result(db: Session, game: Game, current_user: User, *, comment: str | None) -> Game:
    """Confirm a submitted result, make it effective, and write score logs."""

    game = lock_game_state(db, game, options=GAME_REVIEW_LOAD_OPTIONS)
    _ensure_status(game, {GameResultStatus.SUBMITTED}, "Only submitted results for ended games can be confirmed.")
    old_snapshot = build_game_snapshot(game)
    now = datetime.now(timezone.utc)

    game.confirmed_at = now
    game.confirmed_by = current_user.id
    transition_result_status(
        db,
        game,
        GameResultStatus.CONFIRMED,
        transition_key="confirm_result",
        changed_by=current_user.id,
        reason=comment,
    )

    _write_result_confirmation(
        db,
        game=game,
        submitted_by=game.submitted_by,
        submitted_at=game.submitted_at,
        admin_user_id=current_user.id,
        confirmation_status=ResultConfirmationStatus.APPROVED,
        comment=comment,
    )
    create_effective_score_logs_for_game(db, game, note="Confirmed game result.")
    validate_game_state(game)
    db.flush()

    refreshed_game = reload_game_for_audit(db, game.id)
    write_audit_log(
        db,
        actor_user_id=current_user.id,
        entity_type="game",
        entity_id=game.id,
        action_type="confirm",
        old_value_json=old_snapshot,
        new_value_json=build_game_snapshot(refreshed_game),
        reason=comment,
    )
    db.commit()
    return get_review_game_or_404(db, game.id)


def reject_game_result(db: Session, game: Game, current_user: User, *, comment: str) -> Game:
    """Reject a submitted result and reopen the game for judge work."""

    game = lock_game_state(db, game, options=GAME_REVIEW_LOAD_OPTIONS)
    _ensure_status(game, {GameResultStatus.SUBMITTED}, "Only submitted results for ended games can be rejected.")
    old_snapshot = build_game_snapshot(game)
    submitted_by = game.submitted_by
    submitted_at = game.submitted_at

    game.submitted_at = None
    game.submitted_by = None
    transition_result_status(
        db,
        game,
        GameResultStatus.REJECTED,
        transition_key="reject_result",
        changed_by=current_user.id,
        reason=comment,
    )

    _write_result_confirmation(
        db,
        game=game,
        submitted_by=submitted_by,
        submitted_at=submitted_at,
        admin_user_id=current_user.id,
        confirmation_status=ResultConfirmationStatus.REJECTED,
        comment=comment,
    )
    validate_game_state(game)
    db.flush()

    refreshed_game = reload_game_for_audit(db, game.id)
    write_audit_log(
        db,
        actor_user_id=current_user.id,
        entity_type="game",
        entity_id=game.id,
        action_type="reject",
        old_value_json=old_snapshot,
        new_value_json=build_game_snapshot(refreshed_game),
        reason=comment,
    )
    db.commit()
    return get_review_game_or_404(db, game.id)


def revise_game_result(db: Session, game: Game, payload: GameRevisionWrite, current_user: User) -> Game:
    """Apply an admin revision and rebuild the formal score ledger if needed."""

    game = lock_game_state(db, game, options=GAME_REVIEW_LOAD_OPTIONS)
    _ensure_status(
        game,
        {GameResultStatus.SUBMITTED, GameResultStatus.CONFIRMED, GameResultStatus.REVISED},
        "Only submitted or effective results for ended games can be revised.",
    )
    old_snapshot = build_game_snapshot(game)
    previous_status = game.result_status
    validation = validate_game_result_payload(game, payload, submit_mode=True)
    if validation.errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Revision validation failed.",
                "errors": [item.model_dump() for item in validation.errors],
                "warnings": [item.model_dump() for item in validation.warnings],
            },
        )

    affected_user_ids: set[int] = set()
    if previous_status in {GameResultStatus.CONFIRMED, GameResultStatus.REVISED}:
        affected_user_ids = void_score_logs_for_game(
            db,
            game.id,
            note="Voided because the game result was revised.",
        )

    reconcile_game_result_rows(db, game, payload, current_user)
    db.flush()
    game = get_review_game_or_404(db, game.id)

    game.confirmed_at = datetime.now(timezone.utc)
    game.confirmed_by = current_user.id
    transition_result_status(
        db,
        game,
        GameResultStatus.REVISED,
        transition_key="revise_result",
        changed_by=current_user.id,
        reason=payload.reason,
    )

    _write_result_confirmation(
        db,
        game=game,
        submitted_by=game.submitted_by,
        submitted_at=game.submitted_at,
        admin_user_id=current_user.id,
        confirmation_status=ResultConfirmationStatus.REVISED,
        comment=payload.reason,
    )
    create_effective_score_logs_for_game(
        db,
        game,
        note=f"Revised by admin: {payload.reason}",
        additional_affected_user_ids=affected_user_ids,
    )
    validate_game_state(game)
    db.flush()

    refreshed_game = reload_game_for_audit(db, game.id)
    write_audit_log(
        db,
        actor_user_id=current_user.id,
        entity_type="game",
        entity_id=game.id,
        action_type="revise",
        old_value_json=old_snapshot,
        new_value_json=build_game_snapshot(refreshed_game),
        reason=payload.reason,
    )
    db.commit()
    return get_review_game_or_404(db, game.id)
