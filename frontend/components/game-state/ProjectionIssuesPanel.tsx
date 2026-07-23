"use client";

import { EventProvenanceLink } from "@/components/game-state/EventProvenanceLink";
import { useI18n } from "@/components/language-provider";
import type { GameDerivedParticipantState, GameProjectionIssue } from "@/lib/api";
import { projectionIssueMessage } from "@/lib/game-state/issue-messages";


function participantText(participants: GameDerivedParticipantState[], id: number): string {
  const participant = participants.find((item) => item.participant_id === id);
  return participant ? `${participant.seat_number ?? "?"} · ${participant.display_name_snapshot ?? `#${id}`}` : `#${id}`;
}

export function ProjectionIssuesPanel({
  issues,
  participants,
  onOpenEvent,
}: {
  issues: GameProjectionIssue[];
  participants: GameDerivedParticipantState[];
  onOpenEvent: (eventId: number) => void;
}) {
  const { t, language, enumLabel } = useI18n();
  const grouped = {
    warning: issues.filter((issue) => issue.severity === "warning"),
    info: issues.filter((issue) => issue.severity === "info"),
  };
  return (
    <section aria-labelledby="derived-issues-heading" className="py-5">
      <h3 className="text-base font-bold text-slate-950" id="derived-issues-heading">{t("derivedState.issues.title")}</h3>
      <p className="mt-1 text-sm text-slate-600">{t("derivedState.issues.disclaimer")}</p>
      {(["warning", "info"] as const).map((severity) => grouped[severity].length > 0 ? (
        <div className="mt-4" key={severity}>
          <h4 className="text-sm font-bold uppercase text-slate-600">{t(`derivedState.issue.${severity}`)} · {grouped[severity].length}</h4>
          <div className="mt-2 space-y-3">
            {grouped[severity].map((issue, index) => {
              const copy = projectionIssueMessage(issue.code, language);
              return (
                <article className={`border-l-4 px-4 py-3 ${severity === "warning" ? "border-amber-500 bg-amber-50" : "border-sky-500 bg-sky-50"}`} key={`${issue.code}-${index}`}>
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <h5 className="font-bold text-slate-950">{copy.title}</h5>
                      <p className="mt-1 text-sm text-slate-700">{copy.explanation}</p>
                    </div>
                    <code className="text-xs text-slate-500">{issue.code}</code>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-slate-600">
                    {issue.round_no ? <span>{t("eventWorkbench.roundShort", { round: issue.round_no })}</span> : null}
                    {issue.phase ? <span>{enumLabel("gameEventPhase", issue.phase)}</span> : null}
                    {issue.participant_ids.map((id) => <a className="font-semibold underline" href={`#participant-state-${id}`} key={id}>{participantText(participants, id)}</a>)}
                    {issue.event_ids.map((id) => <EventProvenanceLink eventId={id} key={id} onOpenEvent={onOpenEvent} />)}
                  </div>
                  {Object.keys(issue.details).length > 0 ? <p className="mt-2 break-words font-mono text-xs text-slate-600">{JSON.stringify(issue.details)}</p> : null}
                </article>
              );
            })}
          </div>
        </div>
      ) : null)}
      {issues.length === 0 ? <p className="mt-3 border border-dashed border-slate-300 p-4 text-sm text-slate-600">{t("derivedState.issues.empty")}</p> : null}
    </section>
  );
}
