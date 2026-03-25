"""Player profile endpoints for authenticated profile views."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.player_profile import PlayerProfileRead
from app.services.player_profile import build_player_profile


router = APIRouter(prefix="/players", tags=["players"])


@router.get("/{player_id}/profile", response_model=PlayerProfileRead)
def read_player_profile(
    player_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PlayerProfileRead:
    """Return one player's profile and effective game history.

    Players may inspect their own history, while admins can inspect any player.
    """

    if "admin" not in current_user.roles and current_user.id != player_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only view your own player profile.")
    return build_player_profile(db, player_id)

