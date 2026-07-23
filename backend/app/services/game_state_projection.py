"""Pure deterministic projection of the current effective game-event timeline."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Mapping, Sequence

from app.core.enums import GameEventType


PROJECTOR_VERSION = 1
PROJECTION_KIND = "effective_event_projection"


@dataclass(frozen=True)
class GameProjectionContext:
    game_id: int
    play_status: str
    result_status: str
    format_snapshot_id: int | None
    format_key: str | None
    format_name: str | None
    snapshot_schema_version: int | None
    snapshot_player_count: int | None
    snapshot_role_names: tuple[str, ...]
    event_ledger_head_sequence: int
    started_at: datetime | None
    ended_at: datetime | None


@dataclass(frozen=True)
class ParticipantProjectionInput:
    participant_id: int
    user_id: int | None
    seat_number: int | None
    display_name_snapshot: str | None
    role_name: str | None
    faction: str | None


@dataclass(frozen=True)
class GameEventProjectionInput:
    id: int
    game_id: int
    logical_sequence_no: int
    sequence_no: int
    phase: str
    round_no: int
    event_type: str
    actor_participant_id: int | None
    target_participant_id: int | None
    secondary_target_participant_id: int | None
    payload: Mapping[str, Any]
    visibility: str
    source: str
    schema_version: int


@dataclass(frozen=True)
class ProjectionIssue:
    code: str
    severity: str
    message_key: str
    event_ids: tuple[int, ...] = ()
    participant_ids: tuple[int, ...] = ()
    round_no: int | None = None
    phase: str | None = None
    details: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PhaseDerivedState:
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


@dataclass(frozen=True)
class ParticipantDerivedState:
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


@dataclass(frozen=True)
class ParticipantEventProvenance:
    participant_id: int
    event_ids: tuple[int, ...]


@dataclass(frozen=True)
class SheriffDerivedState:
    badge_status: str
    current_sheriff_participant_id: int | None
    elected_event_id: int | None
    last_transfer_event_id: int | None
    destroyed_event_id: int | None
    current_candidate_participant_ids: tuple[int, ...]
    withdrawn_participant_ids: tuple[int, ...]
    declaration_provenance: tuple[ParticipantEventProvenance, ...]
    withdrawal_provenance: tuple[ParticipantEventProvenance, ...]


@dataclass(frozen=True)
class VoteRecord:
    event_id: int
    voter_participant_id: int | None
    target_participant_id: int | None
    vote_weight: float
    logical_sequence_no: int


@dataclass(frozen=True)
class TallyEntry:
    participant_id: int
    vote_weight: float


@dataclass(frozen=True)
class ExplicitTieRecord:
    event_id: int
    candidate_participant_ids: tuple[int, ...]


@dataclass(frozen=True)
class RevoteRecord:
    event_id: int
    eligible_participant_ids: tuple[int, ...]


@dataclass(frozen=True)
class BallotDerivedState:
    vote_kind: str
    round_no: int
    ballot_no: int
    vote_event_ids: tuple[int, ...]
    vote_records: tuple[VoteRecord, ...]
    abstention_records: tuple[VoteRecord, ...]
    voter_participant_ids: tuple[int, ...]
    duplicate_voter_participant_ids: tuple[int, ...]
    raw_tally: tuple[TallyEntry, ...]
    computed_tally: tuple[TallyEntry, ...] | None
    tally_is_unambiguous: bool
    explicit_tie_records: tuple[ExplicitTieRecord, ...]
    revote_records: tuple[RevoteRecord, ...]
    explicit_outcome_event_ids: tuple[int, ...]


@dataclass(frozen=True)
class ParticipantRecordedActionUsage:
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


@dataclass(frozen=True)
class RecordedActionSummary:
    event_type: str
    phase: str
    round_no: int
    actor_participant_id: int | None
    event_ids: tuple[int, ...]
    recorded_count: int
    latest_recorded_target_participant_id: int | None


@dataclass(frozen=True)
class EventTypeCount:
    event_type: str
    count: int


@dataclass(frozen=True)
class RoundSummary:
    round_no: int
    phase: str
    event_count: int
    event_ids: tuple[int, ...]
    phase_started_event_ids: tuple[int, ...]
    phase_completed_event_ids: tuple[int, ...]
    night_resolved_event_ids: tuple[int, ...]
    event_type_counts: tuple[EventTypeCount, ...]


@dataclass(frozen=True)
class NightResolvedRecord:
    event_id: int
    round_no: int
    no_public_death: bool
    note: str | None


@dataclass(frozen=True)
class GameDerivedState:
    projection_version: int
    projection_kind: str
    game_id: int
    through_logical_sequence: int | None
    event_ledger_head_sequence: int
    effective_event_count: int
    last_applied_logical_sequence: int | None
    has_format_snapshot: bool
    is_rule_engine_result: bool
    format_snapshot_id: int | None
    format_key: str | None
    format_name: str | None
    snapshot_schema_version: int | None
    phase: PhaseDerivedState
    participants: tuple[ParticipantDerivedState, ...]
    sheriff: SheriffDerivedState
    ballots: tuple[BallotDerivedState, ...]
    recorded_action_usage: tuple[ParticipantRecordedActionUsage, ...]
    recorded_actions: tuple[RecordedActionSummary, ...]
    round_summaries: tuple[RoundSummary, ...]
    night_resolutions: tuple[NightResolvedRecord, ...]
    issues: tuple[ProjectionIssue, ...]


@dataclass
class _ParticipantState:
    source: ParticipantProjectionInput
    exile_events: list[tuple[int, int]] = field(default_factory=list)
    death_events: list[tuple[int, int]] = field(default_factory=list)

    @property
    def active(self) -> bool:
        return not self.exile_events and not self.death_events


@dataclass
class _BallotState:
    vote_kind: str
    round_no: int
    ballot_no: int
    votes: list[VoteRecord] = field(default_factory=list)
    raw_tally: dict[int, Decimal] = field(default_factory=dict)
    voter_counts: Counter[int] = field(default_factory=Counter)
    ties: list[ExplicitTieRecord] = field(default_factory=list)
    revotes: list[RevoteRecord] = field(default_factory=list)
    outcomes: list[int] = field(default_factory=list)


@dataclass
class _ActionState:
    event_ids: list[int] = field(default_factory=list)
    latest_target: int | None = None


@dataclass
class _RoundState:
    event_ids: list[int] = field(default_factory=list)
    phase_started_ids: list[int] = field(default_factory=list)
    phase_completed_ids: list[int] = field(default_factory=list)
    night_resolved_ids: list[int] = field(default_factory=list)
    type_counts: Counter[str] = field(default_factory=Counter)


@dataclass
class _ProjectionState:
    context: GameProjectionContext
    participants: dict[int, _ParticipantState]
    issues: list[ProjectionIssue] = field(default_factory=list)
    current_phase: str | None = None
    current_round: int | None = None
    phase_started_event_id: int | None = None
    last_completed_phase: str | None = None
    last_completed_round: int | None = None
    last_completed_event_id: int | None = None
    last_observed_phase: str | None = None
    last_observed_round: int | None = None
    last_observed_event_id: int | None = None
    candidates: set[int] = field(default_factory=set)
    withdrawn: set[int] = field(default_factory=set)
    declarations: dict[int, list[int]] = field(default_factory=lambda: defaultdict(list))
    withdrawals: dict[int, list[int]] = field(default_factory=lambda: defaultdict(list))
    badge_status: str = "unassigned"
    sheriff_id: int | None = None
    elected_event_id: int | None = None
    transfer_event_id: int | None = None
    destroyed_event_id: int | None = None
    ballots: dict[tuple[str, int, int], _BallotState] = field(default_factory=dict)
    usage: dict[int, Counter[str]] = field(default_factory=lambda: defaultdict(Counter))
    actions: dict[tuple[str, str, int, int | None], _ActionState] = field(default_factory=dict)
    rounds: dict[tuple[int, str], _RoundState] = field(default_factory=dict)
    night_resolutions: list[NightResolvedRecord] = field(default_factory=list)
    last_applied_logical_sequence: int | None = None

    def issue(
        self,
        code: str,
        *,
        severity: str = "warning",
        event_ids: Sequence[int] = (),
        participant_ids: Sequence[int] = (),
        event: GameEventProjectionInput | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        self.issues.append(
            ProjectionIssue(
                code=code,
                severity=severity,
                message_key=f"projection.issue.{code}",
                event_ids=tuple(event_ids),
                participant_ids=tuple(sorted(set(participant_ids))),
                round_no=event.round_no if event else None,
                phase=event.phase if event else None,
                details=dict(details or {}),
            )
        )

    def ballot(self, vote_kind: str, event: GameEventProjectionInput, ballot_no: int) -> _BallotState:
        key = (vote_kind, event.round_no, ballot_no)
        if key not in self.ballots:
            self.ballots[key] = _BallotState(vote_kind, event.round_no, ballot_no)
        return self.ballots[key]


def _payload_int(
    state: _ProjectionState,
    event: GameEventProjectionInput,
    key: str,
    *,
    default: int = 1,
) -> int:
    value = event.payload.get(key, default)
    if isinstance(value, bool):
        state.issue("invalid_projection_payload", event_ids=(event.id,), event=event, details={"field": key})
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        state.issue("invalid_projection_payload", event_ids=(event.id,), event=event, details={"field": key})
        return default
    if parsed < 1:
        state.issue("invalid_projection_payload", event_ids=(event.id,), event=event, details={"field": key})
        return default
    return parsed


def _payload_decimal(
    state: _ProjectionState,
    event: GameEventProjectionInput,
    key: str,
    *,
    default: Decimal = Decimal("1"),
) -> Decimal:
    try:
        value = Decimal(str(event.payload.get(key, default)))
    except (InvalidOperation, TypeError, ValueError):
        state.issue("invalid_projection_payload", event_ids=(event.id,), event=event, details={"field": key})
        return default
    if not value.is_finite() or value <= 0:
        state.issue("invalid_projection_payload", event_ids=(event.id,), event=event, details={"field": key})
        return default
    return value


def _payload_id_list(event: GameEventProjectionInput, key: str) -> tuple[int, ...]:
    value = event.payload.get(key, ())
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(item for item in value if isinstance(item, int) and not isinstance(item, bool))


def _reduce_phase_started(state: _ProjectionState, event: GameEventProjectionInput) -> None:
    if state.current_phase is not None:
        state.issue(
            "phase_started_while_another_phase_open",
            event_ids=tuple(filter(None, (state.phase_started_event_id, event.id))),
            event=event,
            details={"open_phase": state.current_phase, "open_round_no": state.current_round},
        )
    state.current_phase = event.phase
    state.current_round = event.round_no
    state.phase_started_event_id = event.id


def _reduce_phase_completed(state: _ProjectionState, event: GameEventProjectionInput) -> None:
    if state.current_phase is None:
        state.issue("phase_completed_without_open_phase", event_ids=(event.id,), event=event)
    elif state.current_phase != event.phase or state.current_round != event.round_no:
        state.issue(
            "phase_completed_mismatch",
            event_ids=tuple(filter(None, (state.phase_started_event_id, event.id))),
            event=event,
            details={"open_phase": state.current_phase, "open_round_no": state.current_round},
        )
    state.last_completed_phase = event.phase
    state.last_completed_round = event.round_no
    state.last_completed_event_id = event.id
    if state.current_phase == event.phase and state.current_round == event.round_no:
        state.current_phase = None
        state.current_round = None
        state.phase_started_event_id = None


def _record_action(state: _ProjectionState, event: GameEventProjectionInput, usage_key: str | None) -> None:
    key = (event.event_type, event.phase, event.round_no, event.actor_participant_id)
    action = state.actions.setdefault(key, _ActionState())
    action.event_ids.append(event.id)
    action.latest_target = event.target_participant_id
    if usage_key and event.actor_participant_id in state.participants:
        state.usage[event.actor_participant_id][usage_key] += 1


def _reduce_wolf_kill_selected(state: _ProjectionState, event: GameEventProjectionInput) -> None:
    _record_action(state, event, None)


def _reduce_seer_checked(state: _ProjectionState, event: GameEventProjectionInput) -> None:
    _record_action(state, event, "seer")


def _reduce_witch_saved(state: _ProjectionState, event: GameEventProjectionInput) -> None:
    _record_action(state, event, "witch_antidote")


def _reduce_witch_poisoned(state: _ProjectionState, event: GameEventProjectionInput) -> None:
    _record_action(state, event, "witch_poison")


def _reduce_guard_protected(state: _ProjectionState, event: GameEventProjectionInput) -> None:
    _record_action(state, event, "guard")


def _reduce_hunter_shot(state: _ProjectionState, event: GameEventProjectionInput) -> None:
    _record_action(state, event, "hunter")


def _reduce_wolf_self_exploded(state: _ProjectionState, event: GameEventProjectionInput) -> None:
    _record_action(state, event, "wolf_self_explosion")


def _reduce_wolf_king_shot(state: _ProjectionState, event: GameEventProjectionInput) -> None:
    _record_action(state, event, "wolf_king")


def _reduce_night_resolved(state: _ProjectionState, event: GameEventProjectionInput) -> None:
    existing = [item.event_id for item in state.night_resolutions if item.round_no == event.round_no]
    if existing:
        state.issue(
            "multiple_night_resolved_events",
            event_ids=(*existing, event.id),
            event=event,
        )
    state.night_resolutions.append(
        NightResolvedRecord(
            event_id=event.id,
            round_no=event.round_no,
            no_public_death=bool(event.payload.get("no_public_death", False)),
            note=event.payload.get("note") if isinstance(event.payload.get("note"), str) else None,
        )
    )


def _reduce_sheriff_candidate_declared(
    state: _ProjectionState, event: GameEventProjectionInput
) -> None:
    actor = event.actor_participant_id
    if actor is None or actor not in state.participants:
        return
    state.candidates.add(actor)
    state.declarations[actor].append(event.id)


def _reduce_sheriff_candidate_withdrew(
    state: _ProjectionState, event: GameEventProjectionInput
) -> None:
    actor = event.actor_participant_id
    if actor is None or actor not in state.participants:
        return
    if actor not in state.candidates:
        state.issue(
            "candidate_withdrew_without_declaration",
            event_ids=(event.id,),
            participant_ids=(actor,),
            event=event,
        )
    state.candidates.discard(actor)
    state.withdrawn.add(actor)
    state.withdrawals[actor].append(event.id)


def _reassign_badge(state: _ProjectionState, event: GameEventProjectionInput, target: int) -> None:
    if state.badge_status == "destroyed":
        state.issue(
            "badge_reassigned_after_destroyed",
            event_ids=tuple(filter(None, (state.destroyed_event_id, event.id))),
            participant_ids=(target,),
            event=event,
        )
    state.badge_status = "held"
    state.sheriff_id = target


def _reduce_sheriff_elected(state: _ProjectionState, event: GameEventProjectionInput) -> None:
    target = event.target_participant_id
    if target is None or target not in state.participants:
        return
    if state.badge_status == "held":
        state.issue(
            "sheriff_elected_while_badge_held",
            event_ids=tuple(filter(None, (state.elected_event_id, state.transfer_event_id, event.id))),
            participant_ids=tuple(filter(None, (state.sheriff_id, target))),
            event=event,
        )
    _reassign_badge(state, event, target)
    state.elected_event_id = event.id
    ballot = state.ballot("sheriff", event, _payload_int(state, event, "ballot_no"))
    ballot.outcomes.append(event.id)


def _reduce_sheriff_badge_transferred(
    state: _ProjectionState, event: GameEventProjectionInput
) -> None:
    actor = event.actor_participant_id
    target = event.target_participant_id
    if target is None or target not in state.participants:
        return
    if state.sheriff_id is None:
        state.issue(
            "badge_transfer_without_current_sheriff",
            event_ids=(event.id,),
            participant_ids=tuple(filter(None, (actor, target))),
            event=event,
        )
    elif actor != state.sheriff_id:
        state.issue(
            "badge_transfer_actor_mismatch",
            event_ids=(event.id,),
            participant_ids=tuple(filter(None, (state.sheriff_id, actor, target))),
            event=event,
            details={"expected_actor_participant_id": state.sheriff_id},
        )
    _reassign_badge(state, event, target)
    state.transfer_event_id = event.id


def _reduce_sheriff_badge_destroyed(
    state: _ProjectionState, event: GameEventProjectionInput
) -> None:
    actor = event.actor_participant_id
    if state.sheriff_id is None:
        state.issue(
            "badge_destroyed_without_holder",
            event_ids=(event.id,),
            participant_ids=tuple(filter(None, (actor,))),
            event=event,
        )
    state.sheriff_id = None
    state.badge_status = "destroyed"
    state.destroyed_event_id = event.id


def _record_vote(state: _ProjectionState, event: GameEventProjectionInput, vote_kind: str) -> None:
    ballot_no = _payload_int(state, event, "ballot_no")
    weight = _payload_decimal(state, event, "vote_weight")
    ballot = state.ballot(vote_kind, event, ballot_no)
    record = VoteRecord(
        event_id=event.id,
        voter_participant_id=event.actor_participant_id,
        target_participant_id=event.target_participant_id,
        vote_weight=float(weight),
        logical_sequence_no=event.logical_sequence_no,
    )
    ballot.votes.append(record)
    if event.actor_participant_id in state.participants:
        ballot.voter_counts[event.actor_participant_id] += 1
        state.usage[event.actor_participant_id][f"{vote_kind}_vote"] += 1
    if event.target_participant_id in state.participants:
        ballot.raw_tally[event.target_participant_id] = (
            ballot.raw_tally.get(event.target_participant_id, Decimal("0")) + weight
        )


def _reduce_sheriff_vote_cast(state: _ProjectionState, event: GameEventProjectionInput) -> None:
    _record_vote(state, event, "sheriff")


def _reduce_exile_vote_cast(state: _ProjectionState, event: GameEventProjectionInput) -> None:
    _record_vote(state, event, "exile")


def _reduce_vote_tied(state: _ProjectionState, event: GameEventProjectionInput) -> None:
    vote_kind = event.payload.get("vote_kind")
    if vote_kind not in {"sheriff", "exile"}:
        state.issue(
            "invalid_projection_payload",
            event_ids=(event.id,),
            event=event,
            details={"field": "vote_kind"},
        )
        return
    ballot = state.ballot(vote_kind, event, _payload_int(state, event, "ballot_no"))
    ballot.ties.append(
        ExplicitTieRecord(
            event_id=event.id,
            candidate_participant_ids=_payload_id_list(event, "candidate_participant_ids"),
        )
    )


def _reduce_exile_revote_started(
    state: _ProjectionState, event: GameEventProjectionInput
) -> None:
    ballot = state.ballot("exile", event, _payload_int(state, event, "ballot_no"))
    ballot.revotes.append(
        RevoteRecord(
            event_id=event.id,
            eligible_participant_ids=_payload_id_list(event, "eligible_participant_ids"),
        )
    )


def _record_exit(
    state: _ProjectionState,
    event: GameEventProjectionInput,
    *,
    exit_kind: str,
) -> None:
    target = event.target_participant_id
    participant = state.participants.get(target) if target is not None else None
    if participant is None:
        return
    existing = participant.exile_events if exit_kind == "exile" else participant.death_events
    if existing:
        state.issue(
            f"duplicate_{exit_kind}_record",
            event_ids=(*(item[0] for item in existing), event.id),
            participant_ids=(target,),
            event=event,
        )
    if participant.exile_events or participant.death_events:
        state.issue(
            "multiple_exit_records",
            event_ids=(
                *(item[0] for item in participant.exile_events),
                *(item[0] for item in participant.death_events),
                event.id,
            ),
            participant_ids=(target,),
            event=event,
        )
    existing.append((event.id, event.logical_sequence_no))


def _reduce_player_exiled(state: _ProjectionState, event: GameEventProjectionInput) -> None:
    _record_exit(state, event, exit_kind="exile")
    ballot = state.ballot("exile", event, _payload_int(state, event, "ballot_no"))
    ballot.outcomes.append(event.id)


def _reduce_player_died(state: _ProjectionState, event: GameEventProjectionInput) -> None:
    _record_exit(state, event, exit_kind="death")


EventReducer = Callable[[_ProjectionState, GameEventProjectionInput], None]

EVENT_REDUCERS: dict[str, EventReducer] = {
    GameEventType.PHASE_STARTED.value: _reduce_phase_started,
    GameEventType.PHASE_COMPLETED.value: _reduce_phase_completed,
    GameEventType.WOLF_KILL_SELECTED.value: _reduce_wolf_kill_selected,
    GameEventType.SEER_CHECKED.value: _reduce_seer_checked,
    GameEventType.WITCH_SAVED.value: _reduce_witch_saved,
    GameEventType.WITCH_POISONED.value: _reduce_witch_poisoned,
    GameEventType.GUARD_PROTECTED.value: _reduce_guard_protected,
    GameEventType.NIGHT_RESOLVED.value: _reduce_night_resolved,
    GameEventType.SHERIFF_CANDIDATE_DECLARED.value: _reduce_sheriff_candidate_declared,
    GameEventType.SHERIFF_CANDIDATE_WITHDREW.value: _reduce_sheriff_candidate_withdrew,
    GameEventType.SHERIFF_VOTE_CAST.value: _reduce_sheriff_vote_cast,
    GameEventType.SHERIFF_ELECTED.value: _reduce_sheriff_elected,
    GameEventType.EXILE_VOTE_CAST.value: _reduce_exile_vote_cast,
    GameEventType.VOTE_TIED.value: _reduce_vote_tied,
    GameEventType.EXILE_REVOTE_STARTED.value: _reduce_exile_revote_started,
    GameEventType.PLAYER_EXILED.value: _reduce_player_exiled,
    GameEventType.HUNTER_SHOT.value: _reduce_hunter_shot,
    GameEventType.WOLF_SELF_EXPLODED.value: _reduce_wolf_self_exploded,
    GameEventType.WOLF_KING_SHOT.value: _reduce_wolf_king_shot,
    GameEventType.SHERIFF_BADGE_TRANSFERRED.value: _reduce_sheriff_badge_transferred,
    GameEventType.SHERIFF_BADGE_DESTROYED.value: _reduce_sheriff_badge_destroyed,
    GameEventType.PLAYER_DIED.value: _reduce_player_died,
}


def _participant_references(event: GameEventProjectionInput) -> set[int]:
    references = {
        item
        for item in (
            event.actor_participant_id,
            event.target_participant_id,
            event.secondary_target_participant_id,
        )
        if item is not None
    }
    for key in ("candidate_participant_ids", "eligible_participant_ids"):
        references.update(_payload_id_list(event, key))
    return references


def _record_round(state: _ProjectionState, event: GameEventProjectionInput) -> None:
    summary = state.rounds.setdefault((event.round_no, event.phase), _RoundState())
    summary.event_ids.append(event.id)
    summary.type_counts[event.event_type] += 1
    if event.event_type == GameEventType.PHASE_STARTED.value:
        summary.phase_started_ids.append(event.id)
    elif event.event_type == GameEventType.PHASE_COMPLETED.value:
        summary.phase_completed_ids.append(event.id)
    elif event.event_type == GameEventType.NIGHT_RESOLVED.value:
        summary.night_resolved_ids.append(event.id)


def _record_common_event_issues(
    state: _ProjectionState, event: GameEventProjectionInput
) -> None:
    unknown = _participant_references(event) - state.participants.keys()
    if unknown:
        state.issue(
            "unknown_participant_reference",
            event_ids=(event.id,),
            participant_ids=tuple(unknown),
            event=event,
        )
    actor = state.participants.get(event.actor_participant_id)
    if actor is not None and not actor.active:
        state.issue(
            "event_actor_already_out",
            event_ids=(event.id,),
            participant_ids=(actor.source.participant_id,),
            event=event,
        )
    target = state.participants.get(event.target_participant_id)
    if target is not None and not target.active:
        state.issue(
            "event_target_already_out",
            event_ids=(event.id,),
            participant_ids=(target.source.participant_id,),
            event=event,
        )


def _finalize_participants(state: _ProjectionState) -> tuple[ParticipantDerivedState, ...]:
    result = []
    ordered = sorted(
        state.participants.values(),
        key=lambda item: (
            item.source.seat_number is None,
            item.source.seat_number or 0,
            item.source.participant_id,
        ),
    )
    for item in ordered:
        exits = sorted(
            (*item.exile_events, *item.death_events),
            key=lambda value: (value[1], value[0]),
        )
        result.append(
            ParticipantDerivedState(
                participant_id=item.source.participant_id,
                user_id=item.source.user_id,
                seat_number=item.source.seat_number,
                display_name_snapshot=item.source.display_name_snapshot,
                recorded_role_name=item.source.role_name,
                recorded_faction=item.source.faction,
                is_active_in_game=item.active,
                has_exile_record=bool(item.exile_events),
                has_death_record=bool(item.death_events),
                exile_event_ids=tuple(value[0] for value in item.exile_events),
                death_event_ids=tuple(value[0] for value in item.death_events),
                exit_event_ids=tuple(value[0] for value in exits),
                first_exit_logical_sequence=exits[0][1] if exits else None,
                latest_exit_logical_sequence=exits[-1][1] if exits else None,
            )
        )
    return tuple(result)


def _finalize_sheriff(state: _ProjectionState) -> SheriffDerivedState:
    def provenance(source: Mapping[int, list[int]]) -> tuple[ParticipantEventProvenance, ...]:
        return tuple(
            ParticipantEventProvenance(participant_id=participant_id, event_ids=tuple(event_ids))
            for participant_id, event_ids in sorted(source.items())
        )

    return SheriffDerivedState(
        badge_status=state.badge_status,
        current_sheriff_participant_id=state.sheriff_id,
        elected_event_id=state.elected_event_id,
        last_transfer_event_id=state.transfer_event_id,
        destroyed_event_id=state.destroyed_event_id,
        current_candidate_participant_ids=tuple(sorted(state.candidates)),
        withdrawn_participant_ids=tuple(sorted(state.withdrawn)),
        declaration_provenance=provenance(state.declarations),
        withdrawal_provenance=provenance(state.withdrawals),
    )


def _tally_entries(values: Mapping[int, Decimal]) -> tuple[TallyEntry, ...]:
    return tuple(
        TallyEntry(participant_id=participant_id, vote_weight=float(weight))
        for participant_id, weight in sorted(values.items())
    )


def _finalize_ballots(state: _ProjectionState) -> tuple[BallotDerivedState, ...]:
    result = []
    for key, ballot in sorted(state.ballots.items()):
        duplicate_voters = tuple(
            sorted(voter for voter, count in ballot.voter_counts.items() if count > 1)
        )
        if duplicate_voters:
            duplicate_event_ids = tuple(
                vote.event_id
                for vote in ballot.votes
                if vote.voter_participant_id in duplicate_voters
            )
            state.issue(
                "duplicate_vote_by_voter",
                event_ids=duplicate_event_ids,
                participant_ids=duplicate_voters,
                details={"vote_kind": key[0], "round_no": key[1], "ballot_no": key[2]},
            )
        if ballot.raw_tally and not duplicate_voters:
            maximum = max(ballot.raw_tally.values())
            highest = {
                participant_id
                for participant_id, weight in ballot.raw_tally.items()
                if weight == maximum
            }
            for tie in ballot.ties:
                if set(tie.candidate_participant_ids) != highest:
                    state.issue(
                        "explicit_tie_mismatch",
                        event_ids=(tie.event_id,),
                        participant_ids=(*tie.candidate_participant_ids, *highest),
                        details={"vote_kind": key[0], "round_no": key[1], "ballot_no": key[2]},
                    )
        explicit_outcome_ids = (*[item.event_id for item in ballot.ties], *ballot.outcomes)
        if len(explicit_outcome_ids) > 1:
            state.issue(
                "multiple_explicit_outcomes_for_ballot",
                event_ids=explicit_outcome_ids,
                details={"vote_kind": key[0], "round_no": key[1], "ballot_no": key[2]},
            )
        result.append(
            BallotDerivedState(
                vote_kind=ballot.vote_kind,
                round_no=ballot.round_no,
                ballot_no=ballot.ballot_no,
                vote_event_ids=tuple(item.event_id for item in ballot.votes),
                vote_records=tuple(ballot.votes),
                abstention_records=tuple(
                    item for item in ballot.votes if item.target_participant_id is None
                ),
                voter_participant_ids=tuple(
                    sorted(
                        item
                        for item in ballot.voter_counts
                        if item is not None
                    )
                ),
                duplicate_voter_participant_ids=duplicate_voters,
                raw_tally=_tally_entries(ballot.raw_tally),
                computed_tally=None if duplicate_voters else _tally_entries(ballot.raw_tally),
                tally_is_unambiguous=not duplicate_voters,
                explicit_tie_records=tuple(ballot.ties),
                revote_records=tuple(ballot.revotes),
                explicit_outcome_event_ids=tuple(ballot.outcomes),
            )
        )
    return tuple(result)


def _finalize_usage(state: _ProjectionState) -> tuple[ParticipantRecordedActionUsage, ...]:
    result = []
    for participant_id in sorted(state.participants):
        counts = state.usage[participant_id]
        result.append(
            ParticipantRecordedActionUsage(
                participant_id=participant_id,
                recorded_seer_check_count=counts["seer"],
                recorded_witch_antidote_count=counts["witch_antidote"],
                recorded_witch_poison_count=counts["witch_poison"],
                recorded_guard_protection_count=counts["guard"],
                recorded_hunter_shot_count=counts["hunter"],
                recorded_wolf_king_shot_count=counts["wolf_king"],
                recorded_wolf_self_explosion_count=counts["wolf_self_explosion"],
                recorded_sheriff_vote_count=counts["sheriff_vote"],
                recorded_exile_vote_count=counts["exile_vote"],
            )
        )
    return tuple(result)


def _finalize_actions(state: _ProjectionState) -> tuple[RecordedActionSummary, ...]:
    return tuple(
        RecordedActionSummary(
            event_type=key[0],
            phase=key[1],
            round_no=key[2],
            actor_participant_id=key[3],
            event_ids=tuple(value.event_ids),
            recorded_count=len(value.event_ids),
            latest_recorded_target_participant_id=value.latest_target,
        )
        for key, value in sorted(
            state.actions.items(),
            key=lambda item: (
                item[0][2],
                item[0][1],
                item[0][0],
                item[0][3] is None,
                item[0][3] or 0,
            ),
        )
    )


def _finalize_rounds(state: _ProjectionState) -> tuple[RoundSummary, ...]:
    return tuple(
        RoundSummary(
            round_no=key[0],
            phase=key[1],
            event_count=len(value.event_ids),
            event_ids=tuple(value.event_ids),
            phase_started_event_ids=tuple(value.phase_started_ids),
            phase_completed_event_ids=tuple(value.phase_completed_ids),
            night_resolved_event_ids=tuple(value.night_resolved_ids),
            event_type_counts=tuple(
                EventTypeCount(event_type=event_type, count=count)
                for event_type, count in sorted(value.type_counts.items())
            ),
        )
        for key, value in sorted(state.rounds.items())
    )


def _add_context_issues(
    state: _ProjectionState,
    participants: Sequence[ParticipantProjectionInput],
) -> None:
    context = state.context
    requires_snapshot = (
        context.play_status in {"in_progress", "ended"}
        or context.started_at is not None
        or context.result_status != "empty"
    )
    if context.format_snapshot_id is None and requires_snapshot:
        state.issue("missing_format_snapshot", severity="info")
    if (
        context.snapshot_player_count is not None
        and len(participants) != context.snapshot_player_count
    ):
        state.issue(
            "participant_count_snapshot_mismatch",
            participant_ids=tuple(item.participant_id for item in participants),
            details={
                "participant_count": len(participants),
                "snapshot_player_count": context.snapshot_player_count,
            },
        )
    role_inventory = set(context.snapshot_role_names)
    if context.format_snapshot_id is not None:
        for participant in participants:
            if participant.role_name and participant.role_name not in role_inventory:
                state.issue(
                    "recorded_role_not_in_snapshot",
                    participant_ids=(participant.participant_id,),
                    details={"recorded_role_name": participant.role_name},
                )


def project_game_state(
    *,
    context: GameProjectionContext,
    participants: Sequence[ParticipantProjectionInput],
    events: Sequence[GameEventProjectionInput],
    through_logical_sequence: int | None = None,
) -> GameDerivedState:
    """Project current recorded state without querying or mutating external data."""

    participant_states = {
        item.participant_id: _ParticipantState(source=item)
        for item in participants
    }
    state = _ProjectionState(context=context, participants=participant_states)
    _add_context_issues(state, participants)

    applicable = [
        event
        for event in events
        if through_logical_sequence is None
        or event.logical_sequence_no <= through_logical_sequence
    ]
    ordered = sorted(applicable, key=lambda event: (event.logical_sequence_no, event.id))
    if ordered and context.format_snapshot_id is None and not any(
        issue.code == "missing_format_snapshot" for issue in state.issues
    ):
        state.issue("missing_format_snapshot", severity="info")
    logical_groups: dict[int, list[int]] = defaultdict(list)
    for event in ordered:
        logical_groups[event.logical_sequence_no].append(event.id)
    for logical_sequence, event_ids in sorted(logical_groups.items()):
        if len(event_ids) > 1:
            state.issue(
                "duplicate_active_logical_sequence",
                event_ids=tuple(event_ids),
                details={"logical_sequence_no": logical_sequence},
            )

    for event in ordered:
        if event.game_id != context.game_id:
            state.issue(
                "event_game_mismatch",
                event_ids=(event.id,),
                event=event,
                details={"event_game_id": event.game_id, "expected_game_id": context.game_id},
            )
            continue
        _record_round(state, event)
        _record_common_event_issues(state, event)
        reducer = EVENT_REDUCERS.get(event.event_type)
        if reducer is None:
            state.issue(
                "unsupported_event_type",
                event_ids=(event.id,),
                event=event,
                details={"event_type": event.event_type},
            )
            continue
        state.last_observed_phase = event.phase
        state.last_observed_round = event.round_no
        state.last_observed_event_id = event.id
        reducer(state, event)
        state.last_applied_logical_sequence = event.logical_sequence_no

    ballots = _finalize_ballots(state)
    return GameDerivedState(
        projection_version=PROJECTOR_VERSION,
        projection_kind=PROJECTION_KIND,
        game_id=context.game_id,
        through_logical_sequence=through_logical_sequence,
        event_ledger_head_sequence=context.event_ledger_head_sequence,
        effective_event_count=len(ordered),
        last_applied_logical_sequence=state.last_applied_logical_sequence,
        has_format_snapshot=context.format_snapshot_id is not None,
        is_rule_engine_result=False,
        format_snapshot_id=context.format_snapshot_id,
        format_key=context.format_key,
        format_name=context.format_name,
        snapshot_schema_version=context.snapshot_schema_version,
        phase=PhaseDerivedState(
            current_phase=state.current_phase,
            current_round_no=state.current_round,
            phase_is_open=state.current_phase is not None,
            phase_started_event_id=state.phase_started_event_id,
            last_completed_phase=state.last_completed_phase,
            last_completed_round_no=state.last_completed_round,
            last_completed_event_id=state.last_completed_event_id,
            last_observed_phase=state.last_observed_phase,
            last_observed_round_no=state.last_observed_round,
            last_observed_event_id=state.last_observed_event_id,
        ),
        participants=_finalize_participants(state),
        sheriff=_finalize_sheriff(state),
        ballots=ballots,
        recorded_action_usage=_finalize_usage(state),
        recorded_actions=_finalize_actions(state),
        round_summaries=_finalize_rounds(state),
        night_resolutions=tuple(state.night_resolutions),
        issues=tuple(state.issues),
    )
