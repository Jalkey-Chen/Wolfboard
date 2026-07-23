import type { EventFormState, PendingEventSubmission, StoredEventDraft } from "@/lib/game-events/form-types";


export const EVENT_DRAFT_VERSION = 1;

export function eventDraftStorageKey(gameId: number): string {
  return `wolfboard:event-draft:v1:${gameId}`;
}

export function saveEventDraft(
  storage: Pick<Storage, "setItem">,
  gameId: number,
  form: EventFormState,
  pending: PendingEventSubmission | null,
): void {
  const value: StoredEventDraft = {
    version: EVENT_DRAFT_VERSION,
    formVersion: 1,
    gameId,
    form,
    pending,
    savedAt: new Date().toISOString(),
  };
  storage.setItem(eventDraftStorageKey(gameId), JSON.stringify(value));
}

export function loadEventDraft(
  storage: Pick<Storage, "getItem">,
  gameId: number,
): StoredEventDraft | null {
  const raw = storage.getItem(eventDraftStorageKey(gameId));
  if (!raw) return null;
  try {
    const value = JSON.parse(raw) as Partial<StoredEventDraft>;
    if (
      value.version !== EVENT_DRAFT_VERSION ||
      value.formVersion !== 1 ||
      value.gameId !== gameId ||
      !value.form ||
      typeof value.form !== "object"
    ) return null;
    return value as StoredEventDraft;
  } catch {
    return null;
  }
}

export function clearEventDraft(storage: Pick<Storage, "removeItem">, gameId: number): void {
  storage.removeItem(eventDraftStorageKey(gameId));
}
