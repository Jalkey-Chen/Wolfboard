"""Result-draft loading, persistence, permission, and submission helpers."""

from collections import defaultdict
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import GamePlayStatus, GameResultStatus, ScoreAdjustmentType
from app.models.event_day import EventDay
from app.models.game import Game
from app.models.game_participant import GameParticipant
from app.models.game_player import GamePlayer
from app.models.game_format import GameFormat
from app.models.registration import Registration
from app.models.score_adjustment import ScoreAdjustment
from app.models.user import User
from app.models.user_role import UserRole
from app.schemas.game import GameDetail, GameSummary
from app.schemas.game_format import FormatRoleRead
from app.schemas.game_result import (
    GameResultAdjustmentRead,
    GameResultDraftRead,
    GameResultDraftWrite,
    GameResultPlayerInput,
    GameResultPlayerRead,
    SelectablePlayerRead,
    ValidationSummary,
)
from app.services.result_scoring import calculate_adjustment_score, calculate_base_score, calculate_final_score
from app.services.result_validation import validate_game_result_payload
from app.services.audit import build_game_snapshot
from app.services.game_state import (
    lock_game_state,
    transition_play_status,
    transition_result_status,
    validate_game_state,
    write_game_state_audit,
)


GAME_RESULT_LOAD_OPTIONS = (
    selectinload(Game.event_day).selectinload(EventDay.season),
    selectinload(Game.event_day).selectinload(EventDay.registrations).selectinload(Registration.user),
    selectinload(Game.format).selectinload(GameFormat.format_roles),
    selectinload(Game.judge).selectinload(User.user_roles).selectinload(UserRole.role),
    selectinload(Game.participants).selectinload(GameParticipant.user),
    selectinload(Game.participants).selectinload(GameParticipant.result).selectinload(GamePlayer.adjustments),
    selectinload(Game.players).selectinload(GamePlayer.participant).selectinload(GameParticipant.user),
    selectinload(Game.players).selectinload(GamePlayer.adjustments),
)


def get_game_result_or_404(db: Session, game_id: int) -> Game:
    """Return a game with result-related context preloaded or raise 404."""

    statement = select(Game).options(*GAME_RESULT_LOAD_OPTIONS).where(Game.id == game_id)
    game = db.scalar(statement)
    if game is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found.")
    return game


def _sorted_players(game: Game) -> list[GamePlayer]:
    """Return result rows in stable seat-first display order."""

    return sorted(
        game.players,
        key=lambda player: (
            player.seat_number is None,
            player.seat_number if player.seat_number is not None else 0,
            player.participant_id,
        ),
    )


def ensure_can_view_game_result(game: Game, current_user: User) -> None:
    """Enforce result-draft visibility rules for admins and the assigned judge."""

    if "admin" in current_user.roles:
        return
    if game.result_status in {GameResultStatus.CONFIRMED, GameResultStatus.REVISED}:
        return
    if current_user.id == game.judge_user_id and "judge" in current_user.roles:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this game result.")


def ensure_can_edit_game_result(game: Game, current_user: User) -> None:
    """Enforce judge-owned edit rules for draft and in-progress games only."""

    if "judge" not in current_user.roles or current_user.id != game.judge_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the assigned judge can edit this game result.")
    if game.play_status == GamePlayStatus.CANCELLED or game.result_status not in {
        GameResultStatus.EMPTY,
        GameResultStatus.DRAFT,
        GameResultStatus.REJECTED,
    }:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Submitted or closed games can no longer be edited by the judge.",
        )


def _build_game_detail(game: Game, current_user: User) -> GameDetail:
    """Reuse the existing game detail shape inside result-draft payloads."""

    can_view_internal_fields = "admin" in current_user.roles or current_user.id == game.judge_user_id
    return GameDetail(
        **GameSummary.model_validate(game).model_dump(),
        event_day_venue=game.event_day.venue,
        format=game.format,
        judge=game.judge,
        has_result_draft=game.has_result_draft,
        submitted_at=game.submitted_at if can_view_internal_fields else None,
        submitted_by=game.submitted_by if can_view_internal_fields else None,
        confirmed_at=game.confirmed_at if can_view_internal_fields else None,
        confirmed_by=game.confirmed_by if can_view_internal_fields else None,
    )


