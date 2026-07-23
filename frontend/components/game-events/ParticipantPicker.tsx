"use client";

import { useMemo, useState } from "react";

import type { ParticipantOption } from "@/lib/game-events/form-types";


type ParticipantPickerProps = {
  id: string;
  label: string;
  required: boolean;
  value: number | null;
  participants: ParticipantOption[];
  error?: string;
  disabled?: boolean;
  onChange: (participantId: number | null) => void;
  clearLabel: string;
  searchLabel: string;
};

export function participantDisplay(option: ParticipantOption): string {
  const seat = option.seatNumber === null ? "?" : option.seatNumber;
  return `${seat}号 · ${option.displayName || option.username || `#${option.participantId}`}`;
}

export function ParticipantPicker({
  id,
  label,
  required,
  value,
  participants,
  error,
  disabled,
  onChange,
  clearLabel,
  searchLabel,
}: ParticipantPickerProps) {
  const [query, setQuery] = useState("");
  const filtered = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase();
    if (!needle) return participants;
    return participants.filter((option) => [
      option.seatNumber,
      option.displayName,
      option.username,
      option.roleName,
      option.participantId,
    ].some((item) => String(item ?? "").toLocaleLowerCase().includes(needle)));
  }, [participants, query]);
  const describedBy = error ? `${id}-error` : undefined;

  return (
    <fieldset className="min-w-0" disabled={disabled}>
      <legend className="text-sm font-semibold text-slate-800">
        {label}{required ? <span className="ml-1 text-red-600" aria-hidden="true">*</span> : null}
      </legend>
      <input
        aria-describedby={describedBy}
        aria-label={searchLabel}
        className="mt-2 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-base outline-none focus:border-red-700 focus:ring-2 focus:ring-red-100 disabled:bg-slate-100"
        id={`${id}-search`}
        onChange={(event) => setQuery(event.target.value)}
        placeholder={searchLabel}
        type="search"
        value={query}
      />
      <div className="mt-2 grid max-h-48 grid-cols-2 gap-2 overflow-y-auto pr-1 sm:grid-cols-3" role="listbox" aria-label={label}>
        {!required ? (
          <button
            aria-selected={value === null}
            className={`min-h-12 rounded-md border px-3 py-2 text-left text-sm ${value === null ? "border-slate-800 bg-slate-800 text-white" : "border-slate-200 bg-white text-slate-600"}`}
            onClick={() => onChange(null)}
            role="option"
            type="button"
          >
            {clearLabel}
          </button>
        ) : null}
        {filtered.map((option) => {
          const selected = value === option.participantId;
          return (
            <button
              aria-selected={selected}
              className={`min-h-12 rounded-md border px-3 py-2 text-left ${selected ? "border-red-800 bg-red-800 text-white" : "border-slate-200 bg-white text-slate-800 hover:border-slate-400"}`}
              key={option.participantId}
              onClick={() => onChange(option.participantId)}
              role="option"
              type="button"
            >
              <span className="block text-sm font-semibold">{participantDisplay(option)}</span>
              <span className={`mt-0.5 block text-xs ${selected ? "text-red-100" : "text-slate-500"}`}>
                {option.roleName ?? `ID ${option.participantId}`}
              </span>
            </button>
          );
        })}
      </div>
      {error ? <p className="mt-2 text-sm text-red-700" id={`${id}-error`}>{error}</p> : null}
    </fieldset>
  );
}
