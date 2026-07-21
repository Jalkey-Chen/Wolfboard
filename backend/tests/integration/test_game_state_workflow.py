"""Integration coverage for independent play and result state machines."""

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import GamePlayStatus, GameResultStatus, GameStatusScope
from app.models.audit_log import AuditLog
from app.models.game import Game
from app.models.game_status_history import GameStatusHistory
from tests.integration.result_support import API_PREFIX, create_result_scenario, save_and_submit


pytestmark = pytest.mark.integration


def _state_action(client: TestClient, scenario, action: str, user_id: int, json=None):
    return client.post(
        f"{API_PREFIX}/games/{scenario.game_id}/{action}",
        headers=scenario.headers_for(user_id),
        json=json,
    )


def test_created_game_has_fixed_initial_states_and_rejects_state_input(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session)
    payload = {
        "event_day_id": scenario.event_day_id,
        "game_number": 2,
        "table_number": 1,
        "format_id": scenario.format_id,
        "judge_user_id": scenario.judge_id,
        "game_type": "official",
    }
    created = api_client.post(
        f"{API_PREFIX}/games",
        json=payload,
        headers=scenario.headers_for(scenario.admin_id),
    )
    assert created.status_code == 200, created.text
    assert created.json()["play_status"] == GamePlayStatus.SCHEDULED.value
    assert created.json()["result_status"] == GameResultStatus.EMPTY.value
    assert "status" not in created.json()

    rejected = api_client.post(
        f"{API_PREFIX}/games",
        json={**payload, "game_number": 3, "result_status": "confirmed"},
        headers=scenario.headers_for(scenario.admin_id),
    )
    assert rejected.status_code == 422


def test_assigned_judge_can_start_and_end_with_history_and_audit(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session)
    forbidden = _state_action(api_client, scenario, "start", scenario.other_judge_id)
    assert forbidden.status_code == 403

    started = _state_action(api_client, scenario, "start", scenario.judge_id)
    assert started.status_code == 200, started.text
    assert started.json()["play_status"] == GamePlayStatus.IN_PROGRESS.value
    assert started.json()["result_status"] == GameResultStatus.EMPTY.value
    assert started.json()["started_at"] is not None
    assert _state_action(api_client, scenario, "start", scenario.judge_id).status_code == 409

    ended = _state_action(api_client, scenario, "end", scenario.judge_id)
    assert ended.status_code == 200, ended.text
    assert ended.json()["play_status"] == GamePlayStatus.ENDED.value
    assert ended.json()["ended_at"] is not None
    assert _state_action(api_client, scenario, "end", scenario.judge_id).status_code == 409

    db_session.expire_all()
    histories = list(
        db_session.scalars(
            select(GameStatusHistory)
            .where(GameStatusHistory.game_id == scenario.game_id)
            .order_by(GameStatusHistory.id)
        )
    )
    assert [(item.status_scope, item.transition_key) for item in histories] == [
        (GameStatusScope.PLAY, "start_game"),
        (GameStatusScope.PLAY, "end_game"),
    ]
    assert db_session.scalar(
        select(func.count(AuditLog.id)).where(
            AuditLog.entity_id == scenario.game_id,
            AuditLog.action_type.in_(["start_game", "end_game"]),
        )
    ) == 2


def test_first_draft_save_auto_starts_and_repeated_save_does_not_duplicate_history(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session)
    endpoint = f"{API_PREFIX}/games/{scenario.game_id}/result-draft"
    headers = scenario.headers_for(scenario.judge_id)
    first = api_client.put(endpoint, json=scenario.valid_draft(), headers=headers)
    assert first.status_code == 200, first.text
    assert first.json()["game"]["play_status"] == GamePlayStatus.IN_PROGRESS.value
    assert first.json()["game"]["result_status"] == GameResultStatus.DRAFT.value
    assert first.json()["game"]["started_at"] is not None
    first_ids = [(row["participant_id"], row["id"]) for row in first.json()["players"]]

    payload = scenario.valid_draft()
    for row, saved in zip(payload["players"], first.json()["players"], strict=True):
        row["participant_id"] = saved["participant_id"]
    repeated = api_client.put(endpoint, json=payload, headers=headers)
    assert repeated.status_code == 200, repeated.text
    assert [(row["participant_id"], row["id"]) for row in repeated.json()["players"]] == first_ids

    db_session.expire_all()
    histories = list(
        db_session.scalars(
            select(GameStatusHistory).where(GameStatusHistory.game_id == scenario.game_id)
        )
    )
    assert {(item.status_scope, item.transition_key) for item in histories} == {
        (GameStatusScope.PLAY, "auto_start_on_draft"),
        (GameStatusScope.RESULT, "save_result_draft"),
    }


