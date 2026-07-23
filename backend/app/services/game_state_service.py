"""Read-only ORM boundary for deterministic game-state projection."""

from copy import deepcopy

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.enums import GameEventStatus
from app.models.game import Game
from app.models.game_event import GameEvent
from app.models.game_format_snapshot import GameFormatSnapshot
from app.models.game_participant import GameParticipant
from app.models.user import User
from app.services.game_event import ensure_event_operator
from app.services.game_state_projection import (
    GameDerivedState,
    GameEventProjectionInput,
    GameProjectionContext,
    ParticipantProjectionInput,
    project_game_state,
)


GAME_PROJECTION_LOAD_OPTIONS = (
    selectinload(Game.format_snapshot).selectinload(GameFormatSnapshot.roles),
    selectinload(Game.participants).joinedload(GameParticipant.result),
)


def get_game_derived_state(
    db: Session,
    game_id: int,
    current_user: User,
    *,
    through_logical_sequence: int | None,
) -> GameDerivedState:
    """Load one read snapshot, detach DTOs, and invoke the pure projector."""

    game = db.scalar(
        select(Game)
        .options(*GAME_PROJECTION_LOAD_OPTIONS)
        .where(Game.id == game_id)
    )
    if game is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found.")
    ensure_event_operator(game, current_user)

    event_statement = (
        select(GameEvent)
        .where(
            GameEvent.game_id == game_id,
            GameEvent.status == GameEventStatus.ACTIVE,
        )
        .order_by(GameEvent.logical_sequence_no, GameEvent.id)
    )
    if through_logical_sequence is not None:
        event_statement = event_statement.where(
            GameEvent.logical_sequence_no <= through_logical_sequence
        )
    event_rows = list(db.scalars(event_statement))

    snapshot = game.format_snapshot
    context = GameProjectionContext(
        game_id=game.id,
        play_status=game.play_status.value,
        result_status=game.result_status.value,
        format_snapshot_id=snapshot.id if snapshot else None,
        format_key=snapshot.format_key if snapshot else None,
        format_name=snapshot.format_name if snapshot else None,
        snapshot_schema_version=snapshot.snapshot_schema_version if snapshot else None,
        snapshot_player_count=snapshot.player_count if snapshot else None,
        snapshot_role_names=tuple(role.role_name for role in snapshot.roles) if snapshot else (),
        event_ledger_head_sequence=game.next_event_sequence - 1,
        started_at=game.started_at,
        ended_at=game.ended_at,
    )
    participant_inputs = tuple(
        ParticipantProjectionInput(
            participant_id=participant.id,
            user_id=participant.user_id,
            seat_number=participant.seat_number,
            display_name_snapshot=participant.display_name_snapshot,
            role_name=participant.result.role_name if participant.result else None,
            faction=participant.result.faction.value
            if participant.result and participant.result.faction
            else None,
        )
        for participant in game.participants
    )
    event_inputs = tuple(
        GameEventProjectionInput(
            id=event.id,
            game_id=event.game_id,
            logical_sequence_no=event.logical_sequence_no,
            sequence_no=event.sequence_no,
            phase=event.phase.value,
            round_no=event.round_no,
            event_type=event.event_type,
            actor_participant_id=event.actor_participant_id,
            target_participant_id=event.target_participant_id,
            secondary_target_participant_id=event.secondary_target_participant_id,
            payload=deepcopy(event.payload_json),
            visibility=event.visibility.value,
            source=event.source.value,
            schema_version=event.schema_version,
        )
        for event in event_rows
    )
    return project_game_state(
        context=context,
        participants=participant_inputs,
        events=event_inputs,
        through_logical_sequence=through_logical_sequence,
    )
