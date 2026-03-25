"use client";

/**
 * Player profile page backed by effective score-log history.
 */

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { useI18n } from "@/components/language-provider";
import { PageError, PageLoading } from "@/components/page-state";
import { SiteShell } from "@/components/site-shell";
import { formatDate, formatDateTime } from "@/lib/date";
import { getPlayerProfile, type PlayerProfileRecord } from "@/lib/api";
import { useAuthenticatedSession } from "@/lib/use-authenticated-session";


export default function PlayerProfilePage() {
  const params = useParams<{ id: string }>();
  const playerId = Number(params.id);
  const { t, enumLabel } = useI18n();
  const { token, profile, isLoading } = useAuthenticatedSession();
  const [playerProfile, setPlayerProfile] = useState<PlayerProfileRecord | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!token || !profile || Number.isNaN(playerId)) {
      return;
    }

    void getPlayerProfile(token, playerId)
      .then((response) => setPlayerProfile(response))
      .catch((error) => {
        setErrorMessage(error instanceof Error ? error.message : t("players.loadError"));
      });
  }, [playerId, profile, t, token]);

  if (isLoading) {
    return <PageLoading message={t("players.loading")} />;
  }

  if (!profile || Number.isNaN(playerId)) {
    return null;
  }

  return (
    <SiteShell
      profile={profile}
      title={playerProfile ? playerProfile.display_name : t("players.title")}
      description={t("players.description")}
    >
      <div className="flex flex-col gap-5">
        {errorMessage ? <PageError message={errorMessage} /> : null}

        {playerProfile ? (
          <>
            <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
              <div className="grid gap-4 md:grid-cols-3">
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-400">{t("common.player")}</div>
                  <div className="mt-2 text-sm font-semibold text-slate-700">{playerProfile.display_name}</div>
                  <div className="mt-1 text-xs text-slate-500">{playerProfile.username}</div>
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-400">{t("players.officialTotalScore")}</div>
                  <div className="mt-2 text-sm font-semibold text-slate-700">{playerProfile.total_score}</div>
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-400">{t("players.officialGamesPlayed")}</div>
                  <div className="mt-2 text-sm font-semibold text-slate-700">{playerProfile.games_played}</div>
                </div>
              </div>
            </section>

            <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
              <h2 className="text-2xl font-bold text-ink">{t("players.gameHistory")}</h2>
              <div className="mt-5 overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-200 text-sm">
                  <thead>
                    <tr className="text-left text-slate-500">
                      <th className="px-3 py-3 font-semibold">{t("common.eventDay")}</th>
                      <th className="px-3 py-3 font-semibold">{t("games.title")}</th>
                      <th className="px-3 py-3 font-semibold">{t("common.type")}</th>
                      <th className="px-3 py-3 font-semibold">{t("common.status")}</th>
                      <th className="px-3 py-3 font-semibold">{t("resultEntry.delta")}</th>
                      <th className="px-3 py-3 font-semibold">{t("players.balanceAfter")}</th>
                      <th className="px-3 py-3 font-semibold">{t("common.loggedAt")}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {playerProfile.history.map((entry) => (
                      <tr key={`${entry.game_id}-${entry.created_at}`}>
                        <td className="px-3 py-4 text-slate-700">
                          <Link className="font-semibold text-ink hover:underline" href={`/games/${entry.game_id}`}>
                            {entry.event_day_title}
                          </Link>
                          <div className="text-xs text-slate-500">{formatDate(entry.event_day_date)}</div>
                        </td>
                        <td className="px-3 py-4 text-slate-700">
                          {entry.table_number}桌 / 第{entry.game_number}局
                        </td>
                        <td className="px-3 py-4 text-slate-700">{enumLabel("gameType", entry.game_type)}</td>
                        <td className="px-3 py-4 text-slate-700">{enumLabel("gameStatus", entry.game_status)}</td>
                        <td className="px-3 py-4 text-slate-700">{entry.delta}</td>
                        <td className="px-3 py-4 text-slate-700">{entry.balance_after}</td>
                        <td className="px-3 py-4 text-slate-700">{formatDateTime(entry.created_at)}</td>
                      </tr>
                    ))}
                    {playerProfile.history.length === 0 ? (
                      <tr>
                        <td className="px-3 py-4 text-slate-600" colSpan={7}>
                          {t("players.noHistory")}
                        </td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        ) : null}
      </div>
    </SiteShell>
  );
}