def test_submit_auto_ends_game_and_records_both_transitions(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session)
    headers = scenario.headers_for(scenario.judge_id)
    save = api_client.put(
        f"{API_PREFIX}/games/{scenario.game_id}/result-draft",
        json=scenario.valid_draft(),
        headers=headers,
    )
    assert save.status_code == 200
    submitted = api_client.post(
        f"{API_PREFIX}/games/{scenario.game_id}/submit-result",
        headers=headers,
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["game"]["play_status"] == GamePlayStatus.ENDED.value
    assert submitted.json()["game"]["result_status"] == GameResultStatus.SUBMITTED.value
    assert submitted.json()["game"]["ended_at"] is not None

    db_session.expire_all()
    transitions = {
        (item.status_scope, item.transition_key)
        for item in db_session.scalars(
            select(GameStatusHistory).where(GameStatusHistory.game_id == scenario.game_id)
        )
    }
    assert (GameStatusScope.PLAY, "auto_end_on_submit") in transitions
    assert (GameStatusScope.RESULT, "submit_result") in transitions
    audit = db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_id == scenario.game_id,
            AuditLog.action_type == "submit_result",
        )
    )
    assert audit is not None
    assert audit.new_value_json["game"]["play_status"] == GamePlayStatus.ENDED.value
    assert audit.new_value_json["game"]["result_status"] == GameResultStatus.SUBMITTED.value


def test_admin_cancel_requires_reason_and_blocks_result_workflow(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session)
    assert _state_action(api_client, scenario, "cancel", scenario.admin_id, {"reason": ""}).status_code == 422
    assert _state_action(api_client, scenario, "cancel", scenario.judge_id, {"reason": "No table"}).status_code == 403

    cancelled = _state_action(api_client, scenario, "cancel", scenario.admin_id, {"reason": "No table available"})
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["play_status"] == GamePlayStatus.CANCELLED.value
    assert cancelled.json()["result_status"] == GameResultStatus.EMPTY.value
    assert cancelled.json()["cancelled_at"] is not None
    assert cancelled.json()["cancelled_by"] == scenario.admin_id
    assert cancelled.json()["cancellation_reason"] == "No table available"

    save = api_client.put(
        f"{API_PREFIX}/games/{scenario.game_id}/result-draft",
        json=scenario.valid_draft(),
        headers=scenario.headers_for(scenario.judge_id),
    )
    assert save.status_code == 400
    submit = api_client.post(
        f"{API_PREFIX}/games/{scenario.game_id}/submit-result",
        headers=scenario.headers_for(scenario.judge_id),
    )
    assert submit.status_code == 409


def test_format_freezes_after_start_but_operational_fields_remain_editable(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session)
    headers = scenario.headers_for(scenario.admin_id)
    scheduled_patch = api_client.patch(
        f"{API_PREFIX}/games/{scenario.game_id}",
        json={"format_id": scenario.format_id},
        headers=headers,
    )
    assert scheduled_patch.status_code == 200
    assert _state_action(api_client, scenario, "start", scenario.admin_id).status_code == 200

    frozen = api_client.patch(
        f"{API_PREFIX}/games/{scenario.game_id}",
        json={"format_id": scenario.format_id},
        headers=headers,
    )
    assert frozen.status_code == 409
    operational = api_client.patch(
        f"{API_PREFIX}/games/{scenario.game_id}",
        json={"table_number": 8, "notes": "Moved after start"},
        headers=headers,
    )
    assert operational.status_code == 200
    assert operational.json()["table_number"] == 8


