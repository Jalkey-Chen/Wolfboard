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

import { PageError, PageLoading } from "@/components/page-state";
import { SiteShell } from "@/components/site-shell";
import { formatDate, formatDateTime } from "@/lib/date";
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
        setErrorMessage(error instanceof Error ? error.message : "Failed to load the season.");
      });
  }, [profile, seasonId, token]);

  if (isLoading) {
    return <PageLoading message="Loading season details..." />;
  }

  if (!profile || Number.isNaN(seasonId)) {
    return null;
  }

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
      setErrorMessage(error instanceof Error ? error.message : "Failed to create the event day.");
    } finally {
      setIsCreatingEventDay(false);
    }
  }

  return (
    <SiteShell
      profile={profile}
      title={season?.name ?? "Season"}
      description={season?.description ?? "Season overview and event-day list."}
      actions={
        hasRole("admin") ? (
          <div className="flex flex-wrap gap-3">
            <Link className="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-200" href="/admin/seasons">
              Edit Season
            </Link>
            <button
              className="rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800"
              onClick={() => setShowCreateForm((value) => !value)}
              type="button"
            >
              {showCreateForm ? "Hide Event Day Form" : "Create Event Day"}
            </button>
          </div>
        ) : null
      }
    >
      <div className="flex flex-col gap-5">
        {errorMessage ? <PageError message={errorMessage} /> : null}

        {season ? (
          <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
            <h2 className="text-2xl font-bold text-ink">Season Overview</h2>
            <div className="mt-4 grid gap-4 md:grid-cols-3">
              <div className="rounded-2xl bg-slate-50 px-4 py-4">
                <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Dates</div>
                <div className="mt-2 text-sm text-slate-700">
                  {formatDate(season.start_date)} to {formatDate(season.end_date)}
                </div>
              </div>
              <div className="rounded-2xl bg-slate-50 px-4 py-4">
                <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Status</div>
                <div className="mt-2 text-sm text-slate-700">{season.status}</div>
              </div>
              <div className="rounded-2xl bg-slate-50 px-4 py-4">
                <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Event Days</div>
                <div className="mt-2 text-sm text-slate-700">{season.event_days.length}</div>
              </div>
            </div>
          </section>
        ) : null}

        {hasRole("admin") && showCreateForm ? (
          <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
            <h2 className="text-2xl font-bold text-ink">Create Event Day</h2>
            <form className="mt-5 grid gap-4 md:grid-cols-2" onSubmit={handleCreateEventDay}>
              <input
                className="rounded-2xl border border-slate-200 px-4 py-3 text-sm"
                onChange={(event) => setFormState((current) => ({ ...current, title: event.target.value }))}
                placeholder="Title"
                required
                value={formState.title}
              />
              <input
                className="rounded-2xl border border-slate-200 px-4 py-3 text-sm"
                onChange={(event) => setFormState((current) => ({ ...current, venue: event.target.value }))}
                placeholder="Venue"
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
                    {category}
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
                    {status}
                  </option>
                ))}
              </select>
              <textarea
                className="min-h-28 rounded-2xl border border-slate-200 px-4 py-3 text-sm md:col-span-2"
                onChange={(event) => setFormState((current) => ({ ...current, notes: event.target.value }))}
                placeholder="Notes"
                value={formState.notes}
              />
              <div className="md:col-span-2">
                <button
                  className="rounded-full bg-ink px-5 py-3 text-sm font-semibold text-white hover:bg-slate-800 disabled:bg-slate-400"
                  disabled={isCreatingEventDay}
                  type="submit"
                >
                  {isCreatingEventDay ? "Creating..." : "Create Event Day"}
                </button>
              </div>
            </form>
          </section>
        ) : null}

        <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
          <h2 className="text-2xl font-bold text-ink">Event Days</h2>
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
                      Status: {eventDay.status} · Category: {eventDay.category}
                    </p>
                    <p className="mt-2 text-sm text-slate-600">
                      Registration window: {formatDateTime(eventDay.registration_open_at)} to {formatDateTime(eventDay.registration_close_at)}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-3">
                    <Link className="rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800" href={`/event-days/${eventDay.id}`}>
                      View Event Day
                    </Link>
                    {hasRole("admin") ? (
                      <Link className="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-200" href={`/admin/event-days/${eventDay.id}`}>
                        Manage
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
