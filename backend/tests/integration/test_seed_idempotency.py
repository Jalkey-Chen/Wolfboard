"""Seed regressions for dual-state validity and stable result identities."""

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import GamePlayStatus, GameResultStatus
from app.models.game import Game
from app.models.game_event import GameEvent
from app.models.game_participant import GameParticipant
from app.models.game_player import GamePlayer
from app.models.game_format_role_snapshot import GameFormatRoleSnapshot
from app.models.game_format_snapshot import GameFormatSnapshot
from app.models.user import User
from app.schemas.game_event import GameEventCreate
from app.scripts.seed import main as seed_main
from app.services.game_event import append_game_event


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
    first_snapshots = list(
        db_session.execute(
            select(
                GameFormatSnapshot.id,
                GameFormatSnapshot.game_id,
                GameFormatSnapshot.format_key,
                GameFormatSnapshot.format_name,
                GameFormatSnapshot.player_count,
            ).order_by(GameFormatSnapshot.id)
        )
    )
    first_snapshot_roles = list(
        db_session.execute(
            select(
                GameFormatRoleSnapshot.id,
                GameFormatRoleSnapshot.format_snapshot_id,
                GameFormatRoleSnapshot.role_name,
                GameFormatRoleSnapshot.faction,
                GameFormatRoleSnapshot.role_count,
                GameFormatRoleSnapshot.display_order,
                GameFormatRoleSnapshot.metadata_json,
            ).order_by(GameFormatRoleSnapshot.id)
        )
    )

    event_game = db_session.scalar(
        select(Game).where(
            Game.play_status == GamePlayStatus.IN_PROGRESS,
            Game.result_status == GameResultStatus.DRAFT,
        )
    )
    assert event_game is not None and event_game.judge_user_id is not None
    judge = db_session.get(User, event_game.judge_user_id)
    assert judge is not None
    manual_event = append_game_event(
        db_session,
        event_game.id,
        GameEventCreate.model_validate(
            {
                "phase": "night",
                "round_no": 1,
                "event_type": "phase_started",
                "payload": {},
                "client_event_id": "seed-preservation-check",
            }
        ),
        judge,
    )
    event_id = manual_event.id
    event_game_id = event_game.id
    next_sequence = db_session.get(Game, event_game_id).next_event_sequence

    seed_main()
    db_session.expire_all()
    preserved_event = db_session.get(GameEvent, event_id)
    assert preserved_event is not None
    assert preserved_event.client_event_id == "seed-preservation-check"
    assert db_session.get(Game, event_game_id).next_event_sequence == next_sequence == 2
    assert all(
        game.next_event_sequence == 1
        for game in db_session.scalars(select(Game).where(Game.id != event_game_id))
    )
    assert list(
        db_session.execute(
            select(GameParticipant.id, GameParticipant.game_id, GameParticipant.user_id)
            .order_by(GameParticipant.id)
        )
    ) == first_participants
    assert list(
        db_session.execute(select(GamePlayer.id, GamePlayer.participant_id).order_by(GamePlayer.id))
    ) == first_results
    assert list(
        db_session.execute(
            select(
                GameFormatSnapshot.id,
                GameFormatSnapshot.game_id,
                GameFormatSnapshot.format_key,
                GameFormatSnapshot.format_name,
                GameFormatSnapshot.player_count,
            ).order_by(GameFormatSnapshot.id)
        )
    ) == first_snapshots
    assert list(
        db_session.execute(
            select(
                GameFormatRoleSnapshot.id,
                GameFormatRoleSnapshot.format_snapshot_id,
                GameFormatRoleSnapshot.role_name,
                GameFormatRoleSnapshot.faction,
                GameFormatRoleSnapshot.role_count,
                GameFormatRoleSnapshot.display_order,
                GameFormatRoleSnapshot.metadata_json,
            ).order_by(GameFormatRoleSnapshot.id)
        )
    ) == first_snapshot_roles

    games = list(db_session.scalars(select(Game)))
    assert games
    for game in games:
        if game.play_status == GamePlayStatus.IN_PROGRESS:
            assert game.started_at is not None
        if game.play_status == GamePlayStatus.ENDED:
            assert game.started_at is not None and game.ended_at is not None
        if game.play_status in {GamePlayStatus.IN_PROGRESS, GamePlayStatus.ENDED}:
            assert game.format_snapshot is not None
        if game.result_status in {GameResultStatus.CONFIRMED, GameResultStatus.REVISED}:
            assert game.play_status == GamePlayStatus.ENDED
            assert game.confirmed_at is not None and game.confirmed_by is not None
