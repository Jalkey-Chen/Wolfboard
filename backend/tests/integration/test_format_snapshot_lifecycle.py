"""Runtime format snapshot lifecycle and authority regressions."""

from copy import deepcopy

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import FormatRoleFaction, GamePlayStatus, FormatSnapshotOrigin
from app.models.audit_log import AuditLog
from app.models.format_role import FormatRole
from app.models.game import Game
from app.models.game_format_role_snapshot import GameFormatRoleSnapshot
from app.models.game_format_snapshot import GameFormatSnapshot
from app.models.game_status_history import GameStatusHistory
from app.models.user import User
from app.services.format_snapshot import freeze_game_format
from app.services.game import get_game_or_404
from tests.integration.result_support import API_PREFIX, create_result_scenario


pytestmark = pytest.mark.integration


def test_scheduled_context_is_live_and_start_freezes_latest_source(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session)
    headers = scenario.headers_for(scenario.judge_id)
    context_url = f"{API_PREFIX}/games/{scenario.game_id}/format-context"

    live = api_client.get(context_url, headers=headers)
    assert live.status_code == 200
    assert live.json()["is_frozen"] is False
    assert live.json()["snapshot_id"] is None

    seer = db_session.scalar(
        select(FormatRole).where(
            FormatRole.format_id == scenario.format_id,
            FormatRole.role_name == "Seer",
        )
    )
    assert seer is not None
    seer.metadata_json = {"can_check": True, "nested": {"version": 2}}
    seer.display_order = 9
    db_session.commit()

    started = api_client.post(f"{API_PREFIX}/games/{scenario.game_id}/start", headers=headers)
    assert started.status_code == 200, started.text
    assert started.json()["has_format_snapshot"] is True
    assert started.json()["format_snapshot_id"] is not None

    frozen = api_client.get(context_url, headers=headers).json()
    assert frozen["is_frozen"] is True
    assert frozen["snapshot_origin"] == FormatSnapshotOrigin.RUNTIME_FREEZE.value
    assert frozen["frozen_by_user_id"] == scenario.judge_id
    frozen_seer = next(role for role in frozen["roles"] if role["role_name"] == "Seer")
    assert frozen_seer["display_order"] == 9
    assert frozen_seer["metadata_json"] == {"can_check": True, "nested": {"version": 2}}


def test_snapshot_remains_authoritative_after_source_changes_and_role_rebuild(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session)
    headers = scenario.headers_for(scenario.judge_id)
    assert api_client.post(f"{API_PREFIX}/games/{scenario.game_id}/start", headers=headers).status_code == 200
    context_url = f"{API_PREFIX}/games/{scenario.game_id}/format-context"
    before = api_client.get(context_url, headers=headers).json()
    historical_roles = deepcopy(before["roles"])

    game_format = db_session.get(Game, scenario.game_id).format
    game_format.format_name = "Changed Source Name"
    game_format.description = "Changed after start"
    game_format.player_count = 3
    db_session.query(FormatRole).filter(FormatRole.format_id == scenario.format_id).delete(
        synchronize_session=False
    )
    db_session.flush()
    db_session.add_all(
        [
            FormatRole(
                format_id=scenario.format_id,
                role_name="New Role",
                faction=FormatRoleFaction.GOOD,
                role_count=3,
                display_order=1,
                metadata_json={"new": True},
            )
        ]
    )
    db_session.commit()

    after = api_client.get(context_url, headers=headers).json()
    assert after["snapshot_id"] == before["snapshot_id"]
    assert after["format_name"] == before["format_name"]
    assert after["player_count"] == before["player_count"]
    for role in after["roles"]:
        role.pop("source_format_role_id")
    for role in historical_roles:
        role.pop("source_format_role_id")
    assert after["roles"] == historical_roles
    assert all(role["source_format_role_id"] is None for role in api_client.get(context_url, headers=headers).json()["roles"])

    saved = api_client.put(
        f"{API_PREFIX}/games/{scenario.game_id}/result-draft",
        json=scenario.valid_draft(),
        headers=headers,
    )
    assert saved.status_code == 200, saved.text
    assert {role["role_name"] for role in saved.json()["format_context"]["roles"]} == {"Seer", "Werewolf"}


