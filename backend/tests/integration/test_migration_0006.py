"""Upgrade and downgrade coverage for the effective score-log constraint."""

from pathlib import Path

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import Engine, inspect
from sqlalchemy.orm import Session, sessionmaker

from app.core.enums import ScoreLogEffectiveStatus, ScoreLogSourceType
from app.models.score_log import ScoreLog
from tests.integration.result_support import create_result_scenario


pytestmark = pytest.mark.integration
INDEX_NAME = "uq_score_logs_effective_game_user_source"
BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _alembic_config(engine: Engine) -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", engine.url.render_as_string(hide_password=False))
    return config


def _score_log_index_names(engine: Engine) -> set[str]:
    return {index["name"] for index in inspect(engine).get_indexes("score_logs")}


def test_migration_0006_round_trip_accepts_existing_legal_data(
    test_engine: Engine,
    test_session_factory: sessionmaker[Session],
    clean_database: None,
) -> None:
    _ = clean_database
    config = _alembic_config(test_engine)
    assert INDEX_NAME in _score_log_index_names(test_engine)

    try:
        command.downgrade(config, "20260324_0005")
        assert INDEX_NAME not in _score_log_index_names(test_engine)

        with test_session_factory() as session:
            scenario = create_result_scenario(session)
            session.add(
                ScoreLog(
                    user_id=scenario.player_one_id,
                    game_id=scenario.game_id,
                    source_type=ScoreLogSourceType.GAME_RESULT,
                    delta=1.0,
                    balance_after=1.0,
                    effective_status=ScoreLogEffectiveStatus.EFFECTIVE,
                    note="Legal pre-migration row",
                )
            )
            session.commit()

        command.upgrade(config, "head")
        assert INDEX_NAME in _score_log_index_names(test_engine)
    finally:
        command.upgrade(config, "head")
