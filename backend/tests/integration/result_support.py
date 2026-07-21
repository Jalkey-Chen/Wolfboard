"""Minimal fixtures and request helpers for result-flow integration tests."""

from dataclasses import dataclass
from datetime import date, datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.enums import (
    FormatRoleFaction,
    GamePlayerFaction,
    GamePlayerFinalStatus,
    GamePlayStatus,
    GameResultStatus,
    GameType,
)
from app.core.security import create_access_token
from app.models.event_day import EventDay
from app.models.format_role import FormatRole
from app.models.game import Game
from app.models.game_format import GameFormat
from app.models.registration import Registration
from app.models.role import Role
from app.models.season import Season
from app.models.user import User
from app.models.user_role import UserRole


API_PREFIX = "/api/v1"


@dataclass(frozen=True)
class ResultScenario:
    season_id: int
    event_day_id: int
    format_id: int
    game_id: int
    admin_id: int
    judge_id: int
    other_judge_id: int
    player_one_id: int
    player_two_id: int
    replacement_player_id: int
    viewer_id: int

    def headers_for(self, user_id: int) -> dict[str, str]:
        token = create_access_token(str(user_id))
        return {"Authorization": f"Bearer {token}"}

    def valid_draft(
        self,
        *,
        player_one_id: int | None = None,
        player_two_id: int | None = None,
    ) -> dict[str, object]:
        return {
            "players": [
                {
                    "user_id": player_one_id or self.player_one_id,
                    "seat_number": 1,
                    "role_name": "Seer",
                    "faction": GamePlayerFaction.GOOD.value,
                    "final_status": GamePlayerFinalStatus.ALIVE.value,
                    "is_winner": True,
                    "remarks": "Good team winner",
                },
                {
                    "user_id": player_two_id or self.player_two_id,
                    "seat_number": 2,
                    "role_name": "Werewolf",
                    "faction": GamePlayerFaction.WOLF.value,
                    "final_status": GamePlayerFinalStatus.ELIMINATED.value,
                    "is_winner": False,
                    "remarks": "Wolf team loss",
                },
            ],
            "adjustments": [
                {
                    "target_seat_number": 1,
                    "adjustment_type": "judge_bonus",
                    "delta": 0.25,
                    "reason": "Clear explanation",
                }
            ],
        }


def _create_user(db: Session, username: str, display_name: str, role: Role) -> User:
    user = User(
        username=username,
        display_name=display_name,
        password_hash="integration-test-password-is-not-used",
        account_status="active",
    )
    db.add(user)
    db.flush()
    db.add(UserRole(user_id=user.id, role_id=role.id))
    return user


def create_result_scenario(
    db: Session,
    *,
    game_type: GameType = GameType.OFFICIAL,
    play_status: GamePlayStatus = GamePlayStatus.SCHEDULED,
    result_status: GameResultStatus = GameResultStatus.EMPTY,
) -> ResultScenario:
    now = datetime.now(timezone.utc)
    roles = {
        key: Role(role_key=key, role_name=key.title(), description=f"Test {key} role")
        for key in ("admin", "judge", "player")
    }
    db.add_all(roles.values())
    db.flush()

    admin = _create_user(db, "admin", "Admin", roles["admin"])
    judge = _create_user(db, "judge", "Assigned Judge", roles["judge"])
    other_judge = _create_user(db, "other-judge", "Other Judge", roles["judge"])
    player_one = _create_user(db, "player-one", "Player One", roles["player"])
    player_two = _create_user(db, "player-two", "Player Two", roles["player"])
    replacement = _create_user(db, "replacement", "Replacement Player", roles["player"])
    viewer = _create_user(db, "viewer", "Authenticated Viewer", roles["player"])
    db.flush()

    season = Season(
        name="Integration Season",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        created_by=admin.id,
    )
    db.add(season)
    db.flush()
    event_day = EventDay(
        season_id=season.id,
        title="Integration Event Day",
        event_date=date(2026, 6, 1),
        venue="Test Venue",
        created_by=admin.id,
    )
    db.add(event_day)
    db.flush()

    game_format = GameFormat(
        format_name="Two Player Regression Format",
        format_key="integration-two-player",
        player_count=2,
        is_system_preset=False,
    )
    db.add(game_format)
    db.flush()
    db.add_all(
        [
            FormatRole(
                format_id=game_format.id,
                role_name="Seer",
                faction=FormatRoleFaction.GOOD,
                role_count=1,
                display_order=1,
            ),
            FormatRole(
                format_id=game_format.id,
                role_name="Werewolf",
                faction=FormatRoleFaction.WOLF,
                role_count=1,
                display_order=2,
            ),
        ]
    )
    db.add_all(
        Registration(event_day_id=event_day.id, user_id=user.id)
        for user in (player_one, player_two, replacement, viewer)
    )
    game = Game(
        event_day_id=event_day.id,
        game_number=1,
        table_number=1,
        format_id=game_format.id,
        judge_user_id=judge.id,
        game_type=game_type,
        play_status=play_status,
        result_status=result_status,
        started_at=now if play_status in {GamePlayStatus.IN_PROGRESS, GamePlayStatus.ENDED} else None,
        ended_at=now if play_status == GamePlayStatus.ENDED else None,
        submitted_at=now if result_status == GameResultStatus.SUBMITTED else None,
        submitted_by=judge.id if result_status == GameResultStatus.SUBMITTED else None,
        confirmed_at=now if result_status in {GameResultStatus.CONFIRMED, GameResultStatus.REVISED} else None,
        confirmed_by=admin.id if result_status in {GameResultStatus.CONFIRMED, GameResultStatus.REVISED} else None,
        cancelled_at=now if play_status == GamePlayStatus.CANCELLED else None,
        cancellation_reason="Cancelled integration fixture" if play_status == GamePlayStatus.CANCELLED else None,
    )
    db.add(game)
    db.commit()

    return ResultScenario(
        season_id=season.id,
        event_day_id=event_day.id,
        format_id=game_format.id,
        game_id=game.id,
        admin_id=admin.id,
        judge_id=judge.id,
        other_judge_id=other_judge.id,
        player_one_id=player_one.id,
        player_two_id=player_two.id,
        replacement_player_id=replacement.id,
        viewer_id=viewer.id,
    )


