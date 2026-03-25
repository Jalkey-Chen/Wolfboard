"""Unit tests for milestone 4 scoring helpers."""

from app.core.enums import GamePlayerFaction
from app.services.result_scoring import (
    calculate_adjustment_score,
    calculate_base_score,
    calculate_final_score,
)


def test_calculate_base_score_for_wolf_winner() -> None:
    """Wolf winners should receive the configured 1.5 base score."""

    assert calculate_base_score(GamePlayerFaction.WOLF, True) == 1.5


def test_calculate_final_score_includes_adjustments() -> None:
    """Final score should combine the base score and aggregated adjustments."""

    adjustment_score = calculate_adjustment_score([0.5, -1.0, 2.0])
    assert adjustment_score == 1.5
    assert calculate_final_score(1.0, adjustment_score) == 2.5
