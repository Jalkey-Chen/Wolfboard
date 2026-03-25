"use client";

/**
 * Player profile page backed by effective score-log history.
 */

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { PageError, PageLoading } from "@/components/page-state";
import { SiteShell } from "@/components/site-shell";
import { formatDate, formatDateTime } from "@/lib/date";
import { getPlayerProfile, type PlayerProfileRecord } from "@/lib/api";
import { useAuthenticatedSession } from "@/lib/use-authenticated-session";


export default function PlayerProfilePage() {
  const params = useParams<{ id: string }>();
  const playerId = Number(params.id);
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
        setErrorMessage(error instanceof Error ? error.message : "Failed to load the player profile.");
      });
  }, [playerId, profile, token]);

  if (isLoading) {
    return <PageLoading message="Loading player profile..." />;
  }

  if (!profile || Number.isNaN(playerId)) {
    return null;
  }

  return (
    <SiteShell
      profile={profile}
      title={playerProfile ? playerProfile.display_name : "Player Profile"}
      description="Official score total and effective game history for the selected player."
    >
      <div className="flex flex-col gap-5">
        {errorMessage ? <PageError message={errorMessage} /> : null}

        {playerProfile ? (
          <>
            <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
              <div className="grid gap-4 md:grid-cols-3">
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Player</div>
                  <div className="mt-2 text-sm font-semibold text-slate-700">{playerProfile.display_name}</div>
                  <div className="mt-1 text-xs text-slate-500">{playerProfile.username}</div>
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Official Total Score</div>
                  <div className="mt-2 text-sm font-semibold text-slate-700">{playerProfile.total_score}</div>
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Official Games Played</div>
                  <div className="mt-2 text-sm font-semibold text-slate-700">{playerProfile.games_played}</div>
                </div>
              </div>
            </section>

            <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
              <h2 className="text-2xl font-bold text-ink">Game History</h2>
              <div className="mt-5 overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-200 text-sm">
                  <thead>
                    <tr className="text-left text-slate-500">
                      <th className="px-3 py-3 font-semibold">Event Day</th>
                      <th className="px-3 py-3 font-semibold">Game</th>
                      <th className="px-3 py-3 font-semibold">Type</th>
                      <th className="px-3 py-3 font-semibold">Status</th>
                      <th className="px-3 py-3 font-semibold">Delta</th>
                      <th className="px-3 py-3 font-semibold">Balance After</th>
                      <th className="px-3 py-3 font-semibold">Logged At</th>
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
                          Table {entry.table_number} / Game {entry.game_number}
                        </td>
                        <td className="px-3 py-4 text-slate-700">{entry.game_type}</td>
                        <td className="px-3 py-4 text-slate-700">{entry.game_status}</td>
                        <td className="px-3 py-4 text-slate-700">{entry.delta}</td>
                        <td className="px-3 py-4 text-slate-700">{entry.balance_after}</td>
                        <td className="px-3 py-4 text-slate-700">{formatDateTime(entry.created_at)}</td>
                      </tr>
                    ))}
                    {playerProfile.history.length === 0 ? (
                      <tr>
                        <td className="px-3 py-4 text-slate-600" colSpan={7}>
                          No effective score history exists for this player yet.
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

