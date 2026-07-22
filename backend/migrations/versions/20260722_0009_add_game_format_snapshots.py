"""Add immutable per-game format and role snapshots.

Revision ID: 20260722_0009
Revises: 20260722_0008
Create Date: 2026-07-22 04:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260722_0009"
down_revision = "20260722_0008"
branch_labels = None
depends_on = None


format_category = sa.Enum("standard", "special", "fun", name="format_category", native_enum=False)
format_role_faction = sa.Enum(
    "good", "wolf", "third_party", "special",
    name="format_role_faction", native_enum=False,
)
snapshot_origin = sa.Enum(
    "runtime_freeze", "legacy_backfill",
    name="format_snapshot_origin", native_enum=False,
)


ELIGIBLE_GAME_SQL = """
    game.play_status IN ('in_progress', 'ended')
    OR (game.play_status = 'cancelled' AND (
        game.started_at IS NOT NULL OR game.result_status <> 'empty'
    ))
    OR game.result_status <> 'empty'
    OR game.submitted_at IS NOT NULL
    OR game.confirmed_at IS NOT NULL
"""


def upgrade() -> None:
    op.create_table(
        "game_format_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("source_format_id", sa.Integer(), nullable=True),
        sa.Column("format_key", sa.String(length=120), nullable=False),
        sa.Column("format_name", sa.String(length=120), nullable=False),
        sa.Column("player_count", sa.Integer(), nullable=False),
        sa.Column("category", format_category, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_system_preset", sa.Boolean(), nullable=False),
        sa.Column("source_format_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("snapshot_origin", snapshot_origin, nullable=False),
        sa.Column("snapshot_schema_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("frozen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("frozen_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "snapshot_schema_version >= 1",
            name="ck_game_format_snapshots_schema_version",
        ),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_format_id"], ["game_formats.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["frozen_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("game_id", name="uq_game_format_snapshots_game_id"),
    )
    op.create_index("ix_game_format_snapshots_game_id", "game_format_snapshots", ["game_id"])
    op.create_index("ix_game_format_snapshots_source_format_id", "game_format_snapshots", ["source_format_id"])
    op.create_index("ix_game_format_snapshots_frozen_by_user_id", "game_format_snapshots", ["frozen_by_user_id"])

    op.create_table(
        "game_format_role_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("format_snapshot_id", sa.Integer(), nullable=False),
        sa.Column("source_format_role_id", sa.Integer(), nullable=True),
        sa.Column("role_name", sa.String(length=120), nullable=False),
        sa.Column("faction", format_role_faction, nullable=False),
        sa.Column("role_count", sa.Integer(), nullable=False),
        sa.Column("display_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["format_snapshot_id"], ["game_format_snapshots.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["source_format_role_id"], ["format_roles.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_game_format_role_snapshots_format_snapshot_id",
        "game_format_role_snapshots",
        ["format_snapshot_id"],
    )
    op.create_index(
        "ix_game_format_role_snapshots_source_format_role_id",
        "game_format_role_snapshots",
        ["source_format_role_id"],
    )
    op.create_index(
        "ix_game_format_role_snapshots_order",
        "game_format_role_snapshots",
        ["format_snapshot_id", "display_order"],
    )

    # An eligible game without its source format cannot be explained safely.
    op.execute(
        f"""
        DO $$
        DECLARE missing_game_id integer;
        BEGIN
            SELECT game.id INTO missing_game_id
            FROM games AS game
            LEFT JOIN game_formats AS source ON source.id = game.format_id
            WHERE ({ELIGIBLE_GAME_SQL}) AND source.id IS NULL
            ORDER BY game.id
            LIMIT 1;
            IF missing_game_id IS NOT NULL THEN
                RAISE EXCEPTION 'Cannot backfill format snapshot: game_id % has no source GameFormat', missing_game_id;
            END IF;
        END $$;
        """
    )
    op.execute(
        f"""
        INSERT INTO game_format_snapshots (
            game_id, source_format_id, format_key, format_name, player_count,
            category, description, is_system_preset, source_format_updated_at,
            snapshot_origin, snapshot_schema_version, frozen_at
        )
        SELECT
            game.id, source.id, source.format_key, source.format_name, source.player_count,
            source.category, source.description, source.is_system_preset, source.updated_at,
            'legacy_backfill', 1,
            COALESCE(
                game.started_at, game.ended_at, game.submitted_at, game.confirmed_at,
                game.updated_at, game.created_at
            )
        FROM games AS game
        JOIN game_formats AS source ON source.id = game.format_id
        WHERE {ELIGIBLE_GAME_SQL}
        ORDER BY game.id
        """
    )
    op.execute(
        """
        INSERT INTO game_format_role_snapshots (
            format_snapshot_id, source_format_role_id, role_name, faction,
            role_count, display_order, metadata_json
        )
        SELECT
            snapshot.id, role.id, role.role_name, role.faction,
            role.role_count, role.display_order, role.metadata_json
        FROM game_format_snapshots AS snapshot
        JOIN format_roles AS role ON role.format_id = snapshot.source_format_id
        ORDER BY snapshot.id, role.display_order, role.id
        """
    )
    # Legacy rows are copied verbatim. NOT VALID keeps a historically invalid
    # role count inspectable while enforcing the invariant for all future rows.
    op.execute(
        """
        ALTER TABLE game_format_role_snapshots
        ADD CONSTRAINT ck_game_format_role_snapshots_role_count
        CHECK (role_count > 0) NOT VALID
        """
    )


def downgrade() -> None:
    op.drop_index("ix_game_format_role_snapshots_order", table_name="game_format_role_snapshots")
    op.drop_index("ix_game_format_role_snapshots_source_format_role_id", table_name="game_format_role_snapshots")
    op.drop_index("ix_game_format_role_snapshots_format_snapshot_id", table_name="game_format_role_snapshots")
    op.drop_table("game_format_role_snapshots")
    op.drop_index("ix_game_format_snapshots_frozen_by_user_id", table_name="game_format_snapshots")
    op.drop_index("ix_game_format_snapshots_source_format_id", table_name="game_format_snapshots")
    op.drop_index("ix_game_format_snapshots_game_id", table_name="game_format_snapshots")
    op.drop_table("game_format_snapshots")
