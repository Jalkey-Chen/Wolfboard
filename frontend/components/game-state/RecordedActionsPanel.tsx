"use client";

import { useMemo, useState } from "react";

import { useI18n } from "@/components/language-provider";
import type { GameDerivedParticipantState, GameRecordedActionUsage } from "@/lib/api";
import { selectActionUsage } from "@/lib/game-state/selectors";


const ACTION_FIELDS = [
  "recorded_seer_check_count",
  "recorded_witch_antidote_count",
  "recorded_witch_poison_count",
  "recorded_guard_protection_count",
  "recorded_hunter_shot_count",
  "recorded_wolf_king_shot_count",
  "recorded_wolf_self_explosion_count",
  "recorded_sheriff_vote_count",
  "recorded_exile_vote_count",
] as const satisfies ReadonlyArray<keyof GameRecordedActionUsage>;

export function RecordedActionsPanel({
  usage,
  participants,
}: {
  usage: GameRecordedActionUsage[];
  participants: GameDerivedParticipantState[];
}) {
  const { t } = useI18n();
  const [includeZero, setIncludeZero] = useState(false);
  const visible = useMemo(() => selectActionUsage(usage, includeZero), [includeZero, usage]);
  return (
    <section aria-labelledby="derived-actions-heading" className="border-b border-slate-200 py-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-base font-bold text-slate-950" id="derived-actions-heading">{t("derivedState.actions.title")}</h3>
          <p className="mt-1 text-sm text-slate-600">{t("derivedState.actions.disclaimer")}</p>
        </div>
        <label className="flex items-center gap-2 text-sm font-semibold text-slate-700">
          <input checked={includeZero} onChange={(event) => setIncludeZero(event.target.checked)} type="checkbox" />
          {t("derivedState.actions.showZero")}
        </label>
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {visible.map((item) => {
          const participant = participants.find((candidate) => candidate.participant_id === item.participant_id);
          return (
            <article className="rounded-md border border-slate-200 p-4" key={item.participant_id}>
              <h4 className="font-bold text-slate-900">{participant?.seat_number ?? "?"} · {participant?.display_name_snapshot ?? `#${item.participant_id}`}</h4>
              <dl className="mt-3 space-y-1 text-sm">
                {ACTION_FIELDS.map((field) => (
                  <div className="flex justify-between gap-3" key={field}>
                    <dt className="text-slate-600">{t(`derivedState.actions.${field}`)}</dt>
                    <dd className="font-bold">{t("derivedState.actions.recordedCount", { count: item[field] })}</dd>
                  </div>
                ))}
              </dl>
            </article>
          );
        })}
      </div>
      {visible.length === 0 ? <p className="mt-3 border border-dashed border-slate-300 p-4 text-sm text-slate-600">{t("derivedState.actions.empty")}</p> : null}
    </section>
  );
}
