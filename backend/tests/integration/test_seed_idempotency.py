"""Seed regressions for dual-state validity and stable result identities."""

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import GamePlayStatus, GameResultStatus
from app.models.game import Game
from app.models.game_participant import GameParticipant
from app.models.game_player import GamePlayer
from app.scripts.seed import main as seed_main


pytestmark = pytest.mark.integration


def test_seed_is_idempotent_and_writes_valid_dual_states(db_session: Session) -> None:
    seed_main()
    db_session.expire_all()
    first_participants = list(
        db_session.execute(
            select(GameParticipant.id, GameParticipant.game_id, GameParticipant.user_id)
            .order_by(GameParticipant.id)
        )
    )
    first_results = list(
        db_session.execute(select(GamePlayer.id, GamePlayer.participant_id).order_by(GamePlayer.id))
    )

    seed_main()
    db_session.expire_all()
    assert list(
        db_session.execute(
            select(GameParticipant.id, GameParticipant.game_id, GameParticipant.user_id)
            .order_by(GameParticipant.id)
        )
    ) == first_participants
    assert list(
        db_session.execute(select(GamePlayer.id, GamePlayer.participant_id).order_by(GamePlayer.id))
    ) == first_results

    games = list(db_session.scalars(select(Game)))
    assert games
    for game in games:
        if game.play_status == GamePlayStatus.IN_PROGRESS:
            assert game.started_at is not None
        if game.play_status == GamePlayStatus.ENDED:
            assert game.started_at is not None and game.ended_at is not None
        if game.result_status in {GameResultStatus.CONFIRMED, GameResultStatus.REVISED}:
            assert game.play_status == GamePlayStatus.ENDED
            assert game.confirmed_at is not None and game.confirmed_by is not None
