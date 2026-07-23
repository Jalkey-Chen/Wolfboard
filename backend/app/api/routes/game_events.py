"""Assigned-judge and admin API for structured game-event ledgers."""

from copy import deepcopy
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.game_event import (
    GameEventCorrection,
    GameEventCreate,
    GameEventDefinitionRead,
    GameEventRead,
    GameEventVoid,
)
from app.schemas.game_state_projection import GameDerivedStateRead
from app.services.game_event_registry import EVENT_DEFINITIONS, ReferencePolicy
from app.core.enums import GameEventPhase, GameEventSource
from app.services.game_event import (
    append_game_event,
    build_game_event_read,
    correct_game_event,
    list_game_events,
    read_game_event,
    void_game_event,
)
from app.services.game_state_service import get_game_derived_state


router = APIRouter(tags=["game-events"])


def _inline_json_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Return a stable client schema without Pydantic's internal definitions."""

    definitions = schema.get("$defs", {})

    def visit(value: Any) -> Any:
        if isinstance(value, list):
            return [visit(item) for item in value]
        if not isinstance(value, dict):
            return value
        if "$ref" in value:
            key = value["$ref"].rsplit("/", 1)[-1]
            resolved = deepcopy(definitions[key])
            resolved.update({item_key: item for item_key, item in value.items() if item_key != "$ref"})
            return visit(resolved)
        return {
            item_key: visit(item)
            for item_key, item in value.items()
            if item_key not in {"$defs", "title"}
        }

    return visit(schema)


def build_event_definition_reads() -> list[GameEventDefinitionRead]:
    return [
        GameEventDefinitionRead(
            event_type=event_type,
            allowed_phases=[phase for phase in GameEventPhase if phase in definition.allowed_phases],
            default_visibility=definition.default_visibility,
            required_actor=definition.actor == ReferencePolicy.REQUIRED,
            required_target=definition.target == ReferencePolicy.REQUIRED,
            allows_actor=definition.actor != ReferencePolicy.FORBIDDEN,
            allows_target=definition.target != ReferencePolicy.FORBIDDEN,
            allows_secondary_target=definition.allows_secondary_target,
            allowed_sources=[source for source in GameEventSource if source in definition.allowed_sources],
            schema_version=1,
            payload_schema=_inline_json_schema(definition.payload_schema.model_json_schema()),
            payload_field_semantics=definition.payload_field_semantics,
        )
        for event_type, definition in EVENT_DEFINITIONS.items()
    ]


@router.get("/game-events/definitions", response_model=list[GameEventDefinitionRead])
def list_game_event_definitions(
    current_user: User = Depends(get_current_user),
) -> list[GameEventDefinitionRead]:
    if not {"admin", "judge"}.intersection(current_user.roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The admin or judge role is required to read event definitions.",
        )
    return build_event_definition_reads()


@router.get("/games/{game_id}/derived-state", response_model=GameDerivedStateRead)
def read_game_derived_state(
    game_id: int,
    through_logical_sequence: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GameDerivedStateRead:
    """Project recorded state from the current effective event timeline."""

    projected = get_game_derived_state(
        db,
        game_id,
        current_user,
        through_logical_sequence=through_logical_sequence,
    )
    return GameDerivedStateRead.model_validate(projected)


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
