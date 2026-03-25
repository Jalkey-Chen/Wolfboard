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

import { PageError, PageLoading } from "@/components/page-state";
import { SiteShell } from "@/components/site-shell";
import { formatDate, formatDateTime } from "@/lib/date";
import { getGame, type GameDetail } from "@/lib/api";
import { useAuthenticatedSession } from "@/lib/use-authenticated-session";


export default function GameDetailPage() {
  const params = useParams<{ id: string }>();
  const gameId = Number(params.id);
  const { token, profile, isLoading, hasRole } = useAuthenticatedSession();
  const [game, setGame] = useState<GameDetail | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!token || !profile || Number.isNaN(gameId)) {
      return;
    }

    void getGame(token, gameId)
      .then((response) => setGame(response))
      .catch((error) => {
        setErrorMessage(error instanceof Error ? error.message : "Failed to load the game.");
      });
  }, [gameId, profile, token]);

  if (isLoading) {
    return <PageLoading message="Loading game details..." />;
  }

  if (!profile || Number.isNaN(gameId)) {
    return null;
  }

  return (
    <SiteShell
      profile={profile}
      title={game ? `Table ${game.table_number} · Game ${game.game_number}` : "Game"}
      description={game ? `${game.season_name} · ${game.event_day_title}` : "Game setup detail."}
      actions={
        game && hasRole("admin") ? (
          <Link
            className="rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800"
            href={`/admin/event-days/${game.event_day_id}/games`}
          >
            Manage Games
          </Link>
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
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Season</div>
                  <div className="mt-2 text-sm font-semibold text-slate-700">{game.season_name}</div>
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Event Day</div>
                  <div className="mt-2 text-sm font-semibold text-slate-700">{game.event_day_title}</div>
                  <div className="mt-1 text-xs text-slate-500">{formatDate(game.event_day_date)}</div>
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Format</div>
                  <div className="mt-2 text-sm font-semibold text-slate-700">{game.format.format_name}</div>
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Judge</div>
                  <div className="mt-2 text-sm font-semibold text-slate-700">{game.judge.display_name}</div>
                </div>
              </div>

              <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Table</div>
                  <div className="mt-2 text-sm text-slate-700">{game.table_number}</div>
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Game Number</div>
                  <div className="mt-2 text-sm text-slate-700">{game.game_number}</div>
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Game Type</div>
                  <div className="mt-2 text-sm text-slate-700">{game.game_type}</div>
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Status</div>
                  <div className="mt-2 text-sm text-slate-700">{game.status}</div>
                </div>
              </div>
            </section>

            <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
              <h2 className="text-2xl font-bold text-ink">Timing and Notes</h2>
              <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Venue</div>
                  <div className="mt-2 text-sm text-slate-700">{game.event_day_venue}</div>
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Started At</div>
                  <div className="mt-2 text-sm text-slate-700">{formatDateTime(game.started_at)}</div>
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Ended At</div>
                  <div className="mt-2 text-sm text-slate-700">{formatDateTime(game.ended_at)}</div>
                </div>
              </div>
              <div className="mt-5 rounded-2xl bg-slate-50 px-4 py-4 text-sm text-slate-700">
                {game.notes ?? "No notes provided yet."}
              </div>

              <div className="mt-5 rounded-2xl border border-dashed border-slate-300 px-4 py-4 text-sm text-slate-600">
                Milestone 4 will attach result-entry actions here or on a linked judge workflow page.
              </div>
            </section>
          </>
        ) : null}
      </div>
    </SiteShell>
  );
}
