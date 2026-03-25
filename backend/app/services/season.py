"""Service helpers for season queries and admin mutations.

The service layer keeps route handlers thin and gives later milestones a stable
place to add audit logging, richer validation, or transactional workflows.
"""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.season import Season
from app.models.user import User
from app.schemas.season import SeasonCreate, SeasonUpdate


def list_seasons(db: Session) -> list[Season]:
    """Return all seasons ordered by start date descending.

    The UI favors the most recent or active seasons first, so descending date
    order provides a better default than raw primary-key order.
    """

    statement = select(Season).order_by(Season.start_date.desc(), Season.id.desc())
    return list(db.scalars(statement).all())


def get_season_or_404(db: Session, season_id: int) -> Season:
    """Return a season with event days loaded or raise a 404 error."""

    statement = (
        select(Season)
        .options(selectinload(Season.event_days))
        .where(Season.id == season_id)
    )
    season = db.scalar(statement)
    if season is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Season not found.")
    return season


def create_season(db: Session, payload: SeasonCreate, current_user: User) -> Season:
    """Create a new season owned by the current admin."""

    season = Season(**payload.model_dump(), created_by=current_user.id)
    db.add(season)
    db.commit()
    db.refresh(season)
    return season


def update_season(db: Session, season: Season, payload: SeasonUpdate) -> Season:
    """Apply a partial season update and persist it."""

    update_data = payload.model_dump(exclude_unset=True)

    next_start_date = update_data.get("start_date", season.start_date)
    next_end_date = update_data.get("end_date", season.end_date)
    if next_end_date < next_start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="end_date must be on or after start_date.",
        )

    for field, value in update_data.items():
        setattr(season, field, value)
    db.add(season)
    db.commit()
    db.refresh(season)
    return season
