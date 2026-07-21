"""Score-ledger helpers for confirmation, revision, and leaderboard support."""

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import (
    GameResultStatus,
    GamePlayStatus,
    GameType,
    ScoreLogEffectiveStatus,
    ScoreLogSourceType,
)
from app.models.event_day import EventDay
from app.models.game import Game
from app.models.score_log import ScoreLog


OFFICIAL_STANDING_RESULT_STATUSES = frozenset({GameResultStatus.CONFIRMED, GameResultStatus.REVISED})


def game_affects_official_standings(
    game_type: GameType,
    play_status: GamePlayStatus,
    result_status: GameResultStatus,
) -> bool:
    """Return whether a game's effective logs contribute to formal standings."""

    return (
        game_type == GameType.OFFICIAL
        and play_status == GamePlayStatus.ENDED
        and result_status in OFFICIAL_STANDING_RESULT_STATUSES
    )


def official_score_log_filters():
    """Return the shared SQL criteria for effective formal-standing rows."""

    return (
        Game.game_type == GameType.OFFICIAL,
        Game.play_status == GamePlayStatus.ENDED,
        Game.result_status.in_(OFFICIAL_STANDING_RESULT_STATUSES),
        ScoreLog.effective_status == ScoreLogEffectiveStatus.EFFECTIVE,
    )


def void_score_logs_for_game(db: Session, game_id: int, *, note: str | None = None) -> set[int]:
    """Void a game's effective logs and return every affected user ID."""

    statement = select(ScoreLog).where(
        ScoreLog.game_id == game_id,
        ScoreLog.effective_status == ScoreLogEffectiveStatus.EFFECTIVE,
    )
    affected_user_ids: set[int] = set()
    for score_log in db.scalars(statement):
        affected_user_ids.add(score_log.user_id)
        score_log.effective_status = ScoreLogEffectiveStatus.VOIDED
        if note:
            score_log.note = note
        db.add(score_log)
    db.flush()
    return affected_user_ids


def create_effective_score_logs_for_game(
    db: Session,
    game: Game,
    *,
    note: str | None = None,
    additional_affected_user_ids: set[int] | None = None,
) -> list[ScoreLog]:
    """Write fresh effective score logs from the current persisted game result."""

    created_logs: list[ScoreLog] = []
    affected_user_ids = set(additional_affected_user_ids or ())
    for player in game.players:
        if player.user_id is None:
            continue
        affected_user_ids.add(player.user_id)
        score_log = ScoreLog(
            user_id=player.user_id,
            game_id=game.id,
            source_type=ScoreLogSourceType.GAME_RESULT,
            delta=player.final_score,
            balance_after=0.0,
            note=note,
            effective_status=ScoreLogEffectiveStatus.EFFECTIVE,
        )
        db.add(score_log)
        created_logs.append(score_log)

    db.flush()
    # Balances are recomputed after every confirm or revise action so the
    # season ledger stays consistent even when older games are revised later.
    recalculate_season_balances(db, game.season_id, user_ids=affected_user_ids)
    return created_logs


def recalculate_season_balances(db: Session, season_id: int | None, *, user_ids: set[int] | None = None) -> None:
    """Rebuild `balance_after` values for effective logs within a season."""

    if season_id is None:
        return

    statement = (
        select(ScoreLog, Game.game_type, Game.play_status, Game.result_status)
        .join(ScoreLog.game)
        .join(Game.event_day)
        .where(
            EventDay.season_id == season_id,
            ScoreLog.effective_status == ScoreLogEffectiveStatus.EFFECTIVE,
        )
        .order_by(
            ScoreLog.user_id.asc(),
            EventDay.event_date.asc(),
            Game.game_number.asc(),
            Game.table_number.asc(),
            Game.id.asc(),
            ScoreLog.id.asc(),
        )
    )
    if user_ids:
        statement = statement.where(ScoreLog.user_id.in_(user_ids))

    balances: dict[int, float] = defaultdict(float)
    for score_log, game_type, play_status, result_status in db.execute(statement):
        if game_affects_official_standings(game_type, play_status, result_status):
            balances[score_log.user_id] += score_log.delta
        score_log.balance_after = balances[score_log.user_id]
        db.add(score_log)
