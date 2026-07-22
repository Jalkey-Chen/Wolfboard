"""PostgreSQL locking regressions for concurrent event-ledger writes."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from threading import Event

from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.enums import GameEventStatus, GameResultStatus
from app.models.audit_log import AuditLog
from app.models.game import Game
from app.models.game_event import GameEvent
from app.models.user import User
from app.schemas.game_event import GameEventCorrection, GameEventCreate
from app.schemas.game_result import GameResultDraftWrite
from app.services.game_event import append_game_event, correct_game_event, void_game_event
from app.services.game_result import get_game_result_or_404, save_game_result_draft, submit_game_result
from tests.integration.result_support import API_PREFIX, create_result_scenario


pytestmark = pytest.mark.integration


def _event_payload(
    *,
    event_type: str = "phase_started",
    client_event_id: str | None = None,
    target_participant_id: int | None = None,
) -> dict[str, object]:
    return {
        "phase": "night",
        "round_no": 1,
        "event_type": event_type,
        "actor_participant_id": None,
        "target_participant_id": target_participant_id,
        "secondary_target_participant_id": None,
        "payload": {},
        "occurred_at": None,
        "client_event_id": client_event_id,
    }


def _run_append(
    session_factory: sessionmaker[Session],
    *,
    game_id: int,
    user_id: int,
    payload: dict[str, object],
    loaded: Event,
) -> int | str:
    with session_factory() as session:
        user = session.get(User, user_id)
        assert user is not None
        loaded.set()
        try:
            append_game_event(session, game_id, GameEventCreate.model_validate(payload), user)
        except HTTPException as exc:
            return exc.status_code
        return "success"


def _run_event_mutation(
    session_factory: sessionmaker[Session],
    *,
    game_id: int,
    event_id: int,
    user_id: int,
    action: str,
    loaded: Event,
) -> int | str:
    with session_factory() as session:
        user = session.get(User, user_id)
        assert user is not None
        loaded.set()
        try:
            if action == "correct":
                correct_game_event(
                    session,
                    game_id,
                    event_id,
                    GameEventCorrection.model_validate(
                        {
                            **_event_payload(event_type="phase_completed"),
                            "payload": {"note": "corrected"},
                            "reason": "Concurrent correction",
                        }
                    ),
                    user,
                )
            else:
                void_game_event(session, game_id, event_id, "Concurrent void", user)
        except HTTPException as exc:
            return exc.status_code
        return "success"


def _run_submit(
    session_factory: sessionmaker[Session],
    *,
    game_id: int,
    judge_id: int,
    loaded: Event,
) -> int | str:
    with session_factory() as session:
        game = get_game_result_or_404(session, game_id)
        judge = session.get(User, judge_id)
        assert judge is not None
        loaded.set()
        try:
            submit_game_result(session, game, judge)
        except HTTPException as exc:
            return exc.status_code
        return "success"


def _run_draft_save(
    session_factory: sessionmaker[Session],
    *,
    game_id: int,
    judge_id: int,
    payload: dict[str, object],
    loaded: Event,
) -> int | str:
    with session_factory() as session:
        game = get_game_result_or_404(session, game_id)
        judge = session.get(User, judge_id)
        assert judge is not None
        loaded.set()
        try:
            save_game_result_draft(
                session,
                game,
                GameResultDraftWrite.model_validate(payload),
                judge,
            )
        except HTTPException as exc:
            return exc.status_code
        return "success"


def _prepare_draft(client: TestClient, scenario) -> dict:
    response = client.put(
        f"{API_PREFIX}/games/{scenario.game_id}/result-draft",
        json=scenario.valid_draft(),
        headers=scenario.headers_for(scenario.judge_id),
    )
    assert response.status_code == 200, response.text
    return response.json()


def _lock_game(session: Session, game_id: int) -> None:
    session.execute(select(Game).where(Game.id == game_id).with_for_update()).scalar_one()


def test_concurrent_appends_receive_distinct_monotonic_sequences(
    api_client: TestClient,
    db_session: Session,
    test_session_factory: sessionmaker[Session],
) -> None:
    scenario = create_result_scenario(db_session)
    _prepare_draft(api_client, scenario)

    with test_session_factory() as winning_session:
        judge = winning_session.get(User, scenario.judge_id)
        assert judge is not None
        _lock_game(winning_session, scenario.game_id)
        loaded = Event()
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                _run_append,
                test_session_factory,
                game_id=scenario.game_id,
                user_id=scenario.judge_id,
                payload=_event_payload(client_event_id="parallel-second"),
                loaded=loaded,
            )
            assert loaded.wait(timeout=5)
            assert not future.done()
            append_game_event(
                winning_session,
                scenario.game_id,
                GameEventCreate.model_validate(
                    _event_payload(client_event_id="parallel-first")
                ),
                judge,
            )
            assert future.result(timeout=5) == "success"

    db_session.expire_all()
    events = list(
        db_session.scalars(
            select(GameEvent)
            .where(GameEvent.game_id == scenario.game_id)
            .order_by(GameEvent.sequence_no)
        )
    )
    assert [event.sequence_no for event in events] == [1, 2]
    assert [event.logical_sequence_no for event in events] == [1, 2]
    assert db_session.get(Game, scenario.game_id).next_event_sequence == 3


@pytest.mark.parametrize("same_body", [True, False])
def test_concurrent_client_event_id_is_idempotent_or_conflicts(
    api_client: TestClient,
    db_session: Session,
    test_session_factory: sessionmaker[Session],
    same_body: bool,
) -> None:
    scenario = create_result_scenario(db_session)
    _prepare_draft(api_client, scenario)
    first_payload = _event_payload(client_event_id="retry-key")
    second_payload = first_payload if same_body else _event_payload(
        event_type="phase_completed", client_event_id="retry-key"
    )

    with test_session_factory() as winning_session:
        judge = winning_session.get(User, scenario.judge_id)
        assert judge is not None
        _lock_game(winning_session, scenario.game_id)
        loaded = Event()
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                _run_append,
                test_session_factory,
                game_id=scenario.game_id,
                user_id=scenario.judge_id,
                payload=second_payload,
                loaded=loaded,
            )
            assert loaded.wait(timeout=5)
            append_game_event(
                winning_session,
                scenario.game_id,
                GameEventCreate.model_validate(first_payload),
                judge,
            )
            assert future.result(timeout=5) == ("success" if same_body else 409)

    db_session.expire_all()
    assert db_session.scalar(
        select(func.count(GameEvent.id)).where(GameEvent.game_id == scenario.game_id)
    ) == 1
    assert db_session.get(Game, scenario.game_id).next_event_sequence == 2


def test_concurrent_corrections_create_one_active_logical_version(
    api_client: TestClient,
    db_session: Session,
    test_session_factory: sessionmaker[Session],
) -> None:
    scenario = create_result_scenario(db_session)
    _prepare_draft(api_client, scenario)
    created = api_client.post(
        f"{API_PREFIX}/games/{scenario.game_id}/events",
        json=_event_payload(),
        headers=scenario.headers_for(scenario.judge_id),
    ).json()

    with test_session_factory() as winning_session:
        judge = winning_session.get(User, scenario.judge_id)
        assert judge is not None
        _lock_game(winning_session, scenario.game_id)
        loaded = Event()
        correction = GameEventCorrection.model_validate(
            {
                **_event_payload(event_type="phase_completed"),
                "payload": {"note": "winner"},
                "reason": "Winning correction",
            }
        )
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                _run_event_mutation,
                test_session_factory,
                game_id=scenario.game_id,
                event_id=created["id"],
                user_id=scenario.admin_id,
                action="correct",
                loaded=loaded,
            )
            assert loaded.wait(timeout=5)
            correct_game_event(
                winning_session,
                scenario.game_id,
                created["id"],
                correction,
                judge,
            )
            assert future.result(timeout=5) == 409

    db_session.expire_all()
    assert db_session.scalar(
        select(func.count(GameEvent.id)).where(
            GameEvent.game_id == scenario.game_id,
            GameEvent.status == GameEventStatus.ACTIVE,
            GameEvent.logical_sequence_no == 1,
        )
    ) == 1
    assert db_session.scalar(
        select(func.count(AuditLog.id)).where(
            AuditLog.entity_type == "game_event",
            AuditLog.action_type == "correct",
        )
    ) == 1


@pytest.mark.parametrize("winning_action", ["correct", "void"])
def test_concurrent_correction_and_void_have_one_winner(
    api_client: TestClient,
    db_session: Session,
    test_session_factory: sessionmaker[Session],
    winning_action: str,
) -> None:
    scenario = create_result_scenario(db_session)
    _prepare_draft(api_client, scenario)
    created = api_client.post(
        f"{API_PREFIX}/games/{scenario.game_id}/events",
        json=_event_payload(),
        headers=scenario.headers_for(scenario.judge_id),
    ).json()

    with test_session_factory() as winning_session:
        judge = winning_session.get(User, scenario.judge_id)
        assert judge is not None
        _lock_game(winning_session, scenario.game_id)
        loaded = Event()
        losing_action = "void" if winning_action == "correct" else "correct"
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                _run_event_mutation,
                test_session_factory,
                game_id=scenario.game_id,
                event_id=created["id"],
                user_id=scenario.admin_id,
                action=losing_action,
                loaded=loaded,
            )
            assert loaded.wait(timeout=5)
            if winning_action == "correct":
                correct_game_event(
                    winning_session,
                    scenario.game_id,
                    created["id"],
                    GameEventCorrection.model_validate(
                        {
                            **_event_payload(event_type="phase_completed"),
                            "reason": "Winning correction",
                        }
                    ),
                    judge,
                )
            else:
                void_game_event(
                    winning_session,
                    scenario.game_id,
                    created["id"],
                    "Winning void",
                    judge,
                )
            assert future.result(timeout=5) == 409

    db_session.expire_all()
    active_count = db_session.scalar(
        select(func.count(GameEvent.id)).where(
            GameEvent.game_id == scenario.game_id,
            GameEvent.status == GameEventStatus.ACTIVE,
        )
    )
    assert active_count == (1 if winning_action == "correct" else 0)
    assert db_session.scalar(
        select(func.count(AuditLog.id)).where(AuditLog.entity_type == "game_event")
    ) == 1


def test_event_append_winning_race_prevents_stale_result_submission(
    api_client: TestClient,
    db_session: Session,
    test_session_factory: sessionmaker[Session],
) -> None:
    scenario = create_result_scenario(db_session)
    _prepare_draft(api_client, scenario)

    with test_session_factory() as winning_session:
        judge = winning_session.get(User, scenario.judge_id)
        assert judge is not None
        _lock_game(winning_session, scenario.game_id)
        loaded = Event()
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                _run_submit,
                test_session_factory,
                game_id=scenario.game_id,
                judge_id=scenario.judge_id,
                loaded=loaded,
            )
            assert loaded.wait(timeout=5)
            append_game_event(
                winning_session,
                scenario.game_id,
                GameEventCreate.model_validate(_event_payload()),
                judge,
            )
            assert future.result(timeout=5) == 409

    db_session.expire_all()
    assert db_session.get(Game, scenario.game_id).result_status == GameResultStatus.DRAFT
    assert db_session.scalar(
        select(func.count(GameEvent.id)).where(GameEvent.game_id == scenario.game_id)
    ) == 1


def test_event_append_winning_race_prevents_referenced_participant_deletion(
    api_client: TestClient,
    db_session: Session,
    test_session_factory: sessionmaker[Session],
) -> None:
    scenario = create_result_scenario(db_session)
    saved = _prepare_draft(api_client, scenario)
    removed_participant_id = saved["players"][1]["participant_id"]
    reduced = deepcopy(scenario.valid_draft())
    for request_row, saved_row in zip(reduced["players"], saved["players"], strict=True):
        request_row["participant_id"] = saved_row["participant_id"]
    reduced["players"] = [reduced["players"][0]]
    reduced["adjustments"] = []

    with test_session_factory() as winning_session:
        judge = winning_session.get(User, scenario.judge_id)
        assert judge is not None
        _lock_game(winning_session, scenario.game_id)
        loaded = Event()
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                _run_draft_save,
                test_session_factory,
                game_id=scenario.game_id,
                judge_id=scenario.judge_id,
                payload=reduced,
                loaded=loaded,
            )
            assert loaded.wait(timeout=5)
            append_game_event(
                winning_session,
                scenario.game_id,
                GameEventCreate.model_validate(
                    _event_payload(
                        event_type="wolf_kill_selected",
                        target_participant_id=removed_participant_id,
                    )
                ),
                judge,
            )
            assert future.result(timeout=5) == 409

    db_session.expire_all()
    event = db_session.scalar(
        select(GameEvent).where(GameEvent.game_id == scenario.game_id)
    )
    assert event is not None and event.target_participant_id == removed_participant_id
    assert len(db_session.get(Game, scenario.game_id).participants) == 2
