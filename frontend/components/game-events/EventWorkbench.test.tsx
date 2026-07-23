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


const apiMocks = vi.hoisted(() => ({
  getGame: vi.fn(),
  getGameFormatContext: vi.fn(),
  getGameResultDraft: vi.fn(),
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
});
