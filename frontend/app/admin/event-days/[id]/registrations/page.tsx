"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";

import { PageError, PageLoading } from "@/components/page-state";
import { SiteShell } from "@/components/site-shell";
import { formatDate } from "@/lib/date";
import {
  getEventDay,
  getEventDayRegistrations,
  updateRegistration,
  type CheckInStatus,
  type EventDayDetail,
  type RegistrationRecord,
  type RegistrationStatus,
  type RegistrationType,
} from "@/lib/api";
import { useAuthenticatedSession } from "@/lib/use-authenticated-session";


const registrationStatuses: RegistrationStatus[] = ["registered", "waitlisted", "cancelled"];
const checkInStatuses: CheckInStatus[] = ["not_checked_in", "checked_in", "absent"];
const registrationTypes: RegistrationType[] = ["main", "substitute", "guest"];


export default function AdminEventDayRegistrationsPage() {
  const params = useParams<{ id: string }>();
  const eventDayId = Number(params.id);
  const { token, profile, isLoading } = useAuthenticatedSession({ requiredRole: "admin" });
  const [eventDay, setEventDay] = useState<EventDayDetail | null>(null);
  const [registrations, setRegistrations] = useState<RegistrationRecord[]>([]);
  const [drafts, setDrafts] = useState<Record<number, RegistrationRecord>>({});
  const [savingId, setSavingId] = useState<number | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!token || !profile || Number.isNaN(eventDayId)) {
      return;
    }

    async function loadPage() {
      try {
        const [eventDayResponse, registrationResponse] = await Promise.all([
          getEventDay(token, eventDayId),
          getEventDayRegistrations(token, eventDayId),
        ]);
        setEventDay(eventDayResponse);
        setRegistrations(registrationResponse);
        setDrafts(
          Object.fromEntries(registrationResponse.map((registration) => [registration.id, registration])),
        );
      } catch (error) {
        setErrorMessage(error instanceof Error ? error.message : "Failed to load registrations.");
      }
    }

    void loadPage();
  }, [eventDayId, profile, token]);

  const rows = useMemo(
    () => registrations.map((registration) => drafts[registration.id] ?? registration),
    [drafts, registrations],
  );

  if (isLoading) {
    return <PageLoading message="Loading admin registration management..." />;
  }

  if (!profile || Number.isNaN(eventDayId)) {
    return null;
  }

  async function refreshRegistrations() {
    if (!token) {
      return;
    }

    const registrationResponse = await getEventDayRegistrations(token, eventDayId);
    setRegistrations(registrationResponse);
    setDrafts(
      Object.fromEntries(registrationResponse.map((registration) => [registration.id, registration])),
    );
  }

  async function handleSave(registrationId: number) {
    if (!token) {
      return;
    }

    const draft = drafts[registrationId];
    if (!draft) {
      return;
    }

    setSavingId(registrationId);
    setErrorMessage(null);

    try {
      await updateRegistration(token, registrationId, {
        registration_status: draft.registration_status,
        check_in_status: draft.check_in_status,
        registration_type: draft.registration_type,
        note: draft.note,
      });
      await refreshRegistrations();
      const updatedEventDay = await getEventDay(token, eventDayId);
      setEventDay(updatedEventDay);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to update the registration.");
    } finally {
      setSavingId(null);
    }
  }

  return (
    <SiteShell
      profile={profile}
      title={eventDay ? `${eventDay.title} · Registrations` : "Registrations"}
      description="Admin-only registration and check-in management for a single event day."
      actions={
        eventDay ? (
          <div className="flex flex-wrap gap-3">
            <Link className="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-200" href={`/admin/event-days/${eventDay.id}`}>
              Edit Event Day
            </Link>
            <Link className="rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800" href={`/event-days/${eventDay.id}`}>
              Public View
            </Link>
          </div>
        ) : null
      }
    >
      <div className="flex flex-col gap-5">
        {errorMessage ? <PageError message={errorMessage} /> : null}

        {eventDay ? (
          <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
            <div className="grid gap-4 md:grid-cols-3">
              <div className="rounded-2xl bg-slate-50 px-4 py-4">
                <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Date</div>
                <div className="mt-2 text-sm text-slate-700">{formatDate(eventDay.event_date)}</div>
              </div>
              <div className="rounded-2xl bg-slate-50 px-4 py-4">
                <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Venue</div>
                <div className="mt-2 text-sm text-slate-700">{eventDay.venue}</div>
              </div>
              <div className="rounded-2xl bg-slate-50 px-4 py-4">
                <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Registration Count</div>
                <div className="mt-2 text-sm text-slate-700">{eventDay.registration_count}</div>
              </div>
            </div>
          </section>
        ) : null}

        <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
          <h2 className="text-2xl font-bold text-ink">Registration List</h2>
          <div className="mt-5 overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead>
                <tr className="text-left text-slate-500">
                  <th className="px-3 py-3 font-semibold">Player</th>
                  <th className="px-3 py-3 font-semibold">Registration</th>
                  <th className="px-3 py-3 font-semibold">Check-in</th>
                  <th className="px-3 py-3 font-semibold">Type</th>
                  <th className="px-3 py-3 font-semibold">Note</th>
                  <th className="px-3 py-3 font-semibold">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {rows.map((registration) => (
                  <tr key={registration.id} className="align-top">
                    <td className="px-3 py-4">
                      <div className="font-semibold text-ink">{registration.display_name}</div>
                      <div className="text-slate-500">{registration.username}</div>
                    </td>
                    <td className="px-3 py-4">
                      <select
                        className="w-full rounded-xl border border-slate-200 px-3 py-2"
                        onChange={(event) =>
                          setDrafts((current) => ({
                            ...current,
                            [registration.id]: {
                              ...registration,
                              registration_status: event.target.value as RegistrationStatus,
                            },
                          }))
                        }
                        value={registration.registration_status}
                      >
                        {registrationStatuses.map((status) => (
                          <option key={status} value={status}>
                            {status}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-3 py-4">
                      <select
                        className="w-full rounded-xl border border-slate-200 px-3 py-2"
                        onChange={(event) =>
                          setDrafts((current) => ({
                            ...current,
                            [registration.id]: {
                              ...registration,
                              check_in_status: event.target.value as CheckInStatus,
                            },
                          }))
                        }
                        value={registration.check_in_status}
                      >
                        {checkInStatuses.map((status) => (
                          <option key={status} value={status}>
                            {status}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-3 py-4">
                      <select
                        className="w-full rounded-xl border border-slate-200 px-3 py-2"
                        onChange={(event) =>
                          setDrafts((current) => ({
                            ...current,
                            [registration.id]: {
                              ...registration,
                              registration_type: event.target.value as RegistrationType,
                            },
                          }))
                        }
                        value={registration.registration_type}
                      >
                        {registrationTypes.map((type) => (
                          <option key={type} value={type}>
                            {type}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-3 py-4">
                      <textarea
                        className="min-h-24 w-full rounded-xl border border-slate-200 px-3 py-2"
                        onChange={(event) =>
                          setDrafts((current) => ({
                            ...current,
                            [registration.id]: {
                              ...registration,
                              note: event.target.value,
                            },
                          }))
                        }
                        value={registration.note ?? ""}
                      />
                    </td>
                    <td className="px-3 py-4">
                      <button
                        className="rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:bg-slate-400"
                        disabled={savingId === registration.id}
                        onClick={() => void handleSave(registration.id)}
                        type="button"
                      >
                        {savingId === registration.id ? "Saving..." : "Save"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </SiteShell>
  );
}
