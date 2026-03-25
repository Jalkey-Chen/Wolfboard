"""Readonly format endpoints plus a small admin toggle for preset formats."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.game_format import GameFormatDetail, GameFormatRead, GameFormatUpdate
from app.services.format import get_format_or_404, list_formats, update_format


router = APIRouter(prefix="/formats", tags=["formats"])


@router.get("", response_model=list[GameFormatRead])
def read_formats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[GameFormatRead]:
    """Return all preset formats to any authenticated caller."""

    _ = current_user
    return [GameFormatRead.model_validate(game_format) for game_format in list_formats(db)]


@router.get("/{format_id}", response_model=GameFormatDetail)
def read_format(
    format_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GameFormatDetail:
    """Return one format and its role composition."""

    _ = current_user
    return GameFormatDetail.model_validate(get_format_or_404(db, format_id))


@router.patch("/{format_id}", response_model=GameFormatDetail)
def update_format_endpoint(
    format_id: int,
    payload: GameFormatUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> GameFormatDetail:
    """Allow admins to toggle or describe a preset format."""

    _ = current_user
    game_format = get_format_or_404(db, format_id)
    return GameFormatDetail.model_validate(update_format(db, game_format, payload))
