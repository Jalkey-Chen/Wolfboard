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

import { useI18n } from "@/components/language-provider";
import { PageError, PageLoading } from "@/components/page-state";
import { SiteShell } from "@/components/site-shell";
import { formatDate, formatDateTime } from "@/lib/date";
import { getMetaLabelClass } from "@/lib/i18n";
import { cancelRegistration, getEventDay, registerForEventDay, type EventDayDetail } from "@/lib/api";
import { useAuthenticatedSession } from "@/lib/use-authenticated-session";


export default function EventDayDetailPage() {
  const params = useParams<{ id: string }>();
  const eventDayId = Number(params.id);
  const { t, enumLabel, language } = useI18n();
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
        setErrorMessage(error instanceof Error ? error.message : t("eventDay.loadError"));
      });
  }, [eventDayId, profile, t, token]);

  if (isLoading) {
    return <PageLoading message={t("eventDay.loading")} />;
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
      setErrorMessage(error instanceof Error ? error.message : t("eventDay.registerError"));
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
      setErrorMessage(error instanceof Error ? error.message : t("eventDay.cancelError"));
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
  const metaLabelClass = getMetaLabelClass(language);

  return (
    <SiteShell
      profile={profile}
      title={eventDay?.title ?? t("eventDay.title")}
      description={t("eventDay.description", { season: eventDay?.season_name ?? t("common.loading") })}
      actions={
        hasRole("admin") && eventDay ? (
          <div className="flex flex-wrap gap-3">
            <Link className="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-200" href={`/admin/event-days/${eventDay.id}`}>
              {t("eventDay.edit")}
            </Link>
            <Link className="rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800" href={`/admin/event-days/${eventDay.id}/registrations`}>
              {t("eventDay.manageRegistrations")}
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
                  <div className={metaLabelClass}>{t("common.date")}</div>
                  <div className="mt-2 text-sm text-slate-700">{formatDate(eventDay.event_date)}</div>
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className={metaLabelClass}>{t("common.venue")}</div>
                  <div className="mt-2 text-sm text-slate-700">{eventDay.venue}</div>
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className={metaLabelClass}>{t("common.category")}</div>
                  <div className="mt-2 text-sm text-slate-700">{enumLabel("eventDayCategory", eventDay.category)}</div>
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className={metaLabelClass}>{t("common.status")}</div>
                  <div className="mt-2 text-sm text-slate-700">{enumLabel("eventDayStatus", eventDay.status)}</div>
                </div>
              </div>
              <div className="mt-5 grid gap-4 md:grid-cols-2">
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className={metaLabelClass}>{t("common.registrationWindow")}</div>
                  <div className="mt-2 text-sm text-slate-700">
                    {t("common.windowRange", {
                      start: formatDateTime(eventDay.registration_open_at),
                      end: formatDateTime(eventDay.registration_close_at),
                    })}
                  </div>
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className={metaLabelClass}>{t("eventDay.registeredPlayers")}</div>
                  <div className="mt-2 text-sm text-slate-700">{eventDay.registration_count}</div>
                </div>
              </div>
              <div className="mt-5 rounded-2xl bg-slate-50 px-4 py-4 text-sm text-slate-700">
                {eventDay.notes ?? t("common.noNotes")}
              </div>
            </section>

            <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
              <h2 className="text-2xl font-bold text-ink">{t("eventDay.myRegistration")}</h2>
              {eventDay.viewer_registration ? (
                <div className="mt-5 grid gap-4 md:grid-cols-2">
                  <div className="rounded-2xl bg-slate-50 px-4 py-4">
                    <div className={metaLabelClass}>{t("eventDay.registrationStatus")}</div>
                    <div className="mt-2 text-sm text-slate-700">{enumLabel("registrationStatus", eventDay.viewer_registration.registration_status)}</div>
                  </div>
                  <div className="rounded-2xl bg-slate-50 px-4 py-4">
                    <div className={metaLabelClass}>{t("eventDay.checkInStatus")}</div>
                    <div className="mt-2 text-sm text-slate-700">{enumLabel("checkInStatus", eventDay.viewer_registration.check_in_status)}</div>
                  </div>
                  <div className="rounded-2xl bg-slate-50 px-4 py-4">
                    <div className={metaLabelClass}>{t("eventDay.registrationType")}</div>
                    <div className="mt-2 text-sm text-slate-700">{enumLabel("registrationType", eventDay.viewer_registration.registration_type)}</div>
                  </div>
                  <div className="rounded-2xl bg-slate-50 px-4 py-4">
                    <div className={metaLabelClass}>{t("eventDay.note")}</div>
                    <div className="mt-2 text-sm text-slate-700">{eventDay.viewer_registration.note ?? t("common.none")}</div>
                  </div>
                </div>
              ) : (
                <p className="mt-4 text-sm text-slate-600">{t("eventDay.notRegistered")}</p>
              )}

              <div className="mt-5 flex flex-wrap gap-3">
                {canRegister ? (
                  <button
                    className="rounded-full bg-ink px-5 py-3 text-sm font-semibold text-white hover:bg-slate-800 disabled:bg-slate-400"
                    disabled={isSubmitting}
                    onClick={handleRegister}
                    type="button"
                  >
                    {isSubmitting ? t("eventDay.registering") : t("eventDay.register")}
                  </button>
                ) : null}
                {canCancel ? (
                  <button
                    className="rounded-full bg-slate-100 px-5 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-200 disabled:bg-slate-100"
                    disabled={isSubmitting}
                    onClick={handleCancelRegistration}
                    type="button"
                  >
                    {isSubmitting ? t("eventDay.cancelling") : t("eventDay.cancelRegistration")}
                  </button>
                ) : null}
              </div>
            </section>

            <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h2 className="text-2xl font-bold text-ink">{t("eventDay.games")}</h2>
                {hasRole("admin") ? (
                  <Link
                    className="rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800"
                    href={`/admin/event-days/${eventDay.id}/games`}
                  >
                    {t("eventDay.manageGames")}
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
                          {game.table_number}桌 · 第{game.game_number}局
                        </h3>
                        <p className="mt-2 text-sm text-slate-600">
                          {game.format_name} · {enumLabel("role", "judge")}: {game.judge_display_name}
                        </p>
                      </div>
                      <div className="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700">
                        {enumLabel("gameType", game.game_type)} · {enumLabel("gamePlayStatus", game.play_status)} · {enumLabel("gameResultStatus", game.result_status)}
                      </div>
                    </div>
                  </Link>
                ))}

                {eventDay.games.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-600">
                    {t("eventDay.noGames")}
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
