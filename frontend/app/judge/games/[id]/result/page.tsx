"use client";

/**
 * Judge-owned result-entry page.
 *
 * The page supports draft persistence, client-side score preview, and final
 * submission while keeping the backend as the source of truth for persisted
 * scoring and validation.
 */

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";

import { PageError, PageLoading } from "@/components/page-state";
import { SiteShell } from "@/components/site-shell";
import { formatDate, formatDateTime } from "@/lib/date";
import {
  ApiRequestError,
  getGameResultDraft,
  saveGameResultDraft,
  submitGameResult,
  type GamePlayerFaction,
  type GamePlayerFinalStatus,
  type GameResultDraftResponse,
  type ScoreAdjustmentType,
  type ValidationSummary,
} from "@/lib/api";
import {
  buildAdjustmentTotals,
  buildDraftValidation,
  calculateBaseScore,
  type EditableGameResultAdjustment,
  type EditableGameResultPlayer,
} from "@/lib/result-preview";
import { useAuthenticatedSession } from "@/lib/use-authenticated-session";


const playerFactions: Array<GamePlayerFaction> = ["good", "wolf", "third_party"];
const finalStatuses: Array<GamePlayerFinalStatus> = ["alive", "eliminated", "unknown"];
const adjustmentTypes: Array<ScoreAdjustmentType> = [
  "late_penalty",
  "conduct_penalty",
  "judge_bonus",
  "manual_adjustment",
];


function nextRowId(prefix: string): string {
  return `${prefix}-${Math.random().toString(36).slice(2, 10)}`;
}


function createEmptyPlayerRow(): EditableGameResultPlayer {
  return {
    row_id: nextRowId("player"),
    user_id: null,
    seat_number: null,
    role_name: "",
    faction: null,
    final_status: "unknown",
    is_winner: null,
    remarks: "",
  };
}


function createEmptyAdjustmentRow(): EditableGameResultAdjustment {
  return {
    row_id: nextRowId("adjustment"),
    target_seat_number: null,
    adjustment_type: "judge_bonus",
    delta: 0,
    reason: "",
  };
}


function toEditablePlayers(response: GameResultDraftResponse): EditableGameResultPlayer[] {
  if (response.players.length === 0) {
    return response.editable ? [createEmptyPlayerRow()] : [];
  }

  return response.players.map((player) => ({
    row_id: `player-${player.id}`,
    user_id: player.user_id,
    seat_number: player.seat_number,
    role_name: player.role_name ?? "",
    faction: player.faction,
    final_status: player.final_status,
    is_winner: player.is_winner,
    remarks: player.remarks ?? "",
  }));
}


function toEditableAdjustments(response: GameResultDraftResponse): EditableGameResultAdjustment[] {
  return response.adjustments.map((adjustment) => ({
    row_id: `adjustment-${adjustment.id}`,
    target_seat_number: adjustment.target_seat_number,
    adjustment_type: adjustment.adjustment_type,
    delta: adjustment.delta,
    reason: adjustment.reason ?? "",
  }));
}


function parseValidationFromError(error: unknown): ValidationSummary | null {
  if (!(error instanceof ApiRequestError)) {
    return null;
  }

  const detail = error.detail;
  if (!detail || typeof detail !== "object") {
    return null;
  }

  if ("errors" in detail && "warnings" in detail) {
    const validation = detail as { errors: ValidationSummary["errors"]; warnings: ValidationSummary["warnings"] };
    return {
      errors: validation.errors ?? [],
      warnings: validation.warnings ?? [],
    };
  }

  return null;
}


