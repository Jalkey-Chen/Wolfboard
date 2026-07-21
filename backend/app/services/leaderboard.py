"""Leaderboard aggregation helpers built from effective score logs."""

from collections import defaultdict

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.event_day import EventDay
from app.models.game import Game
from app.models.game_player import GamePlayer
from app.models.score_log import ScoreLog
from app.models.season import Season
from app.models.user import User
from app.schemas.leaderboard import LeaderboardEntryRead
from app.services.score_log import official_score_log_filters


def get_season_leaderboard(db: Session, season_id: int) -> list[LeaderboardEntryRead]:
    """Aggregate the official leaderboard for a season from effective score logs."""

    _ = db.get(Season, season_id)
    statement = (
        select(ScoreLog, User, GamePlayer.is_winner)
        .join(ScoreLog.user)
        .join(ScoreLog.game)
        .join(Game.event_day)
        .outerjoin(
            GamePlayer,
            and_(GamePlayer.game_id == ScoreLog.game_id, GamePlayer.user_id == ScoreLog.user_id),
        )
        .where(
            EventDay.season_id == season_id,
            *official_score_log_filters(),
        )
        .order_by(User.display_name.asc(), ScoreLog.created_at.asc(), ScoreLog.id.asc())
    )

    aggregates: dict[int, dict[str, object]] = {}
    for score_log, user, is_winner in db.execute(statement):
        entry = aggregates.setdefault(
            user.id,
            {
                "user_id": user.id,
                "username": user.username,
                "display_name": user.display_name,
                "total_score": 0.0,
                "games_played": 0,
                "wins": 0,
            },
        )
        entry["total_score"] = float(entry["total_score"]) + score_log.delta
        entry["games_played"] = int(entry["games_played"]) + 1
        if is_winner:
            entry["wins"] = int(entry["wins"]) + 1

    ranked = sorted(
        aggregates.values(),
        key=lambda item: (-float(item["total_score"]), -int(item["wins"]), str(item["display_name"]).lower(), int(item["user_id"])),
    )

    return [
        LeaderboardEntryRead(
            ranking=index + 1,
            user_id=int(item["user_id"]),
            username=str(item["username"]),
            display_name=str(item["display_name"]),
            total_score=float(item["total_score"]),
            games_played=int(item["games_played"]),
            wins=int(item["wins"]),
        )
        for index, item in enumerate(ranked)
    ]
