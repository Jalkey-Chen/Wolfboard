"""Split game play and result statuses and extend status history.

Revision ID: 20260722_0008
Revises: 20260721_0007
Create Date: 2026-07-22 01:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260722_0008"
down_revision = "20260721_0007"
branch_labels = None
depends_on = None


game_play_status = sa.Enum(
    "scheduled", "in_progress", "ended", "cancelled",
    name="game_play_status", native_enum=False,
)
game_result_status = sa.Enum(
    "empty", "draft", "submitted", "rejected", "confirmed", "revised",
    name="game_result_status", native_enum=False,
)
game_status_scope = sa.Enum("play", "result", name="game_status_scope", native_enum=False)
legacy_game_status = sa.Enum(
    "draft", "in_progress", "submitted", "confirmed", "revised", "cancelled",
    name="game_status", native_enum=False,
)


def upgrade() -> None:
    op.add_column("games", sa.Column("play_status", game_play_status, nullable=True))
    op.add_column("games", sa.Column("result_status", game_result_status, nullable=True))
    op.add_column("games", sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("games", sa.Column("cancelled_by", sa.Integer(), nullable=True))
    op.add_column("games", sa.Column("cancellation_reason", sa.Text(), nullable=True))
    op.create_foreign_key(
        "fk_games_cancelled_by_users",
        "games",
        "users",
        ["cancelled_by"],
        ["id"],
        ondelete="SET NULL",
    )

    op.execute(
        """
        UPDATE games AS game
        SET play_status = CASE lower(game.status)
                WHEN 'draft' THEN 'scheduled'
                WHEN 'in_progress' THEN 'in_progress'
                WHEN 'submitted' THEN 'ended'
                WHEN 'confirmed' THEN 'ended'
                WHEN 'revised' THEN 'ended'
                WHEN 'cancelled' THEN 'cancelled'
            END,
            result_status = CASE lower(game.status)
                WHEN 'draft' THEN CASE
                    WHEN EXISTS (SELECT 1 FROM game_players gp WHERE gp.game_id = game.id) THEN 'draft'
                    ELSE 'empty'
                END
                WHEN 'in_progress' THEN 'draft'
                WHEN 'submitted' THEN 'submitted'
                WHEN 'confirmed' THEN 'confirmed'
                WHEN 'revised' THEN 'revised'
                WHEN 'cancelled' THEN CASE
                    WHEN (
                        SELECT lower(rc.confirmation_status)
                        FROM result_confirmations rc
                        WHERE rc.game_id = game.id
                        ORDER BY COALESCE(rc.confirmed_at, rc.created_at) DESC, rc.id DESC
                        LIMIT 1
                    ) = 'revised' THEN 'revised'
                    WHEN (
                        SELECT lower(rc.confirmation_status)
                        FROM result_confirmations rc
                        WHERE rc.game_id = game.id
                        ORDER BY COALESCE(rc.confirmed_at, rc.created_at) DESC, rc.id DESC
                        LIMIT 1
                    ) = 'approved' THEN 'confirmed'
                    WHEN EXISTS (
                        SELECT 1 FROM score_logs sl
                        WHERE sl.game_id = game.id AND lower(sl.effective_status) = 'effective'
                    ) THEN 'confirmed'
                    WHEN (
                        SELECT lower(rc.confirmation_status)
                        FROM result_confirmations rc
                        WHERE rc.game_id = game.id
                        ORDER BY COALESCE(rc.confirmed_at, rc.created_at) DESC, rc.id DESC
                        LIMIT 1
                    ) = 'rejected' THEN 'rejected'
                    WHEN game.submitted_at IS NOT NULL OR game.submitted_by IS NOT NULL THEN 'submitted'
                    WHEN EXISTS (SELECT 1 FROM game_players gp WHERE gp.game_id = game.id) THEN 'draft'
                    ELSE 'empty'
                END
            END
        """
    )
    op.execute(
        """
        UPDATE games
        SET started_at = COALESCE(started_at, submitted_at, confirmed_at, updated_at, created_at)
        WHERE play_status IN ('in_progress', 'ended') AND started_at IS NULL
        """
    )
    op.execute(
        """
        UPDATE games
        SET ended_at = COALESCE(ended_at, submitted_at, confirmed_at, updated_at, created_at)
        WHERE play_status = 'ended' AND ended_at IS NULL
        """
    )
    op.execute(
        """
        UPDATE games
        SET cancelled_at = COALESCE(ended_at, updated_at, created_at),
            cancellation_reason = 'Migrated from legacy cancelled status'
        WHERE play_status = 'cancelled'
        """
    )
    op.alter_column("games", "play_status", nullable=False, server_default="scheduled")
    op.alter_column("games", "result_status", nullable=False, server_default="empty")
    op.create_index("ix_games_play_status", "games", ["play_status"])
    op.create_index("ix_games_result_status", "games", ["result_status"])
    op.create_index("ix_games_cancelled_by", "games", ["cancelled_by"])

    op.add_column("game_status_history", sa.Column("status_scope", game_status_scope, nullable=True))
    op.add_column("game_status_history", sa.Column("transition_key", sa.String(length=80), nullable=True))
    op.execute(
        """
        UPDATE game_status_history
        SET status_scope = CASE
                WHEN lower(COALESCE(old_status, '')) = 'in_progress'
                  OR lower(new_status) = 'in_progress' THEN 'play'
                ELSE 'result'
            END,
            transition_key = CASE
                WHEN lower(COALESCE(old_status, '')) = 'submitted' AND lower(new_status) = 'draft'
                    THEN 'reject_result'
                WHEN lower(COALESCE(old_status, '')) = 'submitted' AND lower(new_status) = 'confirmed'
                    THEN 'confirm_result'
                WHEN lower(new_status) = 'revised' THEN 'revise_result'
                WHEN lower(new_status) = 'in_progress' THEN 'migrate_legacy_play_history'
                ELSE 'migrate_legacy_result_history'
            END
        """
    )
    op.execute(
        """
        UPDATE game_status_history
        SET old_status = CASE
                WHEN status_scope = 'play' THEN CASE lower(COALESCE(old_status, ''))
                    WHEN 'draft' THEN 'scheduled'
                    WHEN 'in_progress' THEN 'in_progress'
                    WHEN 'cancelled' THEN 'cancelled'
                    ELSE NULL
                END
                ELSE CASE lower(COALESCE(old_status, ''))
                    WHEN '' THEN NULL
                    WHEN 'in_progress' THEN 'draft'
                    ELSE lower(old_status)
                END
            END,
            new_status = CASE
                WHEN status_scope = 'play' THEN CASE lower(new_status)
                    WHEN 'draft' THEN 'scheduled'
                    WHEN 'in_progress' THEN 'in_progress'
                    WHEN 'cancelled' THEN 'cancelled'
                    ELSE 'ended'
                END
                WHEN lower(COALESCE(old_status, '')) = 'submitted' AND lower(new_status) = 'draft'
                    THEN 'rejected'
                WHEN lower(new_status) = 'in_progress' THEN 'draft'
                ELSE lower(new_status)
            END
        """
    )
    op.alter_column("game_status_history", "status_scope", nullable=False)
    op.alter_column("game_status_history", "transition_key", nullable=False)
    op.create_index("ix_game_status_history_status_scope", "game_status_history", ["status_scope"])
    op.create_index("ix_game_status_history_transition_key", "game_status_history", ["transition_key"])

    op.drop_index("ix_games_status", table_name="games")
    op.drop_column("games", "status")


def downgrade() -> None:
    op.add_column("games", sa.Column("status", legacy_game_status, nullable=True))
    op.execute(
        """
        UPDATE games
        SET status = CASE
            WHEN play_status = 'cancelled' THEN 'cancelled'
            WHEN result_status = 'revised' THEN 'revised'
            WHEN result_status = 'confirmed' THEN 'confirmed'
            WHEN result_status = 'submitted' THEN 'submitted'
            WHEN play_status = 'in_progress' THEN 'in_progress'
            ELSE 'draft'
        END
        """
    )
    op.alter_column("games", "status", nullable=False, server_default="draft")
    op.create_index("ix_games_status", "games", ["status"])

    op.execute(
        """
        UPDATE game_status_history
        SET old_status = CASE
                WHEN old_status IS NULL THEN NULL
                WHEN status_scope = 'play' THEN CASE old_status
                    WHEN 'scheduled' THEN 'draft'
                    WHEN 'in_progress' THEN 'in_progress'
                    WHEN 'cancelled' THEN 'cancelled'
                    ELSE 'submitted'
                END
                ELSE CASE old_status
                    WHEN 'empty' THEN 'draft'
                    WHEN 'rejected' THEN 'draft'
                    ELSE old_status
                END
            END,
            new_status = CASE
                WHEN status_scope = 'play' THEN CASE new_status
                    WHEN 'scheduled' THEN 'draft'
                    WHEN 'in_progress' THEN 'in_progress'
                    WHEN 'cancelled' THEN 'cancelled'
                    ELSE 'submitted'
                END
                ELSE CASE new_status
                    WHEN 'empty' THEN 'draft'
                    WHEN 'rejected' THEN 'draft'
                    ELSE new_status
                END
            END
        """
    )
    op.drop_index("ix_game_status_history_transition_key", table_name="game_status_history")
    op.drop_index("ix_game_status_history_status_scope", table_name="game_status_history")
    op.drop_column("game_status_history", "transition_key")
    op.drop_column("game_status_history", "status_scope")

    op.drop_index("ix_games_cancelled_by", table_name="games")
    op.drop_index("ix_games_result_status", table_name="games")
    op.drop_index("ix_games_play_status", table_name="games")
    op.drop_constraint("fk_games_cancelled_by_users", "games", type_="foreignkey")
    op.drop_column("games", "cancellation_reason")
    op.drop_column("games", "cancelled_by")
    op.drop_column("games", "cancelled_at")
    op.drop_column("games", "result_status")
    op.drop_column("games", "play_status")
