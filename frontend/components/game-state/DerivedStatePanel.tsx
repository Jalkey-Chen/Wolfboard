"use client";

import { BallotSummaryList } from "@/components/game-state/BallotSummaryList";
import { ParticipantStateGrid } from "@/components/game-state/ParticipantStateGrid";
import { PhaseStateCard } from "@/components/game-state/PhaseStateCard";
import { ProjectionHeader } from "@/components/game-state/ProjectionHeader";
import { ProjectionIssuesPanel } from "@/components/game-state/ProjectionIssuesPanel";
import { RecordedActionsPanel } from "@/components/game-state/RecordedActionsPanel";
import { RoundSummaryList } from "@/components/game-state/RoundSummaryList";
import { SheriffStateCard } from "@/components/game-state/SheriffStateCard";
import { useI18n } from "@/components/language-provider";
import type { DerivedStateController } from "@/lib/game-state/use-derived-state";


export function DerivedStatePanel({
  controller,
  ledgerLocked,
  onOpenEvent,
}: {
  controller: DerivedStateController;
  ledgerLocked: boolean;
  onOpenEvent: (eventId: number) => void;
}) {
  const { t } = useI18n();
  const state = controller.state;
  if (!state && controller.loading) {
    return <div aria-live="polite" className="border border-dashed border-slate-300 p-8 text-center text-sm text-slate-600">{t("derivedState.loading")}</div>;
  }
  if (!state) {
    return (
      <div className="border-l-4 border-red-700 bg-red-50 p-4" role="alert">
        <p className="font-semibold text-red-900">{controller.error ?? t("derivedState.loadError")}</p>
        <button className="mt-3 rounded-md border border-red-300 px-3 py-2 text-sm font-bold text-red-900" onClick={() => void controller.refresh()} type="button">{t("common.retry")}</button>
      </div>
    );
  }
  return (
    <div className="min-w-0">
      <ProjectionHeader
        announcement={controller.announcement}
        error={controller.error}
        loading={controller.loading}
        onRefresh={() => void controller.refresh()}
        onShowLatest={() => void controller.showLatest()}
        refreshedAt={controller.refreshedAt}
        selectedEvent={controller.selection?.event ?? null}
        stale={controller.stale}
        state={state}
      />
      {ledgerLocked ? <p className="mt-4 border-l-4 border-slate-500 bg-slate-100 px-4 py-3 text-sm text-slate-800">{t("derivedState.lockedReadable")}</p> : null}
      {state.effective_event_count === 0 ? <p className="mt-4 border border-dashed border-slate-300 p-4 text-sm text-slate-700">{t("derivedState.noEvents")}</p> : null}
      <div className="grid gap-x-6 xl:grid-cols-2">
        <PhaseStateCard onOpenEvent={onOpenEvent} phase={state.phase} />
        <SheriffStateCard onOpenEvent={onOpenEvent} participants={state.participants} sheriff={state.sheriff} />
      </div>
      <ParticipantStateGrid issues={state.issues} onOpenEvent={onOpenEvent} participants={state.participants} />
      <BallotSummaryList ballots={state.ballots} onOpenEvent={onOpenEvent} participants={state.participants} />
      <RecordedActionsPanel participants={state.participants} usage={state.recorded_action_usage} />
      <RoundSummaryList onOpenEvent={onOpenEvent} summaries={state.round_summaries} />
      <ProjectionIssuesPanel issues={state.issues} onOpenEvent={onOpenEvent} participants={state.participants} />
    </div>
  );
}
