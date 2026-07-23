"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { EventPayloadFields } from "@/components/game-events/EventPayloadFields";
import { EventTypePicker } from "@/components/game-events/EventTypePicker";
import { ParticipantPicker } from "@/components/game-events/ParticipantPicker";
import { useI18n } from "@/components/language-provider";
import type {
  GameEventBodyPayload,
  GameEventDefinition,
  GameEventRecord,
  GameEventType,
} from "@/lib/api";
import {
  createInitialEventForm,
  initialPayloadForDefinition,
  selectEventType,
  type EventCategory,
} from "@/lib/game-events/definitions";
import { clearEventDraft, loadEventDraft, saveEventDraft } from "@/lib/game-events/draft-storage";
import { parseWorkbenchError } from "@/lib/game-events/errors";
import type {
  EventFormErrors,
  EventFormState,
  EventPayloadValue,
  ParticipantOption,
  PendingEventSubmission,
} from "@/lib/game-events/form-types";
import { preparePendingSubmission } from "@/lib/game-events/request-normalization";


type GameEventComposerProps = {
  gameId: number;
  definitions: GameEventDefinition[];
  participants: ParticipantOption[];
  events: GameEventRecord[];
  disabled: boolean;
  recentEvent?: GameEventRecord;
  initialEvent?: GameEventRecord;
  mode?: "create" | "correct";
  onSubmit: (request: GameEventBodyPayload, reason: string | null) => Promise<void>;
  onConflict?: () => void;
  onCancel?: () => void;
};

function formFromEvent(event: GameEventRecord): EventFormState {
  return {
    phase: event.phase,
    roundNo: event.round_no,
    eventType: event.event_type,
    actorParticipantId: event.actor_participant_id,
    targetParticipantId: event.target_participant_id,
    secondaryTargetParticipantId: event.secondary_target_participant_id,
    payload: event.payload as EventFormState["payload"],
    occurredAt: event.occurred_at,
  };
}

function validateForm(form: EventFormState, definition: GameEventDefinition): EventFormErrors {
  const errors: EventFormErrors = {};
  if (!Number.isInteger(form.roundNo) || form.roundNo < 1) errors.roundNo = "Round must be a positive integer.";
  if (definition.required_actor && form.actorParticipantId === null) errors.actorParticipantId = "Actor is required.";
  if (definition.required_target && form.targetParticipantId === null) errors.targetParticipantId = "Target is required.";
  for (const field of definition.payload_schema.required ?? []) {
    const value = form.payload[field];
    if (value === undefined || value === null || value === "" || (Array.isArray(value) && value.length === 0)) {
      errors[`payload.${field}`] = `${field} is required.`;
    }
  }
  return errors;
}

