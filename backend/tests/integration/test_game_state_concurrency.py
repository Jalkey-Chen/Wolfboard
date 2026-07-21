"""PostgreSQL row-lock regressions for play/result state races."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event

from fastapi import HTTPException
import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.enums import GamePlayStatus, GameResultStatus
from app.models.audit_log import AuditLog
from app.models.game import Game
from app.models.game_status_history import GameStatusHistory
from app.models.result_confirmation import ResultConfirmation
from app.models.user import User
from app.schemas.game_result import GameResultDraftWrite
from app.services.game import get_game_or_404
from app.services.game_result import get_game_result_or_404, save_game_result_draft, submit_game_result
from app.services.game_review import get_review_game_or_404, reject_game_result
from app.services.game_state import cancel_game, end_game, start_game
from tests.integration.result_support import API_PREFIX, create_result_scenario, save_and_submit


pytestmark = pytest.mark.integration


def _run_play_action(
    session_factory: sessionmaker[Session],
    *,
    game_id: int,
    user_id: int,
    action: str,
    loaded: Event,
) -> int | str:
    with session_factory() as session:
        game = get_game_or_404(session, game_id)
        user = session.get(User, user_id)
        assert user is not None
        loaded.set()
        try:
            if action == "start":
                start_game(session, game, user)
            elif action == "end":
                end_game(session, game, user)
            else:
                cancel_game(session, game, user, reason="Concurrent cancellation")
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


@pytest.mark.parametrize("losing_action", ["start", "cancel"])
def test_concurrent_start_allows_one_play_transition(
    db_session: Session,
    test_session_factory: sessionmaker[Session],
    losing_action: str,
) -> None:
    scenario = create_result_scenario(db_session)

    with test_session_factory() as winning_session:
        game = get_game_or_404(winning_session, scenario.game_id)
        judge = winning_session.get(User, scenario.judge_id)
        assert judge is not None
        winning_session.execute(select(Game).where(Game.id == scenario.game_id).with_for_update()).scalar_one()

        loaded = Event()
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                _run_play_action,
                test_session_factory,
                game_id=scenario.game_id,
                user_id=scenario.admin_id,
                action=losing_action,
                loaded=loaded,
            )
            assert loaded.wait(timeout=5)
            assert not future.done()
            start_game(winning_session, game, judge)
            assert future.result(timeout=5) == 409

    db_session.expire_all()
    game = db_session.get(Game, scenario.game_id)
    assert game is not None and game.play_status == GamePlayStatus.IN_PROGRESS
    assert db_session.scalar(
        select(func.count(GameStatusHistory.id)).where(GameStatusHistory.game_id == scenario.game_id)
    ) == 1
    assert db_session.scalar(
        select(func.count(AuditLog.id)).where(AuditLog.entity_id == scenario.game_id)
    ) == 1


def test_concurrent_end_and_cancel_allows_one_play_transition(
    db_session: Session,
    test_session_factory: sessionmaker[Session],
) -> None:
    scenario = create_result_scenario(db_session)
    with test_session_factory() as setup_session:
        game = get_game_or_404(setup_session, scenario.game_id)
        judge = setup_session.get(User, scenario.judge_id)
        assert judge is not None
        start_game(setup_session, game, judge)

    with test_session_factory() as winning_session:
        game = get_game_or_404(winning_session, scenario.game_id)
        judge = winning_session.get(User, scenario.judge_id)
        assert judge is not None
        winning_session.execute(select(Game).where(Game.id == scenario.game_id).with_for_update()).scalar_one()
        loaded = Event()
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                _run_play_action,
                test_session_factory,
                game_id=scenario.game_id,
                user_id=scenario.admin_id,
                action="cancel",
                loaded=loaded,
            )
            assert loaded.wait(timeout=5)
            end_game(winning_session, game, judge)
            assert future.result(timeout=5) == 409

    db_session.expire_all()
    game = db_session.get(Game, scenario.game_id)
    assert game is not None and game.play_status == GamePlayStatus.ENDED
    assert game.cancelled_at is None
    assert db_session.scalar(
        select(func.count(GameStatusHistory.id)).where(GameStatusHistory.game_id == scenario.game_id)
    ) == 2


def test_concurrent_submit_and_cancel_allows_one_cross_scope_transition(
    api_client,
    db_session: Session,
    test_session_factory: sessionmaker[Session],
) -> None:
    scenario = create_result_scenario(db_session)
    saved = api_client.put(
        f"{API_PREFIX}/games/{scenario.game_id}/result-draft",
        json=scenario.valid_draft(),
        headers=scenario.headers_for(scenario.judge_id),
    )
    assert saved.status_code == 200

    with test_session_factory() as winning_session:
        game = get_game_result_or_404(winning_session, scenario.game_id)
        judge = winning_session.get(User, scenario.judge_id)
        assert judge is not None
        winning_session.execute(select(Game).where(Game.id == scenario.game_id).with_for_update()).scalar_one()
        loaded = Event()
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                _run_play_action,
                test_session_factory,
                game_id=scenario.game_id,
                user_id=scenario.admin_id,
                action="cancel",
                loaded=loaded,
            )
            assert loaded.wait(timeout=5)
            submit_game_result(winning_session, game, judge)
            assert future.result(timeout=5) == 409

    db_session.expire_all()
    game = db_session.get(Game, scenario.game_id)
    assert game is not None
    assert (game.play_status, game.result_status) == (GamePlayStatus.ENDED, GameResultStatus.SUBMITTED)
    assert game.cancelled_at is None
    assert db_session.scalar(
        select(func.count(GameStatusHistory.id)).where(GameStatusHistory.game_id == scenario.game_id)
    ) == 4
    assert db_session.scalar(
        select(func.count(AuditLog.id)).where(AuditLog.entity_id == scenario.game_id)
    ) == 2


def test_concurrent_reject_and_draft_save_uses_one_submitted_version(
    api_client,
    db_session: Session,
    test_session_factory: sessionmaker[Session],
) -> None:
    scenario = create_result_scenario(db_session)
    save_and_submit(api_client, scenario, scenario.game_id)

    with test_session_factory() as winning_session:
        game = get_review_game_or_404(winning_session, scenario.game_id)
        admin = winning_session.get(User, scenario.admin_id)
        assert admin is not None
        winning_session.execute(select(Game).where(Game.id == scenario.game_id).with_for_update()).scalar_one()
        loaded = Event()
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                _run_draft_save,
                test_session_factory,
                game_id=scenario.game_id,
                judge_id=scenario.judge_id,
                payload=scenario.valid_draft(),
                loaded=loaded,
            )
            assert loaded.wait(timeout=5)
            reject_game_result(winning_session, game, admin, comment="Winning rejection")
            assert future.result(timeout=5) == 409

    db_session.expire_all()
    game = db_session.get(Game, scenario.game_id)
    assert game is not None
    assert (game.play_status, game.result_status) == (GamePlayStatus.ENDED, GameResultStatus.REJECTED)
    assert db_session.scalar(
        select(func.count(ResultConfirmation.id)).where(ResultConfirmation.game_id == scenario.game_id)
    ) == 1
    assert db_session.scalar(
        select(func.count(GameStatusHistory.id)).where(GameStatusHistory.game_id == scenario.game_id)
    ) == 5
    assert db_session.scalar(
        select(func.count(AuditLog.id)).where(AuditLog.entity_id == scenario.game_id)
    ) == 3
