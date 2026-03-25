"""Add game formats, format roles, and games tables.

Revision ID: 20260324_0003
Revises: 20260324_0002
Create Date: 2026-03-24 23:15:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260324_0003"
down_revision = "20260324_0002"
branch_labels = None
depends_on = None


format_category = sa.Enum("standard", "special", "fun", name="format_category", native_enum=False)
format_role_faction = sa.Enum(
    "good",
    "wolf",
    "third_party",
    "special",
    name="format_role_faction",
    native_enum=False,
)
game_type = sa.Enum("official", "fun", "practice", name="game_type", native_enum=False)
game_status = sa.Enum(
    "draft",
    "in_progress",
    "submitted",
    "confirmed",
    "revised",
    "cancelled",
    name="game_status",
    native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "game_formats",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("format_name", sa.String(length=120), nullable=False),
        sa.Column("format_key", sa.String(length=120), nullable=False),
        sa.Column("player_count", sa.Integer(), nullable=False),
        sa.Column("category", format_category, server_default="standard", nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_system_preset", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_game_formats_format_key"), "game_formats", ["format_key"], unique=True)
    op.create_index(op.f("ix_game_formats_format_name"), "game_formats", ["format_name"], unique=False)
    op.create_index(op.f("ix_game_formats_player_count"), "game_formats", ["player_count"], unique=False)
    op.create_index(op.f("ix_game_formats_category"), "game_formats", ["category"], unique=False)
    op.create_index(op.f("ix_game_formats_is_active"), "game_formats", ["is_active"], unique=False)

    op.create_table(
        "format_roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("format_id", sa.Integer(), nullable=False),
        sa.Column("role_name", sa.String(length=120), nullable=False),
        sa.Column("faction", format_role_faction, server_default="good", nullable=False),
        sa.Column("role_count", sa.Integer(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["format_id"], ["game_formats.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_format_roles_faction"), "format_roles", ["faction"], unique=False)
    op.create_index(op.f("ix_format_roles_format_id"), "format_roles", ["format_id"], unique=False)

    op.create_table(
        "games",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_day_id", sa.Integer(), nullable=False),
        sa.Column("game_number", sa.Integer(), nullable=False),
        sa.Column("table_number", sa.Integer(), nullable=False),
        sa.Column("format_id", sa.Integer(), nullable=False),
        sa.Column("judge_user_id", sa.Integer(), nullable=False),
        sa.Column("game_type", game_type, server_default="official", nullable=False),
        sa.Column("status", game_status, server_default="draft", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_by", sa.Integer(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_by", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["confirmed_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["event_day_id"], ["event_days.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["format_id"], ["game_formats.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["judge_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["submitted_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "event_day_id",
            "table_number",
            "game_number",
            name="uq_games_event_day_id_table_number_game_number",
        ),
    )
    op.create_index(op.f("ix_games_event_day_id"), "games", ["event_day_id"], unique=False)
    op.create_index(op.f("ix_games_game_number"), "games", ["game_number"], unique=False)
    op.create_index(op.f("ix_games_table_number"), "games", ["table_number"], unique=False)
    op.create_index(op.f("ix_games_format_id"), "games", ["format_id"], unique=False)
    op.create_index(op.f("ix_games_judge_user_id"), "games", ["judge_user_id"], unique=False)
    op.create_index(op.f("ix_games_game_type"), "games", ["game_type"], unique=False)
    op.create_index(op.f("ix_games_status"), "games", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_games_status"), table_name="games")
    op.drop_index(op.f("ix_games_game_type"), table_name="games")
    op.drop_index(op.f("ix_games_judge_user_id"), table_name="games")
    op.drop_index(op.f("ix_games_format_id"), table_name="games")
    op.drop_index(op.f("ix_games_table_number"), table_name="games")
    op.drop_index(op.f("ix_games_game_number"), table_name="games")
    op.drop_index(op.f("ix_games_event_day_id"), table_name="games")
    op.drop_table("games")
    op.drop_index(op.f("ix_format_roles_format_id"), table_name="format_roles")
    op.drop_index(op.f("ix_format_roles_faction"), table_name="format_roles")
    op.drop_table("format_roles")
    op.drop_index(op.f("ix_game_formats_is_active"), table_name="game_formats")
    op.drop_index(op.f("ix_game_formats_category"), table_name="game_formats")
    op.drop_index(op.f("ix_game_formats_player_count"), table_name="game_formats")
    op.drop_index(op.f("ix_game_formats_format_name"), table_name="game_formats")
    op.drop_index(op.f("ix_game_formats_format_key"), table_name="game_formats")
    op.drop_table("game_formats")
