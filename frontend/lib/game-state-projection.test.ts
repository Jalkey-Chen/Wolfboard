import { afterEach, describe, expect, it, vi } from "vitest";

import {
  getGameDerivedState,
  type GameDerivedState,
} from "@/lib/api";


const derivedStateFixture: GameDerivedState = {
  projection_version: 1,
  projection_kind: "effective_event_projection",
  game_id: 42,
  through_logical_sequence: 12,
  event_ledger_head_sequence: 15,
  effective_event_count: 12,
  last_applied_logical_sequence: 12,
  has_format_snapshot: true,
  is_rule_engine_result: false,
  format_snapshot_id: 8,
  format_key: "wolf-king-guard",
  format_name: "Wolf King Guard",
  snapshot_schema_version: 1,
  phase: {
    current_phase: "night",
    current_round_no: 2,
    phase_is_open: true,
    phase_started_event_id: 12,
    last_completed_phase: "day",
    last_completed_round_no: 1,
    last_completed_event_id: 11,
    last_observed_phase: "night",
    last_observed_round_no: 2,
    last_observed_event_id: 12,
  },
  participants: [{
    participant_id: 7,
    user_id: 107,
    seat_number: 7,
    display_name_snapshot: "Player 7",
    recorded_role_name: "Villager",
    recorded_faction: "good",
    is_active_in_game: true,
    has_exile_record: false,
    has_death_record: false,
    exile_event_ids: [],
    death_event_ids: [],
    exit_event_ids: [],
    first_exit_logical_sequence: null,
    latest_exit_logical_sequence: null,
  }],
  sheriff: {
    badge_status: "held",
    current_sheriff_participant_id: 7,
    elected_event_id: 8,
    last_transfer_event_id: null,
    destroyed_event_id: null,
    current_candidate_participant_ids: [],
    withdrawn_participant_ids: [],
    declaration_provenance: [{ participant_id: 7, event_ids: [4] }],
    withdrawal_provenance: [],
  },
  ballots: [],
  recorded_action_usage: [{
    participant_id: 7,
    recorded_seer_check_count: 0,
    recorded_witch_antidote_count: 0,
    recorded_witch_poison_count: 0,
    recorded_guard_protection_count: 0,
    recorded_hunter_shot_count: 0,
    recorded_wolf_king_shot_count: 0,
    recorded_wolf_self_explosion_count: 0,
    recorded_sheriff_vote_count: 1,
    recorded_exile_vote_count: 0,
  }],
  recorded_actions: [],
  round_summaries: [{
    round_no: 2,
    phase: "night",
    event_count: 1,
    event_ids: [12],
    phase_started_event_ids: [12],
    phase_completed_event_ids: [],
    night_resolved_event_ids: [],
    event_type_counts: [{ event_type: "phase_started", count: 1 }],
  }],
  night_resolutions: [],
  issues: [{
    code: "event_actor_already_out",
    severity: "warning",
    message_key: "projection.issue.event_actor_already_out",
    event_ids: [10],
    participant_ids: [9],
    round_no: 1,
    phase: "day",
    details: {},
  }],
};


afterEach(() => {
  vi.unstubAllGlobals();
});


describe("getGameDerivedState", () => {
  it("requests a typed current-effective prefix without running a browser reducer", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => derivedStateFixture,
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await getGameDerivedState("token", 42, 12);

    expect(result).toEqual(derivedStateFixture);
    expect(result.is_rule_engine_result).toBe(false);
    expect(result.participants[0].recorded_role_name).toBe("Villager");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/games/42/derived-state?through_logical_sequence=12",
      expect.objectContaining({
        cache: "no-store",
        headers: expect.objectContaining({ Authorization: "Bearer token" }),
      }),
    );
  });
});
