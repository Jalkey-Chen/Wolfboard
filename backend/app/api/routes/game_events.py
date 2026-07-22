"""Assigned-judge and admin API for structured game-event ledgers."""

from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.game_event import (
    GameEventCorrection,
    GameEventCreate,
    GameEventRead,
    GameEventVoid,
)
from app.services.game_event import (
    append_game_event,
    build_game_event_read,
    correct_game_event,
    list_game_events,
    read_game_event,
    void_game_event,
)


router = APIRouter(tags=["game-events"])


@router.post("/games/{game_id}/events", response_model=GameEventRead)
def create_game_event_endpoint(
    game_id: int,
    payload: GameEventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GameEventRead:
    return build_game_event_read(append_game_event(db, game_id, payload, current_user))


@router.get("/games/{game_id}/events", response_model=list[GameEventRead])
def list_game_events_endpoint(
    game_id: int,
    view: Literal["effective", "ledger"] = Query(default="effective"),
    after_ledger_sequence: int | None = Query(default=None, ge=0),
    after_logical_sequence: int | None = Query(default=None, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[GameEventRead]:
    return [
        build_game_event_read(event)
        for event in list_game_events(
            db,
            game_id,
            current_user,
            view=view,
            after_ledger_sequence=after_ledger_sequence,
            after_logical_sequence=after_logical_sequence,
            limit=limit,
        )
    ]


@router.get("/games/{game_id}/events/{event_id}", response_model=GameEventRead)
def read_game_event_endpoint(
    game_id: int,
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GameEventRead:
    return build_game_event_read(read_game_event(db, game_id, event_id, current_user))


@router.post("/games/{game_id}/events/{event_id}/correct", response_model=GameEventRead)
def correct_game_event_endpoint(
    game_id: int,
    event_id: int,
    payload: GameEventCorrection,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GameEventRead:
    return build_game_event_read(
        correct_game_event(db, game_id, event_id, payload, current_user)
    )


@router.post("/games/{game_id}/events/{event_id}/void", response_model=GameEventRead)
def void_game_event_endpoint(
    game_id: int,
    event_id: int,
    payload: GameEventVoid,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GameEventRead:
    return build_game_event_read(
        void_game_event(db, game_id, event_id, payload.reason, current_user)
    )
