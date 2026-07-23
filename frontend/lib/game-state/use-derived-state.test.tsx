import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { GameEventRecord } from "@/lib/api";
import { useDerivedState } from "@/lib/game-state/use-derived-state";
import { derivedStateFixture } from "@/test/derived-state-fixture";


const apiMocks = vi.hoisted(() => ({
  getGameDerivedState: vi.fn(),
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...await importOriginal<typeof import("@/lib/api")>(),
  ...apiMocks,
}));

function event(id: number): GameEventRecord {
  return {
    id,
    game_id: 1,
    sequence_no: id,
    logical_sequence_no: id,
    phase: "night",
    round_no: 1,
    event_type: "phase_started",
    actor_participant_id: null,
    target_participant_id: null,
    secondary_target_participant_id: null,
    actor: null,
    target: null,
    secondary_target: null,
    payload: {},
    visibility: "public",
    source: "manual",
    schema_version: 1,
    status: "active",
    supersedes_event_id: null,
    revision_reason: null,
    invalidated_at: null,
    invalidated_by_user_id: null,
    invalidation_reason: null,
    created_by_user_id: 7,
    created_by: { user_id: 7, username: "judge", display_name: "Judge" },
    created_at: "2026-07-22T10:00:00Z",
    occurred_at: null,
    client_event_id: null,
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((resolver) => { resolve = resolver; });
  return { promise, resolve };
}

function Harness() {
  const controller = useDerivedState({ gameId: 1, token: "token" });
  return (
    <div>
      <div data-testid="head">{controller.state?.event_ledger_head_sequence ?? "none"}</div>
      <div data-testid="selection">{controller.selection?.logicalSequence ?? "latest"}</div>
      <button onClick={() => void controller.inspectEvent(event(1))} type="button">inspect-1</button>
      <button onClick={() => void controller.inspectEvent(event(2))} type="button">inspect-2</button>
      <button onClick={() => void controller.showLatest()} type="button">latest</button>
    </div>
  );
}

describe("useDerivedState", () => {
  it("aborts stale prefix requests and never lets an older response replace a newer selection", async () => {
    const first = deferred<ReturnType<typeof derivedStateFixture>>();
    const second = deferred<ReturnType<typeof derivedStateFixture>>();
    apiMocks.getGameDerivedState
      .mockResolvedValueOnce(derivedStateFixture({ event_ledger_head_sequence: 0 }))
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise);
    render(<Harness />);
    await waitFor(() => expect(screen.getByTestId("head")).toHaveTextContent("0"));

    await userEvent.click(screen.getByRole("button", { name: "inspect-1" }));
    await userEvent.click(screen.getByRole("button", { name: "inspect-2" }));
    second.resolve(derivedStateFixture({
      through_logical_sequence: 2,
      event_ledger_head_sequence: 2,
    }));
    await waitFor(() => expect(screen.getByTestId("head")).toHaveTextContent("2"));
    first.resolve(derivedStateFixture({
      through_logical_sequence: 1,
      event_ledger_head_sequence: 1,
    }));

    await waitFor(() => expect(screen.getByTestId("head")).toHaveTextContent("2"));
    expect(screen.getByTestId("selection")).toHaveTextContent("2");
    expect(apiMocks.getGameDerivedState.mock.calls[1][3]).toMatchObject({ aborted: true });
    expect(apiMocks.getGameDerivedState.mock.calls[2][2]).toBe(2);
  });

  it("returns to the latest effective projection", async () => {
    apiMocks.getGameDerivedState.mockResolvedValue(derivedStateFixture());
    render(<Harness />);
    await waitFor(() => expect(apiMocks.getGameDerivedState).toHaveBeenCalled());
    await userEvent.click(screen.getByRole("button", { name: "inspect-1" }));
    await userEvent.click(screen.getByRole("button", { name: "latest" }));
    expect(apiMocks.getGameDerivedState).toHaveBeenLastCalledWith(
      "token",
      1,
      undefined,
      expect.any(AbortSignal),
    );
    expect(screen.getByTestId("selection")).toHaveTextContent("latest");
  });
});