export function GameEventComposer({
  gameId,
  definitions,
  participants,
  events,
  disabled,
  recentEvent,
  initialEvent,
  mode = "create",
  onSubmit,
  onConflict,
  onCancel,
}: GameEventComposerProps) {
  const { t, enumLabel } = useI18n();
  const definitionMap = useMemo(
    () => new Map(definitions.map((definition) => [definition.event_type, definition])),
    [definitions],
  );
  const initial = useMemo(
    () => initialEvent
      ? formFromEvent(initialEvent)
      : createInitialEventForm(definitions, recentEvent),
    [definitions, initialEvent, recentEvent],
  );
  const [form, setForm] = useState<EventFormState>(initial);
  const [pending, setPending] = useState<PendingEventSubmission | null>(null);
  const [dirty, setDirty] = useState(false);
  const [restored, setRestored] = useState(false);
  const [reason, setReason] = useState("");
  const [errors, setErrors] = useState<EventFormErrors>({});
  const [message, setMessage] = useState<string | null>(null);
  const [retryable, setRetryable] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const hydrated = useRef(false);

  useEffect(() => {
    if (mode !== "create" || hydrated.current) return;
    hydrated.current = true;
    const stored = loadEventDraft(localStorage, gameId);
    if (stored && definitionMap.has(stored.form.eventType)) {
      setForm(stored.form);
      setPending(stored.pending);
      setDirty(true);
      setRestored(true);
      setRetryable(stored.pending !== null);
    }
  }, [definitionMap, gameId, mode]);

  useEffect(() => {
    if (mode !== "create" || !hydrated.current) return;
    if (dirty || pending) saveEventDraft(localStorage, gameId, form, pending);
    else clearEventDraft(localStorage, gameId);
  }, [dirty, form, gameId, mode, pending]);

  const definition = definitionMap.get(form.eventType) ?? definitions[0];
  if (!definition) return <div className="border border-red-300 bg-red-50 p-4 text-sm text-red-800">{t("eventWorkbench.definitionsMissing")}</div>;

  function updateForm(updater: (current: EventFormState) => EventFormState) {
    setForm((current) => updater(current));
    setPending(null);
    setDirty(true);
    setErrors({});
    setMessage(null);
    setRetryable(false);
  }

  async function submitWithPending(currentPending: PendingEventSubmission) {
    setSubmitting(true);
    setMessage(null);
    setErrors({});
    try {
      await onSubmit(currentPending.request, mode === "correct" ? reason.trim() : null);
      setPending(null);
      setDirty(false);
      setRestored(false);
      clearEventDraft(localStorage, gameId);
      if (mode === "create") {
        setForm((current) => ({
          ...current,
          actorParticipantId: null,
          targetParticipantId: null,
          secondaryTargetParticipantId: null,
          payload: initialPayloadForDefinition(definition),
          occurredAt: null,
        }));
      }
    } catch (error) {
      const parsed = parseWorkbenchError(error);
      setMessage(parsed.message);
      setErrors(parsed.fieldErrors);
      setRetryable(parsed.retryableWithSameRequest);
      if (parsed.status === 409) onConflict?.();
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSubmit() {
    const localErrors = validateForm(form, definition);
    if (mode === "correct" && !reason.trim()) localErrors.reason = t("eventWorkbench.reasonRequired");
    if (Object.keys(localErrors).length > 0) {
      setErrors(localErrors);
      setMessage(t("eventWorkbench.formInvalid"));
      return;
    }
    const nextPending = preparePendingSubmission(form, pending);
    setPending(nextPending);
    await submitWithPending(nextPending);
  }

  function discardDraft() {
    setForm(initial);
    setPending(null);
    setDirty(false);
    setRestored(false);
    setErrors({});
    setMessage(null);
    clearEventDraft(localStorage, gameId);
  }

  return (
    <div className="space-y-5">
      {restored ? (
        <div className="flex flex-wrap items-center justify-between gap-3 border-l-4 border-amber-500 bg-amber-50 px-3 py-3 text-sm text-amber-900" role="status">
          <span>{t("eventWorkbench.restoredDraft")}</span>
          <button className="font-semibold underline" onClick={discardDraft} type="button">{t("eventWorkbench.discardDraft")}</button>
        </div>
      ) : null}
      {message ? <div className="border-l-4 border-red-700 bg-red-50 px-3 py-3 text-sm text-red-800" role="alert">{message}</div> : null}

      <div className="grid grid-cols-2 gap-3">
        <label className="text-sm font-semibold text-slate-800" htmlFor="event-phase">
          {t("eventWorkbench.phase")}
          <select className="mt-2 w-full rounded-md border border-slate-300 bg-white px-3 py-3 text-base" disabled={disabled || submitting} id="event-phase" onChange={(event) => updateForm((current) => ({ ...current, phase: event.target.value as EventFormState["phase"] }))} value={form.phase}>
            <option value="night">{enumLabel("gameEventPhase", "night")}</option>
            <option value="day">{enumLabel("gameEventPhase", "day")}</option>
          </select>
        </label>
        <label className="text-sm font-semibold text-slate-800" htmlFor="event-round">
          {t("eventWorkbench.round")}
          <input aria-describedby={errors.roundNo ? "event-round-error" : undefined} className="mt-2 w-full rounded-md border border-slate-300 px-3 py-3 text-base" disabled={disabled || submitting} id="event-round" min={1} onChange={(event) => updateForm((current) => ({ ...current, roundNo: Number(event.target.value) }))} type="number" value={form.roundNo} />
          {errors.roundNo ? <span className="mt-1 block text-sm text-red-700" id="event-round-error">{errors.roundNo}</span> : null}
        </label>
      </div>
      <p className="text-xs text-slate-500">{t("eventWorkbench.recentPrefill")}</p>

      <EventTypePicker
        categoryLabel={(category: EventCategory) => t(`eventWorkbench.category.${category}`)}
        definitions={definitions}
        disabled={disabled || submitting}
        eventLabel={(eventType) => enumLabel("gameEventType", eventType)}
        onChange={(eventType: GameEventType) => {
          const nextDefinition = definitionMap.get(eventType);
          if (nextDefinition) updateForm((current) => selectEventType(current, nextDefinition));
        }}
        quickLabel={t("eventWorkbench.eventType")}
        value={form.eventType}
      />

      {definition.allows_actor ? (
        <ParticipantPicker
          clearLabel={t("common.none")}
          disabled={disabled || submitting}
          error={errors.actorParticipantId}
          id="event-actor"
          label={t("eventWorkbench.actor")}
          onChange={(value) => updateForm((current) => ({ ...current, actorParticipantId: value }))}
          participants={participants}
          required={definition.required_actor}
          searchLabel={t("eventWorkbench.searchParticipant")}
          value={form.actorParticipantId}
        />
      ) : null}

      {definition.allows_target ? (
        <ParticipantPicker
          clearLabel={t("common.none")}
          disabled={disabled || submitting}
          error={errors.targetParticipantId}
          id="event-target"
          label={t("eventWorkbench.target")}
          onChange={(value) => updateForm((current) => ({ ...current, targetParticipantId: value }))}
          participants={participants}
          required={definition.required_target}
          searchLabel={t("eventWorkbench.searchParticipant")}
          value={form.targetParticipantId}
        />
      ) : null}

      {definition.allows_secondary_target ? (
        <ParticipantPicker
          clearLabel={t("common.none")}
          disabled={disabled || submitting}
          error={errors.secondaryTargetParticipantId}
          id="event-secondary-target"
          label={t("eventWorkbench.secondaryTarget")}
          onChange={(value) => updateForm((current) => ({ ...current, secondaryTargetParticipantId: value }))}
          participants={participants}
          required={false}
          searchLabel={t("eventWorkbench.searchParticipant")}
          value={form.secondaryTargetParticipantId}
        />
      ) : null}

      <EventPayloadFields
        definition={definition}
        disabled={disabled || submitting}
        errors={errors}
        eventLabel={(event) => enumLabel("gameEventType", event.event_type)}
        events={events}
        labelFor={(field) => t(`eventWorkbench.payload.${field}`)}
        onChange={(field: string, value: EventPayloadValue) => updateForm((current) => ({ ...current, payload: { ...current.payload, [field]: value } }))}
        participants={participants}
        values={form.payload}
      />

      <div className="border-l-4 border-slate-300 bg-slate-50 px-3 py-3 text-sm text-slate-700">
        {t("eventWorkbench.visibility")}: <strong>{enumLabel("gameEventVisibility", definition.default_visibility)}</strong>
        {definition.default_visibility === "postgame_full" ? <p className="mt-1 text-xs">{t("eventWorkbench.hiddenHint")}</p> : null}
      </div>

      {mode === "correct" ? (
        <label className="block text-sm font-semibold text-slate-800" htmlFor="correction-reason">
          {t("common.reason")} <span className="text-red-600">*</span>
          <textarea aria-describedby={errors.reason ? "correction-reason-error" : undefined} className="mt-2 min-h-20 w-full rounded-md border border-slate-300 px-3 py-2 text-base" disabled={submitting} id="correction-reason" onChange={(event) => { setReason(event.target.value); setErrors({}); }} value={reason} />
          {errors.reason ? <span className="mt-1 block text-sm text-red-700" id="correction-reason-error">{errors.reason}</span> : null}
        </label>
      ) : null}

      <div className="flex flex-wrap gap-2 border-t border-slate-200 pt-4" aria-live="polite">
        <button className="min-h-12 flex-1 rounded-md bg-red-800 px-4 py-3 text-sm font-bold text-white hover:bg-red-900 disabled:bg-slate-400" disabled={disabled || submitting} onClick={() => void handleSubmit()} type="button">
          {submitting ? t("eventWorkbench.saving") : mode === "correct" ? t("eventWorkbench.saveCorrection") : t("eventWorkbench.saveEvent")}
        </button>
        {retryable && pending ? (
          <button className="min-h-12 rounded-md border border-red-800 px-4 py-3 text-sm font-bold text-red-800" disabled={submitting} onClick={() => void submitWithPending(pending)} type="button">
            {t("eventWorkbench.retrySameRequest")}
          </button>
        ) : null}
        {onCancel ? <button className="min-h-12 rounded-md border border-slate-300 px-4 py-3 text-sm font-semibold" onClick={onCancel} type="button">{t("common.cancel")}</button> : null}
      </div>
    </div>
  );
}