def create_additional_game(
    db: Session,
    scenario: ResultScenario,
    *,
    game_type: GameType = GameType.OFFICIAL,
    play_status: GamePlayStatus = GamePlayStatus.SCHEDULED,
    result_status: GameResultStatus = GameResultStatus.EMPTY,
    judge_user_id: int | None = None,
) -> int:
    now = datetime.now(timezone.utc)
    existing_count = db.query(Game).filter(Game.event_day_id == scenario.event_day_id).count()
    game = Game(
        event_day_id=scenario.event_day_id,
        game_number=existing_count + 1,
        table_number=1,
        format_id=scenario.format_id,
        judge_user_id=judge_user_id or scenario.judge_id,
        game_type=game_type,
        play_status=play_status,
        result_status=result_status,
        started_at=now if play_status in {GamePlayStatus.IN_PROGRESS, GamePlayStatus.ENDED} else None,
        ended_at=now if play_status == GamePlayStatus.ENDED else None,
        submitted_at=now if result_status == GameResultStatus.SUBMITTED else None,
        submitted_by=scenario.judge_id if result_status == GameResultStatus.SUBMITTED else None,
        confirmed_at=now if result_status in {GameResultStatus.CONFIRMED, GameResultStatus.REVISED} else None,
        confirmed_by=scenario.admin_id if result_status in {GameResultStatus.CONFIRMED, GameResultStatus.REVISED} else None,
        cancelled_at=now if play_status == GamePlayStatus.CANCELLED else None,
        cancellation_reason="Cancelled integration fixture" if play_status == GamePlayStatus.CANCELLED else None,
    )
    db.add(game)
    db.commit()
    return game.id
def save_and_submit(
    client: TestClient,
    scenario: ResultScenario,
    game_id: int,
    payload: dict[str, object] | None = None,
) -> None:
    headers = scenario.headers_for(scenario.judge_id)
    save_response = client.put(
        f"{API_PREFIX}/games/{game_id}/result-draft",
        json=payload or scenario.valid_draft(),
        headers=headers,
    )
    assert save_response.status_code == 200, save_response.text
    submit_response = client.post(
        f"{API_PREFIX}/games/{game_id}/submit-result",
        headers=headers,
    )
    assert submit_response.status_code == 200, submit_response.text


def confirm(
    client: TestClient,
    scenario: ResultScenario,
    game_id: int,
    comment: str = "Approved in integration test",
) -> None:
    response = client.post(
        f"{API_PREFIX}/games/{game_id}/confirm-result",
        json={"comment": comment},
        headers=scenario.headers_for(scenario.admin_id),
    )
    assert response.status_code == 200, response.text
