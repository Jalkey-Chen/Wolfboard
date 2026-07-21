"""Player profile aggregation helpers."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import GamePlayStatus, GameResultStatus, ScoreLogEffectiveStatus
from app.models.event_day import EventDay
from app.models.game import Game
from app.models.score_log import ScoreLog
from app.models.user import User
from app.schemas.player_profile import PlayerProfileGameRead, PlayerProfileRead
from app.services.score_log import game_affects_official_standings


def get_player_profile_or_404(db: Session, player_id: int) -> User:
    """Return a player user row or raise a not-found error upstream via `None`."""

    player = db.get(User, player_id)
    if player is None:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not found.")
    return player


def build_player_profile(db: Session, player_id: int) -> PlayerProfileRead:
    """Build a player profile from effective score logs and confirmed games."""

    player = get_player_profile_or_404(db, player_id)
    statement = (
        select(ScoreLog, Game, EventDay)
        .join(ScoreLog.game)
        .join(Game.event_day)
        .where(
            ScoreLog.user_id == player_id,
            ScoreLog.effective_status == ScoreLogEffectiveStatus.EFFECTIVE,
            Game.play_status == GamePlayStatus.ENDED,
            Game.result_status.in_([GameResultStatus.CONFIRMED, GameResultStatus.REVISED]),
        )
        .order_by(EventDay.event_date.desc(), Game.table_number.asc(), Game.game_number.asc(), ScoreLog.id.desc())
    )

    history: list[PlayerProfileGameRead] = []
    total_score = 0.0
    games_played = 0

    for score_log, game, event_day in db.execute(statement):
        if game_affects_official_standings(game.game_type, game.play_status, game.result_status):
            total_score += score_log.delta
            games_played += 1

        history.append(
            PlayerProfileGameRead(
                game_id=game.id,
                season_id=event_day.season_id,
                season_name=game.season_name,
                event_day_id=event_day.id,
                event_day_title=event_day.title,
                event_day_date=event_day.event_date,
                table_number=game.table_number,
                game_number=game.game_number,
                game_type=game.game_type,
                play_status=game.play_status,
                result_status=game.result_status,
                delta=score_log.delta,
                balance_after=score_log.balance_after,
                effective_status=score_log.effective_status,
                created_at=score_log.created_at,
            )
        )

    return PlayerProfileRead(
        user_id=player.id,
        username=player.username,
        display_name=player.display_name,
        total_score=total_score,
        games_played=games_played,
        history=history,
    )
