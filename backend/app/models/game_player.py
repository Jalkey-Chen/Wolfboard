"""Game-player model representing a saved result row inside one game."""

from datetime import datetime

from sqlalchemy import DateTime, Enum as SqlEnum, Float, ForeignKey, ForeignKeyConstraint, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import GamePlayerFaction, GamePlayerFinalStatus
from app.db.base_class import Base


class GamePlayer(Base):
    """Saved player result row for a single game.

    Several fields are nullable to support draft persistence before submission.
    Final submission validation is enforced in the result service rather than
    by making the table impossible to use for incomplete drafts.
    """

    __tablename__ = "game_players"
    __table_args__ = (
        ForeignKeyConstraint(
            ["participant_id", "game_id"],
            ["game_participants.id", "game_participants.game_id"],
            name="fk_game_players_participant_game",
            ondelete="CASCADE",
        ),
        UniqueConstraint("participant_id", name="uq_game_players_participant_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), index=True)
    participant_id: Mapped[int] = mapped_column(nullable=False, index=True)
    role_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    faction: Mapped[GamePlayerFaction | None] = mapped_column(
        SqlEnum(GamePlayerFaction, name="game_player_faction", native_enum=False),
        nullable=True,
        index=True,
    )
    final_status: Mapped[GamePlayerFinalStatus] = mapped_column(
        SqlEnum(GamePlayerFinalStatus, name="game_player_final_status", native_enum=False),
        default=GamePlayerFinalStatus.UNKNOWN,
        server_default=GamePlayerFinalStatus.UNKNOWN.value,
        index=True,
    )
    is_winner: Mapped[bool | None] = mapped_column(nullable=True)
    base_score: Mapped[float] = mapped_column(Float(), default=0.0, server_default="0")
    adjustment_score: Mapped[float] = mapped_column(Float(), default=0.0, server_default="0")
    final_score: Mapped[float] = mapped_column(Float(), default=0.0, server_default="0")
    judge_bonus_note: Mapped[str | None] = mapped_column(Text(), nullable=True)
    penalty_note: Mapped[str | None] = mapped_column(Text(), nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    game = relationship("Game", back_populates="players", overlaps="participant,result", viewonly=True)
    participant = relationship("GameParticipant", back_populates="result", overlaps="game,players")
    adjustments = relationship(
        "ScoreAdjustment",
        back_populates="game_player",
        cascade="all, delete-orphan",
        order_by="ScoreAdjustment.created_at.asc()",
    )

    @property
    def username(self) -> str:
        """Expose the related username for result payloads."""

        if self.participant is None or self.participant.user is None:
            return ""
        return self.participant.user.username

    @property
    def display_name(self) -> str:
        """Expose the related display name for result payloads."""

        if self.participant is None:
            return ""
        return self.participant.display_name_snapshot or ""

    @property
    def user_id(self) -> int | None:
        """Project the participant's account binding for API compatibility."""

        return self.participant.user_id if self.participant is not None else None

    @property
    def seat_number(self) -> int | None:
        """Project the participant's current seat for API compatibility."""

        return self.participant.seat_number if self.participant is not None else None
