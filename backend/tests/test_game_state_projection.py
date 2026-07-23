"""Pure unit coverage for deterministic effective-event projection."""

from copy import deepcopy

import pytest

from app.core.enums import GameEventType
from app.services.game_state_projection import EVENT_REDUCERS, project_game_state
from tests.projection_support import (
    golden_scenario_events,
    projection_context,
    projection_event,
    projection_participants,
    valid_event_for_type,
)


def _project(events=(), *, context=None, participants=None, through=None):
    return project_game_state(
        context=context or projection_context(),
        participants=participants or projection_participants(),
        events=events,
        through_logical_sequence=through,
    )


def _codes(state) -> set[str]:
    return {issue.code for issue in state.issues}


def _participant(state, participant_id: int):
    return next(item for item in state.participants if item.participant_id == participant_id)


def _ballot(state, vote_kind: str, ballot_no: int):
    return next(
        item
        for item in state.ballots
        if item.vote_kind == vote_kind and item.ballot_no == ballot_no
    )


def test_empty_projection_is_initial_recorded_state() -> None:
    context = projection_context(
        play_status="scheduled",
        result_status="empty",
        snapshot=False,
        ledger_head=0,
    )

    state = _project(context=context)

    assert state.projection_version == 1
    assert state.projection_kind == "effective_event_projection"
    assert state.effective_event_count == 0
    assert state.last_applied_logical_sequence is None
    assert state.phase.current_phase is None
    assert state.phase.phase_is_open is False
    assert all(item.is_active_in_game for item in state.participants)
    assert state.sheriff.badge_status == "unassigned"
    assert state.ballots == ()
    assert state.issues == ()
    assert all(
        item.recorded_seer_check_count == 0
        and item.recorded_exile_vote_count == 0
        for item in state.recorded_action_usage
    )


def test_projection_is_order_independent_deterministic_and_does_not_mutate_inputs() -> None:
    participants = list(projection_participants())
    events = [
        projection_event(2, "player_died", target=7, payload={"cause": "other"}),
        projection_event(1, "phase_started", phase="night"),
    ]
    original_participants = deepcopy(participants)
    original_events = deepcopy(events)

    first = _project(events, participants=participants)
    second = _project(list(reversed(events)), participants=participants)

    assert first == second
    assert participants == original_participants
    assert events == original_events


def test_projection_supports_current_effective_timeline_prefix() -> None:
    events = (
        projection_event(1, "phase_started", phase="night"),
        projection_event(2, "player_died", phase="night", target=7, payload={"cause": "other"}),
        projection_event(3, "phase_completed", phase="night"),
    )

    state = _project(events, through=2)

    assert state.through_logical_sequence == 2
    assert state.effective_event_count == 2
    assert state.last_applied_logical_sequence == 2
    assert state.phase.phase_is_open is True
    assert _participant(state, 7).is_active_in_game is False


def test_structural_anomalies_are_issues_instead_of_failures() -> None:
    events = (
        projection_event(1, "future_event_type"),
        projection_event(2, "phase_started", logical_sequence_no=2),
        projection_event(3, "phase_completed", logical_sequence_no=2),
        projection_event(4, "phase_started", game_id=99),
        projection_event(5, "seer_checked", actor=999, target=998),
    )

    state = _project(events)

    assert {
        "unsupported_event_type",
        "duplicate_active_logical_sequence",
        "event_game_mismatch",
        "unknown_participant_reference",
    } <= _codes(state)
    assert state.last_applied_logical_sequence == 5


@pytest.mark.parametrize("event_type", [item.value for item in GameEventType])
def test_every_v1_event_type_has_an_explicit_handler(event_type: str) -> None:
    assert set(EVENT_REDUCERS) == {item.value for item in GameEventType}

    state = _project((valid_event_for_type(event_type),))

    assert "unsupported_event_type" not in _codes(state)


def test_phase_changes_only_on_explicit_phase_events() -> None:
    ordinary = _project(
        (projection_event(1, "wolf_kill_selected", phase="night", target=7),)
    )
    assert ordinary.phase.current_phase is None
    assert ordinary.phase.last_observed_phase == "night"

    normal = _project(
        (
            projection_event(1, "phase_started", phase="night"),
            projection_event(2, "phase_completed", phase="night"),
        )
    )
    assert normal.phase.phase_is_open is False
    assert normal.phase.last_completed_phase == "night"

    inconsistent = _project(
        (
            projection_event(1, "phase_completed", phase="night"),
            projection_event(2, "phase_started", phase="night"),
            projection_event(3, "phase_started", phase="day"),
            projection_event(4, "phase_completed", phase="night"),
        )
    )
    assert {
        "phase_completed_without_open_phase",
        "phase_started_while_another_phase_open",
        "phase_completed_mismatch",
    } <= _codes(inconsistent)
    assert inconsistent.phase.current_phase == "day"