def test_invalid_runtime_format_and_failed_auto_start_leave_no_side_effects(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session)
    headers = scenario.headers_for(scenario.judge_id)
    game_format = db_session.get(Game, scenario.game_id).format
    game_format.is_active = False
    db_session.commit()

    failed_start = api_client.post(f"{API_PREFIX}/games/{scenario.game_id}/start", headers=headers)
    assert failed_start.status_code == 409
    db_session.expire_all()
    game = db_session.get(Game, scenario.game_id)
    assert game.play_status == GamePlayStatus.SCHEDULED
    assert game.format_snapshot is None
    assert db_session.scalar(select(func.count(GameStatusHistory.id))) == 0
    assert db_session.scalar(select(func.count(AuditLog.id))) == 0

    game_format.is_active = True
    game_format.player_count = 3
    db_session.commit()
    invalid_total = api_client.post(f"{API_PREFIX}/games/{scenario.game_id}/start", headers=headers)
    assert invalid_total.status_code == 409
    db_session.expire_all()
    assert db_session.get(Game, scenario.game_id).format_snapshot is None

    game_format = db_session.get(Game, scenario.game_id).format
    game_format.player_count = 2
    db_session.commit()
    invalid_payload = scenario.valid_draft()
    invalid_payload["players"][1]["seat_number"] = 1
    failed_save = api_client.put(
        f"{API_PREFIX}/games/{scenario.game_id}/result-draft",
        json=invalid_payload,
        headers=headers,
    )
    assert failed_save.status_code == 422
    db_session.expire_all()
    game = db_session.get(Game, scenario.game_id)
    assert game.play_status == GamePlayStatus.SCHEDULED
    assert game.format_snapshot is None
    assert db_session.scalar(select(func.count(GameStatusHistory.id))) == 0
    assert db_session.scalar(select(func.count(AuditLog.id))) == 0


def test_freeze_helper_is_idempotent_and_cancel_after_start_retains_snapshot(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session)
    game = get_game_or_404(db_session, scenario.game_id)
    judge = db_session.get(User, scenario.judge_id)
    assert judge is not None
    first = freeze_game_format(db_session, game, frozen_by_user_id=judge.id)
    second = freeze_game_format(db_session, game, frozen_by_user_id=judge.id)
    assert first.id == second.id
    db_session.rollback()

    headers = scenario.headers_for(scenario.judge_id)
    assert api_client.post(f"{API_PREFIX}/games/{scenario.game_id}/start", headers=headers).status_code == 200
    db_session.expire_all()
    snapshot_id = db_session.scalar(
        select(GameFormatSnapshot.id).where(GameFormatSnapshot.game_id == scenario.game_id)
    )
    cancelled = api_client.post(
        f"{API_PREFIX}/games/{scenario.game_id}/cancel",
        json={"reason": "Weather interruption"},
        headers=scenario.headers_for(scenario.admin_id),
    )
    assert cancelled.status_code == 200
    assert db_session.scalar(
        select(GameFormatSnapshot.id).where(GameFormatSnapshot.game_id == scenario.game_id)
    ) == snapshot_id
    assert db_session.scalar(
        select(func.count(GameFormatRoleSnapshot.id)).where(
            GameFormatRoleSnapshot.format_snapshot_id == snapshot_id
        )
    ) == 2


def test_snapshot_has_no_mutation_api(api_client: TestClient) -> None:
    paths = api_client.app.openapi()["paths"]
    assert all("format-snapshot" not in path for path in paths)


def test_cancel_before_start_does_not_create_snapshot(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session)
    response = api_client.post(
        f"{API_PREFIX}/games/{scenario.game_id}/cancel",
        json={"reason": "Cancelled before seating"},
        headers=scenario.headers_for(scenario.admin_id),
    )
    assert response.status_code == 200
    assert response.json()["has_format_snapshot"] is False
    assert db_session.scalar(
        select(func.count(GameFormatSnapshot.id)).where(GameFormatSnapshot.game_id == scenario.game_id)
    ) == 0
