from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserRead(BaseModel):
    """Public user fields returned by authentication endpoints."""

    id: int
    username: str
    display_name: str
    email: str | None
    account_status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
