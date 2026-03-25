"use client";

/**
 * Home dashboard for Milestone 2.
 *
 * The page now surfaces the active season, a recent event day, recent seeded
 * games, and role-aware navigation into the Milestone 3 format and game flows.
 */
import Link from "next/link";
import { useEffect, useState } from "react";

import { useI18n } from "@/components/language-provider";
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
  const { t, enumLabel } = useI18n();
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
        setDataErrorMessage(error instanceof Error ? error.message : t("seasons.loadError"));
      });
  }, [profile, t, token]);

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
        setDataErrorMessage(error instanceof Error ? error.message : t("seasons.detail.loadError"));
      });
  }, [activeSeason, t, token]);

  useEffect(() => {
    const recentEventDayId = activeSeasonDetail?.event_days[0]?.id;
    if (!token || !recentEventDayId) {
      setRecentEventDayDetail(null);
      return;
    }

    void getEventDay(token, recentEventDayId)
      .then((response) => {
        // The dashboard keeps one richer event-day payload around so recent
        // game cards can be rendered without over-fetching every season row.
        setRecentEventDayDetail(response);
      })
      .catch((error) => {
        setDataErrorMessage(error instanceof Error ? error.message : t("eventDay.loadError"));
      });
  }, [activeSeasonDetail, t, token]);

  if (isLoading) {
    return <PageLoading message={t("common.loading")} />;
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
      title={t("dashboard.title")}
      description={t("dashboard.description")}
    >
      <div className="grid gap-5 lg:grid-cols-2 xl:grid-cols-3">
        {sessionErrorMessage ? <PageError message={sessionErrorMessage} /> : null}
        {dataErrorMessage ? (
          <PageError message={dataErrorMessage} />
        ) : null}

        <article className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">{t("dashboard.activeSeason")}</p>
          {activeSeason ? (
            <>
              <h2 className="mt-3 text-2xl font-bold text-ink">{activeSeason.name}</h2>
              <p className="mt-2 text-sm text-slate-600">
                {t("common.datesRange", {
                  start: formatDate(activeSeason.start_date),
                  end: formatDate(activeSeason.end_date),
                })}
              </p>
              <div className="mt-5">
                <Link className="rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800" href={`/seasons/${activeSeason.id}`}>
                  {t("dashboard.openSeason")}
                </Link>
              </div>
            </>
          ) : (
            <p className="mt-3 text-sm text-slate-600">{t("dashboard.noSeason")}</p>
          )}
        </article>

        <article className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">{t("dashboard.recentEventDay")}</p>
          {recentEventDay ? (
            <>
              <h2 className="mt-3 text-2xl font-bold text-ink">{recentEventDay.title}</h2>
              <p className="mt-2 text-sm text-slate-600">{formatDate(recentEventDay.event_date)} · {recentEventDay.venue}</p>
              <p className="mt-2 text-sm text-slate-600">
                {t("common.registrationWindow")}: {formatDateTime(recentEventDay.registration_close_at)}
              </p>
              <div className="mt-5">
                <Link className="rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800" href={`/event-days/${recentEventDay.id}`}>
                  {t("dashboard.viewEventDay")}
                </Link>
              </div>
            </>
          ) : (
            <p className="mt-3 text-sm text-slate-600">{t("dashboard.noEventDay")}</p>
          )}
        </article>

        {showPlayerSummary ? (
          <article className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">{t("dashboard.registrationSummary")}</p>
            <h2 className="mt-3 text-2xl font-bold text-ink">{t("dashboard.registrationTitle")}</h2>
            <p className="mt-3 text-sm leading-6 text-slate-600">
              {t("dashboard.registrationDescription")}
            </p>
            <div className="mt-5">
              <Link className="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-200" href="/seasons">
                {t("dashboard.browseSeasons")}
              </Link>
            </div>
          </article>
        ) : null}

        {showJudgeSummary ? (
          <article className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">{t("dashboard.judgeQueue")}</p>
            <h2 className="mt-3 text-2xl font-bold text-ink">{t("dashboard.judgeTitle")}</h2>
            <p className="mt-3 text-sm leading-6 text-slate-600">
              {t("dashboard.judgeDescription")}
            </p>
            <div className="mt-5">
              <Link className="rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800" href="/judge/games">
                {t("dashboard.openJudgeQueue")}
              </Link>
            </div>
          </article>
        ) : null}

        {showAdminSummary ? (
          <article className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">{t("dashboard.adminEntry")}</p>
            <h2 className="mt-3 text-2xl font-bold text-ink">{t("dashboard.adminTitle")}</h2>
            <p className="mt-3 text-sm leading-6 text-slate-600">
              {t("dashboard.adminDescription")}
            </p>
            <div className="mt-5 flex flex-wrap gap-3">
              <Link className="rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800" href="/admin/seasons">
                {t("dashboard.openAdmin")}
              </Link>
              {recentEventDay ? (
                <Link className="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-200" href={`/admin/event-days/${recentEventDay.id}/games`}>
                  {t("dashboard.manageRecentGames")}
                </Link>
              ) : null}
              <Link className="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-200" href="/seasons">
                {t("dashboard.viewSeasons")}
              </Link>
            </div>
          </article>
        ) : null}

        <article className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">{t("dashboard.formats")}</p>
          <h2 className="mt-3 text-2xl font-bold text-ink">{t("dashboard.formatsTitle")}</h2>
          <p className="mt-3 text-sm leading-6 text-slate-600">
            {t("dashboard.formatsDescription")}
          </p>
          <div className="mt-5">
            <Link className="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-200" href="/formats">
              {t("dashboard.openFormats")}
            </Link>
          </div>
        </article>

        <article className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50 lg:col-span-2 xl:col-span-3">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">{t("dashboard.currentSeasons")}</p>
          <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {seasons.map((season) => (
              <Link
                key={season.id}
                className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 transition hover:border-slate-300 hover:bg-white"
                href={`/seasons/${season.id}`}
              >
                <div className="text-sm font-semibold text-ink">{season.name}</div>
                <div className="mt-1 text-sm text-slate-600">
                  {t("common.datesRange", {
                    start: formatDate(season.start_date),
                    end: formatDate(season.end_date),
                  })}
                </div>
                <div className="mt-2 text-xs uppercase tracking-[0.18em] text-slate-400">{enumLabel("seasonStatus", season.status)}</div>
              </Link>
            ))}
          </div>
        </article>

        {recentEventDayDetail ? (
          <article className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50 lg:col-span-2 xl:col-span-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">{t("dashboard.recentGames")}</p>
                <h2 className="mt-3 text-2xl font-bold text-ink">{recentEventDayDetail.title}</h2>
              </div>
              <Link className="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-200" href={`/event-days/${recentEventDayDetail.id}`}>
                {t("dashboard.viewEventDay")}
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
                    {t("dashboard.tableGame", { table: game.table_number, game: game.game_number })}
                  </div>
                  <div className="mt-1 text-sm text-slate-600">{game.format_name}</div>
                  <div className="mt-2 text-xs uppercase tracking-[0.18em] text-slate-400">
                    {enumLabel("gameType", game.game_type)} · {enumLabel("gameStatus", game.status)}
                  </div>
                </Link>
              ))}
            </div>

            {recentEventDayDetail.games.length === 0 ? (
              <p className="mt-5 text-sm text-slate-600">{t("dashboard.noRecentGames")}</p>
            ) : null}
          </article>
        ) : null}
      </div>
    </SiteShell>
  );
}
