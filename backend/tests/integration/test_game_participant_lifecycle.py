"""Stable participant identity and result-row reconcile integration coverage."""

from copy import deepcopy

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.game_participant import GameParticipant
from app.models.game_player import GamePlayer
from app.models.score_adjustment import ScoreAdjustment
from app.models.user import User
from tests.integration.result_support import API_PREFIX, create_additional_game, create_result_scenario


pytestmark = pytest.mark.integration


def _endpoint(game_id: int) -> str:
    return f"{API_PREFIX}/games/{game_id}/result-draft"


def _save(client: TestClient, scenario, payload: dict[str, object], game_id: int | None = None):
    return client.put(
        _endpoint(game_id or scenario.game_id),
        json=payload,
        headers=scenario.headers_for(scenario.judge_id),
    )


def _payload_with_ids(payload: dict[str, object], response_json: dict[str, object]) -> dict[str, object]:
    result = deepcopy(payload)
    participants_by_user = {
        player["user_id"]: player["participant_id"]
        for player in response_json["players"]
        if player["user_id"] is not None
    }
    for player in result["players"]:
        player["participant_id"] = participants_by_user[player["user_id"]]
    return result


def test_changed_result_fields_preserve_participant_and_result_ids(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session)
    initial_payload = scenario.valid_draft()
    first = _save(api_client, scenario, initial_payload)
    assert first.status_code == 200, first.text

    changed_payload = _payload_with_ids(initial_payload, first.json())
    changed_payload["players"][0].update(
        role_name="Werewolf",
        faction="wolf",
        final_status="eliminated",
        is_winner=False,
        remarks="Corrected result",
    )
    changed_payload["adjustments"][0]["delta"] = 0.5
    changed = _save(api_client, scenario, changed_payload)
    assert changed.status_code == 200, changed.text

    before = {player["participant_id"]: player["id"] for player in first.json()["players"]}
    after = {player["participant_id"]: player["id"] for player in changed.json()["players"]}
    assert after == before
    corrected = next(player for player in changed.json()["players"] if player["user_id"] == scenario.player_one_id)
    assert corrected["role_name"] == "Werewolf"
    assert corrected["faction"] == "wolf"
    assert corrected["final_status"] == "eliminated"
    assert corrected["is_winner"] is False
    assert corrected["adjustment_score"] == pytest.approx(0.5)


def test_legacy_payload_matching_preserves_ids_and_ambiguous_swap_is_rejected(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session)
    first = _save(api_client, scenario, scenario.valid_draft())
    assert first.status_code == 200, first.text

    repeated = _save(api_client, scenario, scenario.valid_draft())
    assert repeated.status_code == 200, repeated.text
    assert [player["participant_id"] for player in repeated.json()["players"]] == [
        player["participant_id"] for player in first.json()["players"]
    ]
    assert [player["id"] for player in repeated.json()["players"]] == [
        player["id"] for player in first.json()["players"]
    ]

    ambiguous = scenario.valid_draft()
    ambiguous["players"][0]["seat_number"] = 2
    ambiguous["players"][1]["seat_number"] = 1
    response = _save(api_client, scenario, ambiguous)
    assert response.status_code == 409
    assert response.json()["detail"] == "User and seat identify different participants. Reload the result before saving."


def test_display_name_snapshot_does_not_follow_later_user_renames(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session)
    first = _save(api_client, scenario, scenario.valid_draft())
    assert first.status_code == 200, first.text
    participant_id = first.json()["players"][0]["participant_id"]

    user = db_session.get(User, scenario.player_one_id)
    assert user is not None
    user.display_name = "Renamed Account"
    db_session.commit()

    response = api_client.get(
        _endpoint(scenario.game_id),
        headers=scenario.headers_for(scenario.judge_id),
    )
    assert response.status_code == 200
    snapshotted = next(player for player in response.json()["players"] if player["participant_id"] == participant_id)
    assert snapshotted["display_name"] == "Player One"


@pytest.mark.parametrize("seat_order", [(2, 1), (2, 3, 1)])
def test_participants_can_swap_or_cycle_seats_without_changing_identity(
    api_client: TestClient,
    db_session: Session,
    seat_order: tuple[int, ...],
) -> None:
    scenario = create_result_scenario(db_session)
    payload = scenario.valid_draft()
    if len(seat_order) == 3:
        payload["players"].append(
            {
                "user_id": scenario.replacement_player_id,
                "seat_number": 3,
                "role_name": "Villager",
                "faction": "good",
                "final_status": "alive",
                "is_winner": True,
                "remarks": None,
            }
        )
    first = _save(api_client, scenario, payload)
    assert first.status_code == 200, first.text
    changed_payload = _payload_with_ids(payload, first.json())
    identities = {
        player["user_id"]: (player["participant_id"], player["id"])
        for player in first.json()["players"]
    }
    for player, seat_number in zip(changed_payload["players"], seat_order, strict=True):
        player["seat_number"] = seat_number
    changed_payload["adjustments"] = []

    response = _save(api_client, scenario, changed_payload)
    assert response.status_code == 200, response.text
    for player in response.json()["players"]:
        assert (player["participant_id"], player["id"]) == identities[player["user_id"]]


