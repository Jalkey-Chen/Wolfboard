"""Score-ledger helpers for confirmation, revision, and leaderboard support."""

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import ScoreLogEffectiveStatus, ScoreLogSourceType
from app.models.event_day import EventDay
from app.models.game import Game
from app.models.score_log import ScoreLog


def void_score_logs_for_game(db: Session, game_id: int, *, note: str | None = None) -> None:
    """Mark all effective score logs for a game as voided."""

    statement = select(ScoreLog).where(
        ScoreLog.game_id == game_id,
        ScoreLog.effective_status == ScoreLogEffectiveStatus.EFFECTIVE,
    )
    for score_log in db.scalars(statement):
        score_log.effective_status = ScoreLogEffectiveStatus.VOIDED
        if note:
            score_log.note = note
        db.add(score_log)


def create_effective_score_logs_for_game(db: Session, game: Game, *, note: str | None = None) -> list[ScoreLog]:
    """Write fresh effective score logs from the current persisted game result."""

    created_logs: list[ScoreLog] = []
    for player in game.players:
        if player.user_id is None:
            continue
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
    recalculate_season_balances(db, game.season_id, user_ids={player.user_id for player in game.players if player.user_id is not None})
    return created_logs


def recalculate_season_balances(db: Session, season_id: int | None, *, user_ids: set[int] | None = None) -> None:
    """Rebuild `balance_after` values for effective logs within a season."""

    if season_id is None:
        return

    statement = (
        select(ScoreLog)
        .join(ScoreLog.game)
        .join(Game.event_day)
        .where(
            EventDay.season_id == season_id,
            ScoreLog.effective_status == ScoreLogEffectiveStatus.EFFECTIVE,
        )
        .order_by(ScoreLog.user_id.asc(), ScoreLog.created_at.asc(), ScoreLog.id.asc())
    )
    if user_ids:
        statement = statement.where(ScoreLog.user_id.in_(user_ids))

    balances: dict[int, float] = defaultdict(float)
    for score_log in db.scalars(statement):
        balances[score_log.user_id] += score_log.delta
        score_log.balance_after = balances[score_log.user_id]
        db.add(score_log)

