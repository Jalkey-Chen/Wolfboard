"use client";

import { useMemo, useState } from "react";

import { EventProvenanceLink } from "@/components/game-state/EventProvenanceLink";
import { useI18n } from "@/components/language-provider";
import type { GameDerivedParticipantState, GameProjectionIssue } from "@/lib/api";
import {
  issuesForParticipant,
  selectParticipants,
  type ParticipantProjectionFilter,
} from "@/lib/game-state/selectors";


export function ParticipantStateGrid({
  participants,
  issues,
  onOpenEvent,
}: {
  participants: GameDerivedParticipantState[];
  issues: GameProjectionIssue[];
  onOpenEvent: (eventId: number) => void;
}) {
  const { t, enumLabel } = useI18n();
  const [filter, setFilter] = useState<ParticipantProjectionFilter>("all");
  const visible = useMemo(
    () => selectParticipants(participants, issues, filter),
    [filter, issues, participants],
  );
  return (
    <section aria-labelledby="derived-participants-heading" className="border-b border-slate-200 py-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h3 className="text-base font-bold text-slate-950" id="derived-participants-heading">{t("derivedState.participants.title")}</h3>
          <p className="mt-1 text-sm text-slate-600">{t("derivedState.participants.basis")}</p>
        </div>
        <label className="text-sm font-semibold text-slate-700">
          {t("derivedState.participants.filter")}
          <select className="ml-2 rounded-md border border-slate-300 px-2 py-2" onChange={(event) => setFilter(event.target.value as ParticipantProjectionFilter)} value={filter}>
            <option value="all">{t("common.all")}</option>
            <option value="active_record">{t("derivedState.participants.noExitRecord")}</option>
            <option value="exit_record">{t("derivedState.participants.hasExitRecord")}</option>
            <option value="issues">{t("derivedState.participants.hasIssues")}</option>
          </select>
        </label>
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {visible.map((participant) => {
          const participantIssues = issuesForParticipant(issues, participant.participant_id);
          return (
            <article className="min-w-0 rounded-md border border-slate-200 p-4" id={`participant-state-${participant.participant_id}`} key={participant.participant_id}>
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <h4 className="font-bold text-slate-950">{participant.seat_number ?? "?"}{t("common.seatSuffix")} · {participant.display_name_snapshot ?? t("common.notSet")}</h4>
                  <p className="mt-1 break-words text-xs text-slate-500">Participant #{participant.participant_id}</p>
                </div>
                <span className={`shrink-0 rounded border px-2 py-1 text-xs font-bold ${participant.is_active_in_game ? "border-emerald-300 bg-emerald-50 text-emerald-900" : "border-amber-400 bg-amber-50 text-amber-950"}`}>
                  {participant.is_active_in_game ? t("derivedState.participants.noExitRecord") : t("derivedState.participants.hasExitRecord")}
                </span>
              </div>
              <dl className="mt-3 grid grid-cols-2 gap-2 text-sm">
                <div><dt className="text-slate-500">{t("common.role")}</dt><dd className="font-semibold">{participant.recorded_role_name ?? t("common.notSet")}</dd></div>
                <div><dt className="text-slate-500">{t("common.faction")}</dt><dd className="font-semibold">{participant.recorded_faction ? enumLabel("gamePlayerFaction", participant.recorded_faction) : t("common.notSet")}</dd></div>
                <div><dt className="text-slate-500">{t("derivedState.participants.exile")}</dt><dd>{participant.has_exile_record ? t("common.yes") : t("common.no")}</dd></div>
                <div><dt className="text-slate-500">{t("derivedState.participants.death")}</dt><dd>{participant.has_death_record ? t("common.yes") : t("common.no")}</dd></div>
                <div><dt className="text-slate-500">{t("derivedState.participants.firstExit")}</dt><dd>{participant.first_exit_logical_sequence ?? t("common.none")}</dd></div>
                <div><dt className="text-slate-500">{t("derivedState.participants.latestExit")}</dt><dd>{participant.latest_exit_logical_sequence ?? t("common.none")}</dd></div>
              </dl>
              {participant.exit_event_ids.length > 0 ? (
                <div className="mt-3 flex flex-wrap items-center gap-1 border-t border-slate-100 pt-3">
                  <span className="text-xs font-semibold text-slate-500">{t("derivedState.provenance")}</span>
                  {participant.exit_event_ids.map((eventId) => <EventProvenanceLink eventId={eventId} key={eventId} onOpenEvent={onOpenEvent} />)}
                </div>
              ) : null}
              {participantIssues.length > 0 ? (
                <details className="mt-3 text-sm">
                  <summary className="cursor-pointer font-semibold text-amber-900">{t("derivedState.participants.issueCount", { count: participantIssues.length })}</summary>
                  <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-slate-700">
                    {participantIssues.map((issue, index) => <li key={`${issue.code}-${index}`}>{issue.code}</li>)}
                  </ul>
                </details>
              ) : null}
            </article>
          );
        })}
      </div>
      {visible.length === 0 ? <p className="mt-4 border border-dashed border-slate-300 p-4 text-sm text-slate-600">{t("common.noData")}</p> : null}
    </section>
  );
}
