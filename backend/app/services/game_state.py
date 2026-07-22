"""Centralized play and result state transitions for games."""

from datetime import datetime, timezone
from typing import Iterable

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import GamePlayStatus, GameResultStatus, GameStatusScope
from app.models.game import Game
from app.models.game_status_history import GameStatusHistory
from app.models.user import User
from app.services.audit import build_game_snapshot, reload_game_for_audit, write_audit_log
from app.services.format_snapshot import freeze_game_format


def lock_game_state(db: Session, game: Game, *, options: Iterable = ()) -> Game:
    """Lock and reload a game, rejecting an operation based on stale state."""

    expected_play_status = game.play_status
    expected_result_status = game.result_status
    expected_updated_at = game.updated_at
    statement = (
        select(Game)
        .options(*options)
        .where(Game.id == game.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    locked_game = db.scalar(statement)
    if locked_game is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found.")
    if (
        locked_game.play_status != expected_play_status
        or locked_game.result_status != expected_result_status
        or locked_game.updated_at != expected_updated_at
    ):
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The game state changed while this operation was waiting. Reload and try again.",
        )
    return locked_game


def ensure_play_operator(game: Game, current_user: User) -> None:
    """Allow admins or the assigned judge to start and end a game."""

    if "admin" in current_user.roles:
        return
    if "judge" in current_user.roles and current_user.id == game.judge_user_id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Only an admin or the assigned judge can change the game play state.",
    )


def _write_history(
    db: Session,
    *,
    game: Game,
    scope: GameStatusScope,
    old_status: str,
    new_status: str,
    transition_key: str,
    changed_by: int | None,
    reason: str | None,
) -> bool:
    if old_status == new_status:
        return False
    db.add(
        GameStatusHistory(
            game_id=game.id,
            status_scope=scope,
            transition_key=transition_key,
            old_status=old_status,
            new_status=new_status,
            changed_by=changed_by,
            reason=reason,
        )
    )
    return True


def transition_play_status(
    db: Session,
    game: Game,
    new_status: GamePlayStatus,
    *,
    transition_key: str,
    changed_by: int | None,
    reason: str | None = None,
    occurred_at: datetime | None = None,
) -> bool:
    """Apply one play-state transition and its lifecycle timestamps."""

    old_status = game.play_status
    if old_status == new_status:
        return False
    now = occurred_at or datetime.now(timezone.utc)
    if new_status == GamePlayStatus.IN_PROGRESS:
        if old_status != GamePlayStatus.SCHEDULED:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only scheduled games can be started.")
        game.started_at = now
        game.ended_at = None
        game.cancelled_at = None
        game.cancelled_by = None
        game.cancellation_reason = None
    elif new_status == GamePlayStatus.ENDED:
        if old_status != GamePlayStatus.IN_PROGRESS:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only in-progress games can be ended.")
        game.ended_at = now
    elif new_status == GamePlayStatus.CANCELLED:
        if old_status not in {GamePlayStatus.SCHEDULED, GamePlayStatus.IN_PROGRESS, GamePlayStatus.ENDED}:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This game cannot be cancelled from its current state.")
        game.cancelled_at = now
        game.cancellation_reason = reason
    else:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Unsupported play-state transition.")
    game.play_status = new_status
    return _write_history(
        db,
        game=game,
        scope=GameStatusScope.PLAY,
        old_status=old_status.value,
        new_status=new_status.value,
        transition_key=transition_key,
        changed_by=changed_by,
        reason=reason,
    )


def transition_result_status(
    db: Session,
    game: Game,
    new_status: GameResultStatus,
    *,
    transition_key: str,
    changed_by: int | None,
    reason: str | None = None,
) -> bool:
    """Apply a result-state value and record only real changes."""

    old_status = game.result_status
    if old_status == new_status:
        return False
    game.result_status = new_status
    return _write_history(
        db,
        game=game,
        scope=GameStatusScope.RESULT,
        old_status=old_status.value,
        new_status=new_status.value,
        transition_key=transition_key,
        changed_by=changed_by,
        reason=reason,
    )


