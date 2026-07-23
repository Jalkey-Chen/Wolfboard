"""Central V1 event definitions and payload-reference extraction."""

from dataclasses import dataclass
from enum import Enum
from typing import Literal

from pydantic import BaseModel

from app.core.enums import (
    GameEventPhase,
    GameEventSource,
    GameEventType,
    GameEventVisibility,
)
from app.schemas.game_event import (
    AntidotePayload,
    BallotPayload,
    EmptyPayload,
    ExileRevoteStartedPayload,
    NightResolvedPayload,
    NotePayload,
    PlayerDiedPayload,
    PoisonPayload,
    ReasonPayload,
    SeerCheckedPayload,
    SelectionNotePayload,
    SheriffElectedPayload,
    TriggerEventPayload,
    VoteCastPayload,
    VoteTiedPayload,
)


class ReferencePolicy(str, Enum):
    REQUIRED = "required"
    OPTIONAL = "optional"
    FORBIDDEN = "forbidden"


@dataclass(frozen=True)
class EventDefinition:
    event_type: GameEventType
    allowed_phases: frozenset[GameEventPhase]
    default_visibility: GameEventVisibility
    actor: ReferencePolicy
    target: ReferencePolicy
    allows_secondary_target: bool
    payload_schema: type[BaseModel]
    allowed_sources: frozenset[GameEventSource]
    description: str
    payload_field_semantics: dict[str, Literal[
        "participant_id",
        "participant_id_list",
        "event_id",
        "event_id_list",
    ]]


NIGHT = frozenset({GameEventPhase.NIGHT})
DAY = frozenset({GameEventPhase.DAY})
ANY_PHASE = frozenset(GameEventPhase)
ALL_SOURCES = frozenset(GameEventSource)


def _definition(
    event_type: GameEventType,
    phases: frozenset[GameEventPhase],
    visibility: GameEventVisibility,
    actor: ReferencePolicy,
    target: ReferencePolicy,
    payload_schema: type[BaseModel],
    description: str,
    payload_field_semantics: dict[str, Literal[
        "participant_id",
        "participant_id_list",
        "event_id",
        "event_id_list",
    ]] | None = None,
) -> EventDefinition:
    return EventDefinition(
        event_type=event_type,
        allowed_phases=phases,
        default_visibility=visibility,
        actor=actor,
        target=target,
        allows_secondary_target=False,
        payload_schema=payload_schema,
        allowed_sources=ALL_SOURCES,
        description=description,
        payload_field_semantics=payload_field_semantics or {},
    )


