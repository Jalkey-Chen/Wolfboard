"use client";

/**
 * Authenticated season list page.
 *
 * All logged-in users can browse seasons here, while admins also get a direct
 * entry point into the season management page.
 */

import Link from "next/link";
import { useEffect, useState } from "react";

import { useI18n } from "@/components/language-provider";
import { PageError, PageLoading } from "@/components/page-state";
import { SiteShell } from "@/components/site-shell";
import { formatDate } from "@/lib/date";
import { getSeasons, type SeasonRecord } from "@/lib/api";
import { getMetaLabelClass } from "@/lib/i18n";
import { useAuthenticatedSession } from "@/lib/use-authenticated-session";


export default function SeasonsPage() {
  const { t, enumLabel, language } = useI18n();
  const { token, profile, isLoading } = useAuthenticatedSession();
  const [seasons, setSeasons] = useState<SeasonRecord[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

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

  if (isLoading) {
    return <PageLoading message={t("seasons.loading")} />;
  }

  if (!profile) {
    return null;
  }

  const metaLabelClass = getMetaLabelClass(language);

  return (
    <SiteShell
      profile={profile}
      title={t("seasons.title")}
      description={t("seasons.description")}
      actions={
        profile.roles.includes("admin") ? (
          <Link className="rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800" href="/admin/seasons">
            {t("seasons.newSeason")}
          </Link>
        ) : null
      }
    >
      <div className="flex flex-col gap-5">
        {errorMessage ? <PageError message={errorMessage} /> : null}

        <section className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {seasons.map((season) => (
            <Link
              key={season.id}
              className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50 transition hover:border-slate-300 hover:shadow-xl"
              href={`/seasons/${season.id}`}
            >
              <p className={metaLabelClass}>{enumLabel("seasonStatus", season.status)}</p>
              <h2 className="mt-3 text-2xl font-bold text-ink">{season.name}</h2>
              <p className="mt-3 text-sm leading-6 text-slate-600">{season.description ?? t("common.noDescription")}</p>
              <div className="mt-5 text-sm text-slate-600">
                {t("common.datesRange", {
                  start: formatDate(season.start_date),
                  end: formatDate(season.end_date),
                })}
              </div>
            </Link>
          ))}
        </section>
      </div>
    </SiteShell>
  );
}
