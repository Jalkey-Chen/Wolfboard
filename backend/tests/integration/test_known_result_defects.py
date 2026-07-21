"""Executable specifications for known M6 prerequisite defects."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import GameStatus, GameType, ScoreLogEffectiveStatus
from app.models.game import Game
from app.models.game_player import GamePlayer
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


@pytest.mark.xfail(
    strict=True,
    reason="M6.0B: draft replacement leaves the PUT response relationship cache stale until a new request.",
)
def test_draft_save_response_contains_the_persisted_rows(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session)
    response = api_client.put(
        f"{API_PREFIX}/games/{scenario.game_id}/result-draft",
        json=scenario.valid_draft(),
        headers=scenario.headers_for(scenario.judge_id),
    )
    assert response.status_code == 200
    assert len(response.json()["players"]) == 2
    assert len(response.json()["adjustments"]) == 1


@pytest.mark.xfail(
    strict=True,
    reason="M6.0B: rejection clears Game submission metadata before ResultConfirmation captures it.",
)
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


@pytest.mark.xfail(
    strict=True,
    reason="M6.0B: generic game PATCH currently bypasses result state-transition services.",
)
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
    assert response.status_code == 400
    db_session.expire_all()
    game = db_session.get(Game, scenario.game_id)
    assert game is not None and game.status == GameStatus.CONFIRMED


@pytest.mark.xfail(
    strict=True,
    reason="M6.0C: season balance recalculation includes non-official game score logs.",
)
def test_non_official_score_logs_do_not_affect_official_running_balance(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session, game_type=GameType.FUN)
    save_and_submit(api_client, scenario, scenario.game_id)
    confirm(api_client, scenario, scenario.game_id)
    official_game_id = create_additional_game(db_session, scenario, game_type=GameType.OFFICIAL)
    save_and_submit(api_client, scenario, official_game_id)
    confirm(api_client, scenario, official_game_id)

    db_session.expire_all()
    official_log = db_session.scalar(
        select(ScoreLog).where(
            ScoreLog.game_id == official_game_id,
            ScoreLog.user_id == scenario.player_one_id,
            ScoreLog.effective_status == ScoreLogEffectiveStatus.EFFECTIVE,
        )
    )
    assert official_log is not None
    assert official_log.balance_after == official_log.delta


@pytest.mark.xfail(
    strict=True,
    reason="M6.0C: revising a game recalculates balances only for players still present.",
)
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

    replacement_payload = scenario.valid_draft(player_one_id=scenario.replacement_player_id)
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
    later_log = db_session.scalar(
        select(ScoreLog).where(
            ScoreLog.game_id == later_game_id,
            ScoreLog.user_id == scenario.player_one_id,
            ScoreLog.effective_status == ScoreLogEffectiveStatus.EFFECTIVE,
        )
    )
    assert later_log is not None
    assert later_log.balance_after == later_log.delta


@pytest.mark.xfail(
    strict=True,
    reason="M6.0B: full-replacement draft saves delete and recreate GamePlayer rows.",
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
