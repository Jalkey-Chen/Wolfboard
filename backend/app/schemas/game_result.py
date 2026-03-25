"""Schemas for judge-owned result draft reads, saves, and submissions."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import GamePlayerFaction, GamePlayerFinalStatus, ScoreAdjustmentType
from app.schemas.game import GameDetail
from app.schemas.game_format import FormatRoleRead


class ValidationMessage(BaseModel):
    """Single human-readable validation issue returned by result APIs."""

    code: str
    message: str
    field: str | None = None


class ValidationSummary(BaseModel):
    """Error and warning lists describing current draft validity."""

    errors: list[ValidationMessage] = Field(default_factory=list)
    warnings: list[ValidationMessage] = Field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        """Return whether the summary contains blocking validation errors."""

        return len(self.errors) > 0


class SelectablePlayerRead(BaseModel):
    """Player option returned for result-entry user selection controls."""

    user_id: int
    username: str
    display_name: str
    registration_status: str | None = None
    check_in_status: str | None = None


class GameResultPlayerInput(BaseModel):
    """Draft input row for one player result entry."""

    user_id: int | None = None
    seat_number: int | None = None
    role_name: str | None = None
    faction: GamePlayerFaction | None = None
    final_status: GamePlayerFinalStatus = GamePlayerFinalStatus.UNKNOWN
    is_winner: bool | None = None
    remarks: str | None = None


class GameResultAdjustmentInput(BaseModel):
    """Draft input row for one explicit score adjustment."""

    target_seat_number: int
    adjustment_type: ScoreAdjustmentType
    delta: float
    reason: str | None = None


class GameResultDraftWrite(BaseModel):
    """Payload used by the assigned judge to replace the current draft."""

    players: list[GameResultPlayerInput] = Field(default_factory=list)
    adjustments: list[GameResultAdjustmentInput] = Field(default_factory=list)


class GameResultPlayerRead(BaseModel):
    """Persisted player result row returned by draft and submit endpoints."""

    id: int
    game_id: int
    user_id: int | None
    username: str
    display_name: str
    seat_number: int | None
    role_name: str | None
    faction: GamePlayerFaction | None
    final_status: GamePlayerFinalStatus
    is_winner: bool | None
    base_score: float
    adjustment_score: float
    final_score: float
    judge_bonus_note: str | None
    penalty_note: str | None
    remarks: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GameResultAdjustmentRead(BaseModel):
    """Persisted score adjustment line returned by draft and submit endpoints."""

    id: int
    game_player_id: int
    target_seat_number: int | None
    adjustment_type: ScoreAdjustmentType
    delta: float
    reason: str | None
    created_by: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GameResultDraftRead(BaseModel):
    """Full result-draft payload used by the result-entry page."""

    game: GameDetail
    players: list[GameResultPlayerRead]
    adjustments: list[GameResultAdjustmentRead]
    format_roles: list[FormatRoleRead]
    selectable_players: list[SelectablePlayerRead]
    validation: ValidationSummary
    editable: bool
