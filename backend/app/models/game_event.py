"""Append-only structured event versions for one game."""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import GameEventPhase, GameEventSource, GameEventStatus, GameEventVisibility
from app.db.base_class import Base


class GameEvent(Base):
    """One immutable version in a game's structured event ledger."""

    __tablename__ = "game_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["actor_participant_id", "game_id"],
            ["game_participants.id", "game_participants.game_id"],
            name="fk_game_events_actor_participant_game",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["target_participant_id", "game_id"],
            ["game_participants.id", "game_participants.game_id"],
            name="fk_game_events_target_participant_game",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["secondary_target_participant_id", "game_id"],
            ["game_participants.id", "game_participants.game_id"],
            name="fk_game_events_secondary_target_participant_game",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["supersedes_event_id", "game_id"],
            ["game_events.id", "game_events.game_id"],
            name="fk_game_events_supersedes_event_game",
        ),
        UniqueConstraint("id", "game_id", name="uq_game_events_id_game_id"),
        UniqueConstraint("game_id", "sequence_no", name="uq_game_events_game_id_sequence_no"),
        UniqueConstraint("game_id", "client_event_id", name="uq_game_events_game_id_client_event_id"),
        CheckConstraint("sequence_no >= 1", name="ck_game_events_sequence_no"),
        CheckConstraint("logical_sequence_no >= 1", name="ck_game_events_logical_sequence_no"),
        CheckConstraint("round_no >= 1", name="ck_game_events_round_no"),
        CheckConstraint("schema_version >= 1", name="ck_game_events_schema_version"),
        Index("ix_game_events_game_sequence", "game_id", "sequence_no"),
        Index("ix_game_events_game_logical_sequence", "game_id", "logical_sequence_no"),
        Index("ix_game_events_game_status", "game_id", "status"),
        Index("ix_game_events_game_phase_round", "game_id", "phase", "round_no"),
        Index(
            "uq_game_events_active_logical_sequence",
            "game_id",
            "logical_sequence_no",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), nullable=False)
    sequence_no: Mapped[int] = mapped_column(Integer(), nullable=False)
    logical_sequence_no: Mapped[int] = mapped_column(Integer(), nullable=False)
    phase: Mapped[GameEventPhase] = mapped_column(
        SqlEnum(
            GameEventPhase,
            name="game_event_phase",
            native_enum=False,
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
    )
    round_no: Mapped[int] = mapped_column(Integer(), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    actor_participant_id: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    target_participant_id: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    secondary_target_participant_id: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    payload_json: Mapped[dict] = mapped_column(JSONB(), default=dict, server_default="{}", nullable=False)
    visibility: Mapped[GameEventVisibility] = mapped_column(
        SqlEnum(
            GameEventVisibility,
            name="game_event_visibility",
            native_enum=False,
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
    )
    source: Mapped[GameEventSource] = mapped_column(
        SqlEnum(
            GameEventSource,
            name="game_event_source",
            native_enum=False,
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
    )
    schema_version: Mapped[int] = mapped_column(Integer(), default=1, server_default="1", nullable=False)
    status: Mapped[GameEventStatus] = mapped_column(
        SqlEnum(
            GameEventStatus,
            name="game_event_status",
            native_enum=False,
            values_callable=lambda enum: [item.value for item in enum],
        ),
        default=GameEventStatus.ACTIVE,
        server_default=GameEventStatus.ACTIVE.value,
        nullable=False,
    )
    supersedes_event_id: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    revision_reason: Mapped[str | None] = mapped_column(Text(), nullable=True)
    invalidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    invalidated_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    invalidation_reason: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    client_event_id: Mapped[str | None] = mapped_column(String(120), nullable=True)

    game = relationship("Game", back_populates="events", foreign_keys=[game_id])
    actor_participant = relationship("GameParticipant", foreign_keys=[actor_participant_id])
    target_participant = relationship("GameParticipant", foreign_keys=[target_participant_id])
    secondary_target_participant = relationship(
        "GameParticipant", foreign_keys=[secondary_target_participant_id]
    )
    supersedes_event = relationship(
        "GameEvent",
        remote_side=[id, game_id],
        foreign_keys=[supersedes_event_id, game_id],
        uselist=False,
        overlaps="events,game",
    )
    created_by_user = relationship("User", foreign_keys=[created_by_user_id])
    invalidated_by_user = relationship("User", foreign_keys=[invalidated_by_user_id])
