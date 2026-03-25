"use client";

/**
 * Season leaderboard page backed by effective score logs.
 */

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { PageError, PageLoading } from "@/components/page-state";
import { SiteShell } from "@/components/site-shell";
import { getSeasonLeaderboard, getSeasons, type LeaderboardEntry, type SeasonRecord } from "@/lib/api";
import { useAuthenticatedSession } from "@/lib/use-authenticated-session";


export default function LeaderboardPage() {
  const { token, profile, isLoading } = useAuthenticatedSession();
  const [seasons, setSeasons] = useState<SeasonRecord[]>([]);
  const [selectedSeasonId, setSelectedSeasonId] = useState<number | null>(null);
  const [entries, setEntries] = useState<LeaderboardEntry[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!token || !profile) {
      return;
    }

    void getSeasons(token)
      .then((response) => {
        setSeasons(response);
        const activeSeason = response.find((season) => season.status === "active") ?? response[0] ?? null;
        setSelectedSeasonId(activeSeason?.id ?? null);
      })
      .catch((error) => {
        setErrorMessage(error instanceof Error ? error.message : "Failed to load seasons.");
      });
  }, [profile, token]);

  useEffect(() => {
    if (!token || !selectedSeasonId) {
      return;
    }

    void getSeasonLeaderboard(token, selectedSeasonId)
      .then((response) => setEntries(response))
      .catch((error) => {
        setErrorMessage(error instanceof Error ? error.message : "Failed to load the leaderboard.");
      });
  }, [selectedSeasonId, token]);

  const selectedSeason = useMemo(
    () => seasons.find((season) => season.id === selectedSeasonId) ?? null,
    [seasons, selectedSeasonId],
  );

  if (isLoading) {
    return <PageLoading message="Loading leaderboard..." />;
  }

  if (!profile) {
    return null;
  }

  return (
    <SiteShell
      profile={profile}
      title="Leaderboard"
      description="Official standings built from effective score logs for confirmed and revised official games."
    >
      <div className="flex flex-col gap-5">
        {errorMessage ? <PageError message={errorMessage} /> : null}

        <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-2xl font-bold text-ink">Season Selection</h2>
              <p className="mt-2 text-sm text-slate-600">
                {selectedSeason ? `${selectedSeason.name} · ${selectedSeason.status}` : "No season selected."}
              </p>
            </div>
            <select
              className="rounded-2xl border border-slate-200 px-4 py-3 text-sm"
              onChange={(event) => setSelectedSeasonId(Number(event.target.value))}
              value={selectedSeasonId ?? ""}
            >
              {seasons.map((season) => (
                <option key={season.id} value={season.id}>
                  {season.name}
                </option>
              ))}
            </select>
          </div>
        </section>

        <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
          <h2 className="text-2xl font-bold text-ink">Standings</h2>
          <div className="mt-5 overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead>
                <tr className="text-left text-slate-500">
                  <th className="px-3 py-3 font-semibold">Rank</th>
                  <th className="px-3 py-3 font-semibold">Player</th>
                  <th className="px-3 py-3 font-semibold">Total Score</th>
                  <th className="px-3 py-3 font-semibold">Games</th>
                  <th className="px-3 py-3 font-semibold">Wins</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {entries.map((entry) => (
                  <tr key={entry.user_id}>
                    <td className="px-3 py-4 font-semibold text-ink">{entry.ranking}</td>
                    <td className="px-3 py-4 text-slate-700">
                      <Link className="font-semibold text-ink hover:underline" href={`/players/${entry.user_id}`}>
                        {entry.display_name}
                      </Link>
                      <div className="text-xs text-slate-500">{entry.username}</div>
                    </td>
                    <td className="px-3 py-4 text-slate-700">{entry.total_score}</td>
                    <td className="px-3 py-4 text-slate-700">{entry.games_played}</td>
                    <td className="px-3 py-4 text-slate-700">{entry.wins}</td>
                  </tr>
                ))}
                {entries.length === 0 ? (
                  <tr>
                    <td className="px-3 py-4 text-slate-600" colSpan={5}>
                      No effective official score logs exist for the selected season yet.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </SiteShell>
  );
}

