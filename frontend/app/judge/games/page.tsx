"use client";

/**
 * Judge-owned game queue page.
 *
 * The page is intentionally read-heavy in Milestone 3 so judges can verify
 * assignments before Milestone 4 adds result-entry controls.
 */

import Link from "next/link";
import { useEffect, useState } from "react";

import { PageError, PageLoading } from "@/components/page-state";
import { SiteShell } from "@/components/site-shell";
import { formatDate } from "@/lib/date";
import { getJudgeOwnedGames, type GameSummary, type GameStatus } from "@/lib/api";
import { useAuthenticatedSession } from "@/lib/use-authenticated-session";


const statusOptions: Array<GameStatus | "all"> = [
  "all",
  "draft",
  "in_progress",
  "submitted",
  "confirmed",
  "revised",
  "cancelled",
];


export default function JudgeGamesPage() {
  const { token, profile, isLoading, hasRole } = useAuthenticatedSession({ requiredRoles: ["judge", "admin"] });
  const [games, setGames] = useState<GameSummary[]>([]);
  const [statusFilter, setStatusFilter] = useState<GameStatus | "all">("all");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const canUseJudgeQueue = profile?.roles.includes("judge") ?? false;

  useEffect(() => {
    if (!token || !profile || !canUseJudgeQueue) {
      return;
    }

    void getJudgeOwnedGames(token, statusFilter === "all" ? undefined : statusFilter)
      .then((response) => setGames(response))
      .catch((error) => {
        setErrorMessage(error instanceof Error ? error.message : "Failed to load assigned games.");
      });
  }, [canUseJudgeQueue, profile, statusFilter, token]);

  if (isLoading) {
    return <PageLoading message="Loading judge game queue..." />;
  }

  if (!profile) {
    return null;
  }

  return (
    <SiteShell
      profile={profile}
      title="My Judge Games"
      description="Review games currently assigned to you as the responsible judge."
    >
      <div className="flex flex-col gap-5">
        {errorMessage ? <PageError message={errorMessage} /> : null}

        {!canUseJudgeQueue ? (
          <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 text-sm text-slate-600 shadow-lg shadow-slate-200/50">
            This account can open the judge queue page because it has admin access, but it does not currently hold the judge role required to own game assignments.
          </section>
        ) : (
          <>
            <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h2 className="text-2xl font-bold text-ink">Assigned Games</h2>
                <select
                  className="rounded-2xl border border-slate-200 px-4 py-3 text-sm"
                  onChange={(event) => setStatusFilter(event.target.value as GameStatus | "all")}
                  value={statusFilter}
                >
                  {statusOptions.map((status) => (
                    <option key={status} value={status}>
                      {status}
                    </option>
                  ))}
                </select>
              </div>
            </section>

            <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
              <div className="grid gap-4">
                {games.map((game) => (
                  <Link
                    key={game.id}
                    className="rounded-2xl border border-slate-200 bg-slate-50 p-5 transition hover:border-slate-300 hover:bg-white"
                    href={`/games/${game.id}`}
                  >
                    <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                      <div>
                        <h3 className="text-xl font-semibold text-ink">
                          {game.event_day_title} · Table {game.table_number} / Game {game.game_number}
                        </h3>
                        <p className="mt-2 text-sm text-slate-600">
                          {formatDate(game.event_day_date)} · {game.format_name}
                        </p>
                        <p className="mt-2 text-sm text-slate-600">
                          Type: {game.game_type} · Status: {game.status}
                        </p>
                      </div>
                      <div className="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700">
                        Result entry placeholder
                      </div>
                    </div>
                  </Link>
                ))}

                {games.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-600">
                    No games match the current filter.
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
