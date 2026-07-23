import type { GameEventParticipantSummary, GameEventRecord } from "@/lib/api";


export type EventFormatterContext = {
  eventTypeLabel: (eventType: GameEventRecord["event_type"]) => string;
  participantLabel?: (participantId: number) => string | null;
};

function participantText(
  participant: GameEventParticipantSummary | null,
  participantId: number | null,
  context: EventFormatterContext,
): string | null {
  if (participantId === null) return null;
  const external = context.participantLabel?.(participantId);
  if (external) return external;
  if (participant) {
    const seat = participant.seat_number === null ? "?" : participant.seat_number;
    return `${seat}号 · ${participant.display_name_snapshot ?? `#${participant.participant_id}`}`;
  }
  return `#${participantId}`;
}

export function formatGameEvent(
  event: GameEventRecord,
  context: EventFormatterContext,
): string {
  const actor = participantText(event.actor, event.actor_participant_id, context);
  const target = participantText(event.target, event.target_participant_id, context);
  const label = context.eventTypeLabel(event.event_type);
  const payload = event.payload;
  if (event.event_type === "wolf_kill_selected" && target) return `${label}: ${target}`;
  if (["sheriff_vote_cast", "exile_vote_cast"].includes(event.event_type) && actor) {
    return `${label}: ${actor} → ${target ?? "abstain"} · ×${String(payload.vote_weight ?? 1)}`;
  }
  if (event.event_type === "seer_checked" && actor && target) {
    return `${label}: ${actor} → ${target} · ${String(payload.result_faction ?? "")}`;
  }
  if (event.event_type === "player_died" && target) {
    return `${label}: ${target} · ${String(payload.cause ?? "")}`;
  }
  if (actor && target) return `${label}: ${actor} → ${target}`;
  if (target) return `${label}: ${target}`;
  if (actor) return `${label}: ${actor}`;
  return label;
}

export function compactPayload(payload: Record<string, unknown>): string {
  const entries = Object.entries(payload);
  if (entries.length === 0) return "—";
  return entries.map(([key, value]) => {
    if (Array.isArray(value)) return `${key}: ${value.join(", ")}`;
    if (value && typeof value === "object") return `${key}: ${JSON.stringify(value)}`;
    return `${key}: ${String(value)}`;
  }).join(" · ");
}