export default function JudgeGameResultPage() {
  const params = useParams<{ id: string }>();
  const gameId = Number(params.id);
  const { token, profile, isLoading } = useAuthenticatedSession({ requiredRoles: ["judge", "admin"] });
  const [draft, setDraft] = useState<GameResultDraftResponse | null>(null);
  const [playerRows, setPlayerRows] = useState<EditableGameResultPlayer[]>([]);
  const [adjustmentRows, setAdjustmentRows] = useState<EditableGameResultAdjustment[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [remoteValidation, setRemoteValidation] = useState<ValidationSummary | null>(null);

  useEffect(() => {
    if (!token || !profile || Number.isNaN(gameId)) {
      return;
    }

    void getGameResultDraft(token, gameId)
      .then((response) => {
        setDraft(response);
        setPlayerRows(toEditablePlayers(response));
        setAdjustmentRows(toEditableAdjustments(response));
        setRemoteValidation(response.validation);
      })
      .catch((error) => {
        setErrorMessage(error instanceof Error ? error.message : "Failed to load the game result draft.");
      });
  }, [gameId, profile, token]);

  const localValidation = useMemo(() => {
    if (!draft) {
      return { errors: [], warnings: [] };
    }
    // The client preview mirrors the current backend rules for fast feedback
    // while editing, but persisted scores always come from the server.
    return buildDraftValidation({
      players: playerRows,
      adjustments: adjustmentRows,
      formatRoles: draft.format_roles,
      formatPlayerCount: draft.game.format.player_count,
      judgeUserId: draft.game.judge_user_id,
    });
  }, [adjustmentRows, draft, playerRows]);

  const previewByRowId = useMemo(() => {
    // Preview scores stay keyed by the local row id so unsaved rows can still
    // render stable totals before the backend assigns database ids.
    const adjustmentTotals = buildAdjustmentTotals(adjustmentRows);
    return Object.fromEntries(
      playerRows.map((player) => {
        const baseScore = calculateBaseScore(player.faction, player.is_winner);
        const adjustmentScore = player.seat_number !== null ? adjustmentTotals[player.seat_number] ?? 0 : 0;
        return [player.row_id, {
          base_score: baseScore,
          adjustment_score: adjustmentScore,
          final_score: baseScore + adjustmentScore,
        }];
      }),
    );
  }, [adjustmentRows, playerRows]);

  const selectablePlayersById = useMemo(
    () => new Map((draft?.selectable_players ?? []).map((player) => [player.user_id, player])),
    [draft?.selectable_players],
  );

  const validation = remoteValidation ?? localValidation;
  const isReadOnly = draft ? !draft.editable : true;

  function resetValidationFeedback() {
    setErrorMessage(null);
    setRemoteValidation(null);
  }

  async function persistDraft(): Promise<GameResultDraftResponse | null> {
    if (!token || !draft) {
      return null;
    }

    // The browser always sends the full editable snapshot. The backend then
    // replaces the current draft in one pass and recalculates all score fields.
    resetValidationFeedback();
    try {
      const response = await saveGameResultDraft(token, gameId, {
        players: playerRows.map((player) => ({
          user_id: player.user_id,
          seat_number: player.seat_number,
          role_name: player.role_name.trim() || null,
          faction: player.faction,
          final_status: player.final_status,
          is_winner: player.is_winner,
          remarks: player.remarks.trim() || null,
        })),
        adjustments: adjustmentRows
          .filter((adjustment) => adjustment.target_seat_number !== null)
          .map((adjustment) => ({
            target_seat_number: adjustment.target_seat_number as number,
            adjustment_type: adjustment.adjustment_type,
            delta: adjustment.delta,
            reason: adjustment.reason.trim() || null,
          })),
      });
      setDraft(response);
      setPlayerRows(toEditablePlayers(response));
      setAdjustmentRows(toEditableAdjustments(response));
      setRemoteValidation(response.validation);
      return response;
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to save the draft.");
      setRemoteValidation(parseValidationFromError(error));
      return null;
    }
  }

  async function handleSaveDraft() {
    setIsSaving(true);
    try {
      await persistDraft();
    } finally {
      setIsSaving(false);
    }
  }

  async function handleSubmitResult() {
    if (!token || !draft) {
      return;
    }

    setIsSubmitting(true);
    try {
      // Submitting first saves the visible draft so the final validation runs
      // against the exact data the judge sees in the current browser state.
      const savedDraft = await persistDraft();
      if (!savedDraft) {
        return;
      }
      const response = await submitGameResult(token, gameId);
      setDraft(response);
      setPlayerRows(toEditablePlayers(response));
      setAdjustmentRows(toEditableAdjustments(response));
      setRemoteValidation(response.validation);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to submit the result.");
      setRemoteValidation(parseValidationFromError(error));
    } finally {
      setIsSubmitting(false);
    }
  }

  if (isLoading) {
    return <PageLoading message="Loading result entry..." />;
  }

  if (!profile || Number.isNaN(gameId)) {
    return null;
  }

  return (
    <SiteShell
      profile={profile}
      title={draft ? `Result Entry · Table ${draft.game.table_number} / Game ${draft.game.game_number}` : "Result Entry"}
      description={draft ? `${draft.game.season_name} · ${draft.game.event_day_title}` : "Judge-owned game result entry."}
      actions={
        draft ? (
          <div className="flex flex-wrap gap-3">
            <Link
              className="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-200"
              href={`/games/${draft.game.id}`}
            >
              Back to Game
            </Link>
            {!isReadOnly ? (
              <>
                <button
                  className="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-200 disabled:bg-slate-100"
                  disabled={isSaving || isSubmitting}
                  onClick={() => void handleSaveDraft()}
                  type="button"
                >
                  {isSaving ? "Saving..." : "Save Draft"}
                </button>
                <button
                  className="rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:bg-slate-400"
                  disabled={isSaving || isSubmitting}
                  onClick={() => void handleSubmitResult()}
                  type="button"
                >
                  {isSubmitting ? "Submitting..." : "Submit Result"}
                </button>
              </>
            ) : null}
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
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Season</div>
                  <div className="mt-2 text-sm font-semibold text-slate-700">{draft.game.season_name}</div>
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Event Day</div>
                  <div className="mt-2 text-sm font-semibold text-slate-700">{draft.game.event_day_title}</div>
                  <div className="mt-1 text-xs text-slate-500">{formatDate(draft.game.event_day_date)}</div>
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Format</div>
                  <div className="mt-2 text-sm font-semibold text-slate-700">{draft.game.format.format_name}</div>
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Judge</div>
                  <div className="mt-2 text-sm font-semibold text-slate-700">{draft.game.judge.display_name}</div>
                </div>
              </div>

              <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Table</div>
                  <div className="mt-2 text-sm text-slate-700">{draft.game.table_number}</div>
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Game Number</div>
                  <div className="mt-2 text-sm text-slate-700">{draft.game.game_number}</div>
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Current Status</div>
                  <div className="mt-2 text-sm text-slate-700">{draft.game.status}</div>
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Submitted At</div>
                  <div className="mt-2 text-sm text-slate-700">{formatDateTime(draft.game.submitted_at)}</div>
                </div>
              </div>

              {isReadOnly ? (
                <div className="mt-5 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-4 text-sm text-amber-800">
                  This result is read-only. Submitted games are waiting for administrator confirmation.
                </div>
              ) : null}
            </section>

            <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
              <div className="flex items-center justify-between gap-3">
                <h2 className="text-2xl font-bold text-ink">Player Results</h2>
                {!isReadOnly ? (
                  <button
                    className="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-200"
                    onClick={() => {
                      resetValidationFeedback();
                      setPlayerRows((current) => [...current, createEmptyPlayerRow()]);
                    }}
                    type="button"
                  >
                    Add Player Row
                  </button>
                ) : null}
              </div>

              <div className="mt-5 overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-200 text-sm">
                  <thead>
                    <tr className="text-left text-slate-500">
                      <th className="px-3 py-3 font-semibold">Seat</th>
                      <th className="px-3 py-3 font-semibold">Player</th>
                      <th className="px-3 py-3 font-semibold">Role</th>
                      <th className="px-3 py-3 font-semibold">Faction</th>
                      <th className="px-3 py-3 font-semibold">Winner</th>
                      <th className="px-3 py-3 font-semibold">Final Status</th>
                      <th className="px-3 py-3 font-semibold">Remarks</th>
                      {!isReadOnly ? <th className="px-3 py-3 font-semibold">Action</th> : null}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {playerRows.map((player) => (
                      <tr key={player.row_id} className="align-top">
                        <td className="px-3 py-4">
                          <input
                            className="w-20 rounded-xl border border-slate-200 px-3 py-2"
                            disabled={isReadOnly}
                            min={1}
                            onChange={(event) => {
                              resetValidationFeedback();
                              const seatNumber = event.target.value ? Number(event.target.value) : null;
                              setPlayerRows((current) =>
                                current.map((row) => row.row_id === player.row_id ? { ...row, seat_number: seatNumber } : row),
                              );
                            }}
                            type="number"
                            value={player.seat_number ?? ""}
                          />
                        </td>
                        <td className="px-3 py-4">
                          <select
                            className="min-w-52 rounded-xl border border-slate-200 px-3 py-2"
                            disabled={isReadOnly}
                            onChange={(event) => {
                              resetValidationFeedback();
                              const nextUserId = event.target.value ? Number(event.target.value) : null;
                              setPlayerRows((current) =>
                                current.map((row) => row.row_id === player.row_id ? { ...row, user_id: nextUserId } : row),
                              );
                            }}
                            value={player.user_id ?? ""}
                          >
                            <option value="">Select player</option>
                            {draft.selectable_players.map((option) => (
                              <option key={option.user_id} value={option.user_id}>
                                {option.display_name} ({option.username})
                              </option>
                            ))}
                          </select>
                        </td>
                        <td className="px-3 py-4">
                          <input
                            className="min-w-44 rounded-xl border border-slate-200 px-3 py-2"
                            disabled={isReadOnly}
                            list="format-role-options"
                            onChange={(event) => {
                              resetValidationFeedback();
                              setPlayerRows((current) =>
                                current.map((row) => row.row_id === player.row_id ? { ...row, role_name: event.target.value } : row),
                              );
                            }}
                            value={player.role_name}
                          />
                        </td>
                        <td className="px-3 py-4">
                          <select
                            className="min-w-32 rounded-xl border border-slate-200 px-3 py-2"
                            disabled={isReadOnly}
                            onChange={(event) => {
                              resetValidationFeedback();
                              const nextFaction = event.target.value ? event.target.value as GamePlayerFaction : null;
                              setPlayerRows((current) =>
                                current.map((row) => row.row_id === player.row_id ? { ...row, faction: nextFaction } : row),
                              );
                            }}
                            value={player.faction ?? ""}
                          >
                            <option value="">Select faction</option>
                            {playerFactions.map((faction) => (
                              <option key={faction} value={faction}>
                                {faction}
                              </option>
                            ))}
                          </select>
                        </td>
                        <td className="px-3 py-4">
                          <select
                            className="min-w-28 rounded-xl border border-slate-200 px-3 py-2"
                            disabled={isReadOnly}
                            onChange={(event) => {
                              resetValidationFeedback();
                              const value = event.target.value;
                              const nextWinner = value === "" ? null : value === "true";
                              setPlayerRows((current) =>
                                current.map((row) => row.row_id === player.row_id ? { ...row, is_winner: nextWinner } : row),
                              );
                            }}
                            value={player.is_winner === null ? "" : String(player.is_winner)}
                          >
                            <option value="">Select</option>
                            <option value="true">Win</option>
                            <option value="false">Lose</option>
                          </select>
                        </td>
                        <td className="px-3 py-4">
                          <select
                            className="min-w-32 rounded-xl border border-slate-200 px-3 py-2"
                            disabled={isReadOnly}
                            onChange={(event) => {
                              resetValidationFeedback();
                              setPlayerRows((current) =>
                                current.map((row) => row.row_id === player.row_id ? { ...row, final_status: event.target.value as GamePlayerFinalStatus } : row),
                              );
                            }}
                            value={player.final_status}
                          >
                            {finalStatuses.map((finalStatus) => (
                              <option key={finalStatus} value={finalStatus}>
                                {finalStatus}
                              </option>
                            ))}
                          </select>
                        </td>
                        <td className="px-3 py-4">
                          <textarea
                            className="min-h-20 min-w-52 rounded-xl border border-slate-200 px-3 py-2"
                            disabled={isReadOnly}
                            onChange={(event) => {
                              resetValidationFeedback();
                              setPlayerRows((current) =>
                                current.map((row) => row.row_id === player.row_id ? { ...row, remarks: event.target.value } : row),
                              );
                            }}
                            value={player.remarks}
                          />
                        </td>
                        {!isReadOnly ? (
                          <td className="px-3 py-4">
                            <button
                              className="rounded-full bg-slate-100 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-200"
                              onClick={() => {
                                resetValidationFeedback();
                                setPlayerRows((current) => current.filter((row) => row.row_id !== player.row_id));
                              }}
                              type="button"
                            >
                              Remove
                            </button>
                          </td>
                        ) : null}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <datalist id="format-role-options">
                {draft.format_roles.map((role) => (
                  <option key={role.id} value={role.role_name} />
                ))}
              </datalist>
            </section>

            <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
              <div className="flex items-center justify-between gap-3">
                <h2 className="text-2xl font-bold text-ink">Adjustments</h2>
                {!isReadOnly ? (
                  <button
                    className="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-200"
                    onClick={() => {
                      resetValidationFeedback();
                      setAdjustmentRows((current) => [...current, createEmptyAdjustmentRow()]);
                    }}
                    type="button"
                  >
                    Add Adjustment
                  </button>
                ) : null}
              </div>

              <div className="mt-5 overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-200 text-sm">
                  <thead>
                    <tr className="text-left text-slate-500">
                      <th className="px-3 py-3 font-semibold">Target Seat</th>
                      <th className="px-3 py-3 font-semibold">Type</th>
                      <th className="px-3 py-3 font-semibold">Delta</th>
                      <th className="px-3 py-3 font-semibold">Reason</th>
                      {!isReadOnly ? <th className="px-3 py-3 font-semibold">Action</th> : null}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {adjustmentRows.map((adjustment) => (
                      <tr key={adjustment.row_id}>
                        <td className="px-3 py-4">
                          <select
                            className="min-w-28 rounded-xl border border-slate-200 px-3 py-2"
                            disabled={isReadOnly}
                            onChange={(event) => {
                              resetValidationFeedback();
                              const nextSeat = event.target.value ? Number(event.target.value) : null;
                              setAdjustmentRows((current) =>
                                current.map((row) => row.row_id === adjustment.row_id ? { ...row, target_seat_number: nextSeat } : row),
                              );
                            }}
                            value={adjustment.target_seat_number ?? ""}
                          >
                            <option value="">Select seat</option>
                            {playerRows
                              .filter((player) => player.seat_number !== null)
                              .map((player) => (
                                <option key={`${adjustment.row_id}-${player.row_id}`} value={player.seat_number ?? ""}>
                                  Seat {player.seat_number}
                                </option>
                              ))}
                          </select>
                        </td>
                        <td className="px-3 py-4">
                          <select
                            className="min-w-40 rounded-xl border border-slate-200 px-3 py-2"
                            disabled={isReadOnly}
                            onChange={(event) => {
                              resetValidationFeedback();
                              setAdjustmentRows((current) =>
                                current.map((row) => row.row_id === adjustment.row_id ? { ...row, adjustment_type: event.target.value as ScoreAdjustmentType } : row),
                              );
                            }}
                            value={adjustment.adjustment_type}
                          >
                            {adjustmentTypes.map((adjustmentType) => (
                              <option key={adjustmentType} value={adjustmentType}>
                                {adjustmentType}
                              </option>
                            ))}
                          </select>
                        </td>
                        <td className="px-3 py-4">
                          <input
                            className="w-28 rounded-xl border border-slate-200 px-3 py-2"
                            disabled={isReadOnly}
                            onChange={(event) => {
                              resetValidationFeedback();
                              setAdjustmentRows((current) =>
                                current.map((row) => row.row_id === adjustment.row_id ? { ...row, delta: Number(event.target.value || 0) } : row),
                              );
                            }}
                            step="0.5"
                            type="number"
                            value={adjustment.delta}
                          />
                        </td>
                        <td className="px-3 py-4">
                          <textarea
                            className="min-h-20 min-w-56 rounded-xl border border-slate-200 px-3 py-2"
                            disabled={isReadOnly}
                            onChange={(event) => {
                              resetValidationFeedback();
                              setAdjustmentRows((current) =>
                                current.map((row) => row.row_id === adjustment.row_id ? { ...row, reason: event.target.value } : row),
                              );
                            }}
                            value={adjustment.reason}
                          />
                        </td>
                        {!isReadOnly ? (
                          <td className="px-3 py-4">
                            <button
                              className="rounded-full bg-slate-100 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-200"
                              onClick={() => {
                                resetValidationFeedback();
                                setAdjustmentRows((current) => current.filter((row) => row.row_id !== adjustment.row_id));
                              }}
                              type="button"
                            >
                              Remove
                            </button>
                          </td>
                        ) : null}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
              <h2 className="text-2xl font-bold text-ink">Score Preview</h2>
              <div className="mt-5 overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-200 text-sm">
                  <thead>
                    <tr className="text-left text-slate-500">
                      <th className="px-3 py-3 font-semibold">Seat</th>
                      <th className="px-3 py-3 font-semibold">Player</th>
                      <th className="px-3 py-3 font-semibold">Base</th>
                      <th className="px-3 py-3 font-semibold">Adjustment</th>
                      <th className="px-3 py-3 font-semibold">Final</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {playerRows.map((player) => {
                      const preview = previewByRowId[player.row_id] ?? { base_score: 0, adjustment_score: 0, final_score: 0 };
                      const playerOption = player.user_id !== null ? selectablePlayersById.get(player.user_id) : null;
                      return (
                        <tr key={`preview-${player.row_id}`}>
                          <td className="px-3 py-4 text-slate-700">{player.seat_number ?? "Not set"}</td>
                          <td className="px-3 py-4 text-slate-700">{playerOption?.display_name ?? "Not selected"}</td>
                          <td className="px-3 py-4 text-slate-700">{preview.base_score}</td>
                          <td className="px-3 py-4 text-slate-700">{preview.adjustment_score}</td>
                          <td className="px-3 py-4 font-semibold text-ink">{preview.final_score}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </section>

            <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
              <h2 className="text-2xl font-bold text-ink">Validation</h2>
              <div className="mt-5 grid gap-4 md:grid-cols-2">
                <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-4">
                  <div className="text-sm font-semibold text-red-700">Errors</div>
                  <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-red-700">
                    {validation.errors.length > 0 ? (
                      validation.errors.map((message, index) => (
                        <li key={`error-${message.code}-${index}`}>{message.message}</li>
                      ))
                    ) : (
                      <li>No blocking errors.</li>
                    )}
                  </ul>
                </div>
                <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-4">
                  <div className="text-sm font-semibold text-amber-800">Warnings</div>
                  <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-amber-800">
                    {validation.warnings.length > 0 ? (
                      validation.warnings.map((message, index) => (
                        <li key={`warning-${message.code}-${index}`}>{message.message}</li>
                      ))
                    ) : (
                      <li>No warnings.</li>
                    )}
                  </ul>
                </div>
              </div>
            </section>
          </>
        ) : null}
      </div>
    </SiteShell>
  );
}
