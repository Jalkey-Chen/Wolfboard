"""API and V1 payload schemas for the structured game-event ledger."""

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.core.enums import (
    FormatRoleFaction,
    GameDeathCause,
    GameEventPhase,
    GameEventSource,
    GameEventStatus,
    GameEventType,
    GameEventVisibility,
)


NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
ClientEventId = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


class StrictPayload(BaseModel):
    """Base payload rejecting fields outside the registered V1 contract."""

    model_config = ConfigDict(extra="forbid")


class EmptyPayload(StrictPayload):
    pass


class NotePayload(StrictPayload):
    note: str | None = Field(default=None, max_length=1000)


class SelectionNotePayload(StrictPayload):
    selection_note: str | None = Field(default=None, max_length=1000)


class SeerCheckedPayload(StrictPayload):
    result_faction: FormatRoleFaction


class AntidotePayload(StrictPayload):
    potion: Literal["antidote"]


class PoisonPayload(StrictPayload):
    potion: Literal["poison"]


class NightResolvedPayload(StrictPayload):
    no_public_death: bool
    note: str | None = Field(default=None, max_length=1000)


class VoteCastPayload(StrictPayload):
    ballot_no: int = Field(gt=0)
    vote_weight: float = Field(default=1, gt=0)


class SheriffElectedPayload(StrictPayload):
    ballot_no: int = Field(gt=0)
    tally: dict[str, float] | None = None

    @field_validator("tally")
    @classmethod
    def validate_tally(cls, value: dict[str, float] | None) -> dict[str, float] | None:
        if value is not None and any(not key.strip() or score < 0 for key, score in value.items()):
            raise ValueError("Tally keys must be non-empty and values must be non-negative.")
        return value


def _unique_non_empty_ids(value: list[int]) -> list[int]:
    if not value:
        raise ValueError("At least one participant ID is required.")
    if any(item <= 0 for item in value):
        raise ValueError("Participant IDs must be positive.")
    if len(value) != len(set(value)):
        raise ValueError("Participant IDs must be unique.")
    return value


class VoteTiedPayload(StrictPayload):
    vote_kind: Literal["sheriff", "exile"]
    ballot_no: int = Field(gt=0)
    candidate_participant_ids: list[int]

    @field_validator("candidate_participant_ids")
    @classmethod
    def validate_candidates(cls, value: list[int]) -> list[int]:
        return _unique_non_empty_ids(value)


class ExileRevoteStartedPayload(StrictPayload):
    ballot_no: int = Field(gt=0)
    eligible_participant_ids: list[int]

    @field_validator("eligible_participant_ids")
    @classmethod
    def validate_eligible(cls, value: list[int]) -> list[int]:
        return _unique_non_empty_ids(value)


class BallotPayload(StrictPayload):
    ballot_no: int = Field(gt=0)


class TriggerEventPayload(StrictPayload):
    trigger_event_id: int | None = Field(default=None, gt=0)


class ReasonPayload(StrictPayload):
    reason: str | None = Field(default=None, max_length=1000)


class PlayerDiedPayload(StrictPayload):
    cause: GameDeathCause
    source_event_ids: list[int] | None = None
    public_note: str | None = Field(default=None, max_length=1000)

    @field_validator("source_event_ids")
    @classmethod
    def validate_source_events(cls, value: list[int] | None) -> list[int] | None:
        if value is None:
            return None
        if any(item <= 0 for item in value):
            raise ValueError("Event IDs must be positive.")
        if len(value) != len(set(value)):
            raise ValueError("Event IDs must be unique.")
        return value


class GameEventBody(BaseModel):
    """Client-editable event body shared by create and correction requests."""

    phase: GameEventPhase
    round_no: int = Field(ge=1)
    event_type: GameEventType
    actor_participant_id: int | None = Field(default=None, gt=0)
    target_participant_id: int | None = Field(default=None, gt=0)
    secondary_target_participant_id: int | None = Field(default=None, gt=0)
    payload: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime | None = None
    client_event_id: ClientEventId | None = None
    model_config = ConfigDict(extra="forbid")

    @field_validator("occurred_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.utcoffset() is None:
            raise ValueError("occurred_at must include a timezone offset.")
        return value


class GameEventCreate(GameEventBody):
    pass


class GameEventCorrection(GameEventBody):
    reason: NonEmptyText


class GameEventVoid(BaseModel):
    reason: NonEmptyText
    model_config = ConfigDict(extra="forbid")


class GameEventParticipantRead(BaseModel):
    participant_id: int
    seat_number: int | None
    display_name_snapshot: str | None


class GameEventUserRead(BaseModel):
    user_id: int
    username: str
    display_name: str


class GameEventRead(BaseModel):
    id: int
    game_id: int
    sequence_no: int
    logical_sequence_no: int
    phase: GameEventPhase
    round_no: int
    event_type: GameEventType
    actor_participant_id: int | None
    target_participant_id: int | None
    secondary_target_participant_id: int | None
    actor: GameEventParticipantRead | None
    target: GameEventParticipantRead | None
    secondary_target: GameEventParticipantRead | None
    payload: dict[str, Any]
    visibility: GameEventVisibility
    source: GameEventSource
    schema_version: int
    status: GameEventStatus
    supersedes_event_id: int | None
    revision_reason: str | None
    invalidated_at: datetime | None
    invalidated_by_user_id: int | None
    invalidation_reason: str | None
    created_by_user_id: int
    created_by: GameEventUserRead
    created_at: datetime
    occurred_at: datetime | None
    client_event_id: str | None


GameEventView = Literal["effective", "ledger"]
