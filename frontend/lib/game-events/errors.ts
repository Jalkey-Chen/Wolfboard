import { ApiRequestError } from "@/lib/api";
import type { EventFormErrors } from "@/lib/game-events/form-types";


export type WorkbenchError = {
  status: number | null;
  message: string;
  fieldErrors: EventFormErrors;
  retryableWithSameRequest: boolean;
};

function fieldKey(location: unknown): string | null {
  if (!Array.isArray(location)) return null;
  const parts = location.filter((item): item is string => typeof item === "string" && item !== "body");
  if (parts[0] === "payload" && parts[1]) return `payload.${parts[1]}`;
  const aliases: Record<string, string> = {
    round_no: "roundNo",
    event_type: "eventType",
    actor_participant_id: "actorParticipantId",
    target_participant_id: "targetParticipantId",
    secondary_target_participant_id: "secondaryTargetParticipantId",
  };
  return aliases[parts[0]] ?? parts[0] ?? null;
}

export function parseWorkbenchError(error: unknown): WorkbenchError {
  if (!(error instanceof ApiRequestError)) {
    return {
      status: null,
      message: error instanceof Error ? error.message : "Network request failed.",
      fieldErrors: {},
      retryableWithSameRequest: true,
    };
  }

  const fieldErrors: EventFormErrors = {};
  const detail = error.detail;
  const candidateErrors = Array.isArray(detail)
    ? detail
    : detail && typeof detail === "object" && "errors" in detail
      ? (detail as { errors?: unknown }).errors
      : null;
  if (Array.isArray(candidateErrors)) {
    for (const item of candidateErrors) {
      if (!item || typeof item !== "object") continue;
      const record = item as { loc?: unknown; msg?: unknown };
      const key = fieldKey(record.loc);
      if (key && typeof record.msg === "string") fieldErrors[key] = record.msg;
    }
  }
  const structuredMessage = detail && typeof detail === "object" && "message" in detail
    ? (detail as { message?: unknown }).message
    : null;
  return {
    status: error.status,
    message: typeof structuredMessage === "string" ? structuredMessage : error.message,
    fieldErrors,
    retryableWithSameRequest: error.status === null || error.status >= 500,
  };
}
