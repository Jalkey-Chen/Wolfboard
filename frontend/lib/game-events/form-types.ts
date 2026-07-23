import type {
  GameEventBodyPayload,
  GameEventPhase,
  GameEventType,
} from "@/lib/api";


export type EventPayloadValue = string | number | boolean | number[] | Record<string, number> | null;

export type EventFormState = {
  phase: GameEventPhase;
  roundNo: number;
  eventType: GameEventType;
  actorParticipantId: number | null;
  targetParticipantId: number | null;
  secondaryTargetParticipantId: number | null;
  payload: Record<string, EventPayloadValue>;
  occurredAt: string | null;
};

export type PendingEventSubmission = {
  clientEventId: string;
  request: GameEventBodyPayload;
  fingerprint: string;
  createdAt: string;
};

export type StoredEventDraft = {
  version: 1;
  formVersion: 1;
  gameId: number;
  form: EventFormState;
  pending: PendingEventSubmission | null;
  savedAt: string;
};

export type ParticipantOption = {
  participantId: number;
  userId: number | null;
  username: string;
  displayName: string;
  seatNumber: number | null;
  roleName: string | null;
};

export type EventFormErrors = Partial<Record<
  "phase" | "roundNo" | "eventType" | "actorParticipantId" |
  "targetParticipantId" | "secondaryTargetParticipantId" | "payload" | string,
  string
>>;
