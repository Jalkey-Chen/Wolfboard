import type { GameEventBodyPayload } from "@/lib/api";
import type { EventFormState, EventPayloadValue, PendingEventSubmission } from "@/lib/game-events/form-types";


function canonicalize(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(canonicalize);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>)
        .filter(([, item]) => item !== undefined)
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([key, item]) => [key, canonicalize(item)]),
    );
  }
  return value;
}

function normalizePayload(payload: Record<string, EventPayloadValue>): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(payload)
      .filter(([, value]) => value !== null && value !== "")
      .map(([key, value]) => [key, typeof value === "string" ? value.trim() : value]),
  );
}

export function normalizeEventRequest(
  form: EventFormState,
  clientEventId: string,
): GameEventBodyPayload {
  return canonicalize({
    phase: form.phase,
    round_no: Number(form.roundNo),
    event_type: form.eventType,
    actor_participant_id: form.actorParticipantId,
    target_participant_id: form.targetParticipantId,
    secondary_target_participant_id: form.secondaryTargetParticipantId,
    payload: normalizePayload(form.payload),
    occurred_at: form.occurredAt,
    client_event_id: clientEventId,
  }) as GameEventBodyPayload;
}

export function stableRequestFingerprint(request: GameEventBodyPayload): string {
  const withoutClientId = { ...request, client_event_id: undefined };
  const source = JSON.stringify(canonicalize(withoutClientId));
  let hash = 2166136261;
  for (let index = 0; index < source.length; index += 1) {
    hash ^= source.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

export function preparePendingSubmission(
  form: EventFormState,
  existing: PendingEventSubmission | null,
  createUuid: () => string = () => crypto.randomUUID(),
  now: () => string = () => new Date().toISOString(),
): PendingEventSubmission {
  const candidateRequest = normalizeEventRequest(form, existing?.clientEventId ?? "pending");
  const fingerprint = stableRequestFingerprint(candidateRequest);
  if (existing?.fingerprint === fingerprint) return existing;
  const clientEventId = createUuid();
  return {
    clientEventId,
    request: normalizeEventRequest(form, clientEventId),
    fingerprint,
    createdAt: now(),
  };
}
