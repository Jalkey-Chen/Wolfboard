"""Validation helpers for result-draft saves and final submission."""

from collections import Counter

from app.models.game import Game
from app.schemas.game_result import (
    GameResultAdjustmentInput,
    GameResultDraftWrite,
    ValidationMessage,
    ValidationSummary,
)
from app.services.format_snapshot import authoritative_format, authoritative_format_roles


def _message(code: str, message: str, field: str | None = None) -> ValidationMessage:
    """Build a consistent validation message object."""

    return ValidationMessage(code=code, message=message, field=field)


def validate_game_result_payload(
    game: Game,
    payload: GameResultDraftWrite,
    *,
    submit_mode: bool,
) -> ValidationSummary:
    """Validate a game result payload and return blocking errors plus warnings.

    Draft saves are lenient enough to support partial work. Submission mode
    upgrades missing required fields into blocking errors.

    Non-blocking warnings are still returned so the UI can flag player-count
    mismatches and unexpected role names without preventing draft saves.
    """

    errors: list[ValidationMessage] = []
    warnings: list[ValidationMessage] = []

    players = payload.players
    adjustments = payload.adjustments

    if submit_mode and len(players) == 0:
        errors.append(_message("players_required", "At least one player result is required before submission."))

    seat_values = [player.seat_number for player in players if player.seat_number is not None]
    user_values = [player.user_id for player in players if player.user_id is not None]
    participant_values = [player.participant_id for player in players if player.participant_id is not None]

    duplicate_participants = [participant_id for participant_id, count in Counter(participant_values).items() if count > 1]
    if duplicate_participants:
        errors.append(
            _message(
                "duplicate_participant_ids",
                "The same participant cannot appear more than once in a result draft: "
                f"{', '.join(str(participant_id) for participant_id in sorted(duplicate_participants))}.",
                "players",
            )
        )

    duplicate_seats = [seat for seat, count in Counter(seat_values).items() if count > 1]
    if duplicate_seats:
        errors.append(
            _message(
                "duplicate_seat_numbers",
                f"Duplicate seat numbers are not allowed: {', '.join(str(seat) for seat in sorted(duplicate_seats))}.",
                "players",
            )
        )

    duplicate_users = [user_id for user_id, count in Counter(user_values).items() if count > 1]
    if duplicate_users:
        errors.append(
            _message(
                "duplicate_users",
                f"Duplicate users are not allowed in the same game: {', '.join(str(user_id) for user_id in sorted(duplicate_users))}.",
                "players",
            )
        )

    if game.judge_user_id in user_values:
        errors.append(
            _message(
                "judge_in_player_list",
                "The assigned judge cannot also appear in the game player list.",
                "players",
            )
        )

    format_context = authoritative_format(game)
    format_roles = list(authoritative_format_roles(game))
    format_role_names = {format_role.role_name for format_role in format_roles}
    valid_seats = {player.seat_number for player in players if player.seat_number is not None}

    invalid_context_roles = [
        role for role in format_roles if not role.role_name.strip() or role.role_count <= 0
    ]
    configured_role_total = sum(role.role_count for role in format_roles)
    if not format_roles or invalid_context_roles or configured_role_total != format_context.player_count:
        errors.append(
            _message(
                "invalid_format_context",
                "The frozen format context has an invalid role composition and cannot validate results.",
                "players",
            )
        )

    for index, player in enumerate(players, start=1):
        field_prefix = f"players[{index - 1}]"
        if submit_mode:
            if player.seat_number is None:
                errors.append(_message("seat_required", f"Seat number is required for player row {index}.", f"{field_prefix}.seat_number"))
            if player.user_id is None:
                errors.append(_message("user_required", f"User is required for player row {index}.", f"{field_prefix}.user_id"))
            if not player.role_name:
                errors.append(_message("role_required", f"Role name is required for player row {index}.", f"{field_prefix}.role_name"))
            if player.faction is None:
                errors.append(_message("faction_required", f"Faction is required for player row {index}.", f"{field_prefix}.faction"))
            if player.is_winner is None:
                errors.append(_message("winner_required", f"Winner flag is required for player row {index}.", f"{field_prefix}.is_winner"))

        if player.role_name and player.role_name not in format_role_names:
            warnings.append(
                _message(
                    "role_not_in_format",
                    f"Role '{player.role_name}' is not part of the selected format definition.",
                    f"{field_prefix}.role_name",
                )
            )

    expected_player_count = format_context.player_count
    actual_player_count = len(players)
    if actual_player_count > 0 and expected_player_count != actual_player_count:
        warnings.append(
            _message(
                "player_count_mismatch",
                f"The selected format expects {expected_player_count} players, but the draft currently has {actual_player_count}.",
                "players",
            )
        )

    expected_roles = Counter()
    for format_role in format_roles:
        expected_roles[format_role.role_name] += format_role.role_count
    actual_roles = Counter(player.role_name for player in players if player.role_name)
    if players and actual_roles != expected_roles:
        role_message = _message(
            "role_composition_mismatch",
            "The result role composition does not match the frozen format context.",
            "players",
        )
        (errors if submit_mode else warnings).append(role_message)

    for index, adjustment in enumerate(adjustments, start=1):
        field_prefix = f"adjustments[{index - 1}]"
        if adjustment.target_seat_number not in valid_seats:
            errors.append(
                _message(
                    "invalid_adjustment_target",
                    f"Adjustment row {index} targets seat {adjustment.target_seat_number}, which is not present in the draft.",
                    f"{field_prefix}.target_seat_number",
                )
            )

    return ValidationSummary(errors=errors, warnings=warnings)
