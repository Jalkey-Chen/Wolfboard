"""Service helpers for preset game-format browsing and admin toggles."""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.format_role import FormatRole
from app.models.game_format import GameFormat
from app.schemas.game_format import GameFormatUpdate


FORMAT_LOAD_OPTIONS = (
    selectinload(GameFormat.format_roles),
)


def list_formats(db: Session) -> list[GameFormat]:
    """Return all game formats ordered for browsing and admin selection."""

    statement = (
        select(GameFormat)
        .options(*FORMAT_LOAD_OPTIONS)
        .order_by(GameFormat.is_active.desc(), GameFormat.player_count.asc(), GameFormat.id.asc())
    )
    return list(db.scalars(statement).all())


def get_format_or_404(db: Session, format_id: int) -> GameFormat:
    """Return a game format with roles preloaded or raise a 404 error."""

    statement = (
        select(GameFormat)
        .options(*FORMAT_LOAD_OPTIONS)
        .where(GameFormat.id == format_id)
    )
    game_format = db.scalar(statement)
    if game_format is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game format not found.")
    # Access format_roles once so order_by on the relationship is consistently realized.
    _ = list(game_format.format_roles)
    return game_format


def update_format(db: Session, game_format: GameFormat, payload: GameFormatUpdate) -> GameFormat:
    """Apply a small admin patch, typically to enable or disable a preset."""

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(game_format, field, value)
    db.add(game_format)
    db.commit()
    return get_format_or_404(db, game_format.id)
