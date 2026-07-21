"""Regression coverage for the current M5 result and scoring workflows."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import (
    GameStatus,
    GameType,
    ResultConfirmationStatus,
    ScoreLogEffectiveStatus,
)
from app.models.audit_log import AuditLog
from app.models.game import Game
from app.models.game_status_history import GameStatusHistory
from app.models.result_confirmation import ResultConfirmation
from app.models.score_log import ScoreLog
from tests.integration.result_support import (
    API_PREFIX,
    confirm,
    create_additional_game,
    create_result_scenario,
    save_and_submit,
)


pytestmark = pytest.mark.integration


def test_result_draft_permissions_persistence_and_page_payload(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session)
    endpoint = f"{API_PREFIX}/games/{scenario.game_id}/result-draft"

    assert api_client.get(endpoint).status_code == 401

    response = api_client.get(endpoint, headers=scenario.headers_for(scenario.judge_id))
    assert response.status_code == 200
    initial = response.json()
    assert initial["editable"] is True
    assert initial["players"] == []
    assert {role["role_name"] for role in initial["format_roles"]} == {"Seer", "Werewolf"}
    assert {player["user_id"] for player in initial["selectable_players"]} == {
        scenario.player_one_id,
        scenario.player_two_id,
        scenario.replacement_player_id,
        scenario.viewer_id,
    }
    assert initial["game"]["format"]["player_count"] == 2
    assert initial["game"]["judge"]["id"] == scenario.judge_id
    assert initial["validation"]["errors"][0]["code"] == "players_required"

    save_response = api_client.put(
        endpoint,
        json=scenario.valid_draft(),
        headers=scenario.headers_for(scenario.judge_id),
    )
    assert save_response.status_code == 200
    saved = save_response.json()
    assert saved["game"]["status"] == GameStatus.IN_PROGRESS.value
    assert saved["editable"] is True

    restored_response = api_client.get(endpoint, headers=scenario.headers_for(scenario.judge_id))
    assert restored_response.status_code == 200
    restored = restored_response.json()
    assert len(restored["players"]) == 2
    assert restored["players"][0]["final_score"] == 1.25
    assert restored["adjustments"][0]["target_seat_number"] == 1
    assert restored["validation"] == {"errors": [], "warnings": []}

    other_judge = api_client.put(
        endpoint,
        json=scenario.valid_draft(),
        headers=scenario.headers_for(scenario.other_judge_id),
    )
    assert other_judge.status_code == 403
    admin = api_client.put(
        endpoint,
        json=scenario.valid_draft(),
        headers=scenario.headers_for(scenario.admin_id),
    )
    assert admin.status_code == 403
    assert api_client.get(endpoint, headers=scenario.headers_for(scenario.viewer_id)).status_code == 403

    admin_read = api_client.get(endpoint, headers=scenario.headers_for(scenario.admin_id))
    assert admin_read.status_code == 200
    assert admin_read.json()["editable"] is False


def test_assigned_judge_cannot_access_another_judges_open_draft(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session)
    other_game_id = create_additional_game(
        db_session,
        scenario,
        judge_user_id=scenario.other_judge_id,
    )
    endpoint = f"{API_PREFIX}/games/{other_game_id}/result-draft"

    assert api_client.get(endpoint, headers=scenario.headers_for(scenario.judge_id)).status_code == 403
    assert api_client.get(endpoint, headers=scenario.headers_for(scenario.admin_id)).status_code == 200


def test_submit_validates_draft_records_actor_and_rejects_repetition(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session)
    draft_endpoint = f"{API_PREFIX}/games/{scenario.game_id}/result-draft"
    submit_endpoint = f"{API_PREFIX}/games/{scenario.game_id}/submit-result"
    incomplete = {
        "players": [{"user_id": scenario.player_one_id, "seat_number": 1}],
        "adjustments": [],
    }

    assert api_client.put(
        draft_endpoint,
        json=incomplete,
        headers=scenario.headers_for(scenario.judge_id),
    ).status_code == 200
    invalid_submit = api_client.post(
        submit_endpoint,
        headers=scenario.headers_for(scenario.judge_id),
    )
    assert invalid_submit.status_code == 422
    error_codes = {item["code"] for item in invalid_submit.json()["detail"]["errors"]}
    assert {"role_required", "faction_required", "winner_required"} <= error_codes

    assert api_client.put(
        draft_endpoint,
        json=scenario.valid_draft(),
        headers=scenario.headers_for(scenario.judge_id),
    ).status_code == 200
    assert api_client.post(
        submit_endpoint,
        headers=scenario.headers_for(scenario.other_judge_id),
    ).status_code == 403

    submitted = api_client.post(
        submit_endpoint,
        headers=scenario.headers_for(scenario.judge_id),
    )
    assert submitted.status_code == 200
    body = submitted.json()["game"]
    assert body["status"] == GameStatus.SUBMITTED.value
    assert body["submitted_by"] == scenario.judge_id
    assert datetime.fromisoformat(body["submitted_at"]).tzinfo is not None

    repeated = api_client.post(submit_endpoint, headers=scenario.headers_for(scenario.judge_id))
    assert repeated.status_code == 400


def test_reject_is_admin_only_and_writes_review_history_and_audit(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session)
    endpoint = f"{API_PREFIX}/games/{scenario.game_id}/reject-result"

    wrong_status = api_client.post(
        endpoint,
        json={"comment": "Not submitted"},
        headers=scenario.headers_for(scenario.admin_id),
    )
    assert wrong_status.status_code == 400
    save_and_submit(api_client, scenario, scenario.game_id)

    forbidden = api_client.post(
        endpoint,
        json={"comment": "Judge cannot reject"},
        headers=scenario.headers_for(scenario.judge_id),
    )
    assert forbidden.status_code == 403
    rejected = api_client.post(
        endpoint,
        json={"comment": "Please correct this result"},
        headers=scenario.headers_for(scenario.admin_id),
    )
    assert rejected.status_code == 200
    assert rejected.json()["game"]["status"] == GameStatus.DRAFT.value

    db_session.expire_all()
    game = db_session.get(Game, scenario.game_id)
    confirmation = db_session.scalar(
        select(ResultConfirmation).where(ResultConfirmation.game_id == scenario.game_id)
    )
    history = db_session.scalar(
        select(GameStatusHistory).where(GameStatusHistory.game_id == scenario.game_id)
    )
    audit = db_session.scalar(
        select(AuditLog).where(AuditLog.entity_id == scenario.game_id)
    )
    assert game is not None and game.status == GameStatus.DRAFT
    assert game.submitted_at is None and game.submitted_by is None
    assert confirmation is not None
    assert confirmation.confirmation_status == ResultConfirmationStatus.REJECTED
    assert confirmation.confirmed_by == scenario.admin_id
    assert history is not None
    assert (history.old_status, history.new_status) == (GameStatus.SUBMITTED, GameStatus.DRAFT)
    assert history.changed_by == scenario.admin_id
    assert audit is not None and audit.action_type == "reject"
    assert audit.reason == "Please correct this result"
    assert audit.old_value_json["game"]["status"] == GameStatus.SUBMITTED.value
    assert audit.old_value_json["game"]["submitted_by"] == scenario.judge_id
    assert audit.old_value_json["game"]["submitted_at"] is not None
    assert audit.new_value_json["game"]["status"] == GameStatus.DRAFT.value
    assert audit.new_value_json["game"]["submitted_by"] is None
    assert audit.new_value_json["game"]["submitted_at"] is None


def test_confirm_is_admin_only_creates_scores_and_official_leaderboard_entries(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session)
    endpoint = f"{API_PREFIX}/games/{scenario.game_id}/confirm-result"

    assert api_client.post(
        endpoint,
        json={"comment": "Too early"},
        headers=scenario.headers_for(scenario.admin_id),
    ).status_code == 400
    save_and_submit(api_client, scenario, scenario.game_id)
    assert api_client.post(
        endpoint,
        json={"comment": "Judge cannot confirm"},
        headers=scenario.headers_for(scenario.judge_id),
    ).status_code == 403

    confirmed = api_client.post(
        endpoint,
        json={"comment": "Approved"},
        headers=scenario.headers_for(scenario.admin_id),
    )
    assert confirmed.status_code == 200
    game_body = confirmed.json()["game"]
    assert game_body["status"] == GameStatus.CONFIRMED.value
    assert game_body["confirmed_by"] == scenario.admin_id
    assert datetime.fromisoformat(game_body["confirmed_at"]).tzinfo is not None
    assert api_client.post(
        endpoint,
        json={"comment": "Repeated"},
        headers=scenario.headers_for(scenario.admin_id),
    ).status_code == 400

    db_session.expire_all()
    logs = list(db_session.scalars(select(ScoreLog).where(ScoreLog.game_id == scenario.game_id)))
    assert len(logs) == 2
    assert all(log.effective_status == ScoreLogEffectiveStatus.EFFECTIVE for log in logs)
    assert {log.user_id for log in logs} == {scenario.player_one_id, scenario.player_two_id}
    assert db_session.scalar(
        select(func.count(ResultConfirmation.id)).where(ResultConfirmation.game_id == scenario.game_id)
    ) == 1
    assert db_session.scalar(
        select(func.count(GameStatusHistory.id)).where(GameStatusHistory.game_id == scenario.game_id)
    ) == 1
    assert db_session.scalar(
        select(func.count(AuditLog.id)).where(AuditLog.entity_id == scenario.game_id)
    ) == 1
    audit = db_session.scalar(
        select(AuditLog).where(AuditLog.entity_id == scenario.game_id)
    )
    assert audit is not None
    assert audit.old_value_json["game"]["status"] == GameStatus.SUBMITTED.value
    assert audit.new_value_json["game"]["status"] == GameStatus.CONFIRMED.value
    assert len(audit.new_value_json["score_logs"]) == 2
    assert {
        score_log["effective_status"] for score_log in audit.new_value_json["score_logs"]
    } == {ScoreLogEffectiveStatus.EFFECTIVE.value}

    fun_game_id = create_additional_game(db_session, scenario, game_type=GameType.FUN)
    save_and_submit(api_client, scenario, fun_game_id)
    confirm(api_client, scenario, fun_game_id)
    leaderboard = api_client.get(
        f"{API_PREFIX}/seasons/{scenario.season_id}/leaderboard",
        headers=scenario.headers_for(scenario.viewer_id),
    )
    assert leaderboard.status_code == 200
    entries = {entry["user_id"]: entry for entry in leaderboard.json()}
    assert entries[scenario.player_one_id]["total_score"] == 1.25
    assert entries[scenario.player_one_id]["games_played"] == 1
    assert entries[scenario.player_two_id]["total_score"] == -1.0


def test_admin_revision_supports_submitted_confirmed_and_revised_states(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session)
    submitted_game_id = create_additional_game(db_session, scenario)
    save_and_submit(api_client, scenario, submitted_game_id)
    submitted_revision = {
        **scenario.valid_draft(),
        "reason": "Direct correction before confirmation",
    }
    response = api_client.post(
        f"{API_PREFIX}/games/{submitted_game_id}/revise-result",
        json=submitted_revision,
        headers=scenario.headers_for(scenario.admin_id),
    )
    assert response.status_code == 200
    assert response.json()["game"]["status"] == GameStatus.REVISED.value

    save_and_submit(api_client, scenario, scenario.game_id)
    confirm(api_client, scenario, scenario.game_id)
    first_revision = {
        **scenario.valid_draft(),
        "reason": "Correct confirmed result",
    }
    endpoint = f"{API_PREFIX}/games/{scenario.game_id}/revise-result"
    assert api_client.post(
        endpoint,
        json=first_revision,
        headers=scenario.headers_for(scenario.judge_id),
    ).status_code == 403
    revised = api_client.post(
        endpoint,
        json=first_revision,
        headers=scenario.headers_for(scenario.admin_id),
    )
    assert revised.status_code == 200
    assert revised.json()["game"]["status"] == GameStatus.REVISED.value

    second_payload = scenario.valid_draft()
    second_payload["players"][0]["is_winner"] = False  # type: ignore[index]
    second_payload["players"][1]["is_winner"] = True  # type: ignore[index]
    repeated = api_client.post(
        endpoint,
        json={**second_payload, "reason": "Second correction"},
        headers=scenario.headers_for(scenario.admin_id),
    )
    assert repeated.status_code == 200

    db_session.expire_all()
    logs = list(
        db_session.scalars(
            select(ScoreLog)
            .where(ScoreLog.game_id == scenario.game_id)
            .order_by(ScoreLog.id)
        )
    )
    assert len(logs) == 6
    assert [log.effective_status for log in logs].count(ScoreLogEffectiveStatus.VOIDED) == 4
    assert [log.effective_status for log in logs].count(ScoreLogEffectiveStatus.EFFECTIVE) == 2
    confirmations = list(
        db_session.scalars(
            select(ResultConfirmation)
            .where(ResultConfirmation.game_id == scenario.game_id)
            .order_by(ResultConfirmation.id)
        )
    )
    assert [item.confirmation_status for item in confirmations] == [
        ResultConfirmationStatus.APPROVED,
        ResultConfirmationStatus.REVISED,
        ResultConfirmationStatus.REVISED,
    ]
    assert db_session.scalar(
        select(func.count(GameStatusHistory.id)).where(GameStatusHistory.game_id == scenario.game_id)
    ) == 3
    assert db_session.scalar(
        select(func.count(AuditLog.id)).where(AuditLog.entity_id == scenario.game_id)
    ) == 3


def test_confirmed_and_revised_results_are_visible_to_authenticated_users(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session)
    save_and_submit(api_client, scenario, scenario.game_id)
    confirm(api_client, scenario, scenario.game_id)
    endpoint = f"{API_PREFIX}/games/{scenario.game_id}/result-draft"

    confirmed = api_client.get(endpoint, headers=scenario.headers_for(scenario.viewer_id))
    assert confirmed.status_code == 200
    assert confirmed.json()["editable"] is False
    assert {player["role_name"] for player in confirmed.json()["players"]} == {"Seer", "Werewolf"}

    revised_payload = {**scenario.valid_draft(), "reason": "Visibility regression"}
    assert api_client.post(
        f"{API_PREFIX}/games/{scenario.game_id}/revise-result",
        json=revised_payload,
        headers=scenario.headers_for(scenario.admin_id),
    ).status_code == 200
    revised = api_client.get(endpoint, headers=scenario.headers_for(scenario.viewer_id))
    assert revised.status_code == 200
    assert revised.json()["game"]["status"] == GameStatus.REVISED.value
