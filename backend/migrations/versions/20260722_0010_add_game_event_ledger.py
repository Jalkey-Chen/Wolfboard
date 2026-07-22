"""Add the structured per-game event ledger.

Revision ID: 20260722_0010
Revises: 20260722_0009
Create Date: 2026-07-22 08:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260722_0010"
down_revision = "20260722_0009"
branch_labels = None
depends_on = None


game_event_phase = sa.Enum("night", "day", name="game_event_phase", native_enum=False)
game_event_visibility = sa.Enum(
    "public", "postgame_full", "judge_only",
    name="game_event_visibility", native_enum=False,
)
game_event_source = sa.Enum(
    "manual", "system", "imported",
    name="game_event_source", native_enum=False,
)
game_event_status = sa.Enum(
    "active", "superseded", "voided",
    name="game_event_status", native_enum=False,
)


def upgrade() -> None:
    op.add_column(
        "games",
        sa.Column("next_event_sequence", sa.Integer(), server_default="1", nullable=False),
    )
    op.create_check_constraint(
        "ck_games_next_event_sequence",
        "games",
        "next_event_sequence >= 1",
    )

    op.create_table(
        "game_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("logical_sequence_no", sa.Integer(), nullable=False),
        sa.Column("phase", game_event_phase, nullable=False),
        sa.Column("round_no", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("actor_participant_id", sa.Integer(), nullable=True),
        sa.Column("target_participant_id", sa.Integer(), nullable=True),
        sa.Column("secondary_target_participant_id", sa.Integer(), nullable=True),
        sa.Column(
            "payload_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("visibility", game_event_visibility, nullable=False),
        sa.Column("source", game_event_source, nullable=False),
        sa.Column("schema_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("status", game_event_status, server_default="active", nullable=False),
        sa.Column("supersedes_event_id", sa.Integer(), nullable=True),
        sa.Column("revision_reason", sa.Text(), nullable=True),
        sa.Column("invalidated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("invalidated_by_user_id", sa.Integer(), nullable=True),
        sa.Column("invalidation_reason", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("client_event_id", sa.String(length=120), nullable=True),
        sa.CheckConstraint("sequence_no >= 1", name="ck_game_events_sequence_no"),
        sa.CheckConstraint("logical_sequence_no >= 1", name="ck_game_events_logical_sequence_no"),
        sa.CheckConstraint("round_no >= 1", name="ck_game_events_round_no"),
        sa.CheckConstraint("schema_version >= 1", name="ck_game_events_schema_version"),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["actor_participant_id", "game_id"],
            ["game_participants.id", "game_participants.game_id"],
            name="fk_game_events_actor_participant_game",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["target_participant_id", "game_id"],
            ["game_participants.id", "game_participants.game_id"],
            name="fk_game_events_target_participant_game",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["secondary_target_participant_id", "game_id"],
            ["game_participants.id", "game_participants.game_id"],
            name="fk_game_events_secondary_target_participant_game",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_event_id", "game_id"],
            ["game_events.id", "game_events.game_id"],
            name="fk_game_events_supersedes_event_game",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["invalidated_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "game_id", name="uq_game_events_id_game_id"),
        sa.UniqueConstraint("game_id", "sequence_no", name="uq_game_events_game_id_sequence_no"),
        sa.UniqueConstraint("game_id", "client_event_id", name="uq_game_events_game_id_client_event_id"),
    )
    op.create_index("ix_game_events_game_sequence", "game_events", ["game_id", "sequence_no"])
    op.create_index(
        "ix_game_events_game_logical_sequence",
        "game_events",
        ["game_id", "logical_sequence_no"],
    )
    op.create_index("ix_game_events_game_status", "game_events", ["game_id", "status"])
    op.create_index(
        "ix_game_events_game_phase_round",
        "game_events",
        ["game_id", "phase", "round_no"],
    )
    op.create_index(
        "uq_game_events_active_logical_sequence",
        "game_events",
        ["game_id", "logical_sequence_no"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    op.drop_index("uq_game_events_active_logical_sequence", table_name="game_events")
    op.drop_index("ix_game_events_game_phase_round", table_name="game_events")
    op.drop_index("ix_game_events_game_status", table_name="game_events")
    op.drop_index("ix_game_events_game_logical_sequence", table_name="game_events")
    op.drop_index("ix_game_events_game_sequence", table_name="game_events")
    op.drop_table("game_events")
    op.drop_constraint("ck_games_next_event_sequence", "games", type_="check")
    op.drop_column("games", "next_event_sequence")
