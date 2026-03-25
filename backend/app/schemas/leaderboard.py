"""Schemas for leaderboard aggregation responses."""

from pydantic import BaseModel


class LeaderboardEntryRead(BaseModel):
    """One ranked row in a season leaderboard."""

    ranking: int
    user_id: int
    username: str
    display_name: str
    total_score: float
    games_played: int
    wins: int

