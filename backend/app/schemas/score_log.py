"""Schemas for formal score-log ledger payloads."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.enums import ScoreLogEffectiveStatus, ScoreLogSourceType


class ScoreLogRead(BaseModel):
    """Single formal score ledger entry."""

    id: int
    user_id: int
    game_id: int
    source_type: ScoreLogSourceType
    delta: float
    balance_after: float
    note: str | None
    effective_status: ScoreLogEffectiveStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