def test_only_explicit_exit_events_mark_participants_inactive() -> None:
    actions_only = _project(
        (
            projection_event(1, "hunter_shot", actor=5, target=6),
            projection_event(2, "witch_poisoned", phase="night", actor=2, target=7),
            projection_event(3, "wolf_self_exploded", actor=3),
            projection_event(4, "wolf_king_shot", actor=3, target=8),
        )
    )
    assert all(_participant(actions_only, item).is_active_in_game for item in (3, 6, 7, 8))

    state = _project(
        (
            projection_event(1, "player_exiled", target=9, payload={"ballot_no": 1}),
            projection_event(2, "player_died", target=9, payload={"cause": "other"}),
            projection_event(3, "player_died", target=9, payload={"cause": "other"}),
            projection_event(4, "seer_checked", actor=9, target=8),
            projection_event(5, "guard_protected", phase="night", actor=4, target=9),
        )
    )
    player = _participant(state, 9)
    assert player.is_active_in_game is False
    assert player.exile_event_ids == (1,)
    assert player.death_event_ids == (2, 3)
    assert player.first_exit_logical_sequence == 1
    assert player.latest_exit_logical_sequence == 3
    assert {
        "duplicate_death_record",
        "multiple_exit_records",
        "event_actor_already_out",
        "event_target_already_out",
    } <= _codes(state)


def test_sheriff_projection_preserves_explicit_records_and_reports_conflicts() -> None:
    state = _project(
        (
            projection_event(1, "sheriff_candidate_withdrew", actor=3),
            projection_event(2, "sheriff_candidate_declared", actor=4),
            projection_event(3, "sheriff_elected", target=4, payload={"ballot_no": 1}),
            projection_event(4, "sheriff_elected", target=5, payload={"ballot_no": 1}),
            projection_event(5, "sheriff_badge_transferred", actor=4, target=6),
            projection_event(6, "sheriff_badge_destroyed", actor=6),
            projection_event(7, "sheriff_badge_transferred", actor=6, target=7),
        )
    )

    assert state.sheriff.badge_status == "held"
    assert state.sheriff.current_sheriff_participant_id == 7
    assert state.sheriff.elected_event_id == 4
    assert state.sheriff.last_transfer_event_id == 7
    assert {
        "candidate_withdrew_without_declaration",
        "sheriff_elected_while_badge_held",
        "badge_transfer_actor_mismatch",
        "badge_transfer_without_current_sheriff",
        "badge_reassigned_after_destroyed",
    } <= _codes(state)


def test_ballots_compute_unambiguous_tallies_without_inferring_outcomes() -> None:
    state = _project(
        (
            projection_event(
                1,
                "sheriff_vote_cast",
                actor=1,
                target=4,
                payload={"ballot_no": 1, "vote_weight": 1.5},
            ),
            projection_event(
                2,
                "sheriff_vote_cast",
                actor=2,
                target=4,
                payload={"ballot_no": 1, "vote_weight": 1},
            ),
            projection_event(
                3,
                "sheriff_vote_cast",
                actor=3,
                target=None,
                payload={"ballot_no": 1, "vote_weight": 1},
            ),
            projection_event(
                4,
                "exile_vote_cast",
                actor=1,
                target=8,
                payload={"ballot_no": 1, "vote_weight": 1},
            ),
            projection_event(
                5,
                "exile_vote_cast",
                actor=1,
                target=9,
                payload={"ballot_no": 1, "vote_weight": 1},
            ),
            projection_event(
                6,
                "vote_tied",
                payload={
                    "vote_kind": "sheriff",
                    "ballot_no": 1,
                    "candidate_participant_ids": [4, 5],
                },
            ),
            projection_event(
                7,
                "exile_revote_started",
                payload={"ballot_no": 2, "eligible_participant_ids": [8, 9]},
            ),
        )
    )

    sheriff = _ballot(state, "sheriff", 1)
    assert sheriff.tally_is_unambiguous is True
    assert [(item.participant_id, item.vote_weight) for item in sheriff.computed_tally or ()] == [
        (4, 2.5)
    ]
    assert len(sheriff.abstention_records) == 1
    assert sheriff.explicit_outcome_event_ids == ()
    assert state.sheriff.current_sheriff_participant_id is None

    exile = _ballot(state, "exile", 1)
    assert exile.tally_is_unambiguous is False
    assert exile.computed_tally is None
    assert exile.duplicate_voter_participant_ids == (1,)
    assert _participant(state, 8).is_active_in_game is True
    assert _participant(state, 9).is_active_in_game is True
    assert _ballot(state, "exile", 2).revote_records[0].eligible_participant_ids == (8, 9)
    assert {"duplicate_vote_by_voter", "explicit_tie_mismatch"} <= _codes(state)


