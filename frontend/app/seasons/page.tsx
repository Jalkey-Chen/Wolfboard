"use client";

/**
 * Authenticated season list page.
 *
 * All logged-in users can browse seasons here, while admins also get a direct
 * entry point into the season management page.
 */

import Link from "next/link";
import { useEffect, useState } from "react";

import { PageError, PageLoading } from "@/components/page-state";
import { SiteShell } from "@/components/site-shell";
import { formatDate } from "@/lib/date";
import { getSeasons, type SeasonRecord } from "@/lib/api";
import { useAuthenticatedSession } from "@/lib/use-authenticated-session";


export default function SeasonsPage() {
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
        setErrorMessage(error instanceof Error ? error.message : "Failed to load seasons.");
      });
  }, [profile, token]);

  if (isLoading) {
    return <PageLoading message="Loading seasons..." />;
  }

  if (!profile) {
    return null;
  }

  return (
    <SiteShell
      profile={profile}
      title="Seasons"
      description="Browse all seasons and jump into their event days."
      actions={
        profile.roles.includes("admin") ? (
          <Link className="rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800" href="/admin/seasons">
            New Season
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
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">{season.status}</p>
              <h2 className="mt-3 text-2xl font-bold text-ink">{season.name}</h2>
              <p className="mt-3 text-sm leading-6 text-slate-600">{season.description ?? "No description provided."}</p>
              <div className="mt-5 text-sm text-slate-600">
                {formatDate(season.start_date)} to {formatDate(season.end_date)}
              </div>
            </Link>
          ))}
        </section>
      </div>
    </SiteShell>
  );
}
