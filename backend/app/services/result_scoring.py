"""Scoring helpers for draft previews and persisted result calculations."""

from app.core.enums import GamePlayerFaction


def calculate_base_score(faction: GamePlayerFaction | None, is_winner: bool | None) -> float:
    """Return the base score for one player result row.

    The helper tolerates incomplete draft rows by returning `0.0` when the
    row is not ready for a meaningful score calculation yet.
    """

    if faction is None or is_winner is None:
        return 0.0
    if not is_winner:
        return -1.0
    if faction == GamePlayerFaction.WOLF:
        return 1.5
    return 1.0


def calculate_adjustment_score(deltas: list[float]) -> float:
    """Return the sum of all explicit adjustments for a player."""

    return float(sum(deltas))


def calculate_final_score(base_score: float, adjustment_score: float) -> float:
    """Return the final score displayed and persisted for a player."""

    return float(base_score + adjustment_score)
