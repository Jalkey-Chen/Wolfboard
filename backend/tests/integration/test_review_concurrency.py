"""PostgreSQL locking regressions for concurrent admin review actions."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event

from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.enums import ScoreLogEffectiveStatus
from app.models.audit_log import AuditLog
from app.models.game import Game
from app.models.game_status_history import GameStatusHistory
from app.models.result_confirmation import ResultConfirmation
from app.models.score_log import ScoreLog
from app.models.user import User
from app.schemas.game_review import GameRevisionWrite
from app.services.game_review import (
    confirm_game_result,
    get_review_game_or_404,
    reject_game_result,
    revise_game_result,
)
from tests.integration.result_support import create_result_scenario, save_and_submit


pytestmark = pytest.mark.integration


def _run_losing_action(
    session_factory: sessionmaker[Session],
    *,
    game_id: int,
    admin_id: int,
    action: str,
    revision_payload: dict[str, object],
    loaded: Event,
) -> int | str:
    with session_factory() as session:
        game = get_review_game_or_404(session, game_id)
        admin = session.get(User, admin_id)
        assert admin is not None
        loaded.set()
        try:
            if action == "confirm":
                confirm_game_result(session, game, admin, comment="Concurrent confirmation")
            elif action == "reject":
                reject_game_result(session, game, admin, comment="Concurrent rejection")
            else:
                revise_game_result(
                    session,
                    game,
                    GameRevisionWrite.model_validate(
                        {**revision_payload, "reason": "Concurrent revision"}
                    ),
                    admin,
                )
        except HTTPException as exc:
            return exc.status_code
        return "success"


@pytest.mark.parametrize("losing_action", ["confirm", "reject", "revise"])
def test_concurrent_review_actions_allow_only_one_submitted_version_winner(
    api_client: TestClient,
    db_session: Session,
    test_session_factory: sessionmaker[Session],
    losing_action: str,
) -> None:
    scenario = create_result_scenario(db_session)
    save_and_submit(api_client, scenario, scenario.game_id)

    with test_session_factory() as winning_session:
        winning_game = get_review_game_or_404(winning_session, scenario.game_id)
        winning_admin = winning_session.get(User, scenario.admin_id)
        assert winning_admin is not None
        winning_session.execute(
            select(Game).where(Game.id == scenario.game_id).with_for_update()
        ).scalar_one()

        loaded = Event()
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                _run_losing_action,
                test_session_factory,
                game_id=scenario.game_id,
                admin_id=scenario.admin_id,
                action=losing_action,
                revision_payload=scenario.valid_draft(),
                loaded=loaded,
            )
            assert loaded.wait(timeout=5)
            assert not future.done()

            confirm_game_result(
                winning_session,
                winning_game,
                winning_admin,
                comment="Winning confirmation",
            )
            assert future.result(timeout=5) == 409

    db_session.expire_all()
    assert db_session.scalar(
        select(func.count(ResultConfirmation.id)).where(
            ResultConfirmation.game_id == scenario.game_id
        )
    ) == 1
    assert db_session.scalar(
        select(func.count(GameStatusHistory.id)).where(
            GameStatusHistory.game_id == scenario.game_id
        )
    ) == 1
    assert db_session.scalar(
        select(func.count(AuditLog.id)).where(AuditLog.entity_id == scenario.game_id)
    ) == 1
    effective_logs = list(
        db_session.scalars(
            select(ScoreLog).where(
                ScoreLog.game_id == scenario.game_id,
                ScoreLog.effective_status == ScoreLogEffectiveStatus.EFFECTIVE,
            )
        )
    )
    assert len(effective_logs) == 2
    assert len({log.user_id for log in effective_logs}) == 2