def test_participant_can_change_or_clear_user_and_assign_a_null_seat(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session)
    payload = scenario.valid_draft()
    payload["players"][1]["seat_number"] = None
    payload["adjustments"] = []
    first = _save(api_client, scenario, payload)
    assert first.status_code == 200, first.text
    changed_payload = _payload_with_ids(payload, first.json())
    first_identity = {
        player["user_id"]: (player["participant_id"], player["id"])
        for player in first.json()["players"]
    }
    changed_payload["players"][0]["user_id"] = scenario.replacement_player_id
    changed_payload["players"][1]["user_id"] = None
    changed_payload["players"][1]["seat_number"] = 2

    changed = _save(api_client, scenario, changed_payload)
    assert changed.status_code == 200, changed.text
    by_seat = {player["seat_number"]: player for player in changed.json()["players"]}
    assert (by_seat[1]["participant_id"], by_seat[1]["id"]) == first_identity[scenario.player_one_id]
    assert by_seat[1]["user_id"] == scenario.replacement_player_id
    assert by_seat[1]["display_name"] == "Replacement Player"
    assert (by_seat[2]["participant_id"], by_seat[2]["id"]) == first_identity[scenario.player_two_id]
    assert by_seat[2]["user_id"] is None
    assert by_seat[2]["display_name"] == "Player Two"


def test_two_participants_can_swap_users_without_changing_identity(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session)
    first = _save(api_client, scenario, scenario.valid_draft())
    assert first.status_code == 200, first.text
    payload = _payload_with_ids(scenario.valid_draft(), first.json())
    identities_by_seat = {
        player["seat_number"]: (player["participant_id"], player["id"])
        for player in first.json()["players"]
    }
    payload["players"][0]["user_id"] = scenario.player_two_id
    payload["players"][1]["user_id"] = scenario.player_one_id

    response = _save(api_client, scenario, payload)
    assert response.status_code == 200, response.text
    by_seat = {player["seat_number"]: player for player in response.json()["players"]}
    assert (by_seat[1]["participant_id"], by_seat[1]["id"]) == identities_by_seat[1]
    assert (by_seat[2]["participant_id"], by_seat[2]["id"]) == identities_by_seat[2]
    assert by_seat[1]["user_id"] == scenario.player_two_id
    assert by_seat[2]["user_id"] == scenario.player_one_id


@pytest.mark.parametrize(
    ("mutation", "error_code"),
    [
        (lambda payload: payload["players"][1].update(seat_number=1), "duplicate_seat_numbers"),
        (lambda payload: payload["players"][1].update(user_id=payload["players"][0]["user_id"]), "duplicate_users"),
        (lambda payload: payload["players"][1].update(participant_id=payload["players"][0]["participant_id"]), "duplicate_participant_ids"),
    ],
)
def test_duplicate_final_identity_fields_are_rejected(
    api_client: TestClient,
    db_session: Session,
    mutation,
    error_code: str,
) -> None:
    scenario = create_result_scenario(db_session)
    first = _save(api_client, scenario, scenario.valid_draft())
    assert first.status_code == 200, first.text
    payload = _payload_with_ids(scenario.valid_draft(), first.json())
    mutation(payload)

    response = _save(api_client, scenario, payload)
    assert response.status_code == 422
    assert error_code in {error["code"] for error in response.json()["detail"]["errors"]}


def test_participant_from_another_game_is_rejected(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session)
    other_game_id = create_additional_game(db_session, scenario)
    first = _save(api_client, scenario, scenario.valid_draft())
    assert first.status_code == 200, first.text
    payload = scenario.valid_draft()
    payload["players"][0]["participant_id"] = first.json()["players"][0]["participant_id"]

    response = _save(api_client, scenario, payload, other_game_id)
    assert response.status_code == 409
    assert response.json()["detail"] == "Participant does not belong to this game."


def test_unknown_participant_id_is_rejected(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session)
    payload = scenario.valid_draft()
    payload["players"][0]["participant_id"] = 999_999

    response = _save(api_client, scenario, payload)
    assert response.status_code == 422
    assert response.json()["detail"] == "Participant does not exist."


def test_row_addition_and_removal_only_changes_the_targeted_identity(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session)
    first_payload = scenario.valid_draft()
    first_payload["adjustments"][0]["target_seat_number"] = 2
    first = _save(api_client, scenario, first_payload)
    assert first.status_code == 200, first.text
    first_by_user = {player["user_id"]: player for player in first.json()["players"]}
    payload = _payload_with_ids(first_payload, first.json())
    payload["players"] = [payload["players"][0]]
    payload["adjustments"] = []
    payload["players"].append(
        {
            "participant_id": None,
            "user_id": scenario.replacement_player_id,
            "seat_number": 3,
            "role_name": "Villager",
            "faction": "good",
            "final_status": "alive",
            "is_winner": True,
            "remarks": "Added later",
        }
    )

    changed = _save(api_client, scenario, payload)
    assert changed.status_code == 200, changed.text
    changed_by_user = {player["user_id"]: player for player in changed.json()["players"]}
    assert set(changed_by_user) == {scenario.player_one_id, scenario.replacement_player_id}
    assert changed_by_user[scenario.player_one_id]["participant_id"] == first_by_user[scenario.player_one_id]["participant_id"]
    assert changed_by_user[scenario.player_one_id]["id"] == first_by_user[scenario.player_one_id]["id"]
    assert changed_by_user[scenario.replacement_player_id]["participant_id"] not in {
        player["participant_id"] for player in first.json()["players"]
    }

    db_session.expire_all()
    participant_ids = set(db_session.scalars(select(GameParticipant.id).where(GameParticipant.game_id == scenario.game_id)))
    player_participant_ids = set(db_session.scalars(select(GamePlayer.participant_id).where(GamePlayer.game_id == scenario.game_id)))
    assert participant_ids == player_participant_ids
    assert first_by_user[scenario.player_two_id]["participant_id"] not in participant_ids
    assert db_session.scalar(
        select(ScoreAdjustment).where(ScoreAdjustment.game_player_id == first_by_user[scenario.player_two_id]["id"])
    ) is None
