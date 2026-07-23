"use client";

import { useI18n } from "@/components/language-provider";
import type { GameDetail } from "@/lib/api";
import type { WorkbenchMode } from "@/lib/game-events/lifecycle";


export function WorkbenchStatusBanner({ game, mode }: { game: GameDetail; mode: WorkbenchMode }) {
  const { t, enumLabel } = useI18n();
  return (
    <div className={`rounded-lg border px-4 py-3 ${mode.editable ? mode.entryMode === "live" ? "border-emerald-300 bg-emerald-50" : "border-amber-300 bg-amber-50" : "border-slate-300 bg-slate-100"}`} role="status">
      <div className="flex flex-wrap gap-x-5 gap-y-1 text-sm font-semibold text-slate-800">
        <span>{t("common.playStatus")}: {enumLabel("gamePlayStatus", game.play_status)}</span>
        <span>{t("common.resultStatus")}: {enumLabel("gameResultStatus", game.result_status)}</span>
        <span>{t("eventWorkbench.entryStatus")}: {mode.editable ? t("eventWorkbench.available") : t("eventWorkbench.locked")}</span>
      </div>
      <p className="mt-1 text-sm text-slate-600">{t(mode.reasonKey)}</p>
    </div>
  );
}
