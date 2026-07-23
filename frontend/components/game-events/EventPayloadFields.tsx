"use client";

import type { GameEventDefinition, GameEventRecord } from "@/lib/api";
import { schemaForPayloadField, EVENT_UI_DEFINITIONS } from "@/lib/game-events/definitions";
import type { EventFormErrors, EventPayloadValue, ParticipantOption } from "@/lib/game-events/form-types";
import { participantDisplay } from "@/components/game-events/ParticipantPicker";


type EventPayloadFieldsProps = {
  definition: GameEventDefinition;
  values: Record<string, EventPayloadValue>;
  participants: ParticipantOption[];
  events: GameEventRecord[];
  errors: EventFormErrors;
  disabled?: boolean;
  labelFor: (field: string) => string;
  eventLabel: (event: GameEventRecord) => string;
  onChange: (field: string, value: EventPayloadValue) => void;
};

function eventOption(event: GameEventRecord, label: string) {
  return `#${event.sequence_no} · ${label} · R${event.round_no} ${event.phase}`;
}

export function EventPayloadFields({
  definition,
  values,
  participants,
  events,
  errors,
  disabled,
  labelFor,
  eventLabel,
  onChange,
}: EventPayloadFieldsProps) {
  const fields = EVENT_UI_DEFINITIONS[definition.event_type].payloadFields;
  if (fields.length === 0) return null;
  const required = new Set(definition.payload_schema.required ?? []);

  return (
    <div className="grid gap-4">
      {fields.map(({ name, kind }) => {
        const schema = schemaForPayloadField(definition, name);
        const error = errors[`payload.${name}`];
        const id = `event-payload-${name}`;
        const label = labelFor(name);
        const describedBy = error ? `${id}-error` : undefined;
        if (kind === "boolean") {
          return (
            <label className="flex min-h-12 items-center gap-3 rounded-md border border-slate-200 px-3 py-2 text-sm font-medium text-slate-800" key={name}>
              <input checked={Boolean(values[name])} disabled={disabled} onChange={(event) => onChange(name, event.target.checked)} type="checkbox" />
              {label}
            </label>
          );
        }
        if (kind === "enum") {
          const options = schema.enum ?? (schema.const !== undefined ? [schema.const] : []);
          return (
            <label className="block text-sm font-semibold text-slate-800" key={name} htmlFor={id}>
              {label}{required.has(name) ? <span className="ml-1 text-red-600">*</span> : null}
              <select aria-describedby={describedBy} className="mt-2 w-full rounded-md border border-slate-300 bg-white px-3 py-3 text-base" disabled={disabled} id={id} onChange={(event) => onChange(name, event.target.value)} value={String(values[name] ?? "")}>
                {options.map((option) => <option key={String(option)} value={String(option)}>{String(option)}</option>)}
              </select>
              {error ? <span className="mt-1 block text-sm text-red-700" id={`${id}-error`}>{error}</span> : null}
            </label>
          );
        }
        if (kind === "positive_integer" || kind === "positive_number") {
          return (
            <label className="block text-sm font-semibold text-slate-800" key={name} htmlFor={id}>
              {label}{required.has(name) ? <span className="ml-1 text-red-600">*</span> : null}
              <input aria-describedby={describedBy} className="mt-2 w-full rounded-md border border-slate-300 px-3 py-3 text-base" disabled={disabled} id={id} min={kind === "positive_integer" ? 1 : 0.01} onChange={(event) => onChange(name, Number(event.target.value))} step={kind === "positive_integer" ? 1 : "any"} type="number" value={Number(values[name] ?? 1)} />
              {error ? <span className="mt-1 block text-sm text-red-700" id={`${id}-error`}>{error}</span> : null}
            </label>
          );
        }
        if (kind === "participant_id_list") {
          const selected = new Set(Array.isArray(values[name]) ? values[name] as number[] : []);
          return (
            <fieldset className="rounded-md border border-slate-200 p-3" key={name}>
              <legend className="px-1 text-sm font-semibold text-slate-800">{label}{required.has(name) ? " *" : ""}</legend>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                {participants.map((participant) => (
                  <label className="flex min-h-11 items-center gap-2 rounded-md bg-slate-50 px-2 text-sm" key={participant.participantId}>
                    <input checked={selected.has(participant.participantId)} disabled={disabled} onChange={() => {
                      const next = new Set(selected);
                      if (next.has(participant.participantId)) next.delete(participant.participantId);
                      else next.add(participant.participantId);
                      onChange(name, [...next]);
                    }} type="checkbox" />
                    {participantDisplay(participant)}
                  </label>
                ))}
              </div>
              {error ? <p className="mt-2 text-sm text-red-700">{error}</p> : null}
            </fieldset>
          );
        }
        if (kind === "event_id") {
          return (
            <label className="block text-sm font-semibold text-slate-800" key={name} htmlFor={id}>
              {label}
              <select className="mt-2 w-full rounded-md border border-slate-300 bg-white px-3 py-3 text-base" disabled={disabled} id={id} onChange={(event) => onChange(name, event.target.value ? Number(event.target.value) : null)} value={Number(values[name] ?? 0) || ""}>
                <option value="">—</option>
                {events.map((event) => <option key={event.id} value={event.id}>{eventOption(event, eventLabel(event))}</option>)}
              </select>
            </label>
          );
        }
        if (kind === "event_id_list") {
          const selected = new Set(Array.isArray(values[name]) ? values[name] as number[] : []);
          return (
            <fieldset className="rounded-md border border-slate-200 p-3" key={name}>
              <legend className="px-1 text-sm font-semibold text-slate-800">{label}</legend>
              <div className="max-h-40 space-y-1 overflow-y-auto">
                {events.map((event) => (
                  <label className="flex min-h-10 items-center gap-2 text-sm" key={event.id}>
                    <input checked={selected.has(event.id)} disabled={disabled} onChange={() => {
                      const next = new Set(selected);
                      if (next.has(event.id)) next.delete(event.id); else next.add(event.id);
                      onChange(name, [...next]);
                    }} type="checkbox" />
                    {eventOption(event, eventLabel(event))}
                  </label>
                ))}
              </div>
            </fieldset>
          );
        }
        if (kind === "tally") {
          const tally = values[name] && !Array.isArray(values[name]) && typeof values[name] === "object" ? values[name] as Record<string, number> : {};
          return (
            <fieldset className="rounded-md border border-slate-200 p-3" key={name}>
              <legend className="px-1 text-sm font-semibold text-slate-800">{label}</legend>
              <div className="grid gap-2 sm:grid-cols-2">
                {participants.map((participant) => (
                  <label className="flex items-center justify-between gap-2 text-sm" key={participant.participantId}>
                    <span>{participantDisplay(participant)}</span>
                    <input className="w-20 rounded-md border border-slate-300 px-2 py-2" disabled={disabled} min={0} onChange={(event) => {
                      const next = { ...tally };
                      if (event.target.value === "") delete next[String(participant.participantId)];
                      else next[String(participant.participantId)] = Number(event.target.value);
                      onChange(name, next);
                    }} step="any" type="number" value={tally[String(participant.participantId)] ?? ""} />
                  </label>
                ))}
              </div>
            </fieldset>
          );
        }
        return (
          <label className="block text-sm font-semibold text-slate-800" key={name} htmlFor={id}>
            {label}{required.has(name) ? <span className="ml-1 text-red-600">*</span> : null}
            <textarea aria-describedby={describedBy} className="mt-2 min-h-20 w-full rounded-md border border-slate-300 px-3 py-2 text-base" disabled={disabled} id={id} maxLength={schema.maxLength} onChange={(event) => onChange(name, event.target.value)} value={String(values[name] ?? "")} />
            {error ? <span className="mt-1 block text-sm text-red-700" id={`${id}-error`}>{error}</span> : null}
          </label>
        );
      })}
    </div>
  );
}
