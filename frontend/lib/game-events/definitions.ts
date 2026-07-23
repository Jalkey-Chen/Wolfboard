import type {
  GameEventDefinition,
  GameEventPhase,
  GameEventType,
  JsonSchemaNode,
} from "@/lib/api";
import type { EventFormState, EventPayloadValue } from "@/lib/game-events/form-types";


export type EventCategory = "flow" | "night" | "sheriff" | "exile" | "skills";
export type PayloadFieldKind =
  | "text"
  | "boolean"
  | "enum"
  | "positive_integer"
  | "positive_number"
  | "participant_id_list"
  | "event_id"
  | "event_id_list"
  | "tally";

export type EventUiDefinition = {
  category: EventCategory;
  quick: boolean;
  payloadFields: Array<{ name: string; kind: PayloadFieldKind }>;
};

const fields = (...items: Array<[string, PayloadFieldKind]>) =>
  items.map(([name, kind]) => ({ name, kind }));

export const EVENT_UI_DEFINITIONS: Record<GameEventType, EventUiDefinition> = {
  phase_started: { category: "flow", quick: false, payloadFields: [] },
  phase_completed: { category: "flow", quick: false, payloadFields: fields(["note", "text"]) },
  night_resolved: { category: "flow", quick: false, payloadFields: fields(["no_public_death", "boolean"], ["note", "text"]) },
  wolf_kill_selected: { category: "night", quick: true, payloadFields: fields(["selection_note", "text"]) },
  seer_checked: { category: "night", quick: true, payloadFields: fields(["result_faction", "enum"]) },
  witch_saved: { category: "night", quick: true, payloadFields: fields(["potion", "enum"]) },
  witch_poisoned: { category: "night", quick: true, payloadFields: fields(["potion", "enum"]) },
  guard_protected: { category: "night", quick: false, payloadFields: [] },
  sheriff_candidate_declared: { category: "sheriff", quick: false, payloadFields: [] },
  sheriff_candidate_withdrew: { category: "sheriff", quick: false, payloadFields: [] },
  sheriff_vote_cast: { category: "sheriff", quick: true, payloadFields: fields(["ballot_no", "positive_integer"], ["vote_weight", "positive_number"]) },
  sheriff_elected: { category: "sheriff", quick: false, payloadFields: fields(["ballot_no", "positive_integer"], ["tally", "tally"]) },
  sheriff_badge_transferred: { category: "sheriff", quick: false, payloadFields: fields(["reason", "text"]) },
  sheriff_badge_destroyed: { category: "sheriff", quick: false, payloadFields: fields(["reason", "text"]) },
  exile_vote_cast: { category: "exile", quick: true, payloadFields: fields(["ballot_no", "positive_integer"], ["vote_weight", "positive_number"]) },
  vote_tied: { category: "exile", quick: false, payloadFields: fields(["vote_kind", "enum"], ["ballot_no", "positive_integer"], ["candidate_participant_ids", "participant_id_list"]) },
  exile_revote_started: { category: "exile", quick: false, payloadFields: fields(["ballot_no", "positive_integer"], ["eligible_participant_ids", "participant_id_list"]) },
  player_exiled: { category: "exile", quick: false, payloadFields: fields(["ballot_no", "positive_integer"]) },
  hunter_shot: { category: "skills", quick: false, payloadFields: fields(["trigger_event_id", "event_id"]) },
  wolf_self_exploded: { category: "skills", quick: false, payloadFields: fields(["note", "text"]) },
  wolf_king_shot: { category: "skills", quick: false, payloadFields: fields(["trigger_event_id", "event_id"]) },
  player_died: { category: "skills", quick: true, payloadFields: fields(["cause", "enum"], ["source_event_ids", "event_id_list"], ["public_note", "text"]) },
};

export const EVENT_CATEGORY_ORDER: EventCategory[] = ["flow", "night", "sheriff", "exile", "skills"];

function unwrapSchema(schema: JsonSchemaNode | undefined): JsonSchemaNode {
  if (!schema?.anyOf) return schema ?? {};
  return schema.anyOf.find((item) => item.type !== "null") ?? schema;
}

export function schemaForPayloadField(
  definition: GameEventDefinition,
  fieldName: string,
): JsonSchemaNode {
  return unwrapSchema(definition.payload_schema.properties?.[fieldName]);
}

export function initialPayloadForDefinition(
  definition: GameEventDefinition,
): Record<string, EventPayloadValue> {
  const ui = EVENT_UI_DEFINITIONS[definition.event_type];
  return Object.fromEntries(ui.payloadFields.map(({ name, kind }) => {
    const schema = schemaForPayloadField(definition, name);
    if (schema.const !== undefined) return [name, schema.const as EventPayloadValue];
    if (schema.default !== undefined) return [name, schema.default as EventPayloadValue];
    if (kind === "boolean") return [name, false];
    if (kind === "positive_integer" || kind === "positive_number") return [name, 1];
    if (kind === "participant_id_list" || kind === "event_id_list") return [name, []];
    if (kind === "tally") return [name, {}];
    if (kind === "enum") return [name, (schema.enum?.[0] ?? "") as EventPayloadValue];
    return [name, ""];
  }));
}

export function createInitialEventForm(
  definitions: GameEventDefinition[],
  recent?: { phase: GameEventPhase; round_no: number },
): EventFormState {
  const definition = definitions.find((item) => item.event_type === "phase_started") ?? definitions[0];
  if (!definition) {
    return {
      phase: recent?.phase ?? "night",
      roundNo: recent?.round_no ?? 1,
      eventType: "phase_started",
      actorParticipantId: null,
      targetParticipantId: null,
      secondaryTargetParticipantId: null,
      payload: {},
      occurredAt: null,
    };
  }
  return {
    phase: recent?.phase ?? "night",
    roundNo: recent?.round_no ?? 1,
    eventType: definition.event_type,
    actorParticipantId: null,
    targetParticipantId: null,
    secondaryTargetParticipantId: null,
    payload: initialPayloadForDefinition(definition),
    occurredAt: null,
  };
}

export function selectEventType(
  form: EventFormState,
  definition: GameEventDefinition,
): EventFormState {
  const phase = definition.allowed_phases.length === 1 ? definition.allowed_phases[0] : form.phase;
  return {
    ...form,
    phase,
    eventType: definition.event_type,
    actorParticipantId: null,
    targetParticipantId: null,
    secondaryTargetParticipantId: null,
    payload: initialPayloadForDefinition(definition),
  };
}

export function compareDefinitionRegistries(definitions: GameEventDefinition[]) {
  const server = new Set(definitions.map((item) => item.event_type));
  const client = new Set(Object.keys(EVENT_UI_DEFINITIONS) as GameEventType[]);
  return {
    missingRenderers: [...server].filter((item) => !client.has(item)),
    unsupportedClientTypes: [...client].filter((item) => !server.has(item)),
  };
}
