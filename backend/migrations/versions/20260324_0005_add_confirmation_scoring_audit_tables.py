"""Add confirmation, scoring, audit-log, and game-status-history tables.

Revision ID: 20260324_0005
Revises: 20260324_0004
Create Date: 2026-03-24 22:20:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260324_0005"
down_revision = "20260324_0004"
branch_labels = None
depends_on = None


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
result_confirmation_status = sa.Enum(
    "submitted",
    "approved",
    "rejected",
    "revised",
    name="result_confirmation_status",
    native_enum=False,
)
score_log_source_type = sa.Enum(
    "game_result",
    "admin_adjustment",
    "rollback",
    name="score_log_source_type",
    native_enum=False,
)
score_log_effective_status = sa.Enum(
    "pending",
    "effective",
    "voided",
    name="score_log_effective_status",
    native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("action_type", sa.String(length=50), nullable=False),
        sa.Column("old_value_json", sa.JSON(), nullable=True),
        sa.Column("new_value_json", sa.JSON(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_action_type"), "audit_logs", ["action_type"], unique=False)
    op.create_index(op.f("ix_audit_logs_actor_user_id"), "audit_logs", ["actor_user_id"], unique=False)
    op.create_index(op.f("ix_audit_logs_created_at"), "audit_logs", ["created_at"], unique=False)
    op.create_index(op.f("ix_audit_logs_entity_id"), "audit_logs", ["entity_id"], unique=False)
    op.create_index(op.f("ix_audit_logs_entity_type"), "audit_logs", ["entity_type"], unique=False)

    op.create_table(
        "game_status_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("old_status", game_status, nullable=True),
        sa.Column("new_status", game_status, nullable=False),
        sa.Column("changed_by", sa.Integer(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["changed_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_game_status_history_changed_by"), "game_status_history", ["changed_by"], unique=False)
    op.create_index(op.f("ix_game_status_history_game_id"), "game_status_history", ["game_id"], unique=False)

    op.create_table(
        "result_confirmations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("submitted_by", sa.Integer(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_by", sa.Integer(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmation_status", result_confirmation_status, nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["confirmed_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["submitted_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_result_confirmations_confirmation_status"), "result_confirmations", ["confirmation_status"], unique=False)
    op.create_index(op.f("ix_result_confirmations_game_id"), "result_confirmations", ["game_id"], unique=False)

    op.create_table(
        "score_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("source_type", score_log_source_type, server_default="game_result", nullable=False),
        sa.Column("delta", sa.Float(), nullable=False),
        sa.Column("balance_after", sa.Float(), server_default="0", nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("effective_status", score_log_effective_status, server_default="effective", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_score_logs_effective_status"), "score_logs", ["effective_status"], unique=False)
    op.create_index(op.f("ix_score_logs_game_id"), "score_logs", ["game_id"], unique=False)
    op.create_index(op.f("ix_score_logs_source_type"), "score_logs", ["source_type"], unique=False)
    op.create_index(op.f("ix_score_logs_user_id"), "score_logs", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_score_logs_user_id"), table_name="score_logs")
    op.drop_index(op.f("ix_score_logs_source_type"), table_name="score_logs")
    op.drop_index(op.f("ix_score_logs_game_id"), table_name="score_logs")
    op.drop_index(op.f("ix_score_logs_effective_status"), table_name="score_logs")
    op.drop_table("score_logs")

    op.drop_index(op.f("ix_result_confirmations_game_id"), table_name="result_confirmations")
    op.drop_index(op.f("ix_result_confirmations_confirmation_status"), table_name="result_confirmations")
    op.drop_table("result_confirmations")

    op.drop_index(op.f("ix_game_status_history_game_id"), table_name="game_status_history")
    op.drop_index(op.f("ix_game_status_history_changed_by"), table_name="game_status_history")
    op.drop_table("game_status_history")

    op.drop_index(op.f("ix_audit_logs_entity_type"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_entity_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_created_at"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_actor_user_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_action_type"), table_name="audit_logs")
    op.drop_table("audit_logs")
