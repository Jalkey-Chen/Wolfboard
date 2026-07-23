"use client";

import type { GameEventDefinition, GameEventType } from "@/lib/api";
import {
  EVENT_CATEGORY_ORDER,
  EVENT_UI_DEFINITIONS,
  type EventCategory,
} from "@/lib/game-events/definitions";


type EventTypePickerProps = {
  definitions: GameEventDefinition[];
  value: GameEventType;
  onChange: (eventType: GameEventType) => void;
  eventLabel: (eventType: GameEventType) => string;
  categoryLabel: (category: EventCategory) => string;
  quickLabel: string;
  disabled?: boolean;
};

export function EventTypePicker({
  definitions,
  value,
  onChange,
  eventLabel,
  categoryLabel,
  quickLabel,
  disabled,
}: EventTypePickerProps) {
  const supported = new Set(definitions.map((item) => item.event_type));
  const quick = Object.entries(EVENT_UI_DEFINITIONS)
    .filter(([eventType, definition]) => definition.quick && supported.has(eventType as GameEventType))
    .map(([eventType]) => eventType as GameEventType);

  return (
    <div>
      <div className="text-sm font-semibold text-slate-800">{quickLabel}</div>
      <div className="mt-2 flex flex-wrap gap-2">
        {quick.map((eventType) => (
          <button
            className={`rounded-md border px-3 py-2 text-sm font-semibold ${value === eventType ? "border-red-800 bg-red-800 text-white" : "border-slate-300 bg-white text-slate-700 hover:border-slate-500"}`}
            disabled={disabled}
            key={eventType}
            onClick={() => onChange(eventType)}
            type="button"
          >
            {eventLabel(eventType)}
          </button>
        ))}
      </div>
      <label className="mt-4 block text-sm font-semibold text-slate-800" htmlFor="event-type">
        {quickLabel}
      </label>
      <select
        className="mt-2 w-full rounded-md border border-slate-300 bg-white px-3 py-3 text-base outline-none focus:border-red-700 focus:ring-2 focus:ring-red-100 disabled:bg-slate-100"
        disabled={disabled}
        id="event-type"
        onChange={(event) => onChange(event.target.value as GameEventType)}
        value={value}
      >
        {EVENT_CATEGORY_ORDER.map((category) => (
          <optgroup key={category} label={categoryLabel(category)}>
            {(Object.keys(EVENT_UI_DEFINITIONS) as GameEventType[])
              .filter((eventType) => EVENT_UI_DEFINITIONS[eventType].category === category && supported.has(eventType))
              .map((eventType) => <option key={eventType} value={eventType}>{eventLabel(eventType)}</option>)}
          </optgroup>
        ))}
      </select>
    </div>
  );
}
