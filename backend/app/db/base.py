"""Import all SQLAlchemy models so Alembic can discover metadata consistently."""

from app.models.event_day import EventDay
from app.models.format_role import FormatRole
from app.models.game import Game
from app.models.game_player import GamePlayer
from app.models.game_format import GameFormat
from app.models.registration import Registration
from app.models.role import Role
from app.models.score_adjustment import ScoreAdjustment
from app.models.season import Season
from app.models.user import User
from app.models.user_role import UserRole

__all__ = [
    "EventDay",
    "FormatRole",
    "Game",
    "GamePlayer",
    "GameFormat",
    "Registration",
    "Role",
    "ScoreAdjustment",
    "Season",
    "User",
    "UserRole",
]
