"""Backfill and round-trip coverage for immutable game format snapshots."""

from pathlib import Path

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import Engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker


pytestmark = pytest.mark.integration
BACKEND_ROOT = Path(__file__).resolve().parents[2]
REVISION = "20260722_0009"
PREVIOUS_REVISION = "20260722_0008"


def _config(engine: Engine) -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", engine.url.render_as_string(hide_password=False))
    return config


def _insert_0008_matrix(session: Session) -> None:
    session.execute(text("""
        INSERT INTO users (id, username, display_name, password_hash)
        VALUES (1, 'snapshot-admin', 'Snapshot Admin', 'unused'),
               (2, 'snapshot-judge', 'Snapshot Judge', 'unused'),
               (3, 'snapshot-player', 'Snapshot Player', 'unused');
        INSERT INTO seasons (id, name, start_date, end_date, created_by)
        VALUES (1, 'Snapshot Season', '2026-01-01', '2026-12-31', 1);
        INSERT INTO event_days (id, season_id, title, event_date, venue, created_by)
        VALUES (1, 1, 'Snapshot Day', '2026-06-01', 'Snapshot Venue', 1);
        INSERT INTO game_formats (
            id, format_name, format_key, player_count, category, description,
            is_active, is_system_preset, updated_at
        ) VALUES (
            1, 'Migration Format', 'migration-format', 2, 'STANDARD',
            'Migration description', true, false, '2026-01-10T00:00:00Z'
        );
        INSERT INTO format_roles (
            id, format_id, role_name, faction, role_count, display_order, metadata_json
        ) VALUES
            (11, 1, 'Seer', 'GOOD', 1, 2, '{"night_order": 2}'),
            (12, 1, 'Werewolf', 'WOLF', 1, 1, NULL);
        INSERT INTO games (
            id, event_day_id, game_number, table_number, format_id, judge_user_id,
            game_type, play_status, result_status, started_at, ended_at,
            submitted_at, submitted_by, confirmed_at, confirmed_by,
            cancelled_at, cancellation_reason, created_at, updated_at
        ) VALUES
            (1,1,1,1,1,2,'OFFICIAL','scheduled','empty',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-01-01','2026-01-02'),
            (2,1,2,1,1,2,'OFFICIAL','scheduled','draft',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-01-01','2026-01-02'),
            (3,1,3,1,1,2,'OFFICIAL','in_progress','draft','2026-02-01',NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-01-01','2026-01-02'),
            (4,1,4,1,1,2,'OFFICIAL','ended','submitted','2026-02-01','2026-02-02','2026-02-03',2,NULL,NULL,NULL,NULL,'2026-01-01','2026-01-02'),
            (5,1,5,1,1,2,'OFFICIAL','ended','confirmed','2026-02-01','2026-02-02','2026-02-03',2,'2026-02-04',1,NULL,NULL,'2026-01-01','2026-01-02'),
            (6,1,6,1,1,2,'OFFICIAL','ended','revised','2026-02-01','2026-02-02','2026-02-03',2,'2026-02-04',1,NULL,NULL,'2026-01-01','2026-01-02'),
            (7,1,7,1,1,2,'OFFICIAL','cancelled','empty',NULL,NULL,NULL,NULL,NULL,NULL,'2026-02-05','Never started','2026-01-01','2026-01-02'),
            (8,1,8,1,1,2,'OFFICIAL','cancelled','empty','2026-02-01',NULL,NULL,NULL,NULL,NULL,'2026-02-05','Started then cancelled','2026-01-01','2026-01-02'),
            (9,1,9,1,1,2,'OFFICIAL','cancelled','draft',NULL,NULL,NULL,NULL,NULL,NULL,'2026-02-05','Result evidence','2026-01-01','2026-01-02'),
            (10,1,10,1,1,2,'OFFICIAL','scheduled','empty',NULL,NULL,'2026-02-03',2,NULL,NULL,NULL,NULL,'2026-01-01','2026-01-02');
        INSERT INTO game_participants (id, game_id, user_id, seat_number, display_name_snapshot)
        VALUES (20, 5, 3, 1, 'Snapshot Player');
        INSERT INTO game_players (
            id, game_id, participant_id, role_name, faction, final_status,
            is_winner, base_score, adjustment_score, final_score
        ) VALUES (30, 5, 20, 'Seer', 'GOOD', 'ALIVE', true, 1, 0.25, 1.25);
        INSERT INTO score_adjustments (
            id, game_player_id, adjustment_type, delta, reason, created_by
        ) VALUES (40, 30, 'JUDGE_BONUS', 0.25, 'migration adjustment', 2);
        INSERT INTO score_logs (
            id, user_id, game_id, source_type, delta, balance_after, effective_status
        ) VALUES (50, 3, 5, 'GAME_RESULT', 1.25, 1.25, 'EFFECTIVE');
        INSERT INTO game_status_history (
            id, game_id, status_scope, transition_key, old_status, new_status, changed_by
        ) VALUES (60, 5, 'result', 'confirm_result', 'submitted', 'confirmed', 1);
        INSERT INTO audit_logs (
            id, actor_user_id, entity_type, entity_id, action_type
        ) VALUES (70, 1, 'game', 5, 'confirm_result');
    """))
    session.commit()