def test_recorded_action_usage_and_night_resolution_are_non_rule_summaries() -> None:
    events = (
        projection_event(1, "seer_checked", phase="night", actor=1, target=3),
        projection_event(2, "seer_checked", phase="night", actor=1, target=4),
        projection_event(3, "witch_saved", phase="night", actor=2, target=7),
        projection_event(4, "witch_poisoned", phase="night", actor=2, target=8),
        projection_event(5, "guard_protected", phase="night", actor=4, target=7),
        projection_event(6, "hunter_shot", actor=5, target=6),
        projection_event(7, "wolf_king_shot", actor=3, target=6),
        projection_event(8, "wolf_self_exploded", actor=3),
        projection_event(
            9,
            "sheriff_vote_cast",
            actor=1,
            target=4,
            payload={"ballot_no": 1, "vote_weight": 1},
        ),
        projection_event(
            10,
            "exile_vote_cast",
            actor=1,
            target=9,
            payload={"ballot_no": 1, "vote_weight": 1},
        ),
        projection_event(11, "night_resolved", phase="night", payload={"no_public_death": True}),
        projection_event(12, "night_resolved", phase="night", payload={"no_public_death": False}),
    )

    state = _project(events)
    usage_one = next(item for item in state.recorded_action_usage if item.participant_id == 1)
    usage_two = next(item for item in state.recorded_action_usage if item.participant_id == 2)
    assert usage_one.recorded_seer_check_count == 2
    assert usage_one.recorded_sheriff_vote_count == 1
    assert usage_one.recorded_exile_vote_count == 1
    assert usage_two.recorded_witch_antidote_count == 1
    assert usage_two.recorded_witch_poison_count == 1
    seer_summary = next(
        item
        for item in state.recorded_actions
        if item.event_type == "seer_checked" and item.actor_participant_id == 1
    )
    assert seer_summary.recorded_count == 2
    assert seer_summary.latest_recorded_target_participant_id == 4
    assert len(state.night_resolutions) == 2
    assert "multiple_night_resolved_events" in _codes(state)
    assert _participant(state, 6).is_active_in_game is True


def test_snapshot_and_recorded_result_consistency_are_only_reported() -> None:
    participants = (
        projection_participants(1)[0],
        projection_participants(2)[1],
    )
    participants = (
        participants[0],
        type(participants[1])(
            participant_id=2,
            user_id=102,
            seat_number=2,
            display_name_snapshot="Player 2",
            role_name="Future Role",
            faction=None,
        ),
    )
    state = _project(
        context=projection_context(player_count=3, role_names=("Seer",)),
        participants=participants,
    )

    assert {
        "participant_count_snapshot_mismatch",
        "recorded_role_not_in_snapshot",
    } <= _codes(state)
    assert _participant(state, 2).recorded_faction is None


def test_golden_scenario_projects_only_explicit_recorded_facts() -> None:
    state = _project(golden_scenario_events())

    assert state.phase.current_phase == "night"
    assert state.phase.current_round_no == 2
    assert _participant(state, 9).is_active_in_game is False
    assert _participant(state, 7).is_active_in_game is True
    assert state.sheriff.current_sheriff_participant_id == 4
    sheriff_ballot = _ballot(state, "sheriff", 1)
    assert [(item.participant_id, item.vote_weight) for item in sheriff_ballot.raw_tally] == [
        (4, 3.0),
        (5, 1.0),
    ]
    exile_ballot = _ballot(state, "exile", 1)
    assert exile_ballot.explicit_outcome_event_ids == (18,)
    usage = {item.participant_id: item for item in state.recorded_action_usage}
    assert usage[1].recorded_seer_check_count == 1
    assert usage[2].recorded_witch_antidote_count == 1
    assert next(
        item for item in state.round_summaries if item.round_no == 1 and item.phase == "day"
    ).event_count == 14
    assert state.is_rule_engine_result is False


def test_golden_scenario_uses_corrected_and_voided_active_timeline() -> None:
    current_active_events = tuple(
        event
        for event in golden_scenario_events()
        if event.id not in {4, 10}
    ) + (
        projection_event(
            21,
            "sheriff_vote_cast",
            logical_sequence_no=10,
            sequence_no=21,
            actor=1,
            target=5,
            payload={"ballot_no": 1, "vote_weight": 1},
        ),
    )

    state = _project(current_active_events)

    sheriff_ballot = _ballot(state, "sheriff", 1)
    assert sheriff_ballot.vote_event_ids == (21, 11, 12, 13)
    assert [(item.participant_id, item.vote_weight) for item in sheriff_ballot.raw_tally] == [
        (4, 2.0),
        (5, 2.0),
    ]
    usage = {item.participant_id: item for item in state.recorded_action_usage}
    assert usage[2].recorded_witch_antidote_count == 0
    assert all(item.event_type != "witch_saved" for item in state.recorded_actions)
    assert state.effective_event_count == 19


def test_reasonable_500_event_projection_remains_linear_in_shape() -> None:
    events = tuple(
        projection_event(
            index,
            "wolf_kill_selected",
            phase="night",
            round_no=((index - 1) // 20) + 1,
            target=((index - 1) % 12) + 1,
        )
        for index in range(1, 501)
    )

    state = _project(events)

    assert state.effective_event_count == 500
    assert sum(item.event_count for item in state.round_summaries) == 500
    assert sum(item.recorded_count for item in state.recorded_actions) == 500
