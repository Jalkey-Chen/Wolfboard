"""Database enforcement for the effective game-result ledger invariant."""

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.enums import ScoreLogEffectiveStatus, ScoreLogSourceType
from app.models.score_log import ScoreLog
from tests.integration.result_support import confirm, create_result_scenario, save_and_submit


pytestmark = pytest.mark.integration


def test_database_rejects_duplicate_effective_game_result_log(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session)
    save_and_submit(api_client, scenario, scenario.game_id)
    confirm(api_client, scenario, scenario.game_id)

    duplicate = ScoreLog(
        user_id=scenario.player_one_id,
        game_id=scenario.game_id,
        source_type=ScoreLogSourceType.GAME_RESULT,
        delta=99.0,
        balance_after=99.0,
        effective_status=ScoreLogEffectiveStatus.EFFECTIVE,
        note="Must be rejected by the partial unique index",
    )
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
