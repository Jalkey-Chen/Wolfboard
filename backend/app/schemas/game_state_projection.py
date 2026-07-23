"""API schemas for deterministic effective-event projections."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class ProjectionReadModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProjectionIssueRead(ProjectionReadModel):
    code: str
    severity: Literal["info", "warning"]
    message_key: str
    event_ids: tuple[int, ...]
    participant_ids: tuple[int, ...]
    round_no: int | None
    phase: str | None
    details: dict[str, Any]


class PhaseDerivedStateRead(ProjectionReadModel):
    current_phase: str | None
    current_round_no: int | None
    phase_is_open: bool
    phase_started_event_id: int | None
    last_completed_phase: str | None
    last_completed_round_no: int | None
    last_completed_event_id: int | None
    last_observed_phase: str | None
    last_observed_round_no: int | None
    last_observed_event_id: int | None


class ParticipantDerivedStateRead(ProjectionReadModel):
    participant_id: int
    user_id: int | None
    seat_number: int | None
    display_name_snapshot: str | None
    recorded_role_name: str | None
    recorded_faction: str | None
    is_active_in_game: bool
    has_exile_record: bool
    has_death_record: bool
    exile_event_ids: tuple[int, ...]
    death_event_ids: tuple[int, ...]
    exit_event_ids: tuple[int, ...]
    first_exit_logical_sequence: int | None
    latest_exit_logical_sequence: int | None


class ParticipantEventProvenanceRead(ProjectionReadModel):
    participant_id: int
    event_ids: tuple[int, ...]


class SheriffDerivedStateRead(ProjectionReadModel):
    badge_status: Literal["unassigned", "held", "destroyed"]
    current_sheriff_participant_id: int | None
    elected_event_id: int | None
    last_transfer_event_id: int | None
    destroyed_event_id: int | None
    current_candidate_participant_ids: tuple[int, ...]
    withdrawn_participant_ids: tuple[int, ...]
    declaration_provenance: tuple[ParticipantEventProvenanceRead, ...]
    withdrawal_provenance: tuple[ParticipantEventProvenanceRead, ...]


class VoteRecordRead(ProjectionReadModel):
    event_id: int
    voter_participant_id: int | None
    target_participant_id: int | None
    vote_weight: float
    logical_sequence_no: int


class TallyEntryRead(ProjectionReadModel):
    participant_id: int
    vote_weight: float


class ExplicitTieRecordRead(ProjectionReadModel):
    event_id: int
    candidate_participant_ids: tuple[int, ...]


class RevoteRecordRead(ProjectionReadModel):
    event_id: int
    eligible_participant_ids: tuple[int, ...]


class BallotDerivedStateRead(ProjectionReadModel):
    vote_kind: Literal["sheriff", "exile"]
    round_no: int
    ballot_no: int
    vote_event_ids: tuple[int, ...]
    vote_records: tuple[VoteRecordRead, ...]
    abstention_records: tuple[VoteRecordRead, ...]
    voter_participant_ids: tuple[int, ...]
    duplicate_voter_participant_ids: tuple[int, ...]
    raw_tally: tuple[TallyEntryRead, ...]
    computed_tally: tuple[TallyEntryRead, ...] | None
    tally_is_unambiguous: bool
    explicit_tie_records: tuple[ExplicitTieRecordRead, ...]
    revote_records: tuple[RevoteRecordRead, ...]
    explicit_outcome_event_ids: tuple[int, ...]


class ParticipantRecordedActionUsageRead(ProjectionReadModel):
    participant_id: int
    recorded_seer_check_count: int
    recorded_witch_antidote_count: int
    recorded_witch_poison_count: int
    recorded_guard_protection_count: int
    recorded_hunter_shot_count: int
    recorded_wolf_king_shot_count: int
    recorded_wolf_self_explosion_count: int
    recorded_sheriff_vote_count: int
    recorded_exile_vote_count: int


class RecordedActionSummaryRead(ProjectionReadModel):
    event_type: str
    phase: str
    round_no: int
    actor_participant_id: int | None
    event_ids: tuple[int, ...]
    recorded_count: int
    latest_recorded_target_participant_id: int | None


class EventTypeCountRead(ProjectionReadModel):
    event_type: str
    count: int


class RoundSummaryRead(ProjectionReadModel):
    round_no: int
    phase: str
    event_count: int
    event_ids: tuple[int, ...]
    phase_started_event_ids: tuple[int, ...]
    phase_completed_event_ids: tuple[int, ...]
    night_resolved_event_ids: tuple[int, ...]
    event_type_counts: tuple[EventTypeCountRead, ...]


class NightResolvedRecordRead(ProjectionReadModel):
    event_id: int
    round_no: int
    no_public_death: bool
    note: str | None


class GameDerivedStateRead(ProjectionReadModel):
    projection_version: Literal[1]
    projection_kind: Literal["effective_event_projection"]
    game_id: int
    through_logical_sequence: int | None
    event_ledger_head_sequence: int
    effective_event_count: int
    last_applied_logical_sequence: int | None
    has_format_snapshot: bool
    is_rule_engine_result: Literal[False]
    format_snapshot_id: int | None
    format_key: str | None
    format_name: str | None
    snapshot_schema_version: int | None
    phase: PhaseDerivedStateRead
    participants: tuple[ParticipantDerivedStateRead, ...]
    sheriff: SheriffDerivedStateRead
    ballots: tuple[BallotDerivedStateRead, ...]
    recorded_action_usage: tuple[ParticipantRecordedActionUsageRead, ...]
    recorded_actions: tuple[RecordedActionSummaryRead, ...]
    round_summaries: tuple[RoundSummaryRead, ...]
    night_resolutions: tuple[NightResolvedRecordRead, ...]
    issues: tuple[ProjectionIssueRead, ...]
