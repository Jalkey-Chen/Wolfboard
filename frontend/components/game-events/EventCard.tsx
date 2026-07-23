"use client";

import { formatDateTime } from "@/lib/date";
import { useI18n } from "@/components/language-provider";
import type { GameEventRecord } from "@/lib/api";
import { compactPayload, formatGameEvent } from "@/lib/game-events/formatters";
import type { ParticipantOption } from "@/lib/game-events/form-types";
import { participantDisplay } from "@/components/game-events/ParticipantPicker";


type EventCardProps = {
  event: GameEventRecord;
  participants: ParticipantOption[];
  ledger?: boolean;
  editable: boolean;
  onCorrect: (event: GameEventRecord) => void;
  onVoid: (event: GameEventRecord) => void;
};

export function EventCard({ event, participants, ledger, editable, onCorrect, onVoid }: EventCardProps) {
  const { t, enumLabel } = useI18n();
  const participantMap = new Map(participants.map((item) => [item.participantId, participantDisplay(item)]));
  const statusClass = event.status === "active"
    ? "border-emerald-300 bg-emerald-50 text-emerald-800"
    : event.status === "superseded"
      ? "border-amber-300 bg-amber-50 text-amber-900"
      : "border-slate-300 bg-slate-100 text-slate-700";
  const summary = formatGameEvent(event, {
    eventTypeLabel: (type) => enumLabel("gameEventType", type),
    participantLabel: (id) => participantMap.get(id) ?? null,
  });

  return (
    <article className={`rounded-lg border bg-white p-4 ${event.status === "active" ? "border-slate-200" : "border-slate-300"}`} id={`event-${event.id}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
            <span className="font-mono">{ledger ? `#${event.sequence_no} / L${event.logical_sequence_no}` : `L${event.logical_sequence_no}`}</span>
            <span>{t("eventWorkbench.roundShort", { round: event.round_no })} · {enumLabel("gameEventPhase", event.phase)}</span>
            <span className={`rounded border px-2 py-0.5 font-semibold ${statusClass}`}>{enumLabel("gameEventStatus", event.status)}</span>
            {!ledger && event.supersedes_event_id ? <span className="font-semibold text-amber-800">{t("eventWorkbench.corrected")}</span> : null}
            <span className="rounded border border-slate-200 px-2 py-0.5">{enumLabel("gameEventVisibility", event.visibility)}</span>
          </div>
          <h3 className="mt-2 text-base font-bold text-slate-900">{summary}</h3>
          <p className="mt-2 break-words text-xs text-slate-600">{compactPayload(event.payload)}</p>
        </div>
        {editable && event.status === "active" ? (
          <div className="flex shrink-0 gap-2">
            <button className="rounded-md border border-slate-300 px-3 py-2 text-sm font-semibold hover:bg-slate-50" onClick={() => onCorrect(event)} type="button">{t("eventWorkbench.correct")}</button>
            <button className="rounded-md border border-red-300 px-3 py-2 text-sm font-semibold text-red-800 hover:bg-red-50" onClick={() => onVoid(event)} type="button">{t("eventWorkbench.void")}</button>
          </div>
        ) : null}
      </div>
      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 border-t border-slate-100 pt-3 text-xs text-slate-500">
        <span>{event.created_by.display_name} · {formatDateTime(event.created_at)}</span>
        {event.supersedes_event_id ? <a className="font-semibold underline" href={`#event-${event.supersedes_event_id}`}>{t("eventWorkbench.supersedes", { id: event.supersedes_event_id })}</a> : null}
        {event.revision_reason ? <span>{t("common.reason")}: {event.revision_reason}</span> : null}
        {event.invalidation_reason ? <span>{t("eventWorkbench.invalidation")}: {event.invalidation_reason}</span> : null}
        {ledger && event.client_event_id ? <span className="font-mono">client: {event.client_event_id.slice(0, 12)}…</span> : null}
      </div>
    </article>
  );
}
