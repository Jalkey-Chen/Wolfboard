"""Audit-log query and snapshot helpers for admin result actions."""

from datetime import date, datetime
from enum import Enum
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.audit_log import AuditLog
from app.models.event_day import EventDay
from app.models.game import Game
from app.models.game_participant import GameParticipant
from app.models.game_player import GamePlayer
from app.models.game_format_snapshot import GameFormatSnapshot
from app.models.score_adjustment import ScoreAdjustment
from app.models.score_log import ScoreLog
from app.models.user import User


AUDIT_GAME_LOAD_OPTIONS = (
    selectinload(Game.event_day).selectinload(EventDay.season),
    selectinload(Game.format),
    selectinload(Game.format_snapshot).selectinload(GameFormatSnapshot.roles),
    selectinload(Game.judge).selectinload(User.user_roles),
    selectinload(Game.players).selectinload(GamePlayer.participant).selectinload(GameParticipant.user),
    selectinload(Game.players).selectinload(GamePlayer.adjustments),
    selectinload(Game.score_logs),
)


def _to_jsonable(value: Any) -> Any:
    """Convert enums and datetime-like values into JSON-safe primitives."""

    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    return value


def reload_game_for_audit(db: Session, game_id: int) -> Game:
    """Reload a game with the relationships needed for audit snapshots."""

    statement = (
        select(Game)
        .options(*AUDIT_GAME_LOAD_OPTIONS)
        .where(Game.id == game_id)
        .execution_options(populate_existing=True)
    )
    return db.scalar(statement)


def build_game_snapshot(game: Game) -> dict[str, Any]:
    """Serialize the current game, result, and ledger state for auditing."""

    players = []
    adjustments = []

    for player in game.players:
        players.append(
            _to_jsonable(
                {
                    "id": player.id,
                    "participant_id": player.participant_id,
                    "user_id": player.user_id,
                    "username": player.username,
                    "display_name": player.display_name,
                    "seat_number": player.seat_number,
                    "role_name": player.role_name,
                    "faction": player.faction,
                    "final_status": player.final_status,
                    "is_winner": player.is_winner,
                    "base_score": player.base_score,
                    "adjustment_score": player.adjustment_score,
                    "final_score": player.final_score,
                    "judge_bonus_note": player.judge_bonus_note,
                    "penalty_note": player.penalty_note,
                    "remarks": player.remarks,
                }
            )
        )
        for adjustment in player.adjustments:
            adjustments.append(
                _to_jsonable(
                    {
                        "id": adjustment.id,
                        "game_player_id": adjustment.game_player_id,
                        "target_seat_number": adjustment.target_seat_number,
                        "adjustment_type": adjustment.adjustment_type,
                        "delta": adjustment.delta,
                        "reason": adjustment.reason,
                        "created_by": adjustment.created_by,
                    }
                )
            )

    score_logs = [
        _to_jsonable(
            {
                "id": log.id,
                "user_id": log.user_id,
                "delta": log.delta,
                "balance_after": log.balance_after,
                "source_type": log.source_type,
                "effective_status": log.effective_status,
                "note": log.note,
                "created_at": log.created_at,
            }
        )
        for log in game.score_logs
    ]

    return _to_jsonable(
        {
            "game": {
                "id": game.id,
                "season_id": game.season_id,
                "season_name": game.season_name,
                "event_day_id": game.event_day_id,
                "event_day_title": game.event_day_title,
                "game_number": game.game_number,
                "table_number": game.table_number,
                "format_id": game.format_id,
                "format_name": game.format_name,
                "format_snapshot_id": game.format_snapshot_id,
                "format_snapshot_origin": (
                    game.format_snapshot.snapshot_origin if game.format_snapshot is not None else None
                ),
                "format_snapshot_frozen_at": (
                    game.format_snapshot.frozen_at if game.format_snapshot is not None else None
                ),
                "judge_user_id": game.judge_user_id,
                "judge_display_name": game.judge_display_name,
                "game_type": game.game_type,
                "play_status": game.play_status,
                "result_status": game.result_status,
                "started_at": game.started_at,
                "ended_at": game.ended_at,
                "submitted_at": game.submitted_at,
                "submitted_by": game.submitted_by,
                "confirmed_at": game.confirmed_at,
                "confirmed_by": game.confirmed_by,
                "cancelled_at": game.cancelled_at,
                "cancelled_by": game.cancelled_by,
                "cancellation_reason": game.cancellation_reason,
                "notes": game.notes,
            },
            "players": players,
            "adjustments": adjustments,
            "score_logs": score_logs,
        }
    )


def write_audit_log(
    db: Session,
    *,
    actor_user_id: int | None,
    entity_type: str,
    entity_id: int,
    action_type: str,
    old_value_json: dict | list | None,
    new_value_json: dict | list | None,
    reason: str | None,
) -> AuditLog:
    """Create an audit-log row for a critical admin action."""

    audit_log = AuditLog(
        actor_user_id=actor_user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action_type=action_type,
        old_value_json=old_value_json,
        new_value_json=new_value_json,
        reason=reason,
    )
    db.add(audit_log)
    return audit_log


def list_audit_logs(
    db: Session,
    *,
    entity_type: str | None = None,
    actor_user_id: int | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
) -> list[AuditLog]:
    """Return audit logs filtered by common admin review criteria."""

    statement = select(AuditLog).options(selectinload(AuditLog.actor)).order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    if entity_type:
        statement = statement.where(AuditLog.entity_type == entity_type)
    if actor_user_id is not None:
        statement = statement.where(AuditLog.actor_user_id == actor_user_id)
    if created_from is not None:
        statement = statement.where(AuditLog.created_at >= created_from)
    if created_to is not None:
        statement = statement.where(AuditLog.created_at <= created_to)
    return list(db.scalars(statement))
