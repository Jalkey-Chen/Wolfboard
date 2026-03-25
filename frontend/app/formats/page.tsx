"use client";

/**
 * Preset format list page.
 *
 * Milestone 3 exposes formats as real data instead of static documentation so
 * admins and judges can reference the same preset catalog before game setup.
 */

import Link from "next/link";
import { useEffect, useState } from "react";

import { useI18n } from "@/components/language-provider";
import { PageError, PageLoading } from "@/components/page-state";
import { SiteShell } from "@/components/site-shell";
import { getFormats, type GameFormatRecord } from "@/lib/api";
import { getMetaLabelClass, translatePresetFormatDescription } from "@/lib/i18n";
import { useAuthenticatedSession } from "@/lib/use-authenticated-session";


export default function FormatsPage() {
  const { t, enumLabel, language } = useI18n();
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
        setErrorMessage(error instanceof Error ? error.message : t("formats.loadError"));
      });
  }, [profile, t, token]);

  if (isLoading) {
    return <PageLoading message={t("formats.loading")} />;
  }

  if (!profile) {
    return null;
  }

  const infoLabelClass = getMetaLabelClass(language);
  const statusBadgeClass = language === "zh"
    ? "inline-flex shrink-0 items-center whitespace-nowrap rounded-full px-4 py-1.5 text-sm font-semibold"
    : "inline-flex shrink-0 items-center whitespace-nowrap rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em]";

  return (
    <SiteShell
      profile={profile}
      title={t("formats.title")}
      description={t("formats.description")}
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
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <h2 className="text-xl font-semibold text-ink">{gameFormat.format_name}</h2>
                    <p className="mt-2 min-h-[5.25rem] text-sm leading-7 text-slate-600">
                      {translatePresetFormatDescription(language, gameFormat.format_key, gameFormat.description)}
                    </p>
                  </div>
                  <span
                    className={`${statusBadgeClass} ${
                      gameFormat.is_active
                        ? "bg-emerald-50 text-emerald-700"
                        : "bg-slate-200 text-slate-600"
                    }`}
                  >
                    {gameFormat.is_active ? t("formats.active") : t("formats.inactive")}
                  </span>
                </div>

                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  <div className="rounded-xl bg-white px-3 py-3 text-sm text-slate-700">
                    <div className={infoLabelClass}>{t("formats.playerCount")}</div>
                    <div className="mt-2 font-semibold">{gameFormat.player_count}</div>
                  </div>
                  <div className="rounded-xl bg-white px-3 py-3 text-sm text-slate-700">
                    <div className={infoLabelClass}>{t("common.category")}</div>
                    <div className="mt-2 font-semibold">{enumLabel("formatCategory", gameFormat.category)}</div>
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
