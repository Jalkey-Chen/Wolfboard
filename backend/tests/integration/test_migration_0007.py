"""Upgrade, backfill, constraint, and downgrade coverage for game participants."""

from pathlib import Path

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.core.enums import GameStatus
from tests.integration.result_support import create_additional_game, create_result_scenario


pytestmark = pytest.mark.integration
BACKEND_ROOT = Path(__file__).resolve().parents[2]
REVISION = "20260721_0007"
PREVIOUS_REVISION = "20260721_0006"


def _alembic_config(engine: Engine) -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", engine.url.render_as_string(hide_password=False))
    return config


def _insert_legacy_results(session: Session, game_id: int, user_one_id: int, user_two_id: int, actor_id: int) -> None:
    session.execute(
        text(
            """
            INSERT INTO game_players (
                id, game_id, user_id, seat_number, role_name, faction,
                final_status, is_winner, base_score, adjustment_score, final_score,
                remarks
            ) VALUES
                (101, :game_id, :user_one_id, 1, 'Seer', 'GOOD', 'ALIVE', true, 1.0, 0.25, 1.25, 'complete'),
                (102, :game_id, NULL, 2, 'Guest', 'GOOD', 'UNKNOWN', NULL, 0.0, 0.0, 0.0, 'null user'),
                (103, :game_id, :user_two_id, NULL, 'Werewolf', 'WOLF', 'ELIMINATED', false, 0.0, 0.0, 0.0, 'null seat')
            """
        ),
        {"game_id": game_id, "user_one_id": user_one_id, "user_two_id": user_two_id},
    )
    session.execute(
        text(
            """
            INSERT INTO score_adjustments (
                id, game_player_id, adjustment_type, delta, reason, created_by
            ) VALUES (201, 101, 'JUDGE_BONUS', 0.25, 'legacy bonus', :actor_id)
            """
        ),
        {"actor_id": actor_id},
    )
    session.execute(
        text(
            """
            INSERT INTO score_logs (
                id, user_id, game_id, source_type, delta, balance_after,
                note, effective_status
            ) VALUES (301, :user_id, :game_id, 'GAME_RESULT', 1.25, 1.25, 'legacy score', 'EFFECTIVE')
            """
        ),
        {"user_id": user_one_id, "game_id": game_id},
    )
    session.commit()


