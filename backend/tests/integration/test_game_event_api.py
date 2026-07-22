"""API regressions for V1 event validation, lifecycle, and versioning."""

from copy import deepcopy

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import GameEventStatus
from app.models.audit_log import AuditLog
from app.models.game import Game
from app.models.game_event import GameEvent
from tests.integration.result_support import (
    API_PREFIX,
    create_additional_game,
    create_result_scenario,
)


pytestmark = pytest.mark.integration


def _prepare_draft(client: TestClient, scenario) -> tuple[dict, int, int]:
    response = client.put(
        f"{API_PREFIX}/games/{scenario.game_id}/result-draft",
        json=scenario.valid_draft(),
        headers=scenario.headers_for(scenario.judge_id),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    return body, body["players"][0]["participant_id"], body["players"][1]["participant_id"]


def _event_payload(
    event_type: str,
    *,
    phase: str = "day",
    actor: int | None = None,
    target: int | None = None,
    payload: dict | None = None,
    client_event_id: str | None = None,
) -> dict:
    return {
        "client_event_id": client_event_id,
        "phase": phase,
        "round_no": 1,
        "event_type": event_type,
        "actor_participant_id": actor,
        "target_participant_id": target,
        "secondary_target_participant_id": None,
        "payload": payload or {},
        "occurred_at": None,
    }


@pytest.mark.parametrize(
    ("event_type", "phase", "actor_policy", "target_policy", "payload", "visibility"),
    [
        ("phase_started", "night", False, False, {}, "public"),
        ("phase_completed", "day", False, False, {"note": "done"}, "public"),
        ("wolf_kill_selected", "night", False, True, {"selection_note": "final"}, "postgame_full"),
        ("seer_checked", "night", True, True, {"result_faction": "wolf"}, "postgame_full"),
        ("witch_saved", "night", True, True, {"potion": "antidote"}, "postgame_full"),
        ("witch_poisoned", "night", True, True, {"potion": "poison"}, "postgame_full"),
        ("guard_protected", "night", True, True, {}, "postgame_full"),
        ("night_resolved", "night", False, False, {"no_public_death": True}, "public"),
        ("sheriff_candidate_declared", "day", True, False, {}, "public"),
        ("sheriff_candidate_withdrew", "day", True, False, {}, "public"),
        ("sheriff_vote_cast", "day", True, True, {"ballot_no": 1}, "public"),
        ("sheriff_elected", "day", False, True, {"ballot_no": 1, "tally": {"seat-1": 2}}, "public"),
        ("exile_vote_cast", "day", True, False, {"ballot_no": 1, "vote_weight": 1.5}, "public"),
        ("vote_tied", "day", False, False, {"vote_kind": "exile", "ballot_no": 1, "candidate_participant_ids": "participants"}, "public"),
        ("exile_revote_started", "day", False, False, {"ballot_no": 2, "eligible_participant_ids": "participants"}, "public"),
        ("player_exiled", "day", False, True, {"ballot_no": 1}, "public"),
        ("hunter_shot", "night", True, True, {}, "public"),
        ("wolf_self_exploded", "day", True, False, {"note": "boom"}, "public"),
        ("wolf_king_shot", "day", True, True, {}, "public"),
        ("sheriff_badge_transferred", "day", True, True, {"reason": "last words"}, "public"),
        ("sheriff_badge_destroyed", "day", True, False, {}, "public"),
        ("player_died", "night", False, True, {"cause": "wolf_kill", "public_note": "died"}, "public"),
    ],
)
def test_each_v1_event_type_accepts_its_registered_shape(
    api_client: TestClient,
    db_session: Session,
    event_type: str,
    phase: str,
    actor_policy: bool,
    target_policy: bool,
    payload: dict,
    visibility: str,
) -> None:
    scenario = create_result_scenario(db_session)
    _, participant_one, participant_two = _prepare_draft(api_client, scenario)
    normalized_payload = deepcopy(payload)
    for key in ("candidate_participant_ids", "eligible_participant_ids"):
        if normalized_payload.get(key) == "participants":
            normalized_payload[key] = [participant_one, participant_two]
    response = api_client.post(
        f"{API_PREFIX}/games/{scenario.game_id}/events",
        json=_event_payload(
            event_type,
            phase=phase,
            actor=participant_one if actor_policy else None,
            target=participant_two if target_policy else None,
            payload=normalized_payload,
        ),
        headers=scenario.headers_for(scenario.judge_id),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["event_type"] == event_type
    assert body["visibility"] == visibility
    assert body["source"] == "manual"
    assert body["status"] == "active"
    assert body["schema_version"] == 1
    if event_type == "sheriff_vote_cast":
        assert body["payload"]["vote_weight"] == 1


@pytest.mark.parametrize(
    "mutator",
    [
        lambda body, _p1, _p2: body.update(event_type="unknown_event"),
        lambda body, _p1, _p2: body.update(phase="day"),
        lambda body, _p1, _p2: body.update(actor_participant_id=None),
        lambda body, _p1, _p2: body["payload"].update(extra_field=True),
        lambda body, _p1, _p2: body["payload"].pop("result_faction"),
        lambda body, _p1, _p2: body["payload"].update(result_faction="invalid"),
    ],
)
def test_registry_rejects_unknown_phase_reference_and_payload_shapes(
    api_client: TestClient,
    db_session: Session,
    mutator,
) -> None:
    scenario = create_result_scenario(db_session)
    _, participant_one, participant_two = _prepare_draft(api_client, scenario)
    payload = _event_payload(
        "seer_checked",
        phase="night",
        actor=participant_one,
        target=participant_two,
        payload={"result_faction": "wolf"},
    )
    mutator(payload, participant_one, participant_two)
    response = api_client.post(
        f"{API_PREFIX}/games/{scenario.game_id}/events",
        json=payload,
        headers=scenario.headers_for(scenario.judge_id),
    )
    assert response.status_code == 422


def test_permissions_and_hidden_event_read_scope(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session)
    _, _, participant_two = _prepare_draft(api_client, scenario)
    endpoint = f"{API_PREFIX}/games/{scenario.game_id}/events"
    payload = _event_payload("wolf_kill_selected", phase="night", target=participant_two)
    assert api_client.post(endpoint, json=payload).status_code == 401
    assert api_client.post(endpoint, json=payload, headers=scenario.headers_for(scenario.other_judge_id)).status_code == 403
    assert api_client.get(endpoint, headers=scenario.headers_for(scenario.viewer_id)).status_code == 403

    created = api_client.post(endpoint, json=payload, headers=scenario.headers_for(scenario.judge_id))
    assert created.status_code == 200
    assert api_client.get(endpoint, headers=scenario.headers_for(scenario.judge_id)).status_code == 200
    assert api_client.get(endpoint, headers=scenario.headers_for(scenario.admin_id)).status_code == 200
    event_id = created.json()["id"]
    assert api_client.get(f"{endpoint}/{event_id}", headers=scenario.headers_for(scenario.admin_id)).status_code == 200


def test_sequence_idempotency_correction_void_and_views(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session)
    _, participant_one, participant_two = _prepare_draft(api_client, scenario)
    endpoint = f"{API_PREFIX}/games/{scenario.game_id}/events"
    headers = scenario.headers_for(scenario.judge_id)
    first_payload = _event_payload(
        "sheriff_candidate_declared",
        actor=participant_one,
        client_event_id="candidate-1",
    )
    first = api_client.post(endpoint, json=first_payload, headers=headers)
    retry = api_client.post(endpoint, json=first_payload, headers=headers)
    assert first.status_code == retry.status_code == 200
    assert retry.json()["id"] == first.json()["id"]
    assert retry.json()["sequence_no"] == 1

    conflict_payload = deepcopy(first_payload)
    conflict_payload["round_no"] = 2
    assert api_client.post(endpoint, json=conflict_payload, headers=headers).status_code == 409
    second = api_client.post(
        endpoint,
        json=_event_payload("sheriff_candidate_declared", actor=participant_two),
        headers=headers,
    )
    assert second.json()["sequence_no"] == 2

    correction_payload = _event_payload(
        "sheriff_candidate_withdrew",
        actor=participant_one,
        client_event_id="candidate-correction-1",
    )
    correction_payload["reason"] = "Candidate withdrew"
    corrected = api_client.post(
        f"{endpoint}/{first.json()['id']}/correct",
        json=correction_payload,
        headers=headers,
    )
    assert corrected.status_code == 200, corrected.text
    assert corrected.json()["sequence_no"] == 3
    assert corrected.json()["logical_sequence_no"] == 1
    assert corrected.json()["supersedes_event_id"] == first.json()["id"]
    correction_retry = api_client.post(
        f"{endpoint}/{first.json()['id']}/correct",
        json=correction_payload,
        headers=headers,
    )
    assert correction_retry.status_code == 200
    assert correction_retry.json()["id"] == corrected.json()["id"]

    voided = api_client.post(
        f"{endpoint}/{second.json()['id']}/void",
        json={"reason": "Not actually declared"},
        headers=headers,
    )
    assert voided.status_code == 200
    assert voided.json()["status"] == "voided"
    assert api_client.post(
        f"{endpoint}/{second.json()['id']}/void",
        json={"reason": "again"},
        headers=headers,
    ).status_code == 409

    effective = api_client.get(endpoint, headers=headers).json()
    assert [(item["logical_sequence_no"], item["id"]) for item in effective] == [(1, corrected.json()["id"])]
    ledger = api_client.get(f"{endpoint}?view=ledger", headers=headers).json()
    assert [item["sequence_no"] for item in ledger] == [1, 2, 3]
    assert [item["status"] for item in ledger] == ["superseded", "voided", "active"]
    assert api_client.get(f"{endpoint}?view=ledger&after_ledger_sequence=1", headers=headers).status_code == 200
    assert api_client.get(f"{endpoint}?view=effective&after_ledger_sequence=1", headers=headers).status_code == 422

    db_session.expire_all()
    game = db_session.get(Game, scenario.game_id)
    assert game.next_event_sequence == 4
    assert db_session.scalar(
        select(func.count(AuditLog.id)).where(AuditLog.entity_type == "game_event")
    ) == 2


def test_event_references_freeze_participant_identity_but_not_unreferenced_rows(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session)
    draft, participant_one, participant_two = _prepare_draft(api_client, scenario)
    endpoint = f"{API_PREFIX}/games/{scenario.game_id}/events"
    headers = scenario.headers_for(scenario.judge_id)
    created = api_client.post(
        endpoint,
        json=_event_payload("wolf_kill_selected", phase="night", target=participant_one),
        headers=headers,
    )
    assert created.status_code == 200

    changed = scenario.valid_draft()
    for request_row, saved_row in zip(changed["players"], draft["players"], strict=True):
        request_row["participant_id"] = saved_row["participant_id"]
    changed["players"][0]["seat_number"] = 3
    changed["adjustments"] = []
    assert api_client.put(
        f"{API_PREFIX}/games/{scenario.game_id}/result-draft",
        json=changed,
        headers=headers,
    ).status_code == 409

    removed = deepcopy(changed)
    removed["players"] = [removed["players"][1]]
    removed["players"][0]["seat_number"] = 2
    assert api_client.put(
        f"{API_PREFIX}/games/{scenario.game_id}/result-draft",
        json=removed,
        headers=headers,
    ).status_code == 409

    allowed = scenario.valid_draft()
    for request_row, saved_row in zip(allowed["players"], draft["players"], strict=True):
        request_row["participant_id"] = saved_row["participant_id"]
    allowed["players"][1]["user_id"] = scenario.replacement_player_id
    response = api_client.put(
        f"{API_PREFIX}/games/{scenario.game_id}/result-draft",
        json=allowed,
        headers=headers,
    )
    assert response.status_code == 200, response.text
    assert next(item for item in response.json()["players"] if item["participant_id"] == participant_two)["user_id"] == scenario.replacement_player_id


def test_submitted_confirmed_and_cancelled_ledgers_are_locked(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session)
    _, _, participant_two = _prepare_draft(api_client, scenario)
    endpoint = f"{API_PREFIX}/games/{scenario.game_id}/events"
    payload = _event_payload("wolf_kill_selected", phase="night", target=participant_two)
    headers = scenario.headers_for(scenario.judge_id)
    assert api_client.post(endpoint, json=payload, headers=headers).status_code == 200
    assert api_client.post(f"{API_PREFIX}/games/{scenario.game_id}/submit-result", headers=headers).status_code == 200
    assert api_client.post(endpoint, json=payload, headers=headers).status_code == 409

    rejected = api_client.post(
        f"{API_PREFIX}/games/{scenario.game_id}/reject-result",
        json={"comment": "Needs event correction"},
        headers=scenario.headers_for(scenario.admin_id),
    )
    assert rejected.status_code == 200
    assert api_client.post(endpoint, json={**payload, "client_event_id": "after-reject"}, headers=headers).status_code == 200


def test_scheduled_game_cannot_append_and_cancelled_game_stays_locked(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session)
    endpoint = f"{API_PREFIX}/games/{scenario.game_id}/events"
    payload = _event_payload("phase_started", phase="night")
    headers = scenario.headers_for(scenario.judge_id)
    assert api_client.post(endpoint, json=payload, headers=headers).status_code == 409
    cancelled = api_client.post(
        f"{API_PREFIX}/games/{scenario.game_id}/cancel",
        json={"reason": "No table"},
        headers=scenario.headers_for(scenario.admin_id),
    )
    assert cancelled.status_code == 200
    assert api_client.post(endpoint, json=payload, headers=headers).status_code == 409


def test_cross_game_and_duplicate_payload_references_are_rejected(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session)
    _, participant_one, participant_two = _prepare_draft(api_client, scenario)
    other_game_id = create_additional_game(db_session, scenario)
    other_saved = api_client.put(
        f"{API_PREFIX}/games/{other_game_id}/result-draft",
        json=scenario.valid_draft(),
        headers=scenario.headers_for(scenario.judge_id),
    )
    assert other_saved.status_code == 200
    other_participant = other_saved.json()["players"][0]["participant_id"]
    other_event = api_client.post(
        f"{API_PREFIX}/games/{other_game_id}/events",
        json=_event_payload("phase_started", phase="night"),
        headers=scenario.headers_for(scenario.judge_id),
    )
    assert other_event.status_code == 200

    endpoint = f"{API_PREFIX}/games/{scenario.game_id}/events"
    headers = scenario.headers_for(scenario.judge_id)
    invalid_payloads = [
        _event_payload("wolf_kill_selected", phase="night", target=other_participant),
        _event_payload(
            "vote_tied",
            payload={
                "vote_kind": "exile",
                "ballot_no": 1,
                "candidate_participant_ids": [participant_one, other_participant],
            },
        ),
        _event_payload(
            "vote_tied",
            payload={
                "vote_kind": "exile",
                "ballot_no": 1,
                "candidate_participant_ids": [participant_one, participant_one],
            },
        ),
        _event_payload(
            "hunter_shot",
            actor=participant_one,
            target=participant_two,
            payload={"trigger_event_id": other_event.json()["id"]},
        ),
        _event_payload(
            "player_died",
            phase="night",
            target=participant_two,
            payload={"cause": "not-a-cause"},
        ),
        _event_payload(
            "player_died",
            phase="night",
            target=participant_two,
            payload={
                "cause": "other",
                "source_event_ids": [other_event.json()["id"]],
            },
        ),
        _event_payload(
            "player_died",
            phase="night",
            target=participant_two,
            payload={
                "cause": "other",
                "source_event_ids": [other_event.json()["id"], other_event.json()["id"]],
            },
        ),
    ]
    for payload in invalid_payloads:
        assert api_client.post(endpoint, json=payload, headers=headers).status_code == 422


def test_ended_draft_allows_events_but_confirmed_and_revised_lock_ledger(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session)
    _prepare_draft(api_client, scenario)
    judge_headers = scenario.headers_for(scenario.judge_id)
    admin_headers = scenario.headers_for(scenario.admin_id)
    endpoint = f"{API_PREFIX}/games/{scenario.game_id}/events"
    ended = api_client.post(
        f"{API_PREFIX}/games/{scenario.game_id}/end",
        headers=judge_headers,
    )
    assert ended.status_code == 200
    assert api_client.post(
        endpoint,
        json=_event_payload("phase_completed", payload={"note": "postgame entry"}),
        headers=judge_headers,
    ).status_code == 200

    assert api_client.post(
        f"{API_PREFIX}/games/{scenario.game_id}/submit-result",
        headers=judge_headers,
    ).status_code == 200
    assert api_client.post(
        f"{API_PREFIX}/games/{scenario.game_id}/confirm-result",
        json={"comment": "confirmed"},
        headers=admin_headers,
    ).status_code == 200
    assert api_client.post(
        endpoint,
        json=_event_payload("phase_completed"),
        headers=admin_headers,
    ).status_code == 409

    revised = api_client.post(
        f"{API_PREFIX}/games/{scenario.game_id}/revise-result",
        json={**scenario.valid_draft(), "reason": "score correction"},
        headers=admin_headers,
    )
    assert revised.status_code == 200, revised.text
    assert api_client.post(
        endpoint,
        json=_event_payload("phase_completed"),
        headers=admin_headers,
    ).status_code == 409
