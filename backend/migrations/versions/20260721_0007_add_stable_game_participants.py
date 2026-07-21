"""Add stable game participants and backfill existing result rows.

Revision ID: 20260721_0007
Revises: 20260721_0006
Create Date: 2026-07-21 20:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260721_0007"
down_revision = "20260721_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "game_participants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("seat_number", sa.Integer(), nullable=True),
        sa.Column("display_name_snapshot", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("game_id", "seat_number", name="uq_game_participants_game_id_seat_number"),
        sa.UniqueConstraint("game_id", "user_id", name="uq_game_participants_game_id_user_id"),
        sa.UniqueConstraint("id", "game_id", name="uq_game_participants_id_game_id"),
    )
    op.create_index("ix_game_participants_game_id", "game_participants", ["game_id"])
    op.create_index("ix_game_participants_user_id", "game_participants", ["user_id"])
    op.create_index("ix_game_participants_game_id_seat_number", "game_participants", ["game_id", "seat_number"])

    op.add_column("game_players", sa.Column("participant_id", sa.Integer(), nullable=True))
    op.execute(
        """
        INSERT INTO game_participants (
            id, game_id, user_id, seat_number, display_name_snapshot, created_at, updated_at
        )
        SELECT
            gp.id,
            gp.game_id,
            gp.user_id,
            gp.seat_number,
            u.display_name,
            gp.created_at,
            gp.updated_at
        FROM game_players AS gp
        LEFT JOIN users AS u ON u.id = gp.user_id
        """
    )
    op.execute("UPDATE game_players SET participant_id = id")
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM game_players WHERE participant_id IS NULL) THEN
                RAISE EXCEPTION 'Cannot migrate game_players without participants';
            END IF;
        END $$
        """
    )
    op.execute(
        """
        SELECT setval(
            pg_get_serial_sequence('game_participants', 'id'),
            COALESCE((SELECT MAX(id) FROM game_participants), 1),
            EXISTS (SELECT 1 FROM game_participants)
        )
        """
    )

    op.alter_column("game_players", "participant_id", nullable=False)
    op.create_index("ix_game_players_participant_id", "game_players", ["participant_id"])
    op.create_unique_constraint("uq_game_players_participant_id", "game_players", ["participant_id"])
    op.create_foreign_key(
        "fk_game_players_participant_game",
        "game_players",
        "game_participants",
        ["participant_id", "game_id"],
        ["id", "game_id"],
        ondelete="CASCADE",
    )

    op.drop_constraint("uq_game_players_game_id_seat_number", "game_players", type_="unique")
    op.drop_constraint("uq_game_players_game_id_user_id", "game_players", type_="unique")
    op.drop_index("ix_game_players_user_id", table_name="game_players")
    op.drop_constraint("game_players_user_id_fkey", "game_players", type_="foreignkey")
    op.drop_column("game_players", "seat_number")
    op.drop_column("game_players", "user_id")


def downgrade() -> None:
    # Although the current result API always creates a result with a participant,
    # preserve participant-only rows as blank legacy results during downgrade.
    op.execute(
        """
        INSERT INTO game_players (
            game_id, participant_id, role_name, faction, final_status,
            is_winner, base_score, adjustment_score, final_score, remarks
        )
        SELECT
            participant.game_id,
            participant.id,
            NULL,
            NULL,
            'UNKNOWN',
            NULL,
            0,
            0,
            0,
            'Created while downgrading a participant without a result row.'
        FROM game_participants AS participant
        LEFT JOIN game_players AS gp ON gp.participant_id = participant.id
        WHERE gp.id IS NULL
        """
    )
    op.add_column("game_players", sa.Column("user_id", sa.Integer(), nullable=True))
    op.add_column("game_players", sa.Column("seat_number", sa.Integer(), nullable=True))
    op.execute(
        """
        UPDATE game_players AS gp
        SET user_id = participant.user_id,
            seat_number = participant.seat_number
        FROM game_participants AS participant
        WHERE participant.id = gp.participant_id
          AND participant.game_id = gp.game_id
        """
    )
    op.create_foreign_key(
        "game_players_user_id_fkey",
        "game_players",
        "users",
        ["user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_game_players_user_id", "game_players", ["user_id"])
    op.create_unique_constraint("uq_game_players_game_id_user_id", "game_players", ["game_id", "user_id"])
    op.create_unique_constraint("uq_game_players_game_id_seat_number", "game_players", ["game_id", "seat_number"])

    op.drop_constraint("fk_game_players_participant_game", "game_players", type_="foreignkey")
    op.drop_constraint("uq_game_players_participant_id", "game_players", type_="unique")
    op.drop_index("ix_game_players_participant_id", table_name="game_players")
    op.drop_column("game_players", "participant_id")

    op.drop_index("ix_game_participants_game_id_seat_number", table_name="game_participants")
    op.drop_index("ix_game_participants_user_id", table_name="game_participants")
    op.drop_index("ix_game_participants_game_id", table_name="game_participants")
    op.drop_table("game_participants")
