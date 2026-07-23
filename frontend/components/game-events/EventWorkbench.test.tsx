import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { EventWorkbench } from "@/components/game-events/EventWorkbench";
import { LanguageProvider } from "@/components/language-provider";
import type {
  CurrentUserResponse,
  GameDetail,
  GameEventDefinition,
  GameEventRecord,
  GameFormatContext,
  GameResultDraftResponse,
} from "@/lib/api";
import { EVENT_UI_DEFINITIONS } from "@/lib/game-events/definitions";
import { LANGUAGE_STORAGE_KEY } from "@/lib/i18n";
import { derivedStateFixture } from "@/test/derived-state-fixture";


const apiMocks = vi.hoisted(() => ({
  getGame: vi.fn(),
  getGameFormatContext: vi.fn(),
  getGameResultDraft: vi.fn(),
  getGameDerivedState: vi.fn(),
  getGameEvent: vi.fn(),
  listGameEventDefinitions: vi.fn(),
  listGameEvents: vi.fn(),
  startGame: vi.fn(),
  endGame: vi.fn(),
  createGameEvent: vi.fn(),
  correctGameEvent: vi.fn(),
  voidGameEvent: vi.fn(),
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...await importOriginal<typeof import("@/lib/api")>(),
  ...apiMocks,
}));

vi.mock("@/components/site-shell", () => ({
  SiteShell: ({ actions, children, title }: { actions?: React.ReactNode; children: React.ReactNode; title: string }) => (
    <main><h1>{title}</h1>{actions}{children}</main>
  ),
}));

const profile: CurrentUserResponse = {
  roles: ["judge"],
  user: {
    id: 7,
    username: "judge",
    display_name: "Judge",
    email: "judge@example.com",
    account_status: "active",
    created_at: "2026-07-22T09:00:00Z",
    updated_at: "2026-07-22T09:00:00Z",
  },
};

function game(overrides: Partial<GameDetail> = {}): GameDetail {
  return {
    id: 1,
    event_day_id: 1,
    season_id: 1,
    season_name: "Season",
    event_day_title: "Final",
    event_day_date: "2026-07-22",
    event_day_venue: "Hall",
    game_number: 2,
    table_number: 3,
    format_id: 1,
    format_name: "Wolf King Guard",
    format: { id: 1, format_name: "Wolf King Guard", format_key: "wolf_king_guard", player_count: 12 },
    judge_user_id: 7,
    judge_display_name: "Judge",
    judge: { id: 7, username: "judge", display_name: "Judge" },
    game_type: "official",
    play_status: "in_progress",
    result_status: "draft",
    started_at: "2026-07-22T10:00:00Z",
    ended_at: null,
    cancelled_at: null,
    cancelled_by: null,
    cancellation_reason: null,
    notes: null,
    created_at: "2026-07-22T09:00:00Z",
    updated_at: "2026-07-22T10:00:00Z",
    has_format_snapshot: true,
    format_snapshot_id: 2,
    has_result_draft: true,
    submitted_at: null,
    submitted_by: null,
    confirmed_at: null,
    confirmed_by: null,
    ...overrides,
  };
}

const formatContext: GameFormatContext = {
  is_frozen: true,
  source_format_id: 1,
  snapshot_id: 2,
  snapshot_origin: "runtime_freeze",
  snapshot_schema_version: 1,
  format_key: "wolf_king_guard",
  format_name: "Wolf King Guard",
  player_count: 12,
  category: "standard",
  description: null,
  is_system_preset: true,
  frozen_at: "2026-07-22T10:00:00Z",
  frozen_by_user_id: 7,
  roles: [],
};

const definitions = (Object.keys(EVENT_UI_DEFINITIONS) as Array<keyof typeof EVENT_UI_DEFINITIONS>).map<GameEventDefinition>((eventType) => ({
  event_type: eventType,
  allowed_phases: ["night", "day"],
  default_visibility: "public",
  required_actor: false,
  required_target: false,
  allows_actor: false,
  allows_target: false,
  allows_secondary_target: false,
  allowed_sources: ["manual"],
  schema_version: 1,
  payload_schema: { type: "object", properties: {}, required: [], additionalProperties: false },
  payload_field_semantics: {},
}));

function event(): GameEventRecord {
  return {
    id: 1,
    game_id: 1,
    sequence_no: 1,
    logical_sequence_no: 1,
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
    created_at: "2026-07-22T10:01:00Z",
    occurred_at: null,
    client_event_id: "event-id",
  };
}

function draft(players: GameResultDraftResponse["players"] = []): GameResultDraftResponse {
  return {
    game: game(),
    players,
    adjustments: [],
    format_context: formatContext,
    format_roles: [],
    selectable_players: [],
    validation: { errors: [], warnings: [] },
    editable: true,
  };
}

function renderWorkbench() {
  return render(
    <LanguageProvider>
      <EventWorkbench gameId={1} profile={profile} token="token" />
    </LanguageProvider>,
  );
}

