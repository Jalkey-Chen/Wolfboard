"use client";

/**
 * Admin review detail page for one submitted or revised game result.
 */

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { useI18n } from "@/components/language-provider";
import { PageError, PageLoading } from "@/components/page-state";
import { SiteShell } from "@/components/site-shell";
import { formatDate, formatDateTime } from "@/lib/date";
import { getMetaLabelClass } from "@/lib/i18n";
import {
  confirmGameResult,
  getGameResultDraft,
  rejectGameResult,
  type GameResultDraftResponse,
} from "@/lib/api";
import { useAuthenticatedSession } from "@/lib/use-authenticated-session";


export default function AdminGameReviewPage() {
  const params = useParams<{ id: string }>();
  const gameId = Number(params.id);
  const { t, enumLabel, language } = useI18n();
  const { token, profile, isLoading } = useAuthenticatedSession({ requiredRole: "admin" });
  const [draft, setDraft] = useState<GameResultDraftResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [rejectComment, setRejectComment] = useState("");
  const [confirmComment, setConfirmComment] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (!token || !profile || Number.isNaN(gameId)) {
      return;
    }

    void getGameResultDraft(token, gameId)
      .then((response) => setDraft(response))
      .catch((error) => {
        setErrorMessage(error instanceof Error ? error.message : t("common.failedToLoad"));
      });
  }, [gameId, profile, t, token]);

  async function handleConfirm() {
    if (!token || !draft) {
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      const response = await confirmGameResult(token, draft.game.id, { comment: confirmComment.trim() || null });
      setDraft(response);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : t("common.failedToLoad"));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleReject() {
    if (!token || !draft) {
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      const response = await rejectGameResult(token, draft.game.id, { comment: rejectComment.trim() });
      setDraft(response);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : t("common.failedToLoad"));
    } finally {
      setIsSubmitting(false);
    }
  }

  if (isLoading) {
    return <PageLoading message={`${t("review.detailTitle")}...`} />;
  }

  if (!profile || Number.isNaN(gameId)) {
    return null;
  }

  const canConfirmOrReject = draft?.game.status === "submitted";
  const metaLabelClass = getMetaLabelClass(language);

  return (
    <SiteShell
      profile={profile}
      title={draft ? `${t("review.detailTitle")} · ${draft.game.table_number}桌 / 第${draft.game.game_number}局` : t("review.detailTitle")}
      description={draft ? `${draft.game.season_name} · ${draft.game.event_day_title}` : t("review.queueDescription")}
      actions={
        draft ? (
          <div className="flex flex-wrap gap-3">
            <Link
              className="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-200"
              href="/admin/games/review"
            >
              {t("common.back")}
            </Link>
            <Link
              className="rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800"
              href={`/admin/games/${draft.game.id}/revise`}
            >
              {t("review.reviseResult")}
            </Link>
          </div>
        ) : null
      }
    >
      <div className="flex flex-col gap-5">
        {errorMessage ? <PageError message={errorMessage} /> : null}

        {draft ? (
          <>
            <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className={metaLabelClass}>{t("common.season")}</div>
                  <div className="mt-2 text-sm font-semibold text-slate-700">{draft.game.season_name}</div>
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className={metaLabelClass}>{t("common.eventDay")}</div>
                  <div className="mt-2 text-sm font-semibold text-slate-700">{draft.game.event_day_title}</div>
                  <div className="mt-1 text-xs text-slate-500">{formatDate(draft.game.event_day_date)}</div>
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className={metaLabelClass}>{t("common.format")}</div>
                  <div className="mt-2 text-sm font-semibold text-slate-700">{draft.game.format.format_name}</div>
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className={metaLabelClass}>{t("common.status")}</div>
                  <div className="mt-2 text-sm font-semibold text-slate-700">{enumLabel("gameStatus", draft.game.status)}</div>
                  <div className="mt-1 text-xs text-slate-500">{t("resultEntry.submittedAt")} {formatDateTime(draft.game.submitted_at)}</div>
                </div>
              </div>
            </section>

            <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
              <h2 className="text-2xl font-bold text-ink">{t("resultEntry.playerResults")}</h2>
              <div className="mt-5 overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-200 text-sm">
                  <thead>
                    <tr className="text-left text-slate-500">
                      <th className="px-3 py-3 font-semibold">{t("common.seat")}</th>
                      <th className="px-3 py-3 font-semibold">{t("common.player")}</th>
                      <th className="px-3 py-3 font-semibold">{t("common.role")}</th>
                      <th className="px-3 py-3 font-semibold">{t("common.faction")}</th>
                      <th className="px-3 py-3 font-semibold">{t("common.winner")}</th>
                      <th className="px-3 py-3 font-semibold">{t("common.status")}</th>
                      <th className="px-3 py-3 font-semibold">{t("resultEntry.base")}</th>
                      <th className="px-3 py-3 font-semibold">{t("resultEntry.adjustment")}</th>
                      <th className="px-3 py-3 font-semibold">{t("resultEntry.final")}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {draft.players.map((player) => (
                      <tr key={player.id}>
                        <td className="px-3 py-4 text-slate-700">{player.seat_number}</td>
                        <td className="px-3 py-4 text-slate-700">{player.display_name}</td>
                        <td className="px-3 py-4 text-slate-700">{player.role_name}</td>
                        <td className="px-3 py-4 text-slate-700">{player.faction ? enumLabel("gamePlayerFaction", player.faction) : t("common.notSet")}</td>
                        <td className="px-3 py-4 text-slate-700">{player.is_winner ? t("common.win") : t("common.lose")}</td>
                        <td className="px-3 py-4 text-slate-700">{enumLabel("gamePlayerFinalStatus", player.final_status)}</td>
                        <td className="px-3 py-4 text-slate-700">{player.base_score}</td>
                        <td className="px-3 py-4 text-slate-700">{player.adjustment_score}</td>
                        <td className="px-3 py-4 font-semibold text-ink">{player.final_score}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
              <h2 className="text-2xl font-bold text-ink">{t("resultEntry.adjustments")}</h2>
              <div className="mt-5 overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-200 text-sm">
                  <thead>
                    <tr className="text-left text-slate-500">
                      <th className="px-3 py-3 font-semibold">{t("common.seat")}</th>
                      <th className="px-3 py-3 font-semibold">{t("common.type")}</th>
                      <th className="px-3 py-3 font-semibold">{t("resultEntry.delta")}</th>
                      <th className="px-3 py-3 font-semibold">{t("common.reason")}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {draft.adjustments.map((adjustment) => (
                      <tr key={adjustment.id}>
                        <td className="px-3 py-4 text-slate-700">{adjustment.target_seat_number}</td>
                        <td className="px-3 py-4 text-slate-700">{enumLabel("scoreAdjustmentType", adjustment.adjustment_type)}</td>
                        <td className="px-3 py-4 text-slate-700">{adjustment.delta}</td>
                        <td className="px-3 py-4 text-slate-700">{adjustment.reason ?? t("common.none")}</td>
                      </tr>
                    ))}
                    {draft.adjustments.length === 0 ? (
                      <tr>
                        <td className="px-3 py-4 text-slate-600" colSpan={4}>
                          {t("common.noData")}
                        </td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>
            </section>

            <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
              <h2 className="text-2xl font-bold text-ink">{t("resultEntry.validation")}</h2>
              <div className="mt-5 grid gap-4 md:grid-cols-2">
                <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-4">
                  <div className="text-sm font-semibold text-red-700">{t("resultEntry.errors")}</div>
                  <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-red-700">
                    {draft.validation.errors.length > 0 ? (
                      draft.validation.errors.map((message, index) => (
                        <li key={`review-error-${message.code}-${index}`}>{message.message}</li>
                      ))
                    ) : (
                      <li>{t("common.noErrors")}</li>
                    )}
                  </ul>
                </div>
                <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-4">
                  <div className="text-sm font-semibold text-amber-800">{t("resultEntry.warnings")}</div>
                  <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-amber-800">
                    {draft.validation.warnings.length > 0 ? (
                      draft.validation.warnings.map((message, index) => (
                        <li key={`review-warning-${message.code}-${index}`}>{message.message}</li>
                      ))
                    ) : (
                      <li>{t("common.noWarnings")}</li>
                    )}
                  </ul>
                </div>
              </div>
            </section>

            <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
              <h2 className="text-2xl font-bold text-ink">{t("common.actions")}</h2>
              {/* Confirmation and rejection stay separate here on purpose so the
                  admin has to make an explicit decision before a result becomes
                  effective in the formal score ledger. */}
              <div className="mt-5 grid gap-4 xl:grid-cols-2">
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
                  <label className="text-sm font-semibold text-slate-700" htmlFor="confirm-comment">
                    {t("review.comment")}
                  </label>
                  <textarea
                    className="mt-3 min-h-28 w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm"
                    id="confirm-comment"
                    onChange={(event) => setConfirmComment(event.target.value)}
                    placeholder={t("review.comment")}
                    value={confirmComment}
                  />
                  <button
                    className="mt-4 rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:bg-slate-400"
                    disabled={isSubmitting || !canConfirmOrReject}
                    onClick={() => void handleConfirm()}
                    type="button"
                  >
                    {t("review.confirmResult")}
                  </button>
                </div>

                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
                  <label className="text-sm font-semibold text-slate-700" htmlFor="reject-comment">
                    {t("review.comment")}
                  </label>
                  <textarea
                    className="mt-3 min-h-28 w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm"
                    id="reject-comment"
                    onChange={(event) => setRejectComment(event.target.value)}
                    placeholder={t("review.revisionReason")}
                    value={rejectComment}
                  />
                  <button
                    className="mt-4 rounded-full bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700 disabled:bg-red-300"
                    disabled={isSubmitting || !canConfirmOrReject || rejectComment.trim().length === 0}
                    onClick={() => void handleReject()}
                    type="button"
                  >
                    {t("review.rejectResult")}
                  </button>
                </div>
              </div>
            </section>
          </>
        ) : null}
      </div>
    </SiteShell>
  );
}
