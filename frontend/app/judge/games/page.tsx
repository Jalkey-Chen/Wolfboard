"use client";

/**
 * Judge-owned game queue page.
 *
 * The page is intentionally read-heavy in Milestone 3 so judges can verify
 * assignments before Milestone 4 adds result-entry controls.
 */

import Link from "next/link";
import { useEffect, useState } from "react";

import { useI18n } from "@/components/language-provider";
import { PageError, PageLoading } from "@/components/page-state";
import { SiteShell } from "@/components/site-shell";
import { formatDate } from "@/lib/date";
import {
  getJudgeOwnedGames,
  type GamePlayStatus,
  type GameResultStatus,
  type GameSummary,
} from "@/lib/api";
import { useAuthenticatedSession } from "@/lib/use-authenticated-session";


const playStatusOptions: Array<GamePlayStatus | "all"> = ["all", "scheduled", "in_progress", "ended", "cancelled"];
const resultStatusOptions: Array<GameResultStatus | "all"> = ["all", "empty", "draft", "submitted", "rejected", "confirmed", "revised"];


export default function JudgeGamesPage() {
  const { t, enumLabel } = useI18n();
  const { token, profile, isLoading } = useAuthenticatedSession({ requiredRoles: ["judge", "admin"] });
  const [games, setGames] = useState<GameSummary[]>([]);
  const [playStatusFilter, setPlayStatusFilter] = useState<GamePlayStatus | "all">("all");
  const [resultStatusFilter, setResultStatusFilter] = useState<GameResultStatus | "all">("all");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const canUseJudgeQueue = profile?.roles.includes("judge") ?? false;

  useEffect(() => {
    if (!token || !profile || !canUseJudgeQueue) {
      return;
    }

    void getJudgeOwnedGames(token, {
      playStatus: playStatusFilter === "all" ? undefined : playStatusFilter,
      resultStatus: resultStatusFilter === "all" ? undefined : resultStatusFilter,
    })
      .then((response) => setGames(response))
      .catch((error) => {
        setErrorMessage(error instanceof Error ? error.message : t("judgeGames.loadError"));
      });
  }, [canUseJudgeQueue, playStatusFilter, profile, resultStatusFilter, t, token]);

  if (isLoading) {
    return <PageLoading message={t("judgeGames.loading")} />;
  }

  if (!profile) {
    return null;
  }

  return (
    <SiteShell
      profile={profile}
      title={t("judgeGames.title")}
      description={t("judgeGames.description")}
    >
      <div className="flex flex-col gap-5">
        {errorMessage ? <PageError message={errorMessage} /> : null}

        {!canUseJudgeQueue ? (
          <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 text-sm text-slate-600 shadow-lg shadow-slate-200/50">
            {t("judgeGames.noJudgeRole")}
          </section>
        ) : (
          <>
            <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h2 className="text-2xl font-bold text-ink">{t("judgeGames.assignedGames")}</h2>
                <div className="flex flex-wrap gap-3">
                  <select
                    aria-label={t("common.playStatus")}
                    className="rounded-2xl border border-slate-200 px-4 py-3 text-sm"
                    onChange={(event) => setPlayStatusFilter(event.target.value as GamePlayStatus | "all")}
                    value={playStatusFilter}
                  >
                    {playStatusOptions.map((status) => (
                      <option key={status} value={status}>
                        {status === "all" ? t("common.playStatus") : enumLabel("gamePlayStatus", status)}
                      </option>
                    ))}
                  </select>
                  <select
                    aria-label={t("common.resultStatus")}
                    className="rounded-2xl border border-slate-200 px-4 py-3 text-sm"
                    onChange={(event) => setResultStatusFilter(event.target.value as GameResultStatus | "all")}
                    value={resultStatusFilter}
                  >
                    {resultStatusOptions.map((status) => (
                      <option key={status} value={status}>
                        {status === "all" ? t("common.resultStatus") : enumLabel("gameResultStatus", status)}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </section>

            <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
              <div className="grid gap-4">
                {games.map((game) => {
                  const resultHref = `/judge/games/${game.id}/result`;
                  const actionLabel =
                    game.play_status !== "cancelled" && ["empty", "draft", "rejected"].includes(game.result_status)
                      ? t("games.enterResult")
                      : game.result_status === "submitted"
                        ? t("judgeGames.viewSubmittedResult")
                        : t("judgeGames.viewGame");

                  return (
                    <div
                      key={game.id}
                      className="rounded-2xl border border-slate-200 bg-slate-50 p-5"
                    >
                      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                        <div>
                        <h3 className="text-xl font-semibold text-ink">
                            {game.event_day_title} · {game.table_number}桌 / 第{game.game_number}局
                          </h3>
                          <p className="mt-2 text-sm text-slate-600">
                            {formatDate(game.event_day_date)} · {game.format_name}
                          </p>
                          <p className="mt-2 text-sm text-slate-600">
                            {t("common.type")}: {enumLabel("gameType", game.game_type)} · {t("common.playStatus")}: {enumLabel("gamePlayStatus", game.play_status)} · {t("common.resultStatus")}: {enumLabel("gameResultStatus", game.result_status)}
                          </p>
                        </div>
                        <div className="flex flex-wrap gap-3">
                          <Link
                            className="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-200"
                            href={`/games/${game.id}`}
                          >
                            {t("common.details")}
                          </Link>
                          <Link
                            className="rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800"
                            href={resultHref}
                          >
                            {actionLabel}
                          </Link>
                        </div>
                      </div>
                    </div>
                  );
                })}

                {games.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-600">
                    {t("judgeGames.noGames")}
                  </div>
                ) : null}
              </div>
            </section>
          </>
        )}
      </div>
    </SiteShell>
  );
}
