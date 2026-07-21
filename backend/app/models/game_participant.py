"""Stable participant identity inside a single game."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class GameParticipant(Base):
    """Stable in-game identity separated from mutable result fields."""

    __tablename__ = "game_participants"
    __table_args__ = (
        UniqueConstraint("game_id", "seat_number", name="uq_game_participants_game_id_seat_number"),
        UniqueConstraint("game_id", "user_id", name="uq_game_participants_game_id_user_id"),
        UniqueConstraint("id", "game_id", name="uq_game_participants_id_game_id"),
        Index("ix_game_participants_game_id_seat_number", "game_id", "seat_number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=True, index=True)
    seat_number: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    display_name_snapshot: Mapped[str | None] = mapped_column(String(100), nullable=True)
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

    game = relationship("Game", back_populates="participants")
    user = relationship("User", back_populates="game_participants")
    result = relationship(
        "GamePlayer",
        back_populates="participant",
        cascade="all, delete-orphan",
        single_parent=True,
        uselist=False,
        overlaps="game,players",
    )