def test_migration_0009_backfills_evidence_games_and_round_trips(
    test_engine: Engine,
    test_session_factory: sessionmaker[Session],
    clean_database: None,
) -> None:
    _ = clean_database
    config = _config(test_engine)
    try:
        command.downgrade(config, PREVIOUS_REVISION)
        with test_session_factory() as session:
            _insert_0008_matrix(session)
        command.upgrade(config, REVISION)

        assert {"game_format_snapshots", "game_format_role_snapshots"} <= set(inspect(test_engine).get_table_names())
        with test_session_factory() as session:
            assert session.scalars(text("SELECT game_id FROM game_format_snapshots ORDER BY game_id")).all() == [2, 3, 4, 5, 6, 8, 9, 10]
            assert session.scalar(text("SELECT COUNT(*) FROM game_format_snapshots")) == 8
            assert session.scalar(text("SELECT COUNT(*) FROM game_format_role_snapshots")) == 16
            assert session.execute(text("""
                SELECT snapshot.snapshot_origin, snapshot.frozen_by_user_id,
                       snapshot.frozen_at = game.started_at
                FROM game_format_snapshots snapshot
                JOIN games game ON game.id = snapshot.game_id
                WHERE game.id = 3
            """)).one() == ("legacy_backfill", None, True)
            assert session.execute(text("""
                SELECT role_name, faction, role_count, display_order, metadata_json
                FROM game_format_role_snapshots
                WHERE format_snapshot_id = (SELECT id FROM game_format_snapshots WHERE game_id = 3)
                ORDER BY display_order, id
            """)).all() == [
                ("Werewolf", "WOLF", 1, 1, None),
                ("Seer", "GOOD", 1, 2, {"night_order": 2}),
            ]
            preserved = session.execute(text("""
                SELECT
                    (SELECT COUNT(*) FROM game_participants),
                    (SELECT COUNT(*) FROM game_players),
                    (SELECT COUNT(*) FROM score_adjustments),
                    (SELECT COUNT(*) FROM score_logs),
                    (SELECT COUNT(*) FROM game_status_history),
                    (SELECT COUNT(*) FROM audit_logs)
            """)).one()

        command.downgrade(config, PREVIOUS_REVISION)
        assert "game_format_snapshots" not in inspect(test_engine).get_table_names()
        with test_session_factory() as session:
            assert session.execute(text("""
                SELECT
                    (SELECT COUNT(*) FROM game_participants),
                    (SELECT COUNT(*) FROM game_players),
                    (SELECT COUNT(*) FROM score_adjustments),
                    (SELECT COUNT(*) FROM score_logs),
                    (SELECT COUNT(*) FROM game_status_history),
                    (SELECT COUNT(*) FROM audit_logs)
            """)).one() == preserved

        command.upgrade(config, REVISION)
        with test_session_factory() as session:
            assert session.scalar(text("SELECT COUNT(*) FROM game_format_snapshots")) == 8
            assert session.scalar(text("""
                SELECT COUNT(*) FROM (
                    SELECT game_id FROM game_format_snapshots GROUP BY game_id HAVING COUNT(*) <> 1
                ) invalid
            """)) == 0
    finally:
        command.upgrade(config, "head")
