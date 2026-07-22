"""Schemas for live and immutable per-game format context."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.core.enums import FormatCategory, FormatRoleFaction, FormatSnapshotOrigin


class GameFormatContextRoleRead(BaseModel):
    """One role row projected from either a live template or a snapshot."""

    id: int | None
    source_format_role_id: int | None
    role_name: str
    faction: FormatRoleFaction
    role_count: int
    display_order: int
    metadata_json: dict[str, Any] | None


class GameFormatContextRead(BaseModel):
    """Authoritative format context for one game."""

    is_frozen: bool
    source_format_id: int | None
    snapshot_id: int | None
    snapshot_origin: FormatSnapshotOrigin | None
    snapshot_schema_version: int | None
    format_key: str
    format_name: str
    player_count: int
    category: FormatCategory
    description: str | None
    is_system_preset: bool
    frozen_at: datetime | None
    frozen_by_user_id: int | None
    roles: list[GameFormatContextRoleRead]
