"use client";

/**
 * Event-day detail page with self-service registration controls.
 *
 * The page shows public event metadata to authenticated users and overlays the
 * viewer's own registration state when present.
 */

import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { PageError, PageLoading } from "@/components/page-state";
import { SiteShell } from "@/components/site-shell";
import { formatDate, formatDateTime } from "@/lib/date";
import { cancelRegistration, getEventDay, registerForEventDay, type EventDayDetail } from "@/lib/api";
import { useAuthenticatedSession } from "@/lib/use-authenticated-session";


export default function EventDayDetailPage() {
  const params = useParams<{ id: string }>();
  const eventDayId = Number(params.id);
  const { token, profile, isLoading, hasRole } = useAuthenticatedSession();
  const [eventDay, setEventDay] = useState<EventDayDetail | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (!token || !profile || Number.isNaN(eventDayId)) {
      return;
    }

    void getEventDay(token, eventDayId)
      .then((response) => {
        setEventDay(response);
      })
      .catch((error) => {
        setErrorMessage(error instanceof Error ? error.message : "Failed to load the event day.");
      });
  }, [eventDayId, profile, token]);

  if (isLoading) {
    return <PageLoading message="Loading event day..." />;
  }

  if (!profile || Number.isNaN(eventDayId)) {
    return null;
  }

  async function refreshEventDay() {
    if (!token) {
      return;
    }

    const response = await getEventDay(token, eventDayId);
    setEventDay(response);
  }

  async function handleRegister() {
    if (!token) {
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      await registerForEventDay(token, eventDayId, {});
      await refreshEventDay();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to register for the event day.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleCancelRegistration() {
    if (!token || !eventDay?.viewer_registration) {
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      await cancelRegistration(token, eventDay.viewer_registration.id);
      await refreshEventDay();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to cancel the registration.");
    } finally {
      setIsSubmitting(false);
    }
  }

  // The page derives button state from the server-returned event-day status and
  // the viewer's own registration row so the UI stays aligned with backend rules.
  const canRegister =
    eventDay?.status === "open_for_registration" &&
    eventDay.viewer_registration === null;
  const canCancel =
    eventDay?.status === "open_for_registration" &&
    eventDay.viewer_registration !== null &&
    eventDay.viewer_registration.registration_status !== "cancelled";

  return (
    <SiteShell
      profile={profile}
      title={eventDay?.title ?? "Event Day"}
      description={`Season: ${eventDay?.season_name ?? "Loading..."}`}
      actions={
        hasRole("admin") && eventDay ? (
          <div className="flex flex-wrap gap-3">
            <Link className="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-200" href={`/admin/event-days/${eventDay.id}`}>
              Edit Event Day
            </Link>
            <Link className="rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800" href={`/admin/event-days/${eventDay.id}/registrations`}>
              Manage Registrations
            </Link>
          </div>
        ) : null
      }
    >
      <div className="flex flex-col gap-5">
        {errorMessage ? <PageError message={errorMessage} /> : null}

        {eventDay ? (
          <>
            <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Date</div>
                  <div className="mt-2 text-sm text-slate-700">{formatDate(eventDay.event_date)}</div>
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Venue</div>
                  <div className="mt-2 text-sm text-slate-700">{eventDay.venue}</div>
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Category</div>
                  <div className="mt-2 text-sm text-slate-700">{eventDay.category}</div>
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Status</div>
                  <div className="mt-2 text-sm text-slate-700">{eventDay.status}</div>
                </div>
              </div>
              <div className="mt-5 grid gap-4 md:grid-cols-2">
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Registration Window</div>
                  <div className="mt-2 text-sm text-slate-700">
                    {formatDateTime(eventDay.registration_open_at)} to {formatDateTime(eventDay.registration_close_at)}
                  </div>
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Registered Players</div>
                  <div className="mt-2 text-sm text-slate-700">{eventDay.registration_count}</div>
                </div>
              </div>
              <div className="mt-5 rounded-2xl bg-slate-50 px-4 py-4 text-sm text-slate-700">
                {eventDay.notes ?? "No notes provided."}
              </div>
            </section>

            <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
              <h2 className="text-2xl font-bold text-ink">My Registration</h2>
              {eventDay.viewer_registration ? (
                <div className="mt-5 grid gap-4 md:grid-cols-2">
                  <div className="rounded-2xl bg-slate-50 px-4 py-4">
                    <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Registration Status</div>
                    <div className="mt-2 text-sm text-slate-700">{eventDay.viewer_registration.registration_status}</div>
                  </div>
                  <div className="rounded-2xl bg-slate-50 px-4 py-4">
                    <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Check-in Status</div>
                    <div className="mt-2 text-sm text-slate-700">{eventDay.viewer_registration.check_in_status}</div>
                  </div>
                  <div className="rounded-2xl bg-slate-50 px-4 py-4">
                    <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Registration Type</div>
                    <div className="mt-2 text-sm text-slate-700">{eventDay.viewer_registration.registration_type}</div>
                  </div>
                  <div className="rounded-2xl bg-slate-50 px-4 py-4">
                    <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Note</div>
                    <div className="mt-2 text-sm text-slate-700">{eventDay.viewer_registration.note ?? "No note."}</div>
                  </div>
                </div>
              ) : (
                <p className="mt-4 text-sm text-slate-600">You have not registered for this event day yet.</p>
              )}

              <div className="mt-5 flex flex-wrap gap-3">
                {canRegister ? (
                  <button
                    className="rounded-full bg-ink px-5 py-3 text-sm font-semibold text-white hover:bg-slate-800 disabled:bg-slate-400"
                    disabled={isSubmitting}
                    onClick={handleRegister}
                    type="button"
                  >
                    {isSubmitting ? "Registering..." : "Register"}
                  </button>
                ) : null}
                {canCancel ? (
                  <button
                    className="rounded-full bg-slate-100 px-5 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-200 disabled:bg-slate-100"
                    disabled={isSubmitting}
                    onClick={handleCancelRegistration}
                    type="button"
                  >
                    {isSubmitting ? "Cancelling..." : "Cancel Registration"}
                  </button>
                ) : null}
              </div>
            </section>

            <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h2 className="text-2xl font-bold text-ink">Games</h2>
                {hasRole("admin") ? (
                  <Link
                    className="rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800"
                    href={`/admin/event-days/${eventDay.id}/games`}
                  >
                    Manage Games
                  </Link>
                ) : null}
              </div>

              <div className="mt-5 grid gap-4">
                {eventDay.games.map((game) => (
                  <Link
                    key={game.id}
                    className="rounded-2xl border border-slate-200 bg-slate-50 p-5 transition hover:border-slate-300 hover:bg-white"
                    href={`/games/${game.id}`}
                  >
                    <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                      <div>
                        <h3 className="text-xl font-semibold text-ink">
                          Table {game.table_number} · Game {game.game_number}
                        </h3>
                        <p className="mt-2 text-sm text-slate-600">
                          {game.format_name} · Judge: {game.judge_display_name}
                        </p>
                      </div>
                      <div className="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700">
                        {game.game_type} · {game.status}
                      </div>
                    </div>
                  </Link>
                ))}

                {eventDay.games.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-600">
                    No games have been created for this event day yet.
                  </div>
                ) : null}
              </div>
            </section>
          </>
        ) : null}
      </div>
    </SiteShell>
  );
}
