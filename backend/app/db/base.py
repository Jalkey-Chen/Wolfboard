"""Import all SQLAlchemy models so Alembic can discover metadata consistently."""

from app.models.audit_log import AuditLog
from app.models.event_day import EventDay
from app.models.format_role import FormatRole
from app.models.game import Game
from app.models.game_event import GameEvent
from app.models.game_status_history import GameStatusHistory
from app.models.game_participant import GameParticipant
from app.models.game_player import GamePlayer
from app.models.game_format import GameFormat
from app.models.game_format_role_snapshot import GameFormatRoleSnapshot
from app.models.game_format_snapshot import GameFormatSnapshot
from app.models.registration import Registration
from app.models.result_confirmation import ResultConfirmation
from app.models.role import Role
from app.models.score_adjustment import ScoreAdjustment
from app.models.score_log import ScoreLog
from app.models.season import Season
from app.models.user import User
from app.models.user_role import UserRole

__all__ = [
    "AuditLog",
    "EventDay",
    "FormatRole",
    "Game",
    "GameEvent",
    "GameStatusHistory",
    "GameParticipant",
    "GamePlayer",
    "GameFormat",
    "GameFormatRoleSnapshot",
    "GameFormatSnapshot",
    "Registration",
    "ResultConfirmation",
    "Role",
    "ScoreAdjustment",
    "ScoreLog",
    "Season",
    "User",
    "UserRole",
]
