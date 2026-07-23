import { describe, expect, it } from "vitest";

import { ApiRequestError, type GameEventDefinition, type GameEventRecord } from "@/lib/api";
import {
  compareDefinitionRegistries,
  createInitialEventForm,
  EVENT_UI_DEFINITIONS,
  initialPayloadForDefinition,
} from "@/lib/game-events/definitions";
import {
  clearEventDraft,
  eventDraftStorageKey,
  loadEventDraft,
  saveEventDraft,
} from "@/lib/game-events/draft-storage";
import { parseWorkbenchError } from "@/lib/game-events/errors";
import { formatGameEvent } from "@/lib/game-events/formatters";
import { preparePendingSubmission, stableRequestFingerprint } from "@/lib/game-events/request-normalization";


function definition(
  eventType: GameEventDefinition["event_type"],
  properties: GameEventDefinition["payload_schema"]["properties"] = {},
): GameEventDefinition {
  return {
    event_type: eventType,
    allowed_phases: ["night", "day"],
    default_visibility: "public",
    required_actor: false,
    required_target: false,
    allows_actor: false,
    allows_target: false,
    allows_secondary_target: false,
    allowed_sources: ["manual"],
    schema_version: 1,
    payload_schema: { type: "object", properties, required: [], additionalProperties: false },
    payload_field_semantics: {},
  };
}

describe("event workbench pure functions", () => {
  it("keeps the client renderer registry complete and detects server drift", () => {
    const all = Object.keys(EVENT_UI_DEFINITIONS).map((type) => definition(type as keyof typeof EVENT_UI_DEFINITIONS));
    expect(compareDefinitionRegistries(all)).toEqual({ missingRenderers: [], unsupportedClientTypes: [] });
    expect(compareDefinitionRegistries(all.slice(1)).unsupportedClientTypes).toEqual(["phase_started"]);
  });

  it("derives payload initial values from server defaults and finite UI controls", () => {
    const vote = definition("sheriff_vote_cast", {
      ballot_no: { type: "integer", exclusiveMinimum: 0 },
      vote_weight: { type: "number", default: 1, exclusiveMinimum: 0 },
    });
    expect(initialPayloadForDefinition(vote)).toEqual({ ballot_no: 1, vote_weight: 1 });
  });

  it("normalizes key order and reuses client IDs only for identical bodies", () => {
    const definitions = [definition("phase_started")];
    const form = createInitialEventForm(definitions);
    form.payload = { z: " value ", a: 1 };
    const first = preparePendingSubmission(form, null, () => "uuid-one", () => "now-one");
    const reordered = { ...form, payload: { a: 1, z: "value" } };
    const retry = preparePendingSubmission(reordered, first, () => "unused");
    expect(retry).toBe(first);
    expect(stableRequestFingerprint(retry.request)).toBe(first.fingerprint);
    const changed = preparePendingSubmission({ ...form, roundNo: 2 }, first, () => "uuid-two", () => "now-two");
    expect(changed.clientEventId).toBe("uuid-two");
    expect(changed.fingerprint).not.toBe(first.fingerprint);
  });

  it("round-trips versioned local drafts without storing unrelated game state", () => {
    const form = createInitialEventForm([definition("phase_started")]);
    saveEventDraft(localStorage, 42, form, null);
    const raw = localStorage.getItem(eventDraftStorageKey(42));
    expect(raw).not.toContain("access_token");
    expect(loadEventDraft(localStorage, 42)?.form).toEqual(form);
    expect(loadEventDraft(localStorage, 7)).toBeNull();
    clearEventDraft(localStorage, 42);
    expect(loadEventDraft(localStorage, 42)).toBeNull();
  });

  it("maps FastAPI validation locations and preserves network retry semantics", () => {
    const validation = parseWorkbenchError(new ApiRequestError("Invalid", [
      { loc: ["body", "payload", "ballot_no"], msg: "Must be positive" },
      { loc: ["body", "actor_participant_id"], msg: "Required" },
    ], 422));
    expect(validation.fieldErrors).toEqual({
      "payload.ballot_no": "Must be positive",
      actorParticipantId: "Required",
    });
    expect(validation.retryableWithSameRequest).toBe(false);
    expect(parseWorkbenchError(new TypeError("offline")).retryableWithSameRequest).toBe(true);
  });

  it("formats participant-aware event summaries without deriving game state", () => {
    const event: GameEventRecord = {
      id: 10,
      game_id: 1,
      sequence_no: 1,
      logical_sequence_no: 1,
      phase: "day",
      round_no: 1,
      event_type: "exile_vote_cast",
      actor_participant_id: 1,
      target_participant_id: 2,
      secondary_target_participant_id: null,
      actor: null,
      target: null,
      secondary_target: null,
      payload: { vote_weight: 1.5 },
      visibility: "public",
      source: "manual",
      schema_version: 1,
      status: "active",
      supersedes_event_id: null,
      revision_reason: null,
      invalidated_at: null,
      invalidated_by_user_id: null,
      invalidation_reason: null,
      created_by_user_id: 1,
      created_by: { user_id: 1, username: "judge", display_name: "Judge" },
      created_at: "2026-07-22T12:00:00Z",
      occurred_at: null,
      client_event_id: "test-event",
    };
    expect(formatGameEvent(event, {
      eventTypeLabel: () => "Exile vote",
      participantLabel: (id) => `${id}号`,
    })).toBe("Exile vote: 1号 → 2号 · ×1.5");
  });
});
