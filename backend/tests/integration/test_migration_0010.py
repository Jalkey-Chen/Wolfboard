"""PostgreSQL constraint and round-trip coverage for the event-ledger migration."""

from pathlib import Path

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker


pytestmark = pytest.mark.integration
BACKEND_ROOT = Path(__file__).resolve().parents[2]
REVISION = "20260722_0010"
PREVIOUS_REVISION = "20260722_0009"


def _config(engine: Engine) -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", engine.url.render_as_string(hide_password=False))
    return config


def _insert_0009_data(session: Session) -> None:
    session.execute(text("""
        INSERT INTO users (id, username, display_name, password_hash)
        VALUES (1, 'event-admin', 'Event Admin', 'unused'),
               (2, 'event-judge', 'Event Judge', 'unused'),
               (3, 'event-player-one', 'Player One', 'unused'),
               (4, 'event-player-two', 'Player Two', 'unused');
        INSERT INTO seasons (id, name, start_date, end_date, created_by)
        VALUES (1, 'Event Season', '2026-01-01', '2026-12-31', 1);
        INSERT INTO event_days (id, season_id, title, event_date, venue, created_by)
        VALUES (1, 1, 'Event Day', '2026-07-01', 'Event Venue', 1);
        INSERT INTO game_formats (id, format_name, format_key, player_count)
        VALUES (1, 'Event Format', 'event-format', 2);
        INSERT INTO format_roles (id, format_id, role_name, faction, role_count, display_order)
        VALUES (1, 1, 'Seer', 'GOOD', 1, 1), (2, 1, 'Werewolf', 'WOLF', 1, 2);
        INSERT INTO games (
            id, event_day_id, game_number, table_number, format_id, judge_user_id,
            game_type, play_status, result_status, started_at
        ) VALUES
            (1, 1, 1, 1, 1, 2, 'OFFICIAL', 'in_progress', 'draft', now()),
            (2, 1, 2, 1, 1, 2, 'OFFICIAL', 'in_progress', 'draft', now());
        INSERT INTO game_participants (id, game_id, user_id, seat_number, display_name_snapshot)
        VALUES (11, 1, 3, 1, 'Player One'),
               (12, 1, 4, 2, 'Player Two'),
               (21, 2, 3, 1, 'Player One');
        INSERT INTO game_players (
            id, game_id, participant_id, role_name, faction, final_status,
            is_winner, base_score, adjustment_score, final_score
        ) VALUES (31, 1, 11, 'Seer', 'GOOD', 'ALIVE', true, 1, 0, 1);
        INSERT INTO game_format_snapshots (
            id, game_id, source_format_id, format_key, format_name, player_count,
            category, is_system_preset, snapshot_origin, snapshot_schema_version, frozen_at
        ) VALUES
            (41, 1, 1, 'event-format', 'Event Format', 2, 'STANDARD', true, 'runtime_freeze', 1, now()),
            (42, 2, 1, 'event-format', 'Event Format', 2, 'STANDARD', true, 'runtime_freeze', 1, now());
        INSERT INTO game_format_role_snapshots (
            id, format_snapshot_id, source_format_role_id, role_name, faction, role_count, display_order
        ) VALUES (51, 41, 1, 'Seer', 'GOOD', 1, 1), (52, 41, 2, 'Werewolf', 'WOLF', 1, 2);
        INSERT INTO audit_logs (id, actor_user_id, entity_type, entity_id, action_type)
        VALUES (61, 1, 'game', 1, 'start_game');
    """))
    session.commit()


def _insert_event(
    session: Session,
    *,
    event_id: int,
    game_id: int,
    sequence_no: int,
    logical_sequence_no: int,
    status_value: str = "active",
    client_event_id: str | None = None,
    actor_participant_id: int | None = None,
    supersedes_event_id: int | None = None,
    round_no: int = 1,
    schema_version: int = 1,
) -> None:
    session.execute(
        text("""
            INSERT INTO game_events (
                id, game_id, sequence_no, logical_sequence_no, phase, round_no,
                event_type, actor_participant_id, payload_json, visibility,
                source, schema_version, status, supersedes_event_id,
                created_by_user_id, client_event_id
            ) VALUES (
                :id, :game_id, :sequence_no, :logical_sequence_no, 'night', :round_no,
                'phase_started', :actor_participant_id, '{}'::jsonb, 'public',
                'manual', :schema_version, :status_value, :supersedes_event_id,
                2, :client_event_id
            )
        """),
        {
            "id": event_id,
            "game_id": game_id,
            "sequence_no": sequence_no,
            "logical_sequence_no": logical_sequence_no,
            "round_no": round_no,
            "schema_version": schema_version,
            "status_value": status_value,
            "client_event_id": client_event_id,
            "actor_participant_id": actor_participant_id,
            "supersedes_event_id": supersedes_event_id,
        },
    )