def validate_game_state(game: Game) -> None:
    """Validate timestamp and cross-state invariants before commit."""

    if game.play_status == GamePlayStatus.IN_PROGRESS and game.started_at is None:
        raise RuntimeError("An in-progress game must have started_at.")
    if game.play_status == GamePlayStatus.ENDED and (game.started_at is None or game.ended_at is None):
        raise RuntimeError("An ended game must have started_at and ended_at.")
    if game.play_status == GamePlayStatus.CANCELLED and (
        game.cancelled_at is None or not game.cancellation_reason
    ):
        raise RuntimeError("A cancelled game must have cancellation metadata.")
    if game.result_status == GameResultStatus.SUBMITTED and (
        game.play_status != GamePlayStatus.ENDED
        or game.submitted_at is None
        or game.submitted_by is None
    ):
        raise RuntimeError("A submitted result requires an ended game and submission metadata.")
    if game.result_status in {GameResultStatus.CONFIRMED, GameResultStatus.REVISED} and (
        game.play_status != GamePlayStatus.ENDED
        or game.confirmed_at is None
        or game.confirmed_by is None
    ):
        raise RuntimeError("A confirmed or revised result requires an ended game and confirmation metadata.")
    requires_snapshot = (
        game.play_status in {GamePlayStatus.IN_PROGRESS, GamePlayStatus.ENDED}
        or (game.play_status == GamePlayStatus.CANCELLED and game.started_at is not None)
        or game.result_status != GameResultStatus.EMPTY
    )
    if requires_snapshot and game.format_snapshot is None:
        raise RuntimeError("A started or result-bearing game must have frozen format context.")


def write_game_state_audit(
    db: Session,
    *,
    game: Game,
    current_user: User,
    action_type: str,
    old_snapshot: dict,
    reason: str | None = None,
) -> Game:
    """Flush and write an audit snapshot inside the caller's transaction."""

    db.flush()
    refreshed_game = reload_game_for_audit(db, game.id)
    write_audit_log(
        db,
        actor_user_id=current_user.id,
        entity_type="game",
        entity_id=game.id,
        action_type=action_type,
        old_value_json=old_snapshot,
        new_value_json=build_game_snapshot(refreshed_game),
        reason=reason,
    )
    return refreshed_game


def start_game(db: Session, game: Game, current_user: User) -> Game:
    """Start one scheduled game."""

    game = lock_game_state(db, game)
    ensure_play_operator(game, current_user)
    if game.play_status == GamePlayStatus.IN_PROGRESS:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The game is already in progress.")
    old_snapshot = build_game_snapshot(game)
    freeze_game_format(db, game, frozen_by_user_id=current_user.id)
    transition_play_status(
        db,
        game,
        GamePlayStatus.IN_PROGRESS,
        transition_key="start_game",
        changed_by=current_user.id,
    )
    validate_game_state(game)
    refreshed = write_game_state_audit(
        db,
        game=game,
        current_user=current_user,
        action_type="start_game",
        old_snapshot=old_snapshot,
    )
    db.commit()
    return refreshed


def end_game(db: Session, game: Game, current_user: User) -> Game:
    """End one in-progress game."""

    game = lock_game_state(db, game)
    ensure_play_operator(game, current_user)
    if game.play_status == GamePlayStatus.ENDED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The game has already ended.")
    old_snapshot = build_game_snapshot(game)
    transition_play_status(
        db,
        game,
        GamePlayStatus.ENDED,
        transition_key="end_game",
        changed_by=current_user.id,
    )
    validate_game_state(game)
    refreshed = write_game_state_audit(
        db,
        game=game,
        current_user=current_user,
        action_type="end_game",
        old_snapshot=old_snapshot,
    )
    db.commit()
    return refreshed


def cancel_game(db: Session, game: Game, current_user: User, *, reason: str) -> Game:
    """Cancel an unreviewed game; score-bearing cancellation remains deferred."""

    game = lock_game_state(db, game)
    if "admin" not in current_user.roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can cancel games.")
    if game.play_status == GamePlayStatus.CANCELLED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The game is already cancelled.")
    if game.result_status in {
        GameResultStatus.SUBMITTED,
        GameResultStatus.CONFIRMED,
        GameResultStatus.REVISED,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Submitted or effective results require a dedicated score-void cancellation flow.",
        )
    old_snapshot = build_game_snapshot(game)
    transition_play_status(
        db,
        game,
        GamePlayStatus.CANCELLED,
        transition_key="cancel_game",
        changed_by=current_user.id,
        reason=reason,
    )
    game.cancelled_by = current_user.id
    validate_game_state(game)
    refreshed = write_game_state_audit(
        db,
        game=game,
        current_user=current_user,
        action_type="cancel_game",
        old_snapshot=old_snapshot,
        reason=reason,
    )
    db.commit()
    return refreshed
