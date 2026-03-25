"use client";

/**
 * Base game detail page.
 *
 * Milestone 3 keeps this page focused on setup metadata so Milestone 4 can add
 * result-entry affordances without redesigning the route structure.
 */

import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { useI18n } from "@/components/language-provider";
import { PageError, PageLoading } from "@/components/page-state";
import { SiteShell } from "@/components/site-shell";
import { formatDate, formatDateTime } from "@/lib/date";
import { getMetaLabelClass } from "@/lib/i18n";
import { getGame, getGameResultDraft, type GameDetail, type GameResultDraftResponse } from "@/lib/api";
import { useAuthenticatedSession } from "@/lib/use-authenticated-session";


export default function GameDetailPage() {
  const params = useParams<{ id: string }>();
  const gameId = Number(params.id);
  const { t, enumLabel, language } = useI18n();
  const { token, profile, isLoading } = useAuthenticatedSession();
  const [game, setGame] = useState<GameDetail | null>(null);
  const [resultDraft, setResultDraft] = useState<GameResultDraftResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const userIsAdmin = profile?.roles.includes("admin") ?? false;
  const userIsJudge = profile?.roles.includes("judge") ?? false;

  useEffect(() => {
    if (!token || !profile || Number.isNaN(gameId)) {
      return;
    }

    void getGame(token, gameId)
      .then((response) => setGame(response))
      .catch((error) => {
        setErrorMessage(error instanceof Error ? error.message : t("games.loadError"));
      });
  }, [gameId, profile, t, token]);

  useEffect(() => {
    if (!token || !profile || !game) {
      return;
    }

    const canOpenResultPage =
      userIsAdmin ||
      (userIsJudge && profile.user.id === game.judge_user_id) ||
      game.status === "confirmed" ||
      game.status === "revised";
    if (!canOpenResultPage) {
      setResultDraft(null);
      return;
    }

    void getGameResultDraft(token, game.id)
      .then((response) => setResultDraft(response))
      .catch(() => {
        setResultDraft(null);
      });
  }, [game, profile, token, userIsAdmin, userIsJudge]);

  if (isLoading) {
    return <PageLoading message={t("games.loading")} />;
  }

  if (!profile || Number.isNaN(gameId)) {
    return null;
  }

  const canOpenResultPage =
    game !== null && (userIsAdmin || (userIsJudge && profile.user.id === game.judge_user_id));
  const canEditResult =
    game !== null &&
    userIsJudge &&
    profile.user.id === game.judge_user_id &&
    (game.status === "draft" || game.status === "in_progress");
  const canReviewResult = game !== null && userIsAdmin && game.status === "submitted";
  const metaLabelClass = getMetaLabelClass(language);

  return (
    <SiteShell
      profile={profile}
      title={game ? `${game.table_number}桌 · 第${game.game_number}局` : t("games.title")}
      description={game ? `${game.season_name} · ${game.event_day_title}` : t("games.description")}
      actions={
        game ? (
          <div className="flex flex-wrap gap-3">
            {canOpenResultPage ? (
              <Link
                className="rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800"
                href={`/judge/games/${game.id}/result`}
              >
                {canEditResult ? t("games.enterResult") : t("games.viewResult")}
              </Link>
            ) : null}
            {canReviewResult ? (
              <Link
                className="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-200"
                href={`/admin/games/${game.id}/review`}
              >
                {t("games.reviewResult")}
              </Link>
            ) : null}
            {userIsAdmin ? (
              <Link
                className="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-200"
                href={`/admin/event-days/${game.event_day_id}/games`}
              >
                {t("games.manageGames")}
              </Link>
            ) : null}
          </div>
        ) : null
      }
    >
      <div className="flex flex-col gap-5">
        {errorMessage ? <PageError message={errorMessage} /> : null}

        {game ? (
          <>
            <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className={metaLabelClass}>{t("common.season")}</div>
                  <div className="mt-2 text-sm font-semibold text-slate-700">{game.season_name}</div>
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className={metaLabelClass}>{t("common.eventDay")}</div>
                  <div className="mt-2 text-sm font-semibold text-slate-700">{game.event_day_title}</div>
                  <div className="mt-1 text-xs text-slate-500">{formatDate(game.event_day_date)}</div>
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className={metaLabelClass}>{t("common.format")}</div>
                  <div className="mt-2 text-sm font-semibold text-slate-700">{game.format.format_name}</div>
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className={metaLabelClass}>{t("common.judge")}</div>
                  <div className="mt-2 text-sm font-semibold text-slate-700">{game.judge.display_name}</div>
                </div>
              </div>

              <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className={metaLabelClass}>{t("common.table")}</div>
                  <div className="mt-2 text-sm text-slate-700">{game.table_number}</div>
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className={metaLabelClass}>{t("common.gameNumber")}</div>
                  <div className="mt-2 text-sm text-slate-700">{game.game_number}</div>
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className={metaLabelClass}>{t("common.gameType")}</div>
                  <div className="mt-2 text-sm text-slate-700">{enumLabel("gameType", game.game_type)}</div>
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className={metaLabelClass}>{t("common.status")}</div>
                  <div className="mt-2 text-sm text-slate-700">{enumLabel("gameStatus", game.status)}</div>
                </div>
              </div>
            </section>

            <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
              <h2 className="text-2xl font-bold text-ink">{t("games.timingAndNotes")}</h2>
              <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className={metaLabelClass}>{t("common.venue")}</div>
                  <div className="mt-2 text-sm text-slate-700">{game.event_day_venue}</div>
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className={metaLabelClass}>{t("games.startedAt")}</div>
                  <div className="mt-2 text-sm text-slate-700">{formatDateTime(game.started_at)}</div>
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className={metaLabelClass}>{t("games.endedAt")}</div>
                  <div className="mt-2 text-sm text-slate-700">{formatDateTime(game.ended_at)}</div>
                </div>
              </div>
              <div className="mt-5 rounded-2xl bg-slate-50 px-4 py-4 text-sm text-slate-700">
                {game.notes ?? t("common.noNotes")}
              </div>

              <div className="mt-5 rounded-2xl border border-dashed border-slate-300 px-4 py-4 text-sm text-slate-600">
                {canEditResult
                  ? t("games.editableHint")
                  : game.status === "submitted"
                    ? t("games.submittedHint")
                    : t("games.noActionHint")}
              </div>
            </section>

            <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
              <h2 className="text-2xl font-bold text-ink">{t("games.resultSummary")}</h2>
              {resultDraft && resultDraft.players.length > 0 ? (
                <div className="mt-5 overflow-x-auto">
                  <table className="min-w-full divide-y divide-slate-200 text-sm">
                    <thead>
                      <tr className="text-left text-slate-500">
                        <th className="px-3 py-3 font-semibold">{t("common.seat")}</th>
                        <th className="px-3 py-3 font-semibold">{t("common.player")}</th>
                        <th className="px-3 py-3 font-semibold">{t("common.role")}</th>
                        <th className="px-3 py-3 font-semibold">{t("common.faction")}</th>
                        <th className="px-3 py-3 font-semibold">{t("common.winner")}</th>
                        <th className="px-3 py-3 font-semibold">{t("resultEntry.final")}</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {resultDraft.players.map((player) => (
                        <tr key={player.id}>
                          <td className="px-3 py-4 text-slate-700">{player.seat_number ?? t("common.notSet")}</td>
                          <td className="px-3 py-4 text-slate-700">{player.display_name || t("resultEntry.notSelected")}</td>
                          <td className="px-3 py-4 text-slate-700">{player.role_name ?? t("common.notSet")}</td>
                          <td className="px-3 py-4 text-slate-700">{player.faction ? enumLabel("gamePlayerFaction", player.faction) : t("common.notSet")}</td>
                          <td className="px-3 py-4 text-slate-700">{player.is_winner === null ? t("common.notSet") : player.is_winner ? t("common.win") : t("common.lose")}</td>
                          <td className="px-3 py-4 font-semibold text-ink">{player.final_score}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="mt-4 text-sm text-slate-600">{t("games.noResultDraft")}</p>
              )}
            </section>
          </>
        ) : null}
      </div>
    </SiteShell>
  );
}
