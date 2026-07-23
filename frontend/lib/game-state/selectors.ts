import type {
  GameDerivedBallotState,
  GameDerivedParticipantState,
  GameDerivedRoundSummary,
  GameProjectionIssue,
  GameRecordedActionUsage,
} from "@/lib/api";


export type ParticipantProjectionFilter = "all" | "active_record" | "exit_record" | "issues";

export function issuesForParticipant(
  issues: GameProjectionIssue[],
  participantId: number,
): GameProjectionIssue[] {
  return issues.filter((issue) => issue.participant_ids.includes(participantId));
}

export function selectParticipants(
  participants: GameDerivedParticipantState[],
  issues: GameProjectionIssue[],
  filter: ParticipantProjectionFilter,
): GameDerivedParticipantState[] {
  return [...participants]
    .filter((participant) => {
      if (filter === "active_record") return participant.is_active_in_game;
      if (filter === "exit_record") return !participant.is_active_in_game;
      if (filter === "issues") return issuesForParticipant(issues, participant.participant_id).length > 0;
      return true;
    })
    .sort((left, right) => {
      if (left.seat_number === null && right.seat_number !== null) return 1;
      if (left.seat_number !== null && right.seat_number === null) return -1;
      return (left.seat_number ?? 0) - (right.seat_number ?? 0)
        || left.participant_id - right.participant_id;
    });
}

export function selectBallots(ballots: GameDerivedBallotState[]): GameDerivedBallotState[] {
  const kindOrder = { sheriff: 0, exile: 1 };
  return [...ballots].sort((left, right) =>
    left.round_no - right.round_no
    || kindOrder[left.vote_kind] - kindOrder[right.vote_kind]
    || left.ballot_no - right.ballot_no,
  );
}

export function hasRecordedActions(usage: GameRecordedActionUsage): boolean {
  return Object.entries(usage).some(([key, value]) =>
    key !== "participant_id" && typeof value === "number" && value > 0,
  );
}

export function selectActionUsage(
  usage: GameRecordedActionUsage[],
  includeZero: boolean,
): GameRecordedActionUsage[] {
  return usage.filter((item) => includeZero || hasRecordedActions(item));
}

export function selectRoundSummaries(
  summaries: GameDerivedRoundSummary[],
): GameDerivedRoundSummary[] {
  const phaseOrder = { night: 0, day: 1 };
  return [...summaries].sort((left, right) =>
    left.round_no - right.round_no
    || phaseOrder[left.phase] - phaseOrder[right.phase],
  );
}

export function uniqueProvenanceEventIds(...groups: Array<number[] | null | undefined>): number[] {
  return [...new Set(groups.flatMap((group) => group ?? []))].sort((left, right) => left - right);
}

export function throughSequenceModeLabel(
  throughLogicalSequence: number | null,
  language: "zh" | "en",
): string {
  if (throughLogicalSequence === null) {
    return language === "zh" ? "最新有效状态" : "Latest effective state";
  }
  return language === "zh"
    ? `截至逻辑位置 ${throughLogicalSequence}`
    : `Through logical position ${throughLogicalSequence}`;
}
