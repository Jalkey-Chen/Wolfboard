"""Executable specifications for known M6 prerequisite defects."""

from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import GameStatus, GameType, ScoreLogEffectiveStatus
from app.models.game import Game
from app.models.game_player import GamePlayer
from app.models.event_day import EventDay
from app.models.audit_log import AuditLog
from app.models.result_confirmation import ResultConfirmation
from app.models.score_log import ScoreLog
from app.models.season import Season
from tests.integration.result_support import (
    API_PREFIX,
    confirm,
    create_additional_game,
    create_result_scenario,
    save_and_submit,
)


pytestmark = pytest.mark.integration


def test_draft_save_response_contains_the_persisted_rows(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session)
    payload = scenario.valid_draft()
    response = api_client.put(
        f"{API_PREFIX}/games/{scenario.game_id}/result-draft",
        json=payload,
        headers=scenario.headers_for(scenario.judge_id),
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["players"]) == 2
    assert len(body["adjustments"]) == 1
    assert [player["seat_number"] for player in body["players"]] == [1, 2]
    assert [player["role_name"] for player in body["players"]] == ["Seer", "Werewolf"]
    assert [player["final_score"] for player in body["players"]] == [1.25, -1.0]
    assert body["adjustments"][0]["target_seat_number"] == 1
    assert body["adjustments"][0]["delta"] == 0.25

    restored = api_client.get(
        f"{API_PREFIX}/games/{scenario.game_id}/result-draft",
        headers=scenario.headers_for(scenario.judge_id),
    )
    assert restored.status_code == 200
    assert restored.json() == body


def test_rejection_preserves_original_submission_metadata(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session)
    save_and_submit(api_client, scenario, scenario.game_id)
    db_session.expire_all()
    submitted_game = db_session.get(Game, scenario.game_id)
    assert submitted_game is not None
    original_submitted_at = submitted_game.submitted_at

    response = api_client.post(
        f"{API_PREFIX}/games/{scenario.game_id}/reject-result",
        json={"comment": "Known metadata defect"},
        headers=scenario.headers_for(scenario.admin_id),
    )
    assert response.status_code == 200
    db_session.expire_all()
    confirmation = db_session.scalar(
        select(ResultConfirmation).where(ResultConfirmation.game_id == scenario.game_id)
    )
    assert confirmation is not None
    assert confirmation.submitted_by == scenario.judge_id
    assert confirmation.submitted_at == original_submitted_at

    resubmitted = api_client.post(
        f"{API_PREFIX}/games/{scenario.game_id}/submit-result",
        headers=scenario.headers_for(scenario.judge_id),
    )
    assert resubmitted.status_code == 200
    new_submission = resubmitted.json()["game"]
    assert new_submission["submitted_by"] == scenario.judge_id
    assert original_submitted_at is not None
    assert datetime.fromisoformat(new_submission["submitted_at"]) > original_submitted_at

    db_session.expire_all()
    confirmations = list(
        db_session.scalars(
            select(ResultConfirmation).where(ResultConfirmation.game_id == scenario.game_id)
        )
    )
    assert len(confirmations) == 1
    assert confirmations[0].submitted_by == scenario.judge_id
    assert confirmations[0].submitted_at == original_submitted_at


def test_generic_patch_cannot_bypass_confirmed_result_state_machine(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session)
    save_and_submit(api_client, scenario, scenario.game_id)
    confirm(api_client, scenario, scenario.game_id)

    response = api_client.patch(
        f"{API_PREFIX}/games/{scenario.game_id}",
        json={"status": GameStatus.DRAFT.value},
        headers=scenario.headers_for(scenario.admin_id),
    )
    assert response.status_code == 422
    db_session.expire_all()
    game = db_session.get(Game, scenario.game_id)
    assert game is not None and game.status == GameStatus.CONFIRMED

    allowed_patch = api_client.patch(
        f"{API_PREFIX}/games/{scenario.game_id}",
        json={"notes": "Operational note", "table_number": 9},
        headers=scenario.headers_for(scenario.admin_id),
    )
    assert allowed_patch.status_code == 200
    assert allowed_patch.json()["notes"] == "Operational note"
    assert allowed_patch.json()["table_number"] == 9
    assert allowed_patch.json()["status"] == GameStatus.CONFIRMED.value


def test_game_creation_only_allows_draft_initial_status(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session)
    payload = {
        "event_day_id": scenario.event_day_id,
        "game_number": 20,
        "table_number": 1,
        "format_id": scenario.format_id,
        "judge_user_id": scenario.judge_id,
        "game_type": GameType.OFFICIAL.value,
    }

    forbidden = api_client.post(
        f"{API_PREFIX}/games",
        json={**payload, "status": GameStatus.CONFIRMED.value},
        headers=scenario.headers_for(scenario.admin_id),
    )
    assert forbidden.status_code == 422

    created = api_client.post(
        f"{API_PREFIX}/games",
        json=payload,
        headers=scenario.headers_for(scenario.admin_id),
    )
    assert created.status_code == 200
    assert created.json()["status"] == GameStatus.DRAFT.value


