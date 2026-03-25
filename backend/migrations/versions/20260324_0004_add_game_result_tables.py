"""Add game result draft tables.

Revision ID: 20260324_0004
Revises: 20260324_0003
Create Date: 2026-03-24 23:59:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260324_0004"
down_revision = "20260324_0003"
branch_labels = None
depends_on = None


game_player_faction = sa.Enum("good", "wolf", "third_party", name="game_player_faction", native_enum=False)
game_player_final_status = sa.Enum(
    "alive",
    "eliminated",
    "unknown",
    name="game_player_final_status",
    native_enum=False,
)
score_adjustment_type = sa.Enum(
    "late_penalty",
    "conduct_penalty",
    "judge_bonus",
    "manual_adjustment",
    name="score_adjustment_type",
    native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "game_players",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("seat_number", sa.Integer(), nullable=True),
        sa.Column("role_name", sa.String(length=120), nullable=True),
        sa.Column("faction", game_player_faction, nullable=True),
        sa.Column("final_status", game_player_final_status, server_default="unknown", nullable=False),
        sa.Column("is_winner", sa.Boolean(), nullable=True),
        sa.Column("base_score", sa.Float(), server_default="0", nullable=False),
        sa.Column("adjustment_score", sa.Float(), server_default="0", nullable=False),
        sa.Column("final_score", sa.Float(), server_default="0", nullable=False),
        sa.Column("judge_bonus_note", sa.Text(), nullable=True),
        sa.Column("penalty_note", sa.Text(), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("game_id", "seat_number", name="uq_game_players_game_id_seat_number"),
        sa.UniqueConstraint("game_id", "user_id", name="uq_game_players_game_id_user_id"),
    )
    op.create_index(op.f("ix_game_players_game_id"), "game_players", ["game_id"], unique=False)
    op.create_index(op.f("ix_game_players_user_id"), "game_players", ["user_id"], unique=False)
    op.create_index(op.f("ix_game_players_faction"), "game_players", ["faction"], unique=False)
    op.create_index(op.f("ix_game_players_final_status"), "game_players", ["final_status"], unique=False)

    op.create_table(
        "score_adjustments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("game_player_id", sa.Integer(), nullable=False),
        sa.Column("adjustment_type", score_adjustment_type, nullable=False),
        sa.Column("delta", sa.Float(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["game_player_id"], ["game_players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_score_adjustments_game_player_id"), "score_adjustments", ["game_player_id"], unique=False)
    op.create_index(op.f("ix_score_adjustments_adjustment_type"), "score_adjustments", ["adjustment_type"], unique=False)
    op.create_index(op.f("ix_score_adjustments_created_by"), "score_adjustments", ["created_by"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_score_adjustments_created_by"), table_name="score_adjustments")
    op.drop_index(op.f("ix_score_adjustments_adjustment_type"), table_name="score_adjustments")
    op.drop_index(op.f("ix_score_adjustments_game_player_id"), table_name="score_adjustments")
    op.drop_table("score_adjustments")
    op.drop_index(op.f("ix_game_players_final_status"), table_name="game_players")
    op.drop_index(op.f("ix_game_players_faction"), table_name="game_players")
    op.drop_index(op.f("ix_game_players_user_id"), table_name="game_players")
    op.drop_index(op.f("ix_game_players_game_id"), table_name="game_players")
    op.drop_table("game_players")
