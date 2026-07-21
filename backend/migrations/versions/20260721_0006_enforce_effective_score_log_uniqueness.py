"""Enforce one effective score-log row per game, user, and source.

Revision ID: 20260721_0006
Revises: 20260324_0005
Create Date: 2026-07-21 17:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260721_0006"
down_revision = "20260324_0005"
branch_labels = None
depends_on = None


INDEX_NAME = "uq_score_logs_effective_game_user_source"


def upgrade() -> None:
    op.create_index(
        INDEX_NAME,
        "score_logs",
        ["game_id", "user_id", "source_type"],
        unique=True,
        # SQLAlchemy Enum persists Python member names in the existing ORM,
        # despite the lowercase API values exposed by the str Enum classes.
        postgresql_where=sa.text("effective_status = 'EFFECTIVE'"),
    )


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name="score_logs")
