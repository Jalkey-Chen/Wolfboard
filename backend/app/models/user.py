"""User model for authenticated platform accounts."""

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class User(Base):
    """Application user with zero or more system permission roles.

    The model intentionally avoids a single `role_id` field. Multi-role support
    is required because one real person may participate as a player in some
    contexts while also acting as a judge or admin elsewhere.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    account_status: Mapped[str] = mapped_column(String(20), default="active", server_default="active")
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

    user_roles = relationship(
        "UserRole",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    created_seasons = relationship("Season", back_populates="creator")
    created_event_days = relationship("EventDay", back_populates="creator")
    registrations = relationship("Registration", back_populates="user")
    judged_games = relationship("Game", foreign_keys="Game.judge_user_id", back_populates="judge")
    submitted_games = relationship("Game", foreign_keys="Game.submitted_by", back_populates="submitter")
    confirmed_games = relationship("Game", foreign_keys="Game.confirmed_by", back_populates="confirmer")
    game_players = relationship("GamePlayer", back_populates="user")
    created_score_adjustments = relationship("ScoreAdjustment", back_populates="creator")

    @property
    def roles(self) -> list[str]:
        """Return stable role keys for authorization checks and API responses.

        This computed helper keeps the API payload simple while preserving the
        normalized `user_roles` table structure in the database layer.
        """

        return sorted(user_role.role.role_key for user_role in self.user_roles if user_role.role is not None)
