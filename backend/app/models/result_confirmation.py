"""Result-confirmation history model for submitted games."""

from datetime import datetime

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ResultConfirmationStatus
from app.db.base_class import Base


class ResultConfirmation(Base):
    """History of how a submitted result was approved, rejected, or revised."""

    __tablename__ = "result_confirmations"

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), index=True)
    submitted_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmation_status: Mapped[ResultConfirmationStatus] = mapped_column(
        SqlEnum(ResultConfirmationStatus, name="result_confirmation_status", native_enum=False),
        nullable=False,
        index=True,
    )
    comment: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    game = relationship("Game", back_populates="result_confirmations")
    submitter = relationship("User", foreign_keys=[submitted_by], back_populates="result_confirmations_submitted")
    confirmer = relationship("User", foreign_keys=[confirmed_by], back_populates="result_confirmations_confirmed")


