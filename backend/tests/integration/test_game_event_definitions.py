"""Server-driven event-definition metadata regressions."""

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.orm import Session

from app.api.routes.game_events import build_event_definition_reads
from app.services.game_event_registry import EVENT_DEFINITIONS
from tests.integration.result_support import API_PREFIX, create_result_scenario


pytestmark = pytest.mark.integration


def test_event_definitions_expose_the_exact_registry_and_payload_contracts(
    api_client: TestClient,
    db_session: Session,
) -> None:
    scenario = create_result_scenario(db_session)
    endpoint = f"{API_PREFIX}/game-events/definitions"

    assert api_client.get(endpoint).status_code == 401
    assert api_client.get(
        endpoint,
        headers=scenario.headers_for(scenario.viewer_id),
    ).status_code == 403

    expected = [item.model_dump(mode="json") for item in build_event_definition_reads()]
    for user_id in (scenario.judge_id, scenario.admin_id):
        response = api_client.get(endpoint, headers=scenario.headers_for(user_id))
        assert response.status_code == 200
        assert response.json() == expected

    assert len(expected) == len(EVENT_DEFINITIONS) == 22
    assert {item["event_type"] for item in expected} == {
        event_type.value for event_type in EVENT_DEFINITIONS
    }
    for item in expected:
        schema = item["payload_schema"]
        assert "$defs" not in schema
        assert schema["additionalProperties"] is False
        assert set(schema.get("required", [])) <= set(schema.get("properties", {}))
