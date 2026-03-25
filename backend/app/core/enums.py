"""Shared enum values used across Milestone 2 models and schemas."""

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