def _build_selectable_players(game: Game) -> list[SelectablePlayerRead]:
    """Return event-day registration users that can be picked in the result UI.

    The assigned judge is excluded because the same user cannot judge and play
    in the same game.
    """

    options: dict[int, SelectablePlayerRead] = {}
    for registration in game.event_day.registrations:
        if registration.user_id == game.judge_user_id:
            continue
        options[registration.user_id] = SelectablePlayerRead(
            user_id=registration.user_id,
            username=registration.username,
            display_name=registration.display_name,
            registration_status=registration.registration_status.value,
            check_in_status=registration.check_in_status.value,
        )

    for game_player in _sorted_players(game):
        if game_player.user_id is None or game_player.user_id == game.judge_user_id:
            continue
        options.setdefault(
            game_player.user_id,
            SelectablePlayerRead(
                user_id=game_player.user_id,
                username=game_player.username,
                display_name=game_player.display_name,
            ),
        )

    return sorted(options.values(), key=lambda option: (option.display_name.lower(), option.user_id))


def _build_validation(game: Game) -> tuple[GameResultDraftWrite, ValidationSummary]:
    """Build a validation-ready payload from persisted rows."""

    payload = GameResultDraftWrite(
        players=[
            {
                "user_id": player.user_id,
                "participant_id": player.participant_id,
                "seat_number": player.seat_number,
                "role_name": player.role_name,
                "faction": player.faction,
                "final_status": player.final_status,
                "is_winner": player.is_winner,
                "remarks": player.remarks,
            }
            for player in _sorted_players(game)
        ],
        adjustments=[
            {
                "target_seat_number": adjustment.target_seat_number,
                "adjustment_type": adjustment.adjustment_type,
                "delta": adjustment.delta,
                "reason": adjustment.reason,
            }
            for player in _sorted_players(game)
            for adjustment in player.adjustments
            if adjustment.target_seat_number is not None
        ],
    )
    return payload, validate_game_result_payload(game, payload, submit_mode=True)


def build_game_result_response(game: Game, current_user: User) -> GameResultDraftRead:
    """Serialize a game result draft with options, validation, and editability."""

    payload, validation = _build_validation(game)
    _ = payload
    return GameResultDraftRead(
        game=_build_game_detail(game, current_user),
        players=[GameResultPlayerRead.model_validate(player) for player in _sorted_players(game)],
        adjustments=[
            GameResultAdjustmentRead.model_validate(adjustment)
            for player in _sorted_players(game)
            for adjustment in player.adjustments
        ],
        format_roles=[FormatRoleRead.model_validate(format_role) for format_role in game.format.format_roles],
        selectable_players=_build_selectable_players(game),
        validation=validation,
        editable=(
            "judge" in current_user.roles
            and current_user.id == game.judge_user_id
            and game.play_status != GamePlayStatus.CANCELLED
            and game.result_status
            in {GameResultStatus.EMPTY, GameResultStatus.DRAFT, GameResultStatus.REJECTED}
        ),
    )


def _collect_adjustment_notes(adjustments: list[ScoreAdjustment]) -> tuple[str | None, str | None]:
    """Derive aggregate bonus and penalty note strings for a player row."""

    bonus_reasons = [
        adjustment.reason
        for adjustment in adjustments
        if adjustment.adjustment_type == ScoreAdjustmentType.JUDGE_BONUS and adjustment.reason
    ]
    penalty_reasons = [
        adjustment.reason
        for adjustment in adjustments
        if adjustment.adjustment_type in {ScoreAdjustmentType.LATE_PENALTY, ScoreAdjustmentType.CONDUCT_PENALTY} and adjustment.reason
    ]
    return (
        "; ".join(bonus_reasons) if bonus_reasons else None,
        "; ".join(penalty_reasons) if penalty_reasons else None,
    )