def test_migration_0010_constraints_and_round_trip(
    test_engine: Engine,
    test_session_factory: sessionmaker[Session],
    clean_database: None,
) -> None:
    _ = clean_database
    config = _config(test_engine)
    try:
        command.downgrade(config, PREVIOUS_REVISION)
        with test_session_factory() as session:
            _insert_0009_data(session)
        command.upgrade(config, REVISION)

        inspector = inspect(test_engine)
        assert "game_events" in inspector.get_table_names()
        assert "next_event_sequence" in {column["name"] for column in inspector.get_columns("games")}
        with test_session_factory() as session:
            assert session.scalars(text("SELECT next_event_sequence FROM games ORDER BY id")).all() == [1, 1]
            preserved = session.execute(text("""
                SELECT
                    (SELECT COUNT(*) FROM game_participants),
                    (SELECT COUNT(*) FROM game_players),
                    (SELECT COUNT(*) FROM game_format_snapshots),
                    (SELECT COUNT(*) FROM game_format_role_snapshots),
                    (SELECT COUNT(*) FROM audit_logs)
            """)).one()
            _insert_event(
                session,
                event_id=100,
                game_id=1,
                sequence_no=1,
                logical_sequence_no=1,
                client_event_id="migration-event-1",
                actor_participant_id=11,
            )
            session.commit()

            invalid_rows = [
                dict(event_id=101, game_id=1, sequence_no=1, logical_sequence_no=2),
                dict(event_id=102, game_id=1, sequence_no=2, logical_sequence_no=2, client_event_id="migration-event-1"),
                dict(event_id=103, game_id=1, sequence_no=3, logical_sequence_no=1),
                dict(event_id=104, game_id=1, sequence_no=4, logical_sequence_no=4, actor_participant_id=21),
                dict(event_id=105, game_id=1, sequence_no=5, logical_sequence_no=5, supersedes_event_id=200),
                dict(event_id=106, game_id=1, sequence_no=6, logical_sequence_no=6, round_no=0),
                dict(event_id=107, game_id=1, sequence_no=7, logical_sequence_no=7, schema_version=0),
            ]
            _insert_event(session, event_id=200, game_id=2, sequence_no=1, logical_sequence_no=1)
            session.commit()
            for values in invalid_rows:
                with pytest.raises(IntegrityError), session.begin_nested():
                    _insert_event(session, **values)

            _insert_event(
                session,
                event_id=108,
                game_id=1,
                sequence_no=8,
                logical_sequence_no=1,
                status_value="superseded",
            )
            _insert_event(
                session,
                event_id=109,
                game_id=1,
                sequence_no=9,
                logical_sequence_no=1,
                status_value="superseded",
            )
            session.commit()
            assert session.scalar(text("SELECT COUNT(*) FROM game_events WHERE game_id = 1 AND status = 'superseded'")) == 2
            with pytest.raises(IntegrityError), session.begin_nested():
                session.execute(text("DELETE FROM game_participants WHERE id = 11"))
            cascade_check = session.begin_nested()
            session.execute(text("DELETE FROM games WHERE id = 1"))
            assert session.scalar(text("SELECT COUNT(*) FROM game_events WHERE game_id = 1")) == 0
            cascade_check.rollback()

        command.downgrade(config, PREVIOUS_REVISION)
        assert "game_events" not in inspect(test_engine).get_table_names()
        assert "next_event_sequence" not in {column["name"] for column in inspect(test_engine).get_columns("games")}
        with test_session_factory() as session:
            assert session.execute(text("""
                SELECT
                    (SELECT COUNT(*) FROM game_participants),
                    (SELECT COUNT(*) FROM game_players),
                    (SELECT COUNT(*) FROM game_format_snapshots),
                    (SELECT COUNT(*) FROM game_format_role_snapshots),
                    (SELECT COUNT(*) FROM audit_logs)
            """)).one() == preserved

        command.upgrade(config, REVISION)
        with test_session_factory() as session:
            assert session.scalars(text("SELECT next_event_sequence FROM games ORDER BY id")).all() == [1, 1]
            assert session.scalar(text("SELECT COUNT(*) FROM game_events")) == 0
    finally:
        command.upgrade(config, "head")
