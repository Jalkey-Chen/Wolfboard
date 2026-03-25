"use client";

/**
 * Season detail page with embedded admin event-day creation flow.
 *
 * Keeping event-day creation on the season page reduces navigation overhead
 * for admins while preserving a clear public read path for players.
 */

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { useI18n } from "@/components/language-provider";
import { PageError, PageLoading } from "@/components/page-state";
import { SiteShell } from "@/components/site-shell";
import { formatDate, formatDateTime } from "@/lib/date";
import { getMetaLabelClass } from "@/lib/i18n";
import {
  createEventDay,
  getSeason,
  type EventDayCategory,
  type EventDayStatus,
  type SeasonDetail,
} from "@/lib/api";
import { useAuthenticatedSession } from "@/lib/use-authenticated-session";


const eventDayCategories: EventDayCategory[] = ["official", "fun", "mixed"];
const eventDayStatuses: EventDayStatus[] = [
  "draft",
  "open_for_registration",
  "registration_closed",
  "ongoing",
  "completed",
  "archived",
];


export default function SeasonDetailPage() {
  const params = useParams<{ id: string }>();
  const seasonId = Number(params.id);
  const { t, enumLabel, language } = useI18n();
  const { token, profile, isLoading, hasRole } = useAuthenticatedSession();
  const [season, setSeason] = useState<SeasonDetail | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isCreatingEventDay, setIsCreatingEventDay] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [formState, setFormState] = useState({
    title: "",
    event_date: "",
    venue: "",
    category: "official" as EventDayCategory,
    status: "draft" as EventDayStatus,
    notes: "",
    registration_open_at: "",
    registration_close_at: "",
  });

  useEffect(() => {
    if (!token || !profile || Number.isNaN(seasonId)) {
      return;
    }

    void getSeason(token, seasonId)
      .then((response) => {
        setSeason(response);
      })
      .catch((error) => {
        setErrorMessage(error instanceof Error ? error.message : t("seasons.detail.loadError"));
      });
  }, [profile, seasonId, t, token]);

  if (isLoading) {
    return <PageLoading message={t("seasons.detail.loading")} />;
  }

  if (!profile || Number.isNaN(seasonId)) {
    return null;
  }

  const metaLabelClass = getMetaLabelClass(language);

  async function handleCreateEventDay(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) {
      return;
    }

    setIsCreatingEventDay(true);
    setErrorMessage(null);

    try {
      await createEventDay(token, {
        season_id: seasonId,
        title: formState.title,
        event_date: formState.event_date,
        venue: formState.venue,
        category: formState.category,
        status: formState.status,
        notes: formState.notes || null,
        registration_open_at: formState.registration_open_at || null,
        registration_close_at: formState.registration_close_at || null,
      });

      const refreshedSeason = await getSeason(token, seasonId);
      setSeason(refreshedSeason);
      setShowCreateForm(false);
      setFormState({
        title: "",
        event_date: "",
        venue: "",
        category: "official",
        status: "draft",
        notes: "",
        registration_open_at: "",
        registration_close_at: "",
      });
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : t("common.failedToLoad"));
    } finally {
      setIsCreatingEventDay(false);
    }
  }

  return (
    <SiteShell
      profile={profile}
      title={season?.name ?? t("seasons.title")}
      description={season?.description ?? t("seasons.detail.description")}
      actions={
        hasRole("admin") ? (
          <div className="flex flex-wrap gap-3">
            <Link className="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-200" href="/admin/seasons">
              {t("seasons.editSeason")}
            </Link>
            <button
              className="rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800"
              onClick={() => setShowCreateForm((value) => !value)}
              type="button"
            >
              {showCreateForm ? t("seasons.hideEventDayForm") : t("seasons.createEventDay")}
            </button>
          </div>
        ) : null
      }
    >
      <div className="flex flex-col gap-5">
        {errorMessage ? <PageError message={errorMessage} /> : null}

        {season ? (
          <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
            <h2 className="text-2xl font-bold text-ink">{t("seasons.overview")}</h2>
            <div className="mt-4 grid gap-4 md:grid-cols-3">
              <div className="rounded-2xl bg-slate-50 px-4 py-4">
                <div className={metaLabelClass}>{t("common.date")}</div>
                <div className="mt-2 text-sm text-slate-700">
                  {t("common.datesRange", {
                    start: formatDate(season.start_date),
                    end: formatDate(season.end_date),
                  })}
                </div>
              </div>
              <div className="rounded-2xl bg-slate-50 px-4 py-4">
                <div className={metaLabelClass}>{t("common.status")}</div>
                <div className="mt-2 text-sm text-slate-700">{enumLabel("seasonStatus", season.status)}</div>
              </div>
              <div className="rounded-2xl bg-slate-50 px-4 py-4">
                <div className={metaLabelClass}>{t("seasons.eventDaysCount")}</div>
                <div className="mt-2 text-sm text-slate-700">{season.event_days.length}</div>
              </div>
            </div>
          </section>
        ) : null}

        {hasRole("admin") && showCreateForm ? (
          <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
            <h2 className="text-2xl font-bold text-ink">{t("seasons.createEventDayTitle")}</h2>
            <form className="mt-5 grid gap-4 md:grid-cols-2" onSubmit={handleCreateEventDay}>
              <input
                className="rounded-2xl border border-slate-200 px-4 py-3 text-sm"
                onChange={(event) => setFormState((current) => ({ ...current, title: event.target.value }))}
                placeholder={t("eventDay.title")}
                required
                value={formState.title}
              />
              <input
                className="rounded-2xl border border-slate-200 px-4 py-3 text-sm"
                onChange={(event) => setFormState((current) => ({ ...current, venue: event.target.value }))}
                placeholder={t("common.venue")}
                required
                value={formState.venue}
              />
              <input
                className="rounded-2xl border border-slate-200 px-4 py-3 text-sm"
                onChange={(event) => setFormState((current) => ({ ...current, event_date: event.target.value }))}
                required
                type="date"
                value={formState.event_date}
              />
              <select
                className="rounded-2xl border border-slate-200 px-4 py-3 text-sm"
                onChange={(event) => setFormState((current) => ({ ...current, category: event.target.value as EventDayCategory }))}
                value={formState.category}
              >
                {eventDayCategories.map((category) => (
                  <option key={category} value={category}>
                    {enumLabel("eventDayCategory", category)}
                  </option>
                ))}
              </select>
              <input
                className="rounded-2xl border border-slate-200 px-4 py-3 text-sm"
                onChange={(event) => setFormState((current) => ({ ...current, registration_open_at: event.target.value }))}
                type="datetime-local"
                value={formState.registration_open_at}
              />
              <input
                className="rounded-2xl border border-slate-200 px-4 py-3 text-sm"
                onChange={(event) => setFormState((current) => ({ ...current, registration_close_at: event.target.value }))}
                type="datetime-local"
                value={formState.registration_close_at}
              />
              <select
                className="rounded-2xl border border-slate-200 px-4 py-3 text-sm md:col-span-2"
                onChange={(event) => setFormState((current) => ({ ...current, status: event.target.value as EventDayStatus }))}
                value={formState.status}
              >
                {eventDayStatuses.map((status) => (
                  <option key={status} value={status}>
                    {enumLabel("eventDayStatus", status)}
                  </option>
                ))}
              </select>
              <textarea
                className="min-h-28 rounded-2xl border border-slate-200 px-4 py-3 text-sm md:col-span-2"
                onChange={(event) => setFormState((current) => ({ ...current, notes: event.target.value }))}
                placeholder={t("common.note")}
                value={formState.notes}
              />
              <div className="md:col-span-2">
                <button
                  className="rounded-full bg-ink px-5 py-3 text-sm font-semibold text-white hover:bg-slate-800 disabled:bg-slate-400"
                  disabled={isCreatingEventDay}
                  type="submit"
                >
                  {isCreatingEventDay ? `${t("common.create")}...` : t("seasons.createEventDay")}
                </button>
              </div>
            </form>
          </section>
        ) : null}

        <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
          <h2 className="text-2xl font-bold text-ink">{t("seasons.eventDays")}</h2>
          <div className="mt-5 grid gap-4">
            {season?.event_days.map((eventDay) => (
              <div key={eventDay.id} className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
                <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                  <div>
                    <h3 className="text-xl font-semibold text-ink">{eventDay.title}</h3>
                    <p className="mt-2 text-sm text-slate-600">
                      {formatDate(eventDay.event_date)} · {eventDay.venue}
                    </p>
                    <p className="mt-2 text-sm text-slate-600">
                      {t("common.status")}: {enumLabel("eventDayStatus", eventDay.status)} · {t("common.category")}: {enumLabel("eventDayCategory", eventDay.category)}
                    </p>
                    <p className="mt-2 text-sm text-slate-600">
                      {t("common.registrationWindow")}: {t("common.windowRange", {
                        start: formatDateTime(eventDay.registration_open_at),
                        end: formatDateTime(eventDay.registration_close_at),
                      })}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-3">
                    <Link className="rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800" href={`/event-days/${eventDay.id}`}>
                      {t("seasons.viewEventDay")}
                    </Link>
                    {hasRole("admin") ? (
                      <Link className="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-200" href={`/admin/event-days/${eventDay.id}`}>
                        {t("seasons.manage")}
                      </Link>
                    ) : null}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </SiteShell>
  );
}
