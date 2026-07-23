import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { GameEventComposer } from "@/components/game-events/GameEventComposer";
import { CorrectEventDialog } from "@/components/game-events/CorrectEventDialog";
import { VoidEventDialog } from "@/components/game-events/VoidEventDialog";
import { LanguageProvider } from "@/components/language-provider";
import type { GameEventDefinition, GameEventRecord } from "@/lib/api";
import { eventDraftStorageKey } from "@/lib/game-events/draft-storage";


function definition(
  type: GameEventDefinition["event_type"],
  options: Partial<GameEventDefinition> = {},
): GameEventDefinition {
  return {
    event_type: type,
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
    ...options,
  };
}

const phaseDefinition = definition("phase_started");
const seerDefinition = definition("seer_checked", {
  allowed_phases: ["night"],
  required_actor: true,
  required_target: true,
  allows_actor: true,
  allows_target: true,
  payload_schema: {
    type: "object",
    properties: { result_faction: { type: "string", enum: ["good", "wolf", "third_party", "special"] } },
    required: ["result_faction"],
    additionalProperties: false,
  },
});

function eventRecord(): GameEventRecord {
  return {
    id: 9, game_id: 1, sequence_no: 3, logical_sequence_no: 2,
    phase: "night", round_no: 2, event_type: "phase_completed",
    actor_participant_id: null, target_participant_id: null, secondary_target_participant_id: null,
    actor: null, target: null, secondary_target: null, payload: { note: "original" },
    visibility: "public", source: "manual", schema_version: 1, status: "active",
    supersedes_event_id: null, revision_reason: null, invalidated_at: null,
    invalidated_by_user_id: null, invalidation_reason: null, created_by_user_id: 1,
    created_by: { user_id: 1, username: "judge", display_name: "Judge" },
    created_at: "2026-07-22T12:00:00Z", occurred_at: null, client_event_id: "original-id",
  };
}

function renderComposer(definitions = [phaseDefinition], onSubmit = vi.fn().mockResolvedValue(undefined)) {
  return {
    onSubmit,
    ...render(
      <LanguageProvider>
        <GameEventComposer definitions={definitions} disabled={false} events={[]} gameId={1} onSubmit={onSubmit} participants={[]} />
      </LanguageProvider>,
    ),
  };
}

describe("GameEventComposer", () => {
  beforeEach(() => {
    let counter = 0;
    vi.spyOn(globalThis.crypto, "randomUUID").mockImplementation(() => `00000000-0000-4000-8000-${String(++counter).padStart(12, "0")}`);
  });

  it("renders a clear state while server definitions are unavailable", () => {
    renderComposer([]);
    expect(screen.getByText("服务器尚未返回事件定义。")).toBeInTheDocument();
  });

  it("reports server-driven required actor and target fields", async () => {
    renderComposer([phaseDefinition, seerDefinition]);
    await userEvent.selectOptions(screen.getByLabelText("事件类型"), "seer_checked");
    await userEvent.click(screen.getByRole("button", { name: "保存事件" }));
    expect(screen.getByRole("alert")).toHaveTextContent("请检查事件表单中的错误");
    expect(screen.getByText("Actor is required.")).toBeInTheDocument();
    expect(screen.getByText("Target is required.")).toBeInTheDocument();
  });

  it("retains the same client ID after a network failure and changes it after body edits", async () => {
    const onSubmit = vi.fn().mockRejectedValueOnce(new TypeError("offline")).mockRejectedValueOnce(new TypeError("offline")).mockResolvedValue(undefined);
    renderComposer([phaseDefinition], onSubmit);
    await userEvent.click(screen.getByRole("button", { name: "保存事件" }));
    await screen.findByRole("button", { name: "使用相同请求重试" });
    const firstId = onSubmit.mock.calls[0][0].client_event_id;
    await userEvent.click(screen.getByRole("button", { name: "使用相同请求重试" }));
    expect(onSubmit.mock.calls[1][0].client_event_id).toBe(firstId);
    fireEvent.change(screen.getByLabelText("轮次"), { target: { value: "2" } });
    await userEvent.click(screen.getByRole("button", { name: "保存事件" }));
    expect(onSubmit.mock.calls[2][0].client_event_id).not.toBe(firstId);
    await waitFor(() => expect(localStorage.getItem(eventDraftStorageKey(1))).toBeNull());
  });

  it("restores and discards a local unsaved form", async () => {
    localStorage.setItem(eventDraftStorageKey(1), JSON.stringify({
      version: 1, formVersion: 1, gameId: 1, savedAt: "now", pending: null,
      form: { phase: "day", roundNo: 4, eventType: "phase_started", actorParticipantId: null, targetParticipantId: null, secondaryTargetParticipantId: null, payload: {}, occurredAt: null },
    }));
    renderComposer();
    expect(await screen.findByText("已恢复本地未提交草稿。")).toBeInTheDocument();
    expect(screen.getByLabelText("轮次")).toHaveValue(4);
    await userEvent.click(screen.getByRole("button", { name: "丢弃草稿" }));
    expect(localStorage.getItem(eventDraftStorageKey(1))).toBeNull();
  });

  it("restores a pending request with its original retry ID", async () => {
    const request = {
      phase: "night" as const,
      round_no: 1,
      event_type: "phase_started" as const,
      actor_participant_id: null,
      target_participant_id: null,
      secondary_target_participant_id: null,
      payload: {},
      occurred_at: null,
      client_event_id: "00000000-0000-4000-8000-000000000099",
    };
    localStorage.setItem(eventDraftStorageKey(1), JSON.stringify({
      version: 1,
      formVersion: 1,
      gameId: 1,
      savedAt: "now",
      form: { phase: "night", roundNo: 1, eventType: "phase_started", actorParticipantId: null, targetParticipantId: null, secondaryTargetParticipantId: null, payload: {}, occurredAt: null },
      pending: { clientEventId: request.client_event_id, request, fingerprint: "stored", createdAt: "now" },
    }));
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    renderComposer([phaseDefinition], onSubmit);
    await userEvent.click(await screen.findByRole("button", { name: "使用相同请求重试" }));
    expect(onSubmit).toHaveBeenCalledWith(request, null);
  });
});

describe("event mutation dialogs", () => {
  it("prefills correction content and requires a reason", async () => {
    render(
      <LanguageProvider>
        <CorrectEventDialog definitions={[phaseDefinition, definition("phase_completed", { payload_schema: { type: "object", properties: { note: { type: "string" } }, required: [], additionalProperties: false } })]} event={eventRecord()} events={[eventRecord()]} gameId={1} onClose={vi.fn()} onConflict={vi.fn()} onSubmit={vi.fn()} participants={[]} />
      </LanguageProvider>,
    );
    expect(screen.getByLabelText("轮次")).toHaveValue(2);
    expect(screen.getByLabelText("事件类型")).toHaveValue("phase_completed");
    await userEvent.click(screen.getByRole("button", { name: "保存纠正版本" }));
    expect(screen.getByText("必须填写原因。")).toBeInTheDocument();
  });

  it("requires explicit void reason and confirmation", async () => {
    const onConfirm = vi.fn();
    render(<LanguageProvider><VoidEventDialog busy={false} error={null} event={eventRecord()} onClose={vi.fn()} onConfirm={onConfirm} /></LanguageProvider>);
    const confirm = screen.getByRole("button", { name: "确认作废" });
    expect(confirm).toBeDisabled();
    await userEvent.type(screen.getByLabelText(/原因/), "incorrect entry");
    await userEvent.click(confirm);
    expect(onConfirm).toHaveBeenCalledWith("incorrect entry");
  });
});
