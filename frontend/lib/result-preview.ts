/**
 * Client-side preview helpers for the Milestone 4 result-entry form.
 *
 * These helpers intentionally mirror the backend's current MVP scoring and
 * validation rules closely enough to provide immediate feedback while editing.
 * The backend remains the source of truth for saved and submitted results.
 */

import type {
  GameFormatContextRole,
  GamePlayerFaction,
  GamePlayerFinalStatus,
  ScoreAdjustmentType,
  ValidationSummary,
} from "@/lib/api";


export type EditableGameResultPlayer = {
  row_id: string;
  participant_id: number | null;
  user_id: number | null;
  seat_number: number | null;
  role_name: string;
  faction: GamePlayerFaction | null;
  final_status: GamePlayerFinalStatus;
  is_winner: boolean | null;
  remarks: string;
};

export type EditableGameResultAdjustment = {
  row_id: string;
  target_seat_number: number | null;
  adjustment_type: ScoreAdjustmentType;
  delta: number;
  reason: string;
};


export function calculateBaseScore(
  faction: GamePlayerFaction | null,
  isWinner: boolean | null,
): number {
  if (faction === null || isWinner === null) {
    return 0;
  }
  if (!isWinner) {
    return -1;
  }
  if (faction === "wolf") {
    return 1.5;
  }
  return 1;
}


export function buildAdjustmentTotals(
  adjustments: EditableGameResultAdjustment[],
): Record<number, number> {
  const totals: Record<number, number> = {};

  for (const adjustment of adjustments) {
    if (adjustment.target_seat_number === null || Number.isNaN(adjustment.target_seat_number)) {
      continue;
    }
    totals[adjustment.target_seat_number] =
      (totals[adjustment.target_seat_number] ?? 0) + adjustment.delta;
  }

  return totals;
}


export function buildDraftValidation(params: {
  players: EditableGameResultPlayer[];
  adjustments: EditableGameResultAdjustment[];
  formatRoles: GameFormatContextRole[];
  formatPlayerCount: number;
  judgeUserId: number;
}): ValidationSummary {
  const errors: ValidationSummary["errors"] = [];
  const warnings: ValidationSummary["warnings"] = [];
  const { players, adjustments, formatRoles, formatPlayerCount, judgeUserId } = params;

  const seatCounts = new Map<number, number>();
  const userCounts = new Map<number, number>();
  const roleNames = new Set(formatRoles.map((role) => role.role_name));
  const validSeats = new Set<number>();

  for (const [index, player] of players.entries()) {
    const fieldPrefix = `players[${index}]`;

    if (player.seat_number !== null) {
      seatCounts.set(player.seat_number, (seatCounts.get(player.seat_number) ?? 0) + 1);
      validSeats.add(player.seat_number);
    }
    if (player.user_id !== null) {
      userCounts.set(player.user_id, (userCounts.get(player.user_id) ?? 0) + 1);
    }

    if (player.seat_number === null) {
      errors.push({ code: "seat_required", message: `Seat number is required for player row ${index + 1}.`, field: `${fieldPrefix}.seat_number` });
    }
    if (player.user_id === null) {
      errors.push({ code: "user_required", message: `Player selection is required for row ${index + 1}.`, field: `${fieldPrefix}.user_id` });
    }
    if (!player.role_name.trim()) {
      errors.push({ code: "role_required", message: `Role name is required for player row ${index + 1}.`, field: `${fieldPrefix}.role_name` });
    } else if (!roleNames.has(player.role_name.trim())) {
      warnings.push({ code: "role_not_in_format", message: `Role '${player.role_name.trim()}' is not part of the selected format.`, field: `${fieldPrefix}.role_name` });
    }
    if (player.faction === null) {
      errors.push({ code: "faction_required", message: `Faction is required for player row ${index + 1}.`, field: `${fieldPrefix}.faction` });
    }
    if (player.is_winner === null) {
      errors.push({ code: "winner_required", message: `Winner flag is required for player row ${index + 1}.`, field: `${fieldPrefix}.is_winner` });
    }
    if (player.user_id === judgeUserId) {
      errors.push({ code: "judge_in_player_list", message: "The assigned judge cannot also appear in the game player list.", field: `${fieldPrefix}.user_id` });
    }
  }

  for (const [seatNumber, count] of seatCounts.entries()) {
    if (count > 1) {
      errors.push({ code: "duplicate_seat_numbers", message: `Seat ${seatNumber} appears more than once in the draft.`, field: "players" });
    }
  }

  for (const [userId, count] of userCounts.entries()) {
    if (count > 1) {
      errors.push({ code: "duplicate_users", message: `User ${userId} appears more than once in the draft.`, field: "players" });
    }
  }

  if (players.length === 0) {
    errors.push({ code: "players_required", message: "At least one player result is required before submission.", field: "players" });
  } else if (players.length !== formatPlayerCount) {
    warnings.push({
      code: "player_count_mismatch",
      message: `The selected format expects ${formatPlayerCount} players, but the draft currently has ${players.length}.`,
      field: "players",
    });
  }

  for (const [index, adjustment] of adjustments.entries()) {
    const fieldPrefix = `adjustments[${index}]`;
    if (adjustment.target_seat_number === null || !validSeats.has(adjustment.target_seat_number)) {
      errors.push({
        code: "invalid_adjustment_target",
        message: `Adjustment row ${index + 1} targets a seat that does not exist in the current draft.`,
        field: `${fieldPrefix}.target_seat_number`,
      });
    }
  }

  return { errors, warnings };
}
