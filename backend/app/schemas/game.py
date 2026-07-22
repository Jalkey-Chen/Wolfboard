"""Schemas for game list, detail, and admin management workflows."""

from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.core.enums import GamePlayStatus, GameResultStatus, GameType


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
    notes: str | None = None
    model_config = ConfigDict(extra="forbid")


class GameUpdate(BaseModel):
    """Partial admin payload used to edit a game's setup fields."""

    game_number: int | None = None
    table_number: int | None = None
    format_id: int | None = None
    judge_user_id: int | None = None
    game_type: GameType | None = None
    notes: str | None = None
    model_config = ConfigDict(extra="forbid")


class GameCancelRequest(BaseModel):
    """Required reason for the dedicated game cancellation transition."""

    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


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
    play_status: GamePlayStatus
    result_status: GameResultStatus
    started_at: datetime | None
    ended_at: datetime | None
    cancelled_at: datetime | None
    cancelled_by: int | None
    cancellation_reason: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
    has_format_snapshot: bool
    format_snapshot_id: int | None

    model_config = ConfigDict(from_attributes=True)


class GameDetail(GameSummary):
    """Detailed game payload used by admin and judge game detail pages."""

    event_day_venue: str
    format: GameFormatOptionRead
    judge: GameJudgeRead
    has_result_draft: bool
    submitted_at: datetime | None
    submitted_by: int | None
    confirmed_at: datetime | None
    confirmed_by: int | None
