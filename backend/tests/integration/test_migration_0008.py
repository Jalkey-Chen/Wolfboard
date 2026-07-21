"""Legacy state mapping and round-trip coverage for the dual-state migration."""

from pathlib import Path

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import Engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker


pytestmark = pytest.mark.integration
BACKEND_ROOT = Path(__file__).resolve().parents[2]
REVISION = "20260722_0008"
PREVIOUS_REVISION = "20260721_0007"


def _config(engine: Engine) -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", engine.url.render_as_string(hide_password=False))
    return config


def _insert_legacy_state_matrix(session: Session) -> None:
    session.execute(
        text(
            """
            INSERT INTO users (id, username, display_name, password_hash)
            VALUES (1, 'legacy-admin', 'Legacy Admin', 'unused'),
                   (2, 'legacy-judge', 'Legacy Judge', 'unused'),
                   (3, 'legacy-player', 'Legacy Player', 'unused');
            INSERT INTO seasons (id, name, start_date, end_date, created_by)
            VALUES (1, 'Legacy Season', '2026-01-01', '2026-12-31', 1);
            INSERT INTO event_days (id, season_id, title, event_date, venue, created_by)
            VALUES (1, 1, 'Legacy Day', '2026-06-01', 'Legacy Venue', 1);
            INSERT INTO game_formats (id, format_name, format_key, player_count)
            VALUES (1, 'Legacy Format', 'legacy-format', 2);
            INSERT INTO games (
                id, event_day_id, game_number, table_number, format_id,
                judge_user_id, game_type, status, submitted_at, submitted_by,
                confirmed_at, confirmed_by
            ) VALUES
                (1, 1, 1, 1, 1, 2, 'OFFICIAL', 'DRAFT', NULL, NULL, NULL, NULL),
                (2, 1, 2, 1, 1, 2, 'OFFICIAL', 'DRAFT', NULL, NULL, NULL, NULL),
                (3, 1, 3, 1, 1, 2, 'OFFICIAL', 'IN_PROGRESS', NULL, NULL, NULL, NULL),
                (4, 1, 4, 1, 1, 2, 'OFFICIAL', 'SUBMITTED', now(), 2, NULL, NULL),
                (5, 1, 5, 1, 1, 2, 'OFFICIAL', 'CONFIRMED', now(), 2, now(), 1),
                (6, 1, 6, 1, 1, 2, 'OFFICIAL', 'REVISED', now(), 2, now(), 1),
                (7, 1, 7, 1, 1, 2, 'OFFICIAL', 'CANCELLED', NULL, NULL, NULL, NULL),
                (8, 1, 8, 1, 1, 2, 'OFFICIAL', 'CANCELLED', NULL, NULL, NULL, NULL),
                (9, 1, 9, 1, 1, 2, 'OFFICIAL', 'CANCELLED', now(), 2, NULL, NULL),
                (10, 1, 10, 1, 1, 2, 'OFFICIAL', 'CANCELLED', now(), 2, now(), 1),
                (11, 1, 11, 1, 1, 2, 'OFFICIAL', 'CANCELLED', now(), 2, now(), 1);
            INSERT INTO game_participants (id, game_id, user_id, seat_number, display_name_snapshot)
            VALUES (20, 2, 3, 1, 'Legacy Player'),
                   (21, 8, 3, 1, 'Legacy Player');
            INSERT INTO game_players (
                id, game_id, participant_id, role_name, faction, final_status,
                is_winner, base_score, adjustment_score, final_score
            ) VALUES
                (30, 2, 20, 'Seer', 'GOOD', 'ALIVE', true, 1, 0.25, 1.25),
                (31, 8, 21, 'Seer', 'GOOD', 'ALIVE', true, 1, 0, 1);
            INSERT INTO score_adjustments (
                id, game_player_id, adjustment_type, delta, reason, created_by
            ) VALUES (40, 30, 'JUDGE_BONUS', 0.25, 'legacy adjustment', 2);
            INSERT INTO result_confirmations (
                id, game_id, submitted_by, submitted_at, confirmed_by,
                confirmed_at, confirmation_status, comment
            ) VALUES
                (50, 10, 2, now(), 1, now(), 'APPROVED', 'legacy approval'),
                (51, 11, 2, now(), 1, now(), 'APPROVED', 'older approval'),
                (52, 11, 2, now(), 1, now() + interval '1 minute', 'REVISED', 'latest revision');
            INSERT INTO score_logs (
                id, user_id, game_id, source_type, delta, balance_after,
                effective_status
            ) VALUES
                (60, 3, 10, 'GAME_RESULT', 1, 1, 'EFFECTIVE'),
                (61, 3, 11, 'GAME_RESULT', 1.5, 2.5, 'EFFECTIVE');
            INSERT INTO game_status_history (
                id, game_id, old_status, new_status, changed_by, reason
            ) VALUES
                (70, 5, 'SUBMITTED', 'CONFIRMED', 1, 'approved'),
                (71, 8, 'SUBMITTED', 'DRAFT', 1, 'rejected');
            """
        )
    )
    session.commit()