def test_non_official_score_logs_do_not_affect_official_running_balance(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session, game_type=GameType.FUN)
    save_and_submit(api_client, scenario, scenario.game_id)
    confirm(api_client, scenario, scenario.game_id)
    practice_game_id = create_additional_game(db_session, scenario, game_type=GameType.PRACTICE)
    save_and_submit(api_client, scenario, practice_game_id)
    confirm(api_client, scenario, practice_game_id)
    official_game_id = create_additional_game(db_session, scenario, game_type=GameType.OFFICIAL)
    save_and_submit(api_client, scenario, official_game_id)
    confirm(api_client, scenario, official_game_id)
    later_fun_game_id = create_additional_game(db_session, scenario, game_type=GameType.FUN)
    save_and_submit(api_client, scenario, later_fun_game_id)
    confirm(api_client, scenario, later_fun_game_id)

    db_session.expire_all()
    player_logs = {
        score_log.game_id: score_log
        for score_log in db_session.scalars(
            select(ScoreLog).where(
                ScoreLog.user_id == scenario.player_one_id,
                ScoreLog.effective_status == ScoreLogEffectiveStatus.EFFECTIVE,
            )
        )
    }
    assert player_logs[scenario.game_id].balance_after == 0.0
    assert player_logs[practice_game_id].balance_after == 0.0
    assert player_logs[official_game_id].balance_after == 1.25
    assert player_logs[later_fun_game_id].balance_after == 1.25

    revised_payload = scenario.valid_draft()
    revised_players = revised_payload["players"]
    assert isinstance(revised_players, list)
    revised_players[0]["is_winner"] = False
    response = api_client.post(
        f"{API_PREFIX}/games/{official_game_id}/revise-result",
        json={**revised_payload, "reason": "Correct official outcome"},
        headers=scenario.headers_for(scenario.admin_id),
    )
    assert response.status_code == 200

    db_session.expire_all()
    revised_official_log = db_session.scalar(
        select(ScoreLog).where(
            ScoreLog.game_id == official_game_id,
            ScoreLog.user_id == scenario.player_one_id,
            ScoreLog.effective_status == ScoreLogEffectiveStatus.EFFECTIVE,
        )
    )
    later_fun_log = db_session.scalar(
        select(ScoreLog).where(
            ScoreLog.game_id == later_fun_game_id,
            ScoreLog.user_id == scenario.player_one_id,
            ScoreLog.effective_status == ScoreLogEffectiveStatus.EFFECTIVE,
        )
    )
    assert revised_official_log is not None and revised_official_log.balance_after == -0.75
    assert later_fun_log is not None and later_fun_log.balance_after == -0.75

    leaderboard = api_client.get(
        f"{API_PREFIX}/seasons/{scenario.season_id}/leaderboard",
        headers=scenario.headers_for(scenario.viewer_id),
    )
    assert leaderboard.status_code == 200
    player_entry = next(
        entry for entry in leaderboard.json() if entry["user_id"] == scenario.player_one_id
    )
    assert player_entry["total_score"] == revised_official_log.balance_after

    second_season = Season(
        name="Second Integration Season",
        start_date=date(2027, 1, 1),
        end_date=date(2027, 12, 31),
        created_by=scenario.admin_id,
    )
    db_session.add(second_season)
    db_session.flush()
    second_event_day = EventDay(
        season_id=second_season.id,
        title="Second Season Event",
        event_date=date(2027, 6, 1),
        venue="Second Test Venue",
        created_by=scenario.admin_id,
    )
    db_session.add(second_event_day)
    db_session.flush()
    second_season_game = Game(
        event_day_id=second_event_day.id,
        game_number=1,
        table_number=1,
        format_id=scenario.format_id,
        judge_user_id=scenario.judge_id,
        game_type=GameType.OFFICIAL,
        status=GameStatus.DRAFT,
    )
    db_session.add(second_season_game)
    db_session.commit()
    save_and_submit(api_client, scenario, second_season_game.id)
    confirm(api_client, scenario, second_season_game.id)

    db_session.expire_all()
    second_season_log = db_session.scalar(
        select(ScoreLog).where(
            ScoreLog.game_id == second_season_game.id,
            ScoreLog.user_id == scenario.player_one_id,
            ScoreLog.effective_status == ScoreLogEffectiveStatus.EFFECTIVE,
        )
    )
    assert second_season_log is not None
    assert second_season_log.balance_after == second_season_log.delta == 1.25


