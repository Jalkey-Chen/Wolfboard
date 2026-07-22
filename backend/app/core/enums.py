"""Shared enum values used across Milestone 2 models and schemas.

Keeping workflow values centralized prevents drift between SQLAlchemy models,
Pydantic schemas, service logic, and the frontend API contract.
"""

from enum import Enum


class SeasonStatus(str, Enum):
    """Lifecycle states for a tournament season."""

    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class EventDayCategory(str, Enum):
    """High-level category assigned to an event day."""

    OFFICIAL = "official"
    FUN = "fun"
    MIXED = "mixed"


class EventDayStatus(str, Enum):
    """Lifecycle states for an event day."""

    DRAFT = "draft"
    OPEN_FOR_REGISTRATION = "open_for_registration"
    REGISTRATION_CLOSED = "registration_closed"
    ONGOING = "ongoing"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class RegistrationStatus(str, Enum):
    """Registration status values for an event-day signup."""

    REGISTERED = "registered"
    WAITLISTED = "waitlisted"
    CANCELLED = "cancelled"


class CheckInStatus(str, Enum):
    """Check-in states managed by admins on event day."""

    NOT_CHECKED_IN = "not_checked_in"
    CHECKED_IN = "checked_in"
    ABSENT = "absent"


class RegistrationType(str, Enum):
    """Registration categories supported by the MVP."""

    MAIN = "main"
    SUBSTITUTE = "substitute"
    GUEST = "guest"


class FormatCategory(str, Enum):
    """High-level category assigned to a preset game format."""

    STANDARD = "standard"
    SPECIAL = "special"
    FUN = "fun"


class FormatRoleFaction(str, Enum):
    """Faction classification for roles inside a format definition."""

    GOOD = "good"
    WOLF = "wolf"
    THIRD_PARTY = "third_party"
    SPECIAL = "special"


class FormatSnapshotOrigin(str, Enum):
    """Provenance of a per-game immutable format snapshot."""

    RUNTIME_FREEZE = "runtime_freeze"
    LEGACY_BACKFILL = "legacy_backfill"


class GameType(str, Enum):
    """Classification for how a game should be treated operationally."""

    OFFICIAL = "official"
    FUN = "fun"
    PRACTICE = "practice"


class GamePlayStatus(str, Enum):
    """Lifecycle of the game process itself."""

    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    ENDED = "ended"
    CANCELLED = "cancelled"


class GameResultStatus(str, Enum):
    """Lifecycle of result entry and administrative review."""

    EMPTY = "empty"
    DRAFT = "draft"
    SUBMITTED = "submitted"
    REJECTED = "rejected"
    CONFIRMED = "confirmed"
    REVISED = "revised"


class GameStatusScope(str, Enum):
    """Status-machine dimension recorded by game status history."""

    PLAY = "play"
    RESULT = "result"


class GameEventPhase(str, Enum):
    """In-game phase attached to a structured event."""

    NIGHT = "night"
    DAY = "day"


class GameEventSource(str, Enum):
    """Origin of an event-ledger row."""

    MANUAL = "manual"
    SYSTEM = "system"
    IMPORTED = "imported"


class GameEventVisibility(str, Enum):
    """Audience policy attached by the server-side event registry."""

    PUBLIC = "public"
    POSTGAME_FULL = "postgame_full"
    JUDGE_ONLY = "judge_only"


class GameEventStatus(str, Enum):
    """Immutable event-version lifecycle."""

    ACTIVE = "active"
    SUPERSEDED = "superseded"
    VOIDED = "voided"


class GameEventType(str, Enum):
    """V1 structured in-game event taxonomy."""

    PHASE_STARTED = "phase_started"
    PHASE_COMPLETED = "phase_completed"
    WOLF_KILL_SELECTED = "wolf_kill_selected"
    SEER_CHECKED = "seer_checked"
    WITCH_SAVED = "witch_saved"
    WITCH_POISONED = "witch_poisoned"
    GUARD_PROTECTED = "guard_protected"
    NIGHT_RESOLVED = "night_resolved"
    SHERIFF_CANDIDATE_DECLARED = "sheriff_candidate_declared"
    SHERIFF_CANDIDATE_WITHDREW = "sheriff_candidate_withdrew"
    SHERIFF_VOTE_CAST = "sheriff_vote_cast"
    SHERIFF_ELECTED = "sheriff_elected"
    EXILE_VOTE_CAST = "exile_vote_cast"
    VOTE_TIED = "vote_tied"
    EXILE_REVOTE_STARTED = "exile_revote_started"
    PLAYER_EXILED = "player_exiled"
    HUNTER_SHOT = "hunter_shot"
    WOLF_SELF_EXPLODED = "wolf_self_exploded"
    WOLF_KING_SHOT = "wolf_king_shot"
    SHERIFF_BADGE_TRANSFERRED = "sheriff_badge_transferred"
    SHERIFF_BADGE_DESTROYED = "sheriff_badge_destroyed"
    PLAYER_DIED = "player_died"


class GameDeathCause(str, Enum):
    """V1 structural death-cause vocabulary."""

    WOLF_KILL = "wolf_kill"
    WITCH_POISON = "witch_poison"
    EXILE = "exile"
    HUNTER_SHOT = "hunter_shot"
    WOLF_KING_SHOT = "wolf_king_shot"
    SELF_EXPLOSION = "self_explosion"
    OTHER = "other"


class GamePlayerFaction(str, Enum):
    """Faction values stored for player rows in a game result."""

    GOOD = "good"
    WOLF = "wolf"
    THIRD_PARTY = "third_party"


class GamePlayerFinalStatus(str, Enum):
    """Final lifecycle state recorded for a player at game end."""

    ALIVE = "alive"
    ELIMINATED = "eliminated"
    UNKNOWN = "unknown"


class ScoreAdjustmentType(str, Enum):
    """Adjustment categories supported in the MVP result-entry flow."""

    LATE_PENALTY = "late_penalty"
    CONDUCT_PENALTY = "conduct_penalty"
    JUDGE_BONUS = "judge_bonus"
    MANUAL_ADJUSTMENT = "manual_adjustment"


class ScoreLogSourceType(str, Enum):
    """Source categories for formal score ledger entries."""

    GAME_RESULT = "game_result"
    ADMIN_ADJUSTMENT = "admin_adjustment"
    ROLLBACK = "rollback"


class ScoreLogEffectiveStatus(str, Enum):
    """Lifecycle state for score-log rows in the formal ledger."""

    PENDING = "pending"
    EFFECTIVE = "effective"
    VOIDED = "voided"


class ResultConfirmationStatus(str, Enum):
    """Confirmation outcomes recorded for submitted game results."""

    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISED = "revised"
