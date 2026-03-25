"""Schemas for admin-facing user directory helper endpoints."""

from pydantic import BaseModel, ConfigDict


class JudgeDirectoryEntry(BaseModel):
    """Small user payload used when assigning judges to games."""

    id: int
    username: str
    display_name: str

    model_config = ConfigDict(from_attributes=True)
