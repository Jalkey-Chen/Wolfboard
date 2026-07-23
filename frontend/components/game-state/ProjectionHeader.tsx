"use client";

import { useI18n } from "@/components/language-provider";
import type { GameDerivedState, GameEventRecord } from "@/lib/api";
import { formatDateTime } from "@/lib/date";
import { throughSequenceModeLabel } from "@/lib/game-state/selectors";


export function ProjectionHeader({
  state,
  selectedEvent,
  loading,
  error,
  refreshedAt,
  stale,
  announcement,
  onRefresh,
  onShowLatest,
}: {
  state: GameDerivedState;
  selectedEvent: GameEventRecord | null;
  loading: boolean;
  error: string | null;
  refreshedAt: Date | null;
  stale: boolean;
  announcement: string | null;
  onRefresh: () => void;
  onShowLatest: () => void;
}) {
  const { t, language, enumLabel } = useI18n();
  const prefix = state.through_logical_sequence;
  return (
    <header className="border-b border-slate-200 pb-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-bold uppercase text-sky-800">{t("derivedState.recordedState")}</p>
          <h2 className="mt-1 text-xl font-bold text-slate-950">{t("derivedState.title")}</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-700">{t("derivedState.disclaimer")}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {prefix !== null ? (
            <button className="rounded-md border border-slate-300 px-3 py-2 text-sm font-semibold" disabled={loading} onClick={onShowLatest} type="button">
              {t("derivedState.returnLatest")}
            </button>
          ) : null}
          <button className="rounded-md bg-slate-900 px-3 py-2 text-sm font-bold text-white disabled:opacity-60" disabled={loading} onClick={onRefresh} type="button">
            {loading ? t("common.loading") : t("derivedState.refresh")}
          </button>
        </div>
      </div>

      <div className="mt-4 grid gap-3 text-sm sm:grid-cols-2 xl:grid-cols-4">
        <div><span className="font-semibold text-slate-500">{t("derivedState.mode")}</span><div className="mt-1 font-bold">{throughSequenceModeLabel(prefix, language)}</div></div>
        <div><span className="font-semibold text-slate-500">{t("derivedState.effectiveCount")}</span><div className="mt-1 font-bold">{state.effective_event_count}</div></div>
        <div><span className="font-semibold text-slate-500">{t("derivedState.lastApplied")}</span><div className="mt-1 font-bold">{state.last_applied_logical_sequence ?? t("common.none")}</div></div>
        <div><span className="font-semibold text-slate-500">{t("derivedState.formatSnapshot")}</span><div className="mt-1 font-bold">{state.format_name ?? t("common.notSet")}</div></div>
      </div>

      <details className="mt-3 text-xs text-slate-600">
        <summary className="cursor-pointer font-semibold">{t("derivedState.technicalDetails")}</summary>
        <dl className="mt-2 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          <div><dt>{t("derivedState.projectionKind")}</dt><dd className="font-mono">{state.projection_kind}</dd></div>
          <div><dt>{t("derivedState.projectionVersion")}</dt><dd>{state.projection_version}</dd></div>
          <div><dt>{t("derivedState.ledgerHead")}</dt><dd>{state.event_ledger_head_sequence}</dd></div>
          <div><dt>{t("derivedState.refreshedAt")}</dt><dd>{refreshedAt ? formatDateTime(refreshedAt.toISOString()) : t("common.notSet")}</dd></div>
        </dl>
        <p className="mt-2">{t("derivedState.ledgerHeadHint")}</p>
      </details>

      {prefix !== null ? (
        <div className="mt-4 border-l-4 border-sky-600 bg-sky-50 px-4 py-3 text-sm text-sky-950">
          <p className="font-bold">{t("derivedState.prefixDescription", { sequence: prefix })}</p>
          <p className="mt-1">{t("derivedState.prefixNotAsOf")}</p>
          {selectedEvent ? (
            <p className="mt-2">
              L{selectedEvent.logical_sequence_no} · {enumLabel("gameEventType", selectedEvent.event_type)} · {t("eventWorkbench.roundShort", { round: selectedEvent.round_no })} · {enumLabel("gameEventPhase", selectedEvent.phase)}
            </p>
          ) : <p className="mt-2 font-semibold">{t("derivedState.selectedPositionMissing")}</p>}
        </div>
      ) : null}

      {stale ? <p className="mt-3 border-l-4 border-amber-500 bg-amber-50 px-3 py-2 text-sm text-amber-950">{t("derivedState.possiblyStale")}</p> : null}
      {announcement?.startsWith("ledger-updated-prefix:") ? (
        <p aria-live="polite" className="mt-3 text-sm font-semibold text-sky-900">
          {t("derivedState.ledgerUpdatedPrefix", { sequence: prefix ?? "" })}
        </p>
      ) : null}
      {error ? <p className="mt-3 text-sm font-semibold text-red-800" role="alert">{error}</p> : null}
      <span aria-live="polite" className="sr-only">{loading ? t("derivedState.loading") : t("derivedState.loaded")}</span>
    </header>
  );
}