EVENT_DEFINITIONS = {
    item.event_type: item
    for item in [
        _definition(GameEventType.PHASE_STARTED, ANY_PHASE, GameEventVisibility.PUBLIC, ReferencePolicy.FORBIDDEN, ReferencePolicy.FORBIDDEN, EmptyPayload, "Marks an in-game phase start."),
        _definition(GameEventType.PHASE_COMPLETED, ANY_PHASE, GameEventVisibility.PUBLIC, ReferencePolicy.FORBIDDEN, ReferencePolicy.FORBIDDEN, NotePayload, "Marks an in-game phase completion."),
        _definition(GameEventType.WOLF_KILL_SELECTED, NIGHT, GameEventVisibility.POSTGAME_FULL, ReferencePolicy.OPTIONAL, ReferencePolicy.REQUIRED, SelectionNotePayload, "Records the wolves' final kill target."),
        _definition(GameEventType.SEER_CHECKED, NIGHT, GameEventVisibility.POSTGAME_FULL, ReferencePolicy.REQUIRED, ReferencePolicy.REQUIRED, SeerCheckedPayload, "Records a seer inspection and shown faction."),
        _definition(GameEventType.WITCH_SAVED, NIGHT, GameEventVisibility.POSTGAME_FULL, ReferencePolicy.REQUIRED, ReferencePolicy.REQUIRED, AntidotePayload, "Records antidote use."),
        _definition(GameEventType.WITCH_POISONED, NIGHT, GameEventVisibility.POSTGAME_FULL, ReferencePolicy.REQUIRED, ReferencePolicy.REQUIRED, PoisonPayload, "Records poison use."),
        _definition(GameEventType.GUARD_PROTECTED, NIGHT, GameEventVisibility.POSTGAME_FULL, ReferencePolicy.REQUIRED, ReferencePolicy.REQUIRED, EmptyPayload, "Records a guard target."),
        _definition(GameEventType.NIGHT_RESOLVED, NIGHT, GameEventVisibility.PUBLIC, ReferencePolicy.FORBIDDEN, ReferencePolicy.FORBIDDEN, NightResolvedPayload, "Records public night resolution metadata."),
        _definition(GameEventType.SHERIFF_CANDIDATE_DECLARED, DAY, GameEventVisibility.PUBLIC, ReferencePolicy.REQUIRED, ReferencePolicy.FORBIDDEN, EmptyPayload, "Records a sheriff candidate."),
        _definition(GameEventType.SHERIFF_CANDIDATE_WITHDREW, DAY, GameEventVisibility.PUBLIC, ReferencePolicy.REQUIRED, ReferencePolicy.FORBIDDEN, EmptyPayload, "Records candidate withdrawal."),
        _definition(GameEventType.SHERIFF_VOTE_CAST, DAY, GameEventVisibility.PUBLIC, ReferencePolicy.REQUIRED, ReferencePolicy.OPTIONAL, VoteCastPayload, "Records one sheriff ballot."),
        _definition(GameEventType.SHERIFF_ELECTED, DAY, GameEventVisibility.PUBLIC, ReferencePolicy.FORBIDDEN, ReferencePolicy.REQUIRED, SheriffElectedPayload, "Records the elected sheriff."),
        _definition(GameEventType.EXILE_VOTE_CAST, DAY, GameEventVisibility.PUBLIC, ReferencePolicy.REQUIRED, ReferencePolicy.OPTIONAL, VoteCastPayload, "Records one exile ballot."),
        _definition(GameEventType.VOTE_TIED, DAY, GameEventVisibility.PUBLIC, ReferencePolicy.FORBIDDEN, ReferencePolicy.FORBIDDEN, VoteTiedPayload, "Records a tied vote.", {"candidate_participant_ids": "participant_id_list"}),
        _definition(GameEventType.EXILE_REVOTE_STARTED, DAY, GameEventVisibility.PUBLIC, ReferencePolicy.FORBIDDEN, ReferencePolicy.FORBIDDEN, ExileRevoteStartedPayload, "Records an exile revote field.", {"eligible_participant_ids": "participant_id_list"}),
        _definition(GameEventType.PLAYER_EXILED, DAY, GameEventVisibility.PUBLIC, ReferencePolicy.FORBIDDEN, ReferencePolicy.REQUIRED, BallotPayload, "Records the exile result."),
        _definition(GameEventType.HUNTER_SHOT, ANY_PHASE, GameEventVisibility.PUBLIC, ReferencePolicy.REQUIRED, ReferencePolicy.REQUIRED, TriggerEventPayload, "Records a hunter shot.", {"trigger_event_id": "event_id"}),
        _definition(GameEventType.WOLF_SELF_EXPLODED, DAY, GameEventVisibility.PUBLIC, ReferencePolicy.REQUIRED, ReferencePolicy.FORBIDDEN, NotePayload, "Records a wolf self-explosion."),
        _definition(GameEventType.WOLF_KING_SHOT, ANY_PHASE, GameEventVisibility.PUBLIC, ReferencePolicy.REQUIRED, ReferencePolicy.REQUIRED, TriggerEventPayload, "Records a wolf-king shot.", {"trigger_event_id": "event_id"}),
        _definition(GameEventType.SHERIFF_BADGE_TRANSFERRED, DAY, GameEventVisibility.PUBLIC, ReferencePolicy.REQUIRED, ReferencePolicy.REQUIRED, ReasonPayload, "Records badge transfer."),
        _definition(GameEventType.SHERIFF_BADGE_DESTROYED, DAY, GameEventVisibility.PUBLIC, ReferencePolicy.REQUIRED, ReferencePolicy.FORBIDDEN, ReasonPayload, "Records badge destruction."),
        _definition(GameEventType.PLAYER_DIED, ANY_PHASE, GameEventVisibility.PUBLIC, ReferencePolicy.OPTIONAL, ReferencePolicy.REQUIRED, PlayerDiedPayload, "Records one player death fact.", {"source_event_ids": "event_id_list"}),
    ]
}


def payload_participant_ids(payload: BaseModel) -> set[int]:
    if isinstance(payload, VoteTiedPayload):
        return set(payload.candidate_participant_ids)
    if isinstance(payload, ExileRevoteStartedPayload):
        return set(payload.eligible_participant_ids)
    return set()


def payload_event_ids(payload: BaseModel) -> set[int]:
    if isinstance(payload, TriggerEventPayload):
        return {payload.trigger_event_id} if payload.trigger_event_id is not None else set()
    if isinstance(payload, PlayerDiedPayload):
        return set(payload.source_event_ids or [])
    return set()
