"use client";

import { useEffect, useRef } from "react";

import { GameEventComposer } from "@/components/game-events/GameEventComposer";
import { useI18n } from "@/components/language-provider";
import type { GameEventBodyPayload, GameEventDefinition, GameEventRecord } from "@/lib/api";
import type { ParticipantOption } from "@/lib/game-events/form-types";


type CorrectEventDialogProps = {
  gameId: number;
  event: GameEventRecord;
  definitions: GameEventDefinition[];
  participants: ParticipantOption[];
  events: GameEventRecord[];
  onSubmit: (request: GameEventBodyPayload, reason: string) => Promise<void>;
  onClose: () => void;
  onConflict: () => void;
};

export function CorrectEventDialog(props: CorrectEventDialogProps) {
  const { t } = useI18n();
  const closeRef = useRef<HTMLButtonElement>(null);
  const onClose = props.onClose;
  useEffect(() => {
    closeRef.current?.focus();
    function escape(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", escape);
    return () => window.removeEventListener("keydown", escape);
  }, [onClose]);

  return (
    <div aria-labelledby="correct-event-title" aria-modal="true" className="fixed inset-0 z-50 overflow-y-auto bg-slate-950/60 p-0 sm:p-6" role="dialog">
      <div className="mx-auto min-h-full max-w-2xl bg-white p-4 shadow-2xl sm:min-h-0 sm:rounded-lg sm:p-6">
        <div className="mb-5 flex items-center justify-between gap-4 border-b border-slate-200 pb-4">
          <div>
            <h2 className="text-xl font-bold text-slate-900" id="correct-event-title">{t("eventWorkbench.correctEvent")}</h2>
            <p className="mt-1 text-sm text-slate-500">L{props.event.logical_sequence_no} · #{props.event.sequence_no}</p>
          </div>
          <button aria-label={t("common.cancel")} className="min-h-11 rounded-md border border-slate-300 px-4 text-sm font-semibold" onClick={props.onClose} ref={closeRef} type="button">{t("common.cancel")}</button>
        </div>
        <GameEventComposer
          definitions={props.definitions}
          disabled={false}
          events={props.events}
          gameId={props.gameId}
          initialEvent={props.event}
          mode="correct"
          onCancel={props.onClose}
          onConflict={props.onConflict}
          onSubmit={async (request, reason) => {
            await props.onSubmit(request, reason ?? "");
            props.onClose();
          }}
          participants={props.participants}
        />
      </div>
    </div>
  );
}
