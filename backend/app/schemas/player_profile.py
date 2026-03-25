"""Schemas for player profile and result history pages."""

from datetime import date, datetime

from pydantic import BaseModel

from app.core.enums import GameStatus, GameType, ScoreLogEffectiveStatus


class PlayerProfileGameRead(BaseModel):
    """Historical game row shown on a player profile page."""

    game_id: int
    season_id: int
    season_name: str
    event_day_id: int
    event_day_title: str
    event_day_date: date
    table_number: int
    game_number: int
    game_type: GameType
    game_status: GameStatus
    delta: float
    balance_after: float
    effective_status: ScoreLogEffectiveStatus
    created_at: datetime


class PlayerProfileRead(BaseModel):
    """Top-level player profile payload with official score and history."""

    user_id: int
    username: str
    display_name: str
    total_score: float
    games_played: int
    history: list[PlayerProfileGameRead]

