"use client";

/**
 * Preset format list page.
 *
 * Milestone 3 exposes formats as real data instead of static documentation so
 * admins and judges can reference the same preset catalog before game setup.
 */

import Link from "next/link";
import { useEffect, useState } from "react";

import { PageError, PageLoading } from "@/components/page-state";
import { SiteShell } from "@/components/site-shell";
import { getFormats, type GameFormatRecord } from "@/lib/api";
import { useAuthenticatedSession } from "@/lib/use-authenticated-session";


export default function FormatsPage() {
  const { token, profile, isLoading } = useAuthenticatedSession();
  const [formats, setFormats] = useState<GameFormatRecord[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!token || !profile) {
      return;
    }

    void getFormats(token)
      .then((response) => setFormats(response))
      .catch((error) => {
        setErrorMessage(error instanceof Error ? error.message : "Failed to load formats.");
      });
  }, [profile, token]);

  if (isLoading) {
    return <PageLoading message="Loading preset formats..." />;
  }

  if (!profile) {
    return null;
  }

  return (
    <SiteShell
      profile={profile}
      title="Formats"
      description="Browse the preset format catalog and inspect the role composition behind each format."
    >
      <div className="flex flex-col gap-5">
        {errorMessage ? <PageError message={errorMessage} /> : null}

        <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {formats.map((gameFormat) => (
              <Link
                key={gameFormat.id}
                className="rounded-2xl border border-slate-200 bg-slate-50 p-5 transition hover:border-slate-300 hover:bg-white"
                href={`/formats/${gameFormat.id}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h2 className="text-xl font-semibold text-ink">{gameFormat.format_name}</h2>
                    <p className="mt-2 text-sm text-slate-600">{gameFormat.description ?? "No description yet."}</p>
                  </div>
                  <span
                    className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] ${
                      gameFormat.is_active
                        ? "bg-emerald-50 text-emerald-700"
                        : "bg-slate-200 text-slate-600"
                    }`}
                  >
                    {gameFormat.is_active ? "active" : "inactive"}
                  </span>
                </div>

                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  <div className="rounded-xl bg-white px-3 py-3 text-sm text-slate-700">
                    <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Players</div>
                    <div className="mt-2 font-semibold">{gameFormat.player_count}</div>
                  </div>
                  <div className="rounded-xl bg-white px-3 py-3 text-sm text-slate-700">
                    <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Category</div>
                    <div className="mt-2 font-semibold">{gameFormat.category}</div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </section>
      </div>
    </SiteShell>
  );
}
