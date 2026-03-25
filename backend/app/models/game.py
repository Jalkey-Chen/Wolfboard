"""Game model representing a single scheduled table/game pairing."""

from datetime import datetime

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import GameStatus, GameType
from app.db.base_class import Base


class Game(Base):
    """Single game scheduled under an event day.

    The table currently stores only planning and lifecycle metadata. Future
    milestones can hang result entry and per-player records from this model
    without changing how admins create or assign games.
    """

    __tablename__ = "games"
    __table_args__ = (
        UniqueConstraint(
            "event_day_id",
            "table_number",
            "game_number",
            name="uq_games_event_day_id_table_number_game_number",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    event_day_id: Mapped[int] = mapped_column(ForeignKey("event_days.id", ondelete="CASCADE"), index=True)
    game_number: Mapped[int] = mapped_column(index=True)
    table_number: Mapped[int] = mapped_column(index=True)
    format_id: Mapped[int] = mapped_column(ForeignKey("game_formats.id", ondelete="RESTRICT"), index=True)
    judge_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    game_type: Mapped[GameType] = mapped_column(
        SqlEnum(GameType, name="game_type", native_enum=False),
        default=GameType.OFFICIAL,
        server_default=GameType.OFFICIAL.value,
        index=True,
    )
    status: Mapped[GameStatus] = mapped_column(
        SqlEnum(GameStatus, name="game_status", native_enum=False),
        default=GameStatus.DRAFT,
        server_default=GameStatus.DRAFT.value,
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
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

    event_day = relationship("EventDay", back_populates="games")
    format = relationship("GameFormat", back_populates="games")
    judge = relationship("User", foreign_keys=[judge_user_id], back_populates="judged_games")
    submitter = relationship("User", foreign_keys=[submitted_by], back_populates="submitted_games")
    confirmer = relationship("User", foreign_keys=[confirmed_by], back_populates="confirmed_games")
    players = relationship(
        "GamePlayer",
        back_populates="game",
        cascade="all, delete-orphan",
        order_by="GamePlayer.seat_number.asc()",
    )
    score_logs = relationship(
        "ScoreLog",
        back_populates="game",
        cascade="all, delete-orphan",
        order_by="ScoreLog.created_at.asc()",
    )
    result_confirmations = relationship(
        "ResultConfirmation",
        back_populates="game",
        cascade="all, delete-orphan",
        order_by="ResultConfirmation.created_at.desc()",
    )
    status_history = relationship(
        "GameStatusHistory",
        back_populates="game",
        cascade="all, delete-orphan",
        order_by="GameStatusHistory.created_at.desc()",
    )

    @property
    def season_id(self) -> int | None:
        """Expose the parent season ID for response serialization."""

        return self.event_day.season_id if self.event_day is not None else None

    @property
    def season_name(self) -> str:
        """Expose the parent season name for response serialization."""

        if self.event_day is None or self.event_day.season is None:
            return ""
        return self.event_day.season.name

    @property
    def event_day_title(self) -> str:
        """Expose the event-day title for summary responses."""

        return self.event_day.title if self.event_day is not None else ""

    @property
    def event_day_date(self):
        """Expose the event-day date for summary responses."""

        return self.event_day.event_date if self.event_day is not None else None

    @property
    def format_name(self) -> str:
        """Expose the assigned format name for summary responses."""

        return self.format.format_name if self.format is not None else ""

    @property
    def judge_display_name(self) -> str:
        """Expose the assigned judge display name for summary responses."""

        return self.judge.display_name if self.judge is not None else ""

    @property
    def has_result_draft(self) -> bool:
        """Expose whether any game-player rows currently exist for this game."""

        return len(self.players) > 0
