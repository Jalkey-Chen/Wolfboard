"""Append, read, correct, and void structured game-event ledger rows."""

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.enums import (
    GameEventSource,
    GameEventStatus,
    GamePlayStatus,
    GameResultStatus,
)
from app.models.game import Game
from app.models.game_event import GameEvent
from app.models.game_format_snapshot import GameFormatSnapshot
from app.models.game_participant import GameParticipant
from app.models.user import User
from app.schemas.game_event import (
    GameEventBody,
    GameEventCorrection,
    GameEventCreate,
    GameEventParticipantRead,
    GameEventRead,
    GameEventUserRead,
)
from app.services.audit import write_audit_log
from app.services.game_event_registry import (
    EVENT_DEFINITIONS,
    EventDefinition,
    ReferencePolicy,
    payload_event_ids,
    payload_participant_ids,
)


EVENT_LOAD_OPTIONS = (
    joinedload(GameEvent.actor_participant),
    joinedload(GameEvent.target_participant),
    joinedload(GameEvent.secondary_target_participant),
    joinedload(GameEvent.created_by_user),
    joinedload(GameEvent.invalidated_by_user),
)


def _conflict(detail: str) -> None:
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def _unprocessable(detail: Any) -> None:
    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)


def lock_event_game(db: Session, game_id: int) -> Game:
    """Serialize all event and result writes on the owning Game row."""

    statement = (
        select(Game)
        .options(selectinload(Game.format_snapshot).selectinload(GameFormatSnapshot.roles))
        .where(Game.id == game_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    game = db.scalar(statement)
    if game is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found.")
    return game


def get_event_game_or_404(db: Session, game_id: int) -> Game:
    game = db.scalar(select(Game).where(Game.id == game_id))
    if game is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found.")
    return game


def ensure_event_operator(game: Game, current_user: User) -> None:
    if "admin" in current_user.roles:
        return
    if "judge" in current_user.roles and current_user.id == game.judge_user_id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Only an admin or the assigned judge can access this game event ledger.",
    )


def ensure_event_ledger_editable(game: Game) -> None:
    allowed_result_statuses = {
        GameResultStatus.EMPTY,
        GameResultStatus.DRAFT,
        GameResultStatus.REJECTED,
    }
    if (
        game.play_status not in {GamePlayStatus.IN_PROGRESS, GamePlayStatus.ENDED}
        or game.result_status not in allowed_result_statuses
    ):
        _conflict("The game event ledger is locked in the current play or result state.")
    if game.format_snapshot is None:
        _conflict("The game must have frozen format context before events can be recorded.")


def _validate_reference_policy(name: str, value: int | None, policy: ReferencePolicy) -> None:
    if policy == ReferencePolicy.REQUIRED and value is None:
        _unprocessable(f"{name} is required for this event type.")
    if policy == ReferencePolicy.FORBIDDEN and value is not None:
        _unprocessable(f"{name} is not allowed for this event type.")


def _normalize_payload(definition: EventDefinition, raw_payload: dict[str, Any]) -> BaseModel:
    try:
        return definition.payload_schema.model_validate(raw_payload)
    except ValidationError as exc:
        _unprocessable(
            {
                "message": "Event payload validation failed.",
                "errors": jsonable_encoder(exc.errors(include_url=False)),
            }
        )


def _validate_game_references(
    db: Session,
    *,
    game_id: int,
    body: GameEventBody,
    normalized_payload: BaseModel,
) -> None:
    participant_ids = {
        participant_id
        for participant_id in (
            body.actor_participant_id,
            body.target_participant_id,
            body.secondary_target_participant_id,
        )
        if participant_id is not None
    } | payload_participant_ids(normalized_payload)
    if participant_ids:
        found = set(
            db.scalars(
                select(GameParticipant.id).where(
                    GameParticipant.game_id == game_id,
                    GameParticipant.id.in_(participant_ids),
                )
            )
        )
        missing = participant_ids - found
        if missing:
            _unprocessable(
                f"Participant IDs do not belong to this game: {', '.join(map(str, sorted(missing)))}."
            )

    event_ids = payload_event_ids(normalized_payload)
    if event_ids:
        found_events = set(
            db.scalars(
                select(GameEvent.id).where(
                    GameEvent.game_id == game_id,
                    GameEvent.id.in_(event_ids),
                )
            )
        )
        missing_events = event_ids - found_events
        if missing_events:
            _unprocessable(
                f"Event IDs do not belong to this game: {', '.join(map(str, sorted(missing_events)))}."
            )


def normalize_event_body(
    db: Session,
    *,
    game_id: int,
    body: GameEventBody,
    source: GameEventSource = GameEventSource.MANUAL,
) -> tuple[EventDefinition, dict[str, Any]]:
    definition = EVENT_DEFINITIONS[body.event_type]
    if source not in definition.allowed_sources:
        _unprocessable("This event source is not allowed for the event type.")
    if body.phase not in definition.allowed_phases:
        _unprocessable("The event type is not allowed in the requested phase.")
    _validate_reference_policy("actor_participant_id", body.actor_participant_id, definition.actor)
    _validate_reference_policy("target_participant_id", body.target_participant_id, definition.target)
    if body.secondary_target_participant_id is not None and not definition.allows_secondary_target:
        _unprocessable("secondary_target_participant_id is not allowed for this event type.")
    normalized_payload = _normalize_payload(definition, body.payload)
    _validate_game_references(
        db,
        game_id=game_id,
        body=body,
        normalized_payload=normalized_payload,
    )
    return definition, normalized_payload.model_dump(mode="json", exclude_none=True)


def _event_matches_body(
    event: GameEvent,
    body: GameEventBody,
    normalized_payload: dict[str, Any],
    *,
    supersedes_event_id: int | None,
    revision_reason: str | None,
) -> bool:
    return (
        event.phase == body.phase
        and event.round_no == body.round_no
        and event.event_type == body.event_type.value
        and event.actor_participant_id == body.actor_participant_id
        and event.target_participant_id == body.target_participant_id
        and event.secondary_target_participant_id == body.secondary_target_participant_id
        and event.payload_json == normalized_payload
        and event.occurred_at == body.occurred_at
        and event.supersedes_event_id == supersedes_event_id
        and event.revision_reason == revision_reason
    )


def _existing_idempotent_event(
    db: Session,
    *,
    game_id: int,
    body: GameEventBody,
    normalized_payload: dict[str, Any],
    supersedes_event_id: int | None,
    revision_reason: str | None,
) -> GameEvent | None:
    if body.client_event_id is None:
        return None
    existing = db.scalar(
        select(GameEvent)
        .options(*EVENT_LOAD_OPTIONS)
        .where(
            GameEvent.game_id == game_id,
            GameEvent.client_event_id == body.client_event_id,
        )
    )
    if existing is None:
        return None
    if _event_matches_body(
        existing,
        body,
        normalized_payload,
        supersedes_event_id=supersedes_event_id,
        revision_reason=revision_reason,
    ):
        return existing
    _conflict("client_event_id is already used by a different event request.")


def _allocate_sequence(game: Game) -> int:
    sequence_no = game.next_event_sequence
    game.next_event_sequence += 1
    return sequence_no


def _new_event(
    *,
    game: Game,
    body: GameEventBody,
    normalized_payload: dict[str, Any],
    visibility,
    current_user: User,
    logical_sequence_no: int | None = None,
    supersedes_event_id: int | None = None,
    revision_reason: str | None = None,
) -> GameEvent:
    sequence_no = _allocate_sequence(game)
    return GameEvent(
        game_id=game.id,
        sequence_no=sequence_no,
        logical_sequence_no=logical_sequence_no or sequence_no,
        phase=body.phase,
        round_no=body.round_no,
        event_type=body.event_type.value,
        actor_participant_id=body.actor_participant_id,
        target_participant_id=body.target_participant_id,
        secondary_target_participant_id=body.secondary_target_participant_id,
        payload_json=normalized_payload,
        visibility=visibility,
        source=GameEventSource.MANUAL,
        schema_version=1,
        status=GameEventStatus.ACTIVE,
        supersedes_event_id=supersedes_event_id,
        revision_reason=revision_reason,
        created_by_user_id=current_user.id,
        occurred_at=body.occurred_at,
        client_event_id=body.client_event_id,
    )


def append_game_event(
    db: Session,
    game_id: int,
    payload: GameEventCreate,
    current_user: User,
) -> GameEvent:
    game = lock_event_game(db, game_id)
    ensure_event_operator(game, current_user)
    ensure_event_ledger_editable(game)
    definition, normalized_payload = normalize_event_body(db, game_id=game.id, body=payload)
    existing = _existing_idempotent_event(
        db,
        game_id=game.id,
        body=payload,
        normalized_payload=normalized_payload,
        supersedes_event_id=None,
        revision_reason=None,
    )
    if existing is not None:
        db.commit()
        return existing

    event = _new_event(
        game=game,
        body=payload,
        normalized_payload=normalized_payload,
        visibility=definition.default_visibility,
        current_user=current_user,
    )
    db.add(event)
    db.commit()
    return get_game_event_or_404(db, game.id, event.id)


def _get_event(db: Session, game_id: int, event_id: int) -> GameEvent | None:
    return db.scalar(
        select(GameEvent)
        .options(*EVENT_LOAD_OPTIONS)
        .where(GameEvent.game_id == game_id, GameEvent.id == event_id)
    )


def get_game_event_or_404(db: Session, game_id: int, event_id: int) -> GameEvent:
    event = _get_event(db, game_id, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game event not found.")
    return event


def list_game_events(
    db: Session,
    game_id: int,
    current_user: User,
    *,
    view: str,
    after_ledger_sequence: int | None,
    after_logical_sequence: int | None,
    limit: int,
) -> list[GameEvent]:
    game = get_event_game_or_404(db, game_id)
    ensure_event_operator(game, current_user)
    statement = select(GameEvent).options(*EVENT_LOAD_OPTIONS).where(GameEvent.game_id == game_id)
    if view == "effective":
        if after_ledger_sequence is not None:
            _unprocessable("after_ledger_sequence is only valid for ledger view.")
        statement = statement.where(GameEvent.status == GameEventStatus.ACTIVE)
        if after_logical_sequence is not None:
            statement = statement.where(GameEvent.logical_sequence_no > after_logical_sequence)
        statement = statement.order_by(GameEvent.logical_sequence_no, GameEvent.id)
    else:
        if after_logical_sequence is not None:
            _unprocessable("after_logical_sequence is only valid for effective view.")
        if after_ledger_sequence is not None:
            statement = statement.where(GameEvent.sequence_no > after_ledger_sequence)
        statement = statement.order_by(GameEvent.sequence_no)
    return list(db.scalars(statement.limit(limit)))


def read_game_event(
    db: Session,
    game_id: int,
    event_id: int,
    current_user: User,
) -> GameEvent:
    game = get_event_game_or_404(db, game_id)
    ensure_event_operator(game, current_user)
    return get_game_event_or_404(db, game_id, event_id)


def build_event_snapshot(event: GameEvent) -> dict[str, Any]:
    return jsonable_encoder(
        {
            "id": event.id,
            "game_id": event.game_id,
            "sequence_no": event.sequence_no,
            "logical_sequence_no": event.logical_sequence_no,
            "phase": event.phase,
            "round_no": event.round_no,
            "event_type": event.event_type,
            "actor_participant_id": event.actor_participant_id,
            "target_participant_id": event.target_participant_id,
            "secondary_target_participant_id": event.secondary_target_participant_id,
            "payload": event.payload_json,
            "visibility": event.visibility,
            "source": event.source,
            "schema_version": event.schema_version,
            "status": event.status,
            "supersedes_event_id": event.supersedes_event_id,
            "revision_reason": event.revision_reason,
            "invalidated_at": event.invalidated_at,
            "invalidated_by_user_id": event.invalidated_by_user_id,
            "invalidation_reason": event.invalidation_reason,
            "created_by_user_id": event.created_by_user_id,
            "created_at": event.created_at,
            "occurred_at": event.occurred_at,
            "client_event_id": event.client_event_id,
        }
    )


def correct_game_event(
    db: Session,
    game_id: int,
    event_id: int,
    payload: GameEventCorrection,
    current_user: User,
) -> GameEvent:
    game = lock_event_game(db, game_id)
    ensure_event_operator(game, current_user)
    ensure_event_ledger_editable(game)
    original = _get_event(db, game.id, event_id)
    if original is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game event not found.")
    definition, normalized_payload = normalize_event_body(db, game_id=game.id, body=payload)
    existing = _existing_idempotent_event(
        db,
        game_id=game.id,
        body=payload,
        normalized_payload=normalized_payload,
        supersedes_event_id=original.id,
        revision_reason=payload.reason,
    )
    if existing is not None:
        db.commit()
        return existing
    if original.status != GameEventStatus.ACTIVE:
        _conflict("Only the current active event version can be corrected.")

    old_snapshot = build_event_snapshot(original)
    invalidated_at = datetime.now(timezone.utc)
    original.status = GameEventStatus.SUPERSEDED
    original.invalidated_at = invalidated_at
    original.invalidated_by_user_id = current_user.id
    original.invalidation_reason = payload.reason
    db.flush()

    replacement = _new_event(
        game=game,
        body=payload,
        normalized_payload=normalized_payload,
        visibility=definition.default_visibility,
        current_user=current_user,
        logical_sequence_no=original.logical_sequence_no,
        supersedes_event_id=original.id,
        revision_reason=payload.reason,
    )
    db.add(replacement)
    db.flush()
    write_audit_log(
        db,
        actor_user_id=current_user.id,
        entity_type="game_event",
        entity_id=original.id,
        action_type="correct",
        old_value_json=old_snapshot,
        new_value_json=build_event_snapshot(replacement),
        reason=payload.reason,
    )
    db.commit()
    return get_game_event_or_404(db, game.id, replacement.id)


def void_game_event(
    db: Session,
    game_id: int,
    event_id: int,
    reason: str,
    current_user: User,
) -> GameEvent:
    game = lock_event_game(db, game_id)
    ensure_event_operator(game, current_user)
    ensure_event_ledger_editable(game)
    event = _get_event(db, game.id, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game event not found.")
    if event.status != GameEventStatus.ACTIVE:
        _conflict("Only an active event can be voided.")
    old_snapshot = build_event_snapshot(event)
    event.status = GameEventStatus.VOIDED
    event.invalidated_at = datetime.now(timezone.utc)
    event.invalidated_by_user_id = current_user.id
    event.invalidation_reason = reason
    db.flush()
    write_audit_log(
        db,
        actor_user_id=current_user.id,
        entity_type="game_event",
        entity_id=event.id,
        action_type="void",
        old_value_json=old_snapshot,
        new_value_json=build_event_snapshot(event),
        reason=reason,
    )
    db.commit()
    return get_game_event_or_404(db, game.id, event.id)


def build_game_event_read(event: GameEvent) -> GameEventRead:
    def participant(value: GameParticipant | None) -> GameEventParticipantRead | None:
        if value is None:
            return None
        return GameEventParticipantRead(
            participant_id=value.id,
            seat_number=value.seat_number,
            display_name_snapshot=value.display_name_snapshot,
        )

    return GameEventRead(
        id=event.id,
        game_id=event.game_id,
        sequence_no=event.sequence_no,
        logical_sequence_no=event.logical_sequence_no,
        phase=event.phase,
        round_no=event.round_no,
        event_type=event.event_type,
        actor_participant_id=event.actor_participant_id,
        target_participant_id=event.target_participant_id,
        secondary_target_participant_id=event.secondary_target_participant_id,
        actor=participant(event.actor_participant),
        target=participant(event.target_participant),
        secondary_target=participant(event.secondary_target_participant),
        payload=event.payload_json,
        visibility=event.visibility,
        source=event.source,
        schema_version=event.schema_version,
        status=event.status,
        supersedes_event_id=event.supersedes_event_id,
        revision_reason=event.revision_reason,
        invalidated_at=event.invalidated_at,
        invalidated_by_user_id=event.invalidated_by_user_id,
        invalidation_reason=event.invalidation_reason,
        created_by_user_id=event.created_by_user_id,
        created_by=GameEventUserRead(
            user_id=event.created_by_user.id,
            username=event.created_by_user.username,
            display_name=event.created_by_user.display_name,
        ),
        created_at=event.created_at,
        occurred_at=event.occurred_at,
        client_event_id=event.client_event_id,
    )


def get_event_referenced_participant_ids(db: Session, game_id: int) -> set[int]:
    """Return participant IDs frozen by direct or V1 payload event references."""

    referenced: set[int] = set()
    rows = db.execute(
        select(
            GameEvent.actor_participant_id,
            GameEvent.target_participant_id,
            GameEvent.secondary_target_participant_id,
            GameEvent.payload_json,
        ).where(GameEvent.game_id == game_id)
    )
    for actor_id, target_id, secondary_id, payload in rows:
        referenced.update(
            value for value in (actor_id, target_id, secondary_id) if value is not None
        )
        for key in ("candidate_participant_ids", "eligible_participant_ids"):
            referenced.update(payload.get(key, []))
    return referenced
