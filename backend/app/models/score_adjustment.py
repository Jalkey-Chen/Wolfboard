"""Score-adjustment model storing explicit bonus and penalty lines."""

from datetime import datetime

from sqlalchemy import DateTime, Enum as SqlEnum, Float, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ScoreAdjustmentType
from app.db.base_class import Base


class ScoreAdjustment(Base):
    """Adjustment line attached to a specific game player.

    Adjustments stay normalized in their own table so later milestones can
    audit or revise the reasons behind a player's final score without trying to
    reverse-engineer a flat aggregate number.
    """

    __tablename__ = "score_adjustments"

    id: Mapped[int] = mapped_column(primary_key=True)
    game_player_id: Mapped[int] = mapped_column(ForeignKey("game_players.id", ondelete="CASCADE"), index=True)
    adjustment_type: Mapped[ScoreAdjustmentType] = mapped_column(
        SqlEnum(ScoreAdjustmentType, name="score_adjustment_type", native_enum=False),
        index=True,
    )
    delta: Mapped[float] = mapped_column(Float())
    reason: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    game_player = relationship("GamePlayer", back_populates="adjustments")
    creator = relationship("User", back_populates="created_score_adjustments")

    @property
    def target_seat_number(self) -> int | None:
        """Expose the related seat number for draft payload serialization."""

        return self.game_player.seat_number if self.game_player is not None else None