def _participant_conflict(detail: str) -> None:
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def _resolve_participants(
    db: Session,
    game: Game,
    payload: GameResultDraftWrite,
) -> list[tuple[GameResultPlayerInput, GameParticipant | None]]:
    """Resolve write rows to existing participants without guessing through ambiguity."""

    existing = list(game.participants)
    by_id = {participant.id: participant for participant in existing}
    by_user = {participant.user_id: participant for participant in existing if participant.user_id is not None}
    by_seat = {participant.seat_number: participant for participant in existing if participant.seat_number is not None}
    explicitly_referenced_ids = {
        player.participant_id
        for player in payload.players
        if player.participant_id is not None
    }
    resolved: list[tuple[GameResultPlayerInput, GameParticipant | None]] = []
    used_ids: set[int] = set()

    for player_input in payload.players:
        participant: GameParticipant | None
        if player_input.participant_id is not None:
            participant = by_id.get(player_input.participant_id)
            if participant is None:
                referenced = db.get(GameParticipant, player_input.participant_id)
                if referenced is not None:
                    _participant_conflict("Participant does not belong to this game.")
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Participant does not exist.",
                )
        else:
            user_match = by_user.get(player_input.user_id) if player_input.user_id is not None else None
            seat_match = by_seat.get(player_input.seat_number) if player_input.seat_number is not None else None
            if user_match is not None and user_match.id in explicitly_referenced_ids:
                user_match = None
            if seat_match is not None and seat_match.id in explicitly_referenced_ids:
                seat_match = None
            if user_match is not None and seat_match is not None and user_match.id != seat_match.id:
                _participant_conflict(
                    "User and seat identify different participants. Reload the result before saving."
                )
            participant = user_match or seat_match

        if participant is not None:
            if participant.id in used_ids:
                _participant_conflict("The same participant was resolved more than once.")
            used_ids.add(participant.id)
        resolved.append((player_input, participant))

    return resolved


def reconcile_game_result_rows(db: Session, game: Game, payload: GameResultDraftWrite, current_user: User) -> None:
    """Reconcile a full draft while preserving retained participant and result IDs."""

    resolved = _resolve_participants(db, game, payload)
    requested_user_ids = {player.user_id for player in payload.players if player.user_id is not None}
    users_by_id = {
        user.id: user
        for user in db.scalars(select(User).where(User.id.in_(requested_user_ids)))
    }
    missing_user_ids = requested_user_ids - users_by_id.keys()
    if missing_user_ids:
        _participant_conflict(
            f"Unknown user IDs: {', '.join(str(user_id) for user_id in sorted(missing_user_ids))}."
        )

    retained_ids = {participant.id for _, participant in resolved if participant is not None}
    removed_participants = [participant for participant in game.participants if participant.id not in retained_ids]

    # Clear changing unique values in one flush so swaps and cycles cannot trip
    # the final-state uniqueness constraints halfway through the reconcile.
    for player_input, participant in resolved:
        if participant is None:
            continue
        if participant.user_id != player_input.user_id:
            participant.user_id = None
        if participant.seat_number != player_input.seat_number:
            participant.seat_number = None
    for participant in removed_participants:
        participant.user_id = None
        participant.seat_number = None
    db.flush()

    resolved_participants: list[tuple[GameResultPlayerInput, GameParticipant]] = []
    for player_input, participant in resolved:
        user = users_by_id.get(player_input.user_id)
        if participant is None:
            participant = GameParticipant(
                game_id=game.id,
                user_id=player_input.user_id,
                seat_number=player_input.seat_number,
                display_name_snapshot=user.display_name if user is not None else None,
            )
            db.add(participant)
        else:
            previous_user_id = participant.user_id
            participant.user_id = player_input.user_id
            participant.seat_number = player_input.seat_number
            if user is not None and (previous_user_id != player_input.user_id or participant.display_name_snapshot is None):
                participant.display_name_snapshot = user.display_name
        resolved_participants.append((player_input, participant))

    db.flush()
    for participant in removed_participants:
        db.delete(participant)

    players_by_seat: dict[int, GamePlayer] = {}
    result_rows: list[GamePlayer] = []
    for player_input, participant in resolved_participants:
        game_player = participant.result
        if game_player is None:
            game_player = GamePlayer(game_id=game.id, participant=participant)
            db.add(game_player)
        game_player.role_name = player_input.role_name
        game_player.faction = player_input.faction
        game_player.final_status = player_input.final_status
        game_player.is_winner = player_input.is_winner
        game_player.remarks = player_input.remarks
        game_player.base_score = calculate_base_score(player_input.faction, player_input.is_winner)
        game_player.adjustment_score = 0.0
        game_player.final_score = game_player.base_score
        result_rows.append(game_player)
        if player_input.seat_number is not None:
            players_by_seat[player_input.seat_number] = game_player

    db.flush()
    # Adjustment rows remain replace-on-save because they have no client-facing
    # identity contract; replacing only these children preserves GamePlayer IDs.
    for game_player in result_rows:
        game_player.adjustments.clear()
    db.flush()

    adjustments_by_player_id: dict[int, list[ScoreAdjustment]] = defaultdict(list)
    deltas_by_player_id: dict[int, list[float]] = defaultdict(list)
    for adjustment_input in payload.adjustments:
        target_player = players_by_seat[adjustment_input.target_seat_number]
        adjustment = ScoreAdjustment(
            adjustment_type=adjustment_input.adjustment_type,
            delta=adjustment_input.delta,
            reason=adjustment_input.reason,
            created_by=current_user.id,
        )
        target_player.adjustments.append(adjustment)
        adjustments_by_player_id[target_player.id].append(adjustment)
        deltas_by_player_id[target_player.id].append(adjustment_input.delta)

    for player in result_rows:
        adjustment_score = calculate_adjustment_score(deltas_by_player_id[player.id])
        player.adjustment_score = adjustment_score
        player.final_score = calculate_final_score(player.base_score, adjustment_score)
        player.judge_bonus_note, player.penalty_note = _collect_adjustment_notes(adjustments_by_player_id[player.id])
    db.flush()


