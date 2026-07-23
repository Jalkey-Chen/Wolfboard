"""Readable fixtures for deterministic game-state projection tests."""

from datetime import datetime, timezone
from typing import Any

from app.services.game_state_projection import (
    GameEventProjectionInput,
    GameProjectionContext,
    ParticipantProjectionInput,
)


def projection_context(
    *,
    game_id: int = 1,
    play_status: str = "in_progress",
    result_status: str = "draft",
    snapshot: bool = True,
    player_count: int = 12,
    role_names: tuple[str, ...] = ("Seer", "Witch", "Werewolf", "Villager"),
    ledger_head: int = 100,
) -> GameProjectionContext:
    started_at = datetime(2026, 7, 22, 18, 0, tzinfo=timezone.utc)
    return GameProjectionContext(
        game_id=game_id,
        play_status=play_status,
        result_status=result_status,
        format_snapshot_id=10 if snapshot else None,
        format_key="projection-test" if snapshot else None,
        format_name="Projection Test" if snapshot else None,
        snapshot_schema_version=1 if snapshot else None,
        snapshot_player_count=player_count if snapshot else None,
        snapshot_role_names=role_names if snapshot else (),
        event_ledger_head_sequence=ledger_head,
        started_at=started_at if play_status != "scheduled" else None,
        ended_at=started_at if play_status == "ended" else None,
    )


def projection_participants(count: int = 12) -> tuple[ParticipantProjectionInput, ...]:
    roles = ("Seer", "Witch", "Werewolf", "Villager")
    factions = ("good", "good", "wolf", "good")
    return tuple(
        ParticipantProjectionInput(
            participant_id=index,
            user_id=100 + index,
            seat_number=index,
            display_name_snapshot=f"Player {index}",
            role_name=roles[(index - 1) % len(roles)],
            faction=factions[(index - 1) % len(factions)],
        )
        for index in range(1, count + 1)
    )


def projection_event(
    event_id: int,
    event_type: str,
    *,
    game_id: int = 1,
    logical_sequence_no: int | None = None,
    sequence_no: int | None = None,
    phase: str = "day",
    round_no: int = 1,
    actor: int | None = None,
    target: int | None = None,
    secondary_target: int | None = None,
    payload: dict[str, Any] | None = None,
) -> GameEventProjectionInput:
    return GameEventProjectionInput(
        id=event_id,
        game_id=game_id,
        logical_sequence_no=logical_sequence_no or event_id,
        sequence_no=sequence_no or event_id,
        phase=phase,
        round_no=round_no,
        event_type=event_type,
        actor_participant_id=actor,
        target_participant_id=target,
        secondary_target_participant_id=secondary_target,
        payload=payload or {},
        visibility="public",
        source="manual",
        schema_version=1,
    )


