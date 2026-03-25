"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { PageError, PageLoading } from "@/components/page-state";
import { SiteShell } from "@/components/site-shell";
import { formatDateTime, toDateTimeLocalValue } from "@/lib/date";
import {
  getEventDay,
  updateEventDay,
  type EventDayCategory,
  type EventDayDetail,
  type EventDayStatus,
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


export default function AdminEventDayPage() {
  const params = useParams<{ id: string }>();
  const eventDayId = Number(params.id);
  const { token, profile, isLoading } = useAuthenticatedSession({ requiredRole: "admin" });
  const [eventDay, setEventDay] = useState<EventDayDetail | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
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
    if (!token || !profile || Number.isNaN(eventDayId)) {
      return;
    }

    void getEventDay(token, eventDayId)
      .then((response) => {
        setEventDay(response);
        setFormState({
          title: response.title,
          event_date: response.event_date.slice(0, 10),
          venue: response.venue,
          category: response.category,
          status: response.status,
          notes: response.notes ?? "",
          registration_open_at: toDateTimeLocalValue(response.registration_open_at),
          registration_close_at: toDateTimeLocalValue(response.registration_close_at),
        });
      })
      .catch((error) => {
        setErrorMessage(error instanceof Error ? error.message : "Failed to load the event day.");
      });
  }, [eventDayId, profile, token]);

  if (isLoading) {
    return <PageLoading message="Loading admin event-day management..." />;
  }

  if (!profile || Number.isNaN(eventDayId)) {
    return null;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) {
      return;
    }

    setIsSaving(true);
    setErrorMessage(null);

    try {
      const updatedEventDay = await updateEventDay(token, eventDayId, {
        title: formState.title,
        event_date: formState.event_date,
        venue: formState.venue,
        category: formState.category,
        status: formState.status,
        notes: formState.notes || null,
        registration_open_at: formState.registration_open_at || null,
        registration_close_at: formState.registration_close_at || null,
      });
      setEventDay(updatedEventDay);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to update the event day.");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <SiteShell
      profile={profile}
      title={eventDay?.title ?? "Manage Event Day"}
      description="Edit event-day information and open the registration management surface."
      actions={
        eventDay ? (
          <div className="flex flex-wrap gap-3">
            <Link className="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-200" href={`/event-days/${eventDay.id}`}>
              Public View
            </Link>
            <Link className="rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800" href={`/admin/event-days/${eventDay.id}/registrations`}>
              Manage Registrations
            </Link>
          </div>
        ) : null
      }
    >
      <div className="grid gap-5 xl:grid-cols-[1fr_0.8fr]">
        <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
          <h2 className="text-2xl font-bold text-ink">Edit Event Day</h2>
          {errorMessage ? <div className="mt-4"><PageError message={errorMessage} /></div> : null}
          <form className="mt-5 grid gap-4 md:grid-cols-2" onSubmit={handleSubmit}>
            <input
              className="rounded-2xl border border-slate-200 px-4 py-3 text-sm md:col-span-2"
              onChange={(event) => setFormState((current) => ({ ...current, title: event.target.value }))}
              required
              value={formState.title}
            />
            <input
              className="rounded-2xl border border-slate-200 px-4 py-3 text-sm"
              onChange={(event) => setFormState((current) => ({ ...current, event_date: event.target.value }))}
              required
              type="date"
              value={formState.event_date}
            />
            <input
              className="rounded-2xl border border-slate-200 px-4 py-3 text-sm"
              onChange={(event) => setFormState((current) => ({ ...current, venue: event.target.value }))}
              required
              value={formState.venue}
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
            <select
              className="rounded-2xl border border-slate-200 px-4 py-3 text-sm"
              onChange={(event) => setFormState((current) => ({ ...current, status: event.target.value as EventDayStatus }))}
              value={formState.status}
            >
              {eventDayStatuses.map((status) => (
                <option key={status} value={status}>
                  {status}
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
            <textarea
              className="min-h-32 rounded-2xl border border-slate-200 px-4 py-3 text-sm md:col-span-2"
              onChange={(event) => setFormState((current) => ({ ...current, notes: event.target.value }))}
              value={formState.notes}
            />
            <div className="md:col-span-2">
              <button
                className="rounded-full bg-ink px-5 py-3 text-sm font-semibold text-white hover:bg-slate-800 disabled:bg-slate-400"
                disabled={isSaving}
                type="submit"
              >
                {isSaving ? "Saving..." : "Save Event Day"}
              </button>
            </div>
          </form>
        </section>

        {eventDay ? (
          <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
            <h2 className="text-2xl font-bold text-ink">Registration Snapshot</h2>
            <div className="mt-5 space-y-4 text-sm text-slate-700">
              <div className="rounded-2xl bg-slate-50 px-4 py-4">
                <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Current Registration Window</div>
                <div className="mt-2">
                  {formatDateTime(eventDay.registration_open_at)} to {formatDateTime(eventDay.registration_close_at)}
                </div>
              </div>
              <div className="rounded-2xl bg-slate-50 px-4 py-4">
                <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Current Registration Count</div>
                <div className="mt-2">{eventDay.registration_count}</div>
              </div>
            </div>
          </section>
        ) : null}
      </div>
    </SiteShell>
  );
}
