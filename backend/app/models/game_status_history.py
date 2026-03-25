"""Status-transition history model for game lifecycle changes."""

from datetime import datetime

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import GameStatus
from app.db.base_class import Base


class GameStatusHistory(Base):
    """Historical record of status changes applied to a game."""

    __tablename__ = "game_status_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), index=True)
    old_status: Mapped[GameStatus | None] = mapped_column(
        SqlEnum(GameStatus, name="game_status", native_enum=False),
        nullable=True,
    )
    new_status: Mapped[GameStatus] = mapped_column(
        SqlEnum(GameStatus, name="game_status", native_enum=False),
        nullable=False,
    )
    changed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    reason: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    game = relationship("Game", back_populates="status_history")
    actor = relationship("User", back_populates="game_status_history_entries")

