"use client";

/**
 * Admin season management page.
 *
 * This page combines season listing and season editing in one place so admins
 * can quickly move between existing seasons and the create form.
 */

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { useI18n } from "@/components/language-provider";
import { PageError, PageLoading } from "@/components/page-state";
import { SiteShell } from "@/components/site-shell";
import { formatDate, toDateInputValue } from "@/lib/date";
import {
  createSeason,
  getSeasons,
  updateSeason,
  type SeasonRecord,
  type SeasonStatus,
} from "@/lib/api";
import { useAuthenticatedSession } from "@/lib/use-authenticated-session";


const seasonStatuses: SeasonStatus[] = ["draft", "active", "completed", "archived"];


export default function AdminSeasonsPage() {
  const { t, enumLabel } = useI18n();
  const { token, profile, isLoading } = useAuthenticatedSession({ requiredRole: "admin" });
  const [seasons, setSeasons] = useState<SeasonRecord[]>([]);
  const [selectedSeasonId, setSelectedSeasonId] = useState<number | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [formState, setFormState] = useState({
    name: "",
    description: "",
    start_date: "",
    end_date: "",
    status: "draft" as SeasonStatus,
  });

  useEffect(() => {
    if (!token || !profile) {
      return;
    }

    void getSeasons(token)
      .then((response) => {
        setSeasons(response);
      })
      .catch((error) => {
        setErrorMessage(error instanceof Error ? error.message : t("seasons.loadError"));
      });
  }, [profile, t, token]);

  const selectedSeason = useMemo(
    () => seasons.find((season) => season.id === selectedSeasonId) ?? null,
    [seasons, selectedSeasonId],
  );

  if (isLoading) {
    return <PageLoading message={`${t("admin.seasons.title")}...`} />;
  }

  if (!profile) {
    return null;
  }

  function syncFormFromSeason(season: SeasonRecord | null) {
    if (!season) {
      setFormState({
        name: "",
        description: "",
        start_date: "",
        end_date: "",
        status: "draft",
      });
      return;
    }

    setFormState({
      name: season.name,
      description: season.description ?? "",
      start_date: toDateInputValue(season.start_date),
      end_date: toDateInputValue(season.end_date),
      status: season.status,
    });
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) {
      return;
    }

    setIsSaving(true);
    setErrorMessage(null);

    try {
      if (selectedSeason) {
        await updateSeason(token, selectedSeason.id, {
          name: formState.name,
          description: formState.description || null,
          start_date: formState.start_date,
          end_date: formState.end_date,
          status: formState.status,
        });
      } else {
        await createSeason(token, {
          name: formState.name,
          description: formState.description || null,
          start_date: formState.start_date,
          end_date: formState.end_date,
          status: formState.status,
        });
      }

      const refreshedSeasons = await getSeasons(token);
      setSeasons(refreshedSeasons);
      setSelectedSeasonId(null);
      syncFormFromSeason(null);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : t("common.failedToLoad"));
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <SiteShell
      profile={profile}
      title={t("admin.seasons.title")}
      description={t("seasons.description")}
    >
      <div className="grid gap-5 xl:grid-cols-[1.1fr_0.9fr]">
        <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-2xl font-bold text-ink">{t("admin.existingSeasons")}</h2>
            <button
              className="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-200"
              onClick={() => {
                setSelectedSeasonId(null);
                syncFormFromSeason(null);
              }}
              type="button"
            >
              {t("common.create")}
            </button>
          </div>

          <div className="mt-5 grid gap-4">
            {seasons.map((season) => (
              <div key={season.id} className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
                <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                  <div>
                    <h3 className="text-xl font-semibold text-ink">{season.name}</h3>
                    <p className="mt-2 text-sm text-slate-600">
                      {t("common.datesRange", {
                        start: formatDate(season.start_date),
                        end: formatDate(season.end_date),
                      })}
                    </p>
                    <p className="mt-2 text-sm text-slate-600">{enumLabel("seasonStatus", season.status)}</p>
                  </div>
                  <div className="flex flex-wrap gap-3">
                    <button
                      className="rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800"
                      onClick={() => {
                        setSelectedSeasonId(season.id);
                        syncFormFromSeason(season);
                      }}
                      type="button"
                    >
                      {t("common.edit")}
                    </button>
                    <Link className="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-200" href={`/seasons/${season.id}`}>
                      {t("common.view")}
                    </Link>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
          <h2 className="text-2xl font-bold text-ink">{selectedSeason ? t("seasons.editSeason") : t("admin.createSeason")}</h2>
          {errorMessage ? <div className="mt-4"><PageError message={errorMessage} /></div> : null}

          <form className="mt-5 grid gap-4" onSubmit={handleSubmit}>
            <input
              className="rounded-2xl border border-slate-200 px-4 py-3 text-sm"
              onChange={(event) => setFormState((current) => ({ ...current, name: event.target.value }))}
              placeholder={t("seasons.title")}
              required
              value={formState.name}
            />
            <textarea
              className="min-h-28 rounded-2xl border border-slate-200 px-4 py-3 text-sm"
              onChange={(event) => setFormState((current) => ({ ...current, description: event.target.value }))}
              placeholder={t("common.note")}
              value={formState.description}
            />
            <input
              className="rounded-2xl border border-slate-200 px-4 py-3 text-sm"
              onChange={(event) => setFormState((current) => ({ ...current, start_date: event.target.value }))}
              required
              type="date"
              value={formState.start_date}
            />
            <input
              className="rounded-2xl border border-slate-200 px-4 py-3 text-sm"
              onChange={(event) => setFormState((current) => ({ ...current, end_date: event.target.value }))}
              required
              type="date"
              value={formState.end_date}
            />
            <select
              className="rounded-2xl border border-slate-200 px-4 py-3 text-sm"
              onChange={(event) => setFormState((current) => ({ ...current, status: event.target.value as SeasonStatus }))}
              value={formState.status}
            >
              {seasonStatuses.map((status) => (
                <option key={status} value={status}>
                  {enumLabel("seasonStatus", status)}
                </option>
              ))}
            </select>
            <button
              className="rounded-full bg-ink px-5 py-3 text-sm font-semibold text-white hover:bg-slate-800 disabled:bg-slate-400"
              disabled={isSaving}
              type="submit"
            >
              {isSaving ? t("resultEntry.saving") : selectedSeason ? t("common.save") : t("admin.createSeason")}
            </button>
          </form>
        </section>
      </div>
    </SiteShell>
  );
}
