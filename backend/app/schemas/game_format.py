"""Schemas for preset game-format list, detail, and admin toggle operations.

Format schemas stay intentionally lightweight in Milestone 3. The system only
needs to expose preset formats and their role composition before result-entry
logic arrives in the next milestone.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.core.enums import FormatCategory, FormatRoleFaction


class FormatRoleRead(BaseModel):
    """Role definition returned inside a game-format detail payload."""

    id: int
    format_id: int
    role_name: str
    faction: FormatRoleFaction
    role_count: int
    display_order: int
    metadata_json: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GameFormatRead(BaseModel):
    """Compact game-format payload used by list views and selectors."""

    id: int
    format_name: str
    format_key: str
    player_count: int
    category: FormatCategory
    description: str | None
    is_active: bool
    is_system_preset: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GameFormatDetail(GameFormatRead):
    """Detailed format payload including its configured role lineup."""

    roles: list[FormatRoleRead]


class GameFormatUpdate(BaseModel):
    """Partial admin payload used to enable or disable a preset format."""

    is_active: bool | None = None
    description: str | None = None
