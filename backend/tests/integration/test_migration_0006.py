"""Upgrade and downgrade coverage for the effective score-log constraint."""

from pathlib import Path

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import Engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

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
            session.execute(
                text(
                    """
                    INSERT INTO users (id, username, display_name, password_hash)
                    VALUES (1, 'migration-admin', 'Migration Admin', 'unused'),
                           (2, 'migration-judge', 'Migration Judge', 'unused'),
                           (3, 'migration-player', 'Migration Player', 'unused');
                    INSERT INTO seasons (id, name, start_date, end_date, created_by)
                    VALUES (1, 'Migration Season', '2026-01-01', '2026-12-31', 1);
                    INSERT INTO event_days (id, season_id, title, event_date, venue, created_by)
                    VALUES (1, 1, 'Migration Day', '2026-06-01', 'Migration Venue', 1);
                    INSERT INTO game_formats (id, format_name, format_key, player_count)
                    VALUES (1, 'Migration Format', 'migration-format', 2);
                    INSERT INTO games (
                        id, event_day_id, game_number, table_number, format_id,
                        judge_user_id, game_type, status
                    ) VALUES (1, 1, 1, 1, 1, 2, 'OFFICIAL', 'DRAFT');
                    INSERT INTO score_logs (
                        id, user_id, game_id, source_type, delta, balance_after,
                        effective_status, note
                    ) VALUES (1, 3, 1, 'GAME_RESULT', 1, 1, 'EFFECTIVE', 'Legal pre-migration row');
                    """
                )
            )
            session.commit()

        command.upgrade(config, "head")
        assert INDEX_NAME in _score_log_index_names(test_engine)
    finally:
        command.upgrade(config, "head")
