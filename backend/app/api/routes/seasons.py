"""Season list, detail, and admin CRUD endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.event_day import EventDaySummary
from app.schemas.season import SeasonCreate, SeasonDetail, SeasonRead, SeasonUpdate
from app.services.event_day import list_event_days_for_season
from app.services.season import create_season, get_season_or_404, list_seasons, update_season


router = APIRouter(prefix="/seasons", tags=["seasons"])


@router.get("", response_model=list[SeasonRead])
def read_seasons(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SeasonRead]:
    """Return all seasons for authenticated users."""

    _ = current_user
    seasons = list_seasons(db)
    return [SeasonRead.model_validate(season) for season in seasons]


@router.post("", response_model=SeasonRead)
def create_season_endpoint(
    payload: SeasonCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> SeasonRead:
    """Create a new season as an admin."""

    season = create_season(db, payload, current_user)
    return SeasonRead.model_validate(season)


@router.get("/{season_id}", response_model=SeasonDetail)
def read_season(
    season_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SeasonDetail:
    """Return a single season and its event days for authenticated users."""

    _ = current_user
    season = get_season_or_404(db, season_id)
    return SeasonDetail(
        **SeasonRead.model_validate(season).model_dump(),
        event_days=[EventDaySummary.model_validate(event_day) for event_day in season.event_days],
    )


@router.patch("/{season_id}", response_model=SeasonRead)
def update_season_endpoint(
    season_id: int,
    payload: SeasonUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> SeasonRead:
    """Update an existing season as an admin."""

    _ = current_user
    season = get_season_or_404(db, season_id)
    season = update_season(db, season, payload)
    return SeasonRead.model_validate(season)


@router.get("/{season_id}/event-days", response_model=list[EventDaySummary])
def read_season_event_days(
    season_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[EventDaySummary]:
    """Return all event days for a season."""

    _ = current_user
    _ = get_season_or_404(db, season_id)
    event_days = list_event_days_for_season(db, season_id)
    return [EventDaySummary.model_validate(event_day) for event_day in event_days]
