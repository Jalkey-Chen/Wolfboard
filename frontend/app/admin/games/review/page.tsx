"use client";

/**
 * Admin review queue for submitted game results.
 *
 * The queue is intentionally focused on submitted games only, because confirmed
 * and revised results already have an effective outcome in the ledger.
 */

import Link from "next/link";
import { useEffect, useState } from "react";

import { useI18n } from "@/components/language-provider";
import { PageError, PageLoading } from "@/components/page-state";
import { SiteShell } from "@/components/site-shell";
import { formatDate, formatDateTime } from "@/lib/date";
import { getReviewQueue, type GameReviewSummary } from "@/lib/api";
import { useAuthenticatedSession } from "@/lib/use-authenticated-session";


export default function AdminGameReviewQueuePage() {
  const { t } = useI18n();
  const { token, profile, isLoading } = useAuthenticatedSession({ requiredRole: "admin" });
  const [games, setGames] = useState<GameReviewSummary[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!token || !profile) {
      return;
    }

    void getReviewQueue(token)
      .then((response) => setGames(response))
      .catch((error) => {
        setErrorMessage(error instanceof Error ? error.message : t("common.failedToLoad"));
      });
  }, [profile, t, token]);

  if (isLoading) {
    return <PageLoading message={`${t("review.queueTitle")}...`} />;
  }

  if (!profile) {
    return null;
  }

  return (
    <SiteShell
      profile={profile}
      title={t("review.queueTitle")}
      description={t("review.queueDescription")}
    >
      <div className="flex flex-col gap-5">
        {errorMessage ? <PageError message={errorMessage} /> : null}

        <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-2xl font-bold text-ink">{t("review.submittedGames")}</h2>
            <span className="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700">
              {t("review.pendingCount", { count: games.length })}
            </span>
          </div>

          <div className="mt-5 grid gap-4">
            {games.map((game) => (
              <div key={game.id} className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
                <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                  <div>
                    <h3 className="text-xl font-semibold text-ink">
                      {game.event_day_title} · {game.table_number}桌 / 第{game.game_number}局
                    </h3>
                    <p className="mt-2 text-sm text-slate-600">
                      {formatDate(game.event_day_date)} · {game.format_name}
                    </p>
                    <p className="mt-2 text-sm text-slate-600">
                      {t("common.judge")}: {game.judge_display_name} · {t("resultEntry.submittedAt")}: {formatDateTime(game.submitted_at)}
                    </p>
                  </div>
                  <Link
                    className="rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800"
                    href={`/admin/games/${game.id}/review`}
                  >
                    {t("games.reviewResult")}
                  </Link>
                </div>
              </div>
            ))}

            {games.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-600">
                {t("review.noSubmittedGames")}
              </div>
            ) : null}
          </div>
        </section>
      </div>
    </SiteShell>
  );
}
