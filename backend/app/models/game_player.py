"""Game-player model representing a saved result row inside one game."""

from datetime import datetime

from sqlalchemy import DateTime, Enum as SqlEnum, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
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
        UniqueConstraint("game_id", "seat_number", name="uq_game_players_game_id_seat_number"),
        UniqueConstraint("game_id", "user_id", name="uq_game_players_game_id_user_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=True, index=True)
    seat_number: Mapped[int | None] = mapped_column(Integer(), nullable=True)
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

    game = relationship("Game", back_populates="players")
    user = relationship("User", back_populates="game_players")
    adjustments = relationship(
        "ScoreAdjustment",
        back_populates="game_player",
        cascade="all, delete-orphan",
        order_by="ScoreAdjustment.created_at.asc()",
    )

    @property
    def username(self) -> str:
        """Expose the related username for result payloads."""

        return self.user.username if self.user is not None else ""

    @property
    def display_name(self) -> str:
        """Expose the related display name for result payloads."""

        return self.user.display_name if self.user is not None else ""
