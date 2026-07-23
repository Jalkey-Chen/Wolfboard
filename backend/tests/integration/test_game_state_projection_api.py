"""PostgreSQL/API coverage for the read-only derived-state boundary."""

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import event, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.enums import (
    GameEventPhase,
    GameEventSource,
    GameEventStatus,
    GameEventVisibility,
)
from app.models.game import Game
from app.models.game_event import GameEvent
from app.models.user import User
from app.services.game_state_service import get_game_derived_state
from tests.integration.result_support import (
    API_PREFIX,
    create_result_scenario,
)


pytestmark = pytest.mark.integration


def _prepare_draft(client: TestClient, scenario) -> tuple[int, int]:
    response = client.put(
        f"{API_PREFIX}/games/{scenario.game_id}/result-draft",
        json=scenario.valid_draft(),
        headers=scenario.headers_for(scenario.judge_id),
    )
    assert response.status_code == 200, response.text
    players = response.json()["players"]
    return players[0]["participant_id"], players[1]["participant_id"]


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


def test_derived_state_permissions_and_empty_scheduled_game(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session)
    endpoint = f"{API_PREFIX}/games/{scenario.game_id}/derived-state"

    assert api_client.get(endpoint).status_code == 401
    assert api_client.get(
        endpoint,
        headers=scenario.headers_for(scenario.viewer_id),
    ).status_code == 403
    assert api_client.get(
        endpoint,
        headers=scenario.headers_for(scenario.other_judge_id),
    ).status_code == 403

    judge = api_client.get(endpoint, headers=scenario.headers_for(scenario.judge_id))
    admin = api_client.get(endpoint, headers=scenario.headers_for(scenario.admin_id))
    assert judge.status_code == admin.status_code == 200
    body = judge.json()
    assert body["projection_version"] == 1
    assert body["projection_kind"] == "effective_event_projection"
    assert body["is_rule_engine_result"] is False
    assert body["has_format_snapshot"] is False
    assert body["effective_event_count"] == 0
    assert body["phase"]["current_phase"] is None
    assert body["issues"] == []
    assert api_client.get(
        f"{endpoint}?through_logical_sequence=0",
        headers=scenario.headers_for(scenario.admin_id),
    ).status_code == 422


def test_derived_state_uses_only_active_versions_and_supports_current_prefix(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session)
    participant_one, participant_two = _prepare_draft(api_client, scenario)
    event_endpoint = f"{API_PREFIX}/games/{scenario.game_id}/events"
    derived_endpoint = f"{API_PREFIX}/games/{scenario.game_id}/derived-state"
    headers = scenario.headers_for(scenario.judge_id)

    started = api_client.post(
        event_endpoint,
        json=_event_payload("phase_started", phase="day"),
        headers=headers,
    )
    vote = api_client.post(
        event_endpoint,
        json=_event_payload(
            "sheriff_vote_cast",
            actor=participant_one,
            target=participant_two,
            payload={"ballot_no": 1, "vote_weight": 1},
        ),
        headers=headers,
    )
    action = api_client.post(
        event_endpoint,
        json=_event_payload(
            "seer_checked",
            phase="night",
            actor=participant_one,
            target=participant_two,
            payload={"result_faction": "wolf"},
        ),
        headers=headers,
    )
    assert started.status_code == vote.status_code == action.status_code == 200

    correction = _event_payload(
        "sheriff_vote_cast",
        actor=participant_two,
        target=participant_one,
        payload={"ballot_no": 1, "vote_weight": 1.5},
        client_event_id="projection-vote-correction",
    )
    correction["reason"] = "Recorded voter and target were reversed"
    corrected = api_client.post(
        f"{event_endpoint}/{vote.json()['id']}/correct",
        json=correction,
        headers=headers,
    )
    voided = api_client.post(
        f"{event_endpoint}/{action.json()['id']}/void",
        json={"reason": "Check did not happen"},
        headers=headers,
    )
    assert corrected.status_code == voided.status_code == 200

    prefix = api_client.get(
        f"{derived_endpoint}?through_logical_sequence=1",
        headers=headers,
    )
    assert prefix.status_code == 200
    assert prefix.json()["effective_event_count"] == 1
    assert prefix.json()["phase"]["phase_is_open"] is True
    assert prefix.json()["ballots"] == []

    full = api_client.get(derived_endpoint, headers=headers)
    assert full.status_code == 200, full.text
    body = full.json()
    assert body["effective_event_count"] == 2
    assert body["event_ledger_head_sequence"] == 4
    assert body["last_applied_logical_sequence"] == 2
    assert body["recorded_actions"] == []
    ballot = body["ballots"][0]
    assert ballot["vote_event_ids"] == [corrected.json()["id"]]
    assert ballot["voter_participant_ids"] == [participant_two]
    assert ballot["raw_tally"] == [
        {"participant_id": participant_one, "vote_weight": 1.5}
    ]

    db_session.expire_all()
    game = db_session.get(Game, scenario.game_id)
    assert game.next_event_sequence == 5


def test_confirmed_historical_game_remains_projectable(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session)
    _prepare_draft(api_client, scenario)
    judge_headers = scenario.headers_for(scenario.judge_id)
    admin_headers = scenario.headers_for(scenario.admin_id)

    assert api_client.post(
        f"{API_PREFIX}/games/{scenario.game_id}/submit-result",
        headers=judge_headers,
    ).status_code == 200
    assert api_client.post(
        f"{API_PREFIX}/games/{scenario.game_id}/confirm-result",
        json={"comment": "Projection history test"},
        headers=admin_headers,
    ).status_code == 200

    response = api_client.get(
        f"{API_PREFIX}/games/{scenario.game_id}/derived-state",
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["effective_event_count"] == 0
    assert response.json()["has_format_snapshot"] is True


def test_projection_service_has_fixed_read_query_shape_and_no_game_writes(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session)
    participant_one, participant_two = _prepare_draft(api_client, scenario)
    game = db_session.get(Game, scenario.game_id)
    original_updated_at = game.updated_at
    for sequence in range(1, 51):
        db_session.add(
            GameEvent(
                game_id=scenario.game_id,
                sequence_no=sequence,
                logical_sequence_no=sequence,
                phase=GameEventPhase.NIGHT,
                round_no=((sequence - 1) // 10) + 1,
                event_type="wolf_kill_selected",
                target_participant_id=participant_one
                if sequence % 2
                else participant_two,
                payload_json={},
                visibility=GameEventVisibility.POSTGAME_FULL,
                source=GameEventSource.MANUAL,
                status=GameEventStatus.ACTIVE,
                created_by_user_id=scenario.judge_id,
            )
        )
    game.next_event_sequence = 51
    db_session.commit()
    original_updated_at = db_session.get(Game, scenario.game_id).updated_at
    current_user = db_session.scalar(select(User).where(User.id == scenario.judge_id))
    assert current_user is not None
    _ = current_user.roles

    statement_count = 0
    engine = db_session.get_bind()
    assert isinstance(engine, Engine)

    def count_statements(*_args) -> None:
        nonlocal statement_count
        statement_count += 1

    event.listen(engine, "before_cursor_execute", count_statements)
    try:
        state = get_game_derived_state(
            db_session,
            scenario.game_id,
            current_user,
            through_logical_sequence=None,
        )
    finally:
        event.remove(engine, "before_cursor_execute", count_statements)

    assert state.effective_event_count == 50
    assert statement_count <= 5
    db_session.expire_all()
    unchanged = db_session.get(Game, scenario.game_id)
    assert unchanged.next_event_sequence == 51
    assert unchanged.updated_at == original_updated_at