def test_migration_0008_maps_all_legacy_states_and_round_trips(
    test_engine: Engine,
    test_session_factory: sessionmaker[Session],
    clean_database: None,
) -> None:
    _ = clean_database
    config = _config(test_engine)
    try:
        command.downgrade(config, PREVIOUS_REVISION)
        with test_session_factory() as session:
            _insert_legacy_state_matrix(session)
        command.upgrade(config, REVISION)

        columns = {column["name"] for column in inspect(test_engine).get_columns("games")}
        assert "status" not in columns
        assert {"play_status", "result_status", "cancelled_at", "cancelled_by", "cancellation_reason"} <= columns
        with test_session_factory() as session:
            mapped = dict(
                session.execute(
                    text("SELECT id, play_status || '/' || result_status FROM games ORDER BY id")
                ).all()
            )
            assert mapped == {
                1: "scheduled/empty",
                2: "scheduled/draft",
                3: "in_progress/draft",
                4: "ended/submitted",
                5: "ended/confirmed",
                6: "ended/revised",
                7: "cancelled/empty",
                8: "cancelled/draft",
                9: "cancelled/submitted",
                10: "cancelled/confirmed",
                11: "cancelled/revised",
            }
            assert session.scalar(text("SELECT COUNT(*) FROM games WHERE play_status IS NULL OR result_status IS NULL")) == 0
            assert session.scalar(text("SELECT COUNT(*) FROM games WHERE play_status = 'ended' AND (started_at IS NULL OR ended_at IS NULL)")) == 0
            assert session.scalar(text("SELECT COUNT(*) FROM games WHERE play_status = 'cancelled' AND cancellation_reason IS NULL")) == 0
            assert session.execute(
                text("SELECT status_scope, transition_key, old_status, new_status FROM game_status_history WHERE id = 70")
            ).one() == ("result", "confirm_result", "submitted", "confirmed")
            assert session.execute(
                text("SELECT status_scope, transition_key, old_status, new_status FROM game_status_history WHERE id = 71")
            ).one() == ("result", "reject_result", "submitted", "rejected")
            assert session.execute(text("SELECT id, game_player_id, delta FROM score_adjustments WHERE id = 40")).one() == (40, 30, 0.25)
            assert session.execute(text("SELECT id, participant_id FROM game_players ORDER BY id")).all() == [(30, 20), (31, 21)]
            assert session.execute(text("SELECT id, delta, balance_after FROM score_logs ORDER BY id")).all() == [(60, 1.0, 1.0), (61, 1.5, 2.5)]

        command.downgrade(config, PREVIOUS_REVISION)
        with test_session_factory() as session:
            legacy = dict(session.execute(text("SELECT id, lower(status) FROM games ORDER BY id")).all())
            assert legacy[1] == "draft"
            assert legacy[3] == "in_progress"
            assert legacy[4] == "submitted"
            assert legacy[5] == "confirmed"
            assert legacy[6] == "revised"
            assert all(legacy[game_id] == "cancelled" for game_id in range(7, 12))
            assert session.scalar(text("SELECT COUNT(*) FROM games WHERE status IS NULL")) == 0

        command.upgrade(config, REVISION)
        with test_session_factory() as session:
            assert session.scalar(text("SELECT COUNT(*) FROM games WHERE play_status IS NULL OR result_status IS NULL")) == 0
            assert session.execute(text("SELECT id, participant_id FROM game_players ORDER BY id")).all() == [(30, 20), (31, 21)]
    finally:
        command.upgrade(config, "head")