def test_submitted_game_cannot_be_cancelled(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session)
    headers = scenario.headers_for(scenario.judge_id)
    assert api_client.put(
        f"{API_PREFIX}/games/{scenario.game_id}/result-draft",
        json=scenario.valid_draft(),
        headers=headers,
    ).status_code == 200
    assert api_client.post(
        f"{API_PREFIX}/games/{scenario.game_id}/submit-result",
        headers=headers,
    ).status_code == 200
    response = _state_action(
        api_client,
        scenario,
        "cancel",
        scenario.admin_id,
        {"reason": "Too late"},
    )
    assert response.status_code == 409

    db_session.expire_all()
    game = db_session.get(Game, scenario.game_id)
    assert game is not None
    assert game.play_status == GamePlayStatus.ENDED
    assert game.result_status == GameResultStatus.SUBMITTED


def test_rejected_result_must_be_resaved_and_records_draft_transition(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session)
    save_and_submit(api_client, scenario, scenario.game_id)
    rejected = api_client.post(
        f"{API_PREFIX}/games/{scenario.game_id}/reject-result",
        json={"comment": "Correct the result"},
        headers=scenario.headers_for(scenario.admin_id),
    )
    assert rejected.status_code == 200
    assert rejected.json()["game"]["play_status"] == GamePlayStatus.ENDED.value
    assert rejected.json()["game"]["result_status"] == GameResultStatus.REJECTED.value

    assert api_client.post(
        f"{API_PREFIX}/games/{scenario.game_id}/submit-result",
        headers=scenario.headers_for(scenario.judge_id),
    ).status_code == 409
    resaved = api_client.put(
        f"{API_PREFIX}/games/{scenario.game_id}/result-draft",
        json=scenario.valid_draft(),
        headers=scenario.headers_for(scenario.judge_id),
    )
    assert resaved.status_code == 200
    assert resaved.json()["game"]["result_status"] == GameResultStatus.DRAFT.value
    assert resaved.json()["game"]["play_status"] == GamePlayStatus.ENDED.value

    db_session.expire_all()
    transition = db_session.scalar(
        select(GameStatusHistory).where(
            GameStatusHistory.game_id == scenario.game_id,
            GameStatusHistory.old_status == GameResultStatus.REJECTED.value,
            GameStatusHistory.new_status == GameResultStatus.DRAFT.value,
        )
    )
    assert transition is not None and transition.transition_key == "save_result_draft"
    assert db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_id == scenario.game_id,
            AuditLog.action_type == "save_result_draft",
            AuditLog.old_value_json["game"]["result_status"].as_string() == GameResultStatus.REJECTED.value,
        )
    ) is not None


def test_ended_draft_submission_only_changes_result_state(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session)
    assert api_client.put(
        f"{API_PREFIX}/games/{scenario.game_id}/result-draft",
        json=scenario.valid_draft(),
        headers=scenario.headers_for(scenario.judge_id),
    ).status_code == 200
    assert _state_action(api_client, scenario, "end", scenario.judge_id).status_code == 200
    submitted = api_client.post(
        f"{API_PREFIX}/games/{scenario.game_id}/submit-result",
        headers=scenario.headers_for(scenario.judge_id),
    )
    assert submitted.status_code == 200
    assert submitted.json()["game"]["play_status"] == GamePlayStatus.ENDED.value
    transitions = list(
        db_session.scalars(
            select(GameStatusHistory.transition_key).where(GameStatusHistory.game_id == scenario.game_id)
        )
    )
    assert "submit_result" in transitions
    assert "auto_end_on_submit" not in transitions


def test_in_progress_game_can_be_cancelled_but_blank_reason_is_rejected(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session)
    assert _state_action(api_client, scenario, "start", scenario.judge_id).status_code == 200
    blank = _state_action(api_client, scenario, "cancel", scenario.admin_id, {"reason": "   "})
    assert blank.status_code == 422
    cancelled = _state_action(
        api_client,
        scenario,
        "cancel",
        scenario.admin_id,
        {"reason": "Venue closed"},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["play_status"] == GamePlayStatus.CANCELLED.value
