"use client";

/**
 * Admin registration and check-in management page.
 *
 * Each row is edited in place and saved explicitly so admins can review several
 * fields together before persisting a check-in or registration-status change.
 */

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";

import { useI18n } from "@/components/language-provider";
import { PageError, PageLoading } from "@/components/page-state";
import { SiteShell } from "@/components/site-shell";
import { formatDate } from "@/lib/date";
import { getMetaLabelClass } from "@/lib/i18n";
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
  const { t, enumLabel, language } = useI18n();
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
        setErrorMessage(error instanceof Error ? error.message : t("common.failedToLoad"));
      }
    }

    void loadPage();
  }, [eventDayId, profile, t, token]);

  const rows = useMemo(
    () => registrations.map((registration) => drafts[registration.id] ?? registration),
    [drafts, registrations],
  );

  if (isLoading) {
    return <PageLoading message={`${t("admin.registrations.title")}...`} />;
  }

  if (!profile || Number.isNaN(eventDayId)) {
    return null;
  }

  const metaLabelClass = getMetaLabelClass(language);

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
      setErrorMessage(error instanceof Error ? error.message : t("common.failedToLoad"));
    } finally {
      setSavingId(null);
    }
  }

  return (
    <SiteShell
      profile={profile}
      title={eventDay ? `${eventDay.title} · ${t("admin.registrations.title")}` : t("admin.registrations.title")}
      description={t("admin.registrations.title")}
      actions={
        eventDay ? (
          <div className="flex flex-wrap gap-3">
            <Link className="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-200" href={`/admin/event-days/${eventDay.id}`}>
              {t("eventDay.edit")}
            </Link>
            <Link className="rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800" href={`/event-days/${eventDay.id}`}>
              {t("common.view")}
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
                <div className={metaLabelClass}>{t("common.date")}</div>
                <div className="mt-2 text-sm text-slate-700">{formatDate(eventDay.event_date)}</div>
              </div>
              <div className="rounded-2xl bg-slate-50 px-4 py-4">
                <div className={metaLabelClass}>{t("common.venue")}</div>
                <div className="mt-2 text-sm text-slate-700">{eventDay.venue}</div>
              </div>
              <div className="rounded-2xl bg-slate-50 px-4 py-4">
                <div className={metaLabelClass}>{t("eventDay.registeredPlayers")}</div>
                <div className="mt-2 text-sm text-slate-700">{eventDay.registration_count}</div>
              </div>
            </div>
          </section>
        ) : null}

        <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
          <h2 className="text-2xl font-bold text-ink">{t("admin.registrations.title")}</h2>
          <div className="mt-5 overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead>
                <tr className="text-left text-slate-500">
                  <th className="px-3 py-3 font-semibold">{t("common.player")}</th>
                  <th className="px-3 py-3 font-semibold">{t("eventDay.registrationStatus")}</th>
                  <th className="px-3 py-3 font-semibold">{t("eventDay.checkInStatus")}</th>
                  <th className="px-3 py-3 font-semibold">{t("eventDay.registrationType")}</th>
                  <th className="px-3 py-3 font-semibold">{t("common.note")}</th>
                  <th className="px-3 py-3 font-semibold">{t("common.actions")}</th>
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
                            {enumLabel("registrationStatus", status)}
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
                            {enumLabel("checkInStatus", status)}
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
                            {enumLabel("registrationType", type)}
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
                        {savingId === registration.id ? t("resultEntry.saving") : t("common.save")}
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
