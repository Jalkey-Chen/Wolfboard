"use client";

/**
 * Home dashboard for Milestone 2.
 *
 * The page now surfaces the active season, a recent event day, recent seeded
 * games, and role-aware navigation into the Milestone 3 format and game flows.
 */
import Link from "next/link";
import { useEffect, useState } from "react";

import { PageError, PageLoading } from "@/components/page-state";
import { SiteShell } from "@/components/site-shell";
import { formatDate, formatDateTime } from "@/lib/date";
import {
  getEventDay,
  getSeason,
  getSeasons,
  type EventDayDetail,
  type SeasonDetail,
  type SeasonRecord,
} from "@/lib/api";
import { useAuthenticatedSession } from "@/lib/use-authenticated-session";


export function DashboardShell() {
  const { token, profile, isLoading, errorMessage: sessionErrorMessage, hasRole } = useAuthenticatedSession();
  const [seasons, setSeasons] = useState<SeasonRecord[]>([]);
  const [activeSeason, setActiveSeason] = useState<SeasonRecord | null>(null);
  const [activeSeasonDetail, setActiveSeasonDetail] = useState<SeasonDetail | null>(null);
  const [recentEventDayDetail, setRecentEventDayDetail] = useState<EventDayDetail | null>(null);
  const [dataErrorMessage, setDataErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!token || !profile) {
      return;
    }

    void getSeasons(token)
      .then((response) => {
        setSeasons(response);
        const nextActiveSeason = response.find((season) => season.status === "active") ?? response[0] ?? null;
        setActiveSeason(nextActiveSeason);
      })
      .catch((error) => {
        setDataErrorMessage(error instanceof Error ? error.message : "Failed to load seasons.");
      });
  }, [profile, token]);

  useEffect(() => {
    if (!token || !activeSeason) {
      setActiveSeasonDetail(null);
      return;
    }

    void getSeason(token, activeSeason.id)
      .then((response) => {
        setActiveSeasonDetail(response);
      })
      .catch((error) => {
        setDataErrorMessage(error instanceof Error ? error.message : "Failed to load the active season.");
      });
  }, [activeSeason, token]);

  useEffect(() => {
    const recentEventDayId = activeSeasonDetail?.event_days[0]?.id;
    if (!token || !recentEventDayId) {
      setRecentEventDayDetail(null);
      return;
    }

    void getEventDay(token, recentEventDayId)
      .then((response) => {
        setRecentEventDayDetail(response);
      })
      .catch((error) => {
        setDataErrorMessage(error instanceof Error ? error.message : "Failed to load the recent event day.");
      });
  }, [activeSeasonDetail, token]);

  if (isLoading) {
    return <PageLoading message="Loading your dashboard..." />;
  }

  if (!profile) {
    return null;
  }

  const recentEventDay = activeSeasonDetail?.event_days[0] ?? null;
  const showPlayerSummary = hasRole("player") || hasRole("judge");
  const showAdminSummary = hasRole("admin");
  const showJudgeSummary = hasRole("judge");

  return (
    <SiteShell
      profile={profile}
      title="Home"
      description="Milestone 3 adds preset formats, event-day game management, and judge-owned game queues."
    >
      <div className="grid gap-5 lg:grid-cols-2 xl:grid-cols-3">
        {sessionErrorMessage ? <PageError message={sessionErrorMessage} /> : null}
        {dataErrorMessage ? (
          <PageError message={dataErrorMessage} />
        ) : null}

        <article className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">Active Season</p>
          {activeSeason ? (
            <>
              <h2 className="mt-3 text-2xl font-bold text-ink">{activeSeason.name}</h2>
              <p className="mt-2 text-sm text-slate-600">
                {formatDate(activeSeason.start_date)} to {formatDate(activeSeason.end_date)}
              </p>
              <div className="mt-5">
                <Link className="rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800" href={`/seasons/${activeSeason.id}`}>
                  Open Season
                </Link>
              </div>
            </>
          ) : (
            <p className="mt-3 text-sm text-slate-600">No season is available yet.</p>
          )}
        </article>

        <article className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">Recent Event Day</p>
          {recentEventDay ? (
            <>
              <h2 className="mt-3 text-2xl font-bold text-ink">{recentEventDay.title}</h2>
              <p className="mt-2 text-sm text-slate-600">{formatDate(recentEventDay.event_date)} · {recentEventDay.venue}</p>
              <p className="mt-2 text-sm text-slate-600">
                Registration closes: {formatDateTime(recentEventDay.registration_close_at)}
              </p>
              <div className="mt-5">
                <Link className="rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800" href={`/event-days/${recentEventDay.id}`}>
                  View Event Day
                </Link>
              </div>
            </>
          ) : (
            <p className="mt-3 text-sm text-slate-600">No event day is available yet.</p>
          )}
        </article>

        {showPlayerSummary ? (
          <article className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">My Registration Status</p>
            <h2 className="mt-3 text-2xl font-bold text-ink">Season signup flow is live</h2>
            <p className="mt-3 text-sm leading-6 text-slate-600">
              Open registration event days now expose signup directly from their detail page. Your personal registration state is shown there once you sign up.
            </p>
            <div className="mt-5">
              <Link className="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-200" href="/seasons">
                Browse Seasons
              </Link>
            </div>
          </article>
        ) : null}

        {showJudgeSummary ? (
          <article className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">Judge Queue</p>
            <h2 className="mt-3 text-2xl font-bold text-ink">Assigned games are now visible</h2>
            <p className="mt-3 text-sm leading-6 text-slate-600">
              Judges can review only the games assigned to them and open each game detail page from the dedicated queue.
            </p>
            <div className="mt-5">
              <Link className="rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800" href="/judge/games">
                Open Judge Queue
              </Link>
            </div>
          </article>
        ) : null}

        {showAdminSummary ? (
          <article className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">Admin Entry</p>
            <h2 className="mt-3 text-2xl font-bold text-ink">Season, event-day, and game management</h2>
            <p className="mt-3 text-sm leading-6 text-slate-600">
              Create seasons, open registration windows, schedule games, and assign judges from the admin surfaces introduced through Milestones 2 and 3.
            </p>
            <div className="mt-5 flex flex-wrap gap-3">
              <Link className="rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800" href="/admin/seasons">
                Open Admin
              </Link>
              {recentEventDay ? (
                <Link className="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-200" href={`/admin/event-days/${recentEventDay.id}/games`}>
                  Manage Recent Games
                </Link>
              ) : null}
              <Link className="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-200" href="/seasons">
                View Seasons
              </Link>
            </div>
          </article>
        ) : null}

        <article className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">Formats</p>
          <h2 className="mt-3 text-2xl font-bold text-ink">Preset format catalog</h2>
          <p className="mt-3 text-sm leading-6 text-slate-600">
            Browse preset format definitions and inspect their role composition before scheduling event-day games.
          </p>
          <div className="mt-5">
            <Link className="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-200" href="/formats">
              Open Formats
            </Link>
          </div>
        </article>

        <article className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50 lg:col-span-2 xl:col-span-3">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">Current Seasons</p>
          <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {seasons.map((season) => (
              <Link
                key={season.id}
                className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 transition hover:border-slate-300 hover:bg-white"
                href={`/seasons/${season.id}`}
              >
                <div className="text-sm font-semibold text-ink">{season.name}</div>
                <div className="mt-1 text-sm text-slate-600">{formatDate(season.start_date)} to {formatDate(season.end_date)}</div>
                <div className="mt-2 text-xs uppercase tracking-[0.18em] text-slate-400">{season.status}</div>
              </Link>
            ))}
          </div>
        </article>

        {recentEventDayDetail ? (
          <article className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50 lg:col-span-2 xl:col-span-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">Recent Games</p>
                <h2 className="mt-3 text-2xl font-bold text-ink">{recentEventDayDetail.title}</h2>
              </div>
              <Link className="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-200" href={`/event-days/${recentEventDayDetail.id}`}>
                Open Event Day
              </Link>
            </div>

            <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {recentEventDayDetail.games.map((game) => (
                <Link
                  key={game.id}
                  className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 transition hover:border-slate-300 hover:bg-white"
                  href={`/games/${game.id}`}
                >
                  <div className="text-sm font-semibold text-ink">
                    Table {game.table_number} · Game {game.game_number}
                  </div>
                  <div className="mt-1 text-sm text-slate-600">{game.format_name}</div>
                  <div className="mt-2 text-xs uppercase tracking-[0.18em] text-slate-400">
                    {game.game_type} · {game.status}
                  </div>
                </Link>
              ))}
            </div>

            {recentEventDayDetail.games.length === 0 ? (
              <p className="mt-5 text-sm text-slate-600">No games are scheduled on the recent event day yet.</p>
            ) : null}
          </article>
        ) : null}
      </div>
    </SiteShell>
  );
}
