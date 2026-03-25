"""Formal score ledger model used for leaderboard and profile queries."""

from datetime import datetime

from sqlalchemy import DateTime, Enum as SqlEnum, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ScoreLogEffectiveStatus, ScoreLogSourceType
from app.db.base_class import Base


class ScoreLog(Base):
    """Formal point movement written after result confirmation or revision.

    The leaderboard never aggregates directly from `game_players`. Instead it
    relies on these immutable-or-voided ledger rows so admin revisions leave a
    traceable history.
    """

    __tablename__ = "score_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), index=True)
    source_type: Mapped[ScoreLogSourceType] = mapped_column(
        SqlEnum(ScoreLogSourceType, name="score_log_source_type", native_enum=False),
        default=ScoreLogSourceType.GAME_RESULT,
        server_default=ScoreLogSourceType.GAME_RESULT.value,
        index=True,
    )
    delta: Mapped[float] = mapped_column(Float(), nullable=False)
    balance_after: Mapped[float] = mapped_column(Float(), nullable=False, default=0.0, server_default="0")
    note: Mapped[str | None] = mapped_column(Text(), nullable=True)
    effective_status: Mapped[ScoreLogEffectiveStatus] = mapped_column(
        SqlEnum(ScoreLogEffectiveStatus, name="score_log_effective_status", native_enum=False),
        default=ScoreLogEffectiveStatus.EFFECTIVE,
        server_default=ScoreLogEffectiveStatus.EFFECTIVE.value,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user = relationship("User", back_populates="score_logs")
    game = relationship("Game", back_populates="score_logs")