describe("EventWorkbench", () => {
  beforeEach(() => {
    apiMocks.getGame.mockResolvedValue(game());
    apiMocks.getGameFormatContext.mockResolvedValue(formatContext);
    apiMocks.getGameResultDraft.mockResolvedValue(draft());
    apiMocks.listGameEventDefinitions.mockResolvedValue(definitions);
    apiMocks.listGameEvents.mockImplementation((_token, _gameId, options) => Promise.resolve(options.view === "ledger" ? [event()] : [event()]));
    apiMocks.getGameDerivedState.mockResolvedValue(derivedStateFixture());
    apiMocks.getGameEvent.mockResolvedValue(event());
    apiMocks.createGameEvent.mockResolvedValue(event());
    apiMocks.correctGameEvent.mockResolvedValue(event());
    apiMocks.voidGameEvent.mockResolvedValue(event());
  });

  it("explains the participant-empty state while retaining participant-free events", async () => {
    renderWorkbench();
    expect(await screen.findByText("尚未设置本局参与者，带有玩家目标的事件无法录入。")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "保存事件" })).toBeEnabled();
  });

  it("renders lifecycle lock reasons and disables mutations", async () => {
    apiMocks.getGame.mockResolvedValue(game({ play_status: "ended", result_status: "submitted", ended_at: "2026-07-22T11:00:00Z" }));
    renderWorkbench();
    expect(await screen.findByText("赛果已提交，事件账本等待审核并保持锁定。")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "保存事件" })).toBeDisabled();
  });

  it("switches explicitly between the effective timeline and full ledger", async () => {
    renderWorkbench();
    await waitFor(() => expect(screen.getByRole("tab", { name: "有效时间线" })).toHaveAttribute("aria-selected", "true"));
    await userEvent.click(screen.getByRole("tab", { name: "完整账本" }));
    expect(screen.getByRole("tab", { name: "完整账本" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText("以下筛选仅作用于当前已加载的账本记录。")).toBeInTheDocument();
  });

  it("loads the latest server projection and displays recorded state without adjudication language", async () => {
    renderWorkbench();
    await userEvent.click(await screen.findByRole("tab", { name: "推导状态" }));
    expect(await screen.findByRole("heading", { name: "记录状态投影" })).toBeInTheDocument();
    expect(screen.getByText(/不代表自动裁判结果/)).toBeInTheDocument();
    expect(screen.getByText("明确记录的开放阶段：第1轮 · 夜晚")).toBeInTheDocument();
    expect(screen.getByText("警徽由 1 · Player One 持有")).toBeInTheDocument();
    expect(screen.getByText("同一投票人存在多条有效投票记录，无法形成唯一计算票型。")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "投影提示" })).toBeInTheDocument();
    expect(apiMocks.getGameDerivedState).toHaveBeenCalledWith("token", 1, undefined, expect.any(AbortSignal));
  });

  it("shows empty and unknown-phase copy from an empty server projection", async () => {
    apiMocks.getGameDerivedState.mockResolvedValue(derivedStateFixture({
      effective_event_count: 0,
      last_applied_logical_sequence: null,
      phase: {
        current_phase: null,
        current_round_no: null,
        phase_is_open: false,
        phase_started_event_id: null,
        last_completed_phase: null,
        last_completed_round_no: null,
        last_completed_event_id: null,
        last_observed_phase: null,
        last_observed_round_no: null,
        last_observed_event_id: null,
      },
      ballots: [],
      recorded_actions: [],
      round_summaries: [],
      issues: [],
    }));
    renderWorkbench();
    await userEvent.click(await screen.findByRole("tab", { name: "推导状态" }));
    expect(await screen.findByText("未记录明确的开放阶段")).toBeInTheDocument();
    expect(screen.getByText(/尚无有效事件/)).toBeInTheDocument();
  });

  it("keeps event entry available when the independent derived-state request fails", async () => {
    apiMocks.getGameDerivedState.mockRejectedValue(new Error("projection offline"));
    renderWorkbench();
    expect(await screen.findByRole("button", { name: "保存事件" })).toBeEnabled();
    await userEvent.click(screen.getByRole("tab", { name: "推导状态" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("projection offline");
    expect(screen.getByRole("button", { name: "重试" })).toBeInTheDocument();
  });

  it("inspects a current effective prefix and returns to latest state", async () => {
    apiMocks.getGameDerivedState.mockImplementation((_token, _gameId, sequence) => Promise.resolve(
      derivedStateFixture({
        through_logical_sequence: sequence ?? null,
        effective_event_count: sequence ?? 4,
        last_applied_logical_sequence: sequence ?? 4,
      }),
    ));
    renderWorkbench();
    const inspect = await screen.findByRole("button", { name: "查看此事件后的状态" });
    await userEvent.click(inspect);
    expect(await screen.findByText("根据当前有效时间线，应用至逻辑位置 1 后的状态。")).toBeInTheDocument();
    expect(apiMocks.getGameDerivedState).toHaveBeenLastCalledWith("token", 1, 1, expect.any(AbortSignal));
    await userEvent.click(screen.getByRole("button", { name: "返回最新状态" }));
    expect(apiMocks.getGameDerivedState).toHaveBeenLastCalledWith("token", 1, undefined, expect.any(AbortSignal));
  });

  it("refreshes projection after a write while preserving prefix mode", async () => {
    apiMocks.getGameDerivedState.mockImplementation((_token, _gameId, sequence) => Promise.resolve(
      derivedStateFixture({ through_logical_sequence: sequence ?? null }),
    ));
    renderWorkbench();
    await userEvent.click(await screen.findByRole("button", { name: "查看此事件后的状态" }));
    await userEvent.click(screen.getByRole("button", { name: "保存事件" }));
    await waitFor(() => expect(apiMocks.createGameEvent).toHaveBeenCalled());
    await waitFor(() => expect(apiMocks.getGameDerivedState).toHaveBeenLastCalledWith(
      "token",
      1,
      1,
      expect.any(AbortSignal),
    ));
    expect(screen.getByText("账本已更新，当前仍查看逻辑位置 1 的状态。")).toBeInTheDocument();
  });

  it("refreshes derived state after correction and void workflows", async () => {
    renderWorkbench();
    await screen.findByRole("button", { name: "纠正" });
    const initialCalls = apiMocks.getGameDerivedState.mock.calls.length;

    await userEvent.click(screen.getByRole("button", { name: "纠正" }));
    await userEvent.type(screen.getByLabelText(/原因/), "corrected record");
    await userEvent.click(screen.getByRole("button", { name: "保存纠正版本" }));
    await waitFor(() => expect(apiMocks.correctGameEvent).toHaveBeenCalled());
    await waitFor(() => expect(apiMocks.getGameDerivedState.mock.calls.length).toBeGreaterThan(initialCalls));

    const afterCorrection = apiMocks.getGameDerivedState.mock.calls.length;
    await userEvent.click(screen.getByRole("button", { name: "作废" }));
    await userEvent.type(screen.getByLabelText(/原因/), "voided record");
    await userEvent.click(screen.getByRole("button", { name: "确认作废" }));
    await waitFor(() => expect(apiMocks.voidGameEvent).toHaveBeenCalled());
    await waitFor(() => expect(apiMocks.getGameDerivedState.mock.calls.length).toBeGreaterThan(afterCorrection));
  });

  it("locates provenance in the effective timeline and moves keyboard focus", async () => {
    renderWorkbench();
    await userEvent.click(await screen.findByRole("tab", { name: "推导状态" }));
    await userEvent.click((await screen.findAllByRole("button", { name: "事件 #1" }))[0]);
    await waitFor(() => expect(document.activeElement).toHaveAttribute("id", "event-1"));
    expect(screen.getByRole("tab", { name: "有效时间线" })).toHaveAttribute("aria-selected", "true");
  });

  it("keeps a locked game projection readable", async () => {
    apiMocks.getGame.mockResolvedValue(game({
      play_status: "ended",
      result_status: "confirmed",
      ended_at: "2026-07-22T11:00:00Z",
      confirmed_at: "2026-07-22T12:00:00Z",
      confirmed_by: 1,
    }));
    renderWorkbench();
    await userEvent.click(await screen.findByRole("tab", { name: "推导状态" }));
    expect(await screen.findByText("事件账本已锁定，但推导状态仍可查看。它仍然只是事件投影。")).toBeInTheDocument();
  });

  it("renders unknown issues safely and preserves server participant state despite shot records", async () => {
    const base = derivedStateFixture();
    apiMocks.getGameDerivedState.mockResolvedValue(derivedStateFixture({
      participants: base.participants.map((participant) => ({
        ...participant,
        is_active_in_game: true,
        has_exile_record: false,
        exit_event_ids: [],
      })),
      recorded_actions: [{
        event_type: "hunter_shot",
        phase: "day",
        round_no: 1,
        actor_participant_id: 1,
        event_ids: [4],
        recorded_count: 1,
        latest_recorded_target_participant_id: 2,
      }],
      issues: [{
        code: "future_projection_issue",
        severity: "info",
        message_key: "projection.issue.future_projection_issue",
        event_ids: [4],
        participant_ids: [2],
        round_no: 1,
        phase: "day",
        details: {},
      }],
    }));
    renderWorkbench();
    await userEvent.click(await screen.findByRole("tab", { name: "推导状态" }));
    expect(await screen.findByText("未知投影提示")).toBeInTheDocument();
    expect(screen.getAllByText("future_projection_issue")).toHaveLength(2);
    expect(screen.getAllByText("未见明确出局记录")).toHaveLength(3);
  });

  it("renders the critical projection boundary in English", async () => {
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, "en");
    renderWorkbench();
    await userEvent.click(await screen.findByRole("tab", { name: "Derived State" }));
    expect(await screen.findByRole("heading", { name: "Recorded State Projection" })).toBeInTheDocument();
    expect(screen.getByText(/not automated adjudication/)).toBeInTheDocument();
  });
});