def test_migration_0007_backfills_and_round_trips_legacy_results(
    test_engine: Engine,
    test_session_factory: sessionmaker[Session],
    clean_database: None,
) -> None:
    _ = clean_database
    config = _alembic_config(test_engine)

    try:
        command.downgrade(config, PREVIOUS_REVISION)
        assert "game_participants" not in inspect(test_engine).get_table_names()
        with test_session_factory() as session:
            scenario = create_result_scenario(session, game_status=GameStatus.CONFIRMED)
            empty_game_id = create_additional_game(session, scenario, status=GameStatus.REVISED)
            _insert_legacy_results(
                session,
                scenario.game_id,
                scenario.player_one_id,
                scenario.player_two_id,
                scenario.judge_id,
            )
            original_score_log = session.execute(
                text("SELECT user_id, game_id, delta, balance_after, effective_status FROM score_logs WHERE id = 301")
            ).one()

        command.upgrade(config, REVISION)
        inspector = inspect(test_engine)
        assert "game_participants" in inspector.get_table_names()
        assert "participant_id" in {column["name"] for column in inspector.get_columns("game_players")}
        assert "user_id" not in {column["name"] for column in inspector.get_columns("game_players")}
        assert "seat_number" not in {column["name"] for column in inspector.get_columns("game_players")}

        with test_session_factory() as session:
            participants = session.execute(
                text(
                    """
                    SELECT id, game_id, user_id, seat_number, display_name_snapshot
                    FROM game_participants
                    ORDER BY id
                    """
                )
            ).mappings().all()
            assert [participant["id"] for participant in participants] == [101, 102, 103]
            assert participants[0]["display_name_snapshot"] == "Player One"
            assert participants[1]["user_id"] is None
            assert participants[1]["seat_number"] == 2
            assert participants[2]["user_id"] == scenario.player_two_id
            assert participants[2]["seat_number"] is None
            assert session.scalar(text("SELECT COUNT(*) FROM game_participants WHERE game_id = :game_id"), {"game_id": empty_game_id}) == 0
            assert session.scalar(text("SELECT COUNT(*) FROM game_players WHERE participant_id IS NULL")) == 0
            assert session.execute(
                text("SELECT id, game_player_id, delta, reason FROM score_adjustments WHERE id = 201")
            ).one() == (201, 101, 0.25, "legacy bonus")
            assert session.execute(
                text("SELECT user_id, game_id, delta, balance_after, effective_status FROM score_logs WHERE id = 301")
            ).one() == original_score_log

            participant_only_id = session.scalar(
                text(
                    """
                    INSERT INTO game_participants (
                        game_id, user_id, seat_number, display_name_snapshot
                    ) VALUES (:game_id, :user_id, 7, 'Participant Only')
                    RETURNING id
                    """
                ),
                {"game_id": empty_game_id, "user_id": scenario.replacement_player_id},
            )
            session.commit()

            with pytest.raises(IntegrityError), session.begin_nested():
                session.execute(
                    text("INSERT INTO game_players (game_id, participant_id) VALUES (:game_id, 101)"),
                    {"game_id": scenario.game_id},
                )
                session.flush()
            with pytest.raises(IntegrityError), session.begin_nested():
                session.execute(
                    text("INSERT INTO game_players (game_id, participant_id) VALUES (:game_id, 101)"),
                    {"game_id": empty_game_id},
                )
                session.flush()
            with pytest.raises(IntegrityError), session.begin_nested():
                session.execute(
                    text(
                        """
                        INSERT INTO game_participants (game_id, user_id, seat_number)
                        VALUES (:game_id, :user_id, 3), (:game_id, :user_id, 4)
                        """
                    ),
                    {"game_id": scenario.game_id, "user_id": scenario.replacement_player_id},
                )
                session.flush()
            with pytest.raises(IntegrityError), session.begin_nested():
                session.execute(
                    text(
                        """
                        INSERT INTO game_participants (game_id, seat_number)
                        VALUES (:game_id, 5), (:game_id, 5)
                        """
                    ),
                    {"game_id": scenario.game_id},
                )
                session.flush()

        command.downgrade(config, PREVIOUS_REVISION)
        with test_session_factory() as session:
            flattened = session.execute(
                text("SELECT id, user_id, seat_number FROM game_players WHERE id IN (101, 102, 103) ORDER BY id")
            ).all()
            assert flattened == [
                (101, scenario.player_one_id, 1),
                (102, None, 2),
                (103, scenario.player_two_id, None),
            ]
            assert session.execute(
                text(
                    """
                    SELECT user_id, seat_number
                    FROM game_players
                    WHERE game_id = :game_id AND user_id = :user_id
                    """
                ),
                {"game_id": empty_game_id, "user_id": scenario.replacement_player_id},
            ).one() == (scenario.replacement_player_id, 7)
            assert session.execute(
                text("SELECT id, game_player_id, delta, reason FROM score_adjustments WHERE id = 201")
            ).one() == (201, 101, 0.25, "legacy bonus")
            assert session.execute(
                text("SELECT user_id, game_id, delta, balance_after, effective_status FROM score_logs WHERE id = 301")
            ).one() == original_score_log

        command.upgrade(config, REVISION)
        with test_session_factory() as session:
            assert session.scalar(text("SELECT COUNT(*) FROM game_players WHERE participant_id IS NULL")) == 0
            assert session.scalar(text("SELECT COUNT(*) FROM game_participants")) == 4
    finally:
        command.upgrade(config, "head")