def _raise_validation_error(message: str, validation: ValidationSummary) -> None:
    """Raise a normalized validation error payload for API callers."""

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={
            "message": message,
            "errors": [item.model_dump() for item in validation.errors],
            "warnings": [item.model_dump() for item in validation.warnings],
        },
    )


def save_game_result_draft(db: Session, game: Game, payload: GameResultDraftWrite, current_user: User) -> Game:
    """Reconcile a draft and record any compatible play/result transitions."""

    game = lock_game_state(db, game, options=GAME_RESULT_LOAD_OPTIONS)
    ensure_can_edit_game_result(game, current_user)
    validation = validate_game_result_payload(game, payload, submit_mode=False)
    if validation.errors:
        _raise_validation_error("Draft validation failed.", validation)

    old_snapshot = build_game_snapshot(game)
    reconcile_game_result_rows(db, game, payload, current_user)
    state_changed = False
    if game.play_status == GamePlayStatus.SCHEDULED:
        state_changed = transition_play_status(
            db,
            game,
            GamePlayStatus.IN_PROGRESS,
            transition_key="auto_start_on_draft",
            changed_by=current_user.id,
        ) or state_changed
    if game.result_status in {GameResultStatus.EMPTY, GameResultStatus.REJECTED}:
        state_changed = transition_result_status(
            db,
            game,
            GameResultStatus.DRAFT,
            transition_key="save_result_draft",
            changed_by=current_user.id,
        ) or state_changed
    validate_game_state(game)
    if state_changed:
        write_game_state_audit(
            db,
            game=game,
            current_user=current_user,
            action_type="save_result_draft",
            old_snapshot=old_snapshot,
        )
    db.commit()
    # Return a newly loaded aggregate so relationship order and replaced
    # adjustment children exactly match the committed draft.
    db.expire_all()
    return get_game_result_or_404(db, game.id)


def submit_game_result(db: Session, game: Game, current_user: User) -> Game:
    """Validate the current persisted draft and mark the game as submitted."""

    game = lock_game_state(db, game, options=GAME_RESULT_LOAD_OPTIONS)
    if "judge" not in current_user.roles or current_user.id != game.judge_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the assigned judge can submit this game result.")
    if game.result_status != GameResultStatus.DRAFT:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only a saved draft can be submitted.")
    if game.play_status not in {GamePlayStatus.IN_PROGRESS, GamePlayStatus.ENDED}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The game must be in progress or ended before submission.")
    payload, validation = _build_validation(game)
    _ = payload
    if validation.errors:
        _raise_validation_error("Result submission validation failed.", validation)

    old_snapshot = build_game_snapshot(game)
    if game.play_status == GamePlayStatus.IN_PROGRESS:
        transition_play_status(
            db,
            game,
            GamePlayStatus.ENDED,
            transition_key="auto_end_on_submit",
            changed_by=current_user.id,
        )
    game.submitted_at = datetime.now(timezone.utc)
    game.submitted_by = current_user.id
    transition_result_status(
        db,
        game,
        GameResultStatus.SUBMITTED,
        transition_key="submit_result",
        changed_by=current_user.id,
    )
    validate_game_state(game)
    write_game_state_audit(
        db,
        game=game,
        current_user=current_user,
        action_type="submit_result",
        old_snapshot=old_snapshot,
    )
    db.commit()
    return get_game_result_or_404(db, game.id)
