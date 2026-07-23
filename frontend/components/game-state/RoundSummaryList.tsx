"use client";

import { EventProvenanceLink } from "@/components/game-state/EventProvenanceLink";
import { useI18n } from "@/components/language-provider";
import type { GameDerivedRoundSummary } from "@/lib/api";
import { selectRoundSummaries } from "@/lib/game-state/selectors";


export function RoundSummaryList({
  summaries,
  onOpenEvent,
}: {
  summaries: GameDerivedRoundSummary[];
  onOpenEvent: (eventId: number) => void;
}) {
  const { t, enumLabel } = useI18n();
  return (
    <section aria-labelledby="derived-rounds-heading" className="border-b border-slate-200 py-5">
      <h3 className="text-base font-bold text-slate-950" id="derived-rounds-heading">{t("derivedState.rounds.title")}</h3>
      <p className="mt-1 text-sm text-slate-600">{t("derivedState.rounds.disclaimer")}</p>
      <div className="mt-4 space-y-2">
        {selectRoundSummaries(summaries).map((summary) => (
          <details className="rounded-md border border-slate-200 p-4" key={`${summary.round_no}-${summary.phase}`}>
            <summary className="cursor-pointer font-bold">
              {t("eventWorkbench.roundLabel", { round: summary.round_no })} · {enumLabel("gameEventPhase", summary.phase)} · {t("derivedState.rounds.eventCount", { count: summary.event_count })}
            </summary>
            <div className="mt-3 text-sm">
              <ul className="grid gap-1 sm:grid-cols-2">
                {summary.event_type_counts.map((item) => <li key={item.event_type}>{enumLabel("gameEventType", item.event_type)}: {item.count}</li>)}
              </ul>
              <div className="mt-3 flex flex-wrap gap-1 border-t border-slate-100 pt-3">
                {summary.event_ids.map((id) => <EventProvenanceLink eventId={id} key={id} onOpenEvent={onOpenEvent} />)}
              </div>
            </div>
          </details>
        ))}
      </div>
      {summaries.length === 0 ? <p className="mt-3 border border-dashed border-slate-300 p-4 text-sm text-slate-600">{t("common.noData")}</p> : null}
    </section>
  );
}
