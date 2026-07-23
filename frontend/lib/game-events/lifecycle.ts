import type { GamePlayStatus, GameResultStatus } from "@/lib/api";


export type WorkbenchMode = {
  editable: boolean;
  entryMode: "live" | "backfill" | "locked";
  reasonKey: string;
};

export function resolveWorkbenchMode(game: {
  play_status: GamePlayStatus;
  result_status: GameResultStatus;
}): WorkbenchMode {
  const resultEditable = ["empty", "draft", "rejected"].includes(game.result_status);
  if (game.play_status === "in_progress" && resultEditable) {
    return { editable: true, entryMode: "live", reasonKey: "eventWorkbench.mode.live" };
  }
  if (game.play_status === "ended" && resultEditable) {
    return { editable: true, entryMode: "backfill", reasonKey: "eventWorkbench.mode.backfill" };
  }
  if (game.play_status === "scheduled") {
    return { editable: false, entryMode: "locked", reasonKey: "eventWorkbench.lock.scheduled" };
  }
  if (game.play_status === "cancelled") {
    return { editable: false, entryMode: "locked", reasonKey: "eventWorkbench.lock.cancelled" };
  }
  if (game.result_status === "submitted") {
    return { editable: false, entryMode: "locked", reasonKey: "eventWorkbench.lock.submitted" };
  }
  return { editable: false, entryMode: "locked", reasonKey: "eventWorkbench.lock.final" };
}
