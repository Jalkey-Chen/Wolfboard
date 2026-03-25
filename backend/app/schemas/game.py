"""Schemas for game list, detail, and admin management workflows."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.core.enums import GameStatus, GameType


class JudgeOptionRead(BaseModel):
    """Compact judge-capable user payload used by admin assignment forms."""

    id: int
    username: str
    display_name: str

    model_config = ConfigDict(from_attributes=True)


class GameFormatOptionRead(BaseModel):
    """Compact format payload embedded inside game detail responses."""

    id: int
    format_name: str
    format_key: str
    player_count: int

    model_config = ConfigDict(from_attributes=True)


class GameJudgeRead(JudgeOptionRead):
    """Judge payload embedded in game detail responses."""


class GameCreate(BaseModel):
    """Payload used by admins to create a game under an event day."""

    event_day_id: int
    game_number: int
    table_number: int
    format_id: int
    judge_user_id: int
    game_type: GameType = GameType.OFFICIAL
    status: GameStatus = GameStatus.DRAFT
    notes: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None


class GameUpdate(BaseModel):
    """Partial admin payload used to edit a game's setup fields."""

    game_number: int | None = None
    table_number: int | None = None
    format_id: int | None = None
    judge_user_id: int | None = None
    game_type: GameType | None = None
    status: GameStatus | None = None
    notes: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None


class GameSummary(BaseModel):
    """Compact game payload used by event-day pages and judge queues."""

    id: int
    event_day_id: int
    season_id: int
    season_name: str
    event_day_title: str
    event_day_date: date
    game_number: int
    table_number: int
    format_id: int
    format_name: str
    judge_user_id: int
    judge_display_name: str
    game_type: GameType
    status: GameStatus
    started_at: datetime | None
    ended_at: datetime | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GameDetail(GameSummary):
    """Detailed game payload used by admin and judge game detail pages."""

    event_day_venue: str
    format: GameFormatOptionRead
    judge: GameJudgeRead
    submitted_at: datetime | None
    submitted_by: int | None
    confirmed_at: datetime | None
    confirmed_by: int | None
