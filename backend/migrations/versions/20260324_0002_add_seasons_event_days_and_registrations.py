"""Add seasons, event days, and registrations tables.

Revision ID: 20260324_0002
Revises: 20260324_0001
Create Date: 2026-03-24 22:10:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260324_0002"
down_revision = "20260324_0001"
branch_labels = None
depends_on = None


season_status = sa.Enum("draft", "active", "completed", "archived", name="season_status", native_enum=False)
event_day_category = sa.Enum("official", "fun", "mixed", name="event_day_category", native_enum=False)
event_day_status = sa.Enum(
    "draft",
    "open_for_registration",
    "registration_closed",
    "ongoing",
    "completed",
    "archived",
    name="event_day_status",
    native_enum=False,
)
registration_status = sa.Enum("registered", "waitlisted", "cancelled", name="registration_status", native_enum=False)
check_in_status = sa.Enum("not_checked_in", "checked_in", "absent", name="check_in_status", native_enum=False)
registration_type = sa.Enum("main", "substitute", "guest", name="registration_type", native_enum=False)


def upgrade() -> None:
    op.create_table(
        "seasons",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("status", season_status, server_default="draft", nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_seasons_created_by"), "seasons", ["created_by"], unique=False)
    op.create_index(op.f("ix_seasons_name"), "seasons", ["name"], unique=False)
    op.create_index(op.f("ix_seasons_status"), "seasons", ["status"], unique=False)

    op.create_table(
        "event_days",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("season_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=140), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("venue", sa.String(length=180), nullable=False),
        sa.Column("category", event_day_category, server_default="official", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("registration_open_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("registration_close_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("status", event_day_status, server_default="draft", nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["season_id"], ["seasons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_event_days_category"), "event_days", ["category"], unique=False)
    op.create_index(op.f("ix_event_days_created_by"), "event_days", ["created_by"], unique=False)
    op.create_index(op.f("ix_event_days_event_date"), "event_days", ["event_date"], unique=False)
    op.create_index(op.f("ix_event_days_season_id"), "event_days", ["season_id"], unique=False)
    op.create_index(op.f("ix_event_days_status"), "event_days", ["status"], unique=False)

    op.create_table(
        "registrations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_day_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("registration_status", registration_status, server_default="registered", nullable=False),
        sa.Column("check_in_status", check_in_status, server_default="not_checked_in", nullable=False),
        sa.Column("registration_type", registration_type, server_default="main", nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["event_day_id"], ["event_days.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_day_id", "user_id", name="uq_registrations_event_day_id_user_id"),
    )
    op.create_index(op.f("ix_registrations_check_in_status"), "registrations", ["check_in_status"], unique=False)
    op.create_index(op.f("ix_registrations_event_day_id"), "registrations", ["event_day_id"], unique=False)
    op.create_index(op.f("ix_registrations_registration_status"), "registrations", ["registration_status"], unique=False)
    op.create_index(op.f("ix_registrations_user_id"), "registrations", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_registrations_user_id"), table_name="registrations")
    op.drop_index(op.f("ix_registrations_registration_status"), table_name="registrations")
    op.drop_index(op.f("ix_registrations_event_day_id"), table_name="registrations")
    op.drop_index(op.f("ix_registrations_check_in_status"), table_name="registrations")
    op.drop_table("registrations")
    op.drop_index(op.f("ix_event_days_status"), table_name="event_days")
    op.drop_index(op.f("ix_event_days_season_id"), table_name="event_days")
    op.drop_index(op.f("ix_event_days_event_date"), table_name="event_days")
    op.drop_index(op.f("ix_event_days_created_by"), table_name="event_days")
    op.drop_index(op.f("ix_event_days_category"), table_name="event_days")
    op.drop_table("event_days")
    op.drop_index(op.f("ix_seasons_status"), table_name="seasons")
    op.drop_index(op.f("ix_seasons_name"), table_name="seasons")
    op.drop_index(op.f("ix_seasons_created_by"), table_name="seasons")
    op.drop_table("seasons")
