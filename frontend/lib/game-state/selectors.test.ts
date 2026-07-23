import { describe, expect, it } from "vitest";

import { KNOWN_PROJECTION_ISSUE_CODES, projectionIssueMessage } from "@/lib/game-state/issue-messages";
import {
  issuesForParticipant,
  selectActionUsage,
  selectBallots,
  selectParticipants,
  selectRoundSummaries,
  throughSequenceModeLabel,
  uniqueProvenanceEventIds,
} from "@/lib/game-state/selectors";
import { derivedStateFixture } from "@/test/derived-state-fixture";


describe("projection issue messages", () => {
  it("provides Chinese and English copy for every known backend issue code", () => {
    for (const code of KNOWN_PROJECTION_ISSUE_CODES) {
      expect(projectionIssueMessage(code, "zh")).toMatchObject({ known: true });
      expect(projectionIssueMessage(code, "en")).toMatchObject({ known: true });
      expect(projectionIssueMessage(code, "zh").title).not.toBe("");
      expect(projectionIssueMessage(code, "en").explanation).not.toBe("");
    }
  });

  it("uses a readable fallback without hiding an unknown code", () => {
    expect(projectionIssueMessage("future_issue", "zh")).toMatchObject({
      known: false,
      title: "未知投影提示",
    });
    expect(projectionIssueMessage("future_issue", "en")).toMatchObject({
      known: false,
      title: "Unknown projection issue",
    });
  });
});

describe("derived-state selectors", () => {
  it("sorts participants by seat while preserving server active state", () => {
    const fixture = derivedStateFixture();
    const reversed = [...fixture.participants].reverse();
    const selected = selectParticipants(reversed, fixture.issues, "all");
    expect(selected.map((item) => item.participant_id)).toEqual([1, 2]);
    expect(selected[0]).toBe(reversed[1]);
    expect(selected[1].is_active_in_game).toBe(false);
  });

  it("filters participant records and associated issues without deriving exits", () => {
    const fixture = derivedStateFixture();
    expect(selectParticipants(fixture.participants, fixture.issues, "active_record").map((item) => item.participant_id)).toEqual([1]);
    expect(selectParticipants(fixture.participants, fixture.issues, "exit_record").map((item) => item.participant_id)).toEqual([2]);
    expect(selectParticipants(fixture.participants, fixture.issues, "issues").map((item) => item.participant_id)).toEqual([1]);
    expect(issuesForParticipant(fixture.issues, 2)).toEqual([]);
  });

  it("sorts ballots but returns the server tally objects unchanged", () => {
    const fixture = derivedStateFixture();
    const later = {
      ...fixture.ballots[0],
      vote_kind: "exile" as const,
      round_no: 2,
      ballot_no: 2,
      raw_tally: [{ participant_id: 2, vote_weight: 99 }],
      computed_tally: null,
    };
    const result = selectBallots([later, fixture.ballots[0]]);
    expect(result[0]).toBe(fixture.ballots[0]);
    expect(result[1].raw_tally).toEqual([{ participant_id: 2, vote_weight: 99 }]);
    expect(result[1].computed_tally).toBeNull();
  });

  it("filters zero action rows without calculating resource availability", () => {
    const usage = derivedStateFixture().recorded_action_usage;
    expect(selectActionUsage(usage, false).map((item) => item.participant_id)).toEqual([1]);
    expect(selectActionUsage(usage, true)).toEqual(usage);
  });

  it("orders round summaries by round and phase", () => {
    const base = derivedStateFixture().round_summaries[0];
    const result = selectRoundSummaries([
      { ...base, round_no: 2, phase: "day" },
      { ...base, round_no: 1, phase: "day" },
      { ...base, round_no: 1, phase: "night" },
    ]);
    expect(result.map((item) => `${item.round_no}-${item.phase}`)).toEqual([
      "1-night",
      "1-day",
      "2-day",
    ]);
  });

  it("collects stable event provenance and labels projection modes", () => {
    expect(uniqueProvenanceEventIds([3, 1], [1, 2], null)).toEqual([1, 2, 3]);
    expect(throughSequenceModeLabel(null, "zh")).toBe("最新有效状态");
    expect(throughSequenceModeLabel(12, "en")).toBe("Through logical position 12");
  });
});
