"use client";

import { EventProvenanceLink } from "@/components/game-state/EventProvenanceLink";
import { useI18n } from "@/components/language-provider";
import type { GameDerivedPhaseState } from "@/lib/api";


export function PhaseStateCard({
  phase,
  onOpenEvent,
}: {
  phase: GameDerivedPhaseState;
  onOpenEvent: (eventId: number) => void;
}) {
  const { t, enumLabel } = useI18n();
  return (
    <section aria-labelledby="derived-phase-heading" className="border-b border-slate-200 py-5">
      <h3 className="text-base font-bold text-slate-950" id="derived-phase-heading">{t("derivedState.phase.title")}</h3>
      {phase.phase_is_open && phase.current_phase && phase.current_round_no ? (
        <p className="mt-3 text-lg font-bold text-sky-950">
          {t("derivedState.phase.open", {
            round: phase.current_round_no,
            phase: enumLabel("gameEventPhase", phase.current_phase),
          })}
        </p>
      ) : <p className="mt-3 font-semibold text-slate-700">{t("derivedState.phase.unknown")}</p>}
      <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-2">
        <div>
          <dt className="font-semibold text-slate-500">{t("derivedState.phase.startedBy")}</dt>
          <dd className="mt-1">{phase.phase_started_event_id ? <EventProvenanceLink eventId={phase.phase_started_event_id} onOpenEvent={onOpenEvent} /> : t("common.none")}</dd>
        </div>
        <div>
          <dt className="font-semibold text-slate-500">{t("derivedState.phase.lastCompleted")}</dt>
          <dd className="mt-1">
            {phase.last_completed_phase && phase.last_completed_round_no
              ? `${t("eventWorkbench.roundShort", { round: phase.last_completed_round_no })} · ${enumLabel("gameEventPhase", phase.last_completed_phase)}`
              : t("common.none")}
            {phase.last_completed_event_id ? <span className="ml-2"><EventProvenanceLink eventId={phase.last_completed_event_id} onOpenEvent={onOpenEvent} /></span> : null}
          </dd>
        </div>
        <div>
          <dt className="font-semibold text-slate-500">{t("derivedState.phase.lastObserved")}</dt>
          <dd className="mt-1">
            {phase.last_observed_phase && phase.last_observed_round_no
              ? `${t("eventWorkbench.roundShort", { round: phase.last_observed_round_no })} · ${enumLabel("gameEventPhase", phase.last_observed_phase)}`
              : t("common.none")}
            {phase.last_observed_event_id ? <span className="ml-2"><EventProvenanceLink eventId={phase.last_observed_event_id} onOpenEvent={onOpenEvent} /></span> : null}
          </dd>
        </div>
      </dl>
    </section>
  );
}