def valid_event_for_type(event_type: str, event_id: int = 1) -> GameEventProjectionInput:
    values: dict[str, dict[str, Any]] = {
        "phase_started": {"phase": "night"},
        "phase_completed": {"phase": "night", "payload": {"note": "done"}},
        "wolf_kill_selected": {"phase": "night", "target": 7},
        "seer_checked": {
            "phase": "night",
            "actor": 1,
            "target": 3,
            "payload": {"result_faction": "wolf"},
        },
        "witch_saved": {
            "phase": "night",
            "actor": 2,
            "target": 7,
            "payload": {"potion": "antidote"},
        },
        "witch_poisoned": {
            "phase": "night",
            "actor": 2,
            "target": 8,
            "payload": {"potion": "poison"},
        },
        "guard_protected": {"phase": "night", "actor": 4, "target": 7},
        "night_resolved": {
            "phase": "night",
            "payload": {"no_public_death": True, "note": "peaceful"},
        },
        "sheriff_candidate_declared": {"actor": 3},
        "sheriff_candidate_withdrew": {"actor": 3},
        "sheriff_vote_cast": {
            "actor": 1,
            "target": 4,
            "payload": {"ballot_no": 1, "vote_weight": 1},
        },
        "sheriff_elected": {
            "target": 4,
            "payload": {"ballot_no": 1, "tally": {"4": 3}},
        },
        "exile_vote_cast": {
            "actor": 1,
            "target": 9,
            "payload": {"ballot_no": 1, "vote_weight": 1},
        },
        "vote_tied": {
            "payload": {
                "vote_kind": "exile",
                "ballot_no": 1,
                "candidate_participant_ids": [8, 9],
            }
        },
        "exile_revote_started": {
            "payload": {"ballot_no": 2, "eligible_participant_ids": [8, 9]}
        },
        "player_exiled": {"target": 9, "payload": {"ballot_no": 1}},
        "hunter_shot": {"actor": 5, "target": 6, "payload": {}},
        "wolf_self_exploded": {"actor": 3, "payload": {"note": "boom"}},
        "wolf_king_shot": {"actor": 3, "target": 6, "payload": {}},
        "sheriff_badge_transferred": {
            "actor": 4,
            "target": 5,
            "payload": {"reason": "last words"},
        },
        "sheriff_badge_destroyed": {"actor": 4, "payload": {"reason": "destroyed"}},
        "player_died": {
            "target": 7,
            "payload": {"cause": "wolf_kill", "source_event_ids": []},
        },
    }
    return projection_event(event_id, event_type, **values[event_type])


def golden_scenario_events() -> tuple[GameEventProjectionInput, ...]:
    """One readable recorded game prefix without rule-engine assumptions."""

    return (
        projection_event(1, "phase_started", phase="night"),
        projection_event(2, "wolf_kill_selected", phase="night", target=7),
        projection_event(
            3,
            "seer_checked",
            phase="night",
            actor=1,
            target=3,
            payload={"result_faction": "wolf"},
        ),
        projection_event(
            4,
            "witch_saved",
            phase="night",
            actor=2,
            target=7,
            payload={"potion": "antidote"},
        ),
        projection_event(5, "phase_completed", phase="night", payload={"note": "done"}),
        projection_event(6, "phase_started", phase="day"),
        projection_event(7, "sheriff_candidate_declared", actor=3),
        projection_event(8, "sheriff_candidate_declared", actor=4),
        projection_event(9, "sheriff_candidate_declared", actor=5),
        projection_event(
            10,
            "sheriff_vote_cast",
            actor=1,
            target=4,
            payload={"ballot_no": 1, "vote_weight": 1},
        ),
        projection_event(
            11,
            "sheriff_vote_cast",
            actor=2,
            target=4,
            payload={"ballot_no": 1, "vote_weight": 1},
        ),
        projection_event(
            12,
            "sheriff_vote_cast",
            actor=3,
            target=5,
            payload={"ballot_no": 1, "vote_weight": 1},
        ),
        projection_event(
            13,
            "sheriff_vote_cast",
            actor=5,
            target=4,
            payload={"ballot_no": 1, "vote_weight": 1},
        ),
        projection_event(14, "sheriff_elected", target=4, payload={"ballot_no": 1}),
        projection_event(
            15,
            "exile_vote_cast",
            actor=1,
            target=9,
            payload={"ballot_no": 1, "vote_weight": 1},
        ),
        projection_event(
            16,
            "exile_vote_cast",
            actor=2,
            target=9,
            payload={"ballot_no": 1, "vote_weight": 1},
        ),
        projection_event(
            17,
            "exile_vote_cast",
            actor=4,
            target=9,
            payload={"ballot_no": 1, "vote_weight": 1},
        ),
        projection_event(18, "player_exiled", target=9, payload={"ballot_no": 1}),
        projection_event(19, "phase_completed", phase="day", payload={"note": "done"}),
        projection_event(20, "phase_started", phase="night", round_no=2),
    )