def test_revision_recalculates_later_balances_for_removed_player(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session)
    save_and_submit(api_client, scenario, scenario.game_id)
    confirm(api_client, scenario, scenario.game_id)
    later_game_id = create_additional_game(db_session, scenario)
    save_and_submit(api_client, scenario, later_game_id)
    confirm(api_client, scenario, later_game_id)

    db_session.expire_all()
    before_revision = db_session.scalar(
        select(ScoreLog).where(
            ScoreLog.game_id == later_game_id,
            ScoreLog.user_id == scenario.player_one_id,
            ScoreLog.effective_status == ScoreLogEffectiveStatus.EFFECTIVE,
        )
    )
    assert before_revision is not None
    assert before_revision.balance_after == 2.5

    replacement_payload = {
        "players": [
            {
                "user_id": scenario.player_two_id,
                "seat_number": 1,
                "role_name": "Seer",
                "faction": "good",
                "final_status": "alive",
                "is_winner": True,
                "remarks": "Retained player",
            },
            {
                "user_id": scenario.replacement_player_id,
                "seat_number": 2,
                "role_name": "Werewolf",
                "faction": "wolf",
                "final_status": "eliminated",
                "is_winner": False,
                "remarks": "Added player",
            },
        ],
        "adjustments": [
            {
                "target_seat_number": 1,
                "adjustment_type": "judge_bonus",
                "delta": 0.25,
                "reason": "Retained player bonus",
            }
        ],
    }
    response = api_client.post(
        f"{API_PREFIX}/games/{scenario.game_id}/revise-result",
        json={**replacement_payload, "reason": "Remove player from older game"},
        headers=scenario.headers_for(scenario.admin_id),
    )
    assert response.status_code == 200

    db_session.expire_all()
    revised_game_logs = list(
        db_session.scalars(
            select(ScoreLog).where(
                ScoreLog.game_id == scenario.game_id,
                ScoreLog.effective_status == ScoreLogEffectiveStatus.EFFECTIVE,
            )
        )
    )
    assert {log.user_id for log in revised_game_logs} == {
        scenario.replacement_player_id,
        scenario.player_two_id,
    }
    effective_counts: dict[int, int] = {}
    for log in revised_game_logs:
        effective_counts[log.user_id] = effective_counts.get(log.user_id, 0) + 1
    assert effective_counts == {
        scenario.replacement_player_id: 1,
        scenario.player_two_id: 1,
    }
    removed_game_logs = list(
        db_session.scalars(
            select(ScoreLog).where(
                ScoreLog.game_id == scenario.game_id,
                ScoreLog.user_id == scenario.player_one_id,
            )
        )
    )
    assert removed_game_logs
    assert all(
        log.effective_status == ScoreLogEffectiveStatus.VOIDED
        for log in removed_game_logs
    )
    later_log = db_session.scalar(
        select(ScoreLog).where(
            ScoreLog.game_id == later_game_id,
            ScoreLog.user_id == scenario.player_one_id,
            ScoreLog.effective_status == ScoreLogEffectiveStatus.EFFECTIVE,
        )
    )
    assert later_log is not None
    assert later_log.balance_after == later_log.delta

    retained_later_log = db_session.scalar(
        select(ScoreLog).where(
            ScoreLog.game_id == later_game_id,
            ScoreLog.user_id == scenario.player_two_id,
            ScoreLog.effective_status == ScoreLogEffectiveStatus.EFFECTIVE,
        )
    )
    assert retained_later_log is not None
    assert retained_later_log.balance_after == 0.25

    leaderboard = api_client.get(
        f"{API_PREFIX}/seasons/{scenario.season_id}/leaderboard",
        headers=scenario.headers_for(scenario.viewer_id),
    )
    assert leaderboard.status_code == 200
    entries = {entry["user_id"]: entry for entry in leaderboard.json()}
    assert entries[scenario.player_one_id]["total_score"] == later_log.balance_after
    assert entries[scenario.player_two_id]["total_score"] == retained_later_log.balance_after
    assert entries[scenario.replacement_player_id]["total_score"] == -1.0

    audit = db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_id == scenario.game_id,
            AuditLog.action_type == "revise",
        )
    )
    assert audit is not None
    assert {player["user_id"] for player in audit.old_value_json["players"]} == {
        scenario.player_one_id,
        scenario.player_two_id,
    }
    assert {player["user_id"] for player in audit.new_value_json["players"]} == {
        scenario.player_two_id,
        scenario.replacement_player_id,
    }
    assert len(
        [
            score_log
            for score_log in audit.new_value_json["score_logs"]
            if score_log["effective_status"] == ScoreLogEffectiveStatus.EFFECTIVE.value
        ]
    ) == 2


@pytest.mark.xfail(
    strict=True,
    reason="M6.0C: stable participant identity awaits the dedicated participant model decision.",
)
def test_repeated_draft_save_preserves_game_player_ids(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session)
    endpoint = f"{API_PREFIX}/games/{scenario.game_id}/result-draft"
    headers = scenario.headers_for(scenario.judge_id)

    first = api_client.put(endpoint, json=scenario.valid_draft(), headers=headers)
    assert first.status_code == 200
    first_ids = [player["id"] for player in first.json()["players"]]
    second = api_client.put(endpoint, json=scenario.valid_draft(), headers=headers)
    assert second.status_code == 200
    second_ids = [player["id"] for player in second.json()["players"]]

    assert second_ids == first_ids
    db_session.expire_all()
    assert len(list(db_session.scalars(select(GamePlayer)))) == 2
