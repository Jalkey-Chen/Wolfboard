"""Schemas for admin review queue and confirmation actions."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.game import GameSummary
from app.schemas.game_result import GameResultDraftWrite


class GameReviewSummary(GameSummary):
    """Queue row for submitted games waiting on admin review."""

    submitted_at: datetime | None
    submitted_by: int | None


class GameConfirmRequest(BaseModel):
    """Optional admin comment attached when confirming a result."""

    comment: str | None = None


class GameRejectRequest(BaseModel):
    """Required rejection comment for a submitted result."""

    comment: str = Field(min_length=1)


class GameRevisionWrite(GameResultDraftWrite):
    """Admin revision payload for directly effective result changes."""

    reason: str = Field(min_length=1)

